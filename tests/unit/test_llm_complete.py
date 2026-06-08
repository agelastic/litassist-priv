"""
Tests for LLMClient.complete method functionality.

Tests cover:
- System message merging for models without system support
- Heartbeat and timed decorator execution
- Response handling and token counting
- Error handling scenarios
"""

from unittest.mock import Mock, patch
from litassist.llm.client import LLMClient


class TestLLMClientComplete:
    """Test the LLMClient.complete method with mocked API calls."""

    @patch("litassist.config.CONFIG")
    @patch("litassist.llm.client.execute_api_call_with_retry")
    def test_complete_basic_success(self, mock_execute, mock_config):
        """Test basic complete call with successful response."""
        # Setup config
        mock_config.or_key = "test_key"

        # Setup mock response - ensure no error attribute
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Test response")
        mock_response.choices[0].finish_reason = "stop"
        # Explicitly set error to None to avoid error handling
        mock_response.choices[0].error = None
        mock_response.usage = Mock(
            total_tokens=100,
            prompt_tokens=50,
            completion_tokens=50,
            model_dump=lambda: {
                "total_tokens": 100,
                "prompt_tokens": 50,
                "completion_tokens": 50,
            },
        )

        mock_execute.return_value = mock_response

        # Create client
        client = LLMClient(model="gpt-4", temperature=0.7)

        # Call complete
        messages = [{"role": "user", "content": "Hello"}]
        response, stats = client.complete(messages)

        # Verify response
        assert response == "Test response"
        assert stats["total_tokens"] == 100

        # Verify API was called
        assert mock_execute.called

    @patch("litassist.config.CONFIG")
    @patch("litassist.llm.client.execute_api_call_with_retry")
    def test_complete_system_message_merging_no_system_support(
        self, mock_execute, mock_config
    ):
        """Test system message merging for models without system support."""
        mock_config.or_key = "test_key"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Response")
        mock_response.choices[0].finish_reason = "stop"
        mock_response.choices[0].error = None
        mock_response.usage = Mock(
            total_tokens=50,
            prompt_tokens=25,
            completion_tokens=25,
            model_dump=lambda: {
                "total_tokens": 50,
                "prompt_tokens": 25,
                "completion_tokens": 25,
            },
        )

        mock_execute.return_value = mock_response

        # Create client with model that doesn't support system messages
        # Need to use the correct model name pattern for openai_reasoning family
        client = LLMClient(model="openai/o1-preview", temperature=0.7)

        # Call with system message
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]

        response, stats = client.complete(messages)

        # Check that system message was merged into user message
        called_messages = mock_execute.call_args[0][1]
        assert len(called_messages) == 1
        assert called_messages[0]["role"] == "user"
        assert "You are helpful" in called_messages[0]["content"]
        assert "Hello" in called_messages[0]["content"]

    @patch("litassist.config.CONFIG")
    @patch("litassist.llm.client.execute_api_call_with_retry")
    def test_complete_system_message_preserved_with_support(
        self, mock_execute, mock_config
    ):
        """Test system message preserved for models with system support."""
        mock_config.or_key = "test_key"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Response")
        mock_response.choices[0].finish_reason = "stop"
        mock_response.choices[0].error = None
        mock_response.usage = Mock(
            total_tokens=50,
            prompt_tokens=25,
            completion_tokens=25,
            model_dump=lambda: {
                "total_tokens": 50,
                "prompt_tokens": 25,
                "completion_tokens": 25,
            },
        )

        mock_execute.return_value = mock_response

        # Create client with model that supports system messages
        client = LLMClient(model="gpt-4", temperature=0.7)

        # Call with system message
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
        ]

        response, stats = client.complete(messages)

        # Check that system message was preserved with Australian law prompt prepended
        called_messages = mock_execute.call_args[0][1]
        assert len(called_messages) == 2
        assert called_messages[0]["role"] == "system"
        assert "Australian law only" in called_messages[0]["content"]
        assert "You are helpful" in called_messages[0]["content"]
        assert called_messages[1]["role"] == "user"
        assert called_messages[1]["content"] == "Hello"

    @patch("litassist.config.CONFIG")
    @patch("litassist.llm.client.execute_api_call_with_retry")
    def test_complete_user_only_injects_base_prompts_system_capable(
        self, mock_execute, mock_config
    ):
        # Regression: user-only calls on system-capable models must still receive
        # the Australian-law and anti-injection base prompts. Previously the
        # injection helper looped messages and only modified existing system
        # entries; user-only input slipped through unguarded, surfaced via
        # Chain of Verification.
        mock_config.or_key = "test_key"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Response")
        mock_response.choices[0].finish_reason = "stop"
        mock_response.choices[0].error = None
        mock_response.usage = Mock(
            total_tokens=50,
            prompt_tokens=25,
            completion_tokens=25,
            model_dump=lambda: {
                "total_tokens": 50,
                "prompt_tokens": 25,
                "completion_tokens": 25,
            },
        )
        mock_execute.return_value = mock_response

        client = LLMClient(model="gpt-4", temperature=0.7)
        messages = [{"role": "user", "content": "Generate verification questions"}]
        client.complete(messages)

        called_messages = mock_execute.call_args[0][1]
        system_payload = "\n".join(
            m.get("content", "") for m in called_messages if m.get("role") == "system"
        )
        user_payload = "\n".join(
            m.get("content", "") for m in called_messages if m.get("role") == "user"
        )
        combined = system_payload + "\n" + user_payload
        assert "Australian law only" in combined
        assert "CRITICAL ANTI-INJECTION" in combined

    @patch("litassist.config.CONFIG")
    @patch("litassist.llm.client.execute_api_call_with_retry")
    def test_complete_raises_on_length_truncation(self, mock_execute, mock_config):
        # Regression: responses with finish_reason='length' used to be treated
        # as successful completions, silently returning partial content. They
        # must now surface as an explicit error so callers do not act on
        # truncated output (e.g. an incomplete legal draft).
        import pytest

        mock_config.or_key = "test_key"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Partial truncated")
        mock_response.choices[0].finish_reason = "length"
        mock_response.choices[0].error = None
        mock_response.usage = Mock(
            total_tokens=100,
            prompt_tokens=50,
            completion_tokens=50,
            model_dump=lambda: {
                "total_tokens": 100,
                "prompt_tokens": 50,
                "completion_tokens": 50,
            },
        )
        mock_execute.return_value = mock_response

        client = LLMClient(model="gpt-4", temperature=0.7)
        with pytest.raises(Exception) as excinfo:
            client.complete([{"role": "user", "content": "Long prompt"}])
        msg = str(excinfo.value).lower()
        assert "truncat" in msg or "length" in msg, (
            f"Truncation error must mention truncation or length; got: {excinfo.value}"
        )

    @patch("litassist.config.CONFIG")
    @patch("litassist.logging.save_log")
    @patch("litassist.llm.client.execute_api_call_with_retry")
    def test_complete_with_verification_enabled(
        self, mock_execute, mock_save_log, mock_config
    ):
        """Test complete with verification enabled."""
        mock_config.or_key = "test_key"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Response with [2023] FCA 123")
        mock_response.choices[0].finish_reason = "stop"
        mock_response.choices[0].error = None
        mock_response.usage = Mock(
            total_tokens=50,
            prompt_tokens=25,
            completion_tokens=25,
            model_dump=lambda: {
                "total_tokens": 50,
                "prompt_tokens": 25,
                "completion_tokens": 25,
            },
        )

        mock_execute.return_value = mock_response

        # Create client with enforce_citations
        client = LLMClient(model="gpt-4", temperature=0.7)
        client._enforce_citations = True

        with patch.object(client, "validate_and_verify_citations") as mock_verify:
            # Return tuple of (cleaned_content, issues_list, verified_bool)
            mock_verify.return_value = ("Verified response", ["warning"])

            response, stats = client.complete([{"role": "user", "content": "Test"}])

            assert response == "Verified response"
            assert mock_verify.called

    @patch("litassist.config.CONFIG")
    @patch("litassist.llm.client.execute_api_call_with_retry")
    def test_complete_empty_response_handling(self, mock_execute, mock_config):
        """Test handling of empty response content."""
        mock_config.or_key = "test_key"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="")
        mock_response.choices[0].finish_reason = "stop"
        mock_response.choices[0].error = None
        mock_response.usage = Mock(
            total_tokens=50,
            prompt_tokens=25,
            completion_tokens=25,
            model_dump=lambda: {
                "total_tokens": 50,
                "prompt_tokens": 25,
                "completion_tokens": 25,
            },
        )

        mock_execute.return_value = mock_response

        client = LLMClient(model="gpt-4")
        response, stats = client.complete([{"role": "user", "content": "Test"}])

        assert response == ""
        assert stats["total_tokens"] == 50

    @patch("litassist.config.CONFIG")
    @patch("litassist.llm.client.execute_api_call_with_retry")
    def test_complete_with_model_specific_params(self, mock_execute, mock_config):
        """Test that model-specific parameters are passed correctly."""
        mock_config.or_key = "test_key"

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Response")
        mock_response.choices[0].finish_reason = "stop"
        mock_response.choices[0].error = None
        mock_response.usage = Mock(
            total_tokens=50,
            prompt_tokens=25,
            completion_tokens=25,
            model_dump=lambda: {
                "total_tokens": 50,
                "prompt_tokens": 25,
                "completion_tokens": 25,
            },
        )

        mock_execute.return_value = mock_response

        # Test with o3-pro model that has specific parameter requirements
        client = LLMClient(
            model="openai/o3-pro",
            temperature=0.7,  # Should be ignored
            thinking_effort="high",  # Will convert to reasoning object
        )

        response, stats = client.complete([{"role": "user", "content": "Test"}])

        # Verify correct parameters were passed
        _, _, call_params = mock_execute.call_args[0]
        assert "temperature" not in call_params  # Should be filtered out
        assert "reasoning" in call_params
        assert call_params["reasoning"] == {"effort": "high"}
