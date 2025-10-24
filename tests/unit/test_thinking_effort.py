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

    def test_anthropic_thinking_conversion(self):
        """Test Anthropic Claude reasoning object conversion for OpenRouter."""
        # Test none returns empty
        assert convert_thinking_effort("none", "anthropic/claude-4") == {}

        # Test token-based allocation for OpenRouter
        assert convert_thinking_effort("low", "anthropic/claude-4") == {
            "reasoning": {"max_tokens": 1024}
        }

        assert convert_thinking_effort("medium", "anthropic/claude-4") == {
            "reasoning": {"max_tokens": 8192}
        }

        assert convert_thinking_effort("high", "anthropic/claude-4") == {
            "reasoning": {"max_tokens": 16384}
        }

        assert convert_thinking_effort("max", "anthropic/claude-4") == {
            "reasoning": {"max_tokens": 32000}
        }

    def test_google_thinking_config_conversion(self):
        """Test Google Gemini reasoning object conversion for OpenRouter."""
        # Test none returns empty
        assert convert_thinking_effort("none", "google/gemini-2.5-pro") == {}

        # Test effort-based for OpenRouter
        assert convert_thinking_effort("low", "google/gemini-2.5-pro") == {
            "reasoning": {"effort": "low"}
        }

        assert convert_thinking_effort("medium", "google/gemini-2.5-pro") == {
            "reasoning": {"effort": "medium"}
        }

        assert convert_thinking_effort("high", "google/gemini-2.5-pro") == {
            "reasoning": {"effort": "high"}
        }

        # Test max maps to high
        assert convert_thinking_effort("max", "google/gemini-2.5-pro") == {
            "reasoning": {"effort": "high"}
        }

    def test_unknown_model_family(self):
        """Test that unknown model families return empty dict."""
        assert convert_thinking_effort("high", "unknown") == {}
        assert convert_thinking_effort("medium", "random") == {}


class TestModelParameterFiltering:
    """Test that thinking_effort is properly filtered for different models."""

    def test_openai_o3_pro_thinking_effort(self):
        """Test o3-pro properly transforms thinking_effort to reasoning object."""
        params = {
            "thinking_effort": "high",
            "temperature": 0.5,  # Should be filtered
            "max_tokens": 1000,
        }

        filtered = get_model_parameters("openai/o3-pro", params)

        # Should have reasoning object for OpenRouter
        assert "reasoning" in filtered
        assert filtered["reasoning"] == {"effort": "high"}
        assert "thinking_effort" not in filtered
        assert (
            "reasoning_effort" not in filtered
        )  # Should not have standalone parameter

        # Should transform max_tokens
        assert "max_completion_tokens" in filtered
        assert filtered["max_completion_tokens"] == 1000

        # Should not have temperature for o3-pro
        assert "temperature" not in filtered

    def test_anthropic_claude_thinking_effort(self):
        """Test Claude properly transforms thinking_effort to reasoning object."""
        params = {
            "thinking_effort": "medium",
            "temperature": 0.3,
            "max_tokens": 2000,
        }

        filtered = get_model_parameters("anthropic/claude-opus-4.1", params)

        # Should have reasoning object for OpenRouter
        assert "reasoning" in filtered
        assert filtered["reasoning"] == {"max_tokens": 8192}
        assert "thinking_effort" not in filtered
        assert "thinking" not in filtered  # Should not have vendor-specific format

        # Should keep other params
        assert filtered["temperature"] == 0.3
        assert filtered["max_tokens"] == 2000

    def test_google_gemini_thinking_effort(self):
        """Test Gemini properly transforms thinking_effort to reasoning object."""
        params = {
            "thinking_effort": "low",
            "temperature": 0.1,
            "max_tokens": 1500,
        }

        filtered = get_model_parameters("google/gemini-2.5-pro", params)

        # Should have reasoning object for OpenRouter
        assert "reasoning" in filtered
        assert filtered["reasoning"] == {"effort": "low"}
        assert "thinking_effort" not in filtered
        assert (
            "thinking_config" not in filtered
        )  # Should not have vendor-specific format

        # Should keep other params
        assert filtered["temperature"] == 0.1
        assert filtered["max_tokens"] == 1500

    def test_model_without_thinking_support(self):
        """Test that models without thinking support ignore thinking_effort."""
        params = {
            "thinking_effort": "high",
            "temperature": 0.7,
            "max_tokens": 1000,
        }

        # GPT-4 standard doesn't support thinking
        filtered = get_model_parameters("openai/gpt-4", params)

        # Should not have any thinking-related params
        assert "thinking_effort" not in filtered
        assert "reasoning_effort" not in filtered
        assert "thinking" not in filtered
        assert "thinking_config" not in filtered

        # Should keep supported params
        assert filtered["temperature"] == 0.7
        assert filtered["max_tokens"] == 1000


