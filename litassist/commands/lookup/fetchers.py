"""
Content fetching functionality for the lookup command.

This module handles fetching and extracting content from various sources including
HTML pages, PDFs, and JavaScript-rendered sites.
"""

import logging
import random
import time
from urllib.parse import urlsplit, urlunsplit

import click
import requests

from litassist.logging import save_log

# Track last AustLII request completion time for rate limiting
_last_austlii_completion = 0

_AUSTLII_CGI_REWRITE_REASON = "cgi wrapper -> direct content path"
_AUSTLII_PDF_HTML_REWRITE_REASON = ".pdf -> .html sibling"
_AUSTLII_RTF_HTML_REWRITE_REASON = ".rtf -> .html sibling"
_AUSTLII_RTF_INDEX_REWRITE_REASON = (
    ".rtf -> consolidated legislation index.html sibling"
)


class FetchedContent(str):
    """String content with fetch transport metadata for caller status messages."""

    fetch_method: str

    def __new__(cls, value: str, fetch_method: str) -> "FetchedContent":
        obj = str.__new__(cls, value)
        obj.fetch_method = fetch_method
        return obj


def _with_fetch_method(content: str, fetch_method: str) -> str:
    """Attach fetch method metadata while preserving normal str behaviour."""
    if not content:
        return content
    return FetchedContent(content, fetch_method)


def _is_austlii_host(hostname: str) -> bool:
    """Return True for austlii.edu.au and its mirror/subdomain hosts."""
    return hostname == "austlii.edu.au" or hostname.endswith(".austlii.edu.au")


def _normalise_austlii_url(url: str) -> tuple[str, list[str]]:
    """
    Rewrite AustLII URLs into forms that are fetchable by curl_cffi.

    Google CSE sometimes returns AustLII wrapper URLs such as
    /cgi-bin/viewdoc/.../index.html or /cgi-bin/viewdb/.../s122.html. Those
    wrappers can 404 even when the direct /au/... content path returns 200.

    AustLII also blocks Python clients on some binary document paths. HTML
    siblings at the same path are reachable and usually contain equivalent
    text or at least a useful article/document stub.
    """
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if not _is_austlii_host(host):
        return url, []

    path = parts.path
    reasons: list[str] = []

    for prefix in ("/cgi-bin/viewdoc/", "/cgi-bin/viewdb/"):
        if path.startswith(prefix):
            path = "/" + path[len(prefix):].lstrip("/")
            reasons.append(_AUSTLII_CGI_REWRITE_REASON)
            break

    lower_path = path.lower()
    if lower_path.endswith(".pdf"):
        path = path[:-4] + ".html"
        reasons.append(_AUSTLII_PDF_HTML_REWRITE_REASON)
    elif lower_path.endswith(".rtf"):
        if "/consol_act/" in lower_path or "/consol_reg/" in lower_path:
            path = path[:-4] + "/index.html"
            reasons.append(_AUSTLII_RTF_INDEX_REWRITE_REASON)
        else:
            path = path[:-4] + ".html"
            reasons.append(_AUSTLII_RTF_HTML_REWRITE_REASON)

    if not reasons:
        return url, []

    rewritten = urlunsplit(
        (parts.scheme, parts.netloc, path, parts.query, parts.fragment)
    )
    return rewritten, reasons


def _austlii_index_fallback_url(url: str, rewrite_reasons: list[str]) -> str:
    """
    Return the /index.html sibling for AustLII binary URLs first rewritten to
    flat .html, or "" when no targeted fallback should run.

    Some AustLII categories expose HTML siblings as /name/index.html rather
    than /name.html. Avoid broad retries for unrelated AustLII 404s: only
    binary URL rewrites (.pdf/.rtf -> .html) get this second chance.
    """
    if not any(
        reason in rewrite_reasons
        for reason in (
            _AUSTLII_PDF_HTML_REWRITE_REASON,
            _AUSTLII_RTF_HTML_REWRITE_REASON,
        )
    ):
        return ""

    parts = urlsplit(url)
    path = parts.path
    lower_path = path.lower()
    if not lower_path.endswith(".html") or lower_path.endswith("/index.html"):
        return ""

    index_path = path[:-5] + "/index.html"
    return urlunsplit(
        (parts.scheme, parts.netloc, index_path, parts.query, parts.fragment)
    )


