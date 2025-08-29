"""
LLM Client for LitAssist.

This module provides a unified interface for chat completions across different LLM providers,
handling parameter management and response processing.
"""

import re
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple

from litassist.utils import (
    timed,
    save_log,
    heartbeat,
    info_message,
    success_message,
)
from litassist.config import CONFIG
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
            "min_p",
            "top_a",
            "repetition_penalty",
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


def convert_thinking_effort(effort: str, model_name: str, use_openrouter: bool = True) -> dict:
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
                "max": "high"  # Map max to highest available
            }
            mapped_effort = effort_map.get(effort, "medium")
            
            # Only include minimal for GPT-5 and o4-mini
            if mapped_effort == "minimal" and model_family not in ["gpt5"] and "o4" not in model_name:
                mapped_effort = "low"  # Fallback for non-GPT-5/o4 models
            
            # Special handling for o4-mini with summary field
            if "o4" in model_name:
                return {
                    "reasoning": {
                        "effort": mapped_effort,
                        "summary": "auto"  # New o4 feature for automatic summarization
                    }
                }
            # GPT-5 supports both reasoning and verbosity
            elif model_family == "gpt5":
                return {
                    "reasoning": {
                        "effort": mapped_effort
                    }
                    # Verbosity handled separately via convert_verbosity
                }
            else:
                return {
                    "reasoning": {
                        "effort": mapped_effort
                    }
                }
        
        elif model_family in ["claude4", "anthropic"]:
            # Token-based models (Anthropic)
            token_map = {
                "minimal": 1024,
                "low": 1024,
                "medium": 8192,
                "high": 16384,
                "max": 32000  # Max allowed by OpenRouter
            }
            return {
                "reasoning": {
                    "max_tokens": token_map.get(effort, 8192)
                }
            }
        
        elif model_family == "google":
            # Google/Gemini models - try unified reasoning
            effort_map = {
                "minimal": "low",
                "low": "low",
                "medium": "medium",
                "high": "high",
                "max": "high"
            }
            return {
                "reasoning": {
                    "effort": effort_map.get(effort, "medium")
                }
            }
    
    else:
        # Direct vendor API calls (if not using OpenRouter)
        # This path is rarely used as we route most through OpenRouter
        model_family = get_model_family(model_name)
        
        if model_family in ["openai_reasoning", "gpt5"]:
            # Direct OpenAI API uses reasoning_effort
            effort_map = {
                "minimal": "minimal",
                "low": "low",
                "medium": "medium",
                "high": "high",
                "max": "high"
            }
            mapped = effort_map.get(effort, "medium")
            if mapped == "minimal" and model_family != "gpt5":
                mapped = "low"
            return {"reasoning_effort": mapped}
        
        elif model_family in ["anthropic", "claude4"]:
            # Direct Anthropic API format
            token_map = {
                "minimal": 1024,
                "low": 1024,
                "medium": 8192,
                "high": 16384,
                "max": 32768
            }
            budget = token_map.get(effort, 8192)
            return {
                "thinking": {
                    "enabled": True,
                    "budget_tokens": budget
                }
            }
        
        elif model_family == "google":
            # Direct Google API format
            return {
                "thinking_config": {
                    "include_thoughts": True,
                    "thinking_budget": -1
                }
            }
    
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
    if "thinking_effort" in params_to_process and params_to_process["thinking_effort"] is not None:
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
            "force_verify": True,  # Always verify for foundational docs
        },
        # Strategy - enhanced multi-step legal reasoning
        "strategy": {
            "model": "anthropic/claude-opus-4.1",
            "temperature": 0.2,  # Controlled creativity for strategic thinking
            "top_p": 0.8,  # Focused but not overly restrictive
            "thinking_effort": "max",  # Universal parameter, translates to reasoning object
            "verbosity": "medium",  # Balanced depth in strategic analysis
            "max_completion_tokens": 16384,  # Extended output for comprehensive strategies
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
            "max_completion_tokens": 32768,  # Extended output for comprehensive drafts
        },
        # Digest - mode-dependent settings
        "digest-summary": {
            "model": "anthropic/claude-sonnet-4",
            "temperature": 0.1,
            "top_p": 0.1,  # Fixed: was 0, too restrictive
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
            "temperature": 0.1,
            "top_p": 0.2,
            "thinking_effort": "low",  # Fast thinking for rapid search results
            "verbosity": "low",  # Concise search summaries
            "force_verify": False,  # Don't force strict verification
        },
        # Verification - automatic verification for high-risk commands
        "verification": {
            "model": "anthropic/claude-opus-4.1",
            "temperature": 0,
            "top_p": 0.2,
            "thinking_effort": "high",
            "force_verify": False,  # Don't double-verify since this IS verification
        },
        # Verify sub-commands with specific model assignments
        "verify-reasoning": {
            "model": "openai/o3-pro",  # o3-pro for complex reasoning trace extraction
            "temperature": 0,
            "top_p": 0.2,
            "thinking_effort": "high",  # Universal parameter, translates to reasoning_effort
            "force_verify": False,
        },
        "verify-soundness": {
            "model": "anthropic/claude-opus-4.1",  # Opus for soundness checking
            "temperature": 0,
            "top_p": 0.2,
            "thinking_effort": "high",
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
            # Extended token limit for detailed briefs
            "thinking_effort": "high",  # Universal parameter, translates to reasoning object
            "verbosity": "high",  # Detailed comprehensive briefs
            "max_completion_tokens": 32768,  # 32K tokens for comprehensive output
        },
        # Caseplan - LLM-driven workflow planning
        "caseplan": {
            "model": "openai/o4-mini-high",
            "temperature": 0.3,
            "top_p": 0.7,
            "force_verify": False,
        },
        # Caseplan assessment - budget recommendation (Sonnet)
        "caseplan-assessment": {
            "model": "openai/o4-mini-high",
            "temperature": 0.2,
            "top_p": 0.7,
            "force_verify": False,
        },
        # Chain of Verification - fast, efficient question generation
        "cove": {
            "model": "anthropic/claude-sonnet-4",
            "temperature": 0.2,
            "top_p": 0.8,
            "force_verify": False,  # Avoid recursive verification
        },
        # CoVe sub-stages with separate model control
        "cove-questions": {
            "model": "anthropic/claude-sonnet-4",  # Fast question generation
            "temperature": 0.2,
            "top_p": 0.8,
            "force_verify": False,
        },
        "cove-answers": {
            "model": "anthropic/claude-opus-4.1",  # Independent answering
            "temperature": 0.1,
            "top_p": 0.8,
            "thinking_effort": "high",
            "force_verify": False,
        },
        "cove-verify": {
            "model": "anthropic/claude-sonnet-4",  # Inconsistency detection
            "temperature": 0.2,
            "top_p": 0.8,
            "force_verify": False,
        },
        "cove-final": {
            "model": "anthropic/claude-opus-4.1",  # Final regeneration with highest quality
            "temperature": 0.1,
            "top_p": 0.8,
            "thinking_effort": "high",
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
        self._client = None  # Will be created when needed




    # Add heartbeat messages so users see progress during lengthy LLM calls
    # The verification helpers already had their own heartbeat wrapper, but that
    # resulted in progress messages only during the verification stage.  By
    # moving the heartbeat decorator to the main `complete` method we ensure
    # that all long-running LLM invocations – including the initial content
    # generation used by commands such as `extractfacts` – emit "…still working,
    # please wait…" notifications.  Down-stream helpers that themselves call
    # `complete` therefore no longer need their own heartbeat wrappers.
    # The enclosing `complete` method now emits heartbeat updates, so we no
    # longer need a second heartbeat layer here. Retaining only the timing
    # decorator avoids duplicated progress messages.
    @heartbeat(CONFIG.heartbeat_interval)
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
                    today_date = datetime.now().strftime("%B %d, %Y")
                    enhanced_content = f"{system_content}\n\nToday is {today_date}.\n\n{msg.get('content', '')}"
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
            # Prepend base.australian_law to all system messages
            australian_law_prompt = PROMPTS.get("base.australian_law")
            if australian_law_prompt:
                modified_messages = []
                for msg in messages:
                    if msg.get("role") == "system":
                        content = msg.get("content", "")
                        # Only prepend if not already present
                        if australian_law_prompt not in content:
                            today_date = datetime.now().strftime("%B %d, %Y")
                            content = f"{australian_law_prompt}\n\nToday is {today_date}.\n\n{content}"
                        modified_messages.append({"role": "system", "content": content})
                    else:
                        modified_messages.append(msg)
                messages = modified_messages

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
            response = execute_api_call_with_retry(
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

            # Extract content and usage from chat response
            content, usage = extract_content_and_usage(response)
        finally:
            # No cleanup needed with client instances
            pass

        if not skip_citation_verification:
            # Citation verification workflow
            try:
                content, verification_issues = process_citation_verification(
                    content=content,
                    client_instance=self,
                    skip_verification=False
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
                        validate_func=self.validate_and_verify_citations
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

