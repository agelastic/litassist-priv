"""
LLM Client for LitAssist.

This module provides a unified interface for chat completions across different LLM providers,
handling parameter management and response processing.
"""

import openai
import re
import os
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
import time
from litassist.citation_verify import (
    verify_all_citations,
    remove_citation_from_text,
    CitationVerificationError,
)

import tenacity
import logging
import requests


# --- Add missing custom exception classes for retry logic ---
class RetryableAPIError(Exception):
    """Custom exception for retryable API errors."""

    pass


class StreamingAPIError(Exception):
    """Custom exception for streaming-related API errors."""

    pass


class NonRetryableAPIError(Exception):
    """Errors that should not be retried (413, 400 with specific messages)."""

    pass


try:
    import aiohttp
except ImportError:
    aiohttp = None

logger = logging.getLogger(__name__)


# Model family patterns for dynamic parameter handling
MODEL_PATTERNS = {
    "openai_reasoning": r"openai/o\d+",  # Matches o1, o3, o1-pro, o3-pro, etc.
    "anthropic": r"anthropic/claude",
    "google": r"google/(gemini|palm|bard)",
    "openai_standard": r"openai/(gpt|chatgpt)",
    "xai": r"x-ai/grok",
    "meta": r"meta/(llama|codellama)",
    "mistral": r"mistral/",
    "cohere": r"cohere/",
}

# Parameter profiles by model family
PARAMETER_PROFILES = {
    "openai_reasoning": {
        "allowed": ["max_completion_tokens", "reasoning_effort"],
        "transforms": {"max_tokens": "max_completion_tokens"},
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
        ],
    },
    "google": {
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "candidate_count",
            "max_output_tokens",
            "top_k",
            "safety_settings",
            "stop_sequences",
        ],
        "transforms": {"max_tokens": "max_output_tokens"},
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
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "frequency_penalty",
            "presence_penalty",
            "stream",
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
    "default": {
        "allowed": ["temperature", "top_p", "max_tokens", "stop"],  # Safe defaults
    },
}


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
    model_family = get_model_family(model_name)
    profile = PARAMETER_PROFILES.get(model_family, PARAMETER_PROFILES["default"])

    filtered = {}
    transforms = profile.get("transforms", {})
    allowed = profile.get("allowed", [])

    for param, value in requested_params.items():
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


