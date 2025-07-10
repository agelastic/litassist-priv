"""Unit tests for LLMClient streaming error retry logic."""

import pytest
from unittest.mock import patch
from litassist.llm import LLMClient


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
        self.usage = {"prompt_tokens": 10, "completion_tokens": 20}


def test_streaming_error_retry(monkeypatch):
    """Test that streaming errors are retried and eventually succeed."""
    client = LLMClient("anthropic/claude-sonnet-4")

    call_count = {"n": 0}

    def mock_create(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] < 3:
            raise Exception("Error processing stream")
        return MockResponse("Success on third try")

    with patch("openai.ChatCompletion.create", new=mock_create):
        content, usage = client.complete([{"role": "user", "content": "Test message"}])
        assert content == "Success on third try"
        assert call_count["n"] == 3


def test_streaming_error_max_retries(monkeypatch):
    """Test that streaming errors eventually fail after max retries."""
    client = LLMClient("anthropic/claude-sonnet-4")

    def always_streaming_error(*args, **kwargs):
        raise Exception("Error processing stream")

    with patch("openai.ChatCompletion.create", new=always_streaming_error):
        with pytest.raises(Exception, match="Error processing stream"):
            client.complete([{"role": "user", "content": "Test"}])
