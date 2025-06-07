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
        grok_client = LLMClient("x-ai/grok-3-beta", temperature=0.9)
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

    def test_validate_citations_suspicious_year(self):
        """Test citation validation catches anachronistic citations."""
        content = "In [1850] HCA 5, the court decided..."
        issues = self.client.validate_citations(content)
        assert len(issues) > 0
        # Check for anachronistic citation (HCA established 1903)
        anachronistic_issues = [i for i in issues if "ANACHRONISTIC CITATION" in i]
        assert len(anachronistic_issues) > 0

    def test_validate_citations_future_year(self):
        """Test citation validation catches future years."""
        content = "In [2030] HCA 5, the court will decide..."
        issues = self.client.validate_citations(content)
        assert len(issues) > 0
        # Check for future year citation
        future_issues = [i for i in issues if "FUTURE CITATION" in i]
        assert len(future_issues) > 0

    def test_validate_citations_fabricated_names(self):
        """Test citation validation catches generic case names."""
        content = "In Smith v Jones [2020] HCA 999..."
        issues = self.client.validate_citations(content)
        assert len(issues) > 0
        # Should flag either generic case name or high citation number
        generic_issues = [
            i
            for i in issues
            if "GENERIC CASE NAME" in i or "EXCESSIVE CITATION NUMBER" in i
        ]
        assert len(generic_issues) > 0

    def test_validate_citations_valid_citation(self):
        """Test citation validation passes valid citations."""
        content = "In Commonwealth v Tasmania [2020] HCA 5..."
        issues = self.client.validate_citations(content)
        # Should not flag legitimate case names
        fabricated_issues = [i for i in issues if "fabricated" in i]
        assert len(fabricated_issues) == 0

    @patch("openai.ChatCompletion.create")
    def test_verify_with_level_light(self, mock_create):
        """Test light verification level."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Corrected text"
        # Mock the usage attribute with proper data
        mock_usage = Mock()
        mock_usage._asdict = Mock(
            return_value={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            }
        )
        mock_response.usage = mock_usage
        mock_create.return_value = mock_response

        result = self.client.verify_with_level("test content", "light")

        assert result == "Corrected text"
        # Should use light verification prompts
        call_args = mock_create.call_args[1]["messages"]
        assert "Australian English spelling" in call_args[0]["content"]

    @patch("openai.ChatCompletion.create")
    def test_verify_with_level_heavy(self, mock_create):
        """Test heavy verification level."""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Thoroughly reviewed content"
        # Mock the usage attribute with proper data
        mock_usage = Mock()
        mock_usage._asdict = Mock(
            return_value={
                "prompt_tokens": 200,
                "completion_tokens": 100,
                "total_tokens": 300,
            }
        )
        mock_response.usage = mock_usage
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
        grok_client = LLMClient("x-ai/grok-3-beta", temperature=0.9, top_p=0.95)
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