class LLMClientFactory:
    """
    Factory class for creating LLMClient instances with command-specific configurations.

    This centralizes all model and parameter configurations for each command,
    eliminating duplication and providing a single source of truth.
    """

    # Command configurations registry
    COMMAND_CONFIGS = {
        # Extract facts - deterministic, focused on accuracy
        "extractfacts": {
            "model": "anthropic/claude-sonnet-4",
            "temperature": 0,
            "top_p": 0.15,
            "force_verify": True,  # Always verify for foundational docs
        },
        # Strategy - enhanced multi-step legal reasoning (o3-pro has limited parameters)
        "strategy": {
            "model": "openai/o3-pro",
            # o3-pro has fixed parameters: temperature=1, top_p=1, presence_penalty=0, frequency_penalty=0
            # Only max_completion_tokens and reasoning_effort can be controlled
            "reasoning_effort": "high",
            "force_verify": True,  # Always verify for strategic guidance
        },
        # Strategy sub-type for analysis
        "strategy-analysis": {
            "model": "anthropic/claude-opus-4",
            "temperature": 0.2,
            "top_p": 0.8,
        },
        # Brainstorm - varied temperatures for different approaches
        "brainstorm-orthodox": {
            "model": "anthropic/claude-opus-4",
            "temperature": 0.3,
            "top_p": 0.7,
            "force_verify": True,  # Conservative analysis requires verification
        },
        "brainstorm-unorthodox": {
            "model": "x-ai/grok-3",
            "temperature": 0.9,
            "top_p": 0.95,
            "force_verify": True,  # Auto-verify Grok
        },
        "brainstorm-analysis": {
            "model": "openai/o3-pro",
            "temperature": 0.2,
            "top_p": 0.8,
            "reasoning_effort": "high",
        },
        # Draft - superior technical writing (o3 model with very limited parameter support)
        "draft": {"model": "openai/o3-pro", "reasoning_effort": "high"},
        # Digest - mode-dependent settings
        "digest-summary": {
            "model": "anthropic/claude-sonnet-4",
            "temperature": 0.1,
            "top_p": 0,
        },
        "digest-issues": {
            "model": "anthropic/claude-opus-4",
            "temperature": 0.2,
            "top_p": 0.5,
        },
        # Lookup - uses Gemini for rapid processing with verification
        "lookup": {
            "model": "google/gemini-2.5-pro-preview",
            "temperature": 0.1,
            "top_p": 0.2,
            "force_verify": False,  # Don't force strict verification
        },
        # Verify - post-hoc verification command
        "verify": {
            "model": "anthropic/claude-opus-4",
            "temperature": 0,
            "top_p": 0.2,
            "force_verify": False,  # Don't double-verify since this IS verification
        },
        # Counsel's Notes - strategic analysis from advocate's perspective
        "counselnotes": {
            "model": "anthropic/claude-opus-4",
            "temperature": 0.3,
            "top_p": 0.7,
            "force_verify": True,  # Strategic counsel's notes require verification
        },
        # Barrister's brief - comprehensive document generation
        "barbrief": {
            "model": "openai/o3-pro",
            # o3-pro for comprehensive analysis and superior drafting
            # Extended token limit for detailed briefs
            "reasoning_effort": "high",
            "max_completion_tokens": 32768,  # 32K tokens for comprehensive output
        },
        # Caseplan - LLM-driven workflow planning
        "caseplan": {
            "model": "anthropic/claude-opus-4",
            "temperature": 0.3,
            "top_p": 0.7,
            "force_verify": False,
        },
        # Caseplan assessment - budget recommendation (Sonnet)
        "caseplan-assessment": {
            "model": "anthropic/claude-sonnet-4",
            "temperature": 0.2,
            "top_p": 0.7,
            "force_verify": False,
        },
    }

    @classmethod
    def for_command(
        cls, command_name: str, sub_type: str = None, **overrides
    ) -> "LLMClient":
        """
        Create an LLMClient configured for a specific command.

        Args:
            command_name: The command name (e.g., 'extractfacts', 'strategy')
            sub_type: Optional sub-type for commands with multiple clients
                     (e.g., 'orthodox', 'unorthodox', 'analysis' for brainstorm,
                      'summary', 'issues' for digest)
            **overrides: Any parameter overrides to apply to the default configuration

        Returns:
            Configured LLMClient instance with command context set

        Examples:
            # Simple command
            client = LLMClientFactory.for_command('extractfacts')

            # Command with sub-type
            client = LLMClientFactory.for_command('brainstorm', 'orthodox')

            # With overrides
            client = LLMClientFactory.for_command('draft', temperature=0.7)
        """
        # Build the configuration key
        if sub_type:
            config_key = f"{command_name}-{sub_type}"
        else:
            config_key = command_name

        # Get the configuration or fall back to a default
        if config_key not in cls.COMMAND_CONFIGS:
            # Default configuration for unknown commands
            config = {
                "model": "anthropic/claude-sonnet-4",
                "temperature": 0.3,
                "top_p": 0.7,
            }
            # Use default configuration for commands without specific config
            # This is expected behavior for many commands
        else:
            config = cls.COMMAND_CONFIGS[config_key].copy()

        # Extract special flags
        force_verify = config.pop("force_verify", False)

        # Remove premium_model key if present (no longer needed)
        config.pop("premium_model", None)

        # Allow environment variable overrides for model selection
        env_model_key = f"LITASSIST_{command_name.upper()}_MODEL"
        if sub_type:
            env_model_key = f"LITASSIST_{command_name.upper()}_{sub_type.upper()}_MODEL"

        env_model = os.environ.get(env_model_key)
        if env_model:
            config["model"] = env_model
            # Suppress informational message during pytest runs
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                logger.info(info_message(f"Using model from environment: {env_model}"))

        # Apply any provided overrides
        config.update(overrides)

        # Extract model from config
        model = config.pop("model")

        # Create the LLM client with remaining config as parameters
        client = LLMClient(model, **config)

        # Set the command context
        client.command_context = config_key

        # Set force verification flag - explicitly set both True and False
        client._force_verify = force_verify

        return client

    @classmethod
    def get_model_for_command(cls, command_name: str, sub_type: str = None) -> str:
        """
        Get the model name configured for a specific command.

        Useful for logging or debugging purposes.

        Args:
            command_name: The command name
            sub_type: Optional sub-type

        Returns:
            Model name string
        """
        config_key = f"{command_name}-{sub_type}" if sub_type else command_name
        config = cls.COMMAND_CONFIGS.get(
            config_key, {"model": "anthropic/claude-sonnet-4"}
        )
        return config["model"]

    @classmethod
    def list_configurations(cls) -> Dict[str, Dict[str, Any]]:
        """
        List all available command configurations.

        Returns:
            Dictionary of all command configurations
        """
        return cls.COMMAND_CONFIGS.copy()


