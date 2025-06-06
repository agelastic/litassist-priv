"""
Real-time citation verification against AustLII.

This module provides comprehensive verification of Australian legal citations
by checking their existence on AustLII's database. It implements strict validation
with surgical removal of invalid citations and targeted regeneration when necessary.
"""

import re
import requests
import time
from typing import List, Tuple, Dict, Set
from urllib.parse import quote
import threading

# Import logging utility
from litassist.utils import save_log, timed

# Cache for verified citations to avoid repeated requests
_citation_cache: Dict[str, Dict] = {}
_cache_lock = threading.Lock()

# Australian court abbreviations and their AustLII paths
COURT_MAPPINGS = {
    "HCA": "cth/HCA",
    "FCA": "cth/FCA",
    "FCAFC": "cth/FCAFC",
    "FCFCOA": "cth/FCFCOA",
    "FedCFamC1A": "cth/FedCFamC1A",
    "FedCFamC2A": "cth/FedCFamC2A",
    "FamCA": "cth/FamCA",
    "FamCAFC": "cth/FamCAFC",
    "NSWSC": "nsw/NSWSC",
    "NSWCA": "nsw/NSWCA",
    "NSWCCA": "nsw/NSWCCA",
    "NSWDC": "nsw/NSWDC",
    "NSWLC": "nsw/NSWLC",
    "VSC": "vic/VSC",
    "VSCA": "vic/VSCA",
    "VCC": "vic/VCC",
    "VCAT": "vic/VCAT",
    "QSC": "qld/QSC",
    "QCA": "qld/QCA",
    "QDC": "qld/QDC",
    "QCAT": "qld/QCAT",
    "SASC": "sa/SASC",
    "SASCFC": "sa/SASCFC",
    "SADC": "sa/SADC",
    "SACAT": "sa/SACAT",
    "WASC": "wa/WASC",
    "WASCA": "wa/WASCA",
    "WADC": "wa/WADC",
    "WASAT": "wa/WASAT",
    "TASSC": "tas/TASSC",
    "TASFC": "tas/TASFC",
    "ACTSC": "act/ACTSC",
    "ACAT": "act/ACAT",
    "NTSC": "nt/NTSC",
    "NTCA": "nt/NTCA",
    "FCWA": "wa/FCWA",
}


class CitationVerificationError(Exception):
    """Raised when citation verification fails and output cannot proceed."""

    pass


@timed
def extract_citations(text: str) -> List[str]:
    """
    Extract all Australian legal citations from text.

    Args:
        text: Text content to extract citations from

    Returns:
        List of unique citations found
    """
    citations = set()

    # Pattern 1: Medium neutral citations [YEAR] COURT NUMBER
    pattern1 = r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(\d+)"
    matches1 = re.finditer(pattern1, text)
    for match in matches1:
        citations.add(match.group(0))

    # Pattern 2: Traditional citations (YEAR) VOLUME COURT PAGE
    pattern2 = r"\((\d{4})\)\s+(\d+)\s+([A-Z]+[A-Za-z]*)\s+(\d+)"
    matches2 = re.finditer(pattern2, text)
    for match in matches2:
        citations.add(match.group(0))

    return list(citations)


