"""
Content fetching functionality for the lookup command.

This module handles fetching and extracting content from various sources including
HTML pages, PDFs, and JavaScript-rendered sites.
"""

import logging
import requests
import time
import random
from litassist.logging import save_log
import click

# Track last AustLII request completion time for rate limiting
_last_austlii_completion = 0

# Markers that indicate Jina returned a bot-challenge / error interstitial
# instead of the requested page content. Matched case-insensitively.
_JINA_CHALLENGE_MARKERS = (
    "just a moment...",
    "performing security verification",
    "this website uses a security service to protect against malicious bots",
    "warning: target url returned error 403",
    "warning: target url returned error 404",
    "warning: target url returned error 5",
    "verification successful. waiting for",
    "checking your browser before accessing",
    "enable javascript and cookies to continue",
    "captcha",
    "please make sure you are authorized to access this page",
)

# Minimum bytes Jina must return for content to be treated as plausibly real.
# Cloudflare interstitials are typically 800-1500 chars; legitimate legal docs
# are routinely >10k. 2000 is a conservative line that catches the bad case
# without rejecting genuinely short legitimate content like one-paragraph
# definitions or empty-stub pages.
_JINA_MIN_USEFUL_CHARS = 2000


def _looks_like_challenge_page(text: str) -> str:
    """
    Return a short reason string if the given Jina response body looks like a
    bot-challenge / error interstitial, or "" if it looks like real content.
    """
    if not text:
        return "empty body"
    lowered = text.lower()
    for marker in _JINA_CHALLENGE_MARKERS:
        if marker in lowered:
            return f"challenge marker: '{marker}'"
    if len(text) < _JINA_MIN_USEFUL_CHARS:
        return f"too short ({len(text)} < {_JINA_MIN_USEFUL_CHARS} chars)"
    return ""


# Framework root-container markers that identify a JavaScript SPA shell.
# Matched case-insensitively against raw HTML before script removal.
_SPA_CONTAINER_MARKERS = (
    "<app-root",
    'id="root"',
    'id="app"',
    'id="__next"',
    'id="__nuxt"',
    "ng-version=",
)

# When a SPA shell is detected, extracted text shorter than this is treated
# as the empty body of an unrendered page.
_SPA_MIN_TEXT_LENGTH = 1000

# Raw HTML must be at least this large for the ratio heuristic to fire.
# Smaller pages (e.g. legitimate one-paragraph stubs) are exempt.
_SPA_MIN_HTML_LENGTH = 3000

# Maximum text-to-html ratio that still counts as a shell. Real legal pages
# routinely exceed 30%. Shells with bulky script tags fall well below 5%.
_SPA_TEXT_RATIO_THRESHOLD = 0.05


def _looks_like_spa_shell(raw_html: str, extracted_text: str) -> str:
    """
    Return a short reason string if the response looks like a JavaScript SPA
    shell (empty container + script bundle, no rendered content), or "" if it
    looks like a normal HTML page.

    Two signals, either of which flags the response:

    1. Known framework root-container marker is present in the raw HTML and
       the extracted text is short. This catches Angular/React/Vue/Next/Nuxt
       envelopes regardless of script bulk.
    2. Raw HTML is large but extracted text is a tiny fraction of it. Catches
       shells that use uncommon container names but still ship mostly script.
    """
    if not raw_html:
        return ""

    raw_lower = raw_html.lower()
    for marker in _SPA_CONTAINER_MARKERS:
        if marker in raw_lower and len(extracted_text) < _SPA_MIN_TEXT_LENGTH:
            return f"spa container '{marker}' with only {len(extracted_text)} chars of text"

    if len(raw_html) > _SPA_MIN_HTML_LENGTH:
        ratio = len(extracted_text) / len(raw_html)
        if ratio < _SPA_TEXT_RATIO_THRESHOLD:
            return (
                f"text/html ratio {ratio:.3f} below {_SPA_TEXT_RATIO_THRESHOLD} "
                f"({len(extracted_text)} text / {len(raw_html)} html)"
            )

    return ""


