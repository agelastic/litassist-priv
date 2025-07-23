"""Tests for the enhanced verification system."""

from unittest.mock import Mock, patch
from litassist.llm import LLMClient


class TestLLMClientVerification:
    """Test LLM client verification enhancements."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = LLMClient("test/model", temperature=0.5)

    def test_should_auto_verify_extractfacts_command(self):
        """Test auto-verification for extractfacts command."""
        content = "Some basic content"
        assert self.client.should_auto_verify(content, "extractfacts") is True

    def test_should_auto_verify_strategy_command(self):
        """Test auto-verification for strategy command."""
        content = "Some basic content"
        assert self.client.should_auto_verify(content, "strategy") is True

    def test_should_auto_verify_grok_model(self):
        """Test auto-verification for Grok models."""
        grok_client = LLMClient("x-ai/grok-3", temperature=0.9)
        content = "Some basic content"
        assert grok_client.should_auto_verify(content, "brainstorm") is True

    def test_should_auto_verify_citations(self):
        """Test auto-verification for content with citations."""
        content = "In [2020] HCA 5, the court held..."
        assert self.client.should_auto_verify(content) is True

    def test_should_auto_verify_percentages(self):
        """Test auto-verification for content with percentages."""
        content = "The probability of success is 75%"
        assert self.client.should_auto_verify(content) is True

    def test_should_auto_verify_strong_conclusions(self):
        """Test auto-verification for strong legal conclusions."""
        content = 'The defendant "must" comply with the order'
        assert self.client.should_auto_verify(content) is True

    def test_should_not_auto_verify_basic_content(self):
        """Test no auto-verification for basic content."""
        content = "This is a simple summary of events"
        assert self.client.should_auto_verify(content, "digest") is False



    @patch("litassist.utils.save_log")
    @patch("openai.ChatCompletion.create")
    def test_verify_with_level_light(self, mock_create, mock_save_log):
        """Test light verification level."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Corrected text"
        mock_response.choices[0].error = (
            None  # Explicitly set error to None for success case
        )
        mock_response.choices[0].finish_reason = "stop"  # Set proper finish reason
        # Create a dict-like object that's JSON serializable
        mock_response.usage = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }
        mock_create.return_value = mock_response

        result = self.client.verify_with_level("test content", "light")

        assert result == "Corrected text"
        # Should use light verification prompts
        call_args = mock_create.call_args[1]["messages"]
        assert "Australian English spelling" in call_args[0]["content"]

    @patch("litassist.utils.save_log")
    @patch("openai.ChatCompletion.create")
    def test_verify_with_level_heavy(self, mock_create, mock_save_log):
        """Test heavy verification level."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Thoroughly reviewed content"
        mock_response.choices[0].error = (
            None  # Explicitly set error to None for success case
        )
        mock_response.choices[0].finish_reason = "stop"  # Set proper finish reason
        # Create a dict-like object that's JSON serializable
        mock_response.usage = {
            "prompt_tokens": 200,
            "completion_tokens": 100,
            "total_tokens": 300,
        }
        mock_create.return_value = mock_response

        result = self.client.verify_with_level("test content", "heavy")

        assert result == "Thoroughly reviewed content"
        # Should use heavy verification prompts
        call_args = mock_create.call_args[1]["messages"]
        assert "legal accuracy" in call_args[0]["content"]

    def test_command_context_tracking(self):
        """Test command context is properly tracked."""
        self.client.command_context = "extractfacts"
        assert self.client.command_context == "extractfacts"


class TestCommandVerificationIntegration:
    """Test verification integration in commands."""

    def test_extractfacts_command_sets_auto_verify(self):
        """Test that extractfacts command forces verification to True."""
        from litassist.llm import LLMClient

        # Create a client like extractfacts does
        client = LLMClient("anthropic/claude-3-sonnet", temperature=0, top_p=0.15)
        client.command_context = "extractfacts"

        # extractfacts should always auto-verify regardless of input
        content = "Basic content without risk factors"
        assert client.should_auto_verify(content, "extractfacts") is True

    def test_brainstorm_grok_client_auto_verifies(self):
        """Test that Grok clients auto-verify in brainstorm."""
        from litassist.llm import LLMClient

        # Create a Grok client like brainstorm does
        grok_client = LLMClient("x-ai/grok-3", temperature=0.9, top_p=0.95)
        grok_client.command_context = "brainstorm"

        # Grok should auto-verify even basic content
        content = "Basic brainstorming content"
        assert grok_client.should_auto_verify(content, "brainstorm") is True

    def test_strategy_command_sets_auto_verify(self):
        """Test that strategy command forces verification to True."""
        from litassist.llm import LLMClient

        # Create a client like strategy does
        client = LLMClient("openai/gpt-4o", temperature=0.2, top_p=0.9)
        client.command_context = "strategy"

        # strategy should always auto-verify regardless of input
        content = "Basic strategic content"
        assert client.should_auto_verify(content, "strategy") is True
