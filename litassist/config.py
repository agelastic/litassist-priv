"""
Configuration management for LitAssist.

This module handles loading, validation, and access to configuration values
required for LitAssist's operation. All LLM calls route through OpenRouter API.
"""

import os
import yaml
from typing import Dict, Any


class ConfigError(Exception):
    """Raised when configuration loading or validation fails."""

    pass


class Config:
    """Configuration manager for LitAssist."""

    def __init__(self, config_path=None):
        """
        Initialize configuration from a YAML file.

        Args:
            config_path: Path to the configuration file.

        Raises:
            ConfigError: If the configuration file is missing or has invalid entries.
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
        Find config.yaml - ONLY uses {config_dir}/config.yaml.

        This enforces a single global configuration to prevent secret duplication.

        Returns:
            Path to the global configuration file.

        Raises:
            ConfigError: If no configuration file is found.
        """
        from pathlib import Path

        config_dir = Path.home() / ".config" / "litassist"
        config_path = config_dir / "config.yaml"

        # ONLY check {config_dir}/config.yaml - no other locations
        if config_path.exists():
            return str(config_path)

        # If no config found, provide helpful message
        package_dir = Path(__file__).parent.parent
        template_path = package_dir / "config.yaml.template"

        message = (
            "Error: No config.yaml found.\n"
            f"To set up LitAssist:\n  mkdir -p {config_dir}\n  cp {template_path} {config_path}\n  # Edit {config_path} with your API keys\n\n"
            f"Configuration file MUST be at: {config_dir}/config.yaml\n"
            "This is the ONLY location that will be checked."
        )
        if template_path.exists():
            raise ConfigError(message)
        else:
            raise ConfigError(
                "Error: config.yaml not found.\n"
                f"Configuration file MUST be at: {config_dir}/config.yaml"
            )

    def _load_config(self) -> Dict[str, Any]:
        """
        Load the configuration from the YAML file.

        Returns:
            Dictionary containing the configuration values.

        Raises:
            ConfigError: If the configuration file is missing or invalid.
        """
        if not os.path.exists(self.config_path):
            raise ConfigError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path) as f:
            try:
                config = yaml.safe_load(f)
                # Handle empty or all-commented YAML files
                if config is None:
                    config = {}
                return config
            except yaml.YAMLError as e:
                raise ConfigError(f"Invalid YAML in {self.config_path}: {e}")

    def _validate_config(self):
        """
        Validate all required configuration values.

        Raises:
            ConfigError: If any required configuration is missing or invalid.
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
            self.cse_id_comprehensive = self.cfg["google_cse"].get(
                "cse_id_comprehensive", None
            )
            self.cse_id_austlii = self.cfg["google_cse"].get("cse_id_austlii", None)
            
            # Optional Jina Reader API key for higher rate limits
            jina_config = self.cfg.get("jina_reader", {})
            self.jina_api_key = jina_config.get("api_key", "") if jina_config else ""
            
            self.pc_key = self.cfg["pinecone"]["api_key"]
            self.pc_env = self.cfg["pinecone"]["environment"]
            self.pc_index = self.cfg["pinecone"]["index_name"]

            # Extract optional LLM settings with defaults
            llm_config = self.cfg.get("llm", {})
            if llm_config is None:
                llm_config = {}
            self.use_token_limits = llm_config.get("use_token_limits", True)
            self.token_limit = llm_config.get("token_limit", 16384)

            # Extract optional general settings with defaults
            general_config = self.cfg.get("general", {})
            if general_config is None:
                general_config = {}
            self.heartbeat_interval = general_config.get("heartbeat_interval", 20)
            self.max_chars = general_config.get("max_chars", 200000)
            self.rag_max_chars = general_config.get("rag_max_chars", 8000)
            self.log_format = general_config.get("log_format", "json")

            # Extract citation validation settings with defaults
            citation_config = self.cfg.get("citation_validation", {})
            if citation_config is None:
                citation_config = {}
            self.offline_validation = citation_config.get("offline_validation", False)

            # Web scraping settings with good defaults
            web_scraping_config = self.cfg.get("web_scraping", {})
            self.fetch_timeout = web_scraping_config.get("fetch_timeout", 10)
            self.max_fetch_time = web_scraping_config.get("max_fetch_time", 300)
            self.selenium_enabled = web_scraping_config.get("selenium_enabled", True)
            self.selenium_timeout_multiplier = web_scraping_config.get(
                "selenium_timeout_multiplier", 2
            )

        # Jade API key is no longer used - functionality now uses public endpoint

        except KeyError as e:
            raise ConfigError(f"config.yaml missing key {e}")

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
                raise ConfigError(f"config '{key}' must be a non-empty string")

    def _setup_api_keys(self):
        """Set API keys for external services."""
        # OpenAI SDK v1.0+ no longer uses global api_key
        # Keys are now passed when creating client instances
        pass

    def using_placeholders(self) -> Dict[str, bool]:
        """
        Check which credential sets are using placeholder values.

        Returns:
            Dictionary of service names mapped to boolean indicating placeholder usage.
        """
        return {
            "openai": "YOUR_" in self.oa_key,
            "openrouter": "YOUR_" in self.or_key,
            "pinecone": "YOUR_PINECONE" in self.pc_key
            or "YOUR_PINECONE" in self.pc_env,
            "google_cse": "YOUR_GOOGLE" in self.g_key or "YOUR_GOOGLE" in self.cse_id,
            "jade": False,  # Jade API is no longer used directly - switched to public endpoint
        }


CONFIG = None


def load_config(config_path: str | None = None) -> "Config":
    """Load the global configuration instance if not already loaded."""
    global CONFIG
    if CONFIG is None:
        CONFIG = Config(config_path)
    return CONFIG


def get_config() -> "Config":
    """Get the global configuration instance, loading it if necessary.

    This should be used instead of directly accessing CONFIG to ensure
    lazy loading and better testability.
    """
    global CONFIG
    if CONFIG is None:
        try:
            CONFIG = Config()
        except ConfigError as e:
            import sys

            print(f"WARNING: Could not load configuration. {e}", file=sys.stderr)
            raise
    return CONFIG


# DO NOT automatically load configuration on module import - use get_config() instead
# This prevents CONFIG from being loaded during test collection when modules are imported
