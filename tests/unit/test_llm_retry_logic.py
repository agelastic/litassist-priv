"""
Tests for LLMClient retry logic in _execute_api_call_with_retry.

Tests retry behavior for rate limits, 413 errors, and other edge cases.
"""

import os
from unittest.mock import Mock, patch, MagicMock
import pytest
import openai.error

from litassist.llm import LLMClient, NonRetryableAPIError, RetryableAPIError, StreamingAPIError


class TestLLMRetryLogic:
    """Test retry logic in _execute_api_call_with_retry method."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Set test environment to use no wait between retries
        os.environ["PYTEST_CURRENT_TEST"] = "test"
        
        # Create client with minimal setup
        with patch("litassist.llm.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_key"
            self.client = LLMClient("openai/gpt-4")
    
    def teardown_method(self):
        """Clean up after tests."""
        # PYTEST_CURRENT_TEST is managed by pytest itself
        pass
    
    @patch("openai.ChatCompletion.create")
    def test_retry_on_rate_limit_error(self, mock_create):
        """Test that RateLimitError triggers retries and eventually succeeds."""
        # Create a proper response object
        success_response = Mock()
        success_response.choices = [Mock()]
        success_response.choices[0].message = Mock(content="Success")
        success_response.choices[0].error = None
        
        # First 2 calls raise RateLimitError, third succeeds
        mock_create.side_effect = [
            openai.error.RateLimitError("Rate limit exceeded"),
            openai.error.RateLimitError("Rate limit exceeded"),
            success_response,
        ]
        
        # Execute the call
        result = self.client._execute_api_call_with_retry(
            "openai/gpt-4", 
            [{"role": "user", "content": "test"}],
            {}
        )
        
        # Verify it succeeded after retries
        assert result.choices[0].message.content == "Success"
        # Verify it was called 3 times
        assert mock_create.call_count == 3
    
    @patch("openai.ChatCompletion.create")
    def test_retry_on_api_connection_error(self, mock_create):
        """Test that APIConnectionError triggers retries."""
        # Create a proper response object
        success_response = Mock()
        success_response.choices = [Mock()]
        success_response.choices[0].message = Mock(content="Success")
        success_response.choices[0].error = None
        
        # First call raises APIConnectionError, second succeeds
        mock_create.side_effect = [
            openai.error.APIConnectionError("Connection failed"),
            success_response,
        ]
        
        result = self.client._execute_api_call_with_retry(
            "openai/gpt-4",
            [{"role": "user", "content": "test"}],
            {}
        )
        
        assert result.choices[0].message.content == "Success"
        assert mock_create.call_count == 2
    
    @patch("openai.ChatCompletion.create")
    def test_no_retry_on_413_error(self, mock_create):
        """Test that 413 errors raise NonRetryableAPIError immediately."""
        # Create an error that looks like a 413
        error = openai.error.InvalidRequestError("413 Request Entity Too Large", param=None)
        mock_create.side_effect = error
        
        # Should raise NonRetryableAPIError without retrying
        with pytest.raises(NonRetryableAPIError) as exc_info:
            self.client._execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {}
            )
        
        assert "Request too large" in str(exc_info.value)
        # Should only be called once (no retries)
        assert mock_create.call_count == 1
    
    @patch("openai.ChatCompletion.create")
    def test_no_retry_on_payload_too_large(self, mock_create):
        """Test that 'payload too large' errors raise NonRetryableAPIError."""
        error = Exception("Payload too large for model")
        mock_create.side_effect = error
        
        with pytest.raises(NonRetryableAPIError) as exc_info:
            self.client._execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {}
            )
        
        assert "Request too large" in str(exc_info.value)
        assert mock_create.call_count == 1
    
    @patch("openai.ChatCompletion.create")
    def test_retry_on_streaming_error(self, mock_create):
        """Test that streaming errors trigger retries."""
        # Create a proper response object
        success_response = Mock()
        success_response.choices = [Mock()]
        success_response.choices[0].message = Mock(content="Success")
        success_response.choices[0].error = None
        
        # First call raises streaming error, second succeeds
        mock_create.side_effect = [
            Exception("Error processing stream"),
            success_response,
        ]
        
        result = self.client._execute_api_call_with_retry(
            "openai/gpt-4",
            [{"role": "user", "content": "test"}],
            {}
        )
        
        assert result.choices[0].message.content == "Success"
        assert mock_create.call_count == 2
    
    @patch("openai.ChatCompletion.create")
    def test_retry_on_overloaded_response(self, mock_create):
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
        
        mock_create.side_effect = [
            error_response,
            success_response,
        ]
        
        result = self.client._execute_api_call_with_retry(
            "openai/gpt-4",
            [{"role": "user", "content": "test"}],
            {}
        )
        
        assert result.choices[0].message.content == "Success"
        assert mock_create.call_count == 2
    
    @patch("openai.ChatCompletion.create")
    def test_max_retries_exceeded(self, mock_create):
        """Test that retries stop after max attempts (5)."""
        # Always raise RateLimitError
        mock_create.side_effect = openai.error.RateLimitError("Rate limit exceeded")
        
        # Should raise the error after 5 attempts
        with pytest.raises(openai.error.RateLimitError):
            self.client._execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {}
            )
        
        # Should be called exactly 5 times
        assert mock_create.call_count == 5
    
    @patch("openai.ChatCompletion.create")
    def test_non_retryable_error_propagates(self, mock_create):
        """Test that non-retryable errors are raised immediately."""
        # Raise a generic exception
        error = ValueError("Invalid parameter")
        mock_create.side_effect = error
        
        with pytest.raises(ValueError) as exc_info:
            self.client._execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {}
            )
        
        assert "Invalid parameter" in str(exc_info.value)
        assert mock_create.call_count == 1
    
    @patch("openai.ChatCompletion.create")
    def test_413_with_response_object(self, mock_create):
        """Test 413 detection when error has response.status_code."""
        # Create error with response object
        error = Exception("Request failed")
        error.response = Mock(status_code=413)
        mock_create.side_effect = error
        
        with pytest.raises(NonRetryableAPIError) as exc_info:
            self.client._execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {}
            )
        
        assert "HTTP 413" in str(exc_info.value)
        assert mock_create.call_count == 1
    
    @patch("openai.ChatCompletion.create")
    def test_413_with_error_dict(self, mock_create):
        """Test 413 detection when error has error dict with code."""
        # Create error with error dict
        error = Exception("Request failed")
        error.error = {"code": 413, "message": "Too large"}
        mock_create.side_effect = error
        
        with pytest.raises(NonRetryableAPIError) as exc_info:
            self.client._execute_api_call_with_retry(
                "openai/gpt-4",
                [{"role": "user", "content": "test"}],
                {}
            )
        
        assert "API Error 413" in str(exc_info.value)
        assert mock_create.call_count == 1