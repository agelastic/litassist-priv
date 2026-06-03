"""
Core utilities for LitAssist.

This module provides core utility functions including timing decorators,
heartbeat functionality, completion messages, and other general utilities
used throughout LitAssist.
"""

import os
import re
import logging
import threading
import functools
import click
from typing import Dict, Optional, Any

from litassist.utils.formatting import (
    success_message,
    saved_message,
    info_message,
    stats_message,
    tip_message,
)


# --- Logging Setup ---
# Logging is now configured centrally in logging_utils.setup_logging()


def heartbeat(interval: Optional[float] = None):
    """
    Decorator to emit a heartbeat message every `interval` seconds while a long-running function executes.

    Args:
        interval: Number of seconds between heartbeat messages. If None, uses config value. Defaults to None.

    Returns:
        A decorator function that wraps the target function with heartbeat functionality.

    Example:
        @heartbeat(60)  # Explicit interval
        def long_running_function():
            pass
        
        @heartbeat()  # Uses config.yaml value
        def another_function():
            pass
    """

    def decorator(fn):
        """Apply heartbeat wrapper to the target function."""
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            """Execute function with background heartbeat thread."""
            # Determine interval at runtime
            actual_interval = interval
            if actual_interval is None:
                try:
                    from litassist.config import get_config
                    config_interval = get_config().heartbeat_interval
                    # Ensure we have a valid number (not a Mock object from tests)
                    if isinstance(config_interval, (int, float)):
                        actual_interval = config_interval
                    else:
                        actual_interval = 20  # Fallback if Mock or invalid
                except Exception:
                    actual_interval = 20  # Fallback to Config class default
            
            done = threading.Event()

            def ping():
                """Emit periodic heartbeat messages until signalled to stop."""
                while not done.is_set():
                    try:
                        # Suppress during pytest runs
                        if not os.environ.get("PYTEST_CURRENT_TEST"):
                            click.echo("...still working, please wait...", err=True)
                    except Exception:
                        logging.debug("Heartbeat thread: failed to emit message, stopping")
                        break
                    done.wait(timeout=actual_interval)

            t = threading.Thread(target=ping, daemon=True)
            t.start()
            try:
                return fn(*args, **kwargs)
            finally:
                done.set()
                t.join(timeout=2)
                if t.is_alive():
                    logging.debug("Heartbeat thread did not stop within 2 seconds")

        return wrapper

    return decorator


def show_command_completion(
    command_name: str,
    output_file: str,
    extra_files: Optional[Dict[str, str]] = None,
    stats: Optional[Dict[str, Any]] = None,
    ctx: Optional[Any] = None,
):
    """
    Display standard completion message for commands.

    Args:
        command_name: Name of the command
        output_file: Path to the main output file
        extra_files: Optional dict of label->path for additional files
        stats: Optional statistics to display
        ctx: Optional Click context containing log file info
    """
    success_msg = success_message(f"{command_name.replace('_', ' ').title()} complete!")
    click.echo(f"\n{success_msg}")
    click.echo(saved_message(f'Output saved to: "{output_file}"'))

    if extra_files:
        for label, path in extra_files.items():
            click.echo(info_message(f'{label}: open "{path}"'))

    if stats:
        click.echo(f"\n{stats_message('Statistics:')}")
        for key, value in stats.items():
            click.echo(f"   {key}: {value}")

    # Show log file location if verbose mode and context available
    if ctx and hasattr(ctx, "obj") and ctx.obj:
        if ctx.obj.get("verbose") and ctx.obj.get("log_file"):
            click.echo(info_message(f"Debug logs saved to: {ctx.obj['log_file']}"))

    tip_msg = tip_message(f'View full output: open "{output_file}"')
    click.echo(f"\n{tip_msg}")


