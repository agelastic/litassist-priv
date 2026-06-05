"""Unit tests for LLMClient streaming error retry logic."""

import pytest
from unittest.mock import patch, MagicMock
from litassist.llm.client import LLMClient


def test_streaming_error_max_retries(monkeypatch):
    """Test that streaming errors eventually fail after max retries."""
    # Mock CONFIG with proper string values for OpenAI v1.x
    with patch("litassist.config.CONFIG") as mock_config:
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test_key"

        client = LLMClient("test/mock-model")

        def always_streaming_error(*args, **kwargs):
            raise Exception("Error processing stream")

        # Mock the get_openai_client function to return a properly mocked client
        with patch("litassist.llm.api_handlers.get_openai_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client
            mock_client.chat.completions.create.side_effect = always_streaming_error

            with pytest.raises(Exception, match="Error processing stream"):
                client.complete([{"role": "user", "content": "Test message"}])
