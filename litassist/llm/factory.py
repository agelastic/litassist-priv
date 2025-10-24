"""
Factory for creating LLM client instances with command-specific configurations.

This module contains the LLMClientFactory class that centralizes all model
and parameter configurations for each command.
"""

import os
import logging
import yaml
from pathlib import Path
from typing import Dict, Any

from litassist.utils.formatting import info_message

# Import LLMClient - must be imported after the class is defined in client.py
# This creates a one-way dependency: factory -> client
from .client import LLMClient

logger = logging.getLogger(__name__)


def _load_model_configs() -> Dict[str, Any]:
    """
    Load model configurations from YAML.

    Raises:
        FileNotFoundError: If model_configs.yaml doesn't exist
        yaml.YAMLError: If YAML syntax is invalid
        ValueError: If YAML content is invalid
    """
    config_path = Path(__file__).parent / "model_configs.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Model configuration file not found: {config_path}\n"
            "This file is required for LLM client initialization."
        )

    with open(config_path, 'r', encoding='utf-8') as f:
        configs = yaml.safe_load(f)

    if not configs or not isinstance(configs, dict):
        raise ValueError(
            f"Invalid model configuration in {config_path}: "
            "Expected non-empty dictionary"
        )

    return configs


# Lazy load with caching
_MODEL_CONFIGS_CACHE = None


def _get_model_configs() -> Dict[str, Any]:
    """Get model configurations with caching."""
    global _MODEL_CONFIGS_CACHE
    if _MODEL_CONFIGS_CACHE is None:
        _MODEL_CONFIGS_CACHE = _load_model_configs()
    return _MODEL_CONFIGS_CACHE


class LLMClientFactory:
    """
    Factory class for creating LLMClient instances with command-specific configurations.

    All models use "provider/model" format and route through OpenRouter.

    This centralizes all model and parameter configurations for each command,
    eliminating duplication and providing a single source of truth.

    Configurations are loaded from model_configs.yaml - NO FALLBACKS.
    Missing configurations raise KeyError.
    """

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

        # Load configurations from YAML - FAIL FAST on missing config
        configs = _get_model_configs()

        if config_key not in configs:
            available = ", ".join(sorted(configs.keys()))
            raise KeyError(
                f"No model configuration found for command '{config_key}'.\n"
                f"Available configurations: {available}\n"
                f"Add configuration to litassist/llm/model_configs.yaml"
            )

        config = configs[config_key].copy()

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
        configs = _get_model_configs()

        if config_key not in configs:
            available = ", ".join(sorted(configs.keys()))
            raise KeyError(
                f"No model configuration found for command '{config_key}'.\n"
                f"Available configurations: {available}"
            )

        return configs[config_key]["model"]

    @classmethod
    def list_configurations(cls) -> Dict[str, Dict[str, Any]]:
        """
        List all available command configurations.

        Returns:
            Dictionary of all command configurations
        """
        return _get_model_configs().copy()


