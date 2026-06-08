"""
Tests for the LLMClientFactory functionality.
"""

from unittest.mock import patch
from litassist.llm.factory import LLMClientFactory, LLMClient


class TestLLMClientFactory:
    """Test the LLMClientFactory pattern."""

    def test_for_command_lookup(self):
        """Test factory creates lookup client wired to its configured model."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"

            configs = LLMClientFactory.list_configurations()
            client = LLMClientFactory.for_command("lookup")

            assert isinstance(client, LLMClient)
            assert client.model == configs["lookup"]["model"]

    def test_for_command_brainstorm(self):
        """Test factory requires sub-type for brainstorm - NO FALLBACK."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"

            # brainstorm without sub-type should raise KeyError - NO FALLBACKS
            import pytest

            with pytest.raises(KeyError) as exc_info:
                LLMClientFactory.for_command("brainstorm")
            assert "No model configuration found" in str(exc_info.value)

            # brainstorm-orthodox should work and resolve its configured model
            configs = LLMClientFactory.list_configurations()
            client = LLMClientFactory.for_command("brainstorm", "orthodox")
            assert isinstance(client, LLMClient)
            assert client.model == configs["brainstorm-orthodox"]["model"]

    def test_for_command_with_overrides(self):
        """Test factory applies parameter overrides correctly."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"

            client = LLMClientFactory.for_command(
                "lookup", temperature=0.8, max_tokens=4096
            )

            assert client.default_params["temperature"] == 0.8
            assert client.default_params["max_tokens"] == 4096

    def test_for_command_unknown_command(self):
        """Test factory fails fast on unknown commands - NO FALLBACK."""
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"

            # Should raise KeyError for unknown commands - NO FALLBACKS
            import pytest

            with pytest.raises(KeyError) as exc_info:
                LLMClientFactory.for_command("unknown_command")
            assert "No model configuration found" in str(exc_info.value)
            assert "unknown_command" in str(exc_info.value)

class TestGetContextWindowForCommand:
    """Tests for LLMClientFactory.get_context_window_for_command."""

    def test_matches_capabilities_file_for_each_configured_model(self):
        """For each configured command, the returned window equals the model's entry
        in model_capabilities.yaml. Proves the model->capability lookup is correct."""
        from litassist.llm.factory import _get_model_capabilities

        configs = LLMClientFactory.list_configurations()
        caps = _get_model_capabilities()
        for command, cfg in configs.items():
            model_id = cfg["model"]
            assert model_id in caps, (
                f"{model_id} (used by {command}) missing from model_capabilities.yaml"
            )
            expected = int(caps[model_id]["context_window"])
            assert LLMClientFactory.get_context_window_for_command(
                command.split("-")[0],
                "-".join(command.split("-")[1:]) or None,
            ) == expected

    def test_raises_on_unknown_command(self):
        """Unknown command -> KeyError from get_model_for_command (no fallback)."""
        import pytest

        with pytest.raises(KeyError) as exc_info:
            LLMClientFactory.get_context_window_for_command("no_such_command")
        assert "No model configuration found" in str(exc_info.value)

    def test_raises_when_capability_missing_for_model(self, monkeypatch):
        """If model_capabilities.yaml is missing the model id used by a command,
        get_context_window_for_command raises KeyError pointing at the refresh
        command. This guards against forgetting to run `litassist refresh` after
        swapping a model in model_configs.yaml."""
        import pytest
        from litassist.llm import factory as factory_module

        monkeypatch.setattr(
            factory_module,
            "_get_model_capabilities",
            lambda: {"other/model": {"context_window": 12345}},
        )
        with pytest.raises(KeyError) as exc_info:
            LLMClientFactory.get_context_window_for_command("draft")
        msg = str(exc_info.value)
        assert "No capability data" in msg
        assert "litassist refresh" in msg or "refresh_model_capabilities" in msg


class TestGetInputBudgetForCommand:
    """Tests for LLMClientFactory.get_input_budget_for_command."""

    def test_sub_type_resolves_subtyped_entry(self):
        """Sub-type lookup hits the suffixed YAML key, e.g. brainstorm-orthodox.
        Verifies sub_type plumbing through to the underlying capability lookup."""
        budget = LLMClientFactory.get_input_budget_for_command(
            "brainstorm", "orthodox"
        )
        assert isinstance(budget, int)
        assert budget > 0
