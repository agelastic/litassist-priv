"""
Basic tests for counselnotes command.

Simplified test suite focusing on core functionality.
"""

import json
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

    @patch("litassist.commands.counselnotes.read_document")
    @patch("litassist.commands.counselnotes.LLMClientFactory")
    @patch("litassist.commands.counselnotes.save_command_output")
    @patch("litassist.commands.counselnotes.save_log")
    @patch("litassist.commands.counselnotes.show_command_completion")
    @patch("litassist.commands.counselnotes.PROMPTS")
    @patch("litassist.commands.counselnotes.CONFIG")
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
        mock_config.max_chars = 10000  # Set a reasonable limit
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

    @patch("litassist.commands.counselnotes.read_document")
    @patch("litassist.commands.counselnotes.LLMClientFactory")
    @patch("litassist.commands.counselnotes.save_command_output")
    @patch("litassist.commands.counselnotes.save_log")
    @patch("litassist.commands.counselnotes.show_command_completion")
    @patch("litassist.commands.counselnotes.PROMPTS")
    @patch("litassist.commands.counselnotes.CONFIG")
    @patch("litassist.commands.counselnotes.process_extraction_response")
    @patch("click.DateTime.convert")
    def test_extraction_mode(
        self,
        mock_datetime,
        mock_process_extraction,
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
        mock_config.max_chars = 10000  # Set a reasonable limit
        mock_read.return_value = "Sample legal document content"
        mock_client = Mock()

        # Return valid JSON
        json_response = json.dumps({"citations": ["Test v Case [2023] HCA 1"]})
        mock_client.complete.return_value = (json_response, self.mock_usage)
        mock_factory.for_command.return_value = mock_client
        mock_prompts.get.return_value = "Extraction prompt"
        mock_output.return_value = "output_file.txt"
        
        # Mock process_extraction_response
        mock_process_extraction.return_value = (
            "CITATIONS FOUND:\nTest v Case [2023] HCA 1",
            {"citations": ["Test v Case [2023] HCA 1"]},
            "test_citations.json"
        )

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
            mock_process_extraction.assert_called_once()
            
            # Verify process_extraction_response was called correctly
            call_args = mock_process_extraction.call_args[0]
            assert call_args[1] == "citations"  # extract_type
            assert call_args[3] == "counselnotes"  # command
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
