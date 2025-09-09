"""
Retry handling for LLM API calls with citation enhancement.

This module manages retry logic when initial API calls fail citation
verification, enhancing prompts and re-attempting with stricter instructions.
"""

from typing import List, Dict, Any, Tuple, Optional, Callable
from litassist.prompts import PROMPTS
from litassist.utils.formatting import error_message, info_message, success_message, warning_message
from . import api_handlers
from .response_parser import extract_content_and_usage


def should_retry_for_citations(error: Exception) -> bool:
    """
    Determine if an error warrants a retry with enhanced citation instructions.

    Args:
        error: The exception that occurred

    Returns:
        True if retry should be attempted, False otherwise
    """
    from litassist.citation_verify import CitationVerificationError

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

    retry_client = api_handlers.get_openai_client(model_name)

    if model in ["openai/o1-pro", "openai/o3-pro"]:
        # Special handling for reasoning models
        retry_filtered_params = get_model_parameters(model, params)

        retry_response = retry_client.chat.completions.create(
            model=model_name,
            messages=enhanced_messages,
            **retry_filtered_params,
        )

        # Check for API errors in response
        check_retry_response_errors(retry_response)
    else:
        # Standard model handling - filter parameters for all models
        retry_filtered_params = get_model_parameters(model, params)
        retry_response = retry_client.chat.completions.create(
            model=model_name, messages=enhanced_messages, **retry_filtered_params
        )

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


def execute_with_document_dropping(
    client,
    messages: List[Dict[str, Any]],
    documents: Optional[Dict[str, str]] = None,
    other_context: str = "",
    max_attempts: int = 5,
    rebuild_prompt_func: Optional[Callable] = None,
    skip_citation_verification: bool = False,
) -> Tuple[Any, Dict[str, Any]]:
    """
    Execute LLM call with automatic document dropping on token limit errors.
    
    This function attempts an LLM API call and automatically handles token/context
    limit errors by progressively dropping the largest documents until the call succeeds
    or all droppable documents are exhausted.
    
    Args:
        client: LLM client instance with complete() method
        messages: Initial messages list for the LLM call
        documents: Optional dict of {"doc_name": "content"} that can be dropped
        other_context: Non-droppable context that must always be included
        max_attempts: Maximum retry attempts (default 5)
        rebuild_prompt_func: Optional function to rebuild prompt with remaining docs
                            Signature: (documents, other_context) -> str
        skip_citation_verification: Pass through to client.complete()
    
    Returns:
        Tuple of (response, usage_dict) from successful API call
    
    Raises:
        Exception: If all documents are dropped and call still fails
    """
    # Track which documents we can drop
    droppable_docs = list(documents.items()) if documents else []
    attempts = 0
    response = None
    
    while response is None and attempts < max_attempts:
        try:
            # Try the API call
            response, usage = client.complete(
                messages, 
                skip_citation_verification=skip_citation_verification
            )
            return response, usage
            
        except Exception as e:
            error_str = str(e).lower()
            
            # Check if this is a token/context limit error
            if any(x in error_str for x in ['token', 'context', 'length', 'too long', 'maximum']):
                if droppable_docs:
                    # Find and drop the largest document
                    largest_idx = max(
                        range(len(droppable_docs)), 
                        key=lambda i: len(droppable_docs[i][1])
                    )
                    dropped_doc = droppable_docs.pop(largest_idx)
                    
                    print(warning_message(
                        f"Prompt exceeded token limit. Dropping largest document: {dropped_doc[0]}"
                    ))
                    
                    # Rebuild the prompt with remaining documents
                    if rebuild_prompt_func:
                        # Use custom rebuilder if provided
                        remaining_docs = dict(droppable_docs)
                        new_content = rebuild_prompt_func(remaining_docs, other_context)
                    else:
                        # Default rebuilding: concatenate remaining docs with other_context
                        doc_text = ""
                        if droppable_docs:
                            for doc_name, doc_content in droppable_docs:
                                doc_text += f"=== {doc_name} ===\n\n{doc_content}\n\n"
                        new_content = doc_text + other_context
                    
                    # Update the messages with new content
                    if messages and messages[-1].get("role") == "user":
                        messages[-1]["content"] = new_content
                    
                    attempts += 1
                else:
                    # No more documents to drop, re-raise the error
                    raise Exception(
                        f"Token limit exceeded even after dropping all documents: {e}"
                    )
            else:
                # Not a token limit error, re-raise
                raise
    
    # If we get here, we failed after max attempts
    if response is None:
        raise Exception(
            f"Failed to get response after {attempts} attempts dropping documents"
        )
