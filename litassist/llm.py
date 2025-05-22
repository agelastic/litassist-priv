"""
LLM Client for LitAssist.

This module provides a unified interface for chat completions across different LLM providers,
handling parameter management and response processing.
"""

import openai
import re
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
        self.command_context = None  # Track which command is using this client

        # Set model-specific token limits if enabled in config and not explicitly specified
        if CONFIG.use_token_limits and "max_tokens" not in default_params:
            # These limits are carefully chosen to balance comprehensive responses with quality
            if "google/gemini" in model.lower():
                default_params["max_tokens"] = (
                    2048  # Gemini - reliable up to this length
                )
            elif "anthropic/claude" in model.lower():
                default_params["max_tokens"] = (
                    4096  # Claude - coherent for longer outputs
                )
            elif "openai/gpt-4" in model.lower():
                default_params["max_tokens"] = (
                    3072  # GPT-4/o - balanced limit for precision
                )
            elif "grok" in model.lower():
                default_params["max_tokens"] = (
                    1536  # Grok - more prone to hallucination
                )
            else:
                default_params["max_tokens"] = 2048  # Default safe limit

        self.default_params = default_params

    @timed
    def complete(
        self, messages: List[Dict[str, str]], **overrides
    ) -> Tuple[str, Dict[str, Any]]:
        # Enforce Australian English in system prompts if not already specified
        has_system_message = any(msg.get("role") == "system" for msg in messages)
        if has_system_message:
            for msg in messages:
                if msg.get("role") == "system" and "Australian English" not in msg.get(
                    "content", ""
                ):
                    msg[
                        "content"
                    ] += "\nUse Australian English spellings and terminology."
        else:
            # Add system message if none exists
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": "Use Australian English spellings and terminology.",
                },
            )
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
            {
                "role": "system",
                "content": "Australian law only. Use Australian English spellings and terminology (e.g., 'judgement' not 'judgment', 'defence' not 'defense').",
            },
            {
                "role": "user",
                "content": primary_text
                + "\n\nIdentify and correct any legal inaccuracies above, and provide the corrected text only. Ensure all spellings follow Australian English conventions.",
            },
        ]
        # Use deterministic settings for verification with appropriate token limits
        params = {"temperature": 0, "top_p": 0.2}

        # Add model-specific token limits for verification if enabled in config
        if CONFIG.use_token_limits and "max_tokens" not in params:
            if "google/gemini" in self.model.lower():
                params["max_tokens"] = 1024  # Concise verification for Gemini
            elif "anthropic/claude" in self.model.lower():
                params["max_tokens"] = 1536  # Claude verification
            elif "openai/gpt-4" in self.model.lower():
                params["max_tokens"] = 1024  # GPT-4 verification
            elif "grok" in self.model.lower():
                params["max_tokens"] = 800  # Tighter limit for Grok
            else:
                params["max_tokens"] = 1024  # Default verification limit

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

    def should_auto_verify(self, content: str, command: str = None) -> bool:
        """
        Determine if content should be automatically verified based on risk factors.
        
        Args:
            content: The generated content to analyze
            command: The command that generated this content (optional)
            
        Returns:
            True if auto-verification should be triggered
        """
        # Always verify critical foundation commands
        if command in ["extractfacts", "strategy"]:
            return True
            
        # Auto-verify Grok outputs (prone to hallucination)
        if "grok" in self.model.lower():
            return True
            
        # Auto-verify when output contains high-risk content
        risk_patterns = [
            r'\[\d{4}\]\s+\w+\s+\d+',  # Case citations
            r'\d+%',  # Percentage claims
            r'"must"|"cannot"|"will"',  # Strong legal conclusions
            r'section\s+\d+',  # Statutory references
            r'rule\s+\d+',  # Court rules
            r'paragraph\s+\d+',  # Paragraph references
        ]
        
        for pattern in risk_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
                
        return False
        
    def validate_citations(self, content: str) -> List[str]:
        """
        Lightweight validation of Australian legal citations.
        
        Args:
            content: Text content to validate
            
        Returns:
            List of potential citation issues found
        """
        issues = []
        
        # Find potential case citations - check both formal citations and case names
        citation_patterns = [
            r'\[\d{4}\]\s+[A-Z]+\s+\d+',  # [2020] HCA 5 format
            r'\(\d{4}\)\s+\d+\s+CLR\s+\d+',  # (2010) 241 CLR 118 format
        ]
        
        # Check case name patterns separately
        case_name_pattern = r'[A-Za-z]+\s+v\s+[A-Za-z]+'
        case_names = re.findall(case_name_pattern, content)
        
        # Check for fabricated case names
        fabricated_names = ['smith.*v.*jones', 'doe.*v.*roe', 'abc.*v.*xyz']
        for case_name in case_names:
            for name_pattern in fabricated_names:
                if re.search(name_pattern, case_name, re.IGNORECASE):
                    issues.append(f"Potentially fabricated case name: {case_name}")
        
        # Check formal citations for suspicious years
        for pattern in citation_patterns:
            citations = re.findall(pattern, content)
            for citation in citations:
                # Check for suspicious years
                year_match = re.search(r'\d{4}', citation)
                if year_match:
                    year = int(year_match.group())
                    if year < 1900 or year > 2025:
                        issues.append(f"Suspicious year in citation: {citation}")
                        
        return issues
        
    def verify_with_level(self, primary_text: str, level: str = "medium") -> str:
        """
        Run verification with different depth levels.
        
        Args:
            primary_text: Text to verify
            level: Verification depth - "light", "medium", or "heavy"
            
        Returns:
            Verification feedback
        """
        if level == "light":
            # Just check Australian English compliance
            critique_prompt = [
                {
                    "role": "system",
                    "content": "Check only for Australian English spelling and terminology compliance."
                },
                {
                    "role": "user", 
                    "content": primary_text + "\n\nCorrect any non-Australian English spellings or terminology."
                }
            ]
        elif level == "heavy":
            # Full legal accuracy and citation check
            critique_prompt = [
                {
                    "role": "system",
                    "content": "Australian law expert. Thoroughly verify legal accuracy, citations, precedents, and reasoning."
                },
                {
                    "role": "user",
                    "content": primary_text + "\n\nProvide comprehensive legal accuracy review: verify all citations, check legal reasoning, identify any errors in law or procedure, and ensure Australian English compliance."
                }
            ]
        else:  # medium (default)
            # Standard verification
            return self.verify(primary_text)
            
        # Use same verification logic with custom prompts
        params = {"temperature": 0, "top_p": 0.2}
        
        if CONFIG.use_token_limits:
            if "google/gemini" in self.model.lower():
                params["max_tokens"] = 1024
            elif "anthropic/claude" in self.model.lower():
                params["max_tokens"] = 1536 if level == "heavy" else 1024
            elif "openai/gpt-4" in self.model.lower():
                params["max_tokens"] = 1024
            elif "grok" in self.model.lower():
                params["max_tokens"] = 800
            else:
                params["max_tokens"] = 1024
                
        # Execute verification
        original_api_base = openai.api_base
        original_api_key = openai.api_key
        model_name = self.model
        
        if "/" in self.model and not self.model.startswith("openai/"):
            openai.api_base = CONFIG.or_base
            openai.api_key = CONFIG.or_key
        else:
            if self.model.startswith("openai/"):
                model_name = self.model.replace("openai/", "")
                
        try:
            response = openai.ChatCompletion.create(
                model=model_name, messages=critique_prompt, **params
            )
        finally:
            openai.api_base = original_api_base
            openai.api_key = original_api_key
            
        return response.choices[0].message.content
