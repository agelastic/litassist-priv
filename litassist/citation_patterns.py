"""
Pattern-based citation validation for Australian legal citations.

This module provides offline validation of citation patterns, complementing
the real-time verification in citation_verify.py.
"""

import re
from typing import List
from litassist.logging import save_log
from litassist.timing import timed
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

    # Pattern 9: Australian statutes with year and optional jurisdiction
    # Build regex in parts for clarity
    connecting_words = r"(?:of|and|for|the|on|in|to|with|by|at|from)"
    sentence_starters = r"(?:Does|Do|Did|Can|Could|Should|Would|Will|Is|Are|Was|Were|Has|Have|Had|What|Where|When|Why|Who|Which|How)"

    # Act pattern components (restrict to single-line, Title-Case start)
    # Prevent crossing newlines by using spaces/tabs only; avoid swallowing ALL-CAPS headers
    act_name_part = (
        r"[A-Z][a-z]+(?:[ \t]+" + connecting_words + r")*(?:[ \t]+[A-Z][a-zA-Z]+)*"
    )
    act_year_part = r"[ \t]+Act[ \t]+\d{4}"
    jurisdiction_part = r"(?:[ \t]+\([A-Z][a-zA-Z]+\))?"

    # Complete pattern: skip sentence starters, then capture Act name
    act_pattern = (
        r"(?<!\w)(?!"
        + sentence_starters
        + r"[ \t]+)("
        + act_name_part
        + act_year_part
        + jurisdiction_part
        + r")"
    )
    for match in re.finditer(act_pattern, text):
        citations.add(match.group(1))

    # Pattern 10: Australian regulations with year
    # e.g., Fair Work Regulations 2009
    pattern10 = r"[A-Z][A-Za-z]+(?:\s+(?:and\s+)?[A-Za-z]+)*\s+Regulations?\s+\d{4}"
    matches10 = re.finditer(pattern10, text)
    for match in matches10:
        citations.add(match.group(0))

    # Note: Section references (e.g., "section 18", "s 18") are not extracted as standalone
    # citations because they need the Act context to be meaningful

    return list(citations)


# ── Individual Validation Functions ─────────────────────────────
# Note: Pattern-based validation functions removed as they are bypassed
# in favor of online database verification (see validate_citation_patterns)


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
        from litassist.citation.verify import verify_all_citations

        _, unverified_citations = verify_all_citations(content)

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
