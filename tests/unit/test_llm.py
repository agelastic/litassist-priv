"""
Unit tests for the LLM module.
"""

import pytest
from unittest.mock import Mock, patch
from litassist.llm import LLMClient
from click import ClickException


class TestLLMClient:
    """Test the LLMClient class."""

    def test_init_with_defaults(self):
        """Test LLMClient initialization with default parameters."""
        client = LLMClient("test/model")
        assert client.model == "test/model"
        assert client.temperature == 0.7
        assert client.top_p == 0.9
        assert client.max_tokens == 4098

    def test_init_with_custom_params(self):
        """Test LLMClient initialization with custom parameters."""
        client = LLMClient(
            "test/model",
            temperature=0.5,
            top_p=0.8,
            max_tokens=2000,
            presence_penalty=0.1,
            frequency_penalty=0.2,
        )
        assert client.temperature == 0.5
        assert client.top_p == 0.8
        assert client.max_tokens == 2000
        assert client.presence_penalty == 0.1
        assert client.frequency_penalty == 0.2

    @patch("litassist.llm.openai.ChatCompletion.create")
    def test_complete_success(self, mock_create):
        """Test successful completion."""
        mock_create.return_value = Mock(
            choices=[Mock(message=Mock(content="Test response"), finish_reason="stop")],
            usage=Mock(total_tokens=100, prompt_tokens=50, completion_tokens=50),
        )

        client = LLMClient("openai/gpt-4")
        messages = [{"role": "user", "content": "Test prompt"}]
        content, usage = client.complete(messages)

        assert content == "Test response"
        assert usage["total_tokens"] == 100
        mock_create.assert_called_once()

    @patch("litassist.llm.openai.ChatCompletion.create")
    def test_complete_with_length_finish(self, mock_create):
        """Test completion with length limit reached."""
        mock_create.return_value = Mock(
            choices=[
                Mock(message=Mock(content="Truncated response"), finish_reason="length")
            ],
            usage=Mock(total_tokens=100),
        )

        client = LLMClient("openai/gpt-4")
        messages = [{"role": "user", "content": "Test prompt"}]
        content, usage = client.complete(messages)

        assert "[Output truncated due to length]" in content

    @patch("litassist.llm.openai.ChatCompletion.create")
    def test_complete_api_error(self, mock_create):
        """Test API error handling."""
        mock_create.side_effect = Exception("API Error")

        client = LLMClient("openai/gpt-4")
        messages = [{"role": "user", "content": "Test prompt"}]

        with pytest.raises(ClickException, match="API request failed"):
            client.complete(messages)

    @patch("litassist.llm.LLMClient.complete")
    def test_verify_success(self, mock_complete):
        """Test successful verification."""
        mock_complete.return_value = ("Looks good", {"total_tokens": 50})

        client = LLMClient("test/model")
        result = client.verify("Test content")

        assert result == "Looks good"
        mock_complete.assert_called_once()

    @patch("litassist.llm.openai.api_key", "test_key")
    @patch("litassist.llm.openai.api_base", "https://api.test.com")
    def test_openrouter_configuration(self):
        """Test OpenRouter-specific configuration."""
        with patch("litassist.llm.openai.ChatCompletion.create") as mock_create:
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content="Test"))],
                usage=Mock(total_tokens=10),
            )

            client = LLMClient("anthropic/claude-3")
            client.complete([{"role": "user", "content": "Test"}])

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["model"] == "anthropic/claude-3"
