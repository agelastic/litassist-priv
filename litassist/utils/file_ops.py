"""
File operations utilities.

This module provides functions for reading documents, validating file sizes,
and handling various file types used throughout LitAssist.
"""

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
