"""
Unit tests for the extractfacts command.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from click.testing import CliRunner
from click import ClickException

from litassist.commands.extractfacts import extractfacts


class TestExtractfactsCommand:
    """Test the extractfacts command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("litassist.commands.extractfacts.read_document")
    @patch("litassist.commands.extractfacts.chunk_text")
    @patch("litassist.commands.extractfacts.LLMClient")
    @patch("litassist.commands.extractfacts.save_log")
    @patch("builtins.open", new_callable=mock_open)
    def test_extractfacts_success(
        self,
        mock_file,
        mock_save_log,
        mock_llm_client,
        mock_chunk_text,
        mock_read_document,
    ):
        """Test successful fact extraction."""
        # Setup mocks
        mock_read_document.return_value = "Test document content"
        mock_chunk_text.return_value = ["Chunk 1", "Chunk 2"]

        mock_llm_instance = Mock()
        mock_llm_instance.complete.side_effect = [
            ("Facts from chunk 1", {"tokens": 100}),
            ("Facts from chunk 2", {"tokens": 100}),
        ]
        mock_llm_client.return_value = mock_llm_instance

        result = self.runner.invoke(extractfacts, ["test_doc.pdf"])

        assert result.exit_code == 0
        assert "case_facts.txt created successfully" in result.output

        # Verify file was written
        mock_file.assert_called_once_with("case_facts.txt", "w", encoding="utf-8")
        written_content = mock_file().write.call_args[0][0]
        assert "Facts from chunk 1" in written_content
        assert "Facts from chunk 2" in written_content

    def test_extractfacts_with_expected_headings(self):
        """Test that extractfacts uses the correct headings."""
        with patch("litassist.commands.extractfacts.read_document"):
            with patch("litassist.commands.extractfacts.chunk_text") as mock_chunk:
                mock_chunk.return_value = ["Test chunk"]

                with patch("litassist.commands.extractfacts.LLMClient") as mock_llm:
                    mock_instance = Mock()
                    mock_llm.return_value = mock_instance

                    result = self.runner.invoke(extractfacts, ["test.txt"])

                    # Check that the prompt includes new headings
                    call_args = mock_instance.complete.call_args[0][0][1]["content"]
                    assert "1. Parties" in call_args
                    assert "2. Background" in call_args
                    assert "3. Key Events" in call_args
                    assert "4. Legal Issues" in call_args
                    assert "5. Evidence Available" in call_args
                    assert "6. Opposing Arguments" in call_args
                    assert "7. Procedural History" in call_args
                    assert "8. Jurisdiction" in call_args
                    assert "9. Applicable Law" in call_args
                    assert "10. Client Objectives" in call_args

    @patch("litassist.commands.extractfacts.read_document")
    @patch("litassist.commands.extractfacts.chunk_text")
    @patch("litassist.commands.extractfacts.LLMClient")
    @patch("builtins.open", new_callable=mock_open)
    def test_extractfacts_with_verify(
        self, mock_file, mock_llm_client, mock_chunk_text, mock_read_document
    ):
        """Test fact extraction with verification."""
        mock_read_document.return_value = "Test content"
        mock_chunk_text.return_value = ["Chunk 1"]

        mock_llm_instance = Mock()
        mock_llm_instance.complete.return_value = ("Facts", {"tokens": 100})
        mock_llm_instance.verify.return_value = "Verification notes"
        mock_llm_client.return_value = mock_llm_instance

        result = self.runner.invoke(extractfacts, ["test.pdf", "--verify"])

        assert result.exit_code == 0
        mock_llm_instance.verify.assert_called_once()

        written_content = mock_file().write.call_args[0][0]
        assert "Corrections" in written_content

    @patch("litassist.commands.extractfacts.read_document")
    def test_extractfacts_file_error(self, mock_read_document):
        """Test error handling for file read failure."""
        mock_read_document.side_effect = ClickException("Cannot read file")

        result = self.runner.invoke(extractfacts, ["bad_file.pdf"])

        assert result.exit_code != 0
        assert "Cannot read file" in result.output

    @patch("litassist.commands.extractfacts.read_document")
    @patch("litassist.commands.extractfacts.chunk_text")
    @patch("litassist.commands.extractfacts.LLMClient")
    def test_extractfacts_llm_error(
        self, mock_llm_client, mock_chunk_text, mock_read_document
    ):
        """Test error handling for LLM failure."""
        mock_read_document.return_value = "Test content"
        mock_chunk_text.return_value = ["Chunk 1"]

        mock_llm_instance = Mock()
        mock_llm_instance.complete.side_effect = Exception("API Error")
        mock_llm_client.return_value = mock_llm_instance

        result = self.runner.invoke(extractfacts, ["test.pdf"])

        assert result.exit_code != 0
        assert "Error extracting facts" in result.output

    @patch("litassist.commands.extractfacts.read_document")
    @patch("litassist.commands.extractfacts.chunk_text")
    @patch("litassist.commands.extractfacts.click.progressbar")
    def test_extractfacts_progress_bar(
        self, mock_progressbar, mock_chunk_text, mock_read_document
    ):
        """Test that progress bar is used for multiple chunks."""
        mock_read_document.return_value = "Test content"
        mock_chunk_text.return_value = ["Chunk 1", "Chunk 2", "Chunk 3"]

        with patch("litassist.commands.extractfacts.LLMClient"):
            result = self.runner.invoke(extractfacts, ["test.pdf"])

            mock_progressbar.assert_called_once()
            assert mock_progressbar.call_args[1]["label"] == "Extracting facts"
