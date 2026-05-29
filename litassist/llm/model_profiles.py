"""
Model family patterns and parameter profiles for LLM clients.

This module contains configuration data for different LLM model families,
including regex patterns for model detection and allowed parameter profiles.
"""

# Model family patterns for dynamic parameter handling.
#
# DO NOT REDUCE THE SET OF MODELS THIS TABLE SUPPORTS. This file is
# intentionally universal -- it must translate parameters for ANY model
# reachable through OpenRouter, including providers/families that no
# active command in `model_configs.yaml` currently uses. The user may
# swap any command to any OpenRouter model at any time without touching
# this code.
#
# The only legitimate reason to edit MODEL_PATTERNS or PARAMETER_PROFILES
# is when OpenRouter's API surface for a family changes (new parameter
# added, existing parameter renamed, response format changed). Removing
# entries because "we don't use that model today" breaks the contract
# of universal coverage.
#
# Ordering matters: more specific patterns must precede general ones.
MODEL_PATTERNS = {
    "openai_reasoning": r"openai/o\d+",
    "gpt5.5": r"openai/gpt-5\.5",
    "gpt5.1": r"openai/gpt-5\.1",
    "gpt5-pro": r"openai/gpt-5-pro$",
    "gpt5": r"openai/gpt-5$",
    # Opus 4.7/4.8 are reasoning models that removed sampling params and use the
    # extended effort scale; matched before the general Claude-4 pattern.
    "claude_opus_4_8": r"anthropic/claude-opus-4\.8",
    "claude_opus_4_7": r"anthropic/claude-opus-4\.7",
    "claude4_sampling": r"anthropic/claude-(opus-4|sonnet-4)(\.\d+)?",
    "anthropic": r"anthropic/claude",
    "google": r"google/(gemini|palm|bard)",
    "openai_standard": r"openai/(gpt|chatgpt)",
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
    "gpt5-pro": {
        "allowed": [
            "reasoning",  # OpenRouter reasoning object (effort: "high" locked for pro)
            "verbosity",  # low/medium/high
            "max_completion_tokens",  # NOT max_tokens
            "response_format",  # Structured outputs
            "seed",  # Deterministic outputs
            "stop",  # Stop sequences
            "stream",  # Streaming
            "tools",  # Function/tool calling
            "tool_choice",  # Tool selection
            "parallel_tool_calls",  # Parallel tool execution
            # EXCLUDED: temperature, top_p, frequency_penalty, presence_penalty,
            #           logprobs, top_logprobs, logit_bias, max_tokens
            # GPT-5 Pro does not support sampling parameters - they destabilize
            # the internal reasoning process
        ],
        "transforms": {
            "max_tokens": "max_completion_tokens",
        },
        "system_message_support": True,  # This family supports system messages
    },
    "gpt5": {
        "allowed": [
            "reasoning",  # OpenRouter reasoning object (supports minimal/low/medium/high)
            "verbosity",  # low/medium/high
            "max_completion_tokens",  # NOT max_tokens
            "response_format",  # Structured outputs
            "seed",  # Deterministic outputs
            "stop",  # Stop sequences
            "stream",  # Streaming
            "tools",  # Function/tool calling
            "tool_choice",  # Tool selection
            "parallel_tool_calls",  # Parallel tool execution
            # This family removed sampling parameters to maintain reasoning quality
        ],
        "transforms": {
            "max_tokens": "max_completion_tokens",
        },
        "system_message_support": True,
    },
    "gpt5.1": {
        "allowed": [
            "reasoning",  # OpenRouter reasoning object (none/low/medium/high)
            "verbosity",  # low/medium/high
            "max_completion_tokens",  # NOT max_tokens
            "response_format",  # Structured outputs
            "seed",  # Deterministic outputs
            "stop",  # Stop sequences
            "stream",  # Streaming
            "tools",  # Function/tool calling
            "tool_choice",  # Tool selection
            "parallel_tool_calls",  # Parallel tool execution
            # GPT-5.1 uses adaptive reasoning - no sampling parameters
        ],
        "transforms": {
            "max_tokens": "max_completion_tokens",
        },
        "system_message_support": True,
    },
    "gpt5.5": {
        "allowed": [
            "reasoning",  # OpenRouter reasoning object (none/low/medium/high)
            "verbosity",  # low/medium/high
            "max_completion_tokens",  # NOT max_tokens
            "response_format",  # Structured outputs
            "seed",  # Deterministic outputs
            "stop",  # Stop sequences
            "stream",  # Streaming
            "tools",  # Function/tool calling
            "tool_choice",  # Tool selection
            "parallel_tool_calls",  # Parallel tool execution
            # GPT-5.5 maintains GPT-5 family constraints - no sampling parameters
        ],
        "transforms": {
            "max_tokens": "max_completion_tokens",
        },
        "system_message_support": True,
    },
    "claude_opus_4_8": {
        # Opus 4.8: adaptive thinking, extended effort scale (low..high..xhigh..
        # max). Sampling params (temperature/top_p/top_k) were removed and return
        # 400 on non-default values, so they are not allowed here.
        "allowed": [
            "max_tokens",
            "stop",
            "reasoning",  # OpenRouter reasoning object
            "response_format",
            "structured_outputs",
            "tools",
            "tool_choice",
            "stream",
        ],
        "transforms": {},
    },
    "claude_opus_4_7": {
        # Opus 4.7: same sampling removal as 4.8 (xhigh-default reasoning).
        "allowed": [
            "max_tokens",
            "stop",
            "reasoning",
            "response_format",
            "structured_outputs",
            "tools",
            "tool_choice",
            "stream",
        ],
        "transforms": {},
    },
    "claude4_sampling": {
        # Other Claude 4.x (older opus, all sonnet-4.x): sampling honoured, but
        # temperature and top_p cannot both be sent (Anthropic since 4.1; the
        # not-both rule is enforced in get_model_parameters).
        "allowed": [
            "temperature",
            "top_p",
            "top_k",
            "max_tokens",
            "stop",
            "reasoning",
            "response_format",
            "structured_outputs",
            "tools",
            "tool_choice",
            "stream",
            "min_p",
            "top_a",
            "repetition_penalty",
        ],
        "transforms": {},
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
