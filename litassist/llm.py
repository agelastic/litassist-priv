"""
LLM Client for LitAssist.

This module provides a unified interface for chat completions across different LLM providers,
handling parameter management and response processing.
"""

import openai
import re
from typing import List, Dict, Any, Tuple

from litassist.utils import timed, save_log
from litassist.config import CONFIG
import time
from litassist.citation_verify import (
    verify_all_citations,
    remove_citation_from_text,
    CitationVerificationError,
)


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
            "model": "anthropic/claude-3-sonnet",
            "temperature": 0,
            "top_p": 0.15,
            "force_verify": True,  # Always verify for foundational docs
        },
        # Strategy - balanced for legal analysis
        "strategy": {
            "model": "openai/o1-preview",
            "temperature": 1,  # o1 models use temperature=1
            "force_verify": True,  # Always verify for strategic guidance
        },
        # Strategy sub-type for analysis
        "strategy-analysis": {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.2,
            "top_p": 0.8,
        },
        # Brainstorm - varied temperatures for different approaches
        "brainstorm-orthodox": {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.3,
            "top_p": 0.7,
            "force_verify": True,  # Conservative analysis requires verification
        },
        "brainstorm-unorthodox": {
            "model": "x-ai/grok-3-beta",
            "temperature": 0.9,
            "top_p": 0.95,
            "force_verify": True,  # Auto-verify Grok
        },
        "brainstorm-analysis": {
            "model": "anthropic/claude-3.5-sonnet",
            "temperature": 0.2,
            "top_p": 0.8,
        },
        # Draft - balanced creativity with accuracy
        "draft": {
            "model": "openai/gpt-4o",
            "temperature": 0.5,
            "top_p": 0.8,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.1,
        },
        # Digest - mode-dependent settings
        "digest-summary": {
            "model": "anthropic/claude-3-sonnet",
            "temperature": 0,
            "top_p": 0,
        },
        "digest-issues": {
            "model": "anthropic/claude-3-sonnet",
            "temperature": 0.2,
            "top_p": 0.5,
        },
        # Lookup - if it uses LLM (not in analyzed commands but for completeness)
        "lookup": {
            "model": "anthropic/claude-3-sonnet",
            "temperature": 0.1,
            "top_p": 0.2,
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
                "model": "anthropic/claude-3-sonnet",
                "temperature": 0.3,
                "top_p": 0.7,
            }
            print(f"⚠️  No configuration found for '{config_key}', using defaults")
        else:
            config = cls.COMMAND_CONFIGS[config_key].copy()

        # Extract special flags
        force_verify = config.pop("force_verify", False)

        # Allow environment variable overrides for model selection
        env_model_key = f"LITASSIST_{command_name.upper()}_MODEL"
        if sub_type:
            env_model_key = f"LITASSIST_{command_name.upper()}_{sub_type.upper()}_MODEL"

        import os

        env_model = os.environ.get(env_model_key)
        if env_model:
            config["model"] = env_model
            print(f"📋 Using model from environment: {env_model}")

        # Apply any provided overrides
        config.update(overrides)

        # Extract model from config
        model = config.pop("model")

        # Create the LLM client with remaining config as parameters
        client = LLMClient(model, **config)

        # Set the command context
        client.command_context = config_key

        # Set force verification flag if applicable
        if force_verify:
            client._force_verify = True

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
            config_key, {"model": "anthropic/claude-3-sonnet"}
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
        # Check if this is an o1 model that doesn't support system messages
        is_o1_model = "o1" in self.model.lower()
        
        if is_o1_model:
            # o1 models don't support system messages - merge into first user message
            modified_messages = []
            system_content = "Use Australian English spellings and terminology."
            
            # Collect all system messages
            system_messages = [msg for msg in messages if msg.get("role") == "system"]
            non_system_messages = [msg for msg in messages if msg.get("role") != "system"]
            
            if system_messages:
                # Combine all system content
                system_content = "\n".join([msg.get("content", "") for msg in system_messages])
                if "Australian English" not in system_content:
                    system_content += "\nUse Australian English spellings and terminology."
            
            # Find first user message and prepend system content
            for i, msg in enumerate(non_system_messages):
                if msg.get("role") == "user":
                    enhanced_content = f"{system_content}\n\n{msg.get('content', '')}"
                    modified_messages.append({
                        "role": "user", 
                        "content": enhanced_content
                    })
                    # Add remaining messages as-is
                    modified_messages.extend(non_system_messages[i+1:])
                    break
            else:
                # No user message found, just use non-system messages
                modified_messages = non_system_messages
            
            messages = modified_messages
        else:
            # Regular models - handle system messages normally
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

        # STRICT CITATION VERIFICATION - Block output with unverified citations
        try:
            verified_content, verification_issues = self.validate_and_verify_citations(
                content, strict_mode=True
            )

            # If we got here, all citations are verified or were safely removed
            if verification_issues:
                # Log what was cleaned but still proceed
                print(f"⚠️  Citation verification: {verification_issues[0]}")
                content = verified_content

        except CitationVerificationError as e:
            # Strict mode failed - attempt retry with enhanced prompt
            print(f"🚫 {str(e)}")
            print("🔄 Retrying with enhanced citation instructions...")

            # Enhance the last user message with strict citation instructions
            enhanced_messages = messages.copy()
            if is_o1_model:
                # For o1 models, append to the enhanced user content from earlier processing
                if enhanced_messages and enhanced_messages[-1].get("role") == "user":
                    enhanced_messages[-1]["content"] += (
                        "\n\nIMPORTANT: Use only real, verifiable Australian cases that exist on AustLII. "
                        "Do not invent case names. If unsure about a citation, omit it rather than guess."
                    )
            else:
                # For regular models with system messages
                if enhanced_messages and enhanced_messages[-1].get("role") == "user":
                    enhanced_messages[-1]["content"] += (
                        "\n\nIMPORTANT: Use only real, verifiable Australian cases that exist on AustLII. "
                        "Do not invent case names. If unsure about a citation, omit it rather than guess."
                    )

            # Retry with enhanced prompt - need to set API base again
            original_api_base_retry = openai.api_base
            original_api_key_retry = openai.api_key

            # Use OpenRouter for non-OpenAI models
            if "/" in self.model and not self.model.startswith("openai/"):
                openai.api_base = CONFIG.or_base
                openai.api_key = CONFIG.or_key

            try:
                retry_response = openai.ChatCompletion.create(
                    model=model_name, messages=enhanced_messages, **params
                )
                retry_content = retry_response.choices[0].message.content
                retry_usage = getattr(retry_response, "usage", {})

                # Verify the retry
                verified_retry_content, retry_issues = (
                    self.validate_and_verify_citations(retry_content, strict_mode=True)
                )

                # If retry succeeded, use it
                content = verified_retry_content
                usage = retry_usage
                if retry_issues:
                    print(f"✅ Retry successful: {retry_issues[0]}")
                else:
                    print("✅ Retry successful: All citations verified")

            except CitationVerificationError as retry_error:
                # Both attempts failed - this is a critical error
                print(f"💥 Retry also failed: {str(retry_error)}")
                raise CitationVerificationError(
                    "CRITICAL: Multiple attempts to generate content with verified citations failed. "
                    "The AI model is consistently generating unverifiable legal citations. "
                    "Manual intervention required."
                )
            finally:
                # Restore original settings after retry
                openai.api_base = original_api_base_retry
                openai.api_key = original_api_key_retry

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
        # Note: o1 models only support temperature=1, so skip temperature override for those
        if "o1" in self.model.lower():
            params = {}  # o1 models use their default parameters
        else:
            params = {"temperature": 0, "top_p": 0.2}

        # Add model-specific token limits for verification if enabled in config
        if CONFIG.use_token_limits:
            if "google/gemini" in self.model.lower():
                params["max_tokens"] = 1024  # Concise verification for Gemini
            elif "anthropic/claude" in self.model.lower():
                params["max_tokens"] = 1536  # Claude verification
            elif "openai/gpt-4" in self.model.lower() or "openai/o1" in self.model.lower():
                params["max_tokens"] = 1024  # GPT-4/o1 verification
            elif "grok" in self.model.lower():
                params["max_tokens"] = 800  # Tighter limit for Grok
            else:
                params["max_tokens"] = 1024  # Default verification limit

        # Use the complete method which handles o1 models properly
        verification_result, usage = self.complete(critique_prompt, **params)

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
                    f"⚠️  Offline validation found {len(pattern_issues)} potential issues"
                )

        # Always do real-time AustLII verification
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
                elif "not found" in reason.lower() or "case not found" in reason.lower():
                    existence_errors.append((citation, reason))
                else:
                    verification_errors.append((citation, reason))
            
            # Only raise error if there are actual blocking issues
            blocking_errors = format_errors + existence_errors + verification_errors
            
            if blocking_errors:
                # Build categorized error message
                error_msg = "🚫 CRITICAL: Citation verification failed:\n\n"
                
                if existence_errors:
                    error_msg += "📋 CASES NOT FOUND IN DATABASE:\n"
                    for citation, reason in existence_errors:
                        error_msg += f"   • {citation}\n     → {reason}\n"
                    error_msg += "\n"
                
                if format_errors:
                    error_msg += "⚠️  CITATION FORMAT ISSUES:\n"
                    for citation, reason in format_errors:
                        error_msg += f"   • {citation}\n     → {reason}\n"
                    error_msg += "\n"
                
                if verification_errors:
                    error_msg += "🔍 VERIFICATION PROBLEMS:\n"
                    for citation, reason in verification_errors:
                        error_msg += f"   • {citation}\n     → {reason}\n"
                    error_msg += "\n"
                
                error_msg += "🛑 ACTION REQUIRED: These citations appear to be AI hallucinations.\n"
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
            enable_online: Whether to perform online AustLII verification after offline checks

        Returns:
            List of potential citation issues found
        """
        from litassist.citation_patterns import validate_citation_patterns

        return validate_citation_patterns(content, enable_online)

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
                    "content": "Check only for Australian English spelling and terminology compliance.",
                },
                {
                    "role": "user",
                    "content": primary_text
                    + "\n\nCorrect any non-Australian English spellings or terminology.",
                },
            ]
        elif level == "heavy":
            # Full legal accuracy and citation check
            critique_prompt = [
                {
                    "role": "system",
                    "content": "Australian law expert. Thoroughly verify legal accuracy, citations, precedents, and reasoning.",
                },
                {
                    "role": "user",
                    "content": primary_text
                    + "\n\nProvide comprehensive legal accuracy review: verify all citations, check legal reasoning, identify any errors in law or procedure, and ensure Australian English compliance.",
                },
            ]
        else:  # medium (default)
            # Standard verification
            return self.verify(primary_text)

        # Use same verification logic with custom prompts
        # Note: o1 models only support temperature=1, so skip temperature override for those
        if "o1" in self.model.lower():
            params = {}  # o1 models use their default parameters
        else:
            params = {"temperature": 0, "top_p": 0.2}

        if CONFIG.use_token_limits:
            if "google/gemini" in self.model.lower():
                params["max_tokens"] = 1024
            elif "anthropic/claude" in self.model.lower():
                params["max_tokens"] = 1536 if level == "heavy" else 1024
            elif "openai/gpt-4" in self.model.lower() or "openai/o1" in self.model.lower():
                params["max_tokens"] = 1024
            elif "grok" in self.model.lower():
                params["max_tokens"] = 800
            else:
                params["max_tokens"] = 1024

        # Use the complete method which handles o1 models properly
        verification_result, usage = self.complete(critique_prompt, **params)

        return verification_result
