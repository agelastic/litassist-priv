"""
Content fetching functionality for the lookup command.

This module handles fetching and extracting content from various sources including
HTML pages, PDFs, and JavaScript-rendered sites like Jade.io.
"""

import logging
import re
import requests
import time
from html.parser import HTMLParser
from litassist.logging_utils import save_log

# Removed Selenium dependency - using Jina Reader API instead


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




def _fetch_via_jina(url: str, timeout: int = 15) -> str:
    """
    Fetch content using Jina Reader API - works for JavaScript sites and complex HTML.
    
    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Extracted text content or empty string if failed
    """
    try:
        headers = {}
        # Use Jina API key if configured for higher rate limits
        from litassist.config import get_config
        config = get_config()
        if hasattr(config, 'jina_api_key') and config.jina_api_key:
            headers['Authorization'] = f'Bearer {config.jina_api_key}'
        
        response = requests.get(f"https://r.jina.ai/{url}", headers=headers, timeout=timeout)
        
        if response.status_code == 200 and len(response.text) > 500:
            content = f"[Source: {url}]\n\n{response.text}"
            save_log("fetch_attempt", {
                "url": url,
                "method": "jina_reader",
                "status": "success",
                "content_size": len(response.text),
                "content": content[:250000],
                "timestamp": time.time()
            })
            return content[:250000]
        else:
            save_log("fetch_attempt", {
                "url": url,
                "method": "jina_reader",
                "status": "failed",
                "http_status": response.status_code,
                "reason": f"HTTP {response.status_code}" if response.status_code != 200 else "Insufficient content",
                "content": "",
                "timestamp": time.time()
            })
            return ""
    except Exception as e:
        logging.warning(f"Jina Reader failed for {url}: {e}")
        save_log("fetch_attempt", {
            "url": url,
            "method": "jina_reader",
            "status": "failed",
            "error": str(e),
            "content": "",
            "timestamp": time.time()
        })
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
                pdf_content = header + extracted_text + "\n" + "=" * 80 + "\n[END OF PDF]"
                save_log("fetch_attempt", {
                    "url": url,
                    "method": "pdf",
                    "status": "success",
                    "pdf_pages": num_pages,
                    "pages_extracted": pages_to_extract,
                    "extracted_size": len(extracted_text),
                    "final_size": len(pdf_content),
                    "content": pdf_content,
                    "timestamp": time.time()
                })
                return pdf_content
            else:
                logging.info(f"PDF has no extractable text (may be scanned): {url}")
                save_log("fetch_attempt", {
                    "url": url,
                    "method": "pdf",
                    "status": "skipped",
                    "reason": "PDF has no extractable text (may be scanned)",
                    "content": "",
                    "timestamp": time.time()
                })
                return ""

    except ImportError:
        logging.warning("pdfplumber not installed - cannot extract PDF text")
        return f"[PDF DOCUMENT at {url}]\n[Note: PDF text extraction unavailable - pdfplumber not installed]\n"
    except Exception as e:
        logging.warning(f"Failed to extract text from PDF {url}: {e}")
        return (
            f"[PDF DOCUMENT at {url}]\n[Note: PDF extraction failed - {str(e)[:100]}]\n"
        )


def _fetch_url_content(url: str, timeout: int = 10) -> str:
    """
    Fetch content from URL - tries direct HTTP first, falls back to Jina if minimal content.
    Handles PDFs, HTML, and JavaScript-rendered sites automatically.
    """
    # Skip jade.io entirely (blocked by Jina, JS-heavy, no good fallback)
    if 'jade.io' in url.lower():
        logging.info(f"Skipping Jade.io URL (blocked by scrapers): {url}")
        save_log("fetch_attempt", {
            "url": url,
            "method": "skipped",
            "status": "blocked",
            "reason": "Jade.io blocked by scrapers",
            "content": "",
            "timestamp": time.time()
        })
        return ""

    try:
        # First, get the content with direct HTTP
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
        )
        
        if response.status_code != 200:
            # Try Jina before giving up
            jina_content = _fetch_via_jina(url, timeout)
            if jina_content:
                return jina_content
            
            save_log("fetch_attempt", {
                "url": url,
                "method": "http",
                "status": "failed",
                "http_status": response.status_code,
                "content": "",
                "timestamp": time.time()
            })
            return ""
        
        # Check for PDF (3 methods)
        content_type = response.headers.get("content-type", "").lower()
        is_pdf = False
        
        # Method 1: Content-Type header
        if "application/pdf" in content_type:
            is_pdf = True
        # Method 2: URL ends with .pdf
        elif url.lower().endswith(".pdf"):
            is_pdf = True
        # Method 3: Content starts with PDF signature
        elif response.content[:5] == b'%PDF-':
            is_pdf = True
        
        if is_pdf:
            return _extract_pdf_text(url, response.content)

        
        # Extract HTML text
        html = response.text
        
        # Use TextExtractor to parse HTML
        try:
            parser = TextExtractor()
            parser.feed(html)
            extracted_text = parser.get_text()
        except Exception as e:
            logging.warning(f"HTML parsing failed for {url}: {e}")
            # Simple fallback - remove tags with regex
            html_clean = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL)
            html_clean = re.sub(r"<style.*?</style>", "", html_clean, flags=re.DOTALL)
            extracted_text = re.sub(r"<[^>]+>", "", html_clean).strip()
        
        # If we got minimal content (< 1000 chars), try Jina
        # This catches ALL cases: JavaScript sites, bot protection, paywall, etc.
        if len(extracted_text) < 1000:
            logging.info(f"Minimal content from HTTP ({len(extracted_text)} chars), trying Jina for {url}")
            jina_content = _fetch_via_jina(url, timeout)
            
            # Use Jina content if it got more than HTTP
            if len(jina_content) > len(extracted_text):
                return jina_content
        
        # We got good content from HTTP, use it
        if extracted_text:
            text_with_source = f"[Source: {url}]\n\n{extracted_text}"
            final_content = text_with_source[:250000]
            
            # Log success
            original_size = len(html)
            reduction = 100 - (len(extracted_text) / original_size * 100) if original_size > 0 else 0
            logging.info(f"Extracted {len(extracted_text)} chars from {url} ({reduction:.1f}% reduction)")
            
            save_log("fetch_attempt", {
                "url": url,
                "method": "http",
                "status": "success",
                "html_size": original_size,
                "extracted_size": len(extracted_text),
                "final_size": len(final_content),
                "reduction_percent": f"{reduction:.1f}",
                "content": final_content,
                "timestamp": time.time()
            })
            return final_content
        
        # No content at all
        save_log("fetch_attempt", {
            "url": url,
            "method": "http",
            "status": "failed",
            "reason": "No content extracted",
            "content": "",
            "timestamp": time.time()
        })
        return ""
    except Exception as e:
        logging.warning(f"Failed to fetch {url}: {e}")
        
        # Try Jina as last resort
        try:
            jina_content = _fetch_via_jina(url, timeout)
            if jina_content:
                return jina_content
        except Exception:
            pass
        
        save_log("fetch_attempt", {
            "url": url,
            "method": "http",
            "status": "failed",
            "error": str(e),
            "content": "",
            "timestamp": time.time()
        })
        return ""
