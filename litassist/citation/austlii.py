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


def construct_austlii_url(citation: str) -> str:
    """
    Construct AustLII URL from medium neutral citation.

    Args:
        citation: Normalized citation like "[2022] ACTSC 272"

    Returns:
        URL string or empty string if cannot construct
    """
    # Parse medium neutral citation format [YYYY] COURT NUMBER
    match = re.match(r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(\d+)", citation)
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