def _fetch_via_curl_cffi(url: str, timeout: int = 10):
    """
    Fetch URL via curl_cffi using Chrome TLS impersonation.

    Defeats TLS fingerprint detection (e.g. Cloudflare) that flags
    python-requests. Returns the curl_cffi response object (shape-compatible
    with requests.Response: .status_code, .content, .text, .headers) on
    success, or None on transport failure.

    Note: curl_cffi defeats TLS fingerprints only. JavaScript-rendered SPAs
    still need Jina rendering.
    """
    from curl_cffi import requests as curl_requests

    try:
        return curl_requests.get(url, timeout=timeout, impersonate="chrome136")
    except Exception as e:
        logging.warning(f"curl_cffi fetch failed for {url}: {e}")
        return None


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
        # Apply URL tricks for known sites to get full content
        original_url = url

        # Queensland legislation - use /whole to get full document
        if "legislation.qld.gov.au/view/html/inforce" in url and "/whole" not in url:
            url = url.rstrip("/") + "/whole"
            click.echo(f"  → Using full document URL: {url}")

        headers = {}
        # Request markdown format for better document structure preservation
        headers["x-respond-with"] = "markdown"

        # Use Jina API key if configured for higher rate limits
        from litassist.config import get_config

        config = get_config()
        if hasattr(config, "jina_api_key") and config.jina_api_key:
            headers["Authorization"] = f"Bearer {config.jina_api_key}"

        response = requests.get(
            f"https://r.jina.ai/{url}", headers=headers, timeout=timeout
        )

        if response.status_code == 200 and response.text.strip():
            challenge_reason = _looks_like_challenge_page(response.text)
            if challenge_reason:
                click.echo(
                    f"  [✗ Jina returned challenge/interstitial: {challenge_reason}]"
                )
                save_log(
                    "fetch_attempt",
                    {
                        "url": original_url,
                        "actual_url": url if url != original_url else None,
                        "method": "jina_reader",
                        "status": "failed",
                        "http_status": response.status_code,
                        "content_size": len(response.text),
                        "rejection_reason": challenge_reason,
                        "response_body": response.text,
                        "timestamp": time.time(),
                    },
                )
                return ""

            content = f"[Source: {original_url}]\n\n{response.text}"
            save_log(
                "fetch_attempt",
                {
                    "url": original_url,
                    "actual_url": url if url != original_url else None,
                    "method": "jina_reader",
                    "status": "success",
                    "content_size": len(response.text),
                    "content": content,
                    "timestamp": time.time(),
                },
            )
            return content
        else:
            # Show error or empty response
            if response.status_code != 200:
                # Try to get error message from response body
                error_msg = (
                    response.text.strip()
                    if response.text
                    else f"HTTP {response.status_code}"
                )
                click.echo(f"  [✗ Jina error: {error_msg}]")
            else:
                click.echo("  [✗ Jina returned empty content]")

            save_log(
                "fetch_attempt",
                {
                    "url": original_url,
                    "actual_url": url if url != original_url else None,
                    "method": "jina_reader",
                    "status": "failed",
                    "http_status": response.status_code,
                    "response_size": len(response.text),
                    "error_message": (
                        response.text if response.status_code != 200 else None
                    ),
                    "timestamp": time.time(),
                },
            )
            return ""
    except Exception as e:
        click.echo(f"  [✗ Jina error: {str(e)}]")
        logging.warning(f"Jina Reader failed for {original_url}: {e}")
        save_log(
            "fetch_attempt",
            {
                "url": original_url,
                "actual_url": url if url != original_url else None,
                "method": "jina_reader",
                "status": "failed",
                "error": str(e),
                "content": "",
                "timestamp": time.time(),
            },
        )
        return ""


