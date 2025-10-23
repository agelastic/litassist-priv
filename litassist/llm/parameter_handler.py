"""
Parameter handling functions for LLM clients.

This module contains functions for converting, filtering, and validating
LLM parameters based on model families and profiles.
"""

import re
from .model_profiles import MODEL_PATTERNS, PARAMETER_PROFILES


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
