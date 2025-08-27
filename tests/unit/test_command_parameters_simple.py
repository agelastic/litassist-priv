"""
Simplified tests for command-specific parameter propagation.

Tests the LLMClientFactory directly to verify correct model configuration.
"""

from unittest.mock import patch
from litassist.llm import LLMClientFactory


class TestCommandParameterConfiguration:
    """Test that commands are configured with correct models and parameters."""

    @patch("litassist.llm.CONFIG")
    def test_extractfacts_configuration(self, mock_config):
        """Test extractfacts command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"
        
        # Check the configuration
        assert "extractfacts" in LLMClientFactory.COMMAND_CONFIGS
        config = LLMClientFactory.COMMAND_CONFIGS["extractfacts"]
        assert config["model"] == "anthropic/claude-sonnet-4"
        
        # Create client and verify model
        client = LLMClientFactory.for_command("extractfacts")
        assert client.model == "anthropic/claude-sonnet-4"

    @patch("litassist.llm.CONFIG")
    def test_lookup_configuration(self, mock_config):
        """Test lookup command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"
        
        assert "lookup" in LLMClientFactory.COMMAND_CONFIGS
        config = LLMClientFactory.COMMAND_CONFIGS["lookup"]
        assert config["model"] == "google/gemini-2.5-pro"
        assert config["force_verify"] is False
        
        client = LLMClientFactory.for_command("lookup")
        assert client.model == "google/gemini-2.5-pro"
        assert client._force_verify is False

    @patch("litassist.llm.CONFIG")
    def test_strategy_configuration(self, mock_config):
        """Test strategy command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"
        
        assert "strategy" in LLMClientFactory.COMMAND_CONFIGS
        config = LLMClientFactory.COMMAND_CONFIGS["strategy"]
        assert config["model"] == "openai/o3-pro"
        assert config["thinking_effort"] == "high"
        assert config["force_verify"] is True
        
        client = LLMClientFactory.for_command("strategy")
        assert client.model == "openai/o3-pro"
        assert client._force_verify is True
        assert client.default_params.get("thinking_effort") == "high"

    @patch("litassist.llm.CONFIG")
    def test_draft_configuration(self, mock_config):
        """Test draft command configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"
        
        assert "draft" in LLMClientFactory.COMMAND_CONFIGS
        config = LLMClientFactory.COMMAND_CONFIGS["draft"]
        assert config["model"] == "openai/o3-pro"
        assert config["thinking_effort"] == "high"
        
        client = LLMClientFactory.for_command("draft")
        assert client.model == "openai/o3-pro"
        # max_completion_tokens might be set by default for o3-pro models
        assert "max_completion_tokens" in client.default_params

    @patch("litassist.llm.CONFIG")
    def test_parameter_filtering_for_o3_pro(self, mock_config):
        """Test that o3-pro models filter out unsupported parameters during API call."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"
        
        # Create client with temperature (will be stored but filtered during API call)
        client = LLMClientFactory.for_command("strategy", temperature=0.9, top_p=0.95)
        
        # Parameters are stored in default_params but will be filtered during API call
        # This is the actual behavior - filtering happens at API call time, not init time
        assert client.default_params.get("temperature") == 0.9  # Stored but will be filtered
        assert client.default_params.get("top_p") == 0.95  # Stored but will be filtered
        assert client.default_params.get("thinking_effort") == "high"
        
        # Verify the model is correct
        assert client.model == "openai/o3-pro"
        
        # Test that get_model_parameters would filter these out
        from litassist.llm import get_model_parameters
        filtered = get_model_parameters("openai/o3-pro", client.default_params)
        assert "temperature" not in filtered
        assert "top_p" not in filtered
        assert filtered.get("reasoning_effort") == "high"  # Converted from thinking_effort

    @patch("litassist.llm.CONFIG")
    def test_default_command_configuration(self, mock_config):
        """Test commands without specific config use defaults."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"
        
        # Command not in COMMAND_CONFIGS should use default
        client = LLMClientFactory.for_command("unknown_command")
        assert client.model == "anthropic/claude-sonnet-4"  # Default model

    @patch("litassist.llm.CONFIG")
    def test_digest_uses_default_config(self, mock_config):
        """Test digest command uses default configuration."""
        mock_config.openrouter_key = "test_key"
        mock_config.openai_key = "test_key"
        
        # digest is not in COMMAND_CONFIGS, should use default
        client = LLMClientFactory.for_command("digest")
        assert client.model == "anthropic/claude-sonnet-4"  # Default model