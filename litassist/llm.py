"""LitAssist LLM module - Backward compatibility wrapper.

This file maintains backward compatibility by importing all components from the
new modular structure. All existing code that imports from litassist.llm will
continue to work without changes.

The actual implementation is now split across multiple modules:
- llm/exceptions.py: Exception classes
- llm/model_config.py: Model configuration and parameter management
- llm/client_factory.py: Factory pattern for creating LLM clients
- llm/api_handlers.py: API interaction and error handling
- llm/verification.py: Verification and citation validation
- llm/client.py: Core LLMClient implementation
"""

import logging

# Import all exceptions
from litassist.llm.exceptions import (
    RetryableAPIError,
    StreamingAPIError,
    NonRetryableAPIError,
    ModelNotFoundError,
    VerificationError,
    CitationValidationError,
)

# Import model configuration functions and constants
from litassist.llm.model_config import (
    MODEL_PATTERNS,
    PARAMETER_PROFILES,
    REASONING_MODELS,
    get_model_family,
    supports_system_messages,
    convert_thinking_effort,
    convert_verbosity,
    get_model_parameters,
    is_reasoning_model,
    get_default_parameters,
)

# Import factory
from litassist.llm.client_factory import LLMClientFactory

# Import API handlers
from litassist.llm.api_handlers import (
    get_openai_client,
    parse_openrouter_error,
    execute_api_call_with_retry,
)

# Import verification components
from litassist.llm.verification import (
    LLMVerificationMixin,
    LLMVerificationClient,
)

# Import main client
from litassist.llm.client import LLMClient

# Set up module logger
logger = logging.getLogger(__name__)

# Export all public components for backward compatibility
__all__ = [
    # Exceptions
    "RetryableAPIError",
    "StreamingAPIError",
    "NonRetryableAPIError",
    "ModelNotFoundError",
    "VerificationError",
    "CitationValidationError",
    # Model configuration
    "MODEL_PATTERNS",
    "PARAMETER_PROFILES",
    "REASONING_MODELS",
    "get_model_family",
    "supports_system_messages",
    "convert_thinking_effort",
    "convert_verbosity",
    "get_model_parameters",
    "is_reasoning_model",
    "get_default_parameters",
    # Factory
    "LLMClientFactory",
    # API handlers
    "get_openai_client",
    "parse_openrouter_error",
    "execute_api_call_with_retry",
    # Verification
    "LLMVerificationMixin",
    "LLMVerificationClient",
    # Main client
    "LLMClient",
]

# Log successful module initialization
logger.debug("LLM module initialized with modular architecture")