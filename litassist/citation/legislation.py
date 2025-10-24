"""
Legislation and international citation handling.

This module provides functions for identifying legislation references and
UK/International citations that don't require verification against Australian
legal databases.
"""

import re

from litassist.timing import timed
from .constants import UK_INTERNATIONAL_COURTS


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


def is_legislation_reference(citation: str) -> bool:
    """
    Check if a citation is legislation (Act or Regulation) rather than case law.

    Legislation doesn't need case law database verification.

    Args:
        citation: Citation text to check

    Returns:
        True if this is legislation, False if it's case law
    """
    # Check for Acts with year (e.g., "Migration Act 1958", "Family Violence Act 2016 (ACT)")
    if re.search(r"\bAct\s+\d{4}(?:\s+\([A-Za-z]+\))?", citation):
        return True

    # Check for Regulations with year (e.g., "Fair Work Regulations 2009")
    if re.search(r"\bRegulations?\s+\d{4}(?:\s+\([A-Za-z]+\))?", citation):
        return True

    return False


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
