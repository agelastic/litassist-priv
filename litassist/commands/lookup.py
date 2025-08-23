"""
Rapid case-law lookup via Jade CSE + Gemini.

This module implements the 'lookup' command which searches for legal information
via Jade.io database using Google Custom Search, then processes the results with Google Gemini
to produce a structured legal answer citing relevant cases.
"""

import click
import warnings
import os
import logging
import time
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

from litassist.config import CONFIG
from litassist.utils import (
    save_log,
    timed,
    save_command_output,
    process_extraction_response,
    warning_message,
    success_message,
    saved_message,
    stats_message,
    info_message,
    verifying_message,
    tip_message,
    error_message,
    LOG_DIR,
)
from litassist.llm import LLMClientFactory
from litassist.prompts import PROMPTS

# Suppress Google API cache warning
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
warnings.filterwarnings("ignore", message=".*file_cache.*")


def _perform_cse_search(service, query, cse_id, limit, primary=False):
    """Perform a Google Custom Search Engine lookup and return links with snippets."""
    from googleapiclient.errors import Error as GoogleApiError

    if not cse_id:
        return [], []
    try:
        res = service.cse().list(q=query, cx=cse_id, num=limit).execute()
        items = res.get("items", [])
        links = [item.get("link") for item in items]
        snippets = []
        for item in items:
            title = item.get("title", "")
            snippet = item.get("snippet", "").replace("\n", " ")
            link = item.get("link", "")
            # Collect ALL snippets from search results
            snippets.append(f"[{title}]\n{link}\n{snippet}")
        return links, snippets
    except GoogleApiError as e:
        msg = f"CSE search failed for '{cse_id}': {e}"
        if primary:
            raise click.ClickException(msg)
        click.echo(f"Warning: {msg}")
        logging.exception(msg)
        return [], []


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

            # Clean up the HTML
            page_source = re.sub(
                r"<script.*?</script>", "", page_source, flags=re.DOTALL
            )
            page_source = re.sub(r"<style.*?</style>", "", page_source, flags=re.DOTALL)

            # Check if we got real content
            text_only = re.sub(r"<[^>]+>", "", page_source)
            if len(text_only.strip()) > 500:
                return page_source[:1000000]

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
        return ""
    except Exception as e:
        logging.warning(f"Failed to extract text from PDF {url}: {e}")
        return ""


class TextExtractor(HTMLParser):
    """
    Extract text from HTML, removing all tags, scripts, and styles.
    Reduces token count by 80-90% while preserving legal content.
    """
    def __init__(self):
        super().__init__()
        self.text = []
        self.skip_tags = {'script', 'style', 'meta', 'link', 'noscript'}
        self.in_skip = False
        self.current_tag = None
        
    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()
        if self.current_tag in self.skip_tags:
            self.in_skip = True
        # Add newlines for block elements to preserve structure
        elif tag.lower() in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'li', 'tr']:
            self.text.append('\n')
            
    def handle_endtag(self, tag):
        if tag.lower() in self.skip_tags:
            self.in_skip = False
        # Add newlines after block elements
        elif tag.lower() in ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            self.text.append('\n')
            
    def handle_data(self, data):
        if not self.in_skip:
            text = data.strip()
            if text:
                # Clean up excessive whitespace but preserve structure
                text = ' '.join(text.split())
                self.text.append(text)
                
    def get_text(self):
        """Get the extracted text with cleaned whitespace."""
        raw_text = ' '.join(self.text)
        # Clean up multiple newlines but keep paragraph structure
        lines = [line.strip() for line in raw_text.split('\n')]
        lines = [line for line in lines if line]
        return '\n'.join(lines)


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
                                logging.info("Success: Got content from Jade.io /print URL")
                                text_with_source = f"[Source: {print_url}]\n\n{extracted_text}"
                                return text_with_source[:250000]
                        except Exception as e:
                            logging.warning(f"HTML parsing with TextExtractor failed for {print_url}, falling back to regex: {e}")
                            # Fallback to regex method
                            html = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
                            html = re.sub(r"<style.*?</style>", "", html, flags=re.DOTALL)
                            text_only = re.sub(r"<[^>]+>", "", html)
                            if len(text_only.strip()) > 500:
                                logging.info("Success: Got content from Jade.io /print URL")
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
                logging.info(f"Extracted text from {url}: {original_size:,} → {final_size:,} chars ({reduction:.1f}% reduction)")
                
                # Truncate if still massive (some judgments can be quite long)
                return text_with_source[:250000]  # ~62k tokens max per document
                
            except Exception as e:
                logging.warning(f"HTML parsing failed for {url}, falling back to regex: {e}")
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


