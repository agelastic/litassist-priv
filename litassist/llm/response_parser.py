"""
Response parsing utilities for LLM API responses.

This module handles extraction and cleaning of content and usage data
from various LLM API response formats.
"""

from typing import Dict, Any, Tuple


def extract_content_and_usage(response: Any) -> Tuple[str, Dict[str, Any]]:
    """
    Extract content and usage information from an LLM API response.

    Args:
        response: The API response object from OpenAI/OpenRouter

    Returns:
        Tuple of (content string, usage dictionary)
    """
    # Extract content from chat response
    content = ""
    if hasattr(response, "choices") and response.choices:
        message = response.choices[0].message
        content = message.content or ""

    # Extract usage data with multiple format handling
    usage = extract_usage_data(response)

    return content, usage


def extract_usage_data(response: Any) -> Dict[str, Any]:
    """
    Extract usage data from various response formats.

    Handles OpenAI v1.x object formats with model_dump(), dict(),
    or direct attribute access.

    Args:
        response: The API response object

    Returns:
        Dictionary with prompt_tokens, completion_tokens, total_tokens
    """
    usage = getattr(response, "usage", {})

    # Handle various usage object formats
    if hasattr(usage, "model_dump"):
        usage = usage.model_dump()
    elif hasattr(usage, "dict"):
        usage = usage.dict()
    elif not isinstance(usage, dict):
        # Convert object attributes to dict
        usage = {
            "prompt_tokens": getattr(usage, "prompt_tokens", 0),
            "completion_tokens": getattr(usage, "completion_tokens", 0),
            "total_tokens": getattr(usage, "total_tokens", 0),
        }

    # Ensure all required keys exist
    usage.setdefault("prompt_tokens", 0)
    usage.setdefault("completion_tokens", 0)
    usage.setdefault("total_tokens", 0)

    return usage
