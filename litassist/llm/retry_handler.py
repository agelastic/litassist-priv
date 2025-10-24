"""
Retry handling for LLM API calls with citation enhancement.

This module manages retry logic when initial API calls fail citation
verification, enhancing prompts and re-attempting with stricter instructions.
"""

from typing import List, Dict, Any, Tuple, Optional
from litassist.prompts import PROMPTS
from litassist.utils.formatting import error_message, info_message, success_message
from .response_parser import extract_content_and_usage


def should_retry_for_citations(error: Exception) -> bool:
    """
    Determine if an error warrants a retry with enhanced citation instructions.

    Args:
        error: The exception that occurred

    Returns:
        True if retry should be attempted, False otherwise
    """
    from litassist.citation.exceptions import CitationVerificationError

    # Only retry for citation verification errors
    return isinstance(error, CitationVerificationError)


def enhance_messages_for_retry(
    messages: List[Dict[str, Any]], model: str
) -> List[Dict[str, Any]]:
    """
    Enhance messages with strict citation instructions for retry.

    Args:
        messages: Original message list
        model: Model name for model-specific handling

    Returns:
        Enhanced message list with citation instructions
    """
    enhanced_messages = messages.copy()
    citation_instructions = PROMPTS.get("verification.citation_retry_instructions")

    # For both o3 and regular models, append to user message
    if enhanced_messages and enhanced_messages[-1].get("role") == "user":
        enhanced_messages[-1]["content"] += f"\n\n{citation_instructions}"

    return enhanced_messages


def execute_retry_request(
    model: str,
    model_name: str,
    enhanced_messages: List[Dict[str, Any]],
    params: Dict[str, Any],
) -> Tuple[Any, str, Dict[str, Any]]:
    """
    Execute a retry request with enhanced messages.

    Args:
        model: Full model identifier (e.g., "openai/o3-pro")
        model_name: Model name for API call
        enhanced_messages: Messages with citation instructions added
        params: Model parameters

    Returns:
        Tuple of (response object, content string, usage dict)
    """
    # Import here to avoid circular dependency
    from .client import get_model_parameters
    from .api_handlers import execute_api_call_with_retry
    
    # Get filtered parameters for the model
    retry_filtered_params = get_model_parameters(model, params)
    
    # Use the existing API handler which properly handles extra_body
    retry_response = execute_api_call_with_retry(
        model_name=model_name,
        messages=enhanced_messages,
        filtered_params=retry_filtered_params
    )
    
    # Check for API errors in response
    check_retry_response_errors(retry_response)
    
    # Extract content and usage
    content, usage = extract_content_and_usage(retry_response)
    return retry_response, content, usage


def check_retry_response_errors(response: Any) -> None:
    """
    Check for errors in retry response and raise if found.

    Args:
        response: The retry response object

    Raises:
        Exception: If errors are detected in response
    """
    # Check for error in choices
    if (
        hasattr(response, "choices")
        and response.choices
        and hasattr(response.choices[0], "error")
        and response.choices[0].error
    ):
        error_info = response.choices[0].error
        error_msg = error_info.get("message", "Unknown API error")
        raise Exception(f"API Error on retry: {error_msg}")

    # Check for error finish_reason
    if (
        hasattr(response, "choices")
        and response.choices
        and hasattr(response.choices[0], "finish_reason")
        and response.choices[0].finish_reason == "error"
    ):
        if hasattr(response.choices[0], "error"):
            error_info = response.choices[0].error
            error_msg = error_info.get("message", "Unknown API error")
            raise Exception(f"API retry request failed: {error_msg}")
        else:
            raise Exception("API retry request failed with error finish_reason")


def handle_citation_retry(
    error: Exception,
    model: str,
    model_name: str,
    messages: List[Dict[str, Any]],
    params: Dict[str, Any],
    validate_func: Any,
) -> Tuple[str, Dict[str, Any], Optional[List[str]]]:
    """
    Handle a complete citation retry workflow.

    Args:
        error: The CitationVerificationError that triggered retry
        model: Full model identifier
        model_name: Model name for API
        messages: Original messages
        params: Model parameters
        validate_func: Function to validate citations (bound method)

    Returns:
        Tuple of (verified content, usage dict, list of issues or None)
    """
    # Display retry messages
    try:
        strict_failed_msg = PROMPTS.get("warnings.strict_mode_failed", error=str(error))
        retrying_msg = PROMPTS.get("warnings.retrying_with_instructions")
    except (KeyError, ValueError):
        strict_failed_msg = error_message(str(error))
        retrying_msg = info_message("Retrying with enhanced citation instructions...")

    print(strict_failed_msg)
    print(retrying_msg)

    # Enhance messages
    enhanced_messages = enhance_messages_for_retry(messages, model)

    # Execute retry
    _, retry_content, retry_usage = execute_retry_request(
        model, model_name, enhanced_messages, params
    )

    # Verify the retry
    verified_retry_content, retry_issues = validate_func(
        retry_content, strict_mode=True
    )

    # Display success message if there were issues
    if retry_issues:
        try:
            success_msg = PROMPTS.get(
                "warnings.retry_successful", issue=retry_issues[0]
            )
        except (KeyError, ValueError):
            success_msg = success_message(
                f"Retry successful. Remaining issue addressed: {retry_issues[0]}"
            )
        print(success_msg)

    return verified_retry_content, retry_usage, retry_issues
