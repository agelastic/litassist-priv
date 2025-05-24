"""
Configuration management for LitAssist.

This module handles loading, validation, and access to configuration values
required for LitAssist's operation.
"""

import os
import sys
import yaml
from typing import Dict, Any


class Config:
    """Configuration manager for LitAssist."""

    def __init__(self, config_path=None):
        """
        Initialize configuration from a YAML file.

        Args:
            config_path: Path to the configuration file.

        Raises:
            SystemExit: If the configuration file is missing or has invalid entries.
        """
        # Allow override from environment for testing
        if config_path is None:
            config_path = os.environ.get("LITASSIST_CONFIG")
            if config_path is None:
                config_path = self._find_config_file()
        self.config_path = config_path
        self.cfg = self._load_config()
        self._validate_config()
        self._setup_api_keys()

    def _find_config_file(self) -> str:
        """
        Find config.yaml in the package directory (global configuration only).

        This enforces a single global configuration to prevent secret duplication.

        Returns:
            Path to the global configuration file.

        Raises:
            SystemExit: If no configuration file is found.
        """
        from pathlib import Path

        # For development installs (-e flag), use the actual source directory
        package_dir = Path(__file__).parent.parent

        # Check if this is an editable install by looking for config.yaml in source
        if (package_dir / "config.yaml").exists():
            return str(package_dir / "config.yaml")

        # For pipx/pip installs, check common global locations
        possible_locations = [
            Path.home() / ".config" / "litassist" / "config.yaml",  # XDG config
            Path.home() / ".litassist" / "config.yaml",  # Home directory
            Path("/etc/litassist/config.yaml"),  # System-wide
        ]

        for config_path in possible_locations:
            if config_path.exists():
                return str(config_path)

        # If no config found, provide helpful message
        config_dir = Path.home() / ".config" / "litassist"
        config_path = config_dir / "config.yaml"
        template_path = package_dir / "config.yaml.template"

        if template_path.exists():
            sys.exit(
                f"Error: No config.yaml found.\n"
                f"To set up LitAssist:\n"
                f"  mkdir -p {config_dir}\n"
                f"  cp {template_path} {config_path}\n"
                f"  # Edit {config_path} with your API keys\n"
                f"\nLitAssist will look for config.yaml in:\n"
                f"  1. {config_dir}/config.yaml (recommended)\n"
                f"  2. ~/.litassist/config.yaml\n"
                f"  3. /etc/litassist/config.yaml"
            )
        else:
            sys.exit(
                f"Error: config.yaml not found.\n"
                f"Create a config.yaml file with your API keys in one of:\n"
                f"  1. {config_dir}/config.yaml (recommended)\n"
                f"  2. ~/.litassist/config.yaml\n"
                f"  3. /etc/litassist/config.yaml"
            )

    def _load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the YAML file.

        Returns:
            Dictionary containing the configuration values.

        Raises:
            SystemExit: If the configuration file is missing or invalid.
        """
        if not os.path.exists(self.config_path):
            sys.exit(f"Error: Configuration file not found: {self.config_path}")

        with open(self.config_path) as f:
            try:
                return yaml.safe_load(f)
            except yaml.YAMLError as e:
                sys.exit(f"Error: Invalid YAML in {self.config_path}: {e}")

    def _validate_config(self):
        """
        Validate all required configuration values.

        Raises:
            SystemExit: If any required configuration is missing or invalid.
        """
        # Extract required values with defaults
        try:
            self.or_key = self.cfg["openrouter"]["api_key"]
            self.or_base = self.cfg["openrouter"].get(
                "api_base", "https://openrouter.ai/api/v1"
            )
            self.oa_key = self.cfg["openai"]["api_key"]
            self.emb_model = self.cfg["openai"].get(
                "embedding_model", "text-embedding-3-small"
            )
            self.g_key = self.cfg["google_cse"]["api_key"]
            self.cse_id = self.cfg["google_cse"]["cse_id"]
            self.pc_key = self.cfg["pinecone"]["api_key"]
            self.pc_env = self.cfg["pinecone"]["environment"]
            self.pc_index = self.cfg["pinecone"]["index_name"]

            # Extract optional LLM settings with defaults
            self.use_token_limits = self.cfg.get("llm", {}).get(
                "use_token_limits", False
            )

            # Extract optional general settings with defaults
            self.heartbeat_interval = self.cfg.get("general", {}).get(
                "heartbeat_interval", 10
            )
            self.max_chars = self.cfg.get("general", {}).get("max_chars", 20000)
            self.rag_max_chars = self.cfg.get("general", {}).get("rag_max_chars", 8000)

        # Jade API key is no longer used - functionality now uses public endpoint

        except KeyError as e:
            sys.exit(f"Error: config.yaml missing key {e}")

        # Validate required entries are non-empty strings
        required_configs = {
            "openrouter.api_key": self.or_key,
            "openai.api_key": self.oa_key,
            "openai.embedding_model": self.emb_model,
            "google_cse.api_key": self.g_key,
            "google_cse.cse_id": self.cse_id,
            "pinecone.api_key": self.pc_key,
            "pinecone.environment": self.pc_env,
            "pinecone.index_name": self.pc_index,
        }
        for key, val in required_configs.items():
            if not isinstance(val, str) or not val.strip():
                sys.exit(f"Error: config '{key}' must be a non-empty string")

    def _setup_api_keys(self):
        """Set API keys for external services."""
        import openai

        openai.api_key = self.oa_key
        # Don't set api_base unless we're using OpenRouter specifically
        # openai.api_base = self.or_base

    def get_jade_api_key(self) -> str:
        """
        Get the Jade API key if configured.

        Note: This method is maintained for backward compatibility.
        The Jade API is no longer used directly - functionality now uses public endpoint.

        Returns:
            Empty string as the API is no longer used.
        """
        return ""

    def using_placeholders(self) -> Dict[str, bool]:
        """
        Check which credential sets are using placeholder values.

        Returns:
            Dictionary of service names mapped to boolean indicating placeholder usage.
        """
        return {
            "openai": "YOUR_" in self.oa_key or "YOUR_" in self.or_key,
            "pinecone": "YOUR_PINECONE" in self.pc_key
            or "YOUR_PINECONE" in self.pc_env,
            "google_cse": "YOUR_GOOGLE" in self.g_key or "YOUR_GOOGLE" in self.cse_id,
            "jade": False,  # Jade API is no longer used directly - switched to public endpoint
        }


# Create default instance when module is imported
try:
    CONFIG = Config()
except SystemExit:
    # During testing, CONFIG might be mocked
    if os.environ.get("PYTEST_CURRENT_TEST"):
        CONFIG = None
    else:
        raise
