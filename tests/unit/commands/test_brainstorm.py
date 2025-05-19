"""
Unit tests for the brainstorm command.
"""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
from click import ClickException

from litassist.commands.brainstorm import brainstorm


class TestBrainstormCommand:
    """Test the brainstorm command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("litassist.commands.brainstorm.read_document")
    @patch("litassist.commands.brainstorm.LLMClient")
    @patch("litassist.commands.brainstorm.save_log")
    @patch("litassist.commands.brainstorm.heartbeat")
    def test_brainstorm_valid_combination(
        self, mock_heartbeat, mock_save_log, mock_llm_client, mock_read_document
    ):
        """Test brainstorm with valid side/area combination."""
        # Setup mocks
        mock_read_document.return_value = "Test facts"
        mock_llm_instance = Mock()
        mock_llm_instance.complete.return_value = (
            "Strategy content",
            {"total_tokens": 100},
        )
        mock_llm_client.return_value = mock_llm_instance
        mock_heartbeat.return_value = lambda f: f

        with self.runner.isolated_filesystem():
            # Create test file
            with open("test_facts.txt", "w") as f:
                f.write("Test facts")

            result = self.runner.invoke(
                brainstorm, ["test_facts.txt", "--side", "plaintiff", "--area", "civil"]
            )

        assert result.exit_code == 0
        assert "Civil Law Strategies for Plaintiff" in result.output
        mock_read_document.assert_called_once_with("test_facts.txt")
        mock_llm_instance.complete.assert_called_once()
        mock_save_log.assert_called_once()

    @patch("litassist.commands.brainstorm.read_document")
    def test_brainstorm_invalid_combination_warning(self, mock_read_document):
        """Test brainstorm shows warning for invalid combinations."""
        mock_read_document.return_value = "Test facts"

        with patch("litassist.commands.brainstorm.LLMClient") as mock_llm:
            mock_instance = Mock()
            mock_instance.complete.return_value = ("Strategy", {"tokens": 100})
            mock_llm.return_value = mock_instance

            result = self.runner.invoke(
                brainstorm,
                ["test_facts.txt", "--side", "plaintiff", "--area", "criminal"],
            )

            assert "Warning" in result.output
            assert "not typically used in criminal matters" in result.output
            assert result.exit_code == 0

    @patch("litassist.commands.brainstorm.read_document")
    def test_brainstorm_accused_in_civil_warning(self, mock_read_document):
        """Test specific warning for accused in civil matters."""
        mock_read_document.return_value = "Test facts"

        with patch("litassist.commands.brainstorm.LLMClient") as mock_llm:
            mock_instance = Mock()
            mock_instance.complete.return_value = ("Strategy", {"tokens": 100})
            mock_llm.return_value = mock_instance

            result = self.runner.invoke(
                brainstorm, ["test_facts.txt", "--side", "accused", "--area", "civil"]
            )

            assert (
                "'Accused' is typically only used in criminal matters" in result.output
            )

    @patch("litassist.commands.brainstorm.read_document")
    @patch("litassist.commands.brainstorm.LLMClient")
    def test_brainstorm_with_verify(self, mock_llm_client, mock_read_document):
        """Test brainstorm with verification enabled."""
        mock_read_document.return_value = "Test facts"
        mock_llm_instance = Mock()
        mock_llm_instance.complete.return_value = ("Strategy", {"tokens": 100})
        mock_llm_instance.verify.return_value = "Verification notes"
        mock_llm_client.return_value = mock_llm_instance

        result = self.runner.invoke(
            brainstorm,
            ["test_facts.txt", "--side", "plaintiff", "--area", "civil", "--verify"],
        )

        assert result.exit_code == 0
        assert "Corrections" in result.output
        mock_llm_instance.verify.assert_called_once()

    @patch("litassist.commands.brainstorm.read_document")
    def test_brainstorm_file_read_error(self, mock_read_document):
        """Test error handling for file read failure."""
        mock_read_document.side_effect = ClickException("File not found")

        result = self.runner.invoke(
            brainstorm, ["nonexistent.txt", "--side", "plaintiff", "--area", "civil"]
        )

        assert result.exit_code != 0
        assert "File not found" in result.output

    @patch("litassist.commands.brainstorm.read_document")
    @patch("litassist.commands.brainstorm.LLMClient")
    def test_brainstorm_llm_error(self, mock_llm_client, mock_read_document):
        """Test error handling for LLM failure."""
        mock_read_document.return_value = "Test facts"
        mock_llm_instance = Mock()
        mock_llm_instance.complete.side_effect = Exception("API Error")
        mock_llm_client.return_value = mock_llm_instance

        result = self.runner.invoke(
            brainstorm, ["test_facts.txt", "--side", "plaintiff", "--area", "civil"]
        )

        assert result.exit_code != 0
        assert "Grok brainstorming error" in result.output

    def test_brainstorm_missing_required_params(self):
        """Test brainstorm fails without required parameters."""
        result = self.runner.invoke(brainstorm, ["test_facts.txt"])

        assert result.exit_code != 0
        assert "Missing option" in result.output
