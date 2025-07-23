"""
Pattern-based citation validation for Australian legal citations.

This module provides offline validation of citation patterns, complementing
the real-time verification in citation_verify.py.
"""

import re
from typing import List
from litassist.utils import save_log, timed
import time


# ── Pattern Constants ─────────────────────────────────────────

# Common generic surnames that are often hallucinated
GENERIC_SURNAMES = [
    "smith",
    "jones",
    "brown",
    "wilson",
    "taylor",
    "johnson",
    "white",
    "martin",
    "anderson",
    "thompson",
    "davis",
    "miller",
    "moore",
    "jackson",
    "harris",
    "clark",
    "lewis",
    "robinson",
    "walker",
]

# Placeholder-like names
PLACEHOLDER_PATTERNS = [
    r"^(test|example|sample|demo|person|party|entity|company)$",
    r"^[a-z]$",  # Single letters
    r"^(abc|xyz|123)$",  # Simple patterns
    r"^(plaintiff|defendant|applicant|respondent)$",  # Role names
    r"^(doe|roe)$",  # Legal placeholders
]

# Valid court abbreviations (Australian + historical UK/Privy Council)
VALID_COURTS = {
    # Australian courts
    "HCA": {
        "name": "High Court of Australia",
        "established": 1903,
        "max_per_year": 100,
    },
    "FCA": {
        "name": "Federal Court of Australia",
        "established": 1977,
        "max_per_year": 2000,
    },
    "FCAFC": {"name": "Full Federal Court", "established": 1977, "max_per_year": 500},
    "FamCA": {
        "name": "Family Court of Australia",
        "established": 1976,
        "max_per_year": 1000,
    },
    "FamCAFC": {"name": "Full Family Court", "established": 1976, "max_per_year": 200},
    "NSWSC": {"name": "NSW Supreme Court", "established": 1824, "max_per_year": 5000},
    "NSWCA": {"name": "NSW Court of Appeal", "established": 1966, "max_per_year": 500},
    "NSWCCA": {
        "name": "NSW Court of Criminal Appeal",
        "established": 1912,
        "max_per_year": 500,
    },
    "VSC": {
        "name": "Victorian Supreme Court",
        "established": 1852,
        "max_per_year": 3000,
    },
    "VSCA": {
        "name": "Victorian Court of Appeal",
        "established": 1995,
        "max_per_year": 300,
    },
    "QSC": {
        "name": "Queensland Supreme Court",
        "established": 1861,
        "max_per_year": 2000,
    },
    "QCA": {
        "name": "Queensland Court of Appeal",
        "established": 1991,
        "max_per_year": 300,
    },
    "SASC": {"name": "SA Supreme Court", "established": 1837, "max_per_year": 1000},
    "SASCFC": {"name": "SA Full Court", "established": 1837, "max_per_year": 200},
    "WASC": {"name": "WA Supreme Court", "established": 1861, "max_per_year": 1500},
    "WASCA": {"name": "WA Court of Appeal", "established": 1969, "max_per_year": 200},
    "TASSC": {
        "name": "Tasmanian Supreme Court",
        "established": 1824,
        "max_per_year": 500,
    },
    "ACTSC": {"name": "ACT Supreme Court", "established": 1934, "max_per_year": 500},
    "NTSC": {"name": "NT Supreme Court", "established": 1911, "max_per_year": 300},
    "ACTOFOI": {
        "name": "ACT Office of the Freedom of Information",
        "established": 1989,
        "max_per_year": 100,
    },
    # UK/Privy Council courts (historically relevant to Australian law)
    "AC": {
        "name": "Appeal Cases (Privy Council)",
        "established": 1875,
        "max_per_year": 9999,
    },
    "PC": {"name": "Privy Council", "established": 1833, "max_per_year": 9999},
    "WLR": {"name": "Weekly Law Reports", "established": 1953, "max_per_year": 9999},
    "QB": {"name": "Queen's Bench", "established": 1875, "max_per_year": 9999},
    "KB": {"name": "King's Bench", "established": 1875, "max_per_year": 9999},
    "Ch": {"name": "Chancery", "established": 1875, "max_per_year": 9999},
}

