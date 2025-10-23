"""
Model family patterns and parameter profiles for LLM clients.

This module contains configuration data for different LLM model families,
including regex patterns for model detection and allowed parameter profiles.
"""

# Model family patterns for dynamic parameter handling
MODEL_PATTERNS = {
    "openai_reasoning": r"openai/o\d+",  # Matches o1, o3, o1-pro, o3-pro, o4, etc.
    "gpt5": r"openai/gpt-5(-pro)?",  # GPT-5 and GPT-5 Pro (August/October 2025)
    "claude4": r"anthropic/claude-(opus-4|sonnet-4)(\.\d+)?",  # Claude 4 models (includes 4.1, 4.5, etc.)
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
