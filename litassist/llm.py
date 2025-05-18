"""
LLM Client for LitAssist.

This module provides a unified interface for chat completions across different LLM providers,
handling parameter management and response processing.
"""

import openai
from typing import List, Dict, Any, Tuple

from litassist.utils import timed
from litassist.config import CONFIG


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
        client = LLMClient("anthropic/claude-3-sonnet", temperature=0.2, top_p=0.8)

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
            model: The model name to use (e.g., 'openai/gpt-4o', 'anthropic/claude-3-sonnet').
            **default_params: Default decoding parameters (temperature, top_p, etc.) to use
                             for all completions unless overridden.
        """
        self.model = model
        self.default_params = default_params

    @timed
    def complete(
        self, messages: List[Dict[str, str]], **overrides
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Run a single chat completion with the configured model.

        Args:
            messages: List of message dictionaries, each containing 'role' (system/user/assistant)
                     and 'content' (the message text).
            **overrides: Optional parameter overrides for this specific completion that will
                        take precedence over the default parameters.

        Returns:
            A tuple containing:
                - The generated text content (str)
                - The usage statistics dictionary (with prompt_tokens, completion_tokens, etc.)

        Raises:
            Exception: If the API call fails or returns an error.
        """
        # Merge default and override parameters
        params = {**self.default_params, **overrides}

        # Set API base based on model type
        original_api_base = openai.api_base
        original_api_key = openai.api_key

        # Determine the correct model name
        model_name = self.model

        # Use OpenRouter for non-OpenAI models
        if "/" in self.model and not self.model.startswith("openai/"):
            openai.api_base = CONFIG.or_base
            openai.api_key = CONFIG.or_key
        else:
            # Extract just the model name for OpenAI models
            if self.model.startswith("openai/"):
                model_name = self.model.replace("openai/", "")

        # Invoke the chat completion
        try:
            response = openai.ChatCompletion.create(
                model=model_name, messages=messages, **params
            )
        finally:
            # Restore original settings
            openai.api_base = original_api_base
            openai.api_key = original_api_key
        # Extract content and usage
        content = response.choices[0].message.content
        usage = getattr(response, "usage", {})
        return content, usage

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
        critique_prompt = [
            {"role": "system", "content": "Australian law only."},
            {
                "role": "user",
                "content": primary_text
                + "\n\nIdentify and correct any legal inaccuracies above, and provide the corrected text only.",
            },
        ]
        # Use deterministic settings for verification
        params = {"temperature": 0, "top_p": 0.2, "max_tokens": 800}

        # Set API base based on model type
        original_api_base = openai.api_base
        original_api_key = openai.api_key

        # Determine the correct model name
        model_name = self.model

        # Use OpenRouter for non-OpenAI models
        if "/" in self.model and not self.model.startswith("openai/"):
            openai.api_base = CONFIG.or_base
            openai.api_key = CONFIG.or_key
        else:
            # Extract just the model name for OpenAI models
            if self.model.startswith("openai/"):
                model_name = self.model.replace("openai/", "")

        # Invoke the verification
        try:
            response = openai.ChatCompletion.create(
                model=model_name, messages=critique_prompt, **params
            )
        finally:
            # Restore original settings
            openai.api_base = original_api_base
            openai.api_key = original_api_key
        return response.choices[0].message.content
