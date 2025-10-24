"""
Tests for the --noverify flag functionality across commands.

This module tests that the --noverify flag properly skips standard verification.
Note: CoVe has moved to standalone command 'verify-cove', so CoVe-related tests are skipped.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from litassist.commands.draft.core import draft
from litassist.commands.extractfacts import extractfacts
from litassist.commands.strategy import strategy


class TestNoVerifyFlag:
    """Test suite for --noverify flag functionality."""

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
    def test_extractfacts_with_noverify_skips_verification(
        self, mock_prompts, mock_save, mock_verify, mock_factory, mock_config
    ):
        """Test that extractfacts with --noverify skips standard verification."""
        # Setup mocks
        mock_config_obj = Mock()
        mock_config_obj.max_chars = 10000  # Set as integer
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
            # Run command with --noverify
            result = self.runner.invoke(extractfacts, [test_file, "--noverify"])

            # Verify command succeeded
            assert result.exit_code == 0

            # Verify that verify_content_if_needed was NOT called when --noverify is set
            mock_verify.assert_not_called()

        finally:
            Path(test_file).unlink()

    @patch("litassist.commands.extractfacts.document_reader.get_config")
    @patch("litassist.commands.extractfacts.core.LLMClientFactory.for_command")
    @patch("litassist.commands.extractfacts.core.verify_content_if_needed")
    @patch("litassist.commands.extractfacts.core.save_command_output")
    @patch("litassist.commands.extractfacts.single_extractor.PROMPTS")
    def test_extractfacts_without_noverify_uses_verification(
        self, mock_prompts, mock_save, mock_verify, mock_factory, mock_config
    ):
        """Test that extractfacts without --noverify uses standard verification."""
        # Setup mocks
        mock_config_obj = Mock()
        mock_config_obj.max_chars = 10000  # Set as integer
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
            # Run command without --noverify
            result = self.runner.invoke(extractfacts, [test_file])

            # Verify command succeeded
            assert result.exit_code == 0

            # Verify that verify_content_if_needed was called with verify_flag=True
            mock_verify.assert_called_once()
            # Check using keyword args or positional args
            assert (
                mock_verify.call_args.kwargs.get(
                    "verify_flag",
                    (
                        mock_verify.call_args.args[3]
                        if len(mock_verify.call_args.args) > 3
                        else None
                    ),
                )
                is True
            )

        finally:
            Path(test_file).unlink()

    @patch("litassist.commands.strategy.validators.extract_legal_issues")
    @patch("litassist.commands.strategy.core.LLMClientFactory.for_command")
    @patch("litassist.commands.strategy.core.verify_content_if_needed")
    @patch("litassist.commands.strategy.file_handler.save_command_output")
    @patch("litassist.commands.strategy.core.PROMPTS")
    def test_strategy_with_noverify_skips_verification(
        self, mock_prompts, mock_save, mock_verify, mock_factory, mock_extract
    ):
        """Test that strategy with --noverify skips standard verification."""
        # Setup mocks
        mock_factory.return_value = self.mock_client
        mock_prompts.get.return_value = "Test prompt"
        mock_prompts.get_system_prompt.return_value = "System prompt"
        mock_save.return_value = "output.txt"
        mock_verify.return_value = ("Content", None)
        mock_extract.return_value = ["Issue 1", "Issue 2"]

        # Create test case facts file with proper format
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                """
Parties:
Test parties

Background:
Test background

Key Events:
Test events

Legal Issues:
Test issues

Evidence Available:
Test evidence

Opposing Arguments:
Test arguments

Procedural History:
Test history

Jurisdiction:
Test jurisdiction

Applicable Law:
Test law

Client Objectives:
Test objectives
            """
            )
            facts_file = f.name

        try:
            # Run command with --noverify
            result = self.runner.invoke(
                strategy, [facts_file, "--outcome", "Win case", "--noverify"]
            )

            # Verify command succeeded
            assert result.exit_code == 0

            # Verify that verify_content_if_needed was NOT called when --noverify is set
            mock_verify.assert_not_called()

        finally:
            Path(facts_file).unlink()

    @patch("litassist.commands.draft.core.LLMClientFactory.for_command")
    @patch("litassist.commands.draft.core.verify_content_if_needed")
    @patch("litassist.commands.draft.core.save_command_output")
    @patch("litassist.commands.draft.prompt_builder.PROMPTS")
    def test_draft_with_noverify_skips_verification(
        self, mock_prompts, mock_save, mock_verify, mock_factory
    ):
        """Test that draft with --noverify skips standard verification."""
        # Setup mocks
        mock_factory.return_value = self.mock_client
        mock_prompts.get.return_value = "Test prompt"
        mock_save.return_value = "output.txt"

        # Create test file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test document content")
            test_file = f.name

        try:
            # Run command with --noverify
            result = self.runner.invoke(
                draft,
                [test_file, "Draft a witness statement", "--noverify"],
                obj={"premium": False},
            )

            # Verify command succeeded
            assert result.exit_code == 0

            # Verify that verify_content_if_needed was NOT called
            mock_verify.assert_not_called()

            # Verify the skip message appears
            assert "Standard verification skipped" in result.output

        finally:
            Path(test_file).unlink()


class TestVerificationDefaults:
    """Test default verification behavior without flags."""

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
    def test_extractfacts_default_enables_verification(
        self, mock_prompts, mock_save, mock_verify, mock_factory, mock_config
    ):
        """Test that extractfacts enables verification by default."""
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

            # Should use verification by default
            mock_verify.assert_called_once()
            # Check using keyword args or positional args
            assert (
                mock_verify.call_args.kwargs.get(
                    "verify_flag",
                    (
                        mock_verify.call_args.args[3]
                        if len(mock_verify.call_args.args) > 3
                        else None
                    ),
                )
                is True
            )

        finally:
            Path(test_file).unlink()


# Test markers
pytestmark = pytest.mark.unit