# Report series validation patterns
REPORT_PATTERNS = [
    (r"\((\d{4})\)\s+(\d+)\s+(CLR)\s+\d+", "CLR", 1903),  # Commonwealth Law Reports
    (r"\((\d{4})\)\s+(\d+)\s+(ALR)\s+\d+", "ALR", 1973),  # Australian Law Reports
    (r"\((\d{4})\)\s+(\d+)\s+(FCR)\s+\d+", "FCR", 1984),  # Federal Court Reports
    (r"\((\d{4})\)\s+(\d+)\s+(FLR)\s+\d+", "FLR", 1976),  # Family Law Reports
    (r"\((\d{4})\)\s+(\d+)\s+(NSWLR)\s+\d+", "NSWLR", 1960),  # NSW Law Reports
    (r"\((\d{4})\)\s+(\d+)\s+(VR)\s+\d+", "VR", 1957),  # Victorian Reports
    (r"\((\d{4})\)\s+(\d+)\s+(QR)\s+\d+", "QR", 1958),  # Queensland Reports
    (r"\((\d{4})\)\s+(\d+)\s+(SASR)\s+\d+", "SASR", 1970),  # SA State Reports
    (r"\((\d{4})\)\s+(\d+)\s+(WAR)\s+\d+", "WAR", 1899),  # WA Reports
]

# Known hallucination patterns
HALLUCINATION_INDICATORS = [
    r"Corporation\s+v\s+Corporation",  # Two corporations with generic names
    r"Pty\s+Ltd\s+v\s+Pty\s+Ltd",  # Two Pty Ltds without proper names
    r"The\s+Queen\s+v\s+[A-Z](?:\s|$)",  # Criminal cases with single letter defendants
    r"(?:Re|In\s+re)\s+[A-Z](?:\s|$)",  # In re cases with single letters
    r"Ex\s+parte\s+[A-Z](?:\s|$)",  # Ex parte with single letters
]


# ── Citation Extraction Functions ─────────────────────────────


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


# ── Individual Validation Functions ─────────────────────────────


def validate_generic_names(content: str, complete_citations: set) -> List[str]:
    """
    Check for generic/placeholder case names that might be hallucinated.

    Args:
        content: Text to validate
        complete_citations: Set of complete citations to exclude from checking

    Returns:
        List of validation issues found
    """
    issues = []

    # Find case patterns and clean up party names
    case_name_pattern = r"([A-Z][A-Za-z\'\-]+(?:\s+[A-Z][A-Za-z\'\-]+)*)\s+v\s+([A-Z][A-Za-z\'\-]+(?:\s+[A-Z][A-Za-z\'\-]+)*)"
    raw_case_names = re.findall(case_name_pattern, content)

    # Clean up party names by removing common prefixes
    prefix_words = {
        "In",
        "in",
        "The",
        "the",
        "Following",
        "following",
        "Case",
        "case",
        "decision",
        "Decision",
    }
    all_case_names = []
    for party1, party2 in raw_case_names:
        # Clean first party
        p1_words = party1.split()
        while p1_words and p1_words[0] in prefix_words:
            p1_words.pop(0)
        clean_party1 = " ".join(p1_words) if p1_words else party1

        # Clean second party
        p2_words = party2.split()
        while p2_words and p2_words[0] in prefix_words:
            p2_words.pop(0)
        clean_party2 = " ".join(p2_words) if p2_words else party2

        # Only add if both parties are still valid after cleaning
        if clean_party1 and clean_party2:
            all_case_names.append((clean_party1, clean_party2))

    # Filter out case names that are part of complete citations
    case_names = []
    for party1, party2 in all_case_names:
        case_name = f"{party1} v {party2}"
        if case_name not in complete_citations:
            case_names.append((party1, party2))

    for party1, party2 in case_names:
        p1_lower = party1.lower().strip()
        p2_lower = party2.lower().strip()

        # Check for generic surnames - flag if both parties have generic single-word surnames
        p1_words = p1_lower.split()
        p2_words = p2_lower.split()

        if (
            len(p1_words) == 1
            and p1_lower in GENERIC_SURNAMES
            and len(p2_words) == 1
            and p2_lower in GENERIC_SURNAMES
        ):
            issues.append(
                f"GENERIC CASE NAME: {party1} v {party2}\n  -> FAILURE: Both parties use common surnames (possible AI hallucination)\n  -> ACTION: Flagging for manual verification"
            )

        # Check for placeholder patterns
        for pattern in PLACEHOLDER_PATTERNS:
            if re.match(pattern, p1_lower) or re.match(pattern, p2_lower):
                issues.append(
                    f"PLACEHOLDER CASE NAME: {party1} v {party2}\n  -> FAILURE: Contains placeholder/test-like party names\n  -> ACTION: Excluding non-real case reference"
                )
                break

        # Check for single letters or very short names
        if (len(p1_lower) <= 2 or len(p2_lower) <= 2) and not any(
            c in "'" for c in party1 + party2
        ):
            issues.append(
                f"INVALID CASE NAME: {party1} v {party2}\n  -> FAILURE: Party name suspiciously short (≤2 characters)\n  -> ACTION: Excluding likely invalid case reference"
            )

    return issues


