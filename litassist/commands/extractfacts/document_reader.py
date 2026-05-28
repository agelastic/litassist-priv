"""
Document reading and processing for extractfacts command.

Handles reading of source files and combining them with source markers.
"""

import os
from typing import Tuple, List

from litassist.llm.factory import LLMClientFactory
from litassist.utils.file_ops import validate_file_size
from litassist.utils.text_processing import chunk_text
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

    # Per-file size cap derives from extractfacts' configured model window:
    # extractfacts ingests one source at a time and concatenates into
    # `all_text`, so the per-file cap must NOT exceed what a single chunk
    # can hold. Using the full input budget per file would allow a
    # multi-file ingest to overflow even at 1-chunk-per-file.
    per_file_max = LLMClientFactory.get_input_budget_for_command("extractfacts")

    all_text = ""
    source_files = []
    for f in files:
        text = validate_file_size(f, max_size=per_file_max, file_type="source")
        source_files.append(os.path.basename(f))
        all_text += f"\n\n--- SOURCE: {os.path.basename(f)} ---\n\n{text}"

    # Chunk the combined text using the same per-command budget. The chunker
    # later splits on sentence boundaries within this character cap.
    chunks = chunk_text(all_text, max_chars=per_file_max)

    return all_text, source_files, chunks
