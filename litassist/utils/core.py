"""
Core utilities for LitAssist.

This module provides core utility functions including timing decorators,
heartbeat functionality, completion messages, and other general utilities
used throughout LitAssist.
"""

import os
import re
import time
import logging
import threading
import functools
import click
from typing import Callable, Dict, Optional, Any

from litassist.utils.formatting import (
    success_message,
    saved_message,
    info_message,
    stats_message,
    tip_message,
)


# ── Logging Setup ───────────────────────────────────────────
# Logging is now configured centrally in logging_utils.setup_logging()


def timed(func: Callable) -> Callable:
    """
    Decorator to measure and log execution time of functions.

    Args:
        func: The function to time.

    Returns:
        A wrapped function that includes timing measurements.

    Example:
        @timed
        def my_function():
            # Function code
            pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            end_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            # Add timing info to the result if it's a tuple with a dict
            if (
                isinstance(result, tuple)
                and len(result) >= 2
                and isinstance(result[1], dict)
            ):
                content, usage_dict = result[0], result[1]
                if "timing" not in usage_dict:
                    usage_dict["timing"] = {}
                usage_dict["timing"].update(
                    {
                        "start_time": start_timestamp,
                        "end_time": end_timestamp,
                        "duration_seconds": round(duration, 3),
                    }
                )
                return content, usage_dict

            # Just log the timing info
            logging.debug(
                f"Function {func.__name__} execution time: {duration:.3f} seconds"
            )
            logging.debug(f"  - Started: {start_timestamp}")
            logging.debug(f"  - Ended: {end_timestamp}")

            return result

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logging.debug(
                f"Function {func.__name__} failed after {duration:.3f} seconds"
            )
            raise e

    return wrapper


def heartbeat(interval: Optional[int] = None):
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
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
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
                while not done.is_set():
                    # Suppress during pytest runs
                    if not os.environ.get("PYTEST_CURRENT_TEST"):
                        click.echo("…still working, please wait…", err=True)
                    time.sleep(actual_interval)

            t = threading.Thread(target=ping, daemon=True)
            t.start()
            try:
                return fn(*args, **kwargs)
            finally:
                done.set()
                t.join(timeout=0)

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
        # Orthodox strategies use "### 1. **Name**" format
        parsed["orthodox_count"] = len(
            re.findall(r"^###\s+\d+\.", orthodox_text, re.MULTILINE)
        )

    # Find UNORTHODOX STRATEGIES section - look for content until next ## header at line start or end
    unorthodox_match = re.search(
        r"## UNORTHODOX STRATEGIES.*?\n(.*?)(?=^## |\Z)",
        strategies_text,
        re.DOTALL | re.MULTILINE,
    )
    if unorthodox_match:
        unorthodox_text = unorthodox_match.group(1)
        # Unorthodox strategies use "### Strategy 1:" format
        parsed["unorthodox_count"] = len(
            re.findall(r"^###\s+Strategy\s+\d+:", unorthodox_text, re.MULTILINE)
        )

    # Find MOST LIKELY TO SUCCEED section - look for content until === divider or end
    likely_match = re.search(
        r"## MOST LIKELY TO SUCCEED.*?\n(.*?)(?=^===|\Z)",
        strategies_text,
        re.DOTALL | re.MULTILINE,
    )
    if likely_match:
        likely_text = likely_match.group(1)
        parsed["most_likely_count"] = len(
            re.findall(r"^\d+\.", likely_text, re.MULTILINE)
        )

    return parsed


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