def _fetch_from_austlii(url: str, timeout: int = 10) -> str:
    """
    Fetch content directly from AustLII with proper headers and rate limiting.

    Args:
        url: AustLII URL
        timeout: Request timeout

    Returns:
        Extracted text content or empty string if failed
    """
    # Rate limit - random 2-3 second delay after last request completed
    global _last_austlii_completion

    current_time = time.time()
    if _last_austlii_completion > 0:
        elapsed = current_time - _last_austlii_completion
        delay = random.uniform(2.0, 3.0)
        if elapsed < delay:
            wait_time = delay - elapsed
            click.echo(f"  → Rate limiting AustLII: waiting {wait_time:.1f}s")
            time.sleep(wait_time)

    try:
        response = _fetch_via_curl_cffi(url, timeout)

        # Update completion timestamp AFTER request finishes
        _last_austlii_completion = time.time()

        if response is None:
            click.echo("  ✗ AustLII fetch returned no response")
            save_log(
                "fetch_attempt",
                {
                    "url": url,
                    "method": "austlii_curl_cffi",
                    "status": "failed",
                    "error": "curl_cffi returned None",
                    "timestamp": time.time(),
                },
            )
            return ""

        if response.status_code == 200:
            # Check if content is actually a PDF
            if response.content.startswith(b'%PDF'):
                click.echo("  → AustLII returned PDF, extracting text...")
                return _extract_pdf_text(url, response.content)

            # Detect Cloudflare interstitial slipping through despite impersonation
            challenge_reason = _looks_like_challenge_page(response.text)
            if challenge_reason:
                click.echo(
                    f"  ✗ AustLII curl_cffi returned challenge page: {challenge_reason}"
                )
                save_log(
                    "fetch_attempt",
                    {
                        "url": url,
                        "method": "austlii_curl_cffi",
                        "status": "failed",
                        "http_status": response.status_code,
                        "content_size": len(response.text),
                        "rejection_reason": challenge_reason,
                        "timestamp": time.time(),
                    },
                )
                return ""

            # Extract text using BeautifulSoup
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            content = f"[Source: {url}]\n\n{text}"

            save_log(
                "fetch_attempt",
                {
                    "url": url,
                    "method": "austlii_curl_cffi",
                    "status": "success",
                    "content_size": len(text),
                    "content": content,
                    "timestamp": time.time(),
                },
            )

            click.echo(f"  ✓ AustLII curl_cffi fetch: {len(text)} chars")
            return content
        else:
            click.echo(f"  ✗ AustLII returned HTTP {response.status_code}")
            save_log(
                "fetch_attempt",
                {
                    "url": url,
                    "method": "austlii_curl_cffi",
                    "status": "failed",
                    "http_status": response.status_code,
                    "timestamp": time.time(),
                },
            )
            return ""

    except Exception as e:
        # Update completion timestamp even on error
        _last_austlii_completion = time.time()

        click.echo(f"  ✗ AustLII error: {str(e)}")
        logging.warning(f"AustLII curl_cffi fetch failed for {url}: {e}")
        save_log(
            "fetch_attempt",
            {
                "url": url,
                "method": "austlii_curl_cffi",
                "status": "failed",
                "error": str(e),
                "timestamp": time.time(),
            },
        )
        return ""


