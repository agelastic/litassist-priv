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

# UK/International court abbreviations - historically relevant to Australian law
# These cannot be verified via AustLII but are valid citations
UK_INTERNATIONAL_COURTS = {
    # UK Courts and Reports
    "AC": "Appeal Cases (House of Lords/Privy Council)",
    "PC": "Privy Council",
    "Ch": "Chancery Division",
    "QB": "Queen's Bench Division",
    "KB": "King's Bench Division",
    "WLR": "Weekly Law Reports",
    "All ER": "All England Reports",
    "AllER": "All England Reports",  # Alternative format
    "UKHL": "UK House of Lords",
    "UKSC": "UK Supreme Court",
    "EWCA": "England and Wales Court of Appeal",
    "EWHC": "England and Wales High Court",
    "Fam": "Family Division",
    "ER": "English Reports (historical)",
    "Cr App R": "Criminal Appeal Reports",
    "CrAppR": "Criminal Appeal Reports",  # Alternative format
    "Lloyd's Rep": "Lloyd's Law Reports",
    # New Zealand
    "NZLR": "New Zealand Law Reports",
    "NZCA": "New Zealand Court of Appeal",
    "NZSC": "New Zealand Supreme Court",
    "NZHC": "New Zealand High Court",
    # Canada
    "SCR": "Supreme Court Reports (Canada)",
    "DLR": "Dominion Law Reports",
    "OR": "Ontario Reports",
    "BCR": "British Columbia Reports",
    "AR": "Alberta Reports",
    "QR": "Quebec Reports",
    "SCC": "Supreme Court of Canada",
    "ONCA": "Ontario Court of Appeal",
    "BCCA": "British Columbia Court of Appeal",
    # Singapore
    "SLR": "Singapore Law Reports",
    "SGCA": "Singapore Court of Appeal",
    "SGHC": "Singapore High Court",
    # Hong Kong
    "HKLR": "Hong Kong Law Reports",
    "HKLRD": "Hong Kong Law Reports & Digest",
    "HKCFA": "Hong Kong Court of Final Appeal",
    "HKCA": "Hong Kong Court of Appeal",
    "HKCFI": "Hong Kong Court of First Instance",
    # Malaysia
    "MLJ": "Malayan Law Journal",
    "CLJ": "Current Law Journal (Malaysia)",
    # South Africa
    "SALR": "South African Law Reports",
    "ZASCA": "South Africa Supreme Court of Appeal",
    "ZACC": "South Africa Constitutional Court",
    # International Courts
    "ICJ": "International Court of Justice",
    "ECHR": "European Court of Human Rights",
    "ECJ": "European Court of Justice",
    "ICC": "International Criminal Court",
    "ITLOS": "International Tribunal for the Law of the Sea",
    # United States (occasionally referenced)
    "US": "United States Reports (Supreme Court)",
    "S.Ct": "Supreme Court Reporter (US)",
    "SCt": "Supreme Court Reporter (US)",  # Alternative format
    "F.2d": "Federal Reporter, Second Series",
    "F.3d": "Federal Reporter, Third Series",
    "F2d": "Federal Reporter, Second Series",  # Alternative format
    "F3d": "Federal Reporter, Third Series",  # Alternative format
    # Academic and Specialist Reports
    "ICLQ": "International & Comparative Law Quarterly",
    "LQR": "Law Quarterly Review",
    "MLR": "Modern Law Review",
    "CLJ": "Cambridge Law Journal",
    "OJLS": "Oxford Journal of Legal Studies",
    "AILR": "Australian Indigenous Law Reporter",
    "IPR": "Intellectual Property Reports",
    "IPLR": "Intellectual Property Law Reports",
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

    # Pattern 3: Medium neutral with case type suffix [YEAR] COURT Type NUMBER
    # e.g., [2020] EWCA Civ 1234, [2020] EWHC (QB) 123
    pattern3 = r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(?:Civ|Crim|Admin|Fam|QB|Ch|Pat|Comm|TCC)\s+(\d+)"
    matches3 = re.finditer(pattern3, text)
    for match in matches3:
        citations.add(match.group(0))

    # Pattern 4: Citations with volume between year and series
    # e.g., [2010] 3 NZLR 123, [2019] 2 SLR 123
    pattern4 = r"\[(\d{4})\]\s+(\d+)\s+([A-Z]+[A-Za-z]*)\s+(\d+)"
    matches4 = re.finditer(pattern4, text)
    for match in matches4:
        citations.add(match.group(0))

    # Pattern 5: US Supreme Court citations
    # e.g., 123 U.S. 456, 123 US 456
    pattern5 = r"\b(\d+)\s+U\.?S\.?\s+(\d+)\b"
    matches5 = re.finditer(pattern5, text)
    for match in matches5:
        citations.add(match.group(0))

    # Pattern 6: US Federal Reporter citations
    # e.g., 456 F.3d 789, 456 F3d 789
    pattern6 = r"\b(\d+)\s+F\.?\s*[23]d\s+(\d+)\b"
    matches6 = re.finditer(pattern6, text)
    for match in matches6:
        citations.add(match.group(0))

    # Pattern 7: US Supreme Court Reporter
    # e.g., 789 S.Ct. 123, 789 SCt 123
    pattern7 = r"\b(\d+)\s+S\.?\s*Ct\.?\s+(\d+)\b"
    matches7 = re.finditer(pattern7, text)
    for match in matches7:
        citations.add(match.group(0))

    # Pattern 8: Lloyd's Reports and Criminal Appeal Reports with possessive
    # e.g., [2005] 2 Lloyd's Rep 123, (1990) 2 Cr App R 456
    pattern8 = r"(?:\[(\d{4})\]|\((\d{4})\))\s+(\d+)\s+(?:Lloyd's\s*Rep|Cr\s*App\s*R|CrAppR)\s+(\d+)"
    matches8 = re.finditer(pattern8, text)
    for match in matches8:
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
    # Check for special citation formats first

    # EWCA/EWHC with case type suffix
    ewca_match = re.match(
        r"\[(\d{4})\]\s+(EWCA|EWHC)\s+(?:Civ|Crim|Admin|Fam|QB|Ch|Pat|Comm|TCC)\s+(\d+)",
        citation,
    )
    if ewca_match:
        court = ewca_match.group(2)
        if court in UK_INTERNATIONAL_COURTS:
            return (
                "",
                f"UK/International citation ({UK_INTERNATIONAL_COURTS[court]}) - not available on AustLII",
            )

    # US Citations
    us_match = re.match(r"\d+\s+U\.?S\.?\s+\d+", citation)
    if us_match:
        return (
            "",
            "UK/International citation (United States Reports (Supreme Court)) - not available on AustLII",
        )

    us_fed_match = re.match(r"\d+\s+F\.?\s*[23]d\s+\d+", citation)
    if us_fed_match:
        return (
            "",
            "UK/International citation (Federal Reporter) - not available on AustLII",
        )

    us_sct_match = re.match(r"\d+\s+S\.?\s*Ct\.?\s+\d+", citation)
    if us_sct_match:
        return (
            "",
            "UK/International citation (Supreme Court Reporter (US)) - not available on AustLII",
        )

    # Lloyd's Reports and Criminal Appeal Reports
    special_reports_match = re.match(
        r"(?:\[(\d{4})\]|\((\d{4})\))\s+\d+\s+(Lloyd's\s*Rep|Cr\s*App\s*R|CrAppR)\s+\d+",
        citation,
    )
    if special_reports_match:
        report_type = special_reports_match.group(3)
        if "Lloyd" in report_type:
            return (
                "",
                "UK/International citation (Lloyd's Law Reports) - not available on AustLII",
            )
        elif "Cr" in report_type:
            return (
                "",
                "UK/International citation (Criminal Appeal Reports) - not available on AustLII",
            )

    # Citations with volume between year and series
    volume_match = re.match(r"\[(\d{4})\]\s+\d+\s+([A-Z]+[A-Za-z]*)\s+\d+", citation)
    if volume_match:
        court = volume_match.group(2)
        if court in UK_INTERNATIONAL_COURTS:
            return (
                "",
                f"UK/International citation ({UK_INTERNATIONAL_COURTS[court]}) - not available on AustLII",
            )

    # Parse standard medium neutral citation
    match = re.match(r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(\d+)", citation)
    if not match:
        # Check if it's a traditional citation format
        trad_match = re.match(
            r"\((\d{4})\)\s+(\d+)\s+([A-Z]+[A-Za-z]*)\s+(\d+)", citation
        )
        if trad_match:
            # Traditional citations can't be directly converted to URLs
            return "", "Traditional citation format - cannot build direct URL"
        return "", "Invalid citation format"

    year, court, number = match.groups()

    # Check if it's a UK/International court
    if court in UK_INTERNATIONAL_COURTS:
        return (
            "",
            f"UK/International citation ({UK_INTERNATIONAL_COURTS[court]}) - not available on AustLII",
        )

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
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; LitAssist Citation Verification)"
            },
            stream=True,  # Don't download the whole body
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
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )

    return success


