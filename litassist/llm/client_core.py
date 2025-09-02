"""
Core LLM Client for LitAssist.

This module provides the core LLMClient class with essential functionality for chat completions
across different LLM providers. Verification logic is provided by the LLMVerificationMixin.
"""

import os
import re
import time
from typing import List, Dict, Any, Tuple

from litassist.utils import (
    timed,
    save_log,
    heartbeat,
    info_message,
    warning_message,
    success_message,
    error_message,
)
from litassist.config import CONFIG
from litassist.prompts import PROMPTS
from .api_handlers import execute_api_call_with_retry
from .verification import LLMVerificationMixin

import logging

logger = logging.getLogger(__name__)


# Model family patterns for dynamic parameter handling
MODEL_PATTERNS = {
    "openai_reasoning": r"openai/o\d+",  # Matches o1, o3, o1-pro, o3-pro, o4, etc.
    "gpt5": r"openai/gpt-5",  # GPT-5 specific (August 2025)
    "claude4": r"anthropic/claude-(opus-4|sonnet-4)",  # Claude 4 models
    "anthropic": r"anthropic/claude",  # Other Claude models
    "google": r"google/(gemini|palm|bard)",
    "openai_standard": r"openai/(gpt|chatgpt)",  # GPT-4, ChatGPT, etc.
    "xai": r"x-ai/grok",
    "meta": r"meta/(llama|codellama)",
    "mistral": r"mistral/",
    "cohere": r"cohere/",
    "moonshotai": r"moonshotai/",
}

# Parameter profiles by model family
PARAMETER_PROFILES = {
    "openai_reasoning": {
        "allowed": [
            "max_completion_tokens",
            "reasoning",  # OpenRouter reasoning object
            "verbosity",  # GPT-5 and newer models
            "seed",
            "response_format",
            "structured_outputs",
        ],
        "transforms": {
            "max_tokens": "max_completion_tokens",
        },
        "system_message_support": False,  # o1/o3 models don't support system messages
    },
    "anthropic": {
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "top_k",
            "stream",
            "metadata",
            "stop_sequences",
            "reasoning",  # OpenRouter reasoning object
            # Advanced parameters
            "min_p",
            "top_a",
            "repetition_penalty",
        ],
        "transforms": {},
    },
    "google": {
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "candidate_count",
            "top_k",
            "safety_settings",
            "stop_sequences",
            "reasoning",  # OpenRouter reasoning object (if supported)
            # Advanced parameters
            "min_p",
            "top_a",
        ],
        "transforms": {},
    },
    "openai_standard": {
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "frequency_penalty",
            "presence_penalty",
            "stop",
            "logit_bias",
            "seed",
            "response_format",
            "stream",
            "n",
            "tools",
            "tool_choice",
            "functions",
            "function_call",
            "user",
            "logprobs",
            "top_logprobs",
        ],
    },
    "xai": {
        # OpenRouter-specific parameters (min_p, top_a, repetition_penalty) are handled
        # through extra_body in api_handlers.py, not as direct parameters
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "frequency_penalty",
            "presence_penalty",
            "stream",
            "reasoning",  # Grok models support reasoning
            "verbosity",
            # OpenRouter-specific params removed from here, handled via extra_body
        ],
    },
    "meta": {
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "frequency_penalty",
            "presence_penalty",
            "stream",
            "min_p",
            "top_a",
            "repetition_penalty",
        ],
    },
    "mistral": {
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "random_seed",
            "safe_mode",
            "stream",
            "min_p",
            "top_a",
            "repetition_penalty",
        ],
        "transforms": {"seed": "random_seed"},
    },
    "cohere": {
        "allowed": [
            "temperature",
            "max_tokens",
            "k",
            "p",
            "stop_sequences",
            "frequency_penalty",
            "presence_penalty",
            "stream",
        ],
        "transforms": {"top_k": "k", "top_p": "p", "stop": "stop_sequences"},
    },
    "moonshotai": {
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "frequency_penalty",
            "presence_penalty",
            "stream",
            "min_p",
            "top_a",
            "repetition_penalty",
        ],
    },
    "default": {
        "allowed": ["temperature", "top_p", "max_tokens", "stop"],  # Safe defaults
    },
}


