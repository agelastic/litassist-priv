"""
Parameter handling functions for LLM clients.

This module contains functions for converting, filtering, and validating
LLM parameters based on model families and profiles.

This is the TRANSLATION layer. The decoding parameters in `model_configs.yaml`
are the per-command INTENT; this module adapts them per model family at call time:
  - thinking_effort is mapped to OpenRouter's reasoning object (or dropped for
    families with no reasoning tier);
  - verbosity is kept for the GPT-5 and Claude families, dropped for the o-series
    / Grok / Gemini families;
  - sampling params NOT in a family's `allowed` profile are silently dropped here
    (e.g. temperature/top_p are dropped for the GPT-5/o3 reasoning families and for
    Opus 4.7/4.8, which expose no sampling);
  - BUT the OpenRouter-extension sampling params (min_p, top_a, repetition_penalty,
    see get_openrouter_params) are NOT dropped here - they are forwarded for every
    model and it is OpenRouter / the target provider that ignores the ones it does
    not support.
Consequence for editing model_configs.yaml: when you swap a command's model, only
ADD parameters - do not trim. Params the new model cannot use are either dropped
here (effort / verbosity / sampling-not-in-`allowed`) or ignored downstream by
OpenRouter (the min_p/top_a/repetition_penalty extensions); removing them changes
intent and gains nothing.
"""

import re
from .model_profiles import MODEL_PATTERNS, PARAMETER_PROFILES


def convert_thinking_effort(effort: str, model_name: str) -> dict:
    """
    Convert universal thinking_effort to OpenRouter's reasoning object format.

    Args:
        effort: Universal effort level (none, minimal, low, medium, high, xhigh,
            max). xhigh is the provider ceiling for Opus 4.7/4.8 and GPT-5.5, so
            "max" maps to xhigh there; other families cap xhigh/max to high.
        model_name: Full model identifier (provider/model slug)

    Returns:
        Dict with OpenRouter reasoning object
    """

    if effort == "none":
        return {}  # Don't send reasoning parameter

    # OpenRouter unified reasoning object approach - ALL models go through OpenRouter
    model_family = get_model_family(model_name)

    # Check model type for appropriate sub-parameters
    if model_family in ["openai_reasoning", "gpt5", "gpt5.1", "gpt5.5", "gpt5-pro", "xai"]:
        # Effort-based models (OpenAI, Grok, GPT-5)
        effort_map = {
            "minimal": "minimal",  # GPT-5 specific
            "low": "low",
            "medium": "medium",
            "high": "high",
            "xhigh": "high",  # Default cap; GPT-5.5 overrides below
            "max": "high",  # Map max to highest available
        }
        mapped_effort = effort_map.get(effort, "medium")

        # GPT-5.5 exposes an xhigh reasoning tier (none/low/medium/high/xhigh);
        # "max" maps to that ceiling. Older GPT-5 variants and o-series cap at
        # high. REMINDER: re-check this when adding a new GPT-5.x / o-series model
        # in case its effort tiers differ.
        if model_family == "gpt5.5" and effort in ("xhigh", "max"):
            mapped_effort = "xhigh"

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
        # GPT-5 family supports both reasoning and verbosity
        elif model_family in ["gpt5", "gpt5.1", "gpt5.5", "gpt5-pro"]:
            return {
                "reasoning": {"effort": mapped_effort}
                # Verbosity handled separately via convert_verbosity
            }
        else:
            return {"reasoning": {"effort": mapped_effort}}

    elif model_family in ["claude_opus_4_7", "claude_opus_4_8"]:
        # Opus 4.7/4.8 effort scale tops out at xhigh. OpenRouter's reasoning.effort
        # enum is none/minimal/low/medium/high/xhigh - there is NO "max" tier, and
        # sending "max" returns HTTP 400, so the universal "max" maps to xhigh.
        effort_map = {
            "minimal": "low",
            "low": "low",
            "medium": "medium",
            "high": "high",
            "xhigh": "xhigh",
            "max": "xhigh",
        }
        # 4.7 defaults to xhigh, 4.8 to high (per Anthropic); only used when an
        # unrecognised effort string is passed.
        default = "xhigh" if model_family == "claude_opus_4_7" else "high"
        return {"reasoning": {"effort": effort_map.get(effort, default)}}

    elif model_family in ["claude4_sampling", "anthropic"]:
        # Older Claude (opus 4.0-4.6, sonnet 4.x, claude-3.x) has no xhigh/max
        # effort tier - cap to high.
        effort_map = {
            "minimal": "low",
            "low": "low",
            "medium": "medium",
            "high": "high",
            "xhigh": "high",
            "max": "high",
        }
        return {"reasoning": {"effort": effort_map.get(effort, "medium")}}

    elif model_family == "google":
        # Google/Gemini models - try unified reasoning
        effort_map = {
            "minimal": "low",
            "low": "low",
            "medium": "medium",
            "high": "high",
            "xhigh": "high",
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
        model_name: The full model identifier (provider/model slug)

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
    return {"reasoning", "min_p", "top_a", "repetition_penalty", "provider", "verbosity"}


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

    # Normalize a directly-supplied reasoning.effort through the same per-family
    # mapping used for thinking_effort, so a caller passing `reasoning` directly
    # cannot smuggle an effort tier the model rejects (e.g. xhigh/max to o3 or
    # sonnet). Only runs when thinking_effort did not already own reasoning.
    direct_reasoning = params_to_process.get("reasoning")
    if isinstance(direct_reasoning, dict) and "effort" in direct_reasoning:
        effort_value = direct_reasoning["effort"]
        if effort_value is None or effort_value == "none":
            # No effort requested -> drop the reasoning object rather than
            # letting the effort_map default coerce it to medium.
            params_to_process.pop("reasoning", None)
        else:
            normalized = convert_thinking_effort(effort_value, model_name)
            if normalized.get("reasoning"):
                params_to_process["reasoning"] = {
                    **direct_reasoning,
                    **normalized["reasoning"],
                }
            else:
                params_to_process.pop("reasoning", None)

    # Handle verbosity parameter. Supported by the GPT-5 family (per OpenAI docs;
    # the OpenRouter capability snapshot may omit it, e.g. gpt-5.5) and by
    # Anthropic Claude; NOT accepted by o-series reasoning models, Grok 4.x, or
    # Gemini, so it is skipped for those. Because the capabilities file can be
    # incomplete for verbosity, it is NOT gated on supported_parameters here.
    # REMINDER: re-check this skip set when adding a model.
    if "verbosity" in params_to_process and params_to_process["verbosity"] is not None:
        verbosity = params_to_process.pop("verbosity")
        if model_family not in ("openai_reasoning", "xai", "google"):
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

    # Anthropic Claude 4.x (since 4.1) rejects temperature and top_p when both
    # are specified together. Keep temperature (primary control) and drop top_p.
    # Opus 4.7+ has no sampling params at all (handled by its profile), so this
    # only applies to the sampling-capable Claude 4.x family.
    if (
        model_family == "claude4_sampling"
        and "temperature" in filtered
        and "top_p" in filtered
    ):
        del filtered["top_p"]

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
