"""
Document reading and processing for extractfacts command.

Handles reading of source files and combining them with source markers.
"""

import os
from typing import Tuple, List

from litassist.utils.file_ops import validate_file_size
from litassist.utils.text_processing import chunk_text
from litassist.config import get_config
from litassist.logging import log_task_event


def read_and_combine_files(files: Tuple[str, ...]) -> Tuple[str, List[str], List[str]]:
    """
    Read all source files and combine with source markers.

    Args:
        files: Tuple of file paths to read

    Returns:
        Tuple of (combined_text, source_files, chunks)
        - combined_text: All files combined with source markers
        - source_files: List of source file basenames
        - chunks: Text split into chunks for processing

    Raises:
        click.ClickException: If file reading or validation fails
    """
    try:
        log_task_event(
            "extractfacts",
            "reading",
            "start",
            "Reading input documents"
        )
    except Exception:
        pass

    all_text = ""
    source_files = []
    for f in files:
        text = validate_file_size(f, max_size=3000000, file_type="source")
        source_files.append(os.path.basename(f))
        all_text += f"\n\n--- SOURCE: {os.path.basename(f)} ---\n\n{text}"

    # Use existing chunking on combined text
    chunks = chunk_text(all_text, max_chars=get_config().max_chars)

    return all_text, source_files, chunks
