"""
Utility functions for LitAssist.

This module provides helper functions and decorators used throughout the LitAssist application,
including timing, logging, document processing, embedding generation, and legal reasoning traces.
"""

import os
import time
import json
import logging
import threading
import functools
import re
from typing import List, Any, Callable, Dict, Optional

import click
import openai
from pypdf import PdfReader

from litassist.prompts import PROMPTS


# ── Terminal Colors ─────────────────────────────────────────
class Colors:
    """ANSI color codes for terminal output."""

    # Color codes
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def colored_message(prefix: str, message: str, color: str) -> str:
    """Format a message with colored prefix."""
    return f"{color}{prefix}{Colors.RESET} {message}"


def success_message(message: str) -> str:
    """Format a success message with green [SUCCESS] prefix."""
    return colored_message("[SUCCESS]", message, Colors.GREEN)


def warning_message(message: str) -> str:
    """Format a warning message with yellow [WARNING] prefix."""
    return colored_message("[WARNING]", message, Colors.YELLOW)


def error_message(message: str) -> str:
    """Format an error message with red [ERROR] prefix."""
    return colored_message("[ERROR]", message, Colors.RED)


def info_message(message: str) -> str:
    """Format an info message with blue [INFO] prefix."""
    return colored_message("[INFO]", message, Colors.BLUE)


def stats_message(message: str) -> str:
    """Format a stats message with cyan [STATS] prefix."""
    return colored_message("[STATS]", message, Colors.CYAN)


def tip_message(message: str) -> str:
    """Format a tip message with magenta [TIP] prefix."""
    return colored_message("[TIP]", message, Colors.MAGENTA)


def saved_message(message: str) -> str:
    """Format a saved file message with blue [SAVED] prefix."""
    return colored_message("[SAVED]", message, Colors.BLUE)


def verifying_message(message: str) -> str:
    """Format a verifying message with blue [VERIFYING] prefix."""
    return colored_message("[VERIFYING]", message, Colors.BLUE)


# ── Directory Setup ─────────────────────────────────────────
# Use current working directory for logs and outputs when running as global command
WORKING_DIR = os.getcwd()
LOG_DIR = os.path.join(WORKING_DIR, "logs")
OUTPUT_DIR = os.path.join(WORKING_DIR, "outputs")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")


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


def _sanitize_for_json(obj):
    """
    Recursively sanitize objects for JSON serialization.

    Converts Mock objects and other non-serializable objects to strings.

    Args:
        obj: The object to sanitize

    Returns:
        A JSON-serializable version of the object
    """
    import unittest.mock

    if isinstance(obj, unittest.mock.Mock):
        return f"<Mock: {obj._mock_name or 'unnamed'}>"
    elif isinstance(obj, dict):
        return {key: _sanitize_for_json(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_for_json(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(_sanitize_for_json(item) for item in obj)
    elif hasattr(obj, "__dict__") and not isinstance(
        obj, (str, int, float, bool, type(None))
    ):
        # Handle custom objects by converting to string
        return str(obj)
    else:
        # Return as-is for basic JSON-serializable types
        return obj


@timed
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
    from litassist.config import CONFIG

    ts = time.strftime("%Y%m%d-%H%M%S")
    ctx = get_current_context(silent=True)

    # Try to get log format from click context first, then CONFIG, then default to json
    if ctx and ctx.obj and "log_format" in ctx.obj:
        log_format = ctx.obj["log_format"]
    else:
        # Fall back to CONFIG setting when not in a click context (e.g., during tests)
        log_format = getattr(CONFIG, "log_format", "json")

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
            elif "response" in payload or "inputs" in payload:
                # Standard command output format
                _write_command_output_markdown(f, tag, ts, payload)
            else:
                # Generic format for unknown log types
                _write_generic_markdown(f, tag, ts, payload)

            logging.debug(f"Markdown log saved: {md_path}")
    except IOError as e:
        raise click.ClickException(f"Failed to save Markdown log {md_path}: {e}")


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
            if isinstance(item, dict):
                f.write(
                    f"- `{item.get('citation', 'N/A')}`: {item.get('reason', 'N/A')}  \n"
                )
            else:
                f.write(f"- {item}  \n")
        f.write("\n")

    # International citations
    intl_citations = payload.get("international_citations", [])
    if intl_citations:
        f.write("## International Citations\n\n")
        for citation in intl_citations:
            f.write(f"- **{citation.get('citation', 'N/A')}**  \n")
            f.write(f"  - Verified: {citation.get('verified', 'N/A')}  \n")
            f.write(f"  - Reason: {citation.get('reason', 'N/A')}  \n")
        f.write("\n")

    # Traditional citations
    trad_citations = payload.get("traditional_citations", [])
    if trad_citations:
        f.write("## Traditional Citations\n\n")
        for citation in trad_citations:
            f.write(f"- **{citation.get('citation', 'N/A')}**  \n")
            f.write(f"  - Verified: {citation.get('verified', 'N/A')}  \n")
            f.write(f"  - Reason: {citation.get('reason', 'N/A')}  \n")
        f.write("\n")

    # Detailed results
    detailed = payload.get("detailed_results", [])
    if detailed:
        f.write("## Detailed Results\n\n")
        for result in detailed:
            f.write(f"### {result.get('citation', 'N/A')}\n\n")
            f.write(f"- **Verified**: {result.get('verified', 'N/A')}  \n")
            f.write(
                f"- **Traditional Format**: {result.get('is_traditional', 'N/A')}  \n"
            )
            f.write(f"- **International**: {result.get('is_international', 'N/A')}  \n")
            if result.get("reason"):
                f.write(f"- **Reason**: {result.get('reason')}  \n")
            if result.get("url"):
                f.write(f"- **URL**: {result.get('url')}  \n")
            f.write("\n")


def _write_citation_validation_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for citation validation logs."""
    f.write(f"# {tag} — {ts}\n\n")

    # Method and parameters
    f.write("## Details\n\n")
    f.write(f"- **Method**: `{payload.get('method', 'N/A')}`  \n")
    f.write(
        f"- **Input Text Length**: {payload.get('input_text_length', 0)} characters  \n"
    )
    f.write(f"- **Online Verification**: {payload.get('enable_online', False)}  \n")
    f.write(f"- **Issues Found**: {payload.get('issues_found', 0)}  \n")
    f.write(f"- **Timestamp**: {payload.get('timestamp', ts)}  \n\n")

    # Issues
    issues = payload.get("issues", [])
    if issues:
        f.write("## Issues Found\n\n")
        for issue in issues:
            f.write(f"- {issue}  \n")
        f.write("\n")


def _write_http_validation_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for HTTP validation logs."""
    f.write(f"# {tag} — {ts}\n\n")

    # Request details
    f.write("## Request Details\n\n")
    f.write(f"- **Method**: `{payload.get('method', 'N/A')}`  \n")
    f.write(f"- **URL**: `{payload.get('url', 'N/A')}`  \n")
    f.write(f"- **Timeout**: {payload.get('timeout', 'N/A')} seconds  \n\n")

    # Response details
    f.write("## Response\n\n")
    f.write(f"- **Status Code**: {payload.get('status_code', 'N/A')}  \n")
    f.write(f"- **Success**: {payload.get('success', 'N/A')}  \n")
    f.write(f"- **Response Time**: {payload.get('response_time_ms', 'N/A')} ms  \n")
    if payload.get("error"):
        f.write(f"- **Error**: {payload.get('error')}  \n")
    f.write(f"- **Timestamp**: {payload.get('timestamp', ts)}  \n")


def _write_search_validation_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for AustLII search validation logs."""
    f.write(f"# {tag} — {ts}\n\n")

    f.write("## Search Details\n\n")
    f.write(f"- **Method**: `{payload.get('method', 'N/A')}`  \n")
    f.write(f"- **Citation**: `{payload.get('citation', 'N/A')}`  \n")
    f.write(f"- **Success**: {payload.get('success', 'N/A')}  \n")
    f.write(f"- **Response Time**: {payload.get('response_time_ms', 'N/A')} ms  \n")
    f.write(f"- **Timeout**: {payload.get('timeout', 'N/A')} seconds  \n")
    f.write(f"- **Timestamp**: {payload.get('timestamp', ts)}  \n")


def _write_command_output_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for standard command output logs."""
    # Original format for command outputs
    f.write(f"# {tag} — {ts}\n\n")
    f.write(f"- **Command**: `{tag}`  \n")
    f.write(f"- **Parameters**: `{payload.get('params','')}`  \n\n")

    # Inputs
    f.write("## Inputs\n\n")
    for k, v in payload.get("inputs", {}).items():
        f.write(f"**{k}**:  \n```\n{v}\n```\n\n")

    # Output
    f.write("## Output\n\n```\n")
    f.write(payload.get("response", "").strip())
    f.write("\n```\n\n")

    # Usage
    f.write("## Usage\n\n")
    usage = payload.get("usage", {})
    for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
        if field in usage:
            f.write(f"- **{field}**: {usage[field]}  \n")

    # Timing information
    timing = usage.get("timing", {})
    if timing:
        f.write("\n## Timing\n\n")
        f.write(f"- **Start Time**: {timing.get('start_time', 'N/A')}  \n")
        f.write(f"- **End Time**: {timing.get('end_time', 'N/A')}  \n")
        f.write(f"- **Duration**: {timing.get('duration_seconds', 'N/A')} seconds  \n")


def _write_generic_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for unknown/generic log types."""
    f.write(f"# {tag} — {ts}\n\n")

    def write_value(key: str, value: Any, level: int = 0):
        """Recursively write values with proper formatting."""
        indent = "  " * level

        if isinstance(value, dict):
            f.write(f"{indent}**{key}**:\n")
            for k, v in value.items():
                write_value(k, v, level + 1)
        elif isinstance(value, list):
            f.write(f"{indent}**{key}**:\n")
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    f.write(f"{indent}  - Item {i + 1}:\n")
                    for k, v in item.items():
                        write_value(k, v, level + 2)
                else:
                    f.write(f"{indent}  - {item}\n")
        else:
            # Handle different value types
            if isinstance(value, str) and len(value) > 100:
                # Long strings in code blocks
                f.write(f"{indent}**{key}**:\n{indent}```\n{value}\n{indent}```\n")
            else:
                f.write(f"{indent}**{key}**: {value}  \n")

    # Write all payload data
    for key, value in payload.items():
        write_value(key, value)
        f.write("\n")


@timed
def read_document(path: str) -> str:
    """
    Read a PDF (text‐only) or plain‐text file and return its full text.

    Args:
        path: The path to the PDF or text file to read.

    Returns:
        The extracted text content as a string.

    Raises:
        click.ClickException: On any I/O or text extraction errors.
    """
    try:
        if path.lower().endswith(".pdf"):
            reader = PdfReader(path)
            pages = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    pages.append(txt)
            if not pages:
                raise click.ClickException(f"No extractable text found in PDF: {path}")
            return "\n".join(pages)
        else:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                raise click.ClickException(f"No text found in file: {path}")
            return content
    except FileNotFoundError:
        raise click.ClickException(f"File not found: {path}")
    except Exception as e:
        raise click.ClickException(f"Error reading document {path}: {e}")


@timed
def create_embeddings(texts: List[str]) -> List[Any]:
    """
    Create embeddings for a list of text inputs.

    Args:
        texts: List of text strings to embed.

    Returns:
        The embedding data from the OpenAI API response.

    Raises:
        Exception: If the embedding API call fails.
        ValueError: If any text exceeds the model's token limit.
    """
    # Import here to avoid circular imports
    from litassist.config import CONFIG

    # Validate text lengths (8191 tokens ≈ 32000 chars for safety)
    MAX_CHARS = 32000
    for i, text in enumerate(texts):
        if len(text) > MAX_CHARS:
            raise ValueError(
                f"Text at index {i} is too long ({len(text)} chars). "
                f"Maximum is approximately {MAX_CHARS} characters. "
                f"Use smaller chunks with chunk_text(text, max_chars=8000)."
            )

    # Use the model without custom dimensions since our index is 1536-dimensional
    return openai.Embedding.create(input=texts, model=CONFIG.emb_model).data


def count_tokens_and_words(text: str) -> tuple[int, int]:
    """
    Count both tokens and words in text content.

    Args:
        text: The text content to analyze

    Returns:
        Tuple of (token_count, word_count)
    """
    # Try to import tiktoken if available
    try:
        import tiktoken
        TIKTOKEN_AVAILABLE = True
    except ImportError:
        TIKTOKEN_AVAILABLE = False
        
    if TIKTOKEN_AVAILABLE:
        try:
            # Use cl100k_base encoding (used by GPT-4, Claude, most modern models)
            encoding = tiktoken.get_encoding("cl100k_base")
            token_count = len(encoding.encode(text))
        except Exception as e:
            # Log warning and fall back to estimation
            logging.warning(f"tiktoken token counting failed: {e}. Falling back to word count estimation.")
            # Fallback: rough estimation (1 token ≈ 0.75 words)
            token_count = int(len(text.split()) * 1.33)
    else:
        # Fallback: rough estimation (1 token ≈ 0.75 words)
        token_count = int(len(text.split()) * 1.33)

    word_count = len(text.split())
    return token_count, word_count


@timed
def chunk_text(text: str, max_chars: int = 20000) -> List[str]:
    """
    Enhanced text chunking that handles OCR artifacts and provides better granularity.

    Uses multiple splitting strategies to create more manageable chunks:
    1. Split by paragraph breaks (double newlines)
    2. Split by enhanced sentence detection (handles OCR issues)
    3. Character-based splitting as fallback

    Args:
        text: The text to split into chunks.
        max_chars: Maximum characters per chunk (default: 20000 for better granularity).

    Returns:
        A list of text chunks, each up to max_chars in length.

    Raises:
        TypeError: If text is not a string or max_chars is not an integer.
        ValueError: If max_chars is not positive or text processing fails.
    """
    # Parameter validation
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not isinstance(max_chars, int):
        raise TypeError("max_chars must be an integer")
    if max_chars <= 0:
        raise ValueError("max_chars must be a positive integer")

    # Handle empty input case
    if not text or not text.strip():
        return []

    try:
        # Normalize whitespace first (OCR often has inconsistent spacing)
        normalized_text = re.sub(r"\s+", " ", text.strip())

        chunks = []
        current_chunk = ""

        # Strategy 1: Split by paragraph breaks (preserve original structure where possible)
        paragraphs = re.split(r"\n\s*\n", normalized_text)

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If paragraph fits in current chunk, add it
            if len(current_chunk) + len(paragraph) + 2 <= max_chars:  # +2 for spacing
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # If paragraph is too long, split it by sentences
                if len(paragraph) > max_chars:
                    sentences = _split_into_sentences(paragraph)

                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 <= max_chars:
                            if current_chunk:
                                current_chunk += " " + sentence
                            else:
                                current_chunk = sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                                current_chunk = ""

                            # If sentence is still too long, split by character
                            if len(sentence) > max_chars:
                                for i in range(0, len(sentence), max_chars):
                                    chunk_part = sentence[i : i + max_chars]
                                    if (
                                        current_chunk
                                        and len(current_chunk) + len(chunk_part)
                                        <= max_chars
                                    ):
                                        current_chunk += chunk_part
                                    else:
                                        if current_chunk:
                                            chunks.append(current_chunk)
                                        current_chunk = chunk_part
                            else:
                                current_chunk = sentence
                else:
                    current_chunk = paragraph

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    except re.error as e:
        raise ValueError(f"Error in regex pattern during text chunking: {e}")
    except MemoryError:
        raise ValueError("Text is too large to process with the given chunk size")
    except Exception as e:
        raise ValueError(f"Error during text chunking: {e}")


def _split_into_sentences(text: str) -> List[str]:
    """
    Enhanced sentence splitting that handles OCR artifacts.

    Args:
        text: Text to split into sentences.

    Returns:
        List of sentences.
    """
    # Multiple patterns to catch different sentence endings common in OCR text
    patterns = [
        r"(?<=[.!?])\s+(?=[A-Z])",  # Standard: punctuation + space + capital
        r"(?<=[.!?])\s*\n+\s*(?=[A-Z])",  # punctuation + newline(s) + capital
        r"(?<=[.!?])\s*(?=\d+\.)",  # punctuation + numbered list
        r"(?<=\.)\s*(?=[A-Z][a-z])",  # period + capital + lowercase (common in OCR)
        r"(?<=[.!?])\s*(?=[A-Z][A-Z])",  # punctuation + all caps (headers)
    ]

    sentences = [text]

    for pattern in patterns:
        new_sentences = []
        for sentence in sentences:
            split_parts = re.split(pattern, sentence)
            new_sentences.extend(split_parts)
        sentences = [s.strip() for s in new_sentences if s.strip()]

    return sentences


def heartbeat(interval: int = 30):
    """
    Decorator to emit a heartbeat message every `interval` seconds while a long-running function executes.

    Args:
        interval: Number of seconds between heartbeat messages. Defaults to 30.

    Returns:
        A decorator function that wraps the target function with heartbeat functionality.

    Example:
        @heartbeat(60)
        def long_running_function():
            # Function that takes a long time to execute
            pass
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            done = threading.Event()

            def ping():
                while not done.is_set():
                    # Suppress during pytest runs
                    if not os.environ.get("PYTEST_CURRENT_TEST"):
                        click.echo("…still working, please wait…", err=True)
                    time.sleep(interval)

            t = threading.Thread(target=ping, daemon=True)
            t.start()
            try:
                return fn(*args, **kwargs)
            finally:
                done.set()
                t.join(timeout=0)

        return wrapper

    return decorator


# ── Legal Reasoning Traces ─────────────────────────────────────


class LegalReasoningTrace:
    """
    Structured legal reasoning trace for analytical commands.

    Provides transparency in legal analysis by capturing the reasoning process
    behind conclusions in a standardized format.
    """

    def __init__(
        self,
        issue: str,
        applicable_law: str,
        application: str,
        conclusion: str,
        confidence: int,
        sources: List[str] = None,
        command: str = None,
    ):
        """
        Initialize a legal reasoning trace.

        Args:
            issue: The legal question or issue being analyzed
            applicable_law: The relevant legal principles, statutes, or cases
            application: How the law applies to the specific facts
            conclusion: The resulting legal conclusion
            confidence: Confidence level (0-100%)
            sources: List of legal sources cited
            command: The LitAssist command that generated this reasoning
        """
        self.issue = issue
        self.applicable_law = applicable_law
        self.application = application
        self.conclusion = conclusion
        self.confidence = confidence  # No clamping - let validation catch errors
        self.sources = sources or []
        self.command = command
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> Dict[str, Any]:
        """Convert reasoning trace to dictionary format."""
        return {
            "issue": self.issue,
            "applicable_law": self.applicable_law,
            "application": self.application,
            "conclusion": self.conclusion,
            "confidence": self.confidence,
            "sources": self.sources,
            "command": self.command,
            "timestamp": self.timestamp,
        }

    def to_markdown(self) -> str:
        """Format reasoning trace as markdown."""
        sources_text = ""
        if self.sources:
            sources_text = "\n\n**Sources:**\n" + "\n".join(
                f"- {source}" for source in self.sources
            )

        return f"""## Legal Reasoning Trace

**Issue:** {self.issue}

**Applicable Law:** {self.applicable_law}

**Application to Facts:** {self.application}

**Conclusion:** {self.conclusion}

**Confidence:** {self.confidence}%{sources_text}

*Generated by {self.command or 'LitAssist'} on {self.timestamp}*
"""

    def to_structured_text(self) -> str:
        """Format reasoning trace as structured text."""
        sources_text = ""
        if self.sources:
            sources_text = f"\nSources: {'; '.join(self.sources)}"

        return f"""=== REASONING ===
Issue: {self.issue}
Applicable Law: {self.applicable_law}
Application to Facts: {self.application}
Conclusion: {self.conclusion}
Confidence: {self.confidence}%{sources_text}
Generated: {self.timestamp} ({self.command or 'LitAssist'})
"""


def create_reasoning_prompt(base_prompt: str, command: str) -> str:
    """
    Enhance a base prompt to include legal reasoning trace generation.

    Args:
        base_prompt: The original prompt for the command
        command: The LitAssist command name for context

    Returns:
        Enhanced prompt that will generate reasoning traces
    """
    reasoning_instruction = f"""

IMPORTANT: After your main analysis, provide a clear legal reasoning trace using this exact format (DO NOT repeat any sections):

=== REASONING ===

Issue: [State the primary legal question or issue being analyzed - write this only once]

Applicable Law: [Identify the relevant legal principles, statutes, cases, or rules - write this only once]

Application to Facts: [Explain how the law applies to the specific facts presented - write this only once]

Conclusion: [State your legal conclusion clearly - write this only once]

Confidence: [Your confidence level as a percentage, 0-100%]

Sources: [List key legal authorities cited, separated by semicolons]

Each section should appear exactly once. Do not repeat sections or content. This reasoning trace helps ensure transparency and accountability in legal analysis for the {command} command."""

    return base_prompt + reasoning_instruction


def extract_reasoning_trace(
    content: str, command: str = None
) -> Optional[LegalReasoningTrace]:
    """
    Extract a legal reasoning trace from LLM output.

    Args:
        content: The LLM response content
        command: The command that generated this content

    Returns:
        LegalReasoningTrace object if found, None otherwise
    """
    # The pattern now looks for the start of the trace and captures everything
    # until the end of the content or another major header. It is non-greedy.
    trace_pattern = r"=== REASONING ===\s*\n(.*?)(?=\n===|$)"
    match = re.search(trace_pattern, content, re.DOTALL | re.IGNORECASE)

    if not match:
        return None

    trace_text = match.group(1).strip()

    # More robust extraction for each component
    components = {}
    patterns = {
        "issue": r"Issue:\s*(.*?)(?=\n\s*Applicable Law:|\n\s*Application to Facts:|\n\s*Conclusion:|\n\s*Confidence:|\n\s*Sources:|\Z)",
        "applicable_law": r"Applicable Law:\s*(.*?)(?=\n\s*Application to Facts:|\n\s*Conclusion:|\n\s*Confidence:|\n\s*Sources:|\Z)",
        "application": r"Application to Facts:\s*(.*?)(?=\n\s*Conclusion:|\n\s*Confidence:|\n\s*Sources:|\Z)",
        "conclusion": r"Conclusion:\s*(.*?)(?=\n\s*Confidence:|\n\s*Sources:|\Z)",
        "confidence": r"Confidence:\s*(\d+)",
        "sources": r"Sources:\s*(.*?)(?=\n\s*Generated:|\Z)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, trace_text, re.DOTALL | re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if key == "confidence":
                components[key] = int(value) if value.isdigit() else 50
            elif key == "sources":
                components[key] = [s.strip() for s in value.split(";") if s.strip()]
            else:
                components[key] = value

    # Check for essential components before creating the trace object
    if all(
        key in components
        for key in ["issue", "applicable_law", "application", "conclusion"]
    ):
        return LegalReasoningTrace(
            issue=components.get("issue", "N/A"),
            applicable_law=components.get("applicable_law", "N/A"),
            application=components.get("application", "N/A"),
            conclusion=components.get("conclusion", "N/A"),
            confidence=components.get("confidence", 50),
            sources=components.get("sources", []),
            command=command,
        )

    return None


def save_reasoning_trace(trace: LegalReasoningTrace, output_file: str) -> str:
    """
    Save reasoning trace to a separate file alongside the main output.

    Args:
        trace: The LegalReasoningTrace to save
        output_file: Path to the main output file

    Returns:
        Path to the saved reasoning trace file
    """
    # Create reasoning trace filename
    base_name = os.path.splitext(output_file)[0]
    trace_file = f"{base_name}_reasoning.txt"

    with open(trace_file, "w", encoding="utf-8") as f:
        f.write(trace.to_structured_text())

    return trace_file


def save_command_output(
    command_name: str,
    content: str,
    query_or_slug: str,
    metadata: Optional[Dict[str, str]] = None,
) -> str:
    """
    Save command output with standard format.

    Args:
        command_name: Name of the command (e.g., 'strategy', 'draft')
        content: The main content to save
        query_or_slug: Query string or slug for filename generation
        metadata: Optional dict of metadata to include in header

    Returns:
        Path to the saved output file
    """
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Create filename slug
    slug = re.sub(r"[^\w\s-]", "", query_or_slug.lower())
    slug = re.sub(r"[-\s]+", "_", slug)[:40].strip("_") or command_name

    output_file = os.path.join(OUTPUT_DIR, f"{command_name}_{slug}_{timestamp}.txt")

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

    return output_file


def show_command_completion(
    command_name: str,
    output_file: str,
    extra_files: Optional[Dict[str, str]] = None,
    stats: Optional[Dict[str, Any]] = None,
):
    """
    Display standard completion message for commands.

    Args:
        command_name: Name of the command
        output_file: Path to the main output file
        extra_files: Optional dict of label->path for additional files
        stats: Optional statistics to display
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

    tip_msg = tip_message(f'View full output: open "{output_file}"')
    click.echo(f"\n{tip_msg}")


def detect_factual_hallucinations(content: str, source_facts: str = "") -> List[str]:
    """
    Detect potential hallucinated facts in drafted content.

    Args:
        content: The drafted content to check
        source_facts: The original source facts to compare against

    Returns:
        List of potential hallucination warnings
    """
    warnings = []

    # Pattern for ages (e.g., "33 years of age", "aged 45")
    age_pattern = r"\b(\d{1,3})\s*years?\s*(?:of\s*)?(?:age|old)\b"
    ages_found = re.findall(age_pattern, content, re.IGNORECASE)
    if ages_found and source_facts:
        for age in ages_found:
            if age not in source_facts:
                warnings.append(f"Potentially hallucinated age: {age} years")

    # Pattern for specific addresses (number + street name)
    address_pattern = r"\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:Street|St|Avenue|Ave|Road|Rd|Court|Ct|Drive|Dr|Place|Pl)\b"
    addresses_found = re.findall(address_pattern, content)
    if addresses_found and source_facts:
        for address in addresses_found:
            # Check if this exact address appears in source
            if address not in source_facts:
                warnings.append(f"Potentially hallucinated address: {address}")

    # Pattern for bank/credit card numbers
    account_pattern = r"(?:account|a/c|card).*?(?:ending|number|no\.?)\s*(?:in\s*)?[-:\s]*(\d{4,}|\*+\d{4}|-\d{4})"
    accounts_found = re.findall(account_pattern, content, re.IGNORECASE)
    if accounts_found:
        for account in accounts_found:
            if source_facts and account not in source_facts:
                warnings.append(
                    f"Potentially hallucinated account/card number: {account}"
                )

    # Pattern for specific exhibit numbers (e.g., "VO-1", "Exhibit 23")
    exhibit_pattern = r"(?:exhibit|annexure)\s*(?:marked\s*)?([A-Z]{1,3}-?\d+|\d+)"
    exhibits_found = re.findall(exhibit_pattern, content, re.IGNORECASE)
    if exhibits_found:
        warnings.append(
            f"Specific exhibit references found: {', '.join(set(exhibits_found))}. Consider using generic placeholders like [EXHIBIT A]"
        )

    # Pattern for document/reference numbers (e.g., "Order No. 12345", "Cheque No. 67890")
    ref_pattern = r"(?:order|cheque|check|reference|ref|invoice|receipt)\s*(?:no\.?|number)\s*[:\s]*(\d{4,})"
    refs_found = re.findall(ref_pattern, content, re.IGNORECASE)
    if refs_found and source_facts:
        for ref in refs_found:
            if ref not in source_facts:
                warnings.append(f"Potentially hallucinated reference number: {ref}")

    # Check for suspiciously specific dates not in source
    date_pattern = r"\b(\d{1,2})\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b"
    dates_found = re.findall(date_pattern, content, re.IGNORECASE)
    if dates_found and source_facts:
        for date in dates_found:
            date_str = f"{date[0]} {date[1]}"
            # Very basic check - could be improved
            if date_str not in source_facts and date[0] not in source_facts:
                warnings.append(f"Potentially hallucinated specific date: {date_str}")

    return warnings


def verify_content_if_needed(
    client: Any,
    content: str,
    command_name: str,
    verify_flag: bool = False,
    citation_already_verified: bool = False,
) -> tuple[str, bool]:
    """
    Handle verification and citation validation.

    Args:
        client: LLMClient instance
        content: Content to verify
        command_name: Name of the command (for context)
        verify_flag: Whether user explicitly requested verification
        citation_already_verified: Whether citation verification was already performed

    Returns:
        Tuple of (possibly modified content, whether verification was performed)
    """
    # Check if auto-verification is needed
    auto_verify = client.should_auto_verify(content, command_name)
    needs_verification = verify_flag or auto_verify

    # Inform user about verification status (suppress during tests)
    if not os.environ.get("PYTEST_CURRENT_TEST"):
        if verify_flag and auto_verify:
            click.echo(
                verifying_message(
                    "Running verification (--verify flag + auto-verification triggered)"
                )
            )
        elif verify_flag:
            click.echo(
                verifying_message("Running verification (--verify flag enabled)")
            )
        elif auto_verify:
            click.echo(
                verifying_message(
                    "Running auto-verification (high-risk content detected)"
                )
            )
        else:
            click.echo(info_message("No verification performed"))

    if needs_verification:
        try:
            # Use appropriate verification level based on command
            if command_name in ["strategy", "draft"]:
                correction = client.verify_with_level(content, "heavy")
            else:
                correction = client.verify(content)

            if correction.strip() and not correction.lower().startswith(
                "no corrections needed"
            ):
                content = (
                    content
                    + f"\n\n--- {command_name.title()} Review ---\n"
                    + correction
                )

            # Run citation validation (skip if already verified)
            if not citation_already_verified:
                citation_issues = client.validate_citations(content)
                if citation_issues:
                    content += "\n\n--- Citation Warnings ---\n" + "\n".join(
                        citation_issues
                    )

        except Exception as e:
            raise click.ClickException(f"Verification error during {command_name}: {e}")

    return content, needs_verification


def validate_file_size(
    file_path: str, max_size: int = 50000, file_type: str = "input"
) -> str:
    """
    Validate file size and return content if within limits.

    Args:
        file_path: Path to the file
        max_size: Maximum allowed characters
        file_type: Type of file for error message

    Returns:
        File content if valid

    Raises:
        click.ClickException: If file is too large
    """
    content = read_document(file_path)

    if len(content) > max_size:
        raise click.ClickException(
            f"{file_type.capitalize()} file too large ({len(content):,} characters). "
            f"Please provide a file under {max_size:,} characters (~{max_size//5:,} words)."
        )

    return content


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

    # Find ORTHODOX STRATEGIES section
    orthodox_match = re.search(
        r"## ORTHODOX STRATEGIES\n(.*?)(?=## [A-Z]|===|\Z)", strategies_text, re.DOTALL
    )
    if orthodox_match:
        orthodox_text = orthodox_match.group(1)
        parsed["orthodox_count"] = len(
            re.findall(r"^\d+\.", orthodox_text, re.MULTILINE)
        )

    # Find UNORTHODOX STRATEGIES section
    unorthodox_match = re.search(
        r"## UNORTHODOX STRATEGIES\n(.*?)(?=## [A-Z]|===|\Z)",
        strategies_text,
        re.DOTALL,
    )
    if unorthodox_match:
        unorthodox_text = unorthodox_match.group(1)
        parsed["unorthodox_count"] = len(
            re.findall(r"^\d+\.", unorthodox_text, re.MULTILINE)
        )

    # Find MOST LIKELY TO SUCCEED section
    likely_match = re.search(
        r"## MOST LIKELY TO SUCCEED\n(.*?)(?====|\Z)", strategies_text, re.DOTALL
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
    import click

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


def validate_file_size_limit(content: str, max_size: int, context: str):
    """
    Validate file size and raise exception if too large.

    Args:
        content: The file content to check
        max_size: Maximum allowed characters
        context: Description of what type of file is being validated

    Raises:
        click.ClickException: If file is too large
    """
    import click

    if len(content) > max_size:
        raise click.ClickException(
            f"{context} file too large ({len(content):,} characters). "
            f"Please provide a file under {max_size:,} characters (~{max_size//5:,} words)."
        )


def process_extraction_response(
    content: str, extract_type: str, output_prefix: str, command: str
) -> tuple[str, dict, str]:
    """
    Process extraction response from LLM with JSON-first approach.

    Follows CLAUDE.md guidance: LLMs return properly formatted output when prompted correctly.
    No fallback parsing needed - trust the LLM to follow format instructions.

    Args:
        content: Raw LLM response expected to be valid JSON
        extract_type: Type of extraction (citations/principles/checklist/all)
        output_prefix: Prefix for output files (e.g., "lookup_citations_20240615_120000")
        command: Command name for context (lookup/counselnotes)

    Returns:
        Tuple of (formatted_text, json_data, json_file_path)

    Raises:
        click.ClickException: If JSON parsing fails (indicates prompt needs improvement)
    """
    import click

    # Parse JSON response - no fallbacks per CLAUDE.md
    try:
        # Clean content if needed (remove any markdown code blocks)
        clean_content = content.strip()
        if clean_content.startswith("```json"):
            clean_content = clean_content[7:]
        if clean_content.startswith("```"):
            clean_content = clean_content[3:]
        if clean_content.endswith("```"):
            clean_content = clean_content[:-3]
        clean_content = clean_content.strip()

        json_data = json.loads(clean_content)
    except json.JSONDecodeError as e:
        # Per CLAUDE.md: Fix prompts, not parsing
        raise click.ClickException(
            f"LLM did not return valid JSON for {extract_type} extraction. "
            f"This indicates the prompt needs improvement. Error: {str(e)}"
        )

    # Save JSON file
    json_file = os.path.join(OUTPUT_DIR, f"{output_prefix}.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)

    # Generate formatted text based on extraction type
    if extract_type == "citations":
        if "citations" in json_data and isinstance(json_data["citations"], list):
            items = json_data["citations"]
            formatted_text = (
                "CITATIONS FOUND:\n" + "\n".join(items)
                if items
                else "No citations found."
            )
        else:
            formatted_text = "No citations found in response."

    elif extract_type == "principles":
        if "principles" in json_data:
            principles = json_data["principles"]
            if isinstance(principles, list):
                formatted_lines = []
                for p in principles:
                    if isinstance(p, dict):
                        # Dict format: {"principle": "...", "authority": "..."}
                        principle = p.get("principle", "")
                        authority = p.get("authority", "")
                        if authority:
                            formatted_lines.append(f"• {principle} ({authority})")
                        else:
                            formatted_lines.append(f"• {principle}")
                    elif isinstance(p, str):
                        # String format: "principle text"
                        formatted_lines.append(f"• {p}")
                    # Skip any other types silently

                if formatted_lines:
                    formatted_text = "LEGAL PRINCIPLES:\n" + "\n".join(formatted_lines)
                else:
                    formatted_text = "LEGAL PRINCIPLES:\n(No valid principles found)"
            else:
                formatted_text = "No legal principles found."
        else:
            formatted_text = "No legal principles found in response."

    elif extract_type == "checklist":
        if "checklist" in json_data and isinstance(json_data["checklist"], list):
            items = json_data["checklist"]
            formatted_text = (
                "PRACTICAL CHECKLIST:\n" + "\n".join(f"[ ] {item}" for item in items)
                if items
                else "No checklist items found."
            )
        else:
            formatted_text = "No checklist items found in response."

    elif extract_type == "all":
        # Comprehensive extraction with multiple sections
        sections = []

        # Strategic summary
        if "strategic_summary" in json_data:
            sections.append(f"STRATEGIC SUMMARY:\n{json_data['strategic_summary']}")

        # Citations
        if "key_citations" in json_data and json_data["key_citations"]:
            sections.append(
                "KEY CITATIONS:\n"
                + "\n".join(f"• {c}" for c in json_data["key_citations"])
            )

        # Principles
        if "legal_principles" in json_data and json_data["legal_principles"]:
            principles_text = "LEGAL PRINCIPLES:\n"
            for p in json_data["legal_principles"]:
                if isinstance(p, dict):
                    principle = p.get("principle", "")
                    authority = p.get("authority", "")
                    if authority:
                        principles_text += f"• {principle} ({authority})\n"
                    else:
                        principles_text += f"• {principle}\n"
                else:
                    principles_text += f"• {p}\n"
            sections.append(principles_text.rstrip())

        # Checklist
        if "tactical_checklist" in json_data and json_data["tactical_checklist"]:
            sections.append(
                "TACTICAL CHECKLIST:\n"
                + "\n".join(f"[ ] {item}" for item in json_data["tactical_checklist"])
            )

        # Risk assessment
        if "risk_assessment" in json_data:
            sections.append(f"RISK ASSESSMENT:\n{json_data['risk_assessment']}")

        # Recommendations
        if "recommendations" in json_data and json_data["recommendations"]:
            sections.append(
                "RECOMMENDATIONS:\n"
                + "\n".join(f"• {r}" for r in json_data["recommendations"])
            )

        formatted_text = (
            "\n\n".join(sections) if sections else "No structured data extracted."
        )

    else:
        formatted_text = f"Unknown extraction type: {extract_type}"

    # Add metadata footer
    formatted_text += (
        f"\n\n---\nExtracted via {command} command\nJSON data saved to: {json_file}"
    )

    return formatted_text, json_data, json_file
