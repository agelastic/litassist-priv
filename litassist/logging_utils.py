"""
Logging utilities for LitAssist.

This module provides centralized logging functionality to avoid circular dependencies.
It handles both JSON and Markdown log formats with intelligent template selection.
"""

import os
import time
import json
import logging
import re
from typing import Dict, Optional, List, Tuple
from unittest.mock import Mock

import click
from litassist.prompts import PROMPTS


# ── Directory Setup ─────────────────────────────────────────
# Use current working directory for logs and outputs when running as global command
WORKING_DIR = os.getcwd()
LOG_DIR = os.path.join(WORKING_DIR, "logs")
OUTPUT_DIR = os.path.join(WORKING_DIR, "outputs")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# ── Logging Configuration ───────────────────────────────────
def setup_logging(verbose: bool = False) -> str:
    """
    Configure logging with file output and optional console output.

    All logs are saved to a timestamped file. Console output is only
    shown when verbose mode is enabled.

    Args:
        verbose: If True, also output logs to console

    Returns:
        Path to the log file
    """
    # Create timestamped log file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"litassist_{timestamp}.log")

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture everything

    # Clear existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # File handler - captures everything
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler - only if verbose
    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        # Simple format for console - just the message
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Configure specific loggers to appropriate levels
    # These will log to file always, console only if verbose
    for logger_name in ["httpx", "openai", "httpcore", "urllib3"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logging.INFO)

    # Log the startup
    logging.info(f"LitAssist logging initialized - verbose mode: {verbose}")
    logging.debug(f"Log file: {log_file}")

    return log_file


