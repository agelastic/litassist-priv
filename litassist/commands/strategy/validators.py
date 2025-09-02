"""
Validation functions for strategy command.

This module contains functions for validating case facts format
and extracting legal issues from case documents.
"""

import re
from typing import List
import click


def validate_case_facts_format(text: str) -> bool:
    """
    Validates that the case facts file follows the required 10-heading structure.

    Args:
        text: The content of the case facts file.

    Returns:
        True if valid, False if not valid.
    """
    required_headings = [
        "Parties",
        "Background",
        "Key Events",
        "Legal Issues",
        "Evidence Available",
        "Opposing Arguments",
        "Procedural History",
        "Jurisdiction",
        "Applicable Law",
        "Client Objectives",
    ]

    missing_headings = []

    # Check if all required headings exist in the text (less restrictive)
    for heading in required_headings:
        # Look for heading with flexible formatting:
        # - Can have non-alphabetical chars before/after
        # - Case insensitive
        # - Must be on its own line (but can have punctuation)
        pattern = r"^\s*[^a-zA-Z]*" + re.escape(heading) + r"[^a-zA-Z]*\s*$"
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            missing_headings.append(heading)

    if missing_headings:
        click.echo(f"Missing required headings: {', '.join(missing_headings)}")
        click.echo("Note: Headings are now case-insensitive and can have punctuation.")
        return False

    return True


def extract_legal_issues(case_text: str) -> List[str]:
    """
    Extract legal issues from the case facts text.

    Args:
        case_text: Full text of the case facts.

    Returns:
        List of identified legal issues.
    """
    # Find the line containing "Legal Issues"
    lines = case_text.split("\n")
    legal_issues_idx = -1
    next_section_idx = -1

    # Find Legal Issues line
    for i, line in enumerate(lines):
        if "legal issues" in line.lower():
            legal_issues_idx = i
            break

    if legal_issues_idx == -1:
        return []

    # Find next section line - must be a header (not just containing the keyword)
    section_headers = [
        "evidence available",
        "opposing arguments",
        "procedural history",
        "jurisdiction",
        "applicable law",
        "client objectives",
    ]
    for i in range(legal_issues_idx + 1, len(lines)):
        line_clean = lines[i].strip().lower()
        # Remove common formatting (##, numbers, colons, asterisks)
        line_clean = re.sub(r"^[#\d\.\*\s]+", "", line_clean)
        line_clean = re.sub(r"[:*\s]+$", "", line_clean)

        # Check if this cleaned line matches a section header exactly
        if line_clean in section_headers:
            next_section_idx = i
            break

    # Extract lines between Legal Issues and next section
    if next_section_idx != -1:
        issue_lines = lines[legal_issues_idx + 1 : next_section_idx]
    else:
        issue_lines = lines[legal_issues_idx + 1 :]

    # Clean up and return non-empty lines
    issues = []
    for line in issue_lines:
        line = line.strip()
        if line:
            # Remove bullet points but keep content
            if line.startswith(("•", "-", "*")):
                line = line[1:].strip()
            issues.append(line)

    return issues
