"""
LLM Client for LitAssist.

This module provides a unified interface for chat completions across different LLM providers,
handling parameter management and response processing.
"""

import re
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple

from litassist.timing import timed
from litassist.logging_utils import save_log
from litassist.utils.core import heartbeat
from litassist.utils.formatting import info_message, success_message
from litassist.config import get_config
from litassist.prompts import PROMPTS
import time
from litassist.citation_verify import (
    CitationVerificationError,
)
from .api_handlers import execute_api_call_with_retry
from .verification import LLMVerificationMixin
from .response_parser import extract_content_and_usage
from .retry_handler import handle_citation_retry
from .citation_handler import process_citation_verification, handle_retry_failure
from .tools import get_tool_definitions, execute_tool, format_tool_response

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
        "system_message_support": False,  # o1/o3 models don't support system messages (but DO support tools as of 2025)
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
    # Universal parameters supported by OpenRouter across models
    "openrouter_universal": {
        "allowed": [
            "temperature",
            "top_p",
            "max_tokens",
            "reasoning",  # OpenRouter unified reasoning object
            "verbosity",
            "min_p",
            "top_a",
            "repetition_penalty",
            "frequency_penalty",
            "presence_penalty",
            "response_format",
            "logit_bias",
            "logprobs",
            "top_logprobs",
            "seed",
            "stop",
        ],
    },
}


def convert_thinking_effort(effort: str, model_name: str) -> dict:
    """
    Convert universal thinking_effort to OpenRouter's reasoning object format.

    Args:
        effort: Universal effort level (none, minimal, low, medium, high, max)
        model_name: Full model name (e.g., "openai/o3-pro", "anthropic/claude-4")

    Returns:
        Dict with OpenRouter reasoning object
    """

    if effort == "none":
        return {}  # Don't send reasoning parameter

    # OpenRouter unified reasoning object approach - ALL models go through OpenRouter
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

    # For all other models, don't add reasoning parameters
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


