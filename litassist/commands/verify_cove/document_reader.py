"""
Document reading and reference file processing for verify-cove command.

Handles reading the main document and processing optional reference files.
"""

import click
from typing import Tuple, List

from litassist.utils.file_ops import read_document, process_reference_files
from litassist.logging import log_task_event


def read_main_document(file: str) -> str:
    """
    Read the main document to be verified.

    Args:
        file: Path to the document file

    Returns:
        Document content as string

    Raises:
        click.ClickException: If file reading fails or file is empty
    """
    try:
        log_task_event(
            "verify-cove",
            "reading",
            "start",
            "Reading input document"
        )
    except Exception:
        pass

    try:
        content = read_document(file)
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(f"Error reading file: {e}")

    if not content.strip():
        raise click.ClickException("File is empty")

    try:
        log_task_event(
            "verify-cove",
            "reading",
            "end",
            f"Read document: {len(content)} characters"
        )
    except Exception:
        pass

    return content


def read_reference_files(reference: str) -> Tuple[str, List[str]]:
    """
    Process optional reference files for CoVe answer stage.

    Args:
        reference: Glob pattern for reference files (e.g., 'exhibits/*.pdf')

    Returns:
        Tuple of (reference_context, reference_files)
        - reference_context: Combined content from all reference files
        - reference_files: List of reference file paths

    Raises:
        click.ClickException: If reference file processing fails
    """
    if reference:
        try:
            log_task_event(
                "verify-cove",
                "reference",
                "start",
                f"Processing reference files: {reference}"
            )
        except Exception:
            pass

    reference_context, reference_files = process_reference_files(
        reference,
        purpose="CoVe answers",
        show_char_count=True,
    )

    if reference:
        try:
            log_task_event(
                "verify-cove",
                "reference",
                "end",
                f"Processed {len(reference_files)} reference files"
            )
        except Exception:
            pass

    return reference_context, reference_files
