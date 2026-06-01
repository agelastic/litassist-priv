"""
Shared case-facts helpers.

The 10-heading structure produced by `extractfacts` is the required input shape
for several commands (`strategy`, `barbrief`). This module is the single source
of truth both for validating that shape and for resolving which case-facts file
to use when one is not given on the command line.
"""

import glob
import os
import re
from datetime import datetime

import click

from litassist.utils.formatting import info_message

# Generated outputs embed a zero-padded YYYYMMDD_HHMMSS timestamp, so case-facts
# files may be named e.g. case_facts_20260530_101500.txt.
_FILENAME_TIMESTAMP = re.compile(r"\d{8}_\d{6}")


def _case_facts_recency(path: str) -> float:
    """Recency sort key for a case-facts file (higher = newer).

    Uses the timestamp embedded in the filename when present (so explicitly
    versioned files rank by their own stamp regardless of when they were copied),
    and falls back to the file's modification time otherwise. The mtime fallback
    is what stops an OLD timestamped file from shadowing a freshly-edited plain
    `case_facts.txt` (which carries no filename timestamp).
    """
    match = _FILENAME_TIMESTAMP.search(os.path.basename(path))
    if match:
        try:
            return datetime.strptime(match.group(0), "%Y%m%d_%H%M%S").timestamp()
        except ValueError:
            pass
    return os.path.getmtime(path)


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
    # Paired contract: these exact heading names must stay in sync with the
    # `case_facts_10_heading` format template in litassist/prompts/formats.yaml,
    # which is what extractfacts and updatefacts instruct the model to emit. A
    # one-sided rename here or there silently breaks the producer/consumer handoff;
    # tests/unit/test_case_facts_validator.py guards that the template validates.
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
        # optional non-alphabetic prefix (numbering, markdown bold/heading marks,
        # whitespace), then optional closing emphasis (`*`/`_`), then the real
        # terminator: a colon or end-of-line. This accepts every form extractfacts
        # produces - "1. **Parties**: ...", "**Parties:**", "PARTIES:",
        # "## Parties" - while rejecting prose that merely starts with the word,
        # including bolded prose like "**Parties** were notified" (the closing
        # `**` is consumed, but the trailing text is neither a colon nor EOL).
        pattern = r"^\s*[^a-zA-Z]*" + re.escape(heading) + r"[*_]*\s*(?::|$)"
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
    most recent by :func:`_case_facts_recency` - the timestamp embedded in the
    filename (e.g. ``case_facts_20260530_101500.txt``) where present, otherwise
    the file's modification time. So the newest timestamped version wins, but a
    freshly-edited plain ``case_facts.txt`` is not shadowed by an older
    timestamped file. The chosen file is printed.

    Returns:
        Path (relative to the launch directory) of the chosen case-facts file.

    Raises:
        click.ClickException: If no ``case_facts*.txt`` exists in the directory.
    """
    # A caseplan runner isolates a run under LITASSIST_OUTPUT_DIR; resolve from
    # there when set, else from the launch directory.
    search_dir = os.environ.get("LITASSIST_OUTPUT_DIR")
    pattern = (
        os.path.join(search_dir, "case_facts*.txt")
        if search_dir
        else "case_facts*.txt"
    )
    candidates = sorted(glob.glob(pattern))
    if not candidates:
        raise click.ClickException(
            "No case facts file provided and no case_facts*.txt found in the "
            "current directory. Pass the file explicitly, or run "
            "'litassist extractfacts' to create one."
        )

    # sorted() first so equal-recency ties resolve deterministically (lexically).
    chosen = max(candidates, key=_case_facts_recency)
    click.echo(info_message(f"Using case facts: {chosen}"))
    return chosen
