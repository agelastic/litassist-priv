"""
Tests for the LLMClientFactory functionality.
"""

from unittest.mock import patch
from litassist.llm import LLMClientFactory, LLMClient


class TestLLMClientFactory:
    """Test the LLMClientFactory pattern."""

    def test_for_command_lookup(self):
        """Test factory creates lookup client with correct configuration."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            client = LLMClientFactory.for_command("lookup")

            assert isinstance(client, LLMClient)
            assert client.model == "google/gemini-2.5-pro-preview"
            assert hasattr(client, "_force_verify")
            assert client._force_verify is False

    def test_for_command_brainstorm(self):
        """Test factory creates brainstorm client with default configuration."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # Default brainstorm falls back to default config (not in COMMAND_CONFIGS)
            client = LLMClientFactory.for_command("brainstorm")

            assert isinstance(client, LLMClient)
            assert hasattr(client, "_force_verify")

    def test_for_command_strategy(self):
        """Test factory creates strategy client with correct configuration."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            client = LLMClientFactory.for_command("strategy")

            assert isinstance(client, LLMClient)
            assert client.model == "openai/o3-pro"
            assert hasattr(client, "_force_verify")
            assert client._force_verify is True

    def test_for_command_draft(self):
        """Test factory creates draft client with correct configuration."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            client = LLMClientFactory.for_command("draft")

            assert isinstance(client, LLMClient)
            assert client.model == "openai/o3-pro"
            assert hasattr(client, "_force_verify")

    def test_for_command_with_overrides(self):
        """Test factory applies parameter overrides correctly."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            client = LLMClientFactory.for_command(
                "lookup", temperature=0.8, max_tokens=4096
            )

            assert client.default_params["temperature"] == 0.8
            assert client.default_params["max_tokens"] == 4096

    def test_for_command_unknown_command(self):
        """Test factory handles unknown commands gracefully."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # Should fall back to default model configuration
            client = LLMClientFactory.for_command("unknown_command")

            assert isinstance(client, LLMClient)
            # Should use default model from fallback config
            assert client.model is not None

    def test_command_configs_exist(self):
        """Test that all expected command configurations exist."""
        from litassist.llm import LLMClientFactory

        configs = LLMClientFactory.COMMAND_CONFIGS

        expected_configs = ["lookup", "extractfacts", "strategy", "draft"]

        for command in expected_configs:
            assert command in configs
            config = configs[command]
            assert "model" in config

    def test_verification_flags_set_correctly(self):
        """Test that force_verify flags are set correctly for different commands."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # Commands that should force verification
            strict_commands = ["extractfacts", "strategy"]
            for command in strict_commands:
                client = LLMClientFactory.for_command(command)
                assert hasattr(client, "_force_verify")
                assert (
                    client._force_verify is True
                ), f"{command} should force verification"

            # Commands that should not force verification
            lenient_commands = ["lookup"]
            for command in lenient_commands:
                client = LLMClientFactory.for_command(command)
                assert hasattr(client, "_force_verify")
                assert (
                    client._force_verify is False
                ), f"{command} should not force verification"

    def test_model_parameter_restrictions(self):
        """Test that o1/o3 models have correct parameter restrictions."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # Test o3-pro model (strategy)
            strategy_client = LLMClientFactory.for_command("strategy")
            strategy_params = strategy_client.default_params

            # o3-pro should have reasoning_effort but not unsupported params
            assert "reasoning_effort" in strategy_params
            assert "temperature" not in strategy_params
            assert "top_p" not in strategy_params

            # Test o3-pro model (draft)
            draft_client = LLMClientFactory.for_command("draft")
            draft_params = draft_client.default_params

            # o3-pro should have reasoning_effort for draft as well
            assert "reasoning_effort" in draft_params

    def test_environment_variable_override(self):
        """Test that environment variables can override model selection."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            with patch.dict(
                "os.environ",
                {"LITASSIST_LOOKUP_MODEL": "anthropic/claude-3-5-sonnet-20241022"},
            ):
                client = LLMClientFactory.for_command("lookup")
                # Environment variable should override the model
                assert client.model == "anthropic/claude-3-5-sonnet-20241022"


class TestLLMClientFactoryIntegration:
    """Integration tests for LLMClientFactory."""

    def test_factory_creates_working_clients(self):
        """Test that factory creates clients that can be used."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            commands = [
                "lookup",
                "brainstorm",
                "strategy",
                "draft",
                "digest",
                "extractfacts",
            ]

            for command in commands:
                client = LLMClientFactory.for_command(command)

                # All clients should have required attributes
                assert hasattr(client, "model")
                assert hasattr(client, "default_params")
                assert hasattr(client, "complete")
                assert hasattr(client, "_force_verify")

                # Model should be a valid string
                assert isinstance(client.model, str)
                assert len(client.model) > 0

    def test_parameter_inheritance_and_override(self):
        """Test that parameters are inherited from config and can be overridden."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # Test base parameters from config
            client1 = LLMClientFactory.for_command("lookup")
            base_temp = client1.default_params.get("temperature")

            # Test override
            client2 = LLMClientFactory.for_command("lookup", temperature=0.9)
            override_temp = client2.default_params.get("temperature")

            assert override_temp == 0.9
            assert override_temp != base_temp  # Should be different from base

    def test_configured_commands_have_specific_models(self):
        """Test that configured commands use specific models."""
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            models = {}
            # Only test commands that have explicit configurations
            configured_commands = ["lookup", "strategy", "draft", "extractfacts"]

            for command in configured_commands:
                client = LLMClientFactory.for_command(command)
                models[command] = client.model

            # Specific model assertions based on current configuration
            assert "gemini" in models["lookup"].lower()  # Uses Gemini for search
            assert "o3-pro" in models["strategy"].lower()  # Uses o3-pro for strategy
            assert "o3-pro" in models["draft"].lower()  # Uses o3-pro for drafting
            assert (
                "claude" in models["extractfacts"].lower()
            )  # Uses Claude for extraction
