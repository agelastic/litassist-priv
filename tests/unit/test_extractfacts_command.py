"""
Basic tests for the extractfacts command.

Tests focus on core extractfacts functionality without external API calls.
"""

from unittest.mock import Mock, patch
from click.testing import CliRunner

from litassist.commands.extractfacts import extractfacts


class TestExtractFactsBasic:
    """Basic test suite for the extractfacts command."""

    def setup_method(self):
        self.runner = CliRunner()
        # Simulated token usage return from LLM
        self.mock_usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        }

    @patch("litassist.commands.extractfacts.document_reader.get_config")
    @patch("litassist.commands.extractfacts.single_extractor.PROMPTS")
    @patch("litassist.commands.extractfacts.core.show_command_completion")
    @patch("litassist.commands.extractfacts.core.save_log")
    @patch("litassist.commands.extractfacts.core.save_command_output")
    @patch("litassist.commands.extractfacts.core.LLMClientFactory")
    @patch("litassist.commands.extractfacts.single_extractor.create_reasoning_prompt")
    @patch("litassist.commands.extractfacts.document_reader.chunk_text")
    @patch("litassist.commands.extractfacts.document_reader.validate_file_size")
    @patch("litassist.commands.extractfacts.core.verify_content_if_needed")
    def test_basic_extractfacts(
        self,
        mock_verify_content,
        mock_validate,
        mock_chunk,
        mock_create_prompt,
        mock_factory,
        mock_output,
        mock_log,
        mock_show,
        mock_prompts,
        mock_config,
        tmp_path,
    ):
        # Arrange: patch file validation and chunking
        mock_validate.return_value = "Sample document text"
        mock_chunk.return_value = ["Sample chunk"]
        # Patch prompts and config
        mock_prompts.get_format_template.return_value = "Format instructions"
        mock_prompts.get_system_prompt.return_value = "System prompt"
        mock_create_prompt.return_value = "Reasoned prompt"
        mock_config_obj = Mock()
        mock_config_obj.max_chars = 1000
        mock_config.return_value = mock_config_obj
        # Patch LLM client
        mock_client = Mock()
        mock_client.complete.return_value = ("Extracted content", self.mock_usage)
        mock_factory.for_command.return_value = mock_client
        mock_output.return_value = "output_file.txt"
        # Mock verify_content_if_needed to return content unchanged
        mock_verify_content.return_value = ("Extracted content", {})

        # Create a temporary input file using pytest's tmp_path fixture
        temp_file = tmp_path / "input.txt"
        temp_file.write_text("irrelevant content")

        # Act: run the command
        result = self.runner.invoke(extractfacts, [str(temp_file)])

        # Assert: command succeeded and LLM was called
        assert result.exit_code == 0
        mock_factory.for_command.assert_called_once_with("extractfacts")
        mock_client.complete.assert_called_once()
        # Verify that verify_content_if_needed was called instead of client.verify
        mock_verify_content.assert_called_once()
        # Ensure output saving and completion display are invoked
        mock_output.assert_called_once()
        mock_log.assert_called_once()
        mock_show.assert_called_once()

    def test_help_and_errors(self):  # no patches needed for help and error paths
        result_help = self.runner.invoke(extractfacts, ["--help"])
        assert result_help.exit_code == 0
        # Missing file argument
        result_no_file = self.runner.invoke(extractfacts, [])
        assert result_no_file.exit_code != 0
