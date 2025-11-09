"""
Tests for the --heavy flag functionality across commands.

This module tests that the --heavy flag properly enables verification-heavy mode
(gpt-5-pro instead of gpt-5).
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from litassist.commands.extractfacts import extractfacts


class TestHeavyFlag:
    """Test suite for --heavy flag functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.mock_client = Mock()
        self.mock_client.complete.return_value = ("Test content", {"total_tokens": 100})
        self.mock_client.verify.return_value = ("Verified content", "mock-model")
        self.mock_client.validate_citations.return_value = []
        self.mock_client.model = "test-model"

    @patch("litassist.commands.extractfacts.document_reader.get_config")
    @patch("litassist.commands.extractfacts.core.LLMClientFactory.for_command")
    @patch("litassist.commands.extractfacts.core.verify_content_if_needed")
    @patch("litassist.commands.extractfacts.core.save_command_output")
    @patch("litassist.commands.extractfacts.single_extractor.PROMPTS")
    def test_extractfacts_with_heavy_passes_flag(
        self, mock_prompts, mock_save, mock_verify, mock_factory, mock_config
    ):
        """Test that extractfacts with --heavy passes heavy=True to verification."""
        # Setup mocks
        mock_config_obj = Mock()
        mock_config_obj.max_chars = 10000
        mock_config.return_value = mock_config_obj
        mock_factory.return_value = self.mock_client
        mock_prompts.get.return_value = "Test prompt"
        mock_prompts.get_format_template.return_value = "Format template"
        mock_prompts.get_system_prompt.return_value = "System prompt"
        mock_save.return_value = "output.txt"
        mock_verify.return_value = ("Content", None)

        # Create test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document content")
            test_file = f.name

        try:
            # Run command with --heavy
            result = self.runner.invoke(extractfacts, [test_file, "--heavy"])

            # Verify command succeeded
            assert result.exit_code == 0

            # Verify that verify_content_if_needed was called with heavy=True
            mock_verify.assert_called_once()
            assert mock_verify.call_args.kwargs.get("heavy") is True

        finally:
            Path(test_file).unlink()

    @patch("litassist.commands.extractfacts.document_reader.get_config")
    @patch("litassist.commands.extractfacts.core.LLMClientFactory.for_command")
    @patch("litassist.commands.extractfacts.core.verify_content_if_needed")
    @patch("litassist.commands.extractfacts.core.save_command_output")
    @patch("litassist.commands.extractfacts.single_extractor.PROMPTS")
    def test_extractfacts_without_heavy_uses_standard(
        self, mock_prompts, mock_save, mock_verify, mock_factory, mock_config
    ):
        """Test that extractfacts without --heavy uses standard verification."""
        # Setup mocks
        mock_config_obj = Mock()
        mock_config_obj.max_chars = 10000
        mock_config.return_value = mock_config_obj
        mock_factory.return_value = self.mock_client
        mock_prompts.get.return_value = "Test prompt"
        mock_prompts.get_format_template.return_value = "Format template"
        mock_prompts.get_system_prompt.return_value = "System prompt"
        mock_save.return_value = "output.txt"
        mock_verify.return_value = ("Verified content", None)

        # Create test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document content")
            test_file = f.name

        try:
            # Run command without --heavy
            result = self.runner.invoke(extractfacts, [test_file])

            # Verify command succeeded
            assert result.exit_code == 0

            # Verify that verify_content_if_needed was called with heavy=False (default)
            mock_verify.assert_called_once()
            assert mock_verify.call_args.kwargs.get("heavy", False) is False

        finally:
            Path(test_file).unlink()


class TestVerificationAlwaysEnabled:
    """Test that verification is always enabled (no --noverify anymore)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.mock_client = Mock()
        self.mock_client.complete.return_value = ("Content", {"tokens": 100})
        self.mock_client.verify.return_value = ("Content", "model")
        self.mock_client.validate_citations.return_value = []

    @patch("litassist.commands.extractfacts.document_reader.get_config")
    @patch("litassist.commands.extractfacts.core.LLMClientFactory.for_command")
    @patch("litassist.commands.extractfacts.core.verify_content_if_needed")
    @patch("litassist.commands.extractfacts.core.save_command_output")
    @patch("litassist.commands.extractfacts.single_extractor.PROMPTS")
    def test_extractfacts_always_verifies(
        self, mock_prompts, mock_save, mock_verify, mock_factory, mock_config
    ):
        """Test that extractfacts always uses verification (no way to skip)."""
        mock_config_obj = Mock()
        mock_config_obj.max_chars = 10000
        mock_config.return_value = mock_config_obj
        mock_factory.return_value = self.mock_client
        mock_prompts.get.return_value = "Test"
        mock_prompts.get_format_template.return_value = "Format"
        mock_prompts.get_system_prompt.return_value = "System"
        mock_save.return_value = "out.txt"
        mock_verify.return_value = ("Content", None)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Content")
            test_file = f.name

        try:
            result = self.runner.invoke(extractfacts, [test_file])
            assert result.exit_code == 0

            # Verification is mandatory
            mock_verify.assert_called_once()

        finally:
            Path(test_file).unlink()


# Test markers
pytestmark = pytest.mark.unit
