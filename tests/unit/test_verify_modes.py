"""
Tests for verify_with_level modes in LLMClient.

Tests different verification modes: light (spelling only) vs heavy (full verification).
"""

from unittest.mock import Mock, patch

from litassist.llm.client import LLMClient


class TestVerifyModes:
    """Test different verification modes in verify_with_level."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create client with minimal setup
        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_key"
            self.client = LLMClient("anthropic/claude-sonnet-4")

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    def test_light_verification_mode(self, mock_for_command):
        """Test that light mode only uses spelling verification prompt."""
        # Create a mock instance that will be returned by the factory
        mock_instance = Mock()
        mock_instance.complete.return_value = (
            "Spelling check complete. All correct.",
            {"total_tokens": 100},
        )
        mock_for_command.return_value = mock_instance

        # Call verify_with_level in light mode
        result = self.client.verify_with_level(
            "This is a test text with judgement.", level="light"
        )
        if isinstance(result, tuple):
            result = result[0]

        # Check the result
        assert result == "Spelling check complete. All correct."

        # Verify LLMClientFactory was called with correct command
        mock_for_command.assert_called_once_with("verification-light")

        # Verify complete was called once
        assert mock_instance.complete.call_count == 1

        # Get the messages passed to complete
        messages = mock_instance.complete.call_args[0][0]

        # Check that it has system and user messages
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        # Verify the system message is about Australian English
        assert "Australian English" in messages[0]["content"]

        # Verify the user message contains the text to check
        assert "This is a test text with judgement." in messages[1]["content"]

        # Check that parameters were passed correctly
        kwargs = mock_instance.complete.call_args[1]
        # No hardcoded max_tokens anymore - token limits come from config
        assert kwargs.get("skip_citation_verification") is True

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    def test_heavy_verification_mode(self, mock_for_command):
        """Test that heavy mode uses full legal verification prompt."""
        # Create a mock instance
        mock_instance = Mock()
        mock_instance.complete.return_value = (
            "Comprehensive legal review complete. Found issues with citations.",
            {"total_tokens": 200},
        )
        mock_for_command.return_value = mock_instance

        # Call verify_with_level in heavy mode
        result = self.client.verify_with_level(
            "Legal text with [2024] HCA 1 citation.", level="heavy"
        )
        if isinstance(result, tuple):
            result = result[0]

        # Check the result
        assert (
            result
            == "Comprehensive legal review complete. Found issues with citations."
        )

        # Verify LLMClientFactory was called with correct command for heavy verification
        mock_for_command.assert_called_once_with("verification-heavy")

        # Verify complete was called once
        assert mock_instance.complete.call_count == 1

        # Get the messages passed to complete
        messages = mock_instance.complete.call_args[0][0]

        # Check message structure
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        # Verify the system message is about legal verification
        assert "law" in messages[0]["content"].lower()

        # Verify the user message contains the text and verification request
        assert "Legal text with [2024] HCA 1 citation." in messages[1]["content"]
        assert "legal" in messages[1]["content"].lower()
        assert (
            "citation" in messages[1]["content"].lower()
            or "accuracy" in messages[1]["content"].lower()
        )

        # Check parameters
        kwargs = mock_instance.complete.call_args[1]
        # No hardcoded max_tokens anymore - token limits come from config
        assert kwargs.get("skip_citation_verification") is True

    @patch("litassist.llm.client.LLMClient.verify")
    def test_default_verification_mode(self, mock_verify):
        """Test that unrecognized level defaults to standard verification."""
        # Mock the verify method
        mock_verify.return_value = (
            "Standard verification complete.",
            "anthropic/claude-opus-4.1",
        )

        # Call verify_with_level with invalid level
        result = self.client.verify_with_level("Test text", level="medium")

        # Check the result
        assert result == (
            "Standard verification complete.",
            "anthropic/claude-opus-4.1",
        )

        # Verify that the standard verify method was called
        mock_verify.assert_called_once_with("Test text")

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    def test_prompts_fallback(self, mock_for_command):
        """Test that prompts have proper fallbacks when PROMPTS.get fails."""
        # Create a mock instance
        mock_instance = Mock()
        mock_instance.complete.return_value = ("Verified", {"total_tokens": 50})
        mock_for_command.return_value = mock_instance

        # Mock PROMPTS to raise KeyError
        with patch("litassist.prompts.PROMPTS") as mock_prompts:
            mock_prompts.get.side_effect = KeyError("Not found")

            # Call light verification
            result = self.client.verify_with_level("colour vs color", level="light")
            if isinstance(result, tuple):
                result = result[0]

            # Should still work with fallback prompt
            assert result == "Verified"

            # Check the fallback prompt was used
            messages = mock_instance.complete.call_args[0][0]
            assert (
                "Check only for Australian English spelling" in messages[0]["content"]
            )

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.llm.verification.get_config")
    def test_token_limits_disabled(self, mock_get_config, mock_for_command):
        """Test behavior when token limits are disabled."""
        # Configure mock with token limits disabled
        mock_config = Mock()
        mock_config.use_token_limits = False
        mock_get_config.return_value = mock_config

        # Create a mock instance
        mock_instance = Mock()
        mock_instance.complete.return_value = ("Verified", {"total_tokens": 100})
        mock_for_command.return_value = mock_instance

        # Test both modes
        for level in ["light", "heavy"]:
            mock_instance.complete.reset_mock()

            self.client.verify_with_level("Test text", level=level)

            # Check that max_tokens was NOT set
            kwargs = mock_instance.complete.call_args[1]
            assert "max_tokens" not in kwargs
            # No hardcoded temperature/top_p anymore - let factory handle it

    @patch("litassist.llm.client.LLMClient.verify")
    def test_unknown_level_calls_standard_verify(self, mock_verify):
        """Test that unknown levels call the standard verify method."""
        mock_verify.return_value = (
            "Standard verification",
            "anthropic/claude-opus-4.1",
        )

        # Test various unknown levels
        for level in ["unknown", "standard", None, "", "xyz"]:
            mock_verify.reset_mock()

            result = self.client.verify_with_level("Test", level=level)

            assert result == ("Standard verification", "anthropic/claude-opus-4.1")
            mock_verify.assert_called_once_with("Test")