# Verifier replies place the corrected document under this header. The match is
# deliberately tolerant of light formatting drift (optional #/##/### or **bold**,
# "and"/"&", case, trailing colon) because verifier models vary, while still
# requiring the exact phrase on its own line so a stray mention never mis-triggers.
_VERIFIED_DOCUMENT_HEADER = re.compile(
    r"^\s*#{0,3}\s*\*{0,2}\s*Verified\s+(?:and|&)\s+Corrected\s+Document\s*\*{0,2}\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def extract_verified_document(text: str, fallback: str) -> tuple[str, bool]:
    """Pull the corrected document out of a verifier reply.

    Verifier prompts ask the model to return the corrected text under a
    "## Verified and Corrected Document" header. Returns (document_body, True)
    when that header is found, else (fallback, False) so callers PRESERVE the
    pre-verification content rather than overwriting it with the verifier's
    freeform reply. The header match tolerates light formatting variants (see
    ``_VERIFIED_DOCUMENT_HEADER``) but stays line-anchored to avoid mis-extraction.
    """
    match = _VERIFIED_DOCUMENT_HEADER.search(text)
    if not match:
        return fallback, False
    return text[match.end():].strip(), True


def parse_strategies_file(strategies_text: str) -> dict:
    """
    Parse the strategies.txt file to extract basic counts and metadata.

    Since we pass the full content to the LLM anyway, we just need rough counts
    for the user display, not detailed parsing.

    Args:
        strategies_text: Content of the strategies.txt file.

    Returns:
        Dictionary containing basic strategies information.
    """
    parsed = {
        "metadata": {},
        "orthodox_count": 0,
        "unorthodox_count": 0,
        "most_likely_count": 0,
        "raw_content": strategies_text,
    }

    # Extract metadata from header comments
    metadata_match = re.search(r"# Side: (.+)\n# Area: (.+)", strategies_text)
    if metadata_match:
        parsed["metadata"]["side"] = metadata_match.group(1).strip()
        parsed["metadata"]["area"] = metadata_match.group(2).strip()

    # Extract and count each section separately to avoid cross-contamination

    # Find ORTHODOX STRATEGIES section - look for content until next ## header at line start or end
    orthodox_match = re.search(
        r"## ORTHODOX STRATEGIES.*?\n(.*?)(?=^## |\Z)",
        strategies_text,
        re.DOTALL | re.MULTILINE,
    )
    if orthodox_match:
        orthodox_text = orthodox_match.group(1)
        # Orthodox strategies use "### Strategy 1:" or "### 1." format
        parsed["orthodox_count"] = len(
            re.findall(r"^###\s+(?:Strategy\s+)?\d+[:.]", orthodox_text, re.MULTILINE)
        )

    # Find UNORTHODOX STRATEGIES section - look for content until next ## header at line start or end
    unorthodox_match = re.search(
        r"## UNORTHODOX STRATEGIES.*?\n(.*?)(?=^## |\Z)",
        strategies_text,
        re.DOTALL | re.MULTILINE,
    )
    if unorthodox_match:
        unorthodox_text = unorthodox_match.group(1)
        # Unorthodox strategies use "### Strategy 1:" or "### 1." format
        parsed["unorthodox_count"] = len(
            re.findall(r"^###\s+(?:Strategy\s+)?\d+[:.]", unorthodox_text, re.MULTILINE)
        )

    # Find MOST LIKELY TO SUCCEED section - look for content until === divider or end
    likely_match = re.search(
        r"## MOST LIKELY TO SUCCEED.*?\n(.*?)(?=^===|\Z)",
        strategies_text,
        re.DOTALL | re.MULTILINE,
    )
    if likely_match:
        likely_text = likely_match.group(1)
        # The analysis prompt formats each entry as "**N. Title**" (bold), so allow
        # an optional leading "**" before the number; bare "N." still matches too.
        parsed["most_likely_count"] = len(
            re.findall(r"^(?:\*\*)?\d+\.", likely_text, re.MULTILINE)
        )

    return parsed


def parse_strategies_files(named_contents) -> dict:
    """Parse and merge several brainstorm strategy files into one summary dict.

    strategy --strategies accepts multiple files (e.g. the dual-brainstorm
    creative AND research sets). Each is parsed individually with
    parse_strategies_file, then the three counts are SUMMED, the side/area
    metadata from the first file that carries it is kept (the sets share a case,
    so this is robust to one file lacking the headers), and the raw bodies are
    joined under the standard '=== label ===' separator for the LLM prompt. The
    return shape matches parse_strategies_file, so downstream code is unchanged.

    Args:
        named_contents: Iterable of (label, text) pairs; label is the filename
            shown in the '=== label ===' separator.

    Returns:
        Dict with summed orthodox/unorthodox/most_likely counts, the first file's
        metadata, and the combined labelled text in raw_content.
    """
    merged = {
        "metadata": {},
        "orthodox_count": 0,
        "unorthodox_count": 0,
        "most_likely_count": 0,
        "raw_content": "",
    }
    parts = []
    for label, text in named_contents:
        parsed = parse_strategies_file(text)
        merged["orthodox_count"] += parsed["orthodox_count"]
        merged["unorthodox_count"] += parsed["unorthodox_count"]
        merged["most_likely_count"] += parsed["most_likely_count"]
        if not merged["metadata"] and parsed["metadata"]:
            merged["metadata"] = parsed["metadata"]
        parts.append(f"=== {label} ===\n{text}")
    merged["raw_content"] = "\n\n".join(parts)
    return merged


def validate_side_area_combination(side: str, area: str):
    """
    Validate side/area combinations and display warnings for incompatible pairs.

    Args:
        side: The side being represented (plaintiff/defendant/accused/respondent)
        area: The legal area (criminal/civil/family/commercial/administrative)
    """
    valid_combinations = {
        "criminal": ["accused"],
        "civil": ["plaintiff", "defendant"],
        "family": ["plaintiff", "defendant", "respondent"],
        "commercial": ["plaintiff", "defendant"],
        "administrative": ["plaintiff", "defendant", "respondent"],
    }

    if area in valid_combinations and side not in valid_combinations[area]:
        warning_msg = click.style(
            f"Warning: '{side}' is not typically used in {area} matters. ",
            fg="yellow",
            bold=True,
        )
        suggestion = click.style(
            f"Standard options for {area} are: {', '.join(valid_combinations[area])}\n",
            fg="yellow",
        )
        click.echo(warning_msg + suggestion)

        # Add specific warnings for common mistakes
        if side == "plaintiff" and area == "criminal":
            click.echo(
                click.style(
                    "Note: Criminal cases use 'accused' instead of 'plaintiff/defendant'\n",
                    fg="yellow",
                )
            )
        elif side == "accused" and area != "criminal":
            click.echo(
                click.style(
                    "Note: 'Accused' is typically only used in criminal matters\n",
                    fg="yellow",
                )
            )
