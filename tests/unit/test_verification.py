"""Tests for the enhanced verification system."""

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