# Markers that indicate the response is a bot-challenge / error interstitial
# rather than the requested page content. Matched case-insensitively. Used on
# both Jina-rendered responses and curl_cffi raw HTML responses.
#
# Audit performed 26/05/2026 against (a) a captured Cloudflare challenge body
# and (b) real fedcourt content with a reCAPTCHA-protected contact form:
# - "captcha" alone is OVER-BROAD - the literal substring appears in
#   legitimate pages embedding Google reCAPTCHA widgets (fedcourt.gov.au
#   practice-note pages, etc.). Replaced with canonical Cloudflare phrasings
#   below that do not appear in real content.
# - The remaining markers are full phrases unlikely to occur in legal prose.
# - "just a moment..." and "enable javascript and cookies to continue" fire
#   reliably on the captured Cloudflare body and were not observed in real
#   fedcourt content.
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
    # Replaced bare "captcha" with phrase-level markers that distinguish
    # Cloudflare interstitials from legitimate reCAPTCHA-protected forms.
    "please complete the captcha",
    "captcha challenge",
    "please make sure you are authorized to access this page",
)

# Minimum bytes a Jina-rendered response must return for content to be
# treated as plausibly real. Jina returns markdown extracted from the
# upstream HTML, so a Cloudflare interstitial passed through Jina collapses
# to ~800-1500 chars of "Just a moment..." text. The same number does NOT
# apply to raw curl_cffi HTML: real Cloudflare interstitial HTML is ~31 KB,
# and legitimate short raw HTML pages are not necessarily junk. The size
# floor is therefore conditional on the caller (see is_jina_markdown).
_JINA_MIN_USEFUL_CHARS = 2000


def _looks_like_challenge_page(text: str, is_jina_markdown: bool = True) -> str:
    """
    Return a short reason string if the given response body looks like a
    bot-challenge / error interstitial, or "" if it looks like real content.

    The size floor (`_JINA_MIN_USEFUL_CHARS`) applies only to Jina-rendered
    markdown responses, where Cloudflare interstitials shrink to ~1 KB and
    a short body is itself a strong signal of trouble. For raw curl HTML
    callers (`is_jina_markdown=False`), only marker-based detection runs;
    short legitimate pages would otherwise be discarded by the floor even
    though they carry usable text after BS4 extraction.
    """
    if not text:
        return "empty body"
    lowered = text.lower()
    for marker in _JINA_CHALLENGE_MARKERS:
        if marker in lowered:
            return f"challenge marker: '{marker}'"
    if is_jina_markdown and len(text) < _JINA_MIN_USEFUL_CHARS:
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
    success, or None on transport failure or missing dependency.

    Note: curl_cffi defeats TLS fingerprints only. JavaScript-rendered SPAs
    still need Jina rendering.
    """
    try:
        from curl_cffi import requests as curl_requests
    except ImportError as e:
        # curl_cffi is declared in requirements.txt but a user may have an
        # existing install (e.g. pipx) that has not picked up the new dep.
        # Degrade gracefully to the Jina fallback path instead of crashing
        # the lookup command.
        logging.warning(
            f"curl_cffi not available ({e}); skipping primary transport. "
            "Install dependencies: pip install -r requirements.txt"
        )
        return None

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
    original_url = url
    try:
        # Apply URL tricks for known sites to get full content
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
            return _with_fetch_method(content, "Jina Reader")
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
                    # Use formatter-recognised field names so audit log
                    # surfaces the failure detail (rather than silently
                    # dropping response_size / error_message).
                    "content_size": len(response.text),
                    "error": (
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


def _rate_limit_austlii() -> None:
    """
    Enforce a 2-3 second random delay between AustLII requests.

    Even with curl_cffi's TLS impersonation defeating Cloudflare's fingerprint
    check, aggressive parallel requests against austlii.edu.au still risk
    re-triggering rate-based protections. The delay is measured from the
    completion of the previous AustLII request (not its start), so a slow
    fetch followed by a fast one waits the full window.
    """
    global _last_austlii_completion
    if _last_austlii_completion <= 0:
        return
    elapsed = time.time() - _last_austlii_completion
    delay = random.uniform(2.0, 3.0)
    if elapsed < delay:
        wait_time = delay - elapsed
        click.echo(f"  → Rate limiting AustLII: waiting {wait_time:.1f}s")
        time.sleep(wait_time)


def _response_audit_fields(response) -> dict:
    """
    Extract HTTP status and Cloudflare diagnostic headers from a response
    for inclusion in save_log audit payloads. Returning these fields makes
    retroactive forensics on the markdown audit log possible (e.g. answering
    "was this a real Cloudflare challenge or a detector false positive").

    Returns a dict with http_status (always) plus cf_mitigated and cf_ray
    when those headers are present on the response.
    """
    fields: dict = {"http_status": response.status_code}
    cf_mit = response.headers.get("cf-mitigated", "")
    if cf_mit:
        fields["cf_mitigated"] = cf_mit
    cf_ray = response.headers.get("cf-ray", "")
    if cf_ray:
        fields["cf_ray"] = cf_ray
    return fields


def _extract_text_from_html(html: str) -> str:
    """
    Strip scripts/styles/meta/link/noscript and return cleaned text from HTML.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "meta", "link", "noscript"]):
        tag.decompose()

    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    return "\n".join(chunk for chunk in chunks if chunk)


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
                return _with_fetch_method(pdf_content, "pdfplumber")
            else:
                logging.info(f"PDF has no extractable text (may be scanned): {url}")
                click.echo(
                    "  ✗ PDF skipped: no extractable text "
                    "(likely scanned/image-only)"
                )
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
        return _with_fetch_method(
            f"[PDF DOCUMENT at {url}]\n"
            "[Note: PDF text extraction unavailable - pdfplumber not installed]\n",
            "pdfplumber unavailable",
        )
    except Exception as e:
        logging.warning(f"Failed to extract text from PDF {url}: {e}")
        return _with_fetch_method(
            f"[PDF DOCUMENT at {url}]\n"
            f"[Note: PDF extraction failed - {str(e)[:100]}]\n",
            "pdfplumber error",
        )


