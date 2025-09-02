"""
Research file handling utilities for brainstorm command.

Handles research file loading, size analysis, and glob pattern expansion.
"""

import os
import glob
import click

from litassist.utils import count_tokens_and_words, info_message, warning_message


def analyze_research_size(research_contents: list, research_paths: list) -> dict:
    """
    Analyze the total size of research content and provide user feedback.

    Args:
        research_contents: List of research file contents
        research_paths: List of research file paths for reporting

    Returns:
        Dictionary with analysis results and combined content
    """
    if not research_contents:
        return {
            "combined_content": "",
            "total_tokens": 0,
            "total_words": 0,
            "file_count": 0,
            "exceeds_threshold": False,
        }

    # Combine all research content
    combined_content = "\n\nRESEARCH CONTEXT:\n" + "\n\n".join(research_contents)

    # Count tokens and words
    total_tokens, total_words = count_tokens_and_words(combined_content)

    # Define threshold (128k tokens as conservative estimate)
    TOKEN_THRESHOLD = 128_000
    exceeds_threshold = total_tokens > TOKEN_THRESHOLD

    # Display analysis to user
    click.echo(
        info_message(
            f"Research files loaded: {len(research_contents)} files, "
            f"{total_words:,} words, {total_tokens:,} tokens"
        )
    )

    if exceeds_threshold:
        click.echo(
            warning_message(
                f"Research content is very large ({total_tokens:,} tokens). "
                f"This may impact verification due to context window limits, but proceeding anyway."
            )
        )
        click.echo(
            info_message(
                "Consider using fewer or smaller research files if you encounter verification issues."
            )
        )

    return {
        "combined_content": combined_content,
        "total_tokens": total_tokens,
        "total_words": total_words,
        "file_count": len(research_contents),
        "exceeds_threshold": exceeds_threshold,
    }


def expand_glob_patterns(ctx, param, value):
    """Expand glob patterns in file paths."""
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