def _fetch_gov_legislation(url: str, timeout: int = 10) -> str:
    """
    Fetch legislation from government sites using direct HTTP.
    Handles table of contents pages by following document links.
    Only uses Jina as last resort if content is gibberish/wrong.

    Args:
        url: Government legislation URL
        timeout: Request timeout

    Returns:
        Extracted text content or empty string if failed
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Direct HTTP fetch
        response = requests.get(url, headers=headers, timeout=timeout)

        if response.status_code == 200:
            content = response.text

            # Check if this is a ToC page (legislation.gov.au pattern)
            if "legislation.gov.au" in url and "/latest/text" in url:
                # Look for document link
                import re

                doc_match = re.search(
                    r'href="([^"]*?/OEBPS/document_1/document_1\.html[^"]*)"', content
                )
                if doc_match:
                    doc_url = doc_match.group(1)
                    if not doc_url.startswith("http"):
                        # Make absolute URL
                        from urllib.parse import urljoin

                        doc_url = urljoin(url, doc_url)

                    click.echo(f"  → Following document link: {doc_url}")
                    # Fetch the actual document
                    doc_response = requests.get(
                        doc_url, headers=headers, timeout=timeout
                    )
                    if doc_response.status_code == 200:
                        content = doc_response.text

            # Extract text from HTML
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            # Validate we got sensible content (not gibberish)
            if len(text) < 100 or text.count("\n") < 5:
                # Too short or no structure, might be gibberish
                click.echo("  ✗ Direct fetch returned gibberish, falling back to Jina")
                return _fetch_via_jina(url, timeout)

            result = f"[Source: {url}]\n\n{text}"

            save_log(
                "fetch_attempt",
                {
                    "url": url,
                    "method": "gov_direct",
                    "status": "success",
                    "content_size": len(text),
                    "content": result,
                    "timestamp": time.time(),
                },
            )

            click.echo(f"  ✓ Direct government fetch: {len(text)} chars")
            return result

        else:
            # Non-200 status, try Jina
            click.echo(
                f"  ✗ Direct fetch failed (HTTP {response.status_code}), trying Jina"
            )
            return _fetch_via_jina(url, timeout)

    except Exception as e:
        click.echo(f"  ✗ Direct fetch error: {str(e)}, trying Jina")
        logging.warning(f"Government direct fetch failed for {url}: {e}")
        return _fetch_via_jina(url, timeout)


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

            # Extract text from every page; oversized prompts are handled
            # by the drop-largest truncation manager at the orchestration layer.
            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

            if text_parts:
                extracted_text = "\n".join(text_parts)

                # Check text/PDF size ratio to detect image-heavy documents
                pdf_size = len(pdf_bytes)
                text_size = len(extracted_text)
                ratio = text_size / pdf_size if pdf_size > 0 else 0

                # Check for FOI document markers in first 1000 chars
                first_chars = (
                    extracted_text[:1000]
                    if len(extracted_text) > 1000
                    else extracted_text
                )

                # Whitelist official FOI Act documents
                is_official_foi_act = "legislation.gov.au/C2004A02562" in url

                foi_markers = [
                    "Documents released",
                    "s. 47F",
                    "s.47F",
                    "released under the FOI Act",
                    "released under the Freedom of Information Act",
                    "FOI disclosure log",
                    "This document has been redacted",
                ]
                has_foi_markers = any(marker in first_chars for marker in foi_markers)

                # Reject if ratio too low (mostly images) or has FOI markers (unless it's the official FOI Act)
                if (
                    ratio < 0.0041
                ):  # Lowered from 0.01 to accept more government documents
                    click.echo(
                        f"  ✗ PDF rejected: text/PDF ratio {ratio:.4f} (likely images/redacted)"
                    )
                    save_log(
                        "pdf_rejected_ratio",
                        {
                            "url": url,
                            "pdf_size": pdf_size,
                            "text_size": text_size,
                            "ratio": ratio,
                            "reason": "Low text/PDF ratio indicates mostly images or redacted content",
                            "timestamp": time.time(),
                        },
                    )
                    return ""

                if has_foi_markers and not is_official_foi_act:
                    click.echo("  ✗ PDF rejected: FOI document markers detected")
                    save_log(
                        "pdf_rejected_foi",
                        {
                            "url": url,
                            "ratio": ratio,
                            "reason": "FOI document markers detected in content",
                            "timestamp": time.time(),
                        },
                    )
                    return ""

                # Add clear markers for LLM
                header = f"[PDF DOCUMENT EXTRACTED - {num_pages} pages]\n"
                header += f"[Source: {url}]\n"
                header += "=" * 80 + "\n"

                # No truncation - full PDF content is preserved

                logging.info(f"Successfully extracted text from PDF: {url}")
                pdf_content = (
                    header + extracted_text + "\n" + "=" * 80 + "\n[END OF PDF]"
                )
                save_log(
                    "fetch_attempt",
                    {
                        "url": url,
                        "method": "pdf",
                        "status": "success",
                        "pdf_pages": num_pages,
                        "extracted_size": len(extracted_text),
                        "final_size": len(pdf_content),
                        "pdf_size": pdf_size,
                        "text_pdf_ratio": ratio,
                        "content": pdf_content,
                        "timestamp": time.time(),
                    },
                )
                return pdf_content
            else:
                logging.info(f"PDF has no extractable text (may be scanned): {url}")
                save_log(
                    "fetch_attempt",
                    {
                        "url": url,
                        "method": "pdf",
                        "status": "skipped",
                        "reason": "PDF has no extractable text (may be scanned)",
                        "content": "",
                        "timestamp": time.time(),
                    },
                )
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
    Fetch content from URL with smart routing based on source type.
    - AustLII: Direct download with rate limiting
    - Government sites: Direct HTTP first, Jina as fallback
    - PDFs: Direct download
    - Local files: Direct file reading
    - Others: Jina Reader
    """
    click.echo(f"[FETCH] Checking: {url}")

    # Check if this is a local file path (not a URL)
    import os

    if not url.startswith(("http://", "https://", "ftp://")) and os.path.isfile(url):
        click.echo("  → Reading local file...")
        try:
            from litassist.utils.file_ops import read_document

            content = read_document(url)
            if content:
                result = f"[Source: {url}]\n\n{content}"
                click.echo(f"  ✓ Local file read: {len(content)} chars")
                return result
            else:
                click.echo("  ✗ Local file is empty")
                return ""
        except Exception as e:
            click.echo(f"  ✗ Local file read error: {str(e)}")
            return ""

    # Handle jade.io URLs - special case for ndfv.jade.io
    if "jade.io" in url.lower():
        # Special handling for ndfv.jade.io subdomain
        if "ndfv.jade.io" in url.lower():
            if "/download" not in url.lower():
                # Transform to download URL
                url = url.rstrip('/') + '/download'
                click.echo(f"  → Transforming to ndfv.jade.io download URL: {url}")
            # Use Jina for ndfv.jade.io URLs
            click.echo("  → Fetching ndfv.jade.io via Jina Reader...")
            return _fetch_via_jina(url, timeout)
        else:
            # Skip all other jade.io domains (main domain and other subdomains)
            logging.info(f"Skipping Jade.io URL (blocked from scrapers): {url}")
            save_log(
                "fetch_attempt",
                {
                    "url": url,
                    "method": "skipped",
                    "status": "blocked",
                    "reason": "Jade.io blocked from scrapers",
                    "content": "",
                    "timestamp": time.time(),
                },
            )
            return ""

    # AustLII - use direct download with rate limiting
    if "austlii.edu.au" in url.lower():
        click.echo("  → Detected AustLII URL, attempting direct download...")
        content = _fetch_from_austlii(url, timeout)
        if content:
            return content
        # Fall through to try Jina if direct download fails
        click.echo("  → AustLII direct failed, trying Jina...")
        return _fetch_via_jina(url, timeout)

    # Government legislation sites - use direct HTTP first
    if any(gov in url.lower() for gov in [".gov.au", "legislation."]):
        click.echo("  → Fetching government content...")
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            if response.status_code == 200:
                # Check if content is actually a PDF
                if response.content.startswith(b'%PDF'):
                    click.echo("  → Government site returned PDF, extracting text...")
                    return _extract_pdf_text(url, response.content)
                else:
                    # HTML legislation - parse with government fetcher
                    click.echo("  → Parsing government HTML content...")
                    return _fetch_gov_legislation(url, timeout)
            else:
                logging.warning(
                    f"Failed to fetch from {url}: HTTP {response.status_code}"
                )
                return ""
        except Exception as e:
            logging.warning(f"Failed to fetch from {url}: {e}")
            return ""

    # Everything else - check if PDF first, otherwise use Jina
    try:
        # Quick check for PDF
        head_response = requests.head(
            url,
            timeout=5,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            },
            allow_redirects=True,
        )

        content_type = head_response.headers.get("content-type", "").lower()
        is_pdf = "application/pdf" in content_type or url.lower().endswith(".pdf")

        if is_pdf:
            click.echo("  → Downloading PDF...")
            response = requests.get(
                url,
                timeout=timeout,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            if response.status_code == 200:
                # Verify it's actually a PDF
                if response.content.startswith(b'%PDF'):
                    return _extract_pdf_text(url, response.content)
                else:
                    # Not actually a PDF, try Jina instead
                    click.echo("  → Content not PDF despite headers, trying Jina...")
                    return _fetch_via_jina(url, timeout)
            else:
                logging.warning(
                    f"Failed to download PDF from {url}: HTTP {response.status_code}"
                )
                return ""
        else:
            click.echo("  → Fetching via Jina Reader...")
            return _fetch_via_jina(url, timeout)

    except Exception as e:
        logging.warning(f"Failed to fetch {url}: {e}")

        # Try Jina as fallback
        try:
            return _fetch_via_jina(url, timeout)
        except Exception as jina_error:
            logging.error(f"Jina fallback also failed for {url}: {jina_error}")

        save_log(
            "fetch_attempt",
            {
                "url": url,
                "method": "failed",
                "status": "failed",
                "error": str(e),
                "content": "",
                "timestamp": time.time(),
            },
        )
        return ""
