"""
Validation functions for strategy command.

This module contains functions for validating case facts format
and extracting legal issues from case documents.
"""

import re
from typing import List

# Single source of truth for the 10-heading check, shared with barbrief.
# Re-exported here so existing `strategy.validators.validate_case_facts_format`
# importers keep working.
from litassist.utils.case_facts import validate_case_facts_format

__all__ = ["validate_case_facts_format", "extract_legal_issues"]


def _is_section_heading(line: str, headers: List[str]) -> bool:
    """True if the line announces one of ``headers``.

    A heading is the header text at the start of the line, after an optional
    non-alphabetic prefix (numbering / markdown / bold / whitespace), and then
    nothing but a heading boundary - a ``:`` or ``*`` or ``#``, or the end of the
    line. That accepts the numbered/bold extractfacts style
    ("5. **Evidence Available**: ..."), the colon style ("Evidence Available:")
    and the markdown style ("## Evidence Available"), while a prose line that
    merely starts with a heading word ("Jurisdiction of the court was disputed")
    is not treated as a heading.
    """
    low = line.lower()
    return any(
        re.match(r"^[#\d.\*\s]*" + re.escape(h) + r"\s*(?:[:*#]|$)", low)
        for h in headers
    )


def extract_legal_issues(case_text: str) -> List[str]:
    """
    Extract legal issues from the case facts text.

    Handles both the plain own-line style ("Legal Issues:" with the issues on
    the following lines) and the extractfacts numbered/bold style
    ("4. **Legal Issues**: <issue>") where the issue can sit inline on the
    heading line. Collection stops at the next section heading in either style.

    Args:
        case_text: Full text of the case facts.

    Returns:
        List of identified legal issues.
    """
    section_headers = [
        "evidence available",
        "opposing arguments",
        "procedural history",
        "jurisdiction",
        "applicable law",
        "client objectives",
    ]

    lines = case_text.split("\n")

    # Locate the Legal Issues heading line (numbering/bold/plain tolerant).
    legal_issues_idx = -1
    for i, line in enumerate(lines):
        if re.match(r"^[#\d.\*\s]*legal issues\s*(?:[:*#]|$)", line.lower()):
            legal_issues_idx = i
            break

    if legal_issues_idx == -1:
        return []

    collected = []

    # Issue text inline on the heading line itself (after the first colon).
    if ":" in lines[legal_issues_idx]:
        inline = lines[legal_issues_idx].split(":", 1)[1].strip().strip("*").strip()
        if inline:
            collected.append(inline)

    # Then any lines below, until the next section heading.
    for line in lines[legal_issues_idx + 1 :]:
        if _is_section_heading(line, section_headers):
            break
        collected.append(line)

    # Clean up and return non-empty lines.
    issues = []
    for line in collected:
        line = line.strip()
        if line:
            # Remove bullet points but keep content
            if line.startswith(("\u2022", "-", "*")):
                line = line[1:].strip()
            issues.append(line)

    return issues