# ── JSON Sanitization ───────────────────────────────────────
def _sanitize_for_json(obj):
    """
    Recursively sanitize an object for JSON serialization.
    Handles Mock objects and other non-serializable types.
    Also filters out combined_content from research_analysis.
    """
    if isinstance(obj, Mock):
        return str(obj)
    elif isinstance(obj, dict):
        # Special handling for research_analysis with combined_content
        if "combined_content" in obj and all(
            key in obj for key in ["total_tokens", "total_words", "file_count"]
        ):
            # This looks like research_analysis - filter out combined_content
            return {
                k: _sanitize_for_json(v)
                for k, v in obj.items()
                if k != "combined_content"
            }
        else:
            return {k: _sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        # For objects with attributes, convert to dict representation
        return _sanitize_for_json(obj.__dict__)
    else:
        # For primitive types and strings
        return obj


# ── Main Logging Function ───────────────────────────────────
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
            sanitized_payload = _sanitize_for_json(payload)
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
            if tag == "citation_verification_session" or "citations_found" in payload:
                _write_citation_verification_markdown(f, tag, ts, payload)
            elif tag == "citation_validation" or "validate_citation_patterns" in str(
                payload.get("method", "")
            ):
                _write_citation_validation_markdown(f, tag, ts, payload)
            elif tag == "austlii_http_validation" or "check_url_exists" in str(
                payload.get("method", "")
            ):
                _write_http_validation_markdown(f, tag, ts, payload)
            elif tag == "austlii_search_validation":
                _write_search_validation_markdown(f, tag, ts, payload)
            elif (
                tag.startswith("llm_")
                or tag.startswith("cove_")
                or "messages_sent" in payload
                or (isinstance(payload.get("messages"), list) and payload.get("model"))
            ):
                # LLM message logs (includes both sent messages and responses)
                _write_llm_messages_markdown(f, tag, ts, payload)
            elif "response" in payload or "inputs" in payload:
                # Standard command output format
                _write_command_output_markdown(f, tag, ts, payload)
            else:
                # Generic format for unknown log types
                _write_generic_markdown(f, tag, ts, payload)

            logging.debug(f"Markdown log saved: {md_path}")
    except IOError as e:
        raise click.ClickException(f"Failed to save Markdown log {md_path}: {e}")


# ── Markdown Writing Functions ──────────────────────────────
def _write_citation_verification_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for citation verification logs."""
    f.write(f"# {tag} — {ts}\n\n")

    # Summary section
    f.write("## Summary\n\n")
    f.write(f"- **Method**: `{payload.get('method', 'N/A')}`  \n")
    f.write(
        f"- **Input Text Length**: {payload.get('input_text_length', 0)} characters  \n"
    )
    f.write(f"- **Citations Found**: {payload.get('citations_found', 0)}  \n")
    f.write(f"- **Verified**: {payload.get('citations_verified', 0)}  \n")
    f.write(f"- **Unverified**: {payload.get('citations_unverified', 0)}  \n")
    f.write(f"- **Processing Time**: {payload.get('processing_time_ms', 'N/A')} ms  \n")
    f.write(f"- **Timestamp**: {payload.get('timestamp', ts)}  \n\n")

    # Verified citations
    verified = payload.get("verified_citations", [])
    if verified:
        f.write("## Verified Citations\n\n")
        for citation in verified:
            f.write(f"- `{citation}`  \n")
        f.write("\n")

    # Unverified citations
    unverified = payload.get("unverified_citations", [])
    if unverified:
        f.write("## Unverified Citations\n\n")
        for item in unverified:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                citation, reason = item[0], item[1]
                f.write(f"- `{citation}`  \n")
                f.write(f"  - **Reason**: {reason}  \n")
            else:
                f.write(f"- `{item}`  \n")
        f.write("\n")

    # Settings
    f.write("## Settings\n\n")
    settings = payload.get("settings", {})
    f.write(f"- **Strict Mode**: {settings.get('strict_mode', 'N/A')}  \n")
    f.write(f"- **Cache Used**: {settings.get('cache_used', 'N/A')}  \n")
    f.write(f"- **API Calls Made**: {settings.get('api_calls_made', 'N/A')}  \n\n")

    # Errors if any
    errors = payload.get("errors", [])
    if errors:
        f.write("## Errors\n\n")
        for error in errors:
            f.write(f"- {error}  \n")
        f.write("\n")


def _write_citation_validation_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for citation validation logs."""
    f.write(f"# {tag} — {ts}\n\n")
    f.write("## Summary\n\n")
    f.write(
        f"- **Method**: `{payload.get('method', 'validate_citation_patterns')}`  \n"
    )
    issues = payload.get("issues", [])
    f.write(f"- **Issues Found**: {len(issues)}  \n")
    f.write(f"- **Online Enabled**: {payload.get('online_enabled', False)}  \n")
    f.write(f"- **Timestamp**: {payload.get('timestamp', ts)}  \n\n")

    if issues:
        f.write("## Issues\n\n")
        for issue in issues:
            f.write(f"- {issue}  \n")
        f.write("\n")


def _write_http_validation_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for HTTP validation logs."""
    f.write(f"# {tag} — {ts}\n\n")
    f.write("## HTTP Validation\n\n")
    f.write(f"- **Method**: `{payload.get('method', 'check_url_exists')}`  \n")
    f.write(f"- **URL**: `{payload.get('url', 'N/A')}`  \n")
    f.write(f"- **Status Code**: {payload.get('status_code', 'N/A')}  \n")
    f.write(f"- **Valid**: {payload.get('valid', False)}  \n")
    if payload.get("error"):
        f.write(f"- **Error**: {payload.get('error')}  \n")
    f.write("\n")


def _write_search_validation_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for search validation logs."""
    f.write(f"# {tag} — {ts}\n\n")
    f.write("## Search Validation\n\n")
    f.write("- **Method**: `search_austlii`  \n")
    f.write(f"- **Citation**: `{payload.get('citation', 'N/A')}`  \n")
    f.write(f"- **Found**: {payload.get('found', False)}  \n")
    if payload.get("url"):
        f.write(f"- **URL**: {payload.get('url')}  \n")
    f.write("\n")


def _write_command_output_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for command output logs."""
    f.write(f"# {tag} — {ts}\n\n")

    # Inputs section
    if "inputs" in payload:
        f.write("## Inputs\n\n")
        inputs = payload["inputs"]
        if isinstance(inputs, dict):
            for key, value in inputs.items():
                # Special handling for complex data structures
                if isinstance(value, dict):
                    # Check for research_analysis with combined_content
                    if key == "research_analysis" and "combined_content" in value:
                        # Only log metadata, not the massive content
                        f.write(f"- **{key}**:\n")
                        f.write(
                            f"  - Total tokens: {value.get('total_tokens', 'N/A')}\n"
                        )
                        f.write(f"  - Total words: {value.get('total_words', 'N/A')}\n")
                        f.write(f"  - File count: {value.get('file_count', 'N/A')}\n")
                        f.write(
                            f"  - Exceeds threshold: {value.get('exceeds_threshold', 'N/A')}\n"
                        )
                    else:
                        # Format dict as JSON code block
                        f.write(
                            f"- **{key}**:\n```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```\n"
                        )
                elif isinstance(value, list):
                    if len(value) > 10:
                        # For long lists, show count and first few items
                        f.write(f"- **{key}**: {len(value)} items\n")
                        f.write(f"  First 3: {value[:3]}\n")
                    else:
                        # Short lists can be shown inline
                        f.write(f"- **{key}**: {value}  \n")
                elif isinstance(value, str) and len(value) > 1000:
                    # Truncate very long strings
                    f.write(
                        f"- **{key}**: {value[:500]}... (truncated, {len(value)} chars total)  \n"
                    )
                else:
                    # Simple values
                    f.write(f"- **{key}**: {value}  \n")
        else:
            f.write(f"{inputs}  \n")
        f.write("\n")

    # Response section
    if "response" in payload:
        f.write("## Response\n\n")
        response = payload["response"]
        # Handle long responses
        if isinstance(response, str) and len(response) > 10000:
            f.write(
                f"{response[:10000]}\n\n... (truncated, {len(response)} total characters)\n"
            )
        else:
            f.write(f"{response}\n")
        f.write("\n")

    # Usage statistics
    if "usage" in payload:
        f.write("## Usage Statistics\n\n")
        usage = payload["usage"]
        if isinstance(usage, dict):
            for key, value in usage.items():
                f.write(f"- **{key}**: {value}  \n")
        f.write("\n")


def _write_llm_messages_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for LLM message logs."""
    f.write(f"# {tag} — {ts}\n\n")

    # Model information
    f.write("## Model Information\n\n")
    f.write(f"- **Model**: {payload.get('model', 'N/A')}\n")
    f.write(f"- **Timestamp**: {payload.get('timestamp', ts)}\n")
    if "correlation_id" in payload:
        f.write(f"- **Correlation ID**: {payload['correlation_id']}\n")
    if "command_context" in payload:
        f.write(f"- **Context**: {payload['command_context']}\n")
    f.write("\n")

    # Messages - check both 'messages' and 'messages_sent' for compatibility
    messages = payload.get("messages", payload.get("messages_sent", []))
    if messages:
        f.write("## Messages Sent\n\n")
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "system":
                f.write("### System Message\n\n")
            elif role == "user":
                f.write("### User Message\n\n")
            elif role == "assistant":
                f.write("### Assistant Message\n\n")
            else:
                f.write(f"### {role.title()} Message\n\n")

            # Handle long content
            if len(content) > 50000:
                f.write(
                    f"{content[:50000]}\n\n[... truncated, {len(content)} total characters ...]\n\n"
                )
            else:
                f.write(f"{content}\n\n")

    # LLM Response - the actual output from the model
    response = payload.get("response")
    if response:
        f.write("## LLM Response\n\n")
        # Handle very long responses (some can be 50K+ chars)
        if len(response) > 100000:
            f.write(
                f"{response[:100000]}\n\n[... truncated, {len(response)} total characters ...]\n\n"
            )
        else:
            f.write(f"{response}\n\n")

    # Parameters
    params = payload.get("params", {})
    if params:
        f.write("## Parameters\n\n")
        f.write("| Parameter | Value |\n")
        f.write("|-----------|-------|\n")
        for key, value in params.items():
            f.write(f"| {key} | {value} |\n")
        f.write("\n")

    # Usage stats if present
    usage = payload.get("usage", {})
    if usage:
        f.write("## Token Usage\n\n")
        for key, value in usage.items():
            f.write(f"- **{key}**: {value}\n")
        f.write("\n")


def _format_dict_as_markdown(d: dict, indent: int = 0) -> str:
    """Recursively format a dictionary as markdown lists."""
    lines = []
    prefix = "  " * indent + "- "

    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}**{key}**:")
            lines.append(_format_dict_as_markdown(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}**{key}**:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(_format_dict_as_markdown(item, indent + 1))
                else:
                    lines.append(f"  {'  ' * indent}- {item}")
        else:
            lines.append(f"{prefix}**{key}**: {value}")

    return "\n".join(lines)


def _write_generic_markdown(f, tag: str, ts: str, payload: dict):
    """Write pure markdown for unknown log types - no JSON."""
    f.write(f"# {tag} — {ts}\n\n")
    f.write("## Log Data\n\n")

    # Convert the payload to pure markdown format
    if payload:
        markdown_content = _format_dict_as_markdown(payload)
        f.write(markdown_content)
        f.write("\n")
    else:
        f.write("No data available.\n")


# ── Command Output Function ─────────────────────────────────
def save_command_output(
    command_name: str,
    content: str,
    query_or_slug: str,
    metadata: Optional[Dict[str, str]] = None,
    critique_sections: Optional[List[Tuple[str, str]]] = None,
) -> str:
    """
    Save command output with standard format.

    Args:
        command_name: Name of the command (e.g., 'strategy', 'draft')
        content: The main content to save
        query_or_slug: Query string or slug for filename generation
        metadata: Optional dict of metadata to include in header
        critique_sections: Optional list of (title, critique_content) tuples for AI critiques

    Returns:
        Path to the saved output file
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Create filename based on whether a slug is provided
    slug = ""
    if query_or_slug:  # Non-empty slug means normal usage
        sanitized_slug = re.sub(r"[^\w\s-]", "", query_or_slug.lower())
        slug = re.sub(r"[-\s]+", "_", sanitized_slug)[:40].strip("_")

    if slug:
        output_file = os.path.join(OUTPUT_DIR, f"{command_name}_{slug}_{timestamp}.txt")
    else:
        # This handles both cases: empty query_or_slug, or a slug that becomes empty after sanitization.
        output_file = os.path.join(OUTPUT_DIR, f"{command_name}_{timestamp}.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        # Standard header
        f.write(f"{command_name.replace('_', ' ').title()}\n")

        # Add metadata if provided
        if metadata:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")

        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 80 + "\n\n")
        f.write(content)

        # Append critique sections if provided
        if critique_sections:
            f.write("\n\n" + "=" * 80 + "\n")
            f.write("AI CRITIQUE & VERIFICATION\n")
            f.write("=" * 80 + "\n\n")

            for title, critique_content in critique_sections:
                f.write(f"## {title}\n\n")
                f.write(critique_content)
                f.write("\n\n")

    return output_file
