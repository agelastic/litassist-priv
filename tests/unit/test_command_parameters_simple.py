"""
Simplified tests for command-specific parameter propagation.

Tests the LLMClientFactory directly to verify correct model configuration.
Expected model identifiers are read from configuration, not hardcoded.
"""

from unittest.mock import patch
from litassist.llm.factory import LLMClientFactory


class TestCommandParameterConfiguration:
    """Test that commands are configured with correct models and parameters."""

    @patch("litassist.config.CONFIG")
    def test_extractfacts_configuration(self, mock_config):
        """Test extractfacts command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        configs = LLMClientFactory.list_configurations()
        assert "extractfacts" in configs
        expected_model = configs["extractfacts"]["model"]

        client = LLMClientFactory.for_command("extractfacts")
        assert client.model == expected_model

    @patch("litassist.config.CONFIG")
    def test_lookup_configuration(self, mock_config):
        """Test lookup command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        configs = LLMClientFactory.list_configurations()
        assert "lookup" in configs
        config = configs["lookup"]
        assert "enforce_citations" in config

        client = LLMClientFactory.for_command("lookup")
        assert client.model == config["model"]
        assert hasattr(client, "_enforce_citations")

    @patch("litassist.config.CONFIG")
    def test_strategy_configuration(self, mock_config):
        """Test strategy command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        configs = LLMClientFactory.list_configurations()
        assert "strategy" in configs
        config = configs["strategy"]
        assert config["thinking_effort"] == "max"
        assert "enforce_citations" in config

        client = LLMClientFactory.for_command("strategy")
        assert client.model == config["model"]
        assert hasattr(client, "_enforce_citations")
        assert client.default_params.get("thinking_effort") == "max"

    @patch("litassist.config.CONFIG")
    def test_draft_configuration(self, mock_config):
        """Test draft command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        configs = LLMClientFactory.list_configurations()
        assert "draft" in configs
        config = configs["draft"]
        assert config["thinking_effort"] == "high"

        client = LLMClientFactory.for_command("draft")
        assert client.model == config["model"]

    @patch("litassist.config.CONFIG")
    def test_parameter_filtering_for_reasoning_family(self, mock_config):
        """Test that o-series reasoning models filter out unsupported sampling parameters."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        from litassist.llm.parameter_handler import get_model_family, get_model_parameters

        client = LLMClientFactory.for_command("draft", temperature=0.9, top_p=0.95)

        assert client.default_params.get("temperature") == 0.9
        assert client.default_params.get("top_p") == 0.95
        assert client.default_params.get("thinking_effort") == "high"

        # Only meaningful when draft is configured with an openai_reasoning model
        if get_model_family(client.model) == "openai_reasoning":
            filtered = get_model_parameters(client.model, client.default_params)
            assert "temperature" not in filtered
            assert "top_p" not in filtered
            assert "reasoning" in filtered
            assert filtered["reasoning"] == {"effort": "high"}

    @patch("litassist.config.CONFIG")
    def test_default_command_configuration(self, mock_config):
        """Test commands without specific config raise KeyError (fail-fast)."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        import pytest

        with pytest.raises(KeyError) as exc_info:
            LLMClientFactory.for_command("unknown_command")
        assert "No model configuration found" in str(exc_info.value)
        assert "unknown_command" in str(exc_info.value)

    @patch("litassist.config.CONFIG")
    def test_digest_requires_subtype(self, mock_config):
        """Test digest command requires sub-type (summary/issues) - NO FALLBACK."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        import pytest

        with pytest.raises(KeyError) as exc_info:
            LLMClientFactory.for_command("digest")
        assert "No model configuration found" in str(exc_info.value)
        assert "digest" in str(exc_info.value)

        configs = LLMClientFactory.list_configurations()
        client_summary = LLMClientFactory.for_command("digest", "summary")
        assert client_summary.model == configs["digest-summary"]["model"]

        client_issues = LLMClientFactory.for_command("digest", "issues")
        assert client_issues.model == configs["digest-issues"]["model"]
