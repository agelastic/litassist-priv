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
    `case_facts.md` (which carries no filename timestamp).
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
        # whitespace), then optional closing emphasis (`*`/`_`), an OPTIONAL
        # parenthetical qualifier (extractfacts sometimes emits e.g.
        # "Key Events (Chronological)", "Opposing Arguments (DTL's Position)"),
        # more optional emphasis, then the real terminator: a colon or
        # end-of-line. This accepts every form extractfacts produces -
        # "1. **Parties**: ...", "**Parties:**", "PARTIES:", "## Parties",
        # "3. **Key Events (Chronological)**:" - while rejecting prose that merely
        # starts with the word, like "**Parties** were notified" (the trailing
        # text is neither a parenthetical+terminator, a colon, nor EOL).
        pattern = (
            r"^\s*[^a-zA-Z]*"
            + re.escape(heading)
            + r"[*_]*\s*(?:\([^)]*\))?\s*[*_]*\s*(?::|$)"
        )
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            missing_headings.append(heading)

    if missing_headings:
        click.echo(f"Missing required headings: {', '.join(missing_headings)}")
        click.echo("Note: Headings are now case-insensitive and can have punctuation.")
        return False

    return True


# --- Matter type -----------------------------------------------------------
#
# matter_type lives as a "Matter type:" line under the Jurisdiction heading of
# case_facts (see the case_facts_10_heading contract in formats.yaml). It drives
# the matter-type posture prepended to the framing commands' system prompts.
# Keep KNOWN_MATTER_TYPES in sync with the keys in
# litassist/prompts/matter_types.yaml.
KNOWN_MATTER_TYPES = (
    "civil",
    "criminal",
    "family",
    "commercial",
    "disciplinary",
    "foi",
    "administrative",
)
DEFAULT_MATTER_TYPE = "civil"

# One delimited line, e.g. "Matter type: disciplinary" (any leading numbering/
# emphasis, case-insensitive). Single regex - no prose mining.
_MATTER_TYPE_RE = re.compile(
    # The `[*_]*` before the value tolerates a markdown-emphasised value
    # (e.g. "Matter type: **disciplinary**"), mirroring the emphasis already
    # tolerated on the key.
    r"(?im)^\s*[^a-zA-Z]*matter\s+type[*_]*\s*:\s*[*_]*([A-Za-z][A-Za-z-]*)"
)


def read_matter_type(text: str) -> str | None:
    """Return the lower-cased matter_type from a case_facts string, or None."""
    if not text:
        return None
    match = _MATTER_TYPE_RE.search(text)
    return match.group(1).strip().lower() if match else None


def _warn_for(reason: str, remedy: str) -> str:
    return (
        f"{reason} - assuming '{DEFAULT_MATTER_TYPE}' (litigation) posture. "
        f"{remedy} (one of: " + ", ".join(KNOWN_MATTER_TYPES) + ") for accurate framing."
    )


_FACTS_REMEDY = "Set a 'Matter type: <value>' line in case facts (or re-run extractfacts)"
_FLAG_REMEDY = "Pass --matter-type <value>"


def resolve_matter_type(text: str) -> tuple[str, str | None]:
    """Resolve matter_type from case_facts text.

    Returns (matter_type, warning). Defaults to civil with a warning when the
    line is absent or carries an unknown value - never raises, never blocks
    (Phase 1 is default-civil-with-warning, not a hard gate).
    """
    raw = read_matter_type(text)
    if raw is None:
        return DEFAULT_MATTER_TYPE, _warn_for(
            "No 'Matter type:' line in case facts", _FACTS_REMEDY
        )
    if raw not in KNOWN_MATTER_TYPES:
        return DEFAULT_MATTER_TYPE, _warn_for(
            f"Unknown matter type '{raw}'", _FACTS_REMEDY
        )
    return raw, None


def normalise_matter_type(value: str | None) -> tuple[str, str | None]:
    """Resolve matter_type from an explicit value (e.g. a CLI flag).

    Used by counselnotes, which takes arbitrary files and has no case_facts to
    read. Same default-civil-with-warning contract as resolve_matter_type.
    """
    if value is None:
        return DEFAULT_MATTER_TYPE, _warn_for("No --matter-type given", _FLAG_REMEDY)
    raw = value.strip().lower()
    if raw not in KNOWN_MATTER_TYPES:
        return DEFAULT_MATTER_TYPE, _warn_for(
            f"Unknown matter type '{raw}'", _FLAG_REMEDY
        )
    return raw, None


def matter_type_posture(matter_type: str) -> str:
    """Return the posture string for a matter_type (falls back to civil)."""
    from litassist.prompts import PROMPTS

    mt = matter_type if matter_type in KNOWN_MATTER_TYPES else DEFAULT_MATTER_TYPE
    return PROMPTS.get(f"matter_types.{mt}.posture")


def resolve_case_facts_file() -> str:
    """
    Pick the case-facts file to use when one was not given on the command line.

    Globs ``case_facts*.{txt,md}`` in the current (launch) directory and returns
    the most recent by :func:`_case_facts_recency` - the timestamp embedded in the
    filename (e.g. ``case_facts_20260530_101500.md``) where present, otherwise
    the file's modification time. So the newest timestamped version wins, but a
    freshly-edited plain ``case_facts.md`` is not shadowed by an older
    timestamped file. The chosen file is printed.

    Returns:
        Path (relative to the launch directory) of the chosen case-facts file.

    Raises:
        click.ClickException: If no ``case_facts*.{txt,md}`` exists in the directory.
    """
    # A caseplan runner isolates a run under LITASSIST_OUTPUT_DIR; resolve from
    # there when set, else from the launch directory.
    search_dir = os.environ.get("LITASSIST_OUTPUT_DIR")
    # Match both the current .md outputs and legacy .txt case-facts files.
    patterns = ["case_facts*.txt", "case_facts*.md"]
    if search_dir:
        patterns = [os.path.join(search_dir, p) for p in patterns]
    candidates = sorted({c for p in patterns for c in glob.glob(p)})
    if not candidates:
        raise click.ClickException(
            "No case facts file provided and no case_facts*.md (or .txt) found in "
            "the current directory. Pass the file explicitly, or run "
            "'litassist extractfacts' to create one."
        )

    # sorted() first so equal-recency ties resolve deterministically (lexically).
    chosen = max(candidates, key=_case_facts_recency)
    click.echo(info_message(f"Using case facts: {chosen}"))
    return chosen
