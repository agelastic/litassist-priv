"""Unit tests for LLMClient streaming error retry logic."""

import pytest
from unittest.mock import patch, MagicMock
from litassist.llm.client import LLMClient


class MockResponse:
    def __init__(self, content):
        self.choices = [
            type(
                "Choice",
                (),
                {
                    "message": type("Msg", (), {"content": content}),
                    "error": None,
                    "finish_reason": "stop",
                },
            )()
        ]
        self.usage = type(
            "Usage",
            (),
            {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
                "model_dump": lambda self: {
                    "prompt_tokens": 10,
                    "completion_tokens": 20,
                    "total_tokens": 30,
                },
            },
        )()


def test_streaming_error_retry(monkeypatch):
    """Test that streaming errors are retried and eventually succeed."""
    # Mock CONFIG with proper string values for OpenAI v1.x
    with patch("litassist.config.CONFIG") as mock_config:
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test_key"
        mock_config.openai_key = "test_key"

        client = LLMClient("anthropic/claude-sonnet-4")

        call_count = {"n": 0}

        def mock_create(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] < 3:
                raise Exception("Error processing stream")
            return MockResponse("Success on third try")

        # Mock the get_openai_client function to return a properly mocked client
        with patch("litassist.llm.api_handlers.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.chat.completions.create.side_effect = mock_create

            content, usage = client.complete(
                [{"role": "user", "content": "Test message"}]
            )
            assert content == "Success on third try"
            assert call_count["n"] == 3


def test_streaming_error_max_retries(monkeypatch):
    """Test that streaming errors eventually fail after max retries."""
    # Mock CONFIG with proper string values for OpenAI v1.x
    with patch("litassist.config.CONFIG") as mock_config:
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test_key"
        mock_config.openai_key = "test_key"

        client = LLMClient("anthropic/claude-sonnet-4")

        def always_streaming_error(*args, **kwargs):
            raise Exception("Error processing stream")

        # Mock the get_openai_client function to return a properly mocked client
        with patch("litassist.llm.api_handlers.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.chat.completions.create.side_effect = always_streaming_error

            with pytest.raises(Exception, match="Error processing stream"):
                client.complete([{"role": "user", "content": "Test message"}])
