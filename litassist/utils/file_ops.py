"""
File operations utilities.

This module provides functions for reading documents, validating file sizes,
and handling various file types used throughout LitAssist.
"""

import glob
import os
from typing import Optional, Tuple, List
import click
from pypdf import PdfReader

from litassist.timing import timed


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
            f"Please provide a file under {max_size:,} characters (~{max_size // 5:,} words)."
        )

    return content


def is_text_file(file_path: str) -> bool:
    """
    Check if a file should be treated as a plain text file.

    Treats .txt and .md files identically as text files.

    Args:
        file_path: Path to the file

    Returns:
        True if file is .txt or .md, False otherwise
    """
    return file_path.lower().endswith((".txt", ".md"))


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
    if len(content) > max_size:
        raise click.ClickException(
            f"{context} file too large ({len(content):,} characters). "
            f"Please provide a file under {max_size:,} characters (~{max_size // 5:,} words)."
        )


def expand_glob_pattern(pattern: str, warn_non_files: bool = True) -> List[str]:
    """
    Expand glob pattern and return list of valid file paths.

    Args:
        pattern: Glob pattern string
        warn_non_files: Whether to warn about non-file matches

    Returns:
        List of valid file paths matching the pattern
    """
    from litassist.utils.formatting import warning_message

    if not pattern:
        return []

    matches = glob.glob(pattern)
    valid_files = []

    for f in matches:
        if os.path.isfile(f):
            valid_files.append(f)
        elif warn_non_files:
            click.echo(warning_message(f"Skipping non-file: {f}"))

    return valid_files


def expand_glob_patterns_callback(ctx, param, value):
    """
    Expand glob patterns in file paths for Click multiple=True options.

    This is a Click callback function for handling glob patterns in command options
    that accept multiple file paths. It expands glob patterns and verifies file existence.

    Args:
        ctx: Click context (unused but required for callbacks)
        param: Click parameter (unused but required for callbacks)
        value: Tuple of file patterns from Click

    Returns:
        Tuple of expanded file paths

    Raises:
        click.BadParameter: If no files match a pattern or file doesn't exist
    """
    if not value:
        return value

    expanded_paths = []
    for pattern in value:
        # Check if it's a glob pattern (contains *, ?, or [)
        if any(char in pattern for char in ["*", "?", "["]):
            # Expand the glob pattern
            matches = glob.glob(pattern)
            if not matches:
                raise click.BadParameter(f"No files matching pattern: {pattern}")
            expanded_paths.extend(matches)
        else:
            # Not a glob pattern, just verify the file exists
            if not os.path.exists(pattern):
                raise click.BadParameter(f"File not found: {pattern}")
            expanded_paths.append(pattern)

    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in expanded_paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return tuple(unique_paths)


def process_reference_files(
    pattern: Optional[str],
    purpose: str = "reference",
    require_flag: Optional[str] = None,
    flag_enabled: bool = True,
    show_char_count: bool = False,
) -> Tuple[str, List[str]]:
    """
    Process reference files from glob pattern for verification context.

    Args:
        pattern: Glob pattern for reference files
        purpose: Purpose description for messages (e.g., "reference", "CoVe", "CoVe answers")
        require_flag: Name of required flag (e.g., "--cove")
        flag_enabled: Whether the required flag is set
        show_char_count: Whether to show character count in success messages

    Returns:
        Tuple of (reference_context, reference_files_list)
        - reference_context: Formatted string with all file contents
        - reference_files_list: List of processed filenames
    """
    from litassist.utils.formatting import (
        warning_message,
        success_message,
        verifying_message,
        info_message,
    )

    if not pattern:
        return "", []

    # Check if required flag is set
    if require_flag and not flag_enabled:
        click.echo(
            warning_message(
                f"Reference pattern requires {require_flag} flag; parameter ignored"
            )
        )
        return "", []

    # Expand glob pattern
    valid_files = expand_glob_pattern(pattern)

    if not valid_files:
        return "", []

    reference_context = ""
    reference_files = []

    # Choose appropriate message function based on context
    # verify.py uses verifying_message for reference documents
    if purpose in ["reference", "CoVe answers"]:
        msg_func = verifying_message
        message = f"Reading {len(valid_files)} reference files"
        if purpose == "CoVe answers":
            message += " for CoVe answer stage"
        message += "..."
    else:
        msg_func = info_message
        message = f"Reading {len(valid_files)} {purpose} reference files..."

    click.echo(msg_func(message))

    for filepath in valid_files:
        try:
            file_content = read_document(filepath)
            filename = os.path.basename(filepath)
            reference_context += f"=== {filename} ===\n\n{file_content}\n\n"
            reference_files.append(filename)

            # Format success message based on options
            if show_char_count:
                msg = f"  - Read {filename} ({len(file_content):,} chars)"
            else:
                msg = f"  - Read {filename}"
                if purpose != "reference":
                    msg += f" for {purpose}"

            click.echo(success_message(msg))
        except Exception as e:
            click.echo(warning_message(f"  - Could not read {filepath}: {e}"))

    return reference_context, reference_files