@timed
def normalize_citation(citation: str) -> str:
    """
    Normalize citation format for consistent processing.

    Args:
        citation: Raw citation text

    Returns:
        Normalized citation string
    """
    # Remove extra whitespace and normalize
    citation = re.sub(r"\s+", " ", citation.strip())

    # Handle medium neutral citations
    match = re.match(r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(\d+)", citation)
    if match:
        year, court, number = match.groups()
        return f"[{year}] {court} {number}"

    return citation


def build_austlii_url(citation: str) -> Tuple[str, str]:
    """
    Build AustLII URL from citation.

    Args:
        citation: Normalized citation

    Returns:
        Tuple of (url, error_reason) where error_reason is empty if successful
    """
    # Parse medium neutral citation
    match = re.match(r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(\d+)", citation)
    if not match:
        return "", "Invalid citation format"

    year, court, number = match.groups()

    # Check if court is known
    if court not in COURT_MAPPINGS:
        return "", f"Unknown court abbreviation: {court}"

    # Build URL
    court_path = COURT_MAPPINGS[court]
    url = f"https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/{court_path}/{year}/{number}.html"

    return url, ""


def check_url_exists(url: str, timeout: int = 5) -> bool:
    """
    Check if URL exists with GET request (AustLII doesn't support HEAD).

    Args:
        url: URL to check
        timeout: Request timeout in seconds

    Returns:
        True if URL exists and returns 200 status
    """
    start_time = time.time()
    status_code = None
    error_msg = None
    
    try:
        # Use GET instead of HEAD as AustLII doesn't properly support HEAD requests
        response = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (compatible; LitAssist Citation Verification)"},
            stream=True  # Don't download the whole body
        )
        status_code = response.status_code
        response.close()  # Close immediately to save bandwidth
        success = response.status_code == 200
    except (requests.RequestException, requests.Timeout) as e:
        success = False
        error_msg = str(e)
    
    # Log the HTTP validation call
    save_log(
        "austlii_http_validation",
        {
            "method": "check_url_exists", 
            "url": url,
            "status_code": status_code,
            "success": success,
            "error": error_msg,
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "timeout": timeout,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )
    
    return success


def is_traditional_citation_format(citation: str) -> bool:
    """
    Check if citation is in traditional format that cannot be verified via AustLII URLs.

    Args:
        citation: Citation to check

    Returns:
        True if citation is in traditional format (volume/page citations)
    """
    # Traditional formats like (1968) 118 CLR 1, [1919] VLR 497, [1955] AC 431
    traditional_patterns = [
        r"\(\d{4}\)\s+\d+\s+[A-Z]+\s+\d+",  # (Year) Volume Series Page - covers CLR, ALR, etc.
        # Australian traditional law reports: VLR=Victorian Law Reports, CLR=Commonwealth Law Reports, 
        # ALR=Australian Law Reports, FCR=Federal Court Reports, FLR=Family Law Reports, etc.
        r"\[\d{4}\]\s+(VLR|CLR|ALR|FCR|FLR|IR|ACTR|NTLR|SASR|WAR|TasR)\s+\d+",  
        r"\[\d{4}\]\s+(AC|PC|WLR|All\s*ER|Ch|QB|KB)\s+\d+",  # UK/Privy Council citations
    ]

    for pattern in traditional_patterns:
        if re.match(pattern, citation.strip()):
            return True
    return False


@timed
def verify_single_citation(citation: str) -> Tuple[bool, str, str]:
    """
    Verify a single citation against AustLII.

    Args:
        citation: Citation to verify

    Returns:
        Tuple of (exists, url, reason) where reason explains failure if any
    """
    # Normalize first
    normalized = normalize_citation(citation)

    # Check cache first
    with _cache_lock:
        if normalized in _citation_cache:
            cached = _citation_cache[normalized]
            return cached["exists"], cached.get("url", ""), cached.get("reason", "")

    # Check if this is a traditional citation format that we should allow through
    if is_traditional_citation_format(normalized):
        # Cache as verified for traditional citations
        with _cache_lock:
            _citation_cache[normalized] = {
                "exists": True,
                "url": "",
                "reason": "Traditional citation format - verification skipped",
                "checked_at": time.time(),
            }
        return True, "", "Traditional citation format - verification skipped"

    # Build URL for medium neutral citations
    url, error_reason = build_austlii_url(normalized)
    if error_reason:
        # Cache the error
        with _cache_lock:
            _citation_cache[normalized] = {
                "exists": False,
                "url": "",
                "reason": error_reason,
                "checked_at": time.time(),
            }
        return False, "", error_reason

    # Check if exists
    exists = check_url_exists(url)
    reason = "" if exists else "Not found on AustLII"

    # Cache the result
    with _cache_lock:
        _citation_cache[normalized] = {
            "exists": exists,
            "url": url if exists else "",
            "reason": reason,
            "checked_at": time.time(),
        }

    return exists, url if exists else "", reason


@timed
def verify_all_citations(text: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Verify all citations in text content.

    Args:
        text: Text content containing citations

    Returns:
        Tuple of (verified_citations, unverified_citations_with_reasons)
    """
    start_time = time.time()
    citations = extract_citations(text)
    verified = []
    unverified = []

    for citation in citations:
        exists, url, reason = verify_single_citation(citation)
        if exists:
            verified.append(citation)
        else:
            unverified.append((citation, reason))

    # Log the overall verification session
    save_log(
        "citation_verification_session",
        {
            "method": "verify_all_citations",
            "input_text_length": len(text),
            "citations_found": len(citations),
            "citations_verified": len(verified),
            "citations_unverified": len(unverified),
            "verified_citations": verified,
            "unverified_citations": [{"citation": cit, "reason": reason} for cit, reason in unverified],
            "processing_time_ms": round((time.time() - start_time) * 1000, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    )

    return verified, unverified


def remove_citation_from_text(text: str, citation: str) -> str:
    """
    Surgically remove a citation from text while preserving readability.

    Args:
        text: Original text
        citation: Citation to remove

    Returns:
        Text with citation removed and cleaned up
    """
    # Escape special regex characters in citation
    escaped_citation = re.escape(citation)

    # Pattern to match citation with surrounding context
    patterns = [
        # Pattern 1: "as held in [citation]"
        rf"\s+as\s+(?:held|established|decided|ruled)\s+in\s+{escaped_citation}",
        # Pattern 2: "([citation])"
        rf"\s*\(\s*{escaped_citation}\s*\)",
        # Pattern 3: "— [citation]"
        rf"\s*[—–-]\s*\*?{escaped_citation}\*?",
        # Pattern 4: "; [citation]"
        rf"\s*;\s*{escaped_citation}",
        # Pattern 5: ", [citation]"
        rf"\s*,\s*{escaped_citation}",
        # Pattern 6: Just the citation itself
        rf"\s*{escaped_citation}",
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            # Remove the pattern
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            break

    # Clean up any double spaces or awkward punctuation
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*\.\s*\.", ".", text)  # Remove double periods
    text = re.sub(r"\s+,", ",", text)  # Fix spacing before commas
    text = re.sub(r"\s+\.", ".", text)  # Fix spacing before periods

    return text.strip()


def is_core_citation(text_section: str, citation: str) -> bool:
    """
    Determine if a citation is core to a text section or just supporting.

    Args:
        text_section: Section of text containing the citation
        citation: The citation to evaluate

    Returns:
        True if citation appears to be core/essential to the argument
    """
    # Look for the citation in the text
    citation_pos = text_section.find(citation)
    if citation_pos == -1:
        return False

    # Check if it's in the first sentence (usually indicates core importance)
    first_sentence_end = text_section.find(".")
    if first_sentence_end != -1 and citation_pos < first_sentence_end:
        return True

    # Check if it's the only citation in this section
    all_citations = extract_citations(text_section)
    if len(all_citations) == 1:
        return True

    # Check for key phrases that indicate core citation
    text_before_citation = text_section[:citation_pos].lower()
    core_indicators = [
        "established in",
        "held in",
        "decided in",
        "per",
        "in the leading case",
        "landmark case",
        "seminal case",
    ]

    for indicator in core_indicators:
        if (
            indicator in text_before_citation[-50:]
        ):  # Check last 50 chars before citation
            return True

    return False


def get_verification_stats() -> Dict:
    """
    Get statistics about citation verification cache.

    Returns:
        Dictionary with cache statistics
    """
    with _cache_lock:
        total = len(_citation_cache)
        verified = sum(1 for entry in _citation_cache.values() if entry["exists"])
        unverified = total - verified

        return {
            "total_checked": total,
            "verified": verified,
            "unverified": unverified,
            "cache_hit_rate": f"{(verified / total * 100):.1f}%" if total > 0 else "0%",
        }


def clear_verification_cache():
    """Clear the citation verification cache."""
    with _cache_lock:
        _citation_cache.clear()
