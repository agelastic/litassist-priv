"""
LLM package for LitAssist.

This package contains modules for LLM client functionality, API handling,
and related utilities.
"""

from .api_handlers import (
    get_openai_client,
    parse_openrouter_error,
    execute_api_call_with_retry,
    RetryableAPIError,
    StreamingAPIError,
    NonRetryableAPIError,
)

from .client import (
    LLMClient,
    LLMClientFactory,
    get_model_family,
    get_model_parameters,
    get_openrouter_params,
    supports_system_messages,
    convert_thinking_effort,
    convert_verbosity,
    MODEL_PATTERNS,
    PARAMETER_PROFILES,
)

from .verification import (
    LLMVerificationMixin,
    LLMVerificationClient,
)

# Re-export CONFIG for backward compatibility with tests
from litassist.config import CONFIG

__all__ = [
    # API handlers
    "get_openai_client",
    "parse_openrouter_error", 
    "execute_api_call_with_retry",
    "RetryableAPIError",
    "StreamingAPIError", 
    "NonRetryableAPIError",
    # Main client classes and functions
    "LLMClient",
    "LLMClientFactory", 
    "get_model_family",
    "get_model_parameters",
    "get_openrouter_params",
    "supports_system_messages",
    "convert_thinking_effort",
    "convert_verbosity",
    "MODEL_PATTERNS",
    "PARAMETER_PROFILES",
    # Verification classes
    "LLMVerificationMixin",
    "LLMVerificationClient",
    # Configuration (for backward compatibility with tests)
    "CONFIG",
]