def validate_court_abbreviations(content: str) -> List[str]:
    """
    Validate court identifiers in medium-neutral citations.

    Args:
        content: Text to validate

    Returns:
        List of validation issues found
    """
    issues = []

    # Find medium-neutral citations
    citation_pattern = r"\[(\d{4})\]\s+([A-Z]+)\s+(\d+)"
    citations = re.findall(citation_pattern, content)

    for year_str, court, number_str in citations:
        year = int(year_str)
        number = int(number_str)
        citation = f"[{year}] {court} {number}"

        # Skip validation for traditional citation formats
        if court in ["AC", "PC", "WLR", "QB", "KB", "Ch"]:
            continue

        # Check if court exists in valid courts
        if court not in VALID_COURTS:
            issues.append(
                f"UNKNOWN COURT: {citation}\n  -> FAILURE: Court abbreviation '{court}' not recognized in Australian legal system\n  -> ACTION: Excluding invalid court reference"
            )
            continue

        court_info = VALID_COURTS[court]

        # Check if court existed in that year
        if year < court_info["established"]:
            issues.append(
                f"ANACHRONISTIC CITATION: {citation}\n  -> FAILURE: {court_info['name']} not established until {court_info['established']}\n  -> ACTION: Excluding impossible historical reference"
            )

        # Check if citation number is reasonable
        if number > court_info["max_per_year"]:
            issues.append(
                f"EXCESSIVE CITATION NUMBER: {citation}\n  -> FAILURE: Citation number {number} exceeds typical annual capacity for {court_info['name']}\n  -> ACTION: Flagging unlikely citation number"
            )

        # Check for future years
        if year > 2025:
            issues.append(
                f"FUTURE CITATION: {citation}\n  -> FAILURE: Citation dated in the future (after 2025)\n  -> ACTION: Excluding impossible future case"
            )

    return issues


def validate_report_series(content: str) -> List[str]:
    """
    Validate traditional report series citations.

    Args:
        content: Text to validate

    Returns:
        List of validation issues found
    """
    issues = []

    for pattern, series_name, established_year in REPORT_PATTERNS:
        report_citations = re.findall(pattern, content)
        for year_str, volume, series in report_citations:
            year = int(year_str)
            if year < established_year:
                issues.append(
                    f"Report series {series_name} not published in {year} (established {established_year})"
                )

    return issues


def validate_page_numbers(content: str) -> List[str]:
    """
    Check for unrealistic page numbers in citations.

    Args:
        content: Text to validate

    Returns:
        List of validation issues found
    """
    issues = []

    # Check for impossible page numbers
    page_pattern = r"(?:at|,)\s+(\d+)(?:-\d+)?(?:\s|,|\.|\)|$)"
    pages = re.findall(page_pattern, content)
    for page_str in pages:
        page = int(page_str)
        if page > 9999:  # Suspiciously high page number
            issues.append(f"Suspiciously high page number: {page}")

    return issues


def validate_parallel_citations(content: str) -> List[str]:
    """
    Check consistency in parallel citations.

    Args:
        content: Text to validate

    Returns:
        List of validation issues found
    """
    issues = []

    # Check for malformed parallel citations
    parallel_pattern = r"(\[\d{4}\]\s+[A-Z]+\s+\d+)\s*[;,]\s*(\[\d{4}\]\s+[A-Z]+\s+\d+)"
    parallel_cites = re.findall(parallel_pattern, content)
    for cite1, cite2 in parallel_cites:
        year1 = re.search(r"\[(\d{4})\]", cite1).group(1)
        year2 = re.search(r"\[(\d{4})\]", cite2).group(1)
        if year1 != year2:
            issues.append(
                f"Parallel citations with different years: {cite1} and {cite2}"
            )

    return issues


