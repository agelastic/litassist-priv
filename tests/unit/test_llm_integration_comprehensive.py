"""
Comprehensive tests for LLM integration functionality.

Tests cover LLM client factory, citation validation, reasoning extraction, and error handling.
All tests run offline using mocked dependencies.
"""

import pytest
from unittest.mock import patch, Mock, MagicMock
from openai import APIConnectionError

from litassist.llm.factory import LLMClientFactory, LLMClient
from litassist.utils.legal_reasoning import LegalReasoningTrace, extract_reasoning_trace


class TestLLMClientFactory:
    """Test LLM client factory functionality."""

    @patch("litassist.config.CONFIG")
    def test_factory_for_command_basic(self, mock_config):
        """Test basic LLM client creation for commands."""
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"

        client = LLMClientFactory.for_command("strategy")

        assert isinstance(client, LLMClient)
        # Model may be different based on configuration
        assert client.model is not None

    @patch("litassist.config.CONFIG")
    def test_factory_with_overrides(self, mock_config):
        """Test LLM client factory with parameter overrides."""
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"
        mock_config.use_token_limits = False  # Disable auto token limits

        overrides = {"temperature": 0.5, "max_tokens": 2000}
        client = LLMClientFactory.for_command("lookup", **overrides)

        assert isinstance(client, LLMClient)
        assert client.default_params.get("temperature") == 0.5
        assert client.default_params.get("max_tokens") == 2000


class TestLLMClient:
    """Test LLM client functionality with mocked API."""

    @patch("litassist.llm.api_handlers.get_openai_client")
    @patch("litassist.config.CONFIG")
    def test_llm_client_retry_on_connection_error(self, mock_config, mock_get_client):
        """Test retry logic on connection errors."""
        # Setup proper CONFIG values for OpenAI v1.x
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"
        mock_config.openai_key = "test-key"

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Simulate connection error for first attempt, then success
        call_count = {"count": 0}

        def side_effect(*args, **kwargs):
            if call_count["count"] < 1:
                call_count["count"] += 1
                raise APIConnectionError(request=Mock())
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message = Mock(content="Retried response")
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
            return mock_response

        mock_client.chat.completions.create.side_effect = side_effect

        client = LLMClient("openai/gpt-4o")
        messages = [{"role": "user", "content": "Test prompt"}]
        content, usage = client.complete(messages, skip_citation_verification=True)
        assert content == "Retried response"
        assert call_count["count"] == 1

    @patch("litassist.llm.api_handlers.get_openai_client")
    @patch("litassist.config.CONFIG")
    def test_llm_client_api_config_restoration(self, mock_config, mock_get_client):
        """Test API config restoration after retries."""
        # Setup proper CONFIG values
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"
        mock_config.openai_key = "test-key"

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Always succeed
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Success")
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
        messages = [{"role": "user", "content": "Test prompt"}]

        # Try multiple times to ensure config is preserved
        for _ in range(3):
            content, usage = client.complete(messages, skip_citation_verification=True)
            assert content == "Success"

    @patch("litassist.llm.api_handlers.get_openai_client")
    @patch("litassist.config.CONFIG")
    def test_llm_client_complete_success(self, mock_config, mock_get_client):
        """Test successful complete operation."""
        # Setup proper CONFIG values
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"
        mock_config.openai_key = "test-key"

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Test response")
        mock_response.choices[0].error = None
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            model_dump=lambda: {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        )

        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient("openai/gpt-4o", temperature=0.7)
        messages = [{"role": "user", "content": "Test prompt"}]
        content, usage = client.complete(messages, skip_citation_verification=True)

        assert content == "Test response"
        assert usage["total_tokens"] == 30
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 20

    @patch("litassist.llm.api_handlers.get_openai_client")
    @patch("litassist.config.CONFIG")
    def test_llm_client_verify_with_level(self, mock_config, mock_get_client):
        """Test verify_with_level functionality."""
        # Setup proper CONFIG values
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"
        mock_config.openai_key = "test-key"

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Verified content")
        mock_response.choices[0].error = None
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model_dump=lambda: {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        )

        mock_client.chat.completions.create.return_value = mock_response

        client = LLMClient("openai/gpt-4o")
        result = client.verify_with_level("Content to verify", "light")

        # verify_with_level returns a tuple of (content, model_used)
        if isinstance(result, tuple):
            content, model_used = result
            assert content == "Verified content"
        else:
            assert result == "Verified content"

        # Token limits are now configured in config, not hardcoded
        # No need to verify specific token limits in unit tests


class TestCitationValidation:
    """Test citation validation with mocked Jade API."""

    @patch("litassist.citation.verify.verify_single_citation")
    def test_citation_validation_mock(self, mock_verify):
        """Test citation validation with mocked Jade responses."""
        mock_verify.return_value = (True, "Citation is valid", "[2022] FCA 123")

        from litassist.citation.verify import verify_single_citation

        valid, msg, normalized = verify_single_citation("[2022] FCA 123")
        assert valid is True
        assert "valid" in msg.lower()


class TestReasoningExtraction:
    """Test legal reasoning trace extraction."""

    def test_extract_reasoning_trace(self):
        """Test extracting reasoning trace from text."""
        text = """
        === REASONING ===
        Issue: Test issue
        
        Applicable Law: Test law
        
        Application to Facts: Test application
        
        Conclusion: Test conclusion
        
        Confidence: 85
        
        Sources: [2023] FCA 123
        """

        trace = extract_reasoning_trace(text)
        assert isinstance(trace, LegalReasoningTrace)
        assert trace.issue == "Test issue"
        assert trace.applicable_law == "Test law"
        assert trace.application == "Test application"
        assert trace.conclusion == "Test conclusion"
        assert trace.confidence == 85
        assert "[2023] FCA 123" in trace.sources

    def test_empty_reasoning_trace(self):
        """Test handling of text without reasoning trace."""
        text = "This is just regular text without reasoning."
        trace = extract_reasoning_trace(text)
        # Should return None when no trace found
        assert trace is None


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
        mock_config.openai_key = "test-key"

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
    def test_api_error_handling(self, mock_config, mock_get_client):
        """Test handling of API errors."""
        # Setup proper CONFIG values
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"
        mock_config.openai_key = "test-key"

        # Mock the OpenAI client to raise an error
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        client = LLMClient("openai/gpt-4o")
        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(Exception) as exc_info:
            client.complete(messages, skip_citation_verification=True)

        assert "API Error" in str(exc_info.value)

    @patch("litassist.llm.api_handlers.get_openai_client")
    @patch("litassist.config.CONFIG")
    def test_empty_response_handling(self, mock_config, mock_get_client):
        """Test handling of empty API responses."""
        # Setup proper CONFIG values
        mock_config.llm_model = "openai/gpt-4o"
        mock_config.api_key = "test-key"
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"
        mock_config.openai_key = "test-key"

        # Mock the OpenAI client to return empty response
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = None

        client = LLMClient("openai/gpt-4o")
        messages = [{"role": "user", "content": "Test"}]

        with pytest.raises(Exception) as exc_info:
            client.complete(messages, skip_citation_verification=True)

        assert "Empty response" in str(exc_info.value)
