"""
JSON sanitization utilities for logging.

Handles conversion of non-serializable objects for JSON logging.
"""

from unittest.mock import Mock


def sanitize_for_json(obj):
    """
    Recursively sanitize an object for JSON serialization.

    Handles Mock objects and other non-serializable types.
    Also filters out combined_content from research_analysis.

    Args:
        obj: Object to sanitize

    Returns:
        JSON-serializable version of the object
    """
    if isinstance(obj, Mock):
        return str(obj)
    elif isinstance(obj, dict):
        # Special handling for research_analysis with combined_content
        if "combined_content" in obj and all(
            key in obj for key in ["total_tokens", "total_words", "file_count"]
        ):
            # This looks like research_analysis - filter out combined_content
            return {
                k: sanitize_for_json(v)
                for k, v in obj.items()
                if k != "combined_content"
            }
        else:
            return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif hasattr(obj, "__dict__"):
        # For objects with attributes, convert to dict representation
        return sanitize_for_json(obj.__dict__)
    else:
        # For primitive types and strings
        return obj
