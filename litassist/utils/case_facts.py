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

    Each heading must start a line (case-insensitive, after optional numbering /
    markdown bold / punctuation), with anything allowed after it - so all the
    forms extractfacts produces validate, e.g. "Parties", "## Parties",
    "PARTIES:", "1. **Parties**: ...". Missing headings are echoed for the user.

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
        # The heading must be the first alphabetic token on its line, after an
        # optional non-alphabetic prefix (numbering, markdown bold, whitespace).
        # Anything may follow (a colon + inline description, or nothing), so this
        # accepts every form extractfacts produces: "Parties", "## Parties",
        # "PARTIES:", and "1. **Parties**: ...". The trailing word-boundary stops
        # "Partiesxyz" from counting.
        pattern = r"^\s*[^a-zA-Z]*" + re.escape(heading) + r"\b"
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            missing_headings.append(heading)

    if missing_headings:
        click.echo(f"Missing required headings: {', '.join(missing_headings)}")
        click.echo("Note: Headings are now case-insensitive and can have punctuation.")
        return False

    return True
