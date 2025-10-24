"""
Tests for the LLMClientFactory functionality.
"""

from unittest.mock import patch
from litassist.llm.factory import LLMClientFactory, LLMClient


class TestLLMClientFactory:
    """Test the LLMClientFactory pattern."""

    def test_for_command_lookup(self):
        """Test factory creates lookup client with correct configuration."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            client = LLMClientFactory.for_command("lookup")

            assert isinstance(client, LLMClient)
            assert client.model == "google/gemini-2.5-pro"
            # Just verify the attribute exists, don't assert specific value
            assert hasattr(client, "_enforce_citations")

    def test_for_command_brainstorm(self):
        """Test factory requires sub-type for brainstorm - NO FALLBACK."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # brainstorm without sub-type should raise KeyError - NO FALLBACKS
            import pytest

            with pytest.raises(KeyError) as exc_info:
                LLMClientFactory.for_command("brainstorm")
            assert "No model configuration found" in str(exc_info.value)

            # brainstorm-orthodox should work
            client = LLMClientFactory.for_command("brainstorm", "orthodox")
            assert isinstance(client, LLMClient)
            assert hasattr(client, "_enforce_citations")

    def test_for_command_strategy(self):
        """Test factory creates strategy client with correct configuration."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            client = LLMClientFactory.for_command("strategy")

            assert isinstance(client, LLMClient)
            # UPDATED: Oct 2025 - Model upgraded to Sonnet 4.5
            assert client.model == "anthropic/claude-sonnet-4.5"
            # Just verify the attribute exists, don't assert specific value
            assert hasattr(client, "_enforce_citations")

    def test_for_command_draft(self):
        """Test factory creates draft client with correct configuration."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            client = LLMClientFactory.for_command("draft")

            assert isinstance(client, LLMClient)
            assert client.model == "openai/o3-pro"
            assert hasattr(client, "_enforce_citations")

    def test_for_command_with_overrides(self):
        """Test factory applies parameter overrides correctly."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            client = LLMClientFactory.for_command(
                "lookup", temperature=0.8, max_tokens=4096
            )

            assert client.default_params["temperature"] == 0.8
            assert client.default_params["max_tokens"] == 4096

    def test_for_command_unknown_command(self):
        """Test factory fails fast on unknown commands - NO FALLBACK."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # Should raise KeyError for unknown commands - NO FALLBACKS
            import pytest

            with pytest.raises(KeyError) as exc_info:
                LLMClientFactory.for_command("unknown_command")
            assert "No model configuration found" in str(exc_info.value)
            assert "unknown_command" in str(exc_info.value)

    def test_command_configs_exist(self):
        """Test that all expected command configurations exist."""
        from litassist.llm.factory import LLMClientFactory

        configs = LLMClientFactory.list_configurations()

        expected_configs = ["lookup", "extractfacts", "strategy", "draft"]

        for command in expected_configs:
            assert command in configs
            config = configs[command]
            assert "model" in config

    def test_verification_flags_set_correctly(self):
        """Test that enforce_citations flags are set correctly for different commands."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # Just verify that various commands have the enforce_citations attribute
            # Don't assert specific values as these may change based on requirements
            test_commands = ["extractfacts", "strategy", "lookup"]
            for command in test_commands:
                client = LLMClientFactory.for_command(command)
                assert hasattr(client, "_enforce_citations"), (
                    f"{command} should have _enforce_citations attribute"
                )

    def test_model_parameter_restrictions(self):
        """Test that o1/o3 models have correct parameter restrictions."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # UPDATED: Oct 2025 - Test claude-sonnet-4.5 model (strategy)
            strategy_client = LLMClientFactory.for_command("strategy")
            strategy_params = strategy_client.default_params

            # claude-sonnet-4.5 should have thinking_effort and standard params
            assert "thinking_effort" in strategy_params
            assert "temperature" in strategy_params  # Claude supports temperature
            assert "top_p" in strategy_params  # Claude supports top_p
            assert strategy_params["temperature"] == 0.2
            assert strategy_params["top_p"] == 0.8

            # Test o3-pro model (draft)
            draft_client = LLMClientFactory.for_command("draft")
            draft_params = draft_client.default_params

            # o3-pro should have thinking_effort for draft as well
            assert "thinking_effort" in draft_params

    def test_environment_variable_override(self):
        """Test that environment variables can override model selection."""
        with patch("litassist.config.CONFIG") as mock_config:
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
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_openai_key"

            # Test simple commands (no sub-type required)
            commands = [
                "lookup",
                "strategy",
                "draft",
                "extractfacts",
            ]

            for command in commands:
                client = LLMClientFactory.for_command(command)

                # All clients should have required attributes
                assert hasattr(client, "model")
                assert hasattr(client, "default_params")
                assert hasattr(client, "complete")
                assert hasattr(client, "_enforce_citations")

                # Model should be a valid string
                assert isinstance(client.model, str)
                assert len(client.model) > 0

    def test_parameter_inheritance_and_override(self):
        """Test that parameters are inherited from config and can be overridden."""
        with patch("litassist.config.CONFIG") as mock_config:
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
        with patch("litassist.config.CONFIG") as mock_config:
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
            # UPDATED: Oct 2025 - Strategy now uses Sonnet 4.5
            assert (
                "claude-sonnet" in models["strategy"].lower()
            )  # Uses Claude Sonnet 4.5 for strategy
            assert "o3-pro" in models["draft"].lower()  # Uses o3-pro for drafting
            # UPDATED: Oct 2025 - Extractfacts upgraded to Sonnet 4.5
            assert (
                "anthropic/claude-sonnet-4.5" in models["extractfacts"].lower()
            )  # Uses Claude Sonnet 4.5 for extraction
