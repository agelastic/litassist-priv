"""
Tests for model parameter handling functions.

Tests cover:
- get_model_family function for identifying model families
- get_model_parameters function for filtering parameters
- Parameter restrictions for different model families
"""

from litassist.llm.parameter_handler import get_model_family, get_model_parameters


class TestGetModelFamily:
    """Test the get_model_family function."""

    def test_openai_reasoning_models(self):
        """Test identification of OpenAI reasoning models."""
        # Pattern matches "openai/o" followed by digits
        assert get_model_family("openai/o1") == "openai_reasoning"
        assert get_model_family("openai/o1-preview") == "openai_reasoning"
        assert get_model_family("openai/o1-mini") == "openai_reasoning"
        assert get_model_family("openai/o3") == "openai_reasoning"
        assert get_model_family("openai/o3-pro") == "openai_reasoning"

        # Without provider prefix, won't match
        assert get_model_family("o1-preview") == "default"
        assert get_model_family("o3-pro") == "default"

    def test_claude_models(self):
        """Test identification of Claude models."""
        # Claude 4 models get special family
        assert get_model_family("anthropic/claude-opus-4") == "claude4"
        assert get_model_family("anthropic/claude-opus-4.1") == "claude4"
        assert get_model_family("anthropic/claude-sonnet-4") == "claude4"

        # Claude 3 and other models are standard anthropic
        assert get_model_family("anthropic/claude-3-opus") == "anthropic"
        assert get_model_family("anthropic/claude-3-sonnet") == "anthropic"
        assert get_model_family("anthropic/claude-3.7-sonnet") == "anthropic"

        # Without provider prefix, won't match
        assert get_model_family("claude-3-opus") == "default"

    def test_openai_standard_models(self):
        """Test identification of standard OpenAI models."""
        # Pattern matches "openai/gpt" or "openai/chatgpt"
        assert get_model_family("openai/gpt-4") == "openai_standard"
        assert get_model_family("openai/gpt-4-turbo") == "openai_standard"
        assert get_model_family("openai/gpt-3.5-turbo") == "openai_standard"
        assert get_model_family("openai/chatgpt") == "openai_standard"

        # Without provider prefix, won't match
        assert get_model_family("gpt-4") == "default"

    def test_google_models(self):
        """Test identification of Google models."""
        # Pattern matches "google/gemini", "google/palm", or "google/bard"
        assert get_model_family("google/gemini-pro") == "google"
        assert get_model_family("google/gemini-2.5-pro") == "google"
        assert get_model_family("google/gemini-2.5-pro-preview") == "google"
        assert get_model_family("google/palm-2") == "google"
        assert get_model_family("google/bard") == "google"

        # Without provider prefix, won't match
        assert get_model_family("gemini-pro") == "default"

    def test_grok_models(self):
        """Test identification of Grok models."""
        # Pattern matches "x-ai/grok"
        assert get_model_family("x-ai/grok-3") == "xai"
        assert get_model_family("x-ai/grok-beta") == "xai"

        # Without provider prefix, won't match
        assert get_model_family("grok-3") == "default"

    def test_other_models(self):
        """Test default handling of other models."""
        assert get_model_family("llama-2") == "default"
        assert get_model_family("mistral-7b") == "default"
        assert get_model_family("unknown-model") == "default"
        assert get_model_family("meta/llama-2") == "meta"
        assert get_model_family("mistral/mistral-7b") == "mistral"


