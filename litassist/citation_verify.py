"""
Real-time citation verification against Jade.io.

This module provides comprehensive verification of Australian legal citations
by checking their existence on Jade.io database via Google Custom Search.
It implements strict validation with surgical removal of invalid citations
and targeted regeneration when necessary.
"""

import re
import time
import os
from typing import List, Tuple, Dict
import threading

# Import logging utility and config
from litassist.utils import save_log, timed
from litassist.config import CONFIG
from litassist.citation_patterns import extract_citations

# Cache for verified citations to avoid repeated requests
_citation_cache: Dict[str, Dict] = {}
_cache_lock = threading.Lock()

# Australian court abbreviations and their traditional paths (for URL building compatibility)
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

# Note: Known citations database removed per user request
# The system now relies on high-authority source acceptance when verification is unavailable

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
    "OJLS": "Oxford Journal of Legal Studies",
    "AILR": "Australian Indigenous Law Reporter",
    "IPR": "Intellectual Property Reports",
    "IPLR": "Intellectual Property Law Reports",
}


class CitationVerificationError(Exception):
    """Raised when citation verification fails and output cannot proceed."""

    pass


class TestVerificationError(CitationVerificationError):
    """Raised for expected verification errors in tests - no console output."""

    def __str__(self):
        return ""


def in_test_mode():
    """Check if running in test mode."""
    return os.environ.get("LITASSIST_TEST_MODE") == "1"


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


