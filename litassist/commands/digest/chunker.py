"""
Document chunking functionality for the digest command.

This module derives chunk size from the configured model's context window
(via `LLMClientFactory.get_context_window_for_command` + the per-model
`context_window` field in `litassist/llm/model_capabilities.yaml`,
refreshable with `litassist refresh`). When digest is pointed at a
different model in `model_configs.yaml`, the chunk size tracks
automatically.
"""

from typing import List, Optional, Tuple
import click
from litassist.llm.factory import LLMClientFactory
from litassist.utils.text_processing import chunk_text
from litassist.utils.file_ops import read_document


# Fraction of the model's input window to use per chunk. The remainder
# covers the system prompt, the per-chunk summary output, and reasoning
# tokens (for reasoning-family models). 35% is conservative for digest's
# summary-style outputs which are typically <20% of input length.
CHUNK_FRACTION_OF_WINDOW = 0.35

# Conservative chars-per-token ratio for legal English. Char-count is a
# safe over-estimate of token count, so chunks fit comfortably.
CHARS_PER_TOKEN = 3.5


def determine_chunk_size(
    command_name: str = "digest", sub_type: Optional[str] = None
) -> int:
    """
    Derive chunk size from the configured model's context window.

    Args:
        command_name: Click command name (default "digest").
        sub_type: Sub-type passed to LLMClientFactory (e.g. digest's "summary"
            or "issues" mode).

    Returns:
        Maximum chunk size in characters.
    """
    window_tokens = LLMClientFactory.get_context_window_for_command(
        command_name, sub_type
    )
    return int(window_tokens * CHARS_PER_TOKEN * CHUNK_FRACTION_OF_WINDOW)


def read_and_chunk_document(
    file_path: str, chunk_limit: int = 100000, overlap: int = 200
) -> Tuple[str, List[str]]:
    """
    Read a document and split it into chunks.

    Args:
        file_path: Path to the document file
        chunk_limit: Maximum size per chunk in characters
        overlap: Number of characters to overlap between chunks

    Returns:
        Tuple of (full content, list of chunks)

    Raises:
        click.ClickException: If file cannot be read
    """
    # Read the document
    content = read_document(file_path)

    # Split into chunks
    chunks = chunk_text(content, max_chars=chunk_limit)

    return content, chunks


def calculate_total_document_size(file_paths: List[str]) -> Tuple[int, int]:
    """
    Calculate total size of all documents to process.

    Args:
        file_paths: List of file paths to process

    Returns:
        Tuple of (total size in bytes, total character count)
    """
    total_size = 0
    total_chars = 0

    for file_path in file_paths:
        try:
            content = read_document(file_path)
            total_chars += len(content)
            # Rough estimate of file size from content
            total_size += len(content.encode("utf-8"))
        except Exception:
            pass  # Skip files that can't be read

    return total_size, total_chars


def warn_if_large_processing(total_chars: int) -> None:
    """
    Warn user if processing a large amount of text.

    Args:
        total_chars: Total number of characters to process
    """
    if total_chars > 1500000:  # More than 1.5M chars (~3+ chunks)
        estimated_tokens = total_chars / 4
        click.echo(
            click.style(
                f"Warning: Processing {total_chars:,} characters (~{estimated_tokens:,.0f} tokens). This may take some time and incur costs.",
                fg="yellow",
                bold=True,
            )
        )
        if not click.confirm("Continue?"):
            raise click.Abort()


def prepare_chunks_for_processing(
    file_path: str, chunk_limit: int, mode: str
) -> Tuple[str, List[str], int]:
    """
    Prepare document chunks for processing.

    Args:
        file_path: Path to the document
        chunk_limit: Maximum chunk size
        mode: Processing mode ('summary' or 'issues')

    Returns:
        Tuple of (full content, chunks list, chunk count)
    """
    content, chunks = read_and_chunk_document(file_path, chunk_limit)

    # Log chunking info
    if len(chunks) > 1:
        click.echo(f"  Split into {len(chunks)} chunks for processing")

    return content, chunks, len(chunks)
