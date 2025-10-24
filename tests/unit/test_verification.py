"""Tests for the enhanced verification system."""

from unittest.mock import Mock, patch, MagicMock
from litassist.llm.client import LLMClient


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

    @patch("litassist.logging.save_log")
    @patch("litassist.llm.api_handlers.get_openai_client")
    @patch("litassist.config.CONFIG")
    def test_verify_with_level_light(self, mock_config, mock_get_client, mock_save_log):
        """Test light verification level."""
        # Setup proper CONFIG values
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"
        mock_config.openai_key = "test-key"

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Corrected text")
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

        result = self.client.verify_with_level("test content", "light")
        if isinstance(result, tuple):
            result = result[0]

        assert result == "Corrected text"
        # Should use light verification prompts
        call_args = mock_client.chat.completions.create.call_args[1]["messages"]
        assert "legal" in call_args[0]["content"].lower()

    @patch("litassist.logging.save_log")
    @patch("litassist.llm.api_handlers.get_openai_client")
    @patch("litassist.config.CONFIG")
    def test_verify_with_level_heavy(self, mock_config, mock_get_client, mock_save_log):
        """Test heavy verification level."""
        # Setup proper CONFIG values
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test-key"
        mock_config.openai_key = "test-key"

        # Mock the OpenAI client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock(content="Thoroughly reviewed content")
        mock_response.choices[0].error = None
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock(
            prompt_tokens=200,
            completion_tokens=100,
            total_tokens=300,
            model_dump=lambda: {
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300,
            },
        )
        mock_client.chat.completions.create.return_value = mock_response

        result = self.client.verify_with_level("test content", "heavy")
        if isinstance(result, tuple):
            result = result[0]

        assert result == "Thoroughly reviewed content"
        # Should use heavy verification prompts
        call_args = mock_client.chat.completions.create.call_args[1]["messages"]
        assert "legal accuracy" in call_args[0]["content"]

    def test_command_context_tracking(self):
        """Test command context is properly tracked."""
        self.client.command_context = "extractfacts"
        assert self.client.command_context == "extractfacts"


class TestCommandVerificationIntegration:
    """Test verification integration in commands."""

    def test_extractfacts_command_sets_auto_verify(self):
        """Test that extractfacts command forces verification to True."""
        from litassist.llm.client import LLMClient

        # Create a client like extractfacts does
        client = LLMClient("anthropic/claude-3-sonnet", temperature=0, top_p=0.15)
        client.command_context = "extractfacts"

        # extractfacts should always auto-verify regardless of input
        content = "Basic content without risk factors"
        assert client.should_auto_verify(content, "extractfacts") is True

    def test_brainstorm_grok_client_auto_verifies(self):
        """Test that Grok models in brainstorm always auto-verify."""
        from litassist.llm.client import LLMClient

        # Create a Grok client like brainstorm does
        client = LLMClient("x-ai/grok-3", temperature=0.9, max_tokens=4000)
        client.command_context = "brainstorm"

        content = "Creative thinking content"
        assert client.should_auto_verify(content, "brainstorm") is True

    def test_strategy_command_auto_verifies(self):
        """Test that strategy command always auto-verifies."""
        from litassist.llm.client import LLMClient

        # Create client like strategy command does
        client = LLMClient("openai/o3-pro", temperature=0.3)
        client.command_context = "strategy"

        content = "Strategic analysis content"
        assert client.should_auto_verify(content, "strategy") is True

    def test_lookup_command_no_auto_verify(self):
        """Test that lookup command doesn't auto-verify basic content."""
        from litassist.llm.client import LLMClient

        # Create client like lookup command does
        client = LLMClient("google/gemini-2.5-pro", temperature=0.3)
        client.command_context = "lookup"

        # Basic lookup content shouldn't auto-verify
        content = "Simple legal search results"
        assert client.should_auto_verify(content, "lookup") is False

        # Content with citations should auto-verify
        content_with_citation = "In [2023] HCA 5, the court held..."
        assert client.should_auto_verify(content_with_citation, "lookup") is True


class TestHighRiskContentDetection:
    """Test detection of high-risk content requiring verification."""

    def test_detect_high_percentage_claims(self):
        """Test detection of high percentage claims."""
        from litassist.llm.client import LLMClient

        client = LLMClient("test/model")
        high_risk_content = [
            "The success rate is 95%",
            "There's a 80% chance of winning",
            "probability of failure is 10%",
        ]

        for content in high_risk_content:
            assert client.should_auto_verify(content) is True

    def test_detect_strong_legal_language(self):
        """Test detection of strong legal language."""
        from litassist.llm.client import LLMClient

        client = LLMClient("test/model")
        strong_language = [
            'The court "must" grant the order',
            'The defendant "will" be liable',
            'The party "cannot" appeal this decision',
            'The judge "will" rule in our favor',
        ]

        for content in strong_language:
            assert client.should_auto_verify(content) is True

    def test_detect_citations(self):
        """Test detection of legal citations."""
        from litassist.llm.client import LLMClient

        client = LLMClient("test/model")
        citations = [
            "[2023] HCA 15",
            "[2022] FCA 100",
            "Smith v Jones [2021] NSWSC 50",
            "Re Application [2020] VCC 123",
        ]

        for content in citations:
            assert client.should_auto_verify(content) is True

    def test_safe_content_no_verification(self):
        """Test that safe content doesn't trigger verification."""
        from litassist.llm.client import LLMClient

        client = LLMClient("test/model")
        safe_content = [
            "The parties met to discuss the matter",
            "Documentation was provided to the court",
            "The hearing is scheduled for next week",
            "Legal advice should be sought",
        ]

        for content in safe_content:
            # Without a high-risk command context, shouldn't auto-verify
            assert client.should_auto_verify(content, "digest") is False
