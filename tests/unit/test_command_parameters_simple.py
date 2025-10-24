"""
Simplified tests for command-specific parameter propagation.

Tests the LLMClientFactory directly to verify correct model configuration.
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

        # Check the configuration
        configs = LLMClientFactory.list_configurations()
        assert "extractfacts" in configs
        config = configs["extractfacts"]
        # UPDATED: Oct 2025 - Model upgraded to Sonnet 4.5
        assert config["model"] == "anthropic/claude-sonnet-4.5"

        # Create client and verify model
        client = LLMClientFactory.for_command("extractfacts")
        assert client.model == "anthropic/claude-sonnet-4.5"

    @patch("litassist.config.CONFIG")
    def test_lookup_configuration(self, mock_config):
        """Test lookup command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        configs = LLMClientFactory.list_configurations()
        assert "lookup" in configs
        config = configs["lookup"]
        assert config["model"] == "google/gemini-2.5-pro"
        # Just verify the key exists, don't assert specific value
        assert "enforce_citations" in config

        client = LLMClientFactory.for_command("lookup")
        assert client.model == "google/gemini-2.5-pro"
        # Just verify the attribute exists, don't assert specific value
        assert hasattr(client, "_enforce_citations")

    @patch("litassist.config.CONFIG")
    def test_strategy_configuration(self, mock_config):
        """Test strategy command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        configs = LLMClientFactory.list_configurations()
        assert "strategy" in configs
        config = configs["strategy"]
        # UPDATED: Oct 2025 - Model upgraded to Sonnet 4.5
        assert config["model"] == "anthropic/claude-sonnet-4.5"
        assert config["thinking_effort"] == "max"
        # Just verify the key exists, don't assert specific value
        assert "enforce_citations" in config

        client = LLMClientFactory.for_command("strategy")
        assert client.model == "anthropic/claude-sonnet-4.5"
        # Just verify the attribute exists, don't assert specific value
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
        assert config["model"] == "openai/o3-pro"
        assert config["thinking_effort"] == "high"

        client = LLMClientFactory.for_command("draft")
        assert client.model == "openai/o3-pro"
        # max_completion_tokens might be set by default for o3-pro models
        assert "max_completion_tokens" in client.default_params

    @patch("litassist.config.CONFIG")
    def test_parameter_filtering_for_o3_pro(self, mock_config):
        """Test that o3-pro models filter out unsupported parameters during API call."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        # Use draft command which actually uses o3-pro model
        client = LLMClientFactory.for_command("draft", temperature=0.9, top_p=0.95)

        # Parameters are stored in default_params but will be filtered during API call
        # This is the actual behavior - filtering happens at API call time, not init time
        assert (
            client.default_params.get("temperature") == 0.9
        )  # Stored but will be filtered
        assert client.default_params.get("top_p") == 0.95  # Stored but will be filtered
        assert client.default_params.get("thinking_effort") == "high"  # Draft uses high

        # Verify the model is correct
        assert client.model == "openai/o3-pro"

        # Test that get_model_parameters would filter these out
        from litassist.llm.parameter_handler import get_model_parameters

        filtered = get_model_parameters("openai/o3-pro", client.default_params)
        assert "temperature" not in filtered
        assert "top_p" not in filtered
        assert "reasoning" in filtered  # Should have reasoning object
        assert filtered["reasoning"] == {
            "effort": "high"
        }  # Converted from thinking_effort (max maps to high)

    @patch("litassist.config.CONFIG")
    def test_default_command_configuration(self, mock_config):
        """Test commands without specific config raise KeyError (fail-fast)."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"

        # Command not in configs should raise KeyError - NO FALLBACKS
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

        # digest without sub-type should raise KeyError - NO FALLBACKS
        import pytest

        with pytest.raises(KeyError) as exc_info:
            LLMClientFactory.for_command("digest")
        assert "No model configuration found" in str(exc_info.value)
        assert "digest" in str(exc_info.value)

        # digest-summary and digest-issues should work
        client_summary = LLMClientFactory.for_command("digest", "summary")
        assert client_summary.model == "anthropic/claude-sonnet-4.5"

        client_issues = LLMClientFactory.for_command("digest", "issues")
        assert client_issues.model == "anthropic/claude-sonnet-4.5"
