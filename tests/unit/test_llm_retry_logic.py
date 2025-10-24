"""
Tests for LLMClient retry logic in _execute_api_call_with_retry.

Tests retry behavior for rate limits, 413 errors, and other edge cases.
"""

import os
from unittest.mock import Mock, patch, MagicMock
import pytest
from openai import RateLimitError, APIConnectionError, BadRequestError

from litassist.llm.client import LLMClient
from litassist.llm.api_handlers import NonRetryableAPIError, execute_api_call_with_retry


class TestLLMRetryLogic:
    """Test retry logic in _execute_api_call_with_retry method."""

    def setup_method(self):
        """Set up test fixtures."""
        # Set test environment to use no wait between retries
        os.environ["PYTEST_CURRENT_TEST"] = "test"

        # Create client with minimal setup
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_key"
            mock_config.or_base = "https://openrouter.ai/api/v1"
            mock_config.or_key = "test_key"
            self.client = LLMClient("openai/gpt-4")

    def teardown_method(self):
        """Clean up after tests."""
        # PYTEST_CURRENT_TEST is managed by pytest itself
        pass

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_retry_on_rate_limit_error(self, mock_get_client):
        """Test that RateLimitError triggers retries and eventually succeeds."""
        # Create a proper response object
        success_response = Mock()
        success_response.choices = [Mock()]
        success_response.choices[0].message = Mock(content="Success")
        success_response.choices[0].error = None

        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # First 2 calls raise RateLimitError, third succeeds
        mock_client.chat.completions.create.side_effect = [
            RateLimitError(
                message="Rate limit exceeded",
                response=Mock(status_code=429),
                body={"error": {"message": "Rate limit exceeded"}},
            ),
            RateLimitError(
                message="Rate limit exceeded",
                response=Mock(status_code=429),
                body={"error": {"message": "Rate limit exceeded"}},
            ),
            success_response,
        ]

        # Execute the call
        result = execute_api_call_with_retry(
            "openai/gpt-4",
            [{"role": "user", "content": "test"}],
            {},
            get_openai_client_func=mock_get_client,
        )

        # Verify it succeeded after retries
        assert result.choices[0].message.content == "Success"
        # Verify it was called 3 times
        assert mock_client.chat.completions.create.call_count == 3

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_retry_on_api_connection_error(self, mock_get_client):
        """Test that APIConnectionError triggers retries."""
        # Create a proper response object
        success_response = Mock()
        success_response.choices = [Mock()]
        success_response.choices[0].message = Mock(content="Success")
        success_response.choices[0].error = None

        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # First call raises APIConnectionError, second succeeds
        mock_client.chat.completions.create.side_effect = [
            APIConnectionError(request=Mock()),
            success_response,
        ]

        result = execute_api_call_with_retry(
            "openai/gpt-4",
            [{"role": "user", "content": "test"}],
            {},
            get_openai_client_func=mock_get_client,
        )

        assert result.choices[0].message.content == "Success"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_no_retry_on_413_error(self, mock_get_client):
        """Test that 413 errors raise NonRetryableAPIError immediately."""
        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create an error that looks like a 413
        error = BadRequestError(
            message="413 Request Entity Too Large",
            response=Mock(status_code=413),
            body={"error": {"message": "413 Request Entity Too Large"}},
        )
        mock_client.chat.completions.create.side_effect = error

        # Should raise NonRetryableAPIError without retrying
        with pytest.raises(NonRetryableAPIError) as exc_info:
            execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {},
                get_openai_client_func=mock_get_client,
            )

        assert "Request too large" in str(exc_info.value)
        # Should only be called once (no retries)
        assert mock_client.chat.completions.create.call_count == 1

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_no_retry_on_payload_too_large(self, mock_get_client):
        """Test that 'payload too large' errors raise NonRetryableAPIError."""
        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        error = Exception("Payload too large for model")
        mock_client.chat.completions.create.side_effect = error

        with pytest.raises(NonRetryableAPIError) as exc_info:
            execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {},
                get_openai_client_func=mock_get_client,
            )

        assert "Request too large" in str(exc_info.value)
        assert mock_client.chat.completions.create.call_count == 1

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_retry_on_streaming_error(self, mock_get_client):
        """Test that streaming errors trigger retries."""
        # Create a proper response object
        success_response = Mock()
        success_response.choices = [Mock()]
        success_response.choices[0].message = Mock(content="Success")
        success_response.choices[0].error = None

        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # First call raises streaming error, second succeeds
        mock_client.chat.completions.create.side_effect = [
            Exception("Error processing stream"),
            success_response,
        ]

        result = execute_api_call_with_retry(
            "openai/gpt-4",
            [{"role": "user", "content": "test"}],
            {},
            get_openai_client_func=mock_get_client,
        )

        assert result.choices[0].message.content == "Success"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_retry_on_overloaded_response(self, mock_get_client):
        """Test retry when API returns overloaded error in response."""
        # Create a response with error in choices
        error_response = Mock()
        error_response.choices = [Mock()]
        error_response.choices[0].error = {"message": "Model is overloaded"}

        # Create a proper response object for the success case
        success_response = Mock()
        success_response.choices = [Mock()]
        success_response.choices[0].message = Mock(content="Success")
        success_response.choices[0].error = None

        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_client.chat.completions.create.side_effect = [
            error_response,
            success_response,
        ]

        result = execute_api_call_with_retry(
            "openai/gpt-4",
            [{"role": "user", "content": "test"}],
            {},
            get_openai_client_func=mock_get_client,
        )

        assert result.choices[0].message.content == "Success"
        assert mock_client.chat.completions.create.call_count == 2

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_max_retries_exceeded(self, mock_get_client):
        """Test that retries stop after max attempts (5)."""
        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Always raise RateLimitError
        mock_client.chat.completions.create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=Mock(status_code=429),
            body={"error": {"message": "Rate limit exceeded"}},
        )

        # Should raise the error after 5 attempts
        with pytest.raises(RateLimitError):
            execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {},
                get_openai_client_func=mock_get_client,
            )

        # Should be called exactly 5 times
        assert mock_client.chat.completions.create.call_count == 5

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_non_retryable_error_propagates(self, mock_get_client):
        """Test that non-retryable errors are raised immediately."""
        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Raise a generic exception
        error = ValueError("Invalid parameter")
        mock_client.chat.completions.create.side_effect = error

        with pytest.raises(ValueError) as exc_info:
            execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {},
                get_openai_client_func=mock_get_client,
            )

        assert "Invalid parameter" in str(exc_info.value)
        assert mock_client.chat.completions.create.call_count == 1

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_413_with_response_object(self, mock_get_client):
        """Test 413 detection when error has response.status_code."""
        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create error with response object
        error = Exception("Request failed")
        error.response = Mock(status_code=413)
        mock_client.chat.completions.create.side_effect = error

        with pytest.raises(NonRetryableAPIError) as exc_info:
            execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {},
                get_openai_client_func=mock_get_client,
            )

        assert "413" in str(exc_info.value) or "Request too large" in str(
            exc_info.value
        )
        assert mock_client.chat.completions.create.call_count == 1

    @patch("litassist.llm.api_handlers.get_openai_client")
    def test_413_with_error_dict(self, mock_get_client):
        """Test 413 detection when error has error dict with code."""
        # Mock the client and its chat.completions.create method
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Create error with error dict
        error = Exception("Request failed")
        error.error = {"code": 413, "message": "Too large"}
        mock_client.chat.completions.create.side_effect = error

        with pytest.raises(NonRetryableAPIError) as exc_info:
            execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {},
                get_openai_client_func=mock_get_client,
            )

        assert "413" in str(exc_info.value) or "Request too large" in str(
            exc_info.value
        )
        assert mock_client.chat.completions.create.call_count == 1
