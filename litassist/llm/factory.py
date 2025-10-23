"""
Factory for creating LLM client instances with command-specific configurations.

This module contains the LLMClientFactory class that centralizes all model
and parameter configurations for each command.
"""

import os
import logging
from typing import Dict, Any

from litassist.utils.formatting import info_message

# Import LLMClient - must be imported after the class is defined in client.py
# This creates a one-way dependency: factory -> client
from .client import LLMClient

logger = logging.getLogger(__name__)


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
        # UPGRADED: Oct 2025 - Sonnet 4 -> Sonnet 4.5 for better legal domain knowledge
        "extractfacts": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-sonnet-4",
            "temperature": 0,
            "top_p": 0.15,
            "thinking_effort": "high",  # Critical foundational command needs thorough thinking
            "enforce_citations": True,  # Retry on citation errors for foundational docs
            "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
        },
        # Strategy - enhanced multi-step legal reasoning
        # UPGRADED: Oct 2025 - Opus 4.1 -> Sonnet 4.5 (state-of-the-art for litigation, 80% cost reduction)
        "strategy": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-opus-4.1",
            "temperature": 0.2,  # Controlled creativity for strategic thinking
            "top_p": 0.8,  # Focused but not overly restrictive
            "thinking_effort": "max",  # Universal parameter, translates to reasoning object
            "verbosity": "medium",  # Balanced depth in strategic analysis
            "enforce_citations": False,  # Don't retry on citation errors for strategy
        },
        # Strategy sub-type for analysis
        "strategy-analysis": {
            "model": "openai/o3-pro",
            # Note: o3-pro ignores temperature and top_p parameters
            "thinking_effort": "max",  # Universal parameter, translates to reasoning_effort
            "disable_tools": True,  # o3-pro doesn't support tool calling
        },
        # Brainstorm - varied temperatures for different approaches
        # UPGRADED: Oct 2025 - Opus 4.1 -> Sonnet 4.5 (better legal domain knowledge, cost-effective)
        "brainstorm-orthodox": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-opus-4.1",
            "temperature": 0.3,
            "top_p": 0.7,
            "thinking_effort": "medium",  # Moderate thinking for balanced analysis
            "enforce_citations": False,  # Don't retry on citation errors for brainstorm
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
            "enforce_citations": False,  # Don't retry on citation errors for creative outputs
        },
        "brainstorm-analysis": {
            "model": "openai/o3-pro",
            "temperature": 0.2,
            "top_p": 0.8,
            "thinking_effort": "high",  # Universal parameter, translates to reasoning_effort
            "disable_tools": True,  # o3-pro doesn't support tool calling
        },
        # Draft - superior technical writing (o3 model with very limited parameter support)
        "draft": {
            "model": "openai/o3-pro",
            "thinking_effort": "high",  # Universal parameter
            "verbosity": "high",  # Comprehensive legal drafting
            "disable_tools": True,  # o3-pro doesn't support tool calling
        },
        # Digest - mode-dependent settings
        # UPGRADED: Oct 2025 - Sonnet 4 -> Sonnet 4.5 for better reasoning
        "digest-summary": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-sonnet-4",
            "temperature": 0.2,
            "top_p": 0.3,  # Fixed: was 0, too restrictive
            "thinking_effort": "medium",  # Simple summarization task
            "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
        },
        # UPGRADED: Oct 2025 - Opus 4.1 -> Sonnet 4.5 (state-of-the-art for legal analysis)
        "digest-issues": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-opus-4.1",
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
            "enforce_citations": False,  # Don't enforce strict citation retries
        },
        # Verification - automatic verification for high-risk commands
        # UPGRADED: Oct 2025 - Opus 4.1 -> GPT-5 base (1.4% hallucination, fast verification)
        "verification": {
            "model": "openai/gpt-5",
            # OLD: "model": "anthropic/claude-opus-4.1",
            "temperature": 0.2,
            "top_p": 0.3,
            "thinking_effort": "high",
            "enforce_citations": False,  # Don't double-enforce since this IS verification
        },
        # UPGRADED: Oct 2025 - Sonnet 4 -> Sonnet 4.5 for better legal domain knowledge
        "verification-light": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-sonnet-4",
            "temperature": 0.2,  # Optimal for factual tasks per hallucination report
            "top_p": 0.2,  # Focused beam for consistency
            "thinking_effort": "medium",  # Just spelling/terminology checks
            "enforce_citations": False,  # Avoid loops
            "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
        },
        # UPGRADED: Oct 2025 - GPT-5 -> GPT-5 Pro (<1% hallucination, 400K context, mandatory reasoning)
        "verification-heavy": {
            "model": "openai/gpt-5-pro",
            # OLD: "model": "openai/gpt-5",
            "temperature": 0.2,  # Optimal per hallucination report
            "top_p": 0.3,  # Slightly wider beam for comprehensive checking
            "thinking_effort": "max",  # Mandatory deep reasoning for critical verification
            "enforce_citations": False,  # Avoid loops
        },
        # Verify sub-commands with specific model assignments
        # UPGRADED: Oct 2025 - o3-pro -> Sonnet 4.5 (state-of-the-art for legal reasoning extraction)
        "verify-reasoning": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "openai/o3-pro",
            "temperature": 0.2,
            "top_p": 0.3,
            "thinking_effort": "high",  # Extended thinking for complex reasoning trace extraction
            "enforce_citations": False,
            "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
        },
        # UPGRADED: Oct 2025 - Opus 4.1 -> GPT-5 Pro (<1% hallucination for critical soundness checking)
        "verify-soundness": {
            "model": "openai/gpt-5-pro",
            # OLD: "model": "anthropic/claude-opus-4.1",
            "temperature": 0.2,
            "top_p": 0.3,
            "thinking_effort": "max",  # Mandatory deep reasoning for soundness analysis
            "verbosity": "high",  # Detailed soundness explanations
            "enforce_citations": False,
        },
        # Counsel's Notes - strategic analysis from advocate's perspective
        "counselnotes": {
            "model": "openai/o3-pro",
            "temperature": 0.3,
            "top_p": 0.7,
            "thinking_effort": "high",  # Universal parameter, translates to reasoning_effort
            "enforce_citations": False,  # Don't retry on citation errors for counsel's notes
            "disable_tools": True,  # o3-pro doesn't support tool calling
        },
        # Barrister's brief - comprehensive document generation
        "barbrief": {
            "model": "openai/o3-pro",
            # o3-pro for comprehensive analysis and superior drafting
            "thinking_effort": "high",  # Universal parameter, translates to reasoning object
            "verbosity": "high",  # Detailed comprehensive briefs
            "disable_tools": True,  # o3-pro doesn't support tool calling
        },
        # Caseplan - LLM-driven workflow planning
        # UPGRADED: Oct 2025 - Sonnet 4 -> Sonnet 4.5 for better reasoning
        "caseplan": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-sonnet-4",
            "temperature": 0.5,
            "enforce_citations": False,
            "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
        },
        # Caseplan assessment - budget recommendation (Sonnet)
        # UPGRADED: Oct 2025 - Sonnet 4 -> Sonnet 4.5 for better reasoning
        "caseplan-assessment": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-sonnet-4",
            "temperature": 0.5,
            "enforce_citations": False,
            "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
        },
        # Chain of Verification - fast, efficient question generation
        # UPGRADED: Oct 2025 - Sonnet 4 -> Sonnet 4.5 for better reasoning
        "cove": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-sonnet-4",
            "temperature": 0.2,
            "top_p": 0.8,
            "thinking_effort": "medium",  # General CoVe coordination
            "enforce_citations": False,  # Avoid recursive verification
            "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
        },
        # CoVe sub-stages with separate model control
        # UPGRADED: Oct 2025 - Sonnet 4 -> Sonnet 4.5 for better question generation
        "cove-questions": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-sonnet-4",
            "temperature": 0.2,
            "top_p": 0.8,
            "thinking_effort": "low",  # Fast question generation, minimal thinking needed
            "enforce_citations": False,
            "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
        },
        # KEPT: Oct 2025 - GPT-5 base is optimal for fast, accurate answers (1.4% hallucination)
        "cove-answers": {
            "model": "openai/gpt-5",  # GPT-5 base for <1.4% hallucination rate
            "temperature": 0.2,
            "top_p": 0.3,
            "thinking_effort": "high",  # Not max - save Pro for final verification
            "enforce_citations": False,
        },
        # UPGRADED: Oct 2025 - Sonnet 4 -> Sonnet 4.5 for better inconsistency detection
        "cove-verify": {
            "model": "anthropic/claude-sonnet-4.5",
            # OLD: "model": "anthropic/claude-sonnet-4",
            "temperature": 0.2,
            "top_p": 0.3,
            "thinking_effort": "high",  # Critical inconsistency detection needs careful analysis
            "enforce_citations": False,
            "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
        },
        # UPGRADED: Oct 2025 - GPT-5 -> GPT-5 Pro for critical final output (<1% hallucination)
        "cove-final": {
            "model": "openai/gpt-5-pro",
            # OLD: "model": "openai/gpt-5",
            "temperature": 0.2,
            "top_p": 0.4,
            "thinking_effort": "max",  # Mandatory deep reasoning for final verification
            "enforce_citations": False,
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
            # UPGRADED: Oct 2025 - Default to Sonnet 4.5
            config = {
                "model": "anthropic/claude-sonnet-4.5",
                # OLD: "model": "anthropic/claude-sonnet-4",
                "temperature": 0.3,
                "top_p": 0.7,
                "disable_tools": True,  # Check if Sonnet 4.5 still has tool calling issues
            }
            # Use default configuration for commands without specific config
            # This is expected behavior for many commands
        else:
            config = cls.COMMAND_CONFIGS[config_key].copy()

        # Extract special flags
        enforce_citations = config.pop("enforce_citations", False)
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

        # Set citation enforcement flag - explicitly set both True and False
        client._enforce_citations = enforce_citations
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
            config_key, {"model": "anthropic/claude-sonnet-4.5", "disable_tools": True}
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