def get_openrouter_params() -> set:
    """
    Get the set of OpenRouter-specific parameters that need special handling.

    These parameters are not part of the standard OpenAI API and must be
    passed through extra_body when using the OpenAI SDK with OpenRouter.

    Returns:
        Set of parameter names that are OpenRouter-specific
    """
    return {"reasoning", "min_p", "top_a", "repetition_penalty"}


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
    # All models go through OpenRouter
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
        reasoning_params = convert_thinking_effort(effort, model_name)
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

    # Get OpenRouter-specific parameters
    openrouter_params = get_openrouter_params()

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
        elif param in openrouter_params:
            # Preserve OpenRouter-specific params - they'll be moved to extra_body in api_handlers
            filtered[param] = value
        # Silently drop other unsupported parameters
        # Note: We don't add universal parameters automatically to maintain model-specific restrictions

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

    All models use "provider/model" format and route through OpenRouter.

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
            "thinking_effort": "high",  # Critical foundational command needs thorough thinking
            "force_verify": True,  # Always verify for foundational docs
            "disable_tools": True,  # Claude Sonnet 4 has tool calling issues on OpenRouter (Sept 2025)
        },
        # Strategy - enhanced multi-step legal reasoning
        "strategy": {
            "model": "anthropic/claude-opus-4.1",
            "temperature": 0.2,  # Controlled creativity for strategic thinking
            "top_p": 0.8,  # Focused but not overly restrictive
            "thinking_effort": "max",  # Universal parameter, translates to reasoning object
            "verbosity": "medium",  # Balanced depth in strategic analysis
            "force_verify": True,  # Always verify for strategic guidance
        },
        # Strategy sub-type for analysis
        "strategy-analysis": {
            "model": "openai/o3-pro",
            # Note: o3-pro ignores temperature and top_p parameters
            "thinking_effort": "max",  # Universal parameter, translates to reasoning_effort
        },
        # Brainstorm - varied temperatures for different approaches
        "brainstorm-orthodox": {
            "model": "anthropic/claude-opus-4.1",
            "temperature": 0.3,
            "top_p": 0.7,
            "thinking_effort": "medium",  # Moderate thinking for balanced analysis
            "force_verify": True,  # Conservative analysis requires verification
        },
        "brainstorm-unorthodox": {
            "model": "x-ai/grok-4",
            "temperature": 0.8,
            "top_p": 0.95,
            "min_p": 0.05,  # Allow more diverse token selection
            "repetition_penalty": 1.2,  # Reduce repetitive ideas
            # Kimi-K2 currently has an 8K context window. Supplying an
            # excessively high `max_tokens` causes "Error processing stream".
            # Explicitly cap it so the request succeeds.
            # "max_tokens": 4096,
            "force_verify": True,  # Auto-verify creative outputs
        },
        "brainstorm-analysis": {
            "model": "openai/o3-pro",
            "temperature": 0.2,
            "top_p": 0.8,
            "thinking_effort": "high",  # Universal parameter, translates to reasoning_effort
        },
        # Draft - superior technical writing (o3 model with very limited parameter support)
        "draft": {
            "model": "openai/o3-pro",
            "thinking_effort": "high",  # Universal parameter
            "verbosity": "high",  # Comprehensive legal drafting
        },
        # Digest - mode-dependent settings
        "digest-summary": {
            "model": "anthropic/claude-sonnet-4",
            "temperature": 0.2,
            "top_p": 0.3,  # Fixed: was 0, too restrictive
            "thinking_effort": "medium",  # Simple summarization task
            "disable_tools": True,  # Claude Sonnet 4 has tool calling issues on OpenRouter (Sept 2025)
        },
        "digest-issues": {
            "model": "anthropic/claude-opus-4.1",
            "temperature": 0.2,
            "top_p": 0.5,
            "thinking_effort": "high",  # Deep analysis for issue spotting
        },
        # Lookup - uses Gemini for rapid processing with verification
        # IMPORTANT: When changing models, adjust max_content_tokens in lookup.py
        # Current: Gemini 2.5 Pro with 1M context window (using 900k for content)
        # Other models have smaller limits - see lookup.py line 528
        "lookup": {
            "model": "google/gemini-2.5-pro",
            "temperature": 0.2,
            "top_p": 0.4,
            "thinking_effort": "low",  # Fast thinking for rapid search results
            "verbosity": "low",  # Concise search summaries
            "force_verify": False,  # Don't force strict verification
        },
        # Verification - automatic verification for high-risk commands
        "verification": {
            "model": "anthropic/claude-opus-4.1",
            "temperature": 0.2,
            "top_p": 0.3,
            "thinking_effort": "high",
            "force_verify": False,  # Don't double-verify since this IS verification
        },
        "verification-light": {
            "model": "anthropic/claude-sonnet-4",  # Cost-effective for spelling/terminology
            "temperature": 0.2,  # Optimal for factual tasks per hallucination report
            "top_p": 0.2,  # Focused beam for consistency
            "thinking_effort": "medium",  # Just spelling/terminology checks
            "force_verify": False,  # Avoid loops
            "disable_tools": True,  # Claude Sonnet 4 has tool calling issues on OpenRouter (Sept 2025)
        },
        "verification-heavy": {
            "model": "openai/gpt-5",  # <1% hallucination rate for critical verification
            "temperature": 0.2,  # Optimal per hallucination report
            "top_p": 0.3,  # Slightly wider beam for comprehensive checking
            "thinking_effort": "max",  # max for critical tasks (maps to high for GPT-5)
            "force_verify": False,  # Avoid loops
        },
        # Verify sub-commands with specific model assignments
        "verify-reasoning": {
            "model": "openai/o3-pro",  # o3-pro for complex reasoning trace extraction
            "temperature": 0.2,  # o3-pro ignores temperature but set for consistency
            "top_p": 0.3,
            "thinking_effort": "high",  # Universal parameter, translates to reasoning_effort
            "force_verify": False,
        },
        "verify-soundness": {
            "model": "anthropic/claude-opus-4.1",  # Opus for soundness checking
            "temperature": 0.2,
            "top_p": 0.3,
            "thinking_effort": "max",  # max gives 32K thinking tokens vs 16K for high
            "force_verify": False,
        },
        # Counsel's Notes - strategic analysis from advocate's perspective
        "counselnotes": {
            "model": "openai/o3-pro",
            "temperature": 0.3,
            "top_p": 0.7,
            "thinking_effort": "high",  # Universal parameter, translates to reasoning_effort
            "force_verify": True,  # Strategic counsel's notes require verification
        },
        # Barrister's brief - comprehensive document generation
        "barbrief": {
            "model": "openai/o3-pro",
            # o3-pro for comprehensive analysis and superior drafting
            "thinking_effort": "high",  # Universal parameter, translates to reasoning object
            "verbosity": "high",  # Detailed comprehensive briefs
        },
        # Caseplan - LLM-driven workflow planning
        "caseplan": {
            "model": "anthropic/claude-sonnet-4",
            "temperature": 0.5,
            "force_verify": False,
            "disable_tools": True,  # Claude Sonnet 4 has tool calling issues on OpenRouter (Sept 2025)
        },
        # Caseplan assessment - budget recommendation (Sonnet)
        "caseplan-assessment": {
            "model": "anthropic/claude-sonnet-4",
            "temperature": 0.5,
            "force_verify": False,
            "disable_tools": True,  # Claude Sonnet 4 has tool calling issues on OpenRouter (Sept 2025)
        },
        # Chain of Verification - fast, efficient question generation
        "cove": {
            "model": "anthropic/claude-sonnet-4",
            "temperature": 0.2,
            "top_p": 0.8,
            "thinking_effort": "medium",  # General CoVe coordination
            "force_verify": False,  # Avoid recursive verification
            "disable_tools": True,  # Claude Sonnet 4 has tool calling issues on OpenRouter (Sept 2025)
        },
        # CoVe sub-stages with separate model control
        "cove-questions": {
            "model": "anthropic/claude-sonnet-4",  # Fast question generation
            "temperature": 0.2,
            "top_p": 0.8,
            "thinking_effort": "low",  # Fast question generation, minimal thinking needed
            "force_verify": False,
            "disable_tools": True,  # Claude Sonnet 4 has tool calling issues on OpenRouter (Sept 2025)
        },
        "cove-answers": {
            "model": "openai/gpt-5",  # GPT-5 for <1% hallucination rate
            "temperature": 0.2,
            "top_p": 0.3,
            "thinking_effort": "max",  # max for consistency (maps to high for GPT-5)
            "force_verify": False,
        },
        "cove-verify": {
            "model": "anthropic/claude-sonnet-4",  # Inconsistency detection
            "temperature": 0.2,
            "top_p": 0.3,
            "thinking_effort": "high",  # Critical inconsistency detection needs careful analysis
            "force_verify": False,
            "disable_tools": True,  # Claude Sonnet 4 has tool calling issues on OpenRouter (Sept 2025)
        },
        "cove-final": {
            "model": "openai/gpt-5",  # GPT-5 for <1% hallucination rate in final output
            "temperature": 0.2,
            "top_p": 0.4,
            "thinking_effort": "max",  # max for consistency (maps to high for GPT-5)
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
                "disable_tools": True,  # Claude Sonnet 4 has tool calling issues on OpenRouter (Sept 2025)
            }
            # Use default configuration for commands without specific config
            # This is expected behavior for many commands
        else:
            config = cls.COMMAND_CONFIGS[config_key].copy()

        # Extract special flags
        force_verify = config.pop("force_verify", False)
        disable_tools = config.pop("disable_tools", False)

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
        client._disable_tools = disable_tools

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
            config_key, {"model": "anthropic/claude-sonnet-4", "disable_tools": True}
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


