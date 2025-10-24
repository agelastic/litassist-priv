"""
Logging utilities for LitAssist.

This module provides centralized logging functionality to avoid circular dependencies.
It handles both JSON and Markdown log formats with intelligent template selection.
"""

import os
import time
import json
import logging
import click
from typing import Dict

from .config import setup_logging as setup_logging
from .json_utils import sanitize_for_json
from .output_saver import save_command_output as save_command_output
from .task_events import log_task_event as _log_task_event_impl
from .markdown_writers import (
    write_citation_verification_markdown,
    write_citation_validation_markdown,
    write_http_validation_markdown,
    write_search_validation_markdown,
    write_command_output_markdown,
    write_llm_messages_markdown,
    write_fetch_log_markdown,
    write_generic_markdown,
    format_dict_as_markdown as format_dict_as_markdown,
)


#    Directory Setup
# Use current working directory for logs and outputs when running as global command
WORKING_DIR = os.getcwd()
LOG_DIR = os.path.join(WORKING_DIR, "logs")
OUTPUT_DIR = os.path.join(WORKING_DIR, "outputs")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


#    Main Logging Function
def save_log(tag: str, payload: dict):
    """
    Save an audit log under logs/ in either JSON or Markdown format.

    Intelligently detects log type and formats markdown appropriately for:
    - Citation verification/validation logs
    - HTTP validation logs
    - Command output logs
    - Generic/unknown log types

    Args:
        tag: A string identifier for the log (e.g., command name).
        payload: Dictionary containing log data including inputs, response, and usage statistics.

    Raises:
        click.ClickException: If there's an error writing the log file.
    """
    from click import get_current_context
    from litassist.config import get_config
    from litassist.prompts import PROMPTS

    ts = time.strftime("%Y%m%d-%H%M%S")
    ctx = get_current_context(silent=True)

    # Try to get log format from click context first, then CONFIG, then default to json
    if ctx and ctx.obj and "log_format" in ctx.obj:
        log_format = ctx.obj["log_format"]
    else:
        # Fall back to CONFIG setting when not in a click context (e.g., during tests)
        config = get_config()
        log_format = config.log_format if config else "json"

    # JSON logging
    if log_format == "json":
        path = os.path.join(LOG_DIR, f"{tag}_{ts}.json")
        try:
            # Sanitize payload for JSON serialization (handle Mock objects)
            sanitized_payload = sanitize_for_json(payload)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(sanitized_payload, f, ensure_ascii=False, indent=2)
            logging.debug(f"JSON log saved: {path}")
        except IOError as e:
            raise click.ClickException(
                PROMPTS.get(
                    "system_feedback.errors.file.save_json_failed",
                    path=path,
                    error=str(e),
                )
            )
        return

    # Markdown logging with intelligent template selection
    md_path = os.path.join(LOG_DIR, f"{tag}_{ts}.md")
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            # Detect log type and use appropriate formatter
            if tag == "fetch_attempt":
                write_fetch_log_markdown(f, tag, ts, payload)
            elif tag == "citation_verification_session" or "citations_found" in payload:
                write_citation_verification_markdown(f, tag, ts, payload)
            elif tag == "citation_validation" or "validate_citation_patterns" in str(
                payload.get("method", "")
            ):
                write_citation_validation_markdown(f, tag, ts, payload)
            elif tag == "austlii_http_validation" or "check_url_exists" in str(
                payload.get("method", "")
            ):
                write_http_validation_markdown(f, tag, ts, payload)
            elif tag == "austlii_search_validation":
                write_search_validation_markdown(f, tag, ts, payload)
            elif (
                tag.startswith("llm_")
                or tag.startswith("cove_")
                or "messages_sent" in payload
                or (isinstance(payload.get("messages"), list) and payload.get("model"))
            ):
                # LLM message logs (includes both sent messages and responses)
                write_llm_messages_markdown(f, tag, ts, payload)
            elif "response" in payload or "inputs" in payload:
                # Standard command output format
                write_command_output_markdown(f, tag, ts, payload)
            else:
                # Generic format for unknown log types
                write_generic_markdown(f, tag, ts, payload)

            logging.debug(f"Markdown log saved: {md_path}")
    except IOError as e:
        raise click.ClickException(f"Failed to save Markdown log {md_path}: {e}")


#    Wrapper for log_task_event with save_log injection
def log_task_event(
    command: str, stage: str, event: str, message: str = "", details: Dict = None
):
    """
    Wrapper around log_task_event that injects save_log to avoid circular imports.

    Args:
        command: Command name
        stage: Stage name
        event: Event type
        message: Event message
        details: Optional additional details
    """
    _log_task_event_impl(command, stage, event, message, details, save_log_fn=save_log)
