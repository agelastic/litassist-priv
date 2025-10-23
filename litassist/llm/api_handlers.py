"""
API handling utilities for LLM client interactions.

This module provides specialized API client management, error parsing, and retry logic
for LLM API calls across different providers. It focuses on robust error handling,
provider-specific client configuration, and automatic retry mechanisms for transient
failures.

Key Components:
    - OpenAI client creation with OpenRouter/direct API routing
    - OpenRouter error parsing with detailed error classification
    - Retry logic with exponential backoff for API resilience

Usage:
    These functions are primarily used internally by the LLMClient class but can
    be imported independently for specialized API handling scenarios.
"""

import json
import logging
import os
from typing import Dict, Any, Tuple

import click
import requests
import tenacity

from litassist.config import get_config
from litassist.logging import log_task_event
from litassist.utils.formatting import warning_message


# Custom exception classes for retry logic
class RetryableAPIError(Exception):
    """Custom exception for retryable API errors."""

    pass


class StreamingAPIError(Exception):
    """Custom exception for streaming-related API errors."""

    pass


class NonRetryableAPIError(Exception):
    """Errors that should not be retried (413, 400 with specific messages)."""

    pass


logger = logging.getLogger(__name__)


def get_openai_client(model_name: str):
    """
    Get or create OpenAI client with appropriate configuration.

    ALL models are routed through OpenRouter. No exceptions.

    Args:
        model_name: The model identifier (e.g., 'openai/gpt-4', 'anthropic/claude-sonnet-4')

    Returns:
        Configured OpenAI client instance routed through OpenRouter

    Note:
        - ALL LLM calls go through OpenRouter
        - Model names with "/" indicate OpenRouter routing
        - No fallback or direct OpenAI API path exists
    """
    # Lazy import to avoid loading OpenAI library when not needed
    from openai import OpenAI

    # ALL models go through OpenRouter - single code path only
    config = get_config()
    base_url = config.or_base
    api_key = config.or_key
    return OpenAI(api_key=api_key, base_url=base_url)


def parse_openrouter_error(error_info: Dict[str, Any]) -> Tuple[str, str]:
    """
    Parse Google API errors from OpenRouter response.

    OpenRouter provides detailed error information from underlying providers like Google
    in a nested format. This function extracts and classifies these errors to provide
    actionable error messages and appropriate retry behavior.

    Args:
        error_info: Error information dictionary from OpenRouter response

    Returns:
        tuple: (error_type, error_message) where error_type is one of:
               'auth', 'quota', 'rate_limit', 'billing', 'disabled',
               'permission', 'context_length', 'other'

    Error Classifications:
        - auth: Authentication failures, invalid API keys
        - quota: API quota exceeded
        - rate_limit: Rate limiting (retryable)
        - billing: Billing not enabled or payment required
        - disabled: API not enabled in project
        - permission: Permission denied for other reasons
        - context_length: Request too long (non-retryable)
        - other/unknown: Unclassified errors
    """
    # Default to generic message
    error_msg = error_info.get("message", "Unknown API error")

    # Check OpenRouter-level errors first
    if "maximum context length" in error_msg:
        return "context_length", error_msg

    # Try to parse the raw Google error
    if "metadata" in error_info and "raw" in error_info["metadata"]:
        raw_error = error_info["metadata"]["raw"]

        try:
            raw_obj = json.loads(raw_error)
            if "error" in raw_obj:
                google_error = raw_obj["error"]
                status = google_error.get("status", "")
                code = google_error.get("code", 0)
                message = google_error.get("message", "")

                # Check for API key issues regardless of status code
                if "API key" in message or "api key" in message.lower():
                    if (
                        "expired" in message.lower()
                        or "invalid" in message.lower()
                        or "not valid" in message.lower()
                    ):
                        return (
                            "auth",
                            f"Google API authentication failed: {message}",
                        )

                # Also check INVALID_ARGUMENT status specifically
                if status == "INVALID_ARGUMENT" and (
                    "key" in message.lower() or "token" in message.lower()
                ):
                    return "auth", f"Google API authentication failed: {message}"

                # Determine error type by status code and status field
                if status == "UNAUTHENTICATED" or code == 401:
                    return "auth", f"Google API authentication failed: {message}"

                elif status == "RESOURCE_EXHAUSTED" or code == 429:
                    if "quota" in message.lower():
                        return "quota", f"Google API quota exceeded: {message}"
                    else:
                        return "rate_limit", f"Google API rate limit hit: {message}"

                elif status == "PERMISSION_DENIED" or code == 403:
                    if "billing" in message.lower():
                        return (
                            "billing",
                            f"Google API billing not enabled: {message}",
                        )
                    elif (
                        "disabled" in message.lower()
                        or "not been used" in message.lower()
                    ):
                        return (
                            "disabled",
                            f"Google API not enabled in project: {message}",
                        )
                    else:
                        return (
                            "permission",
                            f"Google API permission denied: {message}",
                        )

                else:
                    return "other", f"Google API error ({status}): {message}"

        except (json.JSONDecodeError, TypeError):
            # Can't parse, check for auth issue using more specific patterns
            if "UNAUTHENTICATED" in raw_error:
                return "auth", "Google API authentication failed"

    return "unknown", error_msg


