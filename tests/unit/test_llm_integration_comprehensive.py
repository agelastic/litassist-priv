"""
Comprehensive tests for LLM integration functionality.

Tests cover LLM client factory, citation validation, and error handling.
All tests run offline using mocked dependencies.

Reasoning-trace extraction (extract_reasoning_trace) is covered, more
thoroughly, in test_utils_comprehensive.py.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock

from litassist.llm.factory import LLMClient


class TestPromptIntegration:
    """Test prompt system integration with LLM."""

    @patch("litassist.llm.api_handlers.get_openai_client")
    @patch("litassist.config.CONFIG")
    @patch("litassist.prompts.PROMPTS")
    def test_prompt_system_integration(
        self, mock_prompts, mock_config, mock_get_client
    ):
        """Test that prompts are correctly integrated with LLM calls."""
        # Setup proper CONFIG values
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"

        # Mock prompts
        mock_prompts.get.return_value = "Test system prompt"

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Response with prompt")
        mock_response.choices[0].error = None
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock(
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            model_dump=lambda: {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        )

        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient("openai/gpt-4o")
        messages = [{"role": "user", "content": "Test"}]
        content, usage = client.complete(messages, skip_citation_verification=True)

        assert content == "Response with prompt"


class TestErrorHandling:
    """Test error handling in LLM operations."""

    @patch("litassist.llm.api_handlers.get_openai_client")
    @patch("litassist.config.CONFIG")
    def test_empty_response_handling(self, mock_config, mock_get_client):
        """Test handling of empty API responses."""
        # Setup proper CONFIG values
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"

        # Mock the OpenAI client to return empty response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = None

        client = LLMClient("openai/gpt-4o")
        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(Exception) as exc_info:
            client.complete(messages, skip_citation_verification=True)

        assert "Empty response" in str(exc_info.value)