def _fetch_url_content(url: str, timeout: int = 10) -> str:
    """
    Fetch content from URL via a generic chain. All HTTP sources go through
    curl_cffi first (defeats TLS fingerprinting). Responses that look like
    challenge pages, SPA shells, or gibberish fall through to Jina rendering.

    Order:
      1.  Local file path        -> read_document
      2.  jade.io main domain    -> skip (cookie-gated)
      3.  ndfv.jade.io           -> Jina with /download URL rewrite
      3b. AustLII URL normalise  -> direct path + .pdf/.rtf to .html sibling
      4.  AustLII rate-limit     -> 2-3s random delay
      5.  curl_cffi GET
      5b. AustLII sibling retry  -> flat .html 404 tries /index.html
      6.  PDF magic bytes        -> _extract_pdf_text
      6b. RTF magic bytes        -> extract_rtf_text
      6c. Content-Type guard     -> non-text payload falls back to Jina
      6d. legislation.gov.au ToC -> follow OEBPS document link
      7.  BS4 text extract
      8.  Unusable response      -> Jina fallback
      9.  Otherwise              -> return cleaned text
    """
    global _last_austlii_completion
    click.echo(f"[FETCH] Checking: {url}")

    import os

    # 1. Local file
    if not url.startswith(("http://", "https://", "ftp://")) and os.path.isfile(url):
        click.echo("  → Reading local file...")
        try:
            from litassist.utils.file_ops import read_document

            content = read_document(url)
            if content:
                click.echo(f"  ✓ Local file read: {len(content)} chars")
                return _with_fetch_method(f"[Source: {url}]\n\n{content}", "local file")
            click.echo("  ✗ Local file is empty")
            return ""
        except Exception as e:
            click.echo(f"  ✗ Local file read error: {str(e)}")
            return ""

    lower_url = url.lower()

    # 2/3. jade.io special handling
    if "jade.io" in lower_url:
        if "ndfv.jade.io" in lower_url:
            if "/download" not in lower_url:
                url = url.rstrip("/") + "/download"
                click.echo(f"  → Transforming to ndfv.jade.io download URL: {url}")
            click.echo("  → Fetching ndfv.jade.io via Jina Reader...")
            return _fetch_via_jina(url, timeout)
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

    # 3b. AustLII URL normalisation. URL parsing keeps query strings and
    # fragments intact while rewriting only the path.
    normalised_url, austlii_rewrite_reasons = _normalise_austlii_url(url)
    if austlii_rewrite_reasons:
        click.echo(
            "  → Normalising AustLII URL "
            f"({'; '.join(austlii_rewrite_reasons)}): {normalised_url}"
        )
        save_log(
            "fetch_attempt",
            {
                "url": url,
                "method": "austlii_url_normalise",
                "status": "rewrite",
                "rewrite_target": normalised_url,
                "reason": "; ".join(austlii_rewrite_reasons),
                "timestamp": time.time(),
            },
        )
        url = normalised_url
        lower_url = url.lower()

    # 4. AustLII rate limit
    is_austlii = "austlii.edu.au" in lower_url
    if is_austlii:
        _rate_limit_austlii()

    # 5. curl_cffi GET
    try:
        response = _fetch_via_curl_cffi(url, timeout)
    finally:
        if is_austlii:
            _last_austlii_completion = time.time()

    if response is None:
        click.echo("  → curl_cffi returned no response, falling back to Jina")
        return _fetch_via_jina(url, timeout)

    if response.status_code != 200:
        index_fallback_url = ""
        if response.status_code == 404:
            index_fallback_url = _austlii_index_fallback_url(
                url, austlii_rewrite_reasons
            )

        if index_fallback_url:
            click.echo(
                "  → AustLII flat HTML sibling returned 404; "
                f"trying index sibling: {index_fallback_url}"
            )
            save_log(
                "fetch_attempt",
                {
                    "url": url,
                    "method": "curl_cffi",
                    "status": "failed",
                    "rejection_reason": "flat HTML sibling returned 404; retrying index.html sibling",
                    "timestamp": time.time(),
                    **_response_audit_fields(response),
                },
            )
            save_log(
                "fetch_attempt",
                {
                    "url": url,
                    "method": "austlii_url_normalise",
                    "status": "rewrite",
                    "rewrite_target": index_fallback_url,
                    "reason": "flat HTML sibling 404 -> index.html sibling",
                    "timestamp": time.time(),
                },
            )
            if is_austlii:
                _rate_limit_austlii()

            try:
                retry_response = _fetch_via_curl_cffi(index_fallback_url, timeout)
            finally:
                if is_austlii:
                    _last_austlii_completion = time.time()

            if retry_response is not None and retry_response.status_code == 200:
                url = index_fallback_url
                lower_url = url.lower()
                response = retry_response
            else:
                if retry_response is None:
                    click.echo(
                        "  ✗ AustLII index sibling retry returned no response, "
                        "falling back to Jina"
                    )
                    save_log(
                        "fetch_attempt",
                        {
                            "url": index_fallback_url,
                            "method": "curl_cffi",
                            "status": "failed",
                            "rejection_reason": "index.html sibling retry returned no response",
                            "timestamp": time.time(),
                        },
                    )
                    return _fetch_via_jina(index_fallback_url, timeout)
                if retry_response.status_code == 404:
                    click.echo(
                        "  ✗ AustLII index sibling also returned 404; "
                        "skipping Jina"
                    )
                    save_log(
                        "fetch_attempt",
                        {
                            "url": index_fallback_url,
                            "method": "curl_cffi",
                            "status": "failed",
                            "rejection_reason": "confirmed 404 after flat and index HTML siblings",
                            "timestamp": time.time(),
                            **_response_audit_fields(retry_response),
                        },
                    )
                    return ""
                else:
                    click.echo(
                        "  ✗ AustLII index sibling retry returned HTTP "
                        f"{retry_response.status_code}, falling back to Jina"
                    )
                    save_log(
                        "fetch_attempt",
                        {
                            "url": index_fallback_url,
                            "method": "curl_cffi",
                            "status": "failed",
                            "rejection_reason": "index.html sibling retry failed",
                            "timestamp": time.time(),
                            **_response_audit_fields(retry_response),
                        },
                    )
                    return _fetch_via_jina(index_fallback_url, timeout)
        else:
            if response.status_code == 404:
                click.echo("  ✗ curl_cffi returned HTTP 404; skipping Jina")
                save_log(
                    "fetch_attempt",
                    {
                        "url": url,
                        "method": "curl_cffi",
                        "status": "failed",
                        "rejection_reason": "HTTP 404 not found; Jina skipped",
                        "timestamp": time.time(),
                        **_response_audit_fields(response),
                    },
                )
                return ""

            click.echo(
                f"  ✗ curl_cffi returned HTTP {response.status_code}, falling back to Jina"
            )
            save_log(
                "fetch_attempt",
                {
                    "url": url,
                    "method": "curl_cffi",
                    "status": "failed",
                    "timestamp": time.time(),
                    **_response_audit_fields(response),
                },
            )
            return _fetch_via_jina(url, timeout)

    # 6. PDF magic bytes (binary check first - response.text on a PDF is junk)
    if response.content.startswith(b"%PDF"):
        click.echo("  → curl_cffi returned PDF, extracting text...")
        return _extract_pdf_text(url, response.content)

    # 6b. RTF magic bytes (AustLII serves some cases as .rtf)
    from litassist.utils.rtf import looks_like_rtf, extract_rtf_text

    if looks_like_rtf(response.content):
        click.echo("  → curl_cffi returned RTF, extracting text...")
        rtf_content = extract_rtf_text(url, response.content)
        rtf_method = (
            "striprtf"
            if rtf_content.startswith("[RTF DOCUMENT EXTRACTED")
            else "RTF extraction unavailable"
        )
        return _with_fetch_method(rtf_content, rtf_method)

    # 6c. Content-Type guard. If curl_cffi returned a non-HTML payload (e.g.
    # a script bundle from a misconfigured redirect, raw JSON, or a binary
    # blob), treating it as HTML and running BS4 on it would yield long
    # garbage text that the gibberish heuristic (text < 100 chars only)
    # would not catch. Reject non-text content types here; route to Jina.
    _ct = (response.headers.get("content-type", "") or "").lower().split(";")[0].strip()
    _acceptable_types = ("text/html", "text/plain", "text/xml", "application/xhtml+xml", "application/xml", "")
    if _ct and _ct not in _acceptable_types:
        click.echo(
            f"  ✗ curl_cffi returned unexpected content-type '{_ct}', falling back to Jina"
        )
        save_log(
            "fetch_attempt",
            {
                "url": url,
                "method": "curl_cffi",
                "status": "failed",
                "rejection_reason": f"unexpected content-type: {_ct}",
                "timestamp": time.time(),
                **_response_audit_fields(response),
            },
        )
        return _fetch_via_jina(url, timeout)

    # 6d. legislation.gov.au /latest/text returns a ToC page that links to
    # the actual document at OEBPS/document_1/document_1.html. Follow the
    # link via curl_cffi and replace the response with the real document.
    #
    # WHY parsed hostname (not substring match): a URL like
    # https://evil.example.com/article?ref=legislation.gov.au/latest/text
    # would substring-match "legislation.gov.au" and "/latest/text", causing
    # the chain to follow any OEBPS-shaped href the attacker's page emits.
    # urlsplit(url).hostname returns just "evil.example.com" - the hostname
    # check rejects the attacker URL before any link extraction happens.
    # Do not "simplify" back to substring matching.
    _legis_parts = urlsplit(url)
    _legis_host = (_legis_parts.hostname or "").lower()
    if (
        (_legis_host == "legislation.gov.au" or _legis_host.endswith(".legislation.gov.au"))
        and "/latest/text" in _legis_parts.path.lower()
    ):
        import re
        from urllib.parse import urljoin

        # Accept both single- and double-quoted href attributes since
        # legislation.gov.au markup varies; (?P<q>["']) captures the
        # opening quote and the back-reference enforces the matching close.
        doc_match = re.search(
            r"href=(?P<q>[\"'])(?P<u>[^\"']*?/OEBPS/document_1/document_1\.html[^\"']*)(?P=q)",
            response.text,
        )
        if doc_match:
            doc_url = doc_match.group("u")
            if not doc_url.startswith("http"):
                doc_url = urljoin(url, doc_url)
            click.echo(f"  → Following legislation.gov.au document link: {doc_url}")
            doc_response = _fetch_via_curl_cffi(doc_url, timeout)
            if doc_response is not None and doc_response.status_code == 200:
                url = doc_url
                response = doc_response
            else:
                # doc_url fetch failed - falling through to parse the original
                # ToC page would silently surface the ToC text as the
                # 'document', which the loosened gibberish heuristic
                # (text < 100 chars) would not catch. Route to Jina instead.
                click.echo(
                    "  ✗ legislation.gov.au document link fetch failed, "
                    "falling back to Jina (avoiding ToC false positive)"
                )
                save_log(
                    "fetch_attempt",
                    {
                        "url": doc_url,
                        "method": "curl_cffi",
                        "status": "failed",
                        "rejection_reason": "legislation.gov.au doc link fetch failed; ToC would be a false positive",
                        "timestamp": time.time(),
                        **(_response_audit_fields(doc_response) if doc_response is not None else {}),
                    },
                )
                return _fetch_via_jina(doc_url, timeout)

    raw_html = response.text

    # 7. BS4 text extract
    try:
        text = _extract_text_from_html(raw_html)
    except Exception as e:
        click.echo(f"  ✗ HTML parsing failed: {e}, falling back to Jina")
        return _fetch_via_jina(url, timeout)

    # 8. Unusable response detection.
    # raw_html is curl_cffi's untransformed HTML body - the size floor in
    # _looks_like_challenge_page is calibrated for Jina markdown responses
    # only, so skip it here via is_jina_markdown=False. Marker-based detection
    # still runs.
    challenge_reason = _looks_like_challenge_page(raw_html, is_jina_markdown=False)
    if challenge_reason:
        click.echo(
            f"  ✗ curl_cffi returned challenge page: {challenge_reason}, falling back to Jina"
        )
        save_log(
            "fetch_attempt",
            {
                "url": url,
                "method": "curl_cffi",
                "status": "failed",
                "content_size": len(raw_html),
                "rejection_reason": challenge_reason,
                "timestamp": time.time(),
                **_response_audit_fields(response),
            },
        )
        return _fetch_via_jina(url, timeout)

    spa_reason = _looks_like_spa_shell(raw_html, text)
    if spa_reason:
        click.echo(
            f"  ✗ curl_cffi returned SPA shell: {spa_reason}, falling back to Jina"
        )
        save_log(
            "fetch_attempt",
            {
                "url": url,
                "method": "curl_cffi",
                "status": "failed",
                "content_size": len(raw_html),
                "rejection_reason": spa_reason,
                "timestamp": time.time(),
                **_response_audit_fields(response),
            },
        )
        return _fetch_via_jina(url, timeout)

    # Gibberish heuristic: only reject if text is so short it cannot carry
    # meaningful content. The earlier newline-count check (text.count("\n") < 5)
    # was removed 26/05/2026 after live testing on Nuxt-pre-rendered pages
    # (e.g. triplezero.vic.gov.au): those pages use Unicode word-joiner
    # separators (U+2060) instead of newlines, so the count rejected real
    # content. Empirical comparison vs Jina showed 78% vocabulary overlap
    # and all substantive legal phrases present - the content was correct,
    # only the formatting was poor.
    if len(text) < 100:
        click.echo("  ✗ Extracted text too short, falling back to Jina")
        save_log(
            "fetch_attempt",
            {
                "url": url,
                "method": "curl_cffi",
                "status": "failed",
                "content_size": len(text),
                "rejection_reason": "gibberish (text < 100 chars)",
                "timestamp": time.time(),
                **_response_audit_fields(response),
            },
        )
        return _fetch_via_jina(url, timeout)

    # 9. Success
    content = f"[Source: {url}]\n\n{text}"
    save_log(
        "fetch_attempt",
        {
            "url": url,
            "method": "curl_cffi",
            "status": "success",
            "content_size": len(text),
            "content": content,
            "timestamp": time.time(),
            **_response_audit_fields(response),
        },
    )
    click.echo(f"  ✓ curl_cffi fetch: {len(text)} chars")
    return _with_fetch_method(content, "curl_cffi")
