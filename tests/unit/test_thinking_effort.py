"""
Tests for universal thinking_effort parameter handling.

Tests the conversion of universal thinking_effort parameter to
model-specific thinking/reasoning parameters.
"""

import pytest
from unittest.mock import patch
from litassist.llm.parameter_handler import (
    convert_thinking_effort,
    get_model_parameters,
)
from litassist.llm.factory import LLMClientFactory


class TestThinkingEffortConversion:
    """Test thinking effort parameter conversion for OpenRouter reasoning object format."""

    def test_openai_reasoning_conversion(self):
        """Test OpenAI o1/o3 model reasoning object conversion for OpenRouter."""
        # Test effort-based mapping for OpenRouter
        assert convert_thinking_effort("low", "openai/o3-pro") == {
            "reasoning": {"effort": "low"}
        }
        assert convert_thinking_effort("medium", "openai/o3-pro") == {
            "reasoning": {"effort": "medium"}
        }
        assert convert_thinking_effort("high", "openai/o3-pro") == {
            "reasoning": {"effort": "high"}
        }

        # Test max maps to high
        assert convert_thinking_effort("max", "openai/o3-pro") == {
            "reasoning": {"effort": "high"}
        }

        # Test none returns empty
        assert convert_thinking_effort("none", "openai/o3-pro") == {}

        # Test GPT-5 minimal support
        assert convert_thinking_effort("minimal", "openai/gpt-5") == {
            "reasoning": {"effort": "minimal"}
        }

        # Test minimal fallback for non-GPT-5
        assert convert_thinking_effort("minimal", "openai/o3-pro") == {
            "reasoning": {"effort": "low"}
        }

        # GPT-5.5 family must emit reasoning effort (regression: previously dropped).
        # GPT-5.5 added the xhigh tier, so "max" maps to xhigh (its ceiling).
        assert convert_thinking_effort("medium", "openai/gpt-5.5") == {
            "reasoning": {"effort": "medium"}
        }
        assert convert_thinking_effort("max", "openai/gpt-5.5") == {
            "reasoning": {"effort": "xhigh"}
        }

        # GPT-5 Pro family must emit reasoning effort (regression: previously dropped)
        assert convert_thinking_effort("medium", "openai/gpt-5-pro") == {
            "reasoning": {"effort": "medium"}
        }
        assert convert_thinking_effort("max", "openai/gpt-5-pro") == {
            "reasoning": {"effort": "high"}
        }

    def test_unknown_model_family(self):
        """Test that unknown model families return empty dict."""
        assert convert_thinking_effort("high", "unknown") == {}
        assert convert_thinking_effort("medium", "random") == {}


class TestLLMClientFactoryThinkingEffort:
    """Test that LLMClientFactory properly handles thinking_effort in configs."""

    @patch("litassist.config.CONFIG")
    def test_strategy_command_thinking_effort(self, mock_config):
        """Test strategy command uses thinking_effort."""
        client = LLMClientFactory.for_command("strategy")

        # Check that thinking_effort is in default params
        assert "thinking_effort" in client.default_params
        assert (
            client.default_params["thinking_effort"] == "max"
        )  # Updated to match config

    @patch("litassist.config.CONFIG")
    def test_brainstorm_orthodox_thinking_effort(self, mock_config):
        """Test brainstorm-orthodox uses thinking_effort for Claude."""
        client = LLMClientFactory.for_command("brainstorm", "orthodox")

        # Check that thinking_effort is in default params
        assert "thinking_effort" in client.default_params
        assert client.default_params["thinking_effort"] == "medium"

    @patch("litassist.config.CONFIG")
    def test_override_thinking_effort(self, mock_config):
        """Test that thinking_effort can be overridden."""
        client = LLMClientFactory.for_command("strategy", thinking_effort="low")

        # Check override worked
        assert client.default_params["thinking_effort"] == "low"


class TestVerbosityParameter:
    """Test verbosity parameter support."""

    def test_verbosity_parameter(self):
        """Test that verbosity parameter is properly handled."""
        from litassist.llm.parameter_handler import convert_verbosity

        # Valid levels
        assert convert_verbosity("low") == {"verbosity": "low"}
        assert convert_verbosity("medium") == {"verbosity": "medium"}
        assert convert_verbosity("high") == {"verbosity": "high"}

        # Invalid levels
        assert convert_verbosity("invalid") == {}
        assert convert_verbosity("") == {}

    def test_verbosity_in_model_parameters(self):
        """Test verbosity parameter filtering in get_model_parameters."""
        params = {
            "thinking_effort": "high",
            "verbosity": "high",
            "max_tokens": 1000,
        }

        # For GPT-5 which supports verbosity
        filtered = get_model_parameters("openai/gpt-5", params)
        assert "verbosity" in filtered
        assert filtered["verbosity"] == "high"

        # For o3-pro - o-series models do NOT support verbosity (removed per OpenAI docs)
        filtered = get_model_parameters("openai/o3-pro", params)
        assert "verbosity" not in filtered  # o-series skips verbosity


class TestAdvancedParameters:
    """Test advanced parameter support."""

    def test_advanced_sampling_parameters(self):
        """Test min_p, top_a, repetition_penalty parameters."""
        params = {
            "temperature": 0.7,
            "min_p": 0.05,
            "top_a": 0.8,
            "repetition_penalty": 1.2,
            "max_tokens": 1000,
        }

        # For xai models using OpenRouter
        filtered = get_model_parameters("x-ai/grok-4", params)
        # OpenRouter-specific params are preserved for extra_body handling
        assert "min_p" in filtered  # Will be moved to extra_body
        assert filtered["min_p"] == 0.05
        assert "top_a" in filtered  # Will be moved to extra_body
        assert filtered["top_a"] == 0.8
        assert "repetition_penalty" in filtered  # Will be moved to extra_body
        assert filtered["repetition_penalty"] == 1.2

        # Standard params should also be present
        assert "temperature" in filtered
        assert filtered["temperature"] == 0.7
        assert "max_tokens" in filtered
        assert filtered["max_tokens"] == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