def convert_thinking_effort(
    effort: str, model_name: str, use_openrouter: bool = True
) -> dict:
    """
    Convert universal thinking_effort to OpenRouter's reasoning object format.

    Args:
        effort: Universal effort level (none, minimal, low, medium, high, max)
        model_name: Full model name (e.g., "openai/o3-pro", "anthropic/claude-4")
        use_openrouter: Whether routing through OpenRouter (default True)

    Returns:
        Dict with OpenRouter reasoning object or vendor-specific parameters
    """
    if effort == "none":
        return {}  # Don't send reasoning parameter

    # OpenRouter unified reasoning object approach
    if use_openrouter:
        model_family = get_model_family(model_name)

        # Check model type for appropriate sub-parameters
        if model_family in ["openai_reasoning", "gpt5", "xai"]:
            # Effort-based models (OpenAI, Grok, GPT-5)
            effort_map = {
                "minimal": "minimal",  # GPT-5 specific
                "low": "low",
                "medium": "medium",
                "high": "high",
                "max": "high",  # Map max to highest available
            }
            mapped_effort = effort_map.get(effort, "medium")

            # Only include minimal for GPT-5 and o4-mini
            if (
                mapped_effort == "minimal"
                and model_family not in ["gpt5"]
                and "o4" not in model_name
            ):
                mapped_effort = "low"  # Fallback for non-GPT-5/o4 models

            # Special handling for o4-mini with summary field
            if "o4" in model_name:
                return {
                    "reasoning": {
                        "effort": mapped_effort,
                        "summary": "auto",  # New o4 feature for automatic summarization
                    }
                }
            # GPT-5 supports both reasoning and verbosity
            elif model_family == "gpt5":
                return {
                    "reasoning": {"effort": mapped_effort}
                    # Verbosity handled separately via convert_verbosity
                }
            else:
                return {"reasoning": {"effort": mapped_effort}}

        elif model_family in ["claude4", "anthropic"]:
            # Token-based models (Anthropic)
            token_map = {
                "minimal": 1024,
                "low": 1024,
                "medium": 8192,
                "high": 16384,
                "max": 32000,  # Max allowed by OpenRouter
            }
            return {"reasoning": {"max_tokens": token_map.get(effort, 8192)}}

        elif model_family == "google":
            # Google/Gemini models - try unified reasoning
            effort_map = {
                "minimal": "low",
                "low": "low",
                "medium": "medium",
                "high": "high",
                "max": "high",
            }
            return {"reasoning": {"effort": effort_map.get(effort, "medium")}}

    return {}


def convert_verbosity(level: str, model_name: str = None) -> dict:
    """
    Convert verbosity level to API parameter.

    Args:
        level: Verbosity level (low, medium, high)
        model_name: Optional model name for model-specific handling

    Returns:
        Dict with verbosity parameter if valid
    """
    if level in ["low", "medium", "high"]:
        # GPT-5 and other models that support verbosity
        return {"verbosity": level}
    return {}


def get_model_family(model_name: str) -> str:
    """
    Identify the model family based on pattern matching.

    Args:
        model_name: The full model name (e.g., "openai/gpt-4", "anthropic/claude-3")

    Returns:
        The model family name (e.g., "openai_standard", "anthropic")
    """
    for family, pattern in MODEL_PATTERNS.items():
        if re.match(pattern, model_name):
            return family
    return "default"


def get_model_parameters(model_name: str, requested_params: dict) -> dict:
    """
    Dynamically filter parameters based on model patterns.

    Returns only the parameters that the model supports,
    with any necessary transformations applied.

    Args:
        model_name: The full model name
        requested_params: Dictionary of requested parameters

    Returns:
        Filtered dictionary containing only supported parameters
    """
    # Determine if routing through OpenRouter
    use_openrouter = "/" in model_name and not model_name.startswith("direct/")

    model_family = get_model_family(model_name)
    profile = PARAMETER_PROFILES.get(model_family, PARAMETER_PROFILES["default"])

    filtered = {}
    transforms = profile.get("transforms", {})
    allowed = profile.get("allowed", [])

    # Copy parameters to avoid modifying original
    params_to_process = requested_params.copy()

    # Handle thinking_effort conversion FIRST (highest priority)
    if (
        "thinking_effort" in params_to_process
        and params_to_process["thinking_effort"] is not None
    ):
        effort = params_to_process.pop("thinking_effort")
        reasoning_params = convert_thinking_effort(effort, model_name, use_openrouter)
        filtered.update(reasoning_params)

        # CRITICAL: Remove any conflicting parameters to prevent API errors
        # OpenRouter doesn't allow both 'reasoning' and 'reasoning_effort'
        params_to_process.pop("reasoning_effort", None)
        params_to_process.pop("reasoning", None)
        params_to_process.pop("thinking", None)
        params_to_process.pop("thinking_config", None)

    # Handle verbosity parameter
    if "verbosity" in params_to_process and params_to_process["verbosity"] is not None:
        verbosity = params_to_process.pop("verbosity")
        verbosity_params = convert_verbosity(verbosity, model_name)
        filtered.update(verbosity_params)

    # Process remaining parameters
    for param, value in params_to_process.items():
        # Skip None values
        if value is None:
            continue

        # Check if parameter needs transformation
        if param in transforms:
            new_param = transforms[param]
            filtered[new_param] = value
        elif param in allowed:
            filtered[param] = value
        # Silently drop unsupported parameters

    return filtered


