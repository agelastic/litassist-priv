"""
Research file handling utilities for brainstorm command.

Handles research file loading, size analysis, and glob pattern expansion.
"""

import click

from litassist.utils.text_processing import count_tokens_and_words
from litassist.utils.formatting import info_message, warning_message


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
