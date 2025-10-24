"""
Basic tests for counselnotes command.

Simplified test suite focusing on core functionality.
"""

import tempfile
import os
from unittest.mock import Mock, patch
from click.testing import CliRunner

from litassist.commands.counselnotes import counselnotes


class TestCounselNotesBasic:
    """Basic test suite for the counselnotes command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.mock_usage = {
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500,
        }

    @patch("litassist.commands.counselnotes.document_processor.read_document")
    @patch("litassist.commands.counselnotes.core.LLMClientFactory")
    @patch("litassist.commands.counselnotes.core.save_command_output")
    @patch("litassist.commands.counselnotes.core.save_log")
    @patch("litassist.commands.counselnotes.core.show_command_completion")
    @patch("litassist.commands.counselnotes.analysis_processor.PROMPTS")
    @patch("litassist.commands.counselnotes.document_processor.get_config")
    @patch("click.DateTime.convert")
    def test_basic_strategic_analysis(
        self,
        mock_datetime,
        mock_config,
        mock_prompts,
        mock_completion,
        mock_log,
        mock_output,
        mock_factory,
        mock_read,
    ):
        """Test basic strategic analysis mode."""
        # Setup mocks
        mock_datetime.return_value = "2025-01-07 13:51:00"
        mock_config_obj = Mock()
        mock_config_obj.max_chars = 10000  # Set a reasonable limit
        mock_config.return_value = mock_config_obj
        mock_read.return_value = "Sample legal document content"
        mock_client = Mock()
        mock_client.complete.return_value = (
            "Strategic analysis output",
            self.mock_usage,
        )
        mock_factory.for_command.return_value = mock_client
        mock_prompts.get.return_value = "Strategic analysis prompt"
        mock_output.return_value = "output_file.md"

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_file = f.name

        try:
            # Run command
            result = self.runner.invoke(counselnotes, [temp_file])

            # Basic assertions
            assert result.exit_code == 0
            mock_factory.for_command.assert_called_once_with("counselnotes")
            mock_client.complete.assert_called_once()
        finally:
            os.unlink(temp_file)

    @patch("litassist.commands.counselnotes.document_processor.read_document")
    @patch("litassist.commands.counselnotes.core.LLMClientFactory")
    @patch("litassist.commands.counselnotes.core.save_command_output")
    @patch("litassist.commands.counselnotes.core.save_log")
    @patch("litassist.commands.counselnotes.core.show_command_completion")
    @patch("litassist.commands.counselnotes.analysis_processor.PROMPTS")
    @patch("litassist.commands.counselnotes.document_processor.get_config")
    @patch("click.DateTime.convert")
    def test_extraction_mode(
        self,
        mock_datetime,
        mock_config,
        mock_prompts,
        mock_completion,
        mock_log,
        mock_output,
        mock_factory,
        mock_read,
    ):
        """Test extraction mode."""
        # Setup mocks
        mock_datetime.return_value = "2025-01-07 13:51:00"
        mock_config_obj = Mock()
        mock_config_obj.max_chars = 10000  # Set a reasonable limit
        mock_config.return_value = mock_config_obj
        mock_read.return_value = "Sample legal document content"
        mock_client = Mock()

        # Return formatted text directly (not JSON anymore)
        formatted_response = "CITATIONS FOUND:\n• Test v Case [2023] HCA 1"
        mock_client.complete.return_value = (formatted_response, self.mock_usage)
        mock_factory.for_command.return_value = mock_client
        mock_prompts.get.return_value = "Extraction prompt"
        mock_output.return_value = "output_file.txt"

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt") as f:
            f.write("test content")
            temp_file = f.name

        try:
            # Run command with extraction
            result = self.runner.invoke(
                counselnotes, ["--extract", "citations", temp_file]
            )

            # Basic assertions
            assert result.exit_code == 0
            mock_client.complete.assert_called_once()

            # Verify output was saved with formatted text
            mock_output.assert_called_once()
        finally:
            os.unlink(temp_file)

    def test_command_help(self):
        """Test that command help works."""
        result = self.runner.invoke(counselnotes, ["--help"])
        assert result.exit_code == 0
        assert "Strategic analysis and counsel's notes" in result.output

    def test_no_files_error(self):
        """Test error when no files provided."""
        result = self.runner.invoke(counselnotes, [])
        assert result.exit_code != 0

    def test_nonexistent_file_error(self):
        """Test error handling for missing files."""
        result = self.runner.invoke(counselnotes, ["nonexistent.txt"])
        assert result.exit_code != 0
        assert "does not exist" in result.output