def supports_system_messages(model_name: str) -> bool:
    """
    Check if a model supports system messages.

    Args:
        model_name: The full model name

    Returns:
        True if the model supports system messages, False otherwise
    """
    model_family = get_model_family(model_name)
    profile = PARAMETER_PROFILES.get(model_family, PARAMETER_PROFILES["default"])
    return profile.get("system_message_support", True)  # Default to True


class LLMClient(LLMVerificationMixin):
    """
    Core LLM client for chat completions across different providers.

    This class provides a unified interface for chat completions with automatic
    parameter filtering based on model capabilities. Verification functionality
    is provided by inheriting from LLMVerificationMixin.

    Attributes:
        model: The model identifier to use for completions
        default_params: Default parameters dictionary for completions
        command_context: Optional command context for logging
    """

    def __init__(self, model: str, **default_params):
        """
        Initialize an LLM client for chat completions.

        Args:
            model: The model name to use (e.g., 'openai/gpt-4o', 'anthropic/claude-sonnet-4')
            **default_params: Default decoding parameters (temperature, top_p, etc.)
        """
        self.model = model
        self.command_context = None  # Track which command is using this client

        # Set model-specific token limits if enabled in config and not explicitly specified
        if CONFIG.use_token_limits:
            # Determine if we need to transform max_tokens to another parameter
            test_params = {"max_tokens": 1}
            filtered = get_model_parameters(model, test_params)
            token_param = (
                "max_completion_tokens"
                if "max_completion_tokens" in filtered
                else "max_tokens"
            )

            if token_param not in default_params:
                # Set appropriate token limits based on model family
                if "google/gemini" in model.lower():
                    default_params[token_param] = 32768
                elif "anthropic/claude" in model.lower():
                    default_params[token_param] = 32768
                elif "openai/gpt-4" in model.lower():
                    default_params[token_param] = 32768
                elif get_model_family(model) == "openai_reasoning":
                    default_params[token_param] = 32768
                elif "grok" in model.lower():
                    default_params[token_param] = 32768
                else:
                    default_params[token_param] = 32768  # Default increased limit

        self.default_params = default_params
        self._client = None  # Will be created when needed

    @heartbeat(CONFIG.heartbeat_interval if CONFIG else 15)
    @timed
    def complete(
        self,
        messages: List[Dict[str, str]],
        skip_citation_verification: bool = False,
        **overrides,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Run a single chat completion with the configured model.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            skip_citation_verification: If True, bypass citation verification
            **overrides: Optional parameter overrides for this completion

        Returns:
            Tuple of (generated_text, usage_statistics)

        Raises:
            Exception: If the API call fails or returns an error
        """
        # Handle system message support for models that don't support them
        if not supports_system_messages(self.model):
            messages = self._merge_system_messages_for_unsupported_models(messages)
        else:
            messages = self._prepend_australian_law_to_system_messages(messages)

        # Merge default and override parameters
        params = {**self.default_params, **overrides}

        # Determine the correct model name for API call
        model_name = self._get_api_model_name()

        try:
            # Filter parameters based on model capabilities
            filtered_params = get_model_parameters(self.model, params)

            # Log the request and get correlation ID
            correlation_id = self._log_request(messages, filtered_params)

            # Execute API call with retry logic
            response = execute_api_call_with_retry(
                model_name, messages, filtered_params
            )

            # Validate and extract response content
            content, usage = self._extract_response_content(response)

            # Log the response separately
            self._log_response(correlation_id, content, usage)

            # Handle citation verification if not skipped
            if not skip_citation_verification:
                content = self._handle_citation_verification(
                    content, messages, model_name, params
                )

        except Exception:
            # Re-raise any exceptions after cleanup
            raise

        # Log the completion
        self._log_completion(
            messages, {**self.default_params, **overrides}, content, usage
        )

        return content, usage

    def _merge_system_messages_for_unsupported_models(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Merge system messages into first user message for models that don't support system messages."""
        modified_messages = []
        system_content = PROMPTS.get("base.australian_law")

        # Collect all system messages
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        non_system_messages = [msg for msg in messages if msg.get("role") != "system"]

        if system_messages:
            # Combine all system content
            system_content = "\n".join(
                [msg.get("content", "") for msg in system_messages]
            )
            if "Australian English" not in system_content:
                system_content += "\n" + PROMPTS.get("base.australian_law")

        # Find first user message and prepend system content
        for i, msg in enumerate(non_system_messages):
            if msg.get("role") == "user":
                enhanced_content = f"{system_content}\n\n{msg.get('content', '')}"
                modified_messages.append({"role": "user", "content": enhanced_content})
                modified_messages.extend(non_system_messages[i + 1 :])
                break
        else:
            # No user message found, just use non-system messages
            modified_messages = non_system_messages

        return modified_messages

    def _prepend_australian_law_to_system_messages(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Prepend Australian law prompt to all system messages."""
        australian_law_prompt = PROMPTS.get("base.australian_law")
        if not australian_law_prompt:
            return messages

        modified_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                # Only prepend if not already present
                if australian_law_prompt not in content:
                    content = f"{australian_law_prompt}\n\n{content}"
                modified_messages.append({"role": "system", "content": content})
            else:
                modified_messages.append(msg)

        return modified_messages

    def _get_api_model_name(self) -> str:
        """Get the correct model name for API calls."""
        model_name = self.model

        # Extract just the model name for direct OpenAI models
        if (
            self.model.startswith("openai/")
            and "/" in self.model
            and not get_model_family(self.model) == "openai_reasoning"
        ):
            model_name = self.model.replace("openai/", "")

        return model_name

    def _log_request(
        self, messages: List[Dict[str, str]], filtered_params: dict
    ) -> str:
        """Log the API request details and return correlation ID."""
        # Generate unique correlation ID
        correlation_id = (
            f"{time.strftime('%Y%m%d_%H%M%S')}_{os.getpid()}_{id(self) % 1000000}"
        )

        save_log(
            f"llm_request_{self.model.replace('/', '_')}",
            {
                "correlation_id": correlation_id,
                "model": self.model,
                "messages": messages,
                "params": filtered_params,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        return correlation_id

    def _log_response(
        self, correlation_id: str, content: str, usage: Dict[str, Any]
    ) -> None:
        """Log the API response details separately."""
        save_log(
            f"llm_response_{self.model.replace('/', '_')}",
            {
                "correlation_id": correlation_id,
                "model": self.model,
                "response": content,
                "usage": usage,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

    def _extract_response_content(self, response) -> Tuple[str, Dict[str, Any]]:
        """Extract content and usage from API response."""
        # Validate response structure
        self._validate_response_structure(response)

        # Extract content
        content = response.choices[0].message.content or ""

        # Extract usage statistics
        usage = getattr(response, "usage", {})
        if hasattr(usage, "model_dump"):
            usage = usage.model_dump()
        elif hasattr(usage, "dict"):
            usage = usage.dict()
        elif not isinstance(usage, dict):
            usage = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }

        return content, usage

    def _validate_response_structure(self, response) -> None:
        """Validate API response structure and check for errors."""
        if not response:
            raise Exception("Empty response from API")

        # Check for choice-level errors
        if (
            hasattr(response, "choices")
            and response.choices
            and hasattr(response.choices[0], "error")
            and response.choices[0].error
        ):
            error_info = response.choices[0].error
            error_msg = error_info.get("message", "Unknown API error")
            raise Exception(f"API Error: {error_msg}")

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
                raise Exception(f"API request failed: {error_msg}")
            else:
                raise Exception(
                    "API request failed with error finish_reason but no error details"
                )

        # Check for missing choices
        if not hasattr(response, "choices") or not response.choices:
            logging.error(f"Invalid API response structure: {response}")
            error_msg = "API response missing 'choices' field"
            if hasattr(response, "error") and response.error:
                if hasattr(response.error, "get"):
                    error_msg = (
                        f"API error: {response.error.get('message', 'Unknown error')}"
                    )
                else:
                    error_msg = f"API error: {response.error}"
            raise Exception(error_msg)

        # Check for missing message
        if not hasattr(response.choices[0], "message"):
            raise Exception(f"Invalid choice structure: {response.choices[0]}")

    def _handle_citation_verification(
        self,
        content: str,
        messages: List[Dict[str, str]],
        model_name: str,
        params: dict,
    ) -> str:
        """Handle citation verification and potential retry."""
        from litassist.citation_verify import CitationVerificationError

        # Determine verification mode based on force_verify setting
        strict_mode = getattr(self, "_force_verify", True)

        try:
            verified_content, verification_issues = self.validate_and_verify_citations(
                content, strict_mode=strict_mode
            )

            if verification_issues:
                # Log warnings but proceed
                warning_msg = warning_message(
                    f"Citation verification: {verification_issues[0]}"
                )
                print(warning_msg)
                content = verified_content

        except CitationVerificationError as e:
            # Handle citation verification failure with retry
            content = self._retry_with_enhanced_citations(
                e, messages, model_name, params
            )

        return content

    def _retry_with_enhanced_citations(
        self,
        error: Exception,
        messages: List[Dict[str, str]],
        model_name: str,
        params: dict,
    ) -> str:
        """Retry completion with enhanced citation instructions after verification failure."""
        from litassist.citation_verify import CitationVerificationError

        print(error_message(str(error)))
        print(info_message("Retrying with enhanced citation instructions..."))

        # Enhance messages with citation instructions
        enhanced_messages = self._enhance_messages_with_citation_instructions(
            messages.copy()
        )

        # Get retry client and execute
        from .api_handlers import get_openai_client

        retry_client = get_openai_client(model_name)

        try:
            # Execute retry with filtered parameters
            retry_filtered_params = get_model_parameters(self.model, params)
            retry_response = retry_client.chat.completions.create(
                model=model_name,
                messages=enhanced_messages,
                **retry_filtered_params,
            )

            # Validate retry response
            self._validate_response_structure(retry_response)
            retry_content = retry_response.choices[0].message.content or ""

            # Verify the retry
            verified_retry_content, retry_issues = self.validate_and_verify_citations(
                retry_content, strict_mode=True
            )

            # Success - use retry result
            if retry_issues:
                print(success_message(f"Retry successful: {retry_issues[0]}"))
            else:
                print(success_message("Retry successful: All citations verified"))

            return verified_retry_content

        except CitationVerificationError as retry_error:
            # Both attempts failed - critical error
            print(error_message(f"Retry also failed: {str(retry_error)}"))
            raise CitationVerificationError(
                "CRITICAL: Multiple attempts to generate content with verified citations failed. "
                "The AI model is consistently generating unverifiable legal citations. "
                "Manual intervention required."
            )

    def _enhance_messages_with_citation_instructions(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Add citation instructions to messages."""
        citation_instructions = PROMPTS.get("verification.citation_retry_instructions")

        if self.model == "openai/o3-pro":
            # For o3 models, append to user content
            if messages and messages[-1].get("role") == "user":
                messages[-1]["content"] += f"\n\n{citation_instructions}"
        else:
            # For regular models with system messages
            if messages and messages[-1].get("role") == "user":
                messages[-1]["content"] += f"\n\n{citation_instructions}"

        return messages

    def _log_completion(
        self,
        messages: List[Dict[str, str]],
        params: dict,
        content: str,
        usage: Dict[str, Any],
    ) -> None:
        """Log the completion details."""
        # Normalize usage data for serialization
        if hasattr(usage, "_asdict"):
            usage = usage._asdict()
        elif hasattr(usage, "to_dict"):
            usage = usage.to_dict()
        elif not isinstance(usage, dict):
            usage = {"raw": str(usage)}

        # Combined logging removed - now using separate request/response logging
        # The request was logged in _log_request() and response in _log_response()
        # Each with their own files and linked by correlation_id
