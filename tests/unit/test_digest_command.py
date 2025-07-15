"""
Basic tests for the digest command.

Tests focus on core digest functionality without external API calls.
"""

from unittest.mock import Mock, patch
from click.testing import CliRunner

from litassist.commands.digest import digest

class TestDigestBasic:
    """Basic test suite for the digest command in summary mode."""

    def setup_method(self):
        self.runner = CliRunner()
        self.mock_usage = {"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18}

    @patch("litassist.commands.digest.CONFIG")
    @patch("litassist.commands.digest.PROMPTS")
    @patch("litassist.commands.digest.show_command_completion")
    @patch("litassist.commands.digest.save_log")
    @patch("litassist.commands.digest.save_command_output")
    @patch("litassist.commands.digest.LLMClientFactory")
    @patch("litassist.commands.digest.chunk_text")
    @patch("litassist.commands.digest.read_document")
    def test_basic_summary(
        self,
        mock_read,
        mock_chunk,
        mock_factory,
        mock_output,
        mock_log,
        mock_show,
        mock_prompts,
        mock_config,
        tmp_path,
    ):
        # Arrange: patch document reading and chunking
        mock_read.return_value = "Full document text"
        mock_chunk.return_value = ["Chunk1"]
        # Patch prompts and config
        mock_prompts.get.return_value = "Any prompt"
        mock_config.max_chars = 50000
        # Patch LLM client
        mock_client = Mock()
        mock_client.model = "openai"
        mock_client.complete.return_value = ("Digest content", self.mock_usage)
        mock_factory.for_command.return_value = mock_client
        mock_output.return_value = "digest_output.txt"

        # Create temporary input file using pytest's tmp_path fixture
        temp_file = tmp_path / "input.txt"
        temp_file.write_text("irrelevant content")

        # Act: run the command without explicit mode (defaults to summary)
        result = self.runner.invoke(digest, [str(temp_file)])

        # Assert: command succeeded and was invoked correctly
        assert result.exit_code == 0
        mock_factory.for_command.assert_called_once_with("digest", "summary")
        mock_client.complete.assert_called_once()
        mock_output.assert_called_once()
        mock_show.assert_called_once()
        mock_log.assert_called_once()

class TestDigestIssuesMode:
    """Test suite for the digest command in issues mode with citation warnings."""

    def setup_method(self):
        self.runner = CliRunner()
        self.mock_usage = {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12}

    @patch("litassist.commands.digest.CONFIG")
    @patch("litassist.commands.digest.PROMPTS")
    @patch("litassist.commands.digest.show_command_completion")
    @patch("litassist.commands.digest.save_log")
    @patch("litassist.commands.digest.save_command_output")
    @patch("litassist.commands.digest.LLMClientFactory")
    @patch("litassist.commands.digest.chunk_text")
    @patch("litassist.commands.digest.read_document")
    def test_issues_mode_citations(
        self,
        mock_read,
        mock_chunk,
        mock_factory,
        mock_output,
        mock_log,
        mock_show,
        mock_prompts,
        mock_config,
        tmp_path,
    ):
        # Arrange: patch document reading and single-chunk output
        mock_read.return_value = "Doc text for issues"
        mock_chunk.return_value = ["Chunk1"]
        mock_prompts.get.return_value = "Any prompt"
        mock_config.max_chars = 50000
        # Patch LLM client with citation warnings
        mock_client = Mock()
        mock_client.model = "openai"
        mock_client.complete.return_value = ("Issue content", self.mock_usage)
        # Simulate citation issues returned
        mock_client.validate_citations.return_value = ["Warning1", "Warning2"]
        mock_factory.for_command.return_value = mock_client
        mock_output.return_value = "digest_issues_output.txt"

        # Create temporary file using pytest's tmp_path fixture
        temp_file = tmp_path / "input.txt"
        temp_file.write_text("irrelevant content")

        # Act: run the command in issues mode
        result = self.runner.invoke(digest, ["--mode", "issues", str(temp_file)])

        # Assert: correct mode and citation validation occurred
        assert result.exit_code == 0
        mock_factory.for_command.assert_called_once_with("digest", "issues")
        mock_client.complete.assert_called_once()
        mock_client.validate_citations.assert_called_once_with("Issue content")
        mock_output.assert_called_once()
        mock_show.assert_called_once()
        mock_log.assert_called_once()

    def test_help_and_errors(self):
        # Help output
        result_help = self.runner.invoke(digest, ["--help"])
        assert result_help.exit_code == 0
        # No files provided
        result_no_file = self.runner.invoke(digest, [])
        assert result_no_file.exit_code != 0