def execute_api_call_with_retry(
    model_name: str,
    messages: list,
    filtered_params: dict,
    get_openai_client_func=None,
    call_context=None,
) -> Any:
    """
    Execute API call with comprehensive retry logic and error handling.

    This function implements a robust retry mechanism for LLM API calls, handling
    various types of transient and permanent errors. It uses exponential backoff
    for retryable errors and provides detailed error classification and guidance.

    Args:
        model_name: The model identifier for the API call
        messages: List of message dictionaries for the chat completion
        filtered_params: Parameters dictionary filtered for model compatibility
        get_openai_client_func: Optional function to get OpenAI client (defaults to module function)

    Returns:
        API response object from successful completion

    Raises:
        RetryableAPIError: For errors that should be retried (rate limits, overload)
        NonRetryableAPIError: For errors that shouldn't be retried (413, context length)
        StreamingAPIError: For streaming-related errors
        Exception: For other API errors with detailed messages

    Retry Behavior:
        - Retries up to 5 times with exponential backoff
        - No wait time during tests (PYTEST_CURRENT_TEST environment variable)
        - Retries on connection errors, rate limits, and overload conditions
        - Stops immediately on context length, authentication, and other permanent errors
    """
    # Use module function if not provided
    if get_openai_client_func is None:
        get_openai_client_func = get_openai_client

    # Lazy import OpenAI exceptions to avoid loading library when not needed
    from openai import APIConnectionError, RateLimitError, APIError

    # Define retryable error types
    retry_errors = (
        APIConnectionError,
        RateLimitError,
        APIError,
        requests.exceptions.ConnectionError,
        RetryableAPIError,
        requests.ConnectionError,
        requests.Timeout,
    )

    # Use no wait time during tests to speed up retry tests
    wait_config = (
        tenacity.wait_none()  # No wait in tests
        if os.environ.get("PYTEST_CURRENT_TEST")
        else tenacity.wait_exponential(multiplier=0.5, max=10)
    )

    def _call_with_streaming_wrap():
        """Internal wrapper for API call with comprehensive error handling."""
        # Avoid circular import by importing locally
        from .parameter_handler import get_openrouter_params

        try:
            # Get the appropriate client
            client = get_openai_client_func(model_name)

            # Announce outbound LLM call if context provided
            if call_context:
                try:
                    log_task_event(
                        call_context.get("command", "llm"),
                        call_context.get("stage", "call"),
                        "llm_call",
                        f"Calling model {model_name}",
                        {"model": model_name},
                    )
                except Exception:
                    pass

            # Extract OpenRouter-specific parameters that need to go in extra_body
            extra_body = {}
            # Get OpenRouter-specific parameters from centralized definition
            openrouter_params = get_openrouter_params()
            for param in openrouter_params:
                if param in filtered_params:
                    extra_body[param] = filtered_params.pop(param)

            # Create the request with extra_body for OpenRouter parameters
            if extra_body:
                resp = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    extra_body=extra_body,
                    **filtered_params,
                )
            else:
                resp = client.chat.completions.create(
                    model=model_name, messages=messages, **filtered_params
                )

            # Check for error in the response object (OpenRouter v1.x pattern)
            if hasattr(resp, "error") and resp.error:
                error_info = resp.error
                if isinstance(error_info, dict):
                    # Parse the error properly
                    error_type, error_msg = parse_openrouter_error(error_info)

                    # Provide specific guidance based on error type
                    if error_type == "auth":
                        raise Exception(
                            f"{error_msg}. Please configure your Google API key at https://openrouter.ai/settings/keys"
                        )
                    elif error_type == "quota":
                        raise Exception(
                            f"{error_msg}. Consider waiting or upgrading your Google API quota"
                        )
                    elif error_type == "rate_limit":
                        raise RetryableAPIError(f"{error_msg}. Will retry after delay")
                    elif error_type == "billing":
                        raise Exception(
                            f"{error_msg}. Enable billing at https://console.cloud.google.com/billing"
                        )
                    elif error_type == "disabled":
                        raise Exception(
                            f"{error_msg}. Enable the API in your Google Cloud project"
                        )
                    elif error_type == "context_length":
                        raise NonRetryableAPIError(
                            f"{error_msg}. Reduce document size or use selective mode"
                        )
                    else:
                        raise Exception(f"API Error: {error_msg}")

            # Check for API-level errors in response (overloaded, rate limit, etc.)
            if (
                hasattr(resp, "choices")
                and resp.choices
                and hasattr(resp.choices[0], "error")
                and resp.choices[0].error
            ):
                error_info = resp.choices[0].error
                error_msg = error_info.get("message", "Unknown API error")
                # Retry on overloaded, rate limit, busy, timeout
                if any(
                    kw in error_msg.lower()
                    for kw in ["overloaded", "rate limit", "timeout", "busy"]
                ):
                    raise RetryableAPIError(f"API Error: {error_msg}")
                else:
                    raise Exception(f"API Error: {error_msg}")
            # Announce inbound LLM response if context provided
            if call_context:
                try:
                    has_choices = hasattr(resp, "choices") and bool(resp.choices)
                    log_task_event(
                        call_context.get("command", "llm"),
                        call_context.get("stage", "call"),
                        "llm_response",
                        f"Received response from model {model_name}",
                        {"model": model_name, "has_choices": has_choices},
                    )
                except Exception:
                    pass
            return resp

        except Exception as e:
            # Check if it's a 413 or similar non-retryable error
            error_str = str(e)
            if any(
                phrase in error_str.lower()
                for phrase in [
                    "413",
                    "payload too large",
                    "prompt is too long",
                    "request entity too large",
                ]
            ):
                raise NonRetryableAPIError(f"Request too large: {error_str}")

            # Also check response codes in the error if available
            if hasattr(e, "response") and hasattr(e.response, "status_code"):
                if e.response.status_code == 413:
                    raise NonRetryableAPIError(f"HTTP 413: {error_str}")

            # Check for specific OpenAI error types
            if hasattr(e, "error") and isinstance(e.error, dict):
                error_code = e.error.get("code", 0)
                if error_code == 413:
                    raise NonRetryableAPIError(f"API Error 413: {error_str}")

            # Retry on "Error processing stream" or similar streaming errors
            if (
                "Error processing stream" in error_str
                or "streaming" in error_str.lower()
            ):
                raise StreamingAPIError(error_str)
            raise

    def before_retry_callback(retry_state):
        """Show retry attempts to user for better visibility."""
        if retry_state.attempt_number > 1:
            try:
                error = retry_state.outcome.exception()
                error_str = str(error)
                
                # Log retry attempt (CLAUDE.md requirement: log all retries)
                from litassist.logging import save_log
                import time
                save_log("llm_retry_attempt", {
                    "attempt": retry_state.attempt_number,
                    "total_attempts": 5,
                    "model": model_name,
                    "error_type": type(error).__name__,
                    "error_message": error_str[:1000],  # Truncate for summary
                    "full_error": error_str,  # Full error for debugging
                    "messages": messages,  # Full request being retried
                    "params": filtered_params,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                })
                
                # Show user-friendly retry messages for common errors
                if "500" in error_str or "InternalServerError" in str(type(error).__name__):
                    click.echo(warning_message(
                        f"Server error (attempt {retry_state.attempt_number}/5), retrying..."
                    ))
                elif "rate" in error_str.lower() or "429" in error_str:
                    click.echo(warning_message(
                        f"Rate limit hit (attempt {retry_state.attempt_number}/5), waiting..."
                    ))
                elif "timeout" in error_str.lower() or "connection" in error_str.lower():
                    click.echo(warning_message(
                        f"Connection issue (attempt {retry_state.attempt_number}/5), retrying..."
                    ))
            except Exception:
                # If we can't get error details, just show generic retry message
                if retry_state.attempt_number > 1:
                    click.echo(warning_message(
                        f"API error (attempt {retry_state.attempt_number}/5), retrying..."
                    ))

    @tenacity.retry(
        stop=tenacity.stop_after_attempt(5),
        wait=wait_config,
        retry=(
            tenacity.retry_if_exception_type(retry_errors)
            | tenacity.retry_if_exception_type(StreamingAPIError)
        ),
        before=before_retry_callback,
        before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    def _call():
        """Decorated retry wrapper function."""
        return _call_with_streaming_wrap()

    try:
        return _call()
    except Exception as e:
        # Log final failure after all retries exhausted
        from litassist.logging import save_log
        import time
        save_log("llm_final_failure", {
            "model": model_name,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "messages": messages,
            "params": filtered_params,
            "total_attempts": 5,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
        raise