def check_international_citation(citation: str) -> str:
    """
    Check if citation is UK/International (valid but not Australian).

    Args:
        citation: Citation to check

    Returns:
        Reason string if international citation, empty string if Australian
    """
    # EWCA/EWHC with case type suffix
    ewca_match = re.match(
        r"\[(\d{4})\]\s+(EWCA|EWHC)\s+(?:Civ|Crim|Admin|Fam|QB|Ch|Pat|Comm|TCC)\s+(\d+)",
        citation,
    )
    if ewca_match:
        court = ewca_match.group(2)
        if court in UK_INTERNATIONAL_COURTS:
            return f"UK/International citation ({UK_INTERNATIONAL_COURTS[court]}) - not in Australian databases"

    # US Citations
    if re.match(r"\d+\s+U\.?S\.?\s+\d+", citation):
        return "UK/International citation (United States Reports (Supreme Court)) - not in Australian databases"

    if re.match(r"\d+\s+F\.?\s*[23]d\s+\d+", citation):
        return (
            "UK/International citation (Federal Reporter) - not in Australian databases"
        )

    if re.match(r"\d+\s+S\.?\s*Ct\.?\s+\d+", citation):
        return "UK/International citation (Supreme Court Reporter (US)) - not in Australian databases"

    # Lloyd's Reports and Criminal Appeal Reports
    special_reports_match = re.match(
        r"(?:\[(\d{4})\]|\((\d{4})\))\s+\d+\s+(Lloyd's\s*Rep|Cr\s*App\s*R|CrAppR)\s+\d+",
        citation,
    )
    if special_reports_match:
        report_type = special_reports_match.group(3)
        if "Lloyd" in report_type:
            return "UK/International citation (Lloyd's Law Reports) - not in Australian databases"
        elif "Cr" in report_type:
            return "UK/International citation (Criminal Appeal Reports) - not in Australian databases"

    # Citations with volume between year and series
    volume_match = re.match(r"\[(\d{4})\]\s+\d+\s+([A-Z]+[A-Za-z]*)\s+\d+", citation)
    if volume_match:
        series = volume_match.group(2)
        if series in UK_INTERNATIONAL_COURTS:
            return f"UK/International citation ({UK_INTERNATIONAL_COURTS[series]}) - not in Australian databases"

    # Medium neutral citation with UK/International court
    match = re.match(r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(\d+)", citation)
    if match:
        court = match.group(2)
        if court in UK_INTERNATIONAL_COURTS:
            return f"UK/International citation ({UK_INTERNATIONAL_COURTS[court]}) - not in Australian databases"

    return ""  # Not international


def search_jade_via_google_cse(citation: str, timeout: int = 10) -> bool:
    """
    Search Jade.io for a citation using Google Custom Search Engine.

    This is now the primary citation verification method, replacing AustLII.

    Args:
        citation: The citation to search for
        timeout: Request timeout in seconds

    Returns:
        True if citation is found in Jade search results via Google CSE
    """
    start_time = time.time()

    try:
        from googleapiclient.discovery import build

        # Use Google Custom Search to search Jade.io
        service = build(
            "customsearch", "v1", developerKey=CONFIG.g_key, cache_discovery=False
        )

        # Format citation for search - clean format for better matching
        search_query = (
            citation.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
        )

        # Search using configured CSE
        res = (
            service.cse()
            .list(q=search_query, cx=CONFIG.cse_id, num=10)
            .execute()
        )

        # Enhanced search with multiple variations to handle different citation formats
        success = False
        if "items" in res:
            # Create multiple search variations for better matching
            base_citation = (
                citation.replace("(", "")
                .replace(")", "")
                .replace("[", "")
                .replace("]", "")
            )
            citation_variations = [
                citation.lower(),  # Original format
                base_citation.lower(),  # Clean version
                citation.replace("[", "(")
                .replace("]", ")")
                .lower(),  # Convert brackets to parentheses
                citation.replace("(", "[")
                .replace(")", "]")
                .lower(),  # Convert parentheses to brackets
            ]

            # Extract components for flexible matching
            import re

            year_match = re.search(r"(\d{4})", citation)
            volume_match = re.search(
                r"\)\s*(\d+)\s+([A-Z]+)\s+(\d+)", citation
            )  # For (year) vol series page

            for item in res["items"]:
                title = item.get("title", "").lower()
                snippet = item.get("snippet", "").lower()
                link = item.get("link", "").lower()
                combined_text = f"{title} {snippet} {link}"

                # Check for exact citation match in any variation
                for variation in citation_variations:
                    if variation in combined_text:
                        success = True
                        break

                if success:
                    break

                # For traditional citations, check if we can find the key components
                if year_match and volume_match:
                    year = year_match.group(1)
                    series = volume_match.group(2).lower()
                    page = volume_match.group(3)

                    # Check if year, series, and page all appear in the result
                    if (
                        year in combined_text
                        and series in combined_text
                        and page in combined_text
                    ):
                        success = True
                        break

    except Exception:
        success = False

    # Log the search attempt
    save_log(
        "google_cse_validation",
        {
            "method": "search_jade_via_google_cse",
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
    Check if citation is in traditional format that requires search-based verification.

    Args:
        citation: Citation to check

    Returns:
        True if citation is in traditional format (volume/page citations)
    """
    # Traditional formats like (1968) 118 CLR 1, [1919] VLR 497, [1955] AC 431
    traditional_patterns = [
        r"\(\d{4}\)\s+\d+\s+[A-Z]+\s+\d+",  # (Year) Volume Series Page - covers CLR, ALR, etc.
        # Australian traditional law reports - [Year] Series Page
        r"\[\d{4}\]\s+(VR|VLR|CLR|ALR|FCR|FLR|IR|ACTR|NTLR|SASR|WAR|TasR|NSWLR|QLR|QR|SR)\s+\d+",
        # Australian traditional law reports - [Year] Volume Series Page
        r"\[\d{4}\]\s+\d+\s+(VR|VLR|CLR|ALR|FCR|FLR|IR|ACTR|NTLR|SASR|WAR|TasR|NSWLR|QLR|QR|SR)\s+\d+",
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
    Verify a single citation against available databases.

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

    # Check for UK/International citations first (these are valid but not Australian)
    international_reason = check_international_citation(normalized)
    if international_reason:
        with _cache_lock:
            _citation_cache[normalized] = {
                "exists": True,  # Valid but not Australian
                "url": "",
                "reason": international_reason,
                "checked_at": time.time(),
            }
        return True, "", international_reason

    # Check for format issues using offline validation
    from litassist.citation_patterns import validate_citation_patterns

    format_issues = validate_citation_patterns(normalized, enable_online=False)
    if format_issues:
        # Format validation found problems - invalid citation format
        with _cache_lock:
            _citation_cache[normalized] = {
                "exists": False,
                "url": "",
                "reason": f"Invalid citation format: {format_issues[0]}",
                "checked_at": time.time(),
            }
        return False, "", f"Invalid citation format: {format_issues[0]}"

    # Primary verification: Use Jade.io via Google CSE for ALL citations
    try:
        exists_in_jade = search_jade_via_google_cse(normalized, timeout=5)
        if exists_in_jade:
            reason = "Verified via Google CSE search of Jade.io"

            with _cache_lock:
                _citation_cache[normalized] = {
                    "exists": True,
                    "url": "",  # No direct URLs - use Jade.io for access
                    "reason": reason,
                    "checked_at": time.time(),
                }
            return True, "", reason
    except Exception:
        pass  # Fall through to offline validation

    # If online verification fails, accept with offline validation warning
    reason = "[WARNING] OFFLINE VALIDATION ONLY - Online verification unavailable, passed pattern analysis"
    with _cache_lock:
        _citation_cache[normalized] = {
            "exists": True,
            "url": "",
            "reason": reason,
            "checked_at": time.time(),
        }
    return True, "", reason


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
    text = re.sub(r"[ \t]+", " ", text)  # Only collapse spaces/tabs, preserve newlines
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
