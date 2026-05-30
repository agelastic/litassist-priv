"""
Shared case-facts validation.

The 10-heading structure produced by `extractfacts` is the required input shape
for several commands (`strategy`, `barbrief`). This module is the single source
of truth for that check so the commands cannot drift apart.
"""

import re

import click


def validate_case_facts_format(text: str) -> bool:
    """
    Validate that case facts follow the required 10-heading structure.

    Each heading must appear on its own line (flexible: case-insensitive,
    leading/trailing non-alphabetic characters allowed, e.g. "## Parties:").
    Missing headings are echoed for the user.

    Args:
        text: The content of the case facts file.

    Returns:
        True if all ten headings are present, False otherwise.
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
    for heading in required_headings:
        # Heading on its own line: optional non-alphabetic prefix/suffix,
        # case-insensitive (e.g. "## Parties", "PARTIES:", "Parties").
        pattern = r"^\s*[^a-zA-Z]*" + re.escape(heading) + r"[^a-zA-Z]*\s*$"
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            missing_headings.append(heading)

    if missing_headings:
        click.echo(f"Missing required headings: {', '.join(missing_headings)}")
        click.echo("Note: Headings are now case-insensitive and can have punctuation.")
        return False

    return True
