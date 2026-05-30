"""
Shared case-facts helpers.

The 10-heading structure produced by `extractfacts` is the required input shape
for several commands (`strategy`, `barbrief`). This module is the single source
of truth both for validating that shape and for resolving which case-facts file
to use when one is not given on the command line.
"""

import glob
import re

import click

from litassist.utils.formatting import info_message


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


def resolve_case_facts_file() -> str:
    """
    Pick the case-facts file to use when one was not given on the command line.

    Globs ``case_facts*.txt`` in the current (launch) directory and returns the
    latest. Our generated filenames embed a zero-padded ``YYYYMMDD_HHMMSS``
    timestamp and ``"."`` sorts before ``"_"``, so the lexically greatest name is
    the newest timestamped version (e.g. ``case_facts_20260530_101500.txt``); a
    lone ``case_facts.txt`` is returned as-is. The chosen file is printed.

    Returns:
        Path (relative to the launch directory) of the chosen case-facts file.

    Raises:
        click.ClickException: If no ``case_facts*.txt`` exists in the directory.
    """
    candidates = sorted(glob.glob("case_facts*.txt"))
    if not candidates:
        raise click.ClickException(
            "No case facts file provided and no case_facts*.txt found in the "
            "current directory. Pass the file explicitly, or run "
            "'litassist extractfacts' to create one."
        )

    chosen = candidates[-1]
    click.echo(info_message(f"Using case facts: {chosen}"))
    return chosen
