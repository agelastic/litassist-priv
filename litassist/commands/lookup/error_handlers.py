"""
Error handling utilities for the lookup command.

This module provides specific error handling and user guidance for various
types of errors that can occur during lookup operations.
"""

import click
import time
import os
from litassist.utils.formatting import (
    warning_message,
    error_message,
    info_message,
    tip_message,
)
from litassist.logging import LOG_DIR


def handle_llm_error(error_str, contents=None):
    """Handle different types of LLM errors with specific guidance."""
    if "quota exceeded" in error_str.lower():
        click.echo(
            error_message(
                "Google API quota exceeded. Options:\n"
                "  - Wait until quota resets (usually daily)\n"
                "  - Upgrade your Google API quota limits\n"
                "  - Use --no-fetch to skip content fetching\n"
                "  - Try again later with smaller document sets"
            )
        )
    elif "billing not enabled" in error_str.lower():
        click.echo(
            error_message(
                "Google API billing not enabled. To fix:\n"
                "  1. Go to https://console.cloud.google.com/billing\n"
                "  2. Enable billing for your project\n"
                "  3. Ensure the Generative Language API is enabled"
            )
        )
    elif "api not enabled" in error_str.lower() or "disabled" in error_str.lower():
        click.echo(
            error_message(
                "Google Generative Language API not enabled. To fix:\n"
                "  1. Go to Google Cloud Console\n"
                "  2. Enable 'Generative Language API'\n"
                "  3. Verify your API key has access"
            )
        )
    elif "authentication failed" in error_str.lower():
        click.echo(
            error_message(
                "Google API authentication failed. To fix:\n"
                "  1. Go to https://openrouter.ai/settings/keys\n"
                "  2. Add your Google API key (BYOK)\n"
                "  3. Enable 'Always use this key' for google/gemini models"
            )
        )
    elif "maximum context length" in error_str.lower():
        click.echo(
            error_message(
                "Context length exceeded (>1M tokens). Try:\n"
                "  - Using standard mode instead of --comprehensive\n"
                "  - Using --no-fetch to analyze only search results\n"
                "  - Reducing the number of documents fetched"
            )
        )
    elif "choices" in error_str.lower():
        click.echo(
            error_message(
                "API response format error. This usually means:\n"
                "  - Request was too large (token limit exceeded)\n"
                "  - API timeout or rate limit\n"
                "  - Service temporarily unavailable"
            )
        )

        # Save fetched content so user doesn't lose it
        if contents:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            error_file = os.path.join(LOG_DIR, f"lookup_error_content_{timestamp}.txt")
            with open(error_file, "w", encoding="utf-8") as f:
                f.write(f"Error: {error_str}\n\n")
                f.write("\n=== FETCHED CONTENT (saved for retry) ===\n\n")
                f.write("\n".join(contents))
            click.echo(info_message("Fetched content saved to logs for manual review"))

    elif "token" in error_str.lower() or "limit" in error_str.lower():
        click.echo(
            error_message(
                "Token limit exceeded. Try:\n"
                "  - Using --no-fetch to skip content fetching\n"
                "  - Reducing search scope\n"
                "  - Using standard mode instead of --comprehensive"
            )
        )
    elif "timeout" in error_str.lower():
        click.echo(
            error_message(
                "Request timed out. The content was likely too large. "
                "Try again with fewer sources."
            )
        )
    elif "Citation verification failed" in error_str:
        click.echo(warning_message("Citation verification issues detected"))
    else:
        click.echo(error_message(f"LLM API error: {error_str}"))

    # Don't lose all the work - offer recovery options
    if contents:
        click.echo(
            tip_message(
                "Tip: Use 'litassist lookup --no-fetch' with the same query to analyze "
                "just the search results without fetching content"
            )
        )


def check_model_token_limits(client, total_request_tokens):
    """Check if request size exceeds model token limits and warn/truncate if needed."""
    # Check against known model limits
    model_limits = {
        "gemini": 1000000,  # 1M tokens
        "claude": 200000,  # 200k tokens
        "gpt-4": 128000,  # 128k tokens
    }

    # Get model type from client
    model_type = "unknown"
    if hasattr(client, "model") and hasattr(client.model, "lower"):
        model_str = client.model.lower()
        if "gemini" in model_str:
            model_type = "gemini"
        elif "claude" in model_str:
            model_type = "claude"
        elif "gpt" in model_str:
            model_type = "gpt-4"

    max_tokens = model_limits.get(model_type, 100000)  # Conservative default

    if total_request_tokens > max_tokens * 0.9:  # 90% safety margin
        click.echo(
            warning_message(
                f"Request size ({int(total_request_tokens):,} tokens) exceeds safe limit for {model_type}. "
                f"Truncating content..."
            )
        )
        return True, max_tokens

    return False, max_tokens


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