class TestLLMClientFactoryThinkingEffort:
    """Test that LLMClientFactory properly handles thinking_effort in configs."""

    @patch("litassist.config.CONFIG")
    def test_strategy_command_thinking_effort(self, mock_config):
        """Test strategy command uses thinking_effort."""
        mock_config.use_token_limits = False

        client = LLMClientFactory.for_command("strategy")

        # Check that thinking_effort is in default params
        assert "thinking_effort" in client.default_params
        assert (
            client.default_params["thinking_effort"] == "max"
        )  # Updated to match config

    @patch("litassist.config.CONFIG")
    def test_lookup_command_thinking_effort(self, mock_config):
        """Test lookup command uses thinking_effort for Gemini."""
        mock_config.use_token_limits = False

        client = LLMClientFactory.for_command("lookup")

        # Check that thinking_effort is in default params
        assert "thinking_effort" in client.default_params
        assert client.default_params["thinking_effort"] == "low"

    @patch("litassist.config.CONFIG")
    def test_brainstorm_orthodox_thinking_effort(self, mock_config):
        """Test brainstorm-orthodox uses thinking_effort for Claude."""
        mock_config.use_token_limits = False

        client = LLMClientFactory.for_command("brainstorm", "orthodox")

        # Check that thinking_effort is in default params
        assert "thinking_effort" in client.default_params
        assert client.default_params["thinking_effort"] == "medium"

    @patch("litassist.config.CONFIG")
    def test_override_thinking_effort(self, mock_config):
        """Test that thinking_effort can be overridden."""
        mock_config.use_token_limits = False

        client = LLMClientFactory.for_command("strategy", thinking_effort="low")

        # Check override worked
        assert client.default_params["thinking_effort"] == "low"


class TestBackwardCompatibility:
    """Test that parameter conflicts are properly handled."""

    def test_no_conflicting_parameters(self):
        """Test that reasoning and reasoning_effort are never both present."""
        params = {
            "thinking_effort": "high",
            "reasoning_effort": "medium",  # Should be removed
            "reasoning": {"effort": "low"},  # Should be removed
            "max_tokens": 1000,
        }

        filtered = get_model_parameters("openai/o3-pro", params)

        # Should only have reasoning object from thinking_effort
        assert "reasoning" in filtered
        assert filtered["reasoning"] == {"effort": "high"}
        # Should NOT have conflicting parameters
        assert "reasoning_effort" not in filtered
        assert "thinking_effort" not in filtered

    def test_direct_reasoning_object_preserved(self):
        """Test that direct reasoning object is preserved if no thinking_effort."""
        params = {
            "reasoning": {"effort": "high"},  # Direct OpenRouter format
            "max_tokens": 1000,
        }

        filtered = get_model_parameters("openai/o3-pro", params)

        # Should keep direct reasoning object
        assert "reasoning" in filtered
        assert filtered["reasoning"] == {"effort": "high"}


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

        # For o3-pro which also supports it
        filtered = get_model_parameters("openai/o3-pro", params)
        assert "verbosity" in filtered
        assert filtered["verbosity"] == "high"


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