class LLMClient:
    """
    Wrapper for LLM API calls with support for completions and self-verification.

    This class provides a unified interface for chat completions across different LLM
    providers, handling parameter management and response processing. It supports both
    creative (high temperature) and deterministic (low temperature) generation, as well
    as legal self-critique verification.

    Attributes:
        model: The model identifier to use for completions (e.g., 'openai/gpt-4o').
        default_params: Default parameters dictionary for completions.

    Example:
        ```python
        # Initialize client with default parameters
        client = LLMClient("anthropic/claude-sonnet-4", temperature=0.2, top_p=0.8)

        # Run a completion
        content, usage = client.complete([
            {"role": "system", "content": "Australian law only."},
            {"role": "user", "content": "Explain adverse possession."}
        ])

        # Optional verification
        if needs_verification:
            corrections = client.verify(content)
        ```
    """

    def __init__(self, model: str, **default_params):
        """
        Initialize an LLM client for chat completions.

        Args:
            model: The model name to use (e.g., 'openai/gpt-4o', 'anthropic/claude-sonnet-4').
            **default_params: Default decoding parameters (temperature, top_p, etc.) to use
                             for all completions unless overridden.
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
                # These limits are carefully chosen to balance comprehensive responses with quality
                if "google/gemini" in model.lower():
                    default_params[token_param] = (
                        32768  # Gemini - increased for comprehensive outputs
                    )
                elif "anthropic/claude" in model.lower():
                    default_params[token_param] = (
                        32768  # Claude - increased for comprehensive outputs
                    )
                elif "openai/gpt-4" in model.lower():
                    default_params[token_param] = (
                        32768  # GPT-4 - increased for comprehensive outputs
                    )
                elif get_model_family(model) == "openai_reasoning":
                    default_params[token_param] = (
                        32768  # o1-pro/o3-pro - increased for comprehensive outputs
                    )
                elif "grok" in model.lower():
                    default_params[token_param] = (
                        32768  # Grok - increased for comprehensive outputs
                    )
                else:
                    default_params[token_param] = 32768  # Default increased limit

        self.default_params = default_params

    def _execute_api_call_with_retry(self, model_name, messages, filtered_params):
        # --- Begin: Add custom retryable API error for overloaded/rate limit ---
        retry_errors = (
            openai.error.APIConnectionError,
            openai.error.RateLimitError,
            openai.error.APIError,
            requests.exceptions.ConnectionError,
            RetryableAPIError,
        )
        if aiohttp:
            retry_errors = retry_errors + (
                aiohttp.ClientConnectionError,
                aiohttp.ClientPayloadError,
            )

        # Use no wait time during tests to speed up retry tests
        wait_config = (
            tenacity.wait_none()  # No wait in tests
            if os.environ.get("PYTEST_CURRENT_TEST")
            else tenacity.wait_exponential(multiplier=0.5, max=10)
        )

        def _call_with_streaming_wrap():
            try:
                resp = openai.ChatCompletion.create(
                    model=model_name, messages=messages, **filtered_params
                )
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

        @tenacity.retry(
            stop=tenacity.stop_after_attempt(5),
            wait=wait_config,
            retry=(
                tenacity.retry_if_exception_type(retry_errors)
                | tenacity.retry_if_exception_type(StreamingAPIError)
            ),
            before_sleep=tenacity.before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        def _call():
            return _call_with_streaming_wrap()

        return _call()

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
            messages: List of message dictionaries, each containing 'role' (system/user/assistant)
                     and 'content' (the message text).
            skip_citation_verification: If True, bypass the citation verification step.
            **overrides: Optional parameter overrides for this specific completion that will
                        take precedence over the default parameters.

        Returns:
            A tuple containing:
                - The generated text content (str)
                - The usage statistics dictionary (with prompt_tokens, completion_tokens, etc.)

        Raises:
            Exception: If the API call fails or returns an error.
        """
        # Check if this model supports system messages
        if not supports_system_messages(self.model):
            # This model doesn't support system messages - merge into first user message
            modified_messages = []
            system_content = PROMPTS.get("base.australian_law")

            # Collect all system messages
            system_messages = [msg for msg in messages if msg.get("role") == "system"]
            non_system_messages = [
                msg for msg in messages if msg.get("role") != "system"
            ]

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
                    modified_messages.append(
                        {"role": "user", "content": enhanced_content}
                    )
                    # Add remaining messages as-is
                    modified_messages.extend(non_system_messages[i + 1 :])
                    break
            else:
                # No user message found, just use non-system messages
                modified_messages = non_system_messages

            messages = modified_messages
        else:
            # Regular models - handle system messages normally
            # Note: Commands already include base.australian_law in their system prompts,
            # so we don't need to append it here. This prevents prompt corruption.
            pass

        # Merge default and override parameters
        params = {**self.default_params, **overrides}

        # Set API base based on model type
        original_api_base = openai.api_base
        original_api_key = openai.api_key

        # Determine the correct model name
        model_name = self.model

        # Use OpenRouter for non-OpenAI models AND for reasoning models (only available via OpenRouter)
        model_family = get_model_family(self.model)
        if (
            "/" in self.model and not self.model.startswith("openai/")
        ) or model_family == "openai_reasoning":
            openai.api_base = CONFIG.or_base
            openai.api_key = CONFIG.or_key
            # Keep full model name for OpenRouter
            model_name = self.model
        else:
            # Extract just the model name for direct OpenAI models
            if self.model.startswith("openai/"):
                model_name = self.model.replace("openai/", "")

        try:
            # Filter parameters based on model capabilities
            filtered_params = get_model_parameters(self.model, params)

            # Log the final messages being sent to the API
            save_log(
                f"llm_{self.model.replace('/', '_')}_messages",
                {
                    "model": self.model,
                    "messages_sent": messages,
                    "params": filtered_params,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                },
            )

            # Use ChatCompletion API with retry logic
            response = self._execute_api_call_with_retry(
                model_name, messages, filtered_params
            )

            # Check for errors in the response
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
                # Try to get error details
                if hasattr(response.choices[0], "error"):
                    error_info = response.choices[0].error
                    error_msg = error_info.get("message", "Unknown API error")
                    raise Exception(f"API request failed: {error_msg}")
                else:
                    raise Exception(
                        "API request failed with error finish_reason but no error details"
                    )

            # Extract content and usage from chat response
            content = response.choices[0].message.content or ""
            usage = getattr(response, "usage", {})
        finally:
            # Restore original settings
            openai.api_base = original_api_base
            openai.api_key = original_api_key

        if not skip_citation_verification:
            # Citation verification - respect force_verify setting
            # For commands like lookup that have force_verify=False, use lenient mode
            strict_mode = getattr(
                self, "_force_verify", True
            )  # Default to strict unless explicitly disabled

            try:
                verified_content, verification_issues = (
                    self.validate_and_verify_citations(content, strict_mode=strict_mode)
                )

                # If we got here, all citations are verified or were safely removed
                if verification_issues:
                    # Log what was cleaned but still proceed
                    try:
                        warning_msg = PROMPTS.get(
                            "warnings.citation_verification_warning",
                            issue=verification_issues[0],
                        )
                    except (KeyError, ValueError):
                        warning_msg = warning_message(
                            f"Citation verification: {verification_issues[0]}"
                        )

                    print(warning_msg)
                    content = verified_content

            except CitationVerificationError as e:
                # Strict mode failed - attempt retry with enhanced prompt
                try:
                    strict_failed_msg = PROMPTS.get(
                        "warnings.strict_mode_failed", error=str(e)
                    )
                    retrying_msg = PROMPTS.get("warnings.retrying_with_instructions")
                except (KeyError, ValueError):
                    strict_failed_msg = error_message(str(e))
                    retrying_msg = info_message(
                        "Retrying with enhanced citation instructions..."
                    )

                print(strict_failed_msg)
                print(retrying_msg)

                # Enhance the last user message with strict citation instructions
                enhanced_messages = messages.copy()
                citation_instructions = PROMPTS.get(
                    "verification.citation_retry_instructions"
                )

                if self.model == "openai/o3-pro":
                    # For o3 models, append to the enhanced user content from earlier processing
                    if (
                        enhanced_messages
                        and enhanced_messages[-1].get("role") == "user"
                    ):
                        enhanced_messages[-1][
                            "content"
                        ] += f"\n\n{citation_instructions}"
                else:
                    # For regular models with system messages
                    if (
                        enhanced_messages
                        and enhanced_messages[-1].get("role") == "user"
                    ):
                        enhanced_messages[-1][
                            "content"
                        ] += f"\n\n{citation_instructions}"

                # Retry with enhanced prompt - need to set API base again
                original_api_base_retry = openai.api_base
                original_api_key_retry = openai.api_key

                # Use OpenRouter for non-OpenAI models AND for o1-pro/o3-pro models (only available via OpenRouter)
                if (
                    "/" in self.model and not self.model.startswith("openai/")
                ) or self.model in ["openai/o1-pro", "openai/o3-pro"]:
                    openai.api_base = CONFIG.or_base
                    openai.api_key = CONFIG.or_key

                try:
                    if self.model in ["openai/o1-pro", "openai/o3-pro"]:
                        # o1-pro and o3-pro use special handling via OpenRouter
                        # Filter parameters - these models only support max_completion_tokens and reasoning_effort
                        retry_filtered_params = {}
                        if "max_completion_tokens" in params:
                            retry_filtered_params["max_completion_tokens"] = params[
                                "max_completion_tokens"
                            ]
                        if (
                            "reasoning_effort" in params
                            and self.model == "openai/o3-pro"
                        ):
                            retry_filtered_params["reasoning_effort"] = params[
                                "reasoning_effort"
                            ]

                        # Use ChatCompletion API through OpenRouter
                        retry_response = openai.ChatCompletion.create(
                            model=model_name,
                            messages=enhanced_messages,
                            **retry_filtered_params,
                        )

                        # Check for errors in the retry response
                        if (
                            hasattr(retry_response, "choices")
                            and retry_response.choices
                            and hasattr(retry_response.choices[0], "error")
                            and retry_response.choices[0].error
                        ):
                            error_info = retry_response.choices[0].error
                            error_msg = error_info.get("message", "Unknown API error")
                            raise Exception(f"API Error on retry: {error_msg}")

                        if (
                            hasattr(retry_response, "choices")
                            and retry_response.choices
                            and hasattr(retry_response.choices[0], "finish_reason")
                            and retry_response.choices[0].finish_reason == "error"
                        ):
                            if hasattr(retry_response.choices[0], "error"):
                                error_info = retry_response.choices[0].error
                                error_msg = error_info.get(
                                    "message", "Unknown API error"
                                )
                                raise Exception(
                                    f"API retry request failed: {error_msg}"
                                )
                            else:
                                raise Exception(
                                    "API retry request failed with error finish_reason"
                                )

                        retry_content = retry_response.choices[0].message.content or ""
                        retry_usage = getattr(retry_response, "usage", {})
                    else:
                        retry_response = openai.ChatCompletion.create(
                            model=model_name, messages=enhanced_messages, **params
                        )
                        retry_content = retry_response.choices[0].message.content
                        retry_usage = getattr(retry_response, "usage", {})

                    # Verify the retry
                    (
                        verified_retry_content,
                        retry_issues,
                    ) = self.validate_and_verify_citations(
                        retry_content, strict_mode=True
                    )

                    # If retry succeeded, use it
                    content = verified_retry_content
                    usage = retry_usage
                    if retry_issues:
                        try:
                            success_msg = PROMPTS.get(
                                "warnings.retry_successful", issue=retry_issues[0]
                            )
                        except (KeyError, ValueError):
                            success_msg = success_message(
                                f"Retry successful: {retry_issues[0]}"
                            )
                        print(success_msg)
                    else:
                        try:
                            all_verified_msg = PROMPTS.get(
                                "warnings.all_citations_verified"
                            )
                        except (KeyError, ValueError):
                            all_verified_msg = success_message(
                                "Retry successful: All citations verified"
                            )
                        print(all_verified_msg)

                except CitationVerificationError as retry_error:
                    # Both attempts failed - this is a critical error
                    try:
                        retry_failed_msg = PROMPTS.get(
                            "warnings.retry_also_failed", error=str(retry_error)
                        )
                        multiple_attempts_msg = PROMPTS.get(
                            "warnings.multiple_attempts_failed"
                        )
                    except (KeyError, ValueError):
                        retry_failed_msg = error_message(
                            f"Retry also failed: {str(retry_error)}"
                        )
                        multiple_attempts_msg = (
                            "CRITICAL: Multiple attempts to generate content with verified citations failed. "
                            "The AI model is consistently generating unverifiable legal citations. "
                            "Manual intervention required."
                        )

                    print(retry_failed_msg)
                    raise CitationVerificationError(multiple_attempts_msg)
                finally:
                    # Restore original settings after retry
                    openai.api_base = original_api_base_retry
                    openai.api_key = original_api_key_retry

        # Normalize usage data so it can be safely serialized
        if hasattr(usage, "_asdict"):
            usage = usage._asdict()
        elif hasattr(usage, "to_dict"):
            usage = usage.to_dict()
        elif not isinstance(usage, dict):
            usage = {"raw": str(usage)}

        # Log the LLM call
        save_log(
            f"llm_{self.model.replace('/', '_')}",
            {
                "method": "complete",
                "model": self.model,
                "messages": messages,
                "params": {**self.default_params, **overrides},
                "response": content,
                "usage": usage,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

        return content, usage

    @heartbeat()
    @timed
    def verify(self, primary_text: str) -> str:
        """
        Run a self-critique pass to identify and correct legal inaccuracies in text.

        Uses the same model as the client instance but with deterministic settings
        (temperature=0, top_p=0.2) to minimize variability in verification.

        Args:
            primary_text: The text content to verify for legal accuracy.

        Returns:
            A string containing corrections to any legal inaccuracies found.

        Raises:
            Exception: If the verification API call fails.
        """
        try:
            base_prompt = PROMPTS.get("base.australian_law")
            self_critique = PROMPTS.get("verification.self_critique")
        except KeyError:
            # Fallback to hardcoded if prompts not available
            base_prompt = "Australian law only. Use Australian English spellings and terminology (e.g., 'judgement' not 'judgment', 'defence' not 'defense')."
            self_critique = "Identify and correct any legal inaccuracies above, and provide the corrected text only. Ensure all spellings follow Australian English conventions."

        critique_prompt = [
            {
                "role": "system",
                "content": base_prompt,
            },
            {
                "role": "user",
                "content": primary_text + "\n\n" + self_critique,
            },
        ]
        # Use Claude 4 Opus for all verification, regardless of generation model
        verification_client = LLMClient(
            "anthropic/claude-opus-4", **self.default_params
        )
        params = {"temperature": 0, "top_p": 0.2}
        if CONFIG.use_token_limits:
            params["max_tokens"] = 65536  # Large limit for full document verification
        verification_result, usage = verification_client.complete(
            critique_prompt, skip_citation_verification=True, **params
        )
        return verification_result

    def validate_and_verify_citations(
        self, content: str, strict_mode: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Validate and verify citations with strict real-time checking.

        Args:
            content: Text content to validate and verify
            strict_mode: If True, raise CitationVerificationError on unverified citations

        Returns:
            Tuple of (cleaned_content, issues_list)

        Raises:
            CitationVerificationError: If strict_mode=True and unverified citations found
        """
        issues = []

        # Optionally perform offline pattern validation if enabled in config
        if CONFIG.offline_validation:
            pattern_issues = self.validate_citations(content, enable_online=False)
            if pattern_issues:
                issues.extend(pattern_issues)
                print(
                    warning_message(
                        f"Offline validation found {len(pattern_issues)} potential issues"
                    )
                )

        # Always do real-time online database verification
        verified_citations, unverified_citations = verify_all_citations(content)

        if unverified_citations and strict_mode:
            # Categorize issues for better error messages
            format_errors = []
            existence_errors = []
            verification_errors = []

            for citation, reason in unverified_citations:
                # Don't block for offline validation warnings - treat as warnings only
                if "OFFLINE VALIDATION ONLY" in reason:
                    continue  # Skip - these are warnings, not errors
                elif "format" in reason.lower() and "not found" not in reason.lower():
                    format_errors.append((citation, reason))
                elif (
                    "not found" in reason.lower() or "case not found" in reason.lower()
                ):
                    existence_errors.append((citation, reason))
                else:
                    verification_errors.append((citation, reason))

            # Only raise error if there are actual blocking issues
            blocking_errors = format_errors + existence_errors + verification_errors

            if blocking_errors:
                # Build categorized error message using templates
                categorized_issues = ""

                try:
                    if existence_errors:
                        categorized_issues += (
                            PROMPTS.get("warnings.citation_not_found_header") + "\n"
                        )
                        for citation, reason in existence_errors:
                            categorized_issues += (
                                PROMPTS.get(
                                    "warnings.citation_error_item",
                                    citation=citation,
                                    reason=reason,
                                )
                                + "\n"
                            )
                        categorized_issues += "\n"

                    if format_errors:
                        categorized_issues += (
                            PROMPTS.get("warnings.citation_format_issues_header") + "\n"
                        )
                        for citation, reason in format_errors:
                            categorized_issues += (
                                PROMPTS.get(
                                    "warnings.citation_error_item",
                                    citation=citation,
                                    reason=reason,
                                )
                                + "\n"
                            )
                        categorized_issues += "\n"

                    if verification_errors:
                        categorized_issues += (
                            PROMPTS.get(
                                "warnings.citation_verification_problems_header"
                            )
                            + "\n"
                        )
                        for citation, reason in verification_errors:
                            categorized_issues += (
                                PROMPTS.get(
                                    "warnings.citation_error_item",
                                    citation=citation,
                                    reason=reason,
                                )
                                + "\n"
                            )
                        categorized_issues += "\n"

                    error_msg = PROMPTS.get(
                        "warnings.citation_verification_failed",
                        categorized_issues=categorized_issues.rstrip(),
                    )

                except (KeyError, ValueError):
                    # Fallback to hardcoded if templates not available
                    error_msg = "[CRITICAL] Citation verification failed:\n\n"

                    if existence_errors:
                        error_msg += "[NOT FOUND] CASES NOT FOUND IN DATABASE:\n"
                        for citation, reason in existence_errors:
                            error_msg += f"   • {citation}\n     -> {reason}\n"
                        error_msg += "\n"

                    if format_errors:
                        error_msg += "[WARNING] CITATION FORMAT ISSUES:\n"
                        for citation, reason in format_errors:
                            error_msg += f"   • {citation}\n     -> {reason}\n"
                        error_msg += "\n"

                    if verification_errors:
                        error_msg += "[VERIFICATION] VERIFICATION PROBLEMS:\n"
                        for citation, reason in verification_errors:
                            error_msg += f"   • {citation}\n     -> {reason}\n"
                        error_msg += "\n"

                    error_msg += "[ACTION REQUIRED] These citations appear to be AI hallucinations.\n"
                    error_msg += "   Remove these citations and regenerate, or verify them independently."

                raise CitationVerificationError(error_msg)

        # If not strict mode or no unverified citations, clean up the content
        cleaned_content = content

        for citation, reason in unverified_citations:
            # Add to issues list
            issues.append(f"UNVERIFIED: {citation} - {reason}")

            # Remove the citation from content
            cleaned_content = remove_citation_from_text(cleaned_content, citation)

        if unverified_citations:
            issues.insert(
                0,
                f"CITATION VERIFICATION WARNING: {len(unverified_citations)} citations removed as unverified",
            )

        return cleaned_content, issues

    def should_auto_verify(self, content: str, command: str = None) -> bool:
        """
        Determine if content should be automatically verified based on risk factors.

        Args:
            content: The generated content to analyze
            command: The command that generated this content (optional)

        Returns:
            True if auto-verification should be triggered
        """
        # Check if factory has set force verification
        if hasattr(self, "_force_verify") and self._force_verify:
            return True

        # Always verify critical foundation commands
        if command in ["extractfacts", "strategy"]:
            return True

        # Auto-verify Grok outputs (prone to hallucination)
        if "grok" in self.model.lower():
            return True

        # Auto-verify when output contains high-risk content
        risk_patterns = [
            r"\[\d{4}\]\s+\w+\s+\d+",  # Case citations
            r"\d+%",  # Percentage claims
            r'"must"|"cannot"|"will"',  # Strong legal conclusions
            r"section\s+\d+",  # Statutory references
            r"rule\s+\d+",  # Court rules
            r"paragraph\s+\d+",  # Paragraph references
        ]

        for pattern in risk_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        return False

    def validate_citations(self, content: str, enable_online: bool = True) -> List[str]:
        """
        Validate citations using pattern-based checking.

        Delegates to citation_patterns module for the actual validation logic.

        Args:
            content: Text content to validate
            enable_online: Whether to perform online database verification after offline checks

        Returns:
            List of potential citation issues found
        """
        from litassist.citation_patterns import validate_citation_patterns

        return validate_citation_patterns(content, enable_online)

    @heartbeat()
    def verify_with_level(self, primary_text: str, level: str = "medium") -> str:
        """
        Run verification with different depth levels.

        Args:
            primary_text: Text to verify
            level: Verification depth - "light" (spelling only) or "heavy" (comprehensive)
                  Any other value defaults to standard verification

        Returns:
            Verification feedback
        """
        if level == "light":
            # Just check Australian English compliance
            try:
                light_verification = PROMPTS.get("verification.light_verification")
            except KeyError:
                light_verification = "Check only for Australian English spelling and terminology compliance.\n\nCorrect any non-Australian English spellings or terminology."

            critique_prompt = [
                {
                    "role": "system",
                    "content": light_verification.split("\n\n")[0],
                },
                {
                    "role": "user",
                    "content": primary_text
                    + "\n\n"
                    + light_verification.split("\n\n")[-1],
                },
            ]
        elif level == "heavy":
            # Full legal accuracy and citation check
            try:
                system_prompt = PROMPTS.get("verification.system_prompt")
                heavy_verification = PROMPTS.get("verification.heavy_verification")
            except KeyError:
                system_prompt = "Australian law expert. Thoroughly verify legal accuracy, citations, precedents, and reasoning."
                heavy_verification = "Provide comprehensive legal accuracy review: verify all citations, check legal reasoning, identify any errors in law or procedure, and ensure Australian English compliance."

            critique_prompt = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": primary_text + "\n\n" + heavy_verification,
                },
            ]
        else:
            # For any other level, use standard verification
            # This maintains backward compatibility
            return self.verify(primary_text)

        # Use Claude 4 Opus for all verification, regardless of generation model
        verification_client = LLMClient(
            "anthropic/claude-opus-4", **self.default_params
        )
        params = {"temperature": 0, "top_p": 0.2}
        if CONFIG.use_token_limits:
            params["max_tokens"] = 32768 if level == "light" else 65536
        verification_result, usage = verification_client.complete(
            critique_prompt, skip_citation_verification=True, **params
        )
        return verification_result