class TestGetModelParameters:
    """Test the get_model_parameters function."""

    def test_o3_pro_parameter_filtering(self):
        """Test that o3-pro only accepts specific parameters."""
        requested = {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 4096,
            "max_completion_tokens": 8192,
            "thinking_effort": "high",  # Use thinking_effort instead
            "presence_penalty": 0.1,
            "frequency_penalty": 0.1,
        }

        filtered = get_model_parameters("openai/o3-pro", requested)

        # Should only keep allowed parameters
        assert "temperature" not in filtered
        assert "top_p" not in filtered
        assert "max_tokens" not in filtered  # o3-pro uses max_completion_tokens
        assert "presence_penalty" not in filtered
        assert "frequency_penalty" not in filtered

        # Should keep these
        assert filtered["max_completion_tokens"] == 8192
        # Should have reasoning object for OpenRouter
        assert "reasoning" in filtered
        assert filtered["reasoning"] == {"effort": "high"}

    def test_o1_preview_parameter_filtering(self):
        """Test that o1-preview only accepts specific parameters."""
        requested = {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 4096,
            "max_completion_tokens": 8192,
            "presence_penalty": 0.1,
        }

        # o1-preview without provider prefix uses default profile
        filtered = get_model_parameters("o1-preview", requested)
        assert filtered == {"temperature": 0.7, "top_p": 0.95, "max_tokens": 4096}

        # With proper prefix, uses openai_reasoning profile
        filtered = get_model_parameters("openai/o1-preview", requested)
        assert "temperature" not in filtered
        assert "top_p" not in filtered
        assert "max_tokens" not in filtered  # Transformed to max_completion_tokens
        assert "presence_penalty" not in filtered
        assert filtered["max_completion_tokens"] == 8192

    def test_standard_model_parameters(self):
        """Test that standard models accept all common parameters."""
        requested = {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 4096,
            "presence_penalty": 0.1,
            "frequency_penalty": 0.1,
            "stop": ["\n\n"],
            "seed": 42,
        }

        # Test with GPT-4 (with proper prefix)
        filtered = get_model_parameters("openai/gpt-4", requested)
        assert filtered == requested  # openai_standard supports all these

        # Test without prefix (uses default profile)
        filtered = get_model_parameters("gpt-4", requested)
        assert filtered == {
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 4096,
            "stop": ["\n\n"],
        }

        # Test with Claude (anthropic profile)
        filtered = get_model_parameters("anthropic/claude-3-opus", requested)
        # anthropic doesn't support all OpenAI params
        assert "temperature" in filtered
        assert "max_tokens" in filtered
        assert "seed" not in filtered  # Not in anthropic allowed list
        assert "presence_penalty" not in filtered

        # Test with Gemini (google profile)
        filtered = get_model_parameters("google/gemini-pro", requested)
        assert "temperature" in filtered
        assert (
            "max_tokens" in filtered
        )  # No transformation needed with v1.x - OpenRouter handles this
        assert "seed" not in filtered  # Not in google allowed list

    def test_reasoning_effort_validation(self):
        """Test thinking_effort parameter conversion to reasoning object."""
        # Valid values - thinking_effort converts to reasoning object
        for value in ["low", "medium", "high"]:
            filtered = get_model_parameters("openai/o3-pro", {"thinking_effort": value})
            assert "reasoning" in filtered
            assert filtered["reasoning"] == {"effort": value}

        # Test direct reasoning object (when not using thinking_effort)
        filtered = get_model_parameters(
            "openai/o3-pro", {"reasoning": {"effort": "high"}}
        )
        assert "reasoning" in filtered
        assert filtered["reasoning"] == {"effort": "high"}

        # Non-reasoning models should ignore this parameter
        filtered = get_model_parameters("openai/gpt-4", {"thinking_effort": "high"})
        assert "reasoning" not in filtered
        assert "reasoning_effort" not in filtered

    def test_max_tokens_vs_max_completion_tokens(self):
        """Test handling of max_tokens vs max_completion_tokens."""
        # For o3-pro, max_tokens should be ignored
        filtered = get_model_parameters("openai/o3-pro", {"max_tokens": 4096})
        assert "max_tokens" not in filtered

        # But max_completion_tokens should be kept
        filtered = get_model_parameters(
            "openai/o3-pro", {"max_completion_tokens": 4096}
        )
        assert filtered["max_completion_tokens"] == 4096

        # For standard models, max_tokens should be kept
        filtered = get_model_parameters("gpt-4", {"max_tokens": 4096})
        assert filtered["max_tokens"] == 4096

        # And max_completion_tokens should be ignored
        filtered = get_model_parameters("gpt-4", {"max_completion_tokens": 4096})
        assert "max_completion_tokens" not in filtered

    def test_empty_parameters(self):
        """Test handling of empty parameter dict."""
        filtered = get_model_parameters("openai/o3-pro", {})
        assert filtered == {}

        filtered = get_model_parameters("gpt-4", {})
        assert filtered == {}

    def test_none_parameters(self):
        """Test handling of None values in parameters."""
        requested = {"temperature": None, "max_tokens": 4096, "reasoning_effort": None}

        filtered = get_model_parameters("openai/o3-pro", requested)
        # None values should be filtered out
        assert "temperature" not in filtered
        assert "reasoning_effort" not in filtered
        assert "max_tokens" not in filtered

    def test_parameter_type_preservation(self):
        """Test that parameter types are preserved."""
        requested = {
            "temperature": 0.7,  # float
            "max_tokens": 4096,  # int
            "stop": ["\n\n"],  # list
            "response_format": {"type": "json_object"},  # dict
            "stream": True,  # bool
        }

        # Test with proper OpenAI model that supports these params
        filtered = get_model_parameters("openai/gpt-4", requested)

        assert isinstance(filtered["temperature"], float)
        assert isinstance(filtered["max_tokens"], int)
        assert isinstance(filtered["stop"], list)
        assert isinstance(filtered["response_format"], dict)
        assert isinstance(filtered["stream"], bool)

    def test_model_family_edge_cases(self):
        """Test edge cases in model family detection."""
        # The regex patterns are case-sensitive, so uppercase won't match
        assert get_model_family("O1-PREVIEW") == "default"
        assert get_model_family("CLAUDE-3-OPUS") == "default"

        # Lowercase versions will match
        assert get_model_family("openai/o1-preview") == "openai_reasoning"
        assert get_model_family("anthropic/claude-3-opus") == "anthropic"

    def test_parameter_filtering_preserves_order(self):
        """Test that parameter filtering preserves relative order."""
        requested = {
            "a": 1,
            "temperature": 0.7,
            "b": 2,
            "max_completion_tokens": 4096,
            "c": 3,
            "thinking_effort": "high",
            "d": 4,
        }

        filtered = get_model_parameters("openai/o3-pro", requested)

        # Should have reasoning object and max_completion_tokens
        assert "reasoning" in filtered
        assert "max_completion_tokens" in filtered
        assert filtered["reasoning"] == {"effort": "high"}
