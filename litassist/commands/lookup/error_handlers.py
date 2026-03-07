"""
Error handling utilities for the lookup command.

This module provides specific error handling and user guidance for various
types of errors that can occur during lookup operations.
"""

import click
from litassist.utils.formatting import (
    warning_message,
)


def warn_large_content_non_gemini(client, estimated_tokens):
    """Warn if using large content with non-Gemini models."""
    if estimated_tokens > 200000:
        # Check if we're not using Gemini
        if not hasattr(client, "model") or "gemini" not in client.model.lower():
            click.echo(
                warning_message(
                    f"Large content ({int(estimated_tokens):,} tokens) with non-Gemini model. "
                    "Consider using Gemini 2.5 Pro for better handling of large contexts."
                )
            )
