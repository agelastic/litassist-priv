"""
Citation handling and verification for LLM responses.

This module manages citation verification workflows, including initial validation,
retry logic coordination, and issue reporting.
"""

from typing import Tuple, List, Optional, Any
from litassist.prompts import PROMPTS
from litassist.utils.formatting import warning_message
from litassist.citation.exceptions import CitationVerificationError


def handle_citation_verification(
    content: str,
    validate_func: Any,
    strict_mode: bool = True,
    skip_verification: bool = False,
) -> Tuple[str, Optional[List[str]]]:
    """
    Handle citation verification with appropriate warning messages.

    Args:
        content: The content to verify
        validate_func: Bound method to validate citations
        strict_mode: Whether to use strict verification mode
        skip_verification: Whether to skip verification entirely

    Returns:
        Tuple of (verified content, list of issues or None)

    Raises:
        CitationVerificationError: If strict mode verification fails
    """
    if skip_verification:
        return content, None

    # Perform verification
    verified_content, verification_issues = validate_func(
        content, strict_mode=strict_mode
    )

    # Handle any issues found
    if verification_issues:
        display_verification_warning(verification_issues[0])
        return verified_content, verification_issues

    return verified_content, None


def display_verification_warning(issue: str) -> None:
    """
    Display a warning message for citation verification issues.

    Args:
        issue: The verification issue to display
    """
    try:
        warning_msg = PROMPTS.get(
            "warnings.citation_verification_warning",
            issue=issue,
        )
    except (KeyError, ValueError):
        warning_msg = warning_message(f"Citation verification: {issue}")

    print(warning_msg)


def handle_retry_failure(retry_error: CitationVerificationError) -> None:
    """
    Handle the case when citation retry also fails.

    Args:
        retry_error: The error from the retry attempt

    Raises:
        CitationVerificationError: Always raises with comprehensive error message
    """
    try:
        retry_failed_msg = PROMPTS.get(
            "warnings.retry_also_failed", error=str(retry_error)
        )
        multiple_attempts_msg = PROMPTS.get("warnings.multiple_attempts_failed")
    except (KeyError, ValueError):
        from litassist.utils.formatting import error_message

        retry_failed_msg = error_message(f"Retry also failed: {str(retry_error)}")
        multiple_attempts_msg = (
            "CRITICAL: Multiple attempts to generate content with verified citations failed. "
            "The AI model is consistently generating unverifiable legal citations. "
            "Manual intervention required."
        )

    print(retry_failed_msg)
    raise CitationVerificationError(multiple_attempts_msg)


def determine_strict_mode(client_instance: Any) -> bool:
    """
    Determine whether to use strict citation verification mode.

    Args:
        client_instance: The LLM client instance

    Returns:
        True for strict mode, False for lenient mode
    """
    # For commands like lookup that have enforce_citations=False, use lenient mode
    return getattr(client_instance, "_enforce_citations", True)


def process_citation_verification(
    content: str, client_instance: Any, skip_verification: bool = False
) -> Tuple[str, Optional[List[str]]]:
    """
    Complete citation verification workflow for LLM responses.

    Args:
        content: The content to verify
        client_instance: The LLM client instance with validate_and_verify_citations method
        skip_verification: Whether to skip verification

    Returns:
        Tuple of (verified content, list of issues or None)

    Raises:
        CitationVerificationError: If strict mode verification fails
    """
    if skip_verification:
        return content, None

    strict_mode = determine_strict_mode(client_instance)

    return handle_citation_verification(
        content=content,
        validate_func=client_instance.validate_and_verify_citations,
        strict_mode=strict_mode,
        skip_verification=False,
    )