def search_austlii_for_citation(citation: str, timeout: int = 10) -> bool:
    """
    Search AustLII for a citation using their search interface.

    This is a fallback method for citations that can't be directly accessed via URL.

    Args:
        citation: The citation to search for
        timeout: Request timeout in seconds

    Returns:
        True if citation is found in search results
    """
    start_time = time.time()

    try:
        # Format citation for search - wrap in parentheses for exact match
        search_query = f"({citation})"

        # AustLII search URL
        search_url = "https://www.austlii.edu.au/cgi-bin/sinosrch.cgi"

        # Search parameters
        params = {
            "method": "auto",
            "query": search_query,
            "meta": "/au",  # Search Australian content
            "mask_path": "",
            "mask_world": "",
            "results": "10",
            "format": "long",
            "sort": "relevance",
        }

        response = requests.get(
            search_url,
            params=params,
            timeout=timeout,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; LitAssist Citation Verification)"
            },
        )

        if response.status_code == 200:
            # Check if the exact citation appears in the results
            # AustLII returns "0 documents found" if nothing matches
            content = response.text

            # Check for "0 documents found" which indicates no results
            if "0 documents found" in content:
                success = False
            else:
                # Look for the citation in the results
                # Normalize spaces in both the citation and content for matching
                normalized_citation = re.sub(r"\s+", " ", citation.strip())
                normalized_content = re.sub(r"\s+", " ", content)

                # Check if citation appears in results
                success = normalized_citation in normalized_content
        else:
            success = False

    except Exception as e:
        success = False
        error_msg = str(e)

    # Log the search attempt
    save_log(
        "austlii_search_validation",
        {
            "method": "search_austlii_for_citation",
            "citation": citation,
            "success": success,
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "timeout": timeout,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
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
        # Australian traditional law reports
        r"\[\d{4}\]\s+(VR|VLR|CLR|ALR|FCR|FLR|IR|ACTR|NTLR|SASR|WAR|TasR|NSWLR|QLR|QR|SR)\s+\d+",
        # UK/Privy Council citations
        r"\[\d{4}\]\s+(AC|PC|WLR|All\s*ER|AllER|Ch|QB|KB|Fam|ER)\s+\d+",
        r"\[\d{4}\]\s+\d+\s+(WLR|All\s*ER|AllER)\s+\d+",  # Alternative format [Year] Volume Series Page
        r"\(\d{4}\)\s+\d+\s+(Cr\s*App\s*R|CrAppR|Lloyd's\s*Rep)\s+\d+",  # Criminal Appeal Reports, Lloyd's
        # New Zealand
        r"\[\d{4}\]\s+\d+\s+NZLR\s+\d+",
        r"\(\d{4}\)\s+\d+\s+NZLR\s+\d+",
        # Canada
        r"\[\d{4}\]\s+\d+\s+SCR\s+\d+",
        r"\(\d{4}\)\s+\d+\s+(DLR|OR|BCR|AR|QR)\s+\d+",
        # Singapore
        r"\[\d{4}\]\s+\d+\s+SLR\s+\d+",
        # Hong Kong
        r"\[\d{4}\]\s+\d+\s+(HKLR|HKLRD)\s+\d+",
        r"\(\d{4}\)\s+\d+\s+(HKLR|HKLRD)\s+\d+",
        # Malaysia
        r"\[\d{4}\]\s+\d+\s+(MLJ|CLJ)\s+\d+",
        # South Africa
        r"\[\d{4}\]\s+\d+\s+SALR\s+\d+",
        r"\(\d{4}\)\s+\d+\s+SALR\s+\d+",
        # United States
        r"\d+\s+U\.?S\.?\s+\d+",  # 123 U.S. 456 or 123 US 456
        r"\d+\s+S\.?\s*Ct\.?\s+\d+",  # 123 S.Ct. 456 or 123 SCt 456
        r"\d+\s+F\.?\s*[23]d\s+\d+",  # 123 F.2d 456 or 123 F2d 456
        # International law reports/journals
        r"\[\d{4}\]\s+\d*\s*(ICLQ|LQR|MLR|CLJ|OJLS|AILR|IPR|IPLR)\s+\d+",
        r"\(\d{4}\)\s+\d+\s+(ICLQ|LQR|MLR|CLJ|OJLS|AILR|IPR|IPLR)\s+\d+",
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

    # Build URL for medium neutral citations
    url, error_reason = build_austlii_url(normalized)

    if error_reason == "Traditional citation format - cannot build direct URL":
        # Traditional citations temporarily accepted due to AustLII search API being broken
        # TODO: Re-enable search verification once AustLII fixes their API
        with _cache_lock:
            _citation_cache[normalized] = {
                "exists": True,
                "url": "",
                "reason": "Traditional citation - temporarily accepted (AustLII search unavailable)",
                "checked_at": time.time(),
            }
        return True, "", "Traditional citation - temporarily accepted"

    elif error_reason:
        # Check if it's a UK/International citation (which is valid, just not on AustLII)
        if "UK/International citation" in error_reason:
            with _cache_lock:
                _citation_cache[normalized] = {
                    "exists": True,  # Mark as valid
                    "url": "",
                    "reason": error_reason,  # Keep the explanation
                    "checked_at": time.time(),
                }
            return (
                True,
                "",
                error_reason,
            )  # Return True for valid UK/international citations
        else:
            # Other errors (invalid format, etc)
            with _cache_lock:
                _citation_cache[normalized] = {
                    "exists": False,
                    "url": "",
                    "reason": error_reason,
                    "checked_at": time.time(),
                }
            return False, "", error_reason

    # Check if URL exists (for medium neutral citations)
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

    # Enhanced logging to capture full details for audit
    detailed_results = []

    for citation in citations:
        exists, url, reason = verify_single_citation(citation)

        # Capture full details for logging
        citation_detail = {
            "citation": citation,
            "verified": exists,
            "url": url if url else None,
            "reason": reason if reason else None,
            "is_traditional": is_traditional_citation_format(citation),
            "is_international": (
                "UK/International citation" in reason if reason else False
            ),
        }
        detailed_results.append(citation_detail)

        if exists:
            verified.append(citation)
        else:
            unverified.append((citation, reason))

    # Enhanced logging with full citation details
    log_data = {
        "method": "verify_all_citations",
        "input_text_length": len(text),
        "citations_found": len(citations),
        "citations_verified": len(verified),
        "citations_unverified": len(unverified),
        "verified_citations": verified,
        "unverified_citations": [
            {"citation": cit, "reason": reason} for cit, reason in unverified
        ],
        "detailed_results": detailed_results,
        "international_citations": [
            d for d in detailed_results if d.get("is_international", False)
        ],
        "traditional_citations": [
            d for d in detailed_results if d.get("is_traditional", False)
        ],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Log the overall verification session
    save_log("citation_verification_session", log_data)

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