@click.command()
@click.argument("question")
@click.option("--mode", type=click.Choice(["irac", "broad"]), default="irac")
@click.option(
    "--extract",
    type=click.Choice(["citations", "principles", "checklist"]),
    help="Extract specific information in a structured format",
)
@click.option(
    "--comprehensive",
    is_flag=True,
    help=(
        "Enable comprehensive mode: standard searches yield up to 5 results each from Jade and AustLII; "
        "comprehensive mode yields up to 10 results each from Jade, AustLII, and a secondary CSE."
    ),
)
@click.option(
    "--context",
    type=str,
    help="Contextual information to guide the lookup analysis",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.option("--no-fetch", is_flag=True, help="Skip content fetching, use URLs only")
@timed
def lookup(question, mode, extract, comprehensive, context, output, no_fetch):
    """
    Rapid case-law lookup via Jade CSE + Gemini.

    Searches for legal information using Jade.io database via Custom Search Engine,
    then processes the results with Google Gemini to produce a structured
    legal answer citing relevant cases.

    Args:
        question: The legal question to search for.
        mode: Answer format - 'irac' (Issue, Rule, Application, Conclusion) for
              structured analysis, or 'broad' for more creative exploration.
        extract: Extract specific information - 'citations' for case references,
                'principles' for legal rules, or 'checklist' for practical items.
    comprehensive: If True, switches to comprehensive mode: standard searches yield up to
        5 results each from Jade and AustLII; comprehensive searches yield up to
        10 results each from Jade, AustLII, and an additional CSE.

    Raises:
        click.ClickException: If there are errors with the search or LLM API calls.
    """
    # Fetch case links using configured Custom Search Engines
    try:
        from googleapiclient.discovery import build

        service = build(
            "customsearch", "v1", developerKey=CONFIG.g_key, cache_discovery=False
        )
    except Exception as e:
        raise click.ClickException(f"Search initialization error: {e}")

    # Collect links and snippets from configured Custom Search Engines
    links = []
    all_snippets = []  # Collect all search snippets from Google CSE
    # Determine per-source limits
    if comprehensive:
        jade_limit = austlii_limit = comp_limit = 10
    else:
        jade_limit = austlii_limit = 5
    # Primary Jade CSE search
    jade_links, jade_snippets = _perform_cse_search(
        service, question, CONFIG.cse_id, jade_limit, primary=True
    )
    links.extend(jade_links)
    all_snippets.extend(jade_snippets)

    # Rate limit delay between CSE calls
    cse_delay = float(os.environ.get("CSE_RATE_LIMIT_DELAY", "1.5"))
    if cse_delay > 0 and (getattr(CONFIG, "cse_id_austlii", None) or comprehensive):
        click.echo(f"Rate limiting: waiting {cse_delay}s...")
        time.sleep(cse_delay)

    # AustLII CSE search (optional)
    austlii_links, austlii_snippets = _perform_cse_search(
        service, question, getattr(CONFIG, "cse_id_austlii", None), austlii_limit
    )
    links.extend(austlii_links)
    all_snippets.extend(austlii_snippets)

    # Rate limit delay before comprehensive search
    if cse_delay > 0 and comprehensive:
        click.echo(f"Rate limiting: waiting {cse_delay}s...")
        time.sleep(cse_delay)

    # Comprehensive CSE search (optional)
    if comprehensive:
        comp_links, comp_snippets = _perform_cse_search(
            service, question, getattr(CONFIG, "cse_id_comprehensive", None), comp_limit
        )
        links.extend(comp_links)
        all_snippets.extend(comp_snippets)
    # Remove duplicate and empty links while preserving order
    links = list(dict.fromkeys(filter(None, links)))
    # Display found links
    click.echo("Found links:")
    for link in links:
        click.echo(f"- {link}")

    # Save all search snippets to log file if any were collected
    if all_snippets:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        snippet_file = os.path.join(LOG_DIR, f"cse_snippets_{timestamp}.txt")
        with open(snippet_file, "w", encoding="utf-8") as f:
            f.write(f"Query: {question}\n")
            if context:
                f.write(f"Context: {context}\n")
            f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 80 + "\n\n")
            f.write("GOOGLE CSE SEARCH SNIPPETS\n")
            f.write("-" * 40 + "\n\n")

            # Group snippets by domain for better organization
            snippet_by_domain = {}
            for snippet in all_snippets:
                # Extract domain from the link line in the snippet
                lines = snippet.split("\n")
                link_line = next(
                    (line for line in lines if line.startswith("http")), ""
                )
                domain = (
                    link_line.split("/")[2]
                    if link_line and "/" in link_line
                    else "unknown"
                )

                if domain not in snippet_by_domain:
                    snippet_by_domain[domain] = []
                snippet_by_domain[domain].append(snippet)

            # Write snippets grouped by domain
            for domain in sorted(snippet_by_domain.keys()):
                f.write(f"=== {domain.upper()} ===\n\n")
                for snippet in snippet_by_domain[domain]:
                    f.write(snippet + "\n\n" + "-" * 40 + "\n\n")

        click.echo(info_message(f"Saved {len(all_snippets)} search snippet(s) to logs"))

    # Fetch ALL working content (skip only Jade.io JavaScript pages)
    contents = []
    fetched_count = 0
    skipped_count = 0
    pdf_count = 0  # Track PDFs separately

    # Check if Selenium should be disabled
    selenium_enabled = SELENIUM_AVAILABLE and CONFIG.selenium_enabled
    if SELENIUM_AVAILABLE and not CONFIG.selenium_enabled:
        click.echo("  [Info: Selenium disabled in config]")

    # Skip fetching if --no-fetch flag is set
    if no_fetch:
        click.echo("  [Info: Content fetching disabled by --no-fetch flag]")
    else:
        max_time = CONFIG.max_fetch_time  # Use config value
        start_time = time.time()

    # Prioritize AustLII and legislation.gov.au URLs (they work best)
    prioritized_links = []
    other_links = []
    for link in links:
        if "austlii.edu.au" in link.lower() or "legislation.gov.au" in link.lower():
            prioritized_links.append(link)
        else:
            other_links.append(link)

    # Try prioritized links first, then others
    ordered_links = prioritized_links + other_links

    # Track last fetch time per domain for rate limiting
    domain_last_fetch = {}

    if not no_fetch:
        click.echo(
            f"  Attempting to fetch content from {len(ordered_links)} sources..."
        )

        for i, link in enumerate(ordered_links):
            # Safety check: don't run forever
            if time.time() - start_time > max_time:
                click.echo(
                    f"  [⚠ Time limit reached, stopping after {fetched_count} successful fetches]"
                )
                break

            # Skip jade.io main domain URLs - use snippets instead
            if "://jade.io/" in link.lower():
                click.echo(
                    "  [→ Jade.io: Using search snippet only (site restrictions)]"
                )
                skipped_count += 1
                continue  # Skip to next URL

            # Domain-based rate limiting (0.5s between requests to same domain)
            domain = link.split("/")[2]
            if domain in domain_last_fetch:
                elapsed = time.time() - domain_last_fetch[domain]
                if elapsed < 0.5:
                    time.sleep(0.5 - elapsed)
            domain_last_fetch[domain] = time.time()

            content = _fetch_url_content(link, timeout=CONFIG.fetch_timeout)

            # If HTTP fetch got minimal/no content, try Selenium for non-Jade sites
            if (not content or len(content) < 1000) and selenium_enabled:
                if (
                    "jade.io" not in link.lower()
                ):  # Never use Selenium for any jade.io domain
                    click.echo(f"  [↻ Trying Selenium for {link.split('/')[2]}...]")
                    selenium_content = _fetch_url_content_selenium_with_timeout(
                        link,
                        timeout=CONFIG.fetch_timeout
                        * CONFIG.selenium_timeout_multiplier,
                    )
                    if selenium_content and len(selenium_content) > len(content or ""):
                        content = selenium_content
                        method = "Selenium"
                    else:
                        method = "HTTP"
                else:
                    method = "HTTP"
            else:
                method = "HTTP"

            if content:
                # Save fetched page to logs
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                domain = link.split("/")[2].replace(".", "_")

                # Check if it's PDF content for appropriate file naming
                if content.startswith("[PDF DOCUMENT EXTRACTED"):
                    log_file = os.path.join(
                        LOG_DIR, f"pdf_extracted_{domain}_{timestamp}.txt"
                    )
                else:
                    log_file = os.path.join(
                        LOG_DIR, f"fetched_{domain}_{timestamp}.html"
                    )
                with open(log_file, "w", encoding="utf-8") as f:
                    f.write(f"<!-- URL: {link} -->\n")
                    f.write(f"<!-- Fetched: {time.strftime('%Y-%m-%d %H:%M:%S')} -->\n")
                    f.write(content)

                contents.append(
                    f"=== ACTUAL CONTENT FROM: {link} ===\n{content}\n=== END OF CONTENT FROM: {link} ===\n"
                )

                # Check if it's PDF content for appropriate user message
                if content.startswith("[PDF DOCUMENT EXTRACTED"):
                    click.echo(f"  [✓ Extracted text from PDF at {link.split('/')[2]}]")
                    pdf_count += 1
                else:
                    click.echo(
                        f"  [✓ Fetched {len(content)} chars from {link.split('/')[2]} via {method}]"
                    )
                fetched_count += 1
            else:
                # Show why it was skipped (non-Jade URLs)
                click.echo(f"  [✗ Failed to fetch from {link.split('/')[2]}]")
                skipped_count += 1

    # Summary of fetch results
    if fetched_count > 0:
        click.echo(f"\n  Successfully fetched content from {fetched_count} source(s)")
    if pdf_count > 0:
        click.echo(f"  Extracted text from {pdf_count} PDF document(s)")
    if skipped_count > 0:
        click.echo(
            f"  Skipped {skipped_count} source(s) (JavaScript, empty content, or non-extractable PDFs)"
        )

    # Add all search snippets to the beginning of content if available
    if all_snippets:
        snippet_text = "=== GOOGLE CSE SEARCH SNIPPETS ===\n"
        snippet_text += "Note: These are brief search result excerpts from Google, not full content.\n"
        snippet_text += "Sources include: jade.io, austlii.edu.au, legislation.gov.au, and other legal sites.\n\n"

        # Group snippets by domain for better organization
        snippet_by_domain = {}
        for snippet in all_snippets:
            lines = snippet.split("\n")
            link_line = next((line for line in lines if line.startswith("http")), "")
            domain = (
                link_line.split("/")[2] if link_line and "/" in link_line else "unknown"
            )

            if domain not in snippet_by_domain:
                snippet_by_domain[domain] = []
            snippet_by_domain[domain].append(snippet)

        # Add snippets grouped by domain
        for domain in sorted(snippet_by_domain.keys()):
            snippet_text += f"\n--- {domain} ---\n"
            snippet_text += "\n\n".join(snippet_by_domain[domain])
            snippet_text += "\n"

        snippet_text += "\n=== END OF SEARCH SNIPPETS ===\n"
        contents.insert(0, snippet_text)

    # Initialize variables for content and token tracking
    content_text = ""
    estimated_tokens = 0

    # Prepare prompt using centralized template
    if contents:
        # Calculate token estimate and use ALL content intelligently
        total_chars = sum(len(c) for c in contents)
        estimated_tokens = total_chars / 4  # Rough estimate: 4 chars per token

        # Model-specific token limits (adjust when changing models)
        # Gemini 2.5 Pro: 1M context window - using 90% (900k) for content
        # Reserve 100k for response generation, prompts, and safety margin
        # WARNING: Other models have smaller limits - see warning below
        max_content_tokens = 900000  # 90% of Gemini 2.5 Pro's 1M limit

        if estimated_tokens > max_content_tokens:
            # Smart truncation: keep as much as possible
            click.echo(
                f"  [Note: Content exceeds {max_content_tokens:,} token limit ({int(estimated_tokens):,} tokens estimated), intelligently truncating]"
            )

            # Calculate how many documents we can include
            chars_per_doc = total_chars / len(contents)
            docs_to_include = int(max_content_tokens * 4 / chars_per_doc)
            content_text = "\n".join(contents[:docs_to_include])

            click.echo(
                f"  [Including {docs_to_include} of {len(contents)} fetched documents]"
            )
        else:
            # Use ALL fetched content - no artificial limits!
            content_text = "\n".join(contents)
            click.echo(
                f"  [Using all {len(contents)} fetched documents (~{int(estimated_tokens):,} tokens)]"
            )

        # Create a rich prompt with actual content
        prompt = f"""Question: {question}

Successfully fetched and providing ACTUAL CONTENT from {len(contents)} legal sources:
{chr(10).join(links)}

Below is the REAL HTML/TEXT content fetched directly from these URLs:
{content_text}

IMPORTANT: You are reading the ACTUAL CONTENT from these web pages, not just their URLs. 
Analyze this real content to provide comprehensive legal analysis with specific quotes and references."""
    else:
        # Fallback to URL-only prompt (existing behavior)
        prompt = PROMPTS.get("analysis.lookup.question_prompt").format(
            question=question, links="\n".join(links)
        )
    if context:
        prompt = PROMPTS.get("analysis.lookup.context_prompt").format(
            context=context, prompt=prompt
        )

    # Add extraction-specific instructions
    if extract:
        if extract == "citations":
            prompt += f"\n\n{PROMPTS.get('lookup.extraction_instructions.citations')}"
        elif extract == "principles":
            prompt += f"\n\n{PROMPTS.get('lookup.extraction_instructions.principles')}"
        elif extract == "checklist":
            prompt += f"\n\n{PROMPTS.get('lookup.extraction_instructions.checklist')}"
    # Set parameters based on mode and comprehensive flag
    if comprehensive:
        if mode == "irac":
            overrides = {
                "temperature": 0,
                "top_p": 0.05,
                "max_tokens": 8192,
            }  # Maximum precision
        else:  # broad
            overrides = {
                "temperature": 0.3,
                "top_p": 0.7,
                "max_tokens": 8192,
            }  # Controlled creativity
    else:
        # Standard parameters
        if mode == "irac":
            overrides = {"temperature": 0, "top_p": 0.1}
        else:
            overrides = {"temperature": 0.5, "top_p": 0.9}

    # Use LLMClientFactory to create the client
    client = LLMClientFactory.for_command("lookup", **overrides)

    # Warn if using large content with non-Gemini models
    if content_text and estimated_tokens > 200000:
        # Check if we're not using Gemini (the model attribute should be available on client)
        if not hasattr(client, "model") or "gemini" not in client.model.lower():
            click.echo(
                warning_message(
                    f"Large content ({int(estimated_tokens):,} tokens) with non-Gemini model. "
                    "Consider using Gemini 2.5 Pro for better handling of large contexts."
                )
            )

    # Set system prompt based on mode
    base_system = PROMPTS.get("base.australian_law")

    # Special system prompt for extraction mode
    if extract:
        extraction_system = PROMPTS.get("lookup.extraction_system")
        system_content = f"{base_system}\n\n{extraction_system}"
    elif comprehensive:
        requirements = PROMPTS.get("lookup.comprehensive_analysis.requirements")
        citation_requirements = PROMPTS.get(
            "lookup.comprehensive_analysis.citation_requirements"
        )
        output_structure = PROMPTS.get("lookup.comprehensive_analysis.output_structure")
        system_content = f"""{base_system} Provide exhaustive legal analysis.

{requirements}

{citation_requirements}

{output_structure}"""
    else:
        standard_instructions = PROMPTS.get("lookup.standard_analysis.instructions")
        system_content = f"{base_system}\n\n{standard_instructions}"

    # Token pre-flight check
    system_tokens = len(system_content) / 4  # Rough estimate
    user_tokens = len(prompt) / 4
    total_request_tokens = system_tokens + user_tokens

    # Check against known model limits
    model_limits = {
        "gemini": 1000000,  # 1M tokens
        "claude": 200000,  # 200k tokens
        "gpt-4": 128000,  # 128k tokens
    }

    # Get model type from client
    model_type = "unknown"
    if hasattr(client, "model") and hasattr(client.model, "lower"):
        model_str = client.model.lower()
        if "gemini" in model_str:
            model_type = "gemini"
        elif "claude" in model_str:
            model_type = "claude"
        elif "gpt" in model_str:
            model_type = "gpt-4"
    max_tokens = model_limits.get(model_type, 100000)  # Conservative default

    if total_request_tokens > max_tokens * 0.9:  # 90% safety margin
        click.echo(
            warning_message(
                f"Request size ({int(total_request_tokens):,} tokens) exceeds safe limit for {model_type}. "
                f"Truncating content..."
            )
        )
        # Truncate the prompt to fit
        max_prompt_chars = int(max_tokens * 0.8 * 4)  # 80% for prompt, convert to chars
        prompt = prompt[:max_prompt_chars] + "\n[Content truncated due to token limits]"

    # Retry logic for transient errors
    max_retries = 2
    retry_delay = 5
    content = None
    usage = None

    for attempt in range(max_retries + 1):
        try:
            content, usage = client.complete(
                [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": prompt},
                ]
            )
            break  # Success, exit retry loop

        except Exception as e:
            error_str = str(e)
            # Debug logging
            import logging

            logging.error(f"Lookup error details: {error_str}")

            # Check if this is a retryable error
            if attempt < max_retries and any(
                x in error_str.lower() for x in ["choices", "timeout", "rate", "retry"]
            ):
                click.echo(
                    warning_message(
                        f"API error on attempt {attempt + 1}/{max_retries + 1}, retrying in {retry_delay}s..."
                    )
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
                continue

            # Final attempt failed or non-retryable error
            # Provide specific error handling based on error type
            if "quota exceeded" in error_str.lower():
                click.echo(
                    error_message(
                        "Google API quota exceeded. Options:\n"
                        "  - Wait until quota resets (usually daily)\n"
                        "  - Upgrade your Google API quota limits\n"
                        "  - Use --no-fetch to skip content fetching\n"
                        "  - Try again later with smaller document sets"
                    )
                )
            elif "billing not enabled" in error_str.lower():
                click.echo(
                    error_message(
                        "Google API billing not enabled. To fix:\n"
                        "  1. Go to https://console.cloud.google.com/billing\n"
                        "  2. Enable billing for your project\n"
                        "  3. Ensure the Generative Language API is enabled"
                    )
                )
            elif "api not enabled" in error_str.lower() or "disabled" in error_str.lower():
                click.echo(
                    error_message(
                        "Google Generative Language API not enabled. To fix:\n"
                        "  1. Go to Google Cloud Console\n"
                        "  2. Enable 'Generative Language API'\n"
                        "  3. Verify your API key has access"
                    )
                )
            elif "authentication failed" in error_str.lower():
                click.echo(
                    error_message(
                        "Google API authentication failed. To fix:\n"
                        "  1. Go to https://openrouter.ai/settings/keys\n"
                        "  2. Add your Google API key (BYOK)\n"
                        "  3. Enable 'Always use this key' for google/gemini models"
                    )
                )
            elif "maximum context length" in error_str.lower():
                click.echo(
                    error_message(
                        "Context length exceeded (>1M tokens). Try:\n"
                        "  - Using standard mode instead of --comprehensive\n"
                        "  - Using --no-fetch to analyze only search results\n"
                        "  - Reducing the number of documents fetched"
                    )
                )
            elif "choices" in error_str.lower():
                click.echo(
                    error_message(
                        "API response format error. This usually means:\n"
                        "  - Request was too large (token limit exceeded)\n"
                        "  - API timeout or rate limit\n"
                        "  - Service temporarily unavailable"
                    )
                )

                # Save fetched content so user doesn't lose it
                if contents:
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    error_file = os.path.join(
                        LOG_DIR, f"lookup_error_content_{timestamp}.txt"
                    )
                    with open(error_file, "w", encoding="utf-8") as f:
                        f.write(f"Error: {error_str}\n\n")
                        f.write(f"Query: {question}\n")
                        if context:
                            f.write(f"Context: {context}\n")
                        f.write("\n=== FETCHED CONTENT (saved for retry) ===\n\n")
                        f.write("\n".join(contents))
                    click.echo(
                        info_message("Fetched content saved to logs for manual review")
                    )

            elif "token" in error_str.lower() or "limit" in error_str.lower():
                click.echo(
                    error_message(
                        "Token limit exceeded. Try:\n"
                        "  - Using --no-fetch to skip content fetching\n"
                        "  - Reducing search scope\n"
                        "  - Using standard mode instead of --comprehensive"
                    )
                )

            elif "timeout" in error_str.lower():
                click.echo(
                    error_message(
                        "Request timed out. The content was likely too large. "
                        "Try again with fewer sources."
                    )
                )

            elif "Citation verification failed" in error_str:
                click.echo(warning_message("Citation verification issues detected"))

            else:
                # Generic error
                click.echo(error_message(f"LLM API error: {error_str}"))

            # Don't lose all the work - offer recovery options
            if contents:
                click.echo(
                    tip_message(
                        "Tip: Use 'litassist lookup --no-fetch' with the same query to analyze "
                        "just the search results without fetching content"
                    )
                )

            raise click.ClickException("Lookup failed - see error details above")

    # Process extraction if requested
    if extract:
        # Generate output prefix for files
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_prefix = f"lookup_{extract}_{timestamp}"

        # Use shared extraction utility
        formatted_content, json_data, json_file = process_extraction_response(
            content, extract, output_prefix, "lookup"
        )

        # Save the formatted text output
        command_name = f"{output}_{extract}" if output else f"lookup_{extract}"
        metadata = {"Query": question, "Mode": mode, "Extract": extract}
        if context:
            metadata["Context"] = context
        if comprehensive:
            metadata["Comprehensive"] = "True"
        metadata["JSON File"] = json_file

        output_file = save_command_output(
            command_name,
            formatted_content,
            "" if output else question,
            metadata=metadata,
        )
    else:
        # Non-extraction mode - save content as-is
        formatted_content = content
        command_name = output if output else "lookup"
        metadata = {"Query": question, "Mode": mode}
        if context:
            metadata["Context"] = context
        if comprehensive:
            metadata["Comprehensive"] = "True"

        output_file = save_command_output(
            command_name,
            formatted_content,
            "" if output else question,
            metadata=metadata,
        )

    # Save audit log
    params_str = f"mode={mode}"
    if extract:
        params_str += f", extract={extract}"
    if comprehensive:
        params_str += ", comprehensive=True"

    save_log(
        "lookup",
        {
            "params": params_str,
            "inputs": {
                "question": question,
                "links": "\n".join(links),
                "context": context,
                "prompt": prompt,
            },
            "response": content,
            "formatted_output": formatted_content,
            "usage": usage,
            "output_file": output_file,
        },
    )

    # Show summary instead of full content
    click.echo(f"\n{success_message('Lookup complete!')}")
    click.echo(saved_message(f'Output saved to: "{output_file}"'))

    # Show what was found
    if extract:
        extract_type = extract.capitalize()
        msg = stats_message(f"{extract_type} extracted from search results")
        click.echo(f"\n{msg}")
    else:
        analysis_type = "Exhaustive" if comprehensive else "Standard"
        msg = stats_message(f"{analysis_type} legal analysis for: {question}")
        click.echo(f"\n{msg}")

    # Show context if provided
    if context:
        click.echo(info_message(f"Context: '{context}'"))

    # Show links that were searched
    if comprehensive:
        msg = verifying_message(f"Exhaustive search: {len(links)} sources analyzed")
        click.echo(f"\n{msg}")
    else:
        msg = verifying_message(f"Standard search: {len(links)} sources analyzed")
        click.echo(f"\n{msg}")

    for i, link in enumerate(links, 1):
        click.echo(f"   {i}. {link}")

    tip_msg = tip_message(f'View full analysis: open "{output_file}"')
    click.echo(f"\n{tip_msg}")
