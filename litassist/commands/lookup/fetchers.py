"""
Content fetching functionality for the lookup command.

This module handles fetching and extracting content from various sources including
HTML pages, PDFs, and JavaScript-rendered sites like Jade.io.
"""

import logging
import re
import requests
import concurrent.futures
from html.parser import HTMLParser

# Optional Selenium support for JavaScript-rendered content
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options

    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    logging.info(
        "Selenium not installed - Jade.io content may be limited. Install with: pip install selenium"
    )


class TextExtractor(HTMLParser):
    """
    Extract text from HTML, removing all tags, scripts, and styles.
    Reduces token count by 80-90% while preserving legal content.
    """

    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {"script", "style", "meta", "link", "noscript"}
        self.in_skip = False
        self.current_tag = None

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()
        if self.current_tag in self.skip_tags:
            self.in_skip = True
        # Add newlines for block elements to preserve structure
        elif tag.lower() in [
            "p",
            "div",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "br",
            "li",
            "tr",
        ]:
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags:
            self.in_skip = False
        # Add newlines after block elements
        elif tag.lower() in ["p", "div", "h1", "h2", "h3", "h4", "h5", "h6"]:
            self.text.append("\n")

    def handle_data(self, data):
        if not self.in_skip:
            text = data.strip()
            if text:
                # Clean up excessive whitespace but preserve structure
                text = " ".join(text.split())
                self.text.append(text)

    def get_text(self):
        """Get the extracted text with cleaned whitespace."""
        raw_text = " ".join(self.text)
        # Clean up multiple newlines but keep paragraph structure
        lines = [line.strip() for line in raw_text.split("\n")]
        lines = [line for line in lines if line]
        return "\n".join(lines)


def _fetch_url_content_selenium_with_timeout(url: str, timeout: int = 10) -> str:
    """
    Wrapper that adds hard timeout protection for Selenium fetches.
    Prevents indefinite hanging by enforcing a 30-second maximum.
    """
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_fetch_url_content_selenium, url, timeout)
        try:
            return future.result(timeout=30)  # Hard 30-second limit
        except concurrent.futures.TimeoutError:
            logging.warning(f"Selenium timed out after 30s for {url}")
            return ""
        except Exception as e:
            logging.warning(f"Selenium wrapper error for {url}: {e}")
            return ""


def _fetch_url_content_selenium(url: str, timeout: int = 10) -> str:
    """
    Advanced content fetching using Selenium for JavaScript-rendered pages.
    Only used for Jade.io when Selenium is available.
    """
    if not SELENIUM_AVAILABLE:
        return ""

    try:
        # Configure Chrome options for headless operation
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Suppress logs
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        chrome_options.add_argument("--log-level=3")

        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(timeout)

        try:
            driver.get(url)

            # Wait for content to load - Jade.io specific
            wait = WebDriverWait(driver, timeout)

            # Try different selectors for Jade.io content
            content_loaded = False
            for selector in [
                ".documenttext",
                ".document-content",
                ".case-content",
                "article",
                ".content",
            ]:
                try:
                    wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    content_loaded = True
                    break
                except Exception:
                    continue

            if not content_loaded:
                # Fall back to waiting for body to have substantial text
                wait.until(
                    lambda d: len(d.find_element(By.TAG_NAME, "body").text) > 500
                )

            # Get the page source after JavaScript has rendered
            page_source = driver.page_source

            # Extract text using the same TextExtractor as HTTP scraper
            try:
                parser = TextExtractor()
                parser.feed(page_source)
                extracted_text = parser.get_text()

                # Check if we got substantial content (lower threshold for JS-heavy sites)
                if (
                    len(extracted_text) < 200
                ):  # Lower threshold for JS sites with less text
                    logging.info(
                        f"Selenium: Skipping URL (no substantial text content): {url}"
                    )
                    return ""

                # Add URL reference at the top for context (same format as HTTP)
                text_with_source = f"[Source: {url}]\n\n{extracted_text}"

                # Log the reduction achieved
                original_size = len(page_source)
                final_size = len(text_with_source)
                reduction = 100 - (final_size / original_size * 100)
                logging.info(
                    f"Selenium extracted text from {url}: {original_size:,} → {final_size:,} chars ({reduction:.1f}% reduction)"
                )

                # Truncate if still massive (same limit as HTTP)
                return text_with_source[:250000]  # ~62k tokens max per document

            except Exception as e:
                logging.warning(
                    f"Selenium HTML parsing failed for {url}, falling back to regex: {e}"
                )
                # Fallback to old method if parsing fails
                page_source = re.sub(
                    r"<script.*?</script>", "", page_source, flags=re.DOTALL
                )
                page_source = re.sub(
                    r"<style.*?</style>", "", page_source, flags=re.DOTALL
                )
                text_only = re.sub(r"<[^>]+>", "", page_source)
                if len(text_only.strip()) > 500:
                    return page_source[:1000000]
                return ""

        finally:
            driver.quit()

    except Exception as e:
        logging.warning(f"Selenium fetch failed for {url}: {e}")

    return ""


