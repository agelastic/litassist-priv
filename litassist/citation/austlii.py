"""
AustLII direct URL verification.

This module provides functions for verifying citations by constructing and
checking direct URLs on the Australasian Legal Information Institute (AustLII)
database.
"""

import re
import time
from typing import Tuple

from litassist.logging import save_log
from .constants import COURT_MAPPINGS

# Single source of truth for the medium-neutral cite shape "[YYYY] COURT N".
# re.search (not match) so it also finds the neutral cite inside a longer string
# (named cite, or a parallel-citation group); reused by both construct_austlii_url
# and resolve_neutral_from_parallel so the two never drift.
_NEUTRAL_CITE_RE = re.compile(r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(\d+)")


def construct_austlii_url(citation: str) -> str:
    """
    Construct AustLII URL from a medium neutral citation.

    The neutral cite may appear anywhere in the string, so both bare
    citations ("[2022] ACTSC 272") and full named citations
    ("Fallas v Mourlas [2006] NSWCA 32" - the form command outputs use)
    are accepted.

    Args:
        citation: Citation containing a medium neutral cite

    Returns:
        URL string or empty string if cannot construct
    """
    # Parse medium neutral citation format [YYYY] COURT NUMBER; re.search,
    # not re.match - an anchored match silently failed for every citation
    # prefixed with its case name (P-JUDGE finding, 11/06/2026)
    match = _NEUTRAL_CITE_RE.search(citation)
    if not match:
        return ""

    year, court, number = match.groups()

    # Check if court is in our mappings
    if court not in COURT_MAPPINGS:
        return ""

    # COURT_MAPPINGS format is "act/ACTSC" - extract jurisdiction and court
    court_path = COURT_MAPPINGS[court]

    # Build AustLII URL
    return f"https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/{court_path}/{year}/{number}.html"


# Max characters between a traditional cite and its parallel medium-neutral cite for
# the two to count as the same pairing. ~300 spans a typical
# "(1999) 201 CLR 1; [1999] HCA 66" pair plus an intervening clause/pinpoint, while
# staying short enough to avoid pairing across unrelated sentences.
_PARALLEL_CITE_WINDOW = 300

# Max difference between the traditional cite's report year and a candidate neutral
# cite's year for them to be treated as the SAME case. Parallel cites name one
# judgment, so the years match or differ by at most one (a late-year judgment reported
# the next year). A wider gap means a different case sitting nearby in the window
# (e.g. "(2001) 207 CLR 1; [2005] HCA 5" - the neutral belongs to a 2005 case), so
# rejecting it prevents a false pairing that character distance alone cannot catch.
_PARALLEL_CITE_YEAR_TOLERANCE = 1


def _citation_year(citation: str):
    """Year from the leading (YYYY)/[YYYY] of a cite, or None if it carries no year."""
    match = re.search(r"\d{4}", citation)
    return int(match.group(0)) if match else None


def resolve_neutral_from_parallel(traditional_cite: str, source_text: str) -> str:
    """
    Recover a medium-neutral cite printed parallel to a traditional cite (C2 opt 1).

    Authorised-report cites like "(1999) 201 CLR 1" carry no "[YYYY] COURT N" form for
    construct_austlii_url to build from. Drafts and judgments usually print both forms
    together ("(1999) 201 CLR 1; [1999] HCA 66"), so when that neutral cite sits near
    the traditional one in source_text we can recover it and let the existing
    AustLII fetch path run.

    Args:
        traditional_cite: the already-extracted cite string (case name / pinpoint
            stripped by extract_citations), e.g. "(1999) 201 CLR 1"
        source_text: the raw document the cite came from (case names intact)

    Returns:
        The best-matching AustLII-constructible neutral cite within the pairing window
        on either side of the traditional cite, or "" if none. Candidates are validated
        through construct_austlii_url (excludes the traditional cite itself - round
        brackets do not match the neutral pattern - and non-AustLII courts). A candidate
        whose year is more than _PARALLEL_CITE_YEAR_TOLERANCE from the traditional cite's
        year is rejected as a different case; remaining candidates are ranked by year
        proximity first, then character distance.
    """
    if not traditional_cite or not source_text:
        return ""

    traditional_year = _citation_year(traditional_cite)

    best = ""
    best_key = None  # (year_difference, character_distance) - lower is better
    search_from = 0
    while True:
        occ = source_text.find(traditional_cite, search_from)
        if occ == -1:
            break
        occ_end = occ + len(traditional_cite)
        window_start = max(0, occ - _PARALLEL_CITE_WINDOW)
        window_end = min(len(source_text), occ_end + _PARALLEL_CITE_WINDOW)
        window = source_text[window_start:window_end]

        for m in _NEUTRAL_CITE_RE.finditer(window):
            candidate = m.group(0)
            if not construct_austlii_url(candidate):
                continue
            year_difference = 0
            if traditional_year is not None:
                year_difference = abs(int(m.group(1)) - traditional_year)
                if year_difference > _PARALLEL_CITE_YEAR_TOLERANCE:
                    # Different case sitting in the window - not a parallel cite.
                    continue
            candidate_pos = window_start + m.start()
            # Distance from the nearest edge of the traditional occurrence.
            distance = (
                occ - candidate_pos
                if candidate_pos < occ
                else candidate_pos - occ_end
            )
            key = (year_difference, distance)
            if best_key is None or key < best_key:
                best_key = key
                best = candidate

        search_from = occ_end

    return best


def verify_via_austlii_direct(citation: str, timeout: int = 5) -> Tuple[bool, str, str]:
    """
    Verify citation by constructing direct AustLII URL.

    Args:
        citation: Normalized citation
        timeout: Request timeout in seconds

    Returns:
        Tuple of (exists, url, reason)
    """
    url = construct_austlii_url(citation)
    if not url:
        return False, "", "Cannot construct AustLII URL for this citation format"

    start_time = time.time()

    try:
        import requests

        # CRITICAL: Must include User-Agent header for AustLII
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Use GET with stream=True to avoid downloading full document
        # AustLII blocks HEAD requests to /cgi-bin/viewdoc/ paths with 403 Forbidden
        response = requests.get(
            url, headers=headers, timeout=timeout, allow_redirects=True, stream=True
        )
        # Close immediately after getting status - downloads only headers (~400 bytes)
        response.close()

        success = response.status_code == 200

        # Log the attempt
        save_log(
            "austlii_direct_verification",
            {
                "citation": citation,
                "url": url,
                "success": success,
                "http_status": response.status_code,
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

        if success:
            return True, url, "Verified via AustLII direct URL"
        else:
            return False, "", f"AustLII returned HTTP {response.status_code}"

    except Exception as e:
        save_log(
            "austlii_direct_verification",
            {
                "citation": citation,
                "url": url,
                "success": False,
                "error": str(e),
                "response_time_ms": round((time.time() - start_time) * 1000, 2),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        return False, "", f"AustLII verification error: {str(e)}"


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