def detect_hallucination_patterns(content: str) -> List[str]:
    """
    Detect known AI hallucination patterns in case names.

    Args:
        content: Text to validate

    Returns:
        List of validation issues found
    """
    issues = []

    for pattern in HALLUCINATION_INDICATORS:
        if re.search(pattern, content):
            matches = re.findall(pattern, content)
            for match in matches:
                issues.append(f"Potential AI hallucination pattern: {match.strip()}")

    return issues


def extract_complete_citations(content: str) -> set:
    """
    Extract all complete citations to exclude from generic name checking.

    Args:
        content: Text to process

    Returns:
        Set of complete case names found in proper citations
    """
    complete_citations = set()

    # Find traditional citations: (Year) Volume Series Page
    traditional_pattern = r"([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)\s+v\s+([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)\s+\(\d{4}\)\s+\d+\s+[A-Z]+\s+\d+"
    traditional_matches = re.findall(traditional_pattern, content)
    for party1, party2 in traditional_matches:
        complete_citations.add(f"{party1} v {party2}")

    # Find medium-neutral citations: Case Name [Year] Court Number
    medium_neutral_pattern = r"([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)\s+v\s+([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)\s+\[\d{4}\]\s+[A-Z]+\s+\d+"
    medium_neutral_matches = re.findall(medium_neutral_pattern, content)
    for party1, party2 in medium_neutral_matches:
        complete_citations.add(f"{party1} v {party2}")

    return complete_citations


# ── Main Validation Function ─────────────────────────────────────


def validate_citation_patterns(content: str, enable_online: bool = True) -> List[str]:
    """
    Validation of Australian legal citations using online database verification.

    This function relies on online verification to check if citations actually exist
    in legal databases, as pattern validation cannot determine if a citation is real
    or hallucinated.

    Args:
        content: Text content to validate
        enable_online: Whether to perform online database verification (default: True)

    Returns:
        List of potential citation issues found
    """
    unique_issues = []

    # Skip pattern validation entirely - it causes false positives and doesn't
    # determine if citations are real. Go directly to online verification.

    # If online verification is disabled, return empty list since we can't
    # determine if citations are real without checking the database
    if not enable_online:
        return []

    # ── Online Database Verification ────────────────
    # Perform online verification for ALL citations
    try:
        from litassist.citation_verify import verify_all_citations

        verified_citations, unverified_citations = verify_all_citations(content)

        # Add online verification results to issues
        for citation, reason in unverified_citations:
            # Distinguish between different types of online failures
            if "Unknown court" in reason:
                unique_issues.append(
                    f"COURT NOT RECOGNIZED: {citation} - {reason}\n  -> ACTION: Excluding unrecognized court identifier"
                )
            elif (
                "Invalid citation format" in reason
                or "verification unavailable" in reason
            ):
                unique_issues.append(
                    f"CITATION NOT FOUND: {citation} - {reason}\n  -> ACTION: Citation does not exist in legal database"
                )
            else:
                unique_issues.append(
                    f"ONLINE VERIFICATION FAILED: {citation} - {reason}\n  -> ACTION: Could not verify citation authenticity"
                )
    except Exception as e:
        # If online verification fails, just note it and continue
        unique_issues.append(f"Online verification unavailable: {str(e)}")

    # Add summary assessment if issues found
    if len(unique_issues) > 0:
        severity = (
            "high"
            if len(unique_issues) > 5
            else "medium" if len(unique_issues) > 2 else "low"
        )

        # Create detailed action message
        action_msg = f"CITATION VALIDATION FAILURE ({severity} risk): {len(unique_issues)} issues detected.\n"
        action_msg += f"-> ONLINE DATABASE VERIFICATION: {len(unique_issues)} citations not found in legal database\n"
        action_msg += (
            "-> ACTION TAKEN: Flagging questionable citations for manual review\n"
        )
        action_msg += "-> RECOMMENDATION: Verify all citations independently before use"

        unique_issues.insert(0, action_msg)

    # Log the citation validation
    save_log(
        "citation_validation",
        {
            "method": "validate_citation_patterns",
            "input_text_length": len(content),
            "enable_online": enable_online,
            "issues_found": len(unique_issues),
            "issues": unique_issues,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )

    return unique_issues
