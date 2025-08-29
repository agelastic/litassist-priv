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
    # Extract the "Legal Issues" section
    # Match "Legal Issues" (with or without colon, with possible ## prefix)
    # and capture content until the next heading
    match = re.search(
        r"(?:^|\n)\s*(?:##\s*)?Legal\s+Issues\s*:?\s*\n(.*?)(?=\n\s*(?:##\s*)?(?:Evidence|Opposing|Procedural|Jurisdiction|Applicable|Client)|\Z)",
        case_text,
        re.DOTALL | re.IGNORECASE | re.MULTILINE
    )

    if not match:
        return []

    # Extract individual issues (assuming one per line or bullet point)
    issues_text = match.group(1).strip()
    issues = [
        issue.strip().strip("•-*")
        for issue in re.split(r"\n+|•|\*|-", issues_text)
        if issue.strip()
    ]

    return issues