class LLMClient(LLMVerificationMixin):
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

        # Set token limit from config if enabled and not explicitly specified
        config = get_config()
        if config.use_token_limits:
            # Determine if we need to transform max_tokens to another parameter
            test_params = {"max_tokens": 1}
            filtered = get_model_parameters(model, test_params)
            token_param = (
                "max_completion_tokens"
                if "max_completion_tokens" in filtered
                else "max_tokens"
            )

            if token_param not in default_params:
                # Use token limit from config
                default_params[token_param] = config.token_limit

        self.default_params = default_params
        self._client = None  # Will be created when needed

    # Add heartbeat messages so users see progress during lengthy LLM calls
    # The verification helpers already had their own heartbeat wrapper, but that
    # resulted in progress messages only during the verification stage.  By
    # moving the heartbeat decorator to the main `complete` method we ensure
    # that all long-running LLM invocations – including the initial content
    # generation used by commands such as `extractfacts` – emit "…still working,
    # please wait…" notifications.  Down-stream helpers that themselves call
    # `complete` therefore no longer need their own heartbeat wrappers.
    def _format_date_string(self):
        """Get current date formatted for prompt injection."""
        import pytz
        sydney_tz = pytz.timezone('Australia/Sydney')
        return datetime.now(sydney_tz).strftime("%B %d, %Y")
    
    def _prepare_messages_for_model(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Prepare messages based on model's system message support."""
        if not supports_system_messages(self.model):
            # For o1/o3 models - merge system into first user message
            return self._merge_system_into_user(messages)
        else:
            # For all other models - add Australian law to system messages
            return self._add_australian_law_to_system(messages)
    
    def _merge_system_into_user(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Merge system messages into first user message for o1/o3 models."""
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        non_system_messages = [msg for msg in messages if msg.get("role") != "system"]
        
        if not system_messages:
            # No system messages to merge
            return messages
        
        # Combine all system content
        system_content = "\n".join([msg.get("content", "") for msg in system_messages])
        if "Australian English" not in system_content:
            system_content += "\n" + PROMPTS.get("base.australian_law")
        
        # Find first user message and prepend system content
        modified_messages = []
        for i, msg in enumerate(non_system_messages):
            if msg.get("role") == "user":
                content = f"{system_content}\n\n{msg.get('content', '')}"
                modified_messages.append({"role": "user", "content": content})
                modified_messages.extend(non_system_messages[i + 1:])
                return modified_messages
        
        # No user message found - just return non-system messages
        return non_system_messages
    
    def _add_australian_law_to_system(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Add Australian law prompt to system messages."""
        australian_law = PROMPTS.get("base.australian_law")
        if not australian_law:
            return messages
            
        modified_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                # Only add if not already present
                if australian_law not in content:
                    content = f"{australian_law}\n\n{content}"
                modified_messages.append({"role": "system", "content": content})
            else:
                modified_messages.append(msg)
        
        return modified_messages
    
    def _add_date_instruction(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Add appropriate date instruction based on tool availability."""
        if getattr(self, '_disable_tools', False):
            # Tools disabled - inject date directly
            today_date = self._format_date_string()
            date_text = PROMPTS.get("base.date_fallback_instruction").format(date=today_date)
        else:
            # Tools enabled - use tool instruction
            date_text = PROMPTS.get("base.date_tool_instruction")
        
        # Add to first system or user message
        modified_messages = []
        date_added = False
        
        for msg in messages:
            if not date_added and msg.get("role") in ["system", "user"]:
                content = msg.get("content", "")
                content = f"{date_text}\n\n{content}"
                modified_messages.append({"role": msg["role"], "content": content})
                date_added = True
            else:
                modified_messages.append(msg)
        
        return modified_messages

    # The enclosing `complete` method now emits heartbeat updates, so we no
    # longer need a second heartbeat layer here. Retaining only the timing
    # decorator avoids duplicated progress messages.
    @heartbeat()  # Uses heartbeat_interval from config.yaml
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
        # Step 1: Handle model-specific message formatting
        messages = self._prepare_messages_for_model(messages)
        
        # Step 2: Add date instruction (tool or direct based on disable_tools)
        messages = self._add_date_instruction(messages)

        # Merge default and override parameters
        params = {**self.default_params, **overrides}

        # Determine the correct model name
        model_name = self.model

        # Extract just the model name for direct OpenAI models
        if (
            self.model.startswith("openai/")
            and "/" in self.model
            and not get_model_family(self.model) == "openai_reasoning"
        ):
            model_name = self.model.replace("openai/", "")

        try:
            # Filter parameters based on model capabilities
            filtered_params = get_model_parameters(self.model, params)

            # Check if tools should be disabled for this client
            if getattr(self, '_disable_tools', False):
                # Date has already been injected by _add_date_instruction at line 966
                logging.info(f"Tools disabled for {self.model}, using date injection fallback")
                
                # Log the prepared messages
                save_log(
                    f"llm_{self.model.replace('/', '_')}_messages",
                    {
                        "model": self.model,
                        "messages_sent": messages,  # Use already-prepared messages
                        "params": filtered_params,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "tools_disabled": True,
                    },
                )
                
                # Call API without tools using prepared messages
                response = execute_api_call_with_retry(
                    model_name, messages, filtered_params
                )
            else:
                # Add tool definitions for date handling
                tools = get_tool_definitions()

                # Add tools to parameters (most models support this)
                # We'll try with tools, and fall back without if it fails
                filtered_params_with_tools = filtered_params.copy()
                filtered_params_with_tools["tools"] = tools
                # Let the model decide when to call tools (follows "MUST" instruction in prompt)

                # Log the final messages being sent to the API
                save_log(
                    f"llm_{self.model.replace('/', '_')}_messages",
                    {
                        "model": self.model,
                        "messages_sent": messages,
                        "params": filtered_params_with_tools,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )

                # Use ChatCompletion API with retry logic - try with tools first
                try:
                    response = execute_api_call_with_retry(
                        model_name, messages, filtered_params_with_tools
                    )

                    # Check if response is empty (some models don't support forced tool calls)
                    if (
                        hasattr(response, "choices")
                        and response.choices
                        and hasattr(response.choices[0], "message")
                        and not response.choices[0].message.content
                        and not getattr(response.choices[0].message, "tool_calls", None)
                    ):
                        # Empty response - model doesn't support forced tools
                        # Fall back to regular call without tools
                        logging.info(
                            f"Model {model_name} returned empty with forced tools, falling back"
                        )
                        response = execute_api_call_with_retry(
                            model_name, messages, filtered_params
                        )
                except Exception as e:
                    # If tools aren't supported, fall back to regular call
                    if "tools" in str(e).lower() or "tool_choice" in str(e).lower():
                        logging.info(
                            f"Model {model_name} doesn't support tools, falling back"
                        )

                        # Replace tool instruction with direct date injection in messages
                        fallback_messages = []
                        today_date = self._format_date_string()
                        date_fallback = PROMPTS.get(
                            "base.date_fallback_instruction"
                        ).format(date=today_date)
                        tool_instruction = PROMPTS.get("base.date_tool_instruction")

                        for msg in messages:
                            if msg.get("role") in [
                                "system",
                                "user",
                            ] and tool_instruction in msg.get("content", ""):
                                # Replace tool instruction with date fallback
                                new_content = msg["content"].replace(
                                    tool_instruction, date_fallback
                                )
                                fallback_messages.append(
                                    {"role": msg["role"], "content": new_content}
                                )
                            else:
                                fallback_messages.append(msg)

                        response = execute_api_call_with_retry(
                            model_name, fallback_messages, filtered_params
                        )
                    else:
                        raise

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

            # Validate response structure before accessing
            if not response:
                raise Exception("Empty response from API")

            if not hasattr(response, "choices") or not response.choices:
                # Log the actual response for debugging
                logging.error(f"Invalid API response structure: {response}")
                error_msg = "API response missing 'choices' field"
                if hasattr(response, "error") and response.error:
                    if hasattr(response.error, "get"):
                        error_msg = f"API error: {response.error.get('message', 'Unknown error')}"
                    else:
                        error_msg = f"API error: {response.error}"
                raise Exception(error_msg)

            if not hasattr(response.choices[0], "message"):
                raise Exception(f"Invalid choice structure: {response.choices[0]}")

            # Check if the response contains tool calls
            if (
                hasattr(response.choices[0].message, "tool_calls")
                and response.choices[0].message.tool_calls
            ):
                # Handle tool calls - wrap in try/except for test compatibility
                try:
                    tool_calls = response.choices[0].message.tool_calls

                    for tool_call in tool_calls:
                        tool_name = tool_call.function.name
                        # Execute the tool (we know it's the now() function)
                        tool_result = execute_tool(tool_name)

                        # Format the tool response for the model
                        tool_message = format_tool_response(tool_name, tool_result)

                        # Add tool response to messages for follow-up
                        messages.append(response.choices[0].message.model_dump())
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_message,
                            }
                        )

                    # Make a follow-up call with the tool results
                    # This time without forcing tool use
                    filtered_params_followup = filtered_params.copy()
                    response = execute_api_call_with_retry(
                        model_name, messages, filtered_params_followup
                    )
                except (TypeError, AttributeError):
                    # In tests or if tool_calls is not properly formed, skip tool handling
                    logging.debug(
                        "Tool calls not available or malformed, skipping tool handling"
                    )

            # Extract content and usage from chat response
            content, usage = extract_content_and_usage(response)
        finally:
            # No cleanup needed with client instances
            pass

        if not skip_citation_verification:
            # Citation verification workflow
            try:
                content, verification_issues = process_citation_verification(
                    content=content, client_instance=self, skip_verification=False
                )

            except CitationVerificationError as e:
                # Strict mode failed - attempt retry with enhanced prompt
                try:
                    content, usage, retry_issues = handle_citation_retry(
                        error=e,
                        model=self.model,
                        model_name=model_name,
                        messages=messages,
                        params=params,
                        validate_func=self.validate_and_verify_citations,
                    )

                    # Display success message for fully verified retries
                    if not retry_issues:
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
                    handle_retry_failure(retry_error)
                finally:
                    # No cleanup needed with client instances
                    pass

        # Normalize usage data so it can be safely serialized
        if hasattr(usage, "_asdict"):
            usage = usage._asdict()
        elif hasattr(usage, "to_dict"):
            usage = usage.to_dict()
        elif not isinstance(usage, dict):
            usage = {"raw": str(usage)}

        # Log the LLM call with optional CoVe stage identification
        log_tag = f"llm_{self.model.replace('/', '_')}"
        command_context = getattr(self, "command_context", None)

        # Use specific log tag for CoVe stages
        if command_context and "cove" in command_context:
            log_tag = f"{command_context}_{self.model.replace('/', '_')}"

        save_log(
            log_tag,
            {
                "method": "complete",
                "model": self.model,
                "command_context": command_context,
                "messages": messages,
                "params": {**self.default_params, **overrides},
                "response": content,
                "usage": usage,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

        return content, usage