def _extract_pdf_text(url: str, pdf_bytes: bytes) -> str:
    """
    Extract text from PDF without OCR.
    Returns marked-up text or empty string if extraction fails.
    """
    try:
        import pdfplumber
        import io

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            num_pages = len(pdf.pages)
            text_parts = []

            # Extract text from up to 50 pages
            pages_to_extract = min(num_pages, 50)
            for i, page in enumerate(pdf.pages[:pages_to_extract], 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            if text_parts:
                extracted_text = "\n".join(text_parts)
                # Add clear markers for LLM
                header = f"[PDF DOCUMENT EXTRACTED - {num_pages} pages total, {pages_to_extract} pages processed]\n"
                header += f"[Source: {url}]\n"
                header += "=" * 80 + "\n"

                if len(extracted_text) > 1000000:
                    extracted_text = extracted_text[:1000000]
                    header += "[Note: Text truncated to 1M chars]\n"

                logging.info(f"Successfully extracted text from PDF: {url}")
                return header + extracted_text + "\n" + "=" * 80 + "\n[END OF PDF]"
            else:
                logging.info(f"PDF has no extractable text (may be scanned): {url}")
                return ""

    except ImportError:
        logging.warning("pdfplumber not installed - cannot extract PDF text")
        return f"[PDF DOCUMENT at {url}]\n[Note: PDF text extraction unavailable - pdfplumber not installed]\n"
    except Exception as e:
        logging.warning(f"Failed to extract text from PDF {url}: {e}")
        return (
            f"[PDF DOCUMENT at {url}]\n[Note: PDF extraction failed - {str(e)[:100]}]\n"
        )


def _fetch_url_content(url: str, timeout: int = 5) -> str:
    """
    Fetch HTML and extract text content, removing tags for 80-90% token reduction.

    Like Van Gogh painting the night sky - we capture not every star,
    but the swirling essence. As Rilke would say: "Perhaps all the dragons
    in our lives are princesses who are only waiting to see us act,
    just once, with beauty and courage." Here, the dragon of messy HTML
    transforms into the princess of pure legal knowledge when we approach it
    with simple faith rather than complex fear.

    Note: Jade.io uses JavaScript rendering, so we skip it or try print versions.
    AustLII and legislation.gov.au use static HTML and work well.
    """
    # Smart URL detection - handle different sites appropriately
    if "://jade.io/" in url.lower():
        # Jade.io uses heavy JavaScript - content isn't in initial HTML
        # But /print and /download versions might be static!

        # If not already a print/download URL, try those versions first
        if "/print" not in url and "/download" not in url:
            # Try print version first (often static HTML)
            if "/article/" in url or "/summary/" in url:
                print_url = url.rstrip("/") + "/print"
                logging.info(f"Trying Jade.io print version: {print_url}")

                try:
                    response = requests.get(
                        print_url,
                        timeout=timeout,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                        },
                    )
                    if response.status_code == 200 and len(response.text) > 2000:
                        # Got substantial content from print version!
                        html = response.text

                        # Extract text content
                        try:
                            parser = TextExtractor()
                            parser.feed(html)
                            extracted_text = parser.get_text()

                            if len(extracted_text) > 500:
                                logging.info(
                                    "Success: Got content from Jade.io /print URL"
                                )
                                text_with_source = (
                                    f"[Source: {print_url}]\n\n{extracted_text}"
                                )
                                return text_with_source[:250000]
                        except Exception as e:
                            logging.warning(
                                f"HTML parsing with TextExtractor failed for {print_url}, falling back to regex: {e}"
                            )
                            # Fallback to regex method
                            html = re.sub(
                                r"<script.*?</script>", "", html, flags=re.DOTALL
                            )
                            html = re.sub(
                                r"<style.*?</style>", "", html, flags=re.DOTALL
                            )
                            text_only = re.sub(r"<[^>]+>", "", html)
                            if len(text_only.strip()) > 500:
                                logging.info(
                                    "Success: Got content from Jade.io /print URL"
                                )
                                return html[:1000000]
                except Exception as e:
                    logging.debug(f"Jade.io /print attempt failed: {e}")

            # If print didn't work, skip for now (would need Selenium)
            logging.info(f"Skipping Jade.io URL (needs JavaScript): {url}")
            return ""
        # If already a print/download URL, proceed to fetch normally

    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
        )
        if response.status_code == 200:
            # Check Content-Type for PDF
            content_type = response.headers.get("content-type", "").lower()

            # Handle PDF documents
            if "application/pdf" in content_type or url.lower().endswith(".pdf"):
                return _extract_pdf_text(url, response.content)

            # Continue with HTML handling
            html = response.text

            # Quick check for actual content vs empty template
            # If it's just boilerplate HTML with no real content, skip it
            if len(html) < 1000 or "window.location" in html[:500]:
                logging.info(
                    f"Skipping URL (appears to be JS redirect or empty): {url}"
                )
                return ""

            # Check for common signs of JavaScript-rendered content
            js_indicators = [
                '<div id="root">',
                '<div id="app">',
                "ng-app",
                "React",
                "Angular",
                "Vue.js",
            ]
            if any(indicator in html[:2000] for indicator in js_indicators):
                logging.info(f"Detected JavaScript framework at {url}, needs Selenium")
                return ""  # Will trigger Selenium fallback

            # Extract text content from HTML for 80-90% token reduction
            try:
                parser = TextExtractor()
                parser.feed(html)
                extracted_text = parser.get_text()

                # Check if we got actual legal content
                if len(extracted_text) < 500:
                    logging.info(f"Skipping URL (no substantial text content): {url}")
                    return ""

                # Add URL reference at the top for context
                text_with_source = f"[Source: {url}]\n\n{extracted_text}"

                # Log the reduction achieved
                original_size = len(html)
                final_size = len(text_with_source)
                reduction = 100 - (final_size / original_size * 100)
                logging.info(
                    f"Extracted text from {url}: {original_size:,} → {final_size:,} chars ({reduction:.1f}% reduction)"
                )

                # Truncate if still massive (some judgments can be quite long)
                return text_with_source[:250000]  # ~62k tokens max per document

            except Exception as e:
                logging.warning(
                    f"HTML parsing failed for {url}, falling back to regex: {e}"
                )
                # Fallback to old method if parsing fails
                html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
                html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL)
                text_only = re.sub(r"<[^>]+>", "", html)
                if len(text_only.strip()) < 500:
                    logging.info(f"Skipping URL (no substantial text content): {url}")
                    return ""
                return html[:1000000]
    except Exception as e:
        logging.warning(f"Failed to fetch {url}: {e}")
    return ""
