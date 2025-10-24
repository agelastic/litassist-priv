"""
Document processing for counselnotes command.

Handles document reading, consolidation, and chunking logic.
"""

import os
import click
from typing import List, Dict, Tuple

from litassist.config import get_config
from litassist.utils.file_ops import read_document
from litassist.utils.text_processing import chunk_text
from litassist.logging import log_task_event


def read_and_consolidate_documents(files: Tuple[str]) -> Tuple[str, List[Dict]]:
    """
    Read and consolidate multiple documents.

    Args:
        files: Tuple of file paths

    Returns:
        Tuple of (combined_content, file_info)

    Raises:
        click.ClickException: If file reading fails
    """
    try:
        log_task_event(
            "counselnotes",
            "reading",
            "start",
            "Reading input documents"
        )
    except Exception:
        pass

    all_content = []
    file_info = []

    for file_path in files:
        try:
            content = read_document(file_path)
            all_content.append(
                f"=== DOCUMENT: {os.path.basename(file_path)} ===\n{content}\n=== END DOCUMENT: {os.path.basename(file_path)} ==="
            )
            file_info.append(
                {
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "size": len(content),
                }
            )
        except Exception as e:
            raise click.ClickException(f"Error reading {file_path}: {e}")

    try:
        log_task_event(
            "counselnotes",
            "reading",
            "end",
            f"Read {len(files)} document(s)"
        )
    except Exception:
        pass

    # Combine all documents for cross-document analysis
    combined_content = "\n\n".join(all_content)

    return combined_content, file_info


def prepare_chunks(content: str) -> Tuple[List[str], str]:
    """
    Prepare content chunks for processing.

    Args:
        content: Combined document content

    Returns:
        Tuple of (chunks, processing_mode)
    """
    # Check if content needs chunking
    if len(content) > get_config().max_chars:
        # For large content, chunk and process separately then synthesize
        chunks = chunk_text(content, max_chars=get_config().max_chars)
        processing_mode = "chunked"
    else:
        # Process all content together for better synthesis
        chunks = [content]
        processing_mode = "unified"

    return chunks, processing_mode
