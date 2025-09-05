"""
Content fetching functionality for the lookup command.

This module handles fetching and extracting content from various sources including
HTML pages, PDFs, and JavaScript-rendered sites.
"""

import logging
import requests
import time
from litassist.logging_utils import save_log
import click


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
    Fetch content from URL - uses Jina for HTML, direct download for PDFs.
    """
    click.echo(f"[FETCH] Checking: {url}")
    
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
        # Check if it's a PDF with HEAD request
        head_response = requests.head(
            url,
            timeout=5,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            allow_redirects=True
        )
        
        content_type = head_response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in content_type or url.lower().endswith(".pdf")
        
        if is_pdf:
            click.echo("  → Downloading PDF...")
            # Download PDF directly
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                }
            )
            if response.status_code == 200:
                return _extract_pdf_text(url, response.content)
            else:
                logging.warning(f"Failed to download PDF from {url}: HTTP {response.status_code}")
                return ""
        else:
            click.echo("  → Fetching via Jina Reader...")
            # Use Jina for all HTML content
            return _fetch_via_jina(url, timeout)
            
    except Exception as e:
        logging.warning(f"Failed to fetch {url}: {e}")
        
        # Try Jina as fallback (in case HEAD failed but URL is valid)
        try:
            return _fetch_via_jina(url, timeout)
        except Exception:
            pass
        
        save_log("fetch_attempt", {
            "url": url,
            "method": "failed",
            "status": "failed",
            "error": str(e),
            "content": "",
            "timestamp": time.time()
        })
        return ""