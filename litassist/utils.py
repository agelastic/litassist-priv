"""
Utility functions for LitAssist.

This module provides helper functions and decorators used throughout the LitAssist application,
including timing, logging, document processing, and embedding generation.
"""

import os
import time
import json
import logging
import threading
import functools
import re
from typing import List, Dict, Any, Callable, Tuple, Optional, Union

import click
import openai
from PyPDF2 import PdfReader

# ── Logging Setup ─────────────────────────────────────────
# Use current working directory for logs when running as global command
WORKING_DIR = os.getcwd()
LOG_DIR = os.path.join(WORKING_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
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


@timed
def save_log(tag: str, payload: dict):
    """
    Save an audit log under logs/ in either JSON or Markdown format.

    Args:
        tag: A string identifier for the log (e.g., command name).
        payload: Dictionary containing log data including inputs, response, and usage statistics.

    Raises:
        click.ClickException: If there's an error writing the log file.
    """
    from click import get_current_context

    ts = time.strftime("%Y%m%d-%H%M%S")
    ctx = get_current_context(silent=True)
    log_format = (
        ctx.obj.get("log_format", "markdown") if ctx and ctx.obj else "markdown"
    )

    # JSON logging
    if log_format == "json":
        path = os.path.join(LOG_DIR, f"{tag}_{ts}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logging.info(f"JSON log saved: {path}")
        except IOError as e:
            raise click.ClickException(f"Failed to save JSON log {path}: {e}")
        return

    # Markdown logging (default)
    md_path = os.path.join(LOG_DIR, f"{tag}_{ts}.md")
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            # Metadata
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

            # Add timing information if available
            timing = usage.get("timing", {})
            if timing:
                f.write("\n## Timing\n\n")
                f.write(f"- **Start Time**: {timing.get('start_time', 'N/A')}  \n")
                f.write(f"- **End Time**: {timing.get('end_time', 'N/A')}  \n")
                f.write(
                    f"- **Duration**: {timing.get('duration_seconds', 'N/A')} seconds  \n"
                )
        logging.info(f"Markdown log saved: {md_path}")
    except IOError as e:
        raise click.ClickException(f"Failed to save Markdown log {md_path}: {e}")


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
    """
    # Import here to avoid circular imports
    from litassist.config import CONFIG

    # Use the model without custom dimensions since our index is 1536-dimensional
    return openai.Embedding.create(input=texts, model=CONFIG.emb_model).data


@timed
def chunk_text(text: str, max_chars: int = 60000) -> List[str]:
    """
    Split text into chunks of up to max_chars characters, attempting to break at sentence boundaries
    to avoid cutting sentences in half.

    Args:
        text: The text to split into chunks.
        max_chars: Maximum characters per chunk. Must be a positive integer.

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
    if not text:
        return []

    try:
        # Split into sentences by punctuation followed by whitespace
        sentences = re.split(r"(?<=[\.\?\!]\s)", text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # Handle sentences longer than max_chars by splitting directly
                while len(sentence) > max_chars:
                    chunks.append(sentence[:max_chars])
                    sentence = sentence[max_chars:]
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
    except re.error as e:
        raise ValueError(f"Error in regex pattern during text chunking: {e}")
    except MemoryError:
        raise ValueError("Text is too large to process with the given chunk size")
    except Exception as e:
        raise ValueError(f"Error during text chunking: {e}")


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
