"""
Document chunking functionality for the digest command.

This module handles splitting large documents into manageable chunks
based on model-specific token limits.
"""

from typing import List, Tuple
import click
from litassist.utils.text_processing import chunk_text
from litassist.utils.file_ops import read_document


# Model-aware chunk sizing
MODEL_CHUNK_LIMITS = {
    "google": 30000,  # Conservative for Gemini
    "anthropic": 150000,  # Claude handles larger chunks
    "openai": 100000,  # GPT-4 limit
    "x-ai": 100000,  # Grok limit
}


def determine_chunk_size(model_family: str) -> int:
    """
    Determine appropriate chunk size based on model family.

    Args:
        model_family: The model family identifier

    Returns:
        Maximum chunk size in characters
    """
    return MODEL_CHUNK_LIMITS.get(
        model_family, 100000
    )  # Default 100K for unknown models


def warn_if_reduced_chunk_size(model_family: str, model_chunk_limit: int) -> None:
    """
    Warn user if using reduced chunk size for their model.

    Args:
        model_family: The model family being used
        model_chunk_limit: The chunk limit for this model
    """
    if model_family == "google" and model_chunk_limit < 100000:
        click.echo(
            click.style(
                f"Note: Using reduced chunk size ({model_chunk_limit:,} chars) for Gemini model stability",
                fg="yellow",
            )
        )


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
    if total_chars > 500000:  # More than 500k chars
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
