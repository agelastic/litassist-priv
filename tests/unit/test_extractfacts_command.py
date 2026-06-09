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

    @patch("litassist.commands.extractfacts.document_reader.LLMClientFactory.get_input_budget_for_command")
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
        mock_config.return_value = 1000
        # Patch LLM client
        mock_client = Mock()
        mock_client.complete.return_value = ("Extracted content", self.mock_usage)
        mock_factory.for_command.return_value = mock_client
        mock_output.return_value = "output_file.txt"
        # Mock verify_content_if_needed to return content unchanged
        mock_verify_content.return_value = ("Extracted content", False, None)

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
        # Now called twice: once for raw output, once for verified output
        assert mock_output.call_count == 2
        mock_log.assert_called_once()
        mock_show.assert_called_once()

    @patch("litassist.commands.extractfacts.document_reader.LLMClientFactory.get_input_budget_for_command")
    @patch("litassist.commands.extractfacts.single_extractor.PROMPTS")
    @patch("litassist.commands.extractfacts.core.show_command_completion")
    @patch("litassist.commands.extractfacts.core.save_log")
    @patch("litassist.commands.extractfacts.core.save_command_output")
    @patch("litassist.commands.extractfacts.core.LLMClientFactory")
    @patch("litassist.commands.extractfacts.single_extractor.create_reasoning_prompt")
    @patch("litassist.commands.extractfacts.document_reader.chunk_text")
    @patch("litassist.commands.extractfacts.document_reader.validate_file_size")
    @patch("litassist.commands.extractfacts.core.verify_content_if_needed")
    def test_warns_when_output_missing_headings(
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
        # Arrange: the LLM returns content that does NOT satisfy the 10-heading
        # contract (only two headings present).
        invalid = "Parties: A v B\nBackground: a dispute arose."
        mock_validate.return_value = "Sample document text"
        mock_chunk.return_value = ["Sample chunk"]
        mock_prompts.get_format_template.return_value = "Format instructions"
        mock_prompts.get_system_prompt.return_value = "System prompt"
        mock_create_prompt.return_value = "Reasoned prompt"
        mock_config.return_value = 1000
        mock_client = Mock()
        mock_client.complete.return_value = (invalid, self.mock_usage)
        mock_factory.for_command.return_value = mock_client
        mock_output.return_value = "output_file.txt"
        mock_verify_content.return_value = (invalid, False, None)

        temp_file = tmp_path / "input.txt"
        temp_file.write_text("irrelevant content")

        # Act
        result = self.runner.invoke(extractfacts, [str(temp_file)])

        # Assert: command still succeeds and saves, but the user is warned that
        # the produced facts are missing required headings (producer-side check).
        assert result.exit_code == 0
        assert "missing one or more required headings" in result.output.lower()
        # Final output is still saved (raw + final = 2 calls).
        assert mock_output.call_count == 2

    @patch("litassist.commands.extractfacts.document_reader.LLMClientFactory.get_input_budget_for_command")
    @patch("litassist.commands.extractfacts.single_extractor.PROMPTS")
    @patch("litassist.commands.extractfacts.core.show_command_completion")
    @patch("litassist.commands.extractfacts.core.save_log")
    @patch("litassist.commands.extractfacts.core.save_command_output")
    @patch("litassist.commands.extractfacts.core.LLMClientFactory")
    @patch("litassist.commands.extractfacts.single_extractor.create_reasoning_prompt")
    @patch("litassist.commands.extractfacts.document_reader.chunk_text")
    @patch("litassist.commands.extractfacts.document_reader.validate_file_size")
    @patch("litassist.commands.extractfacts.core.verify_content_if_needed")
    def test_short_circuit_reported_not_applied(
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
        # Arrange: a valid 10-heading extraction, but verification short-circuited
        # (chain bailed before the LLM stage on citation pattern issues).
        valid = "\n".join(
            f"{h}: x"
            for h in [
                "Parties", "Background", "Key Events", "Legal Issues",
                "Evidence Available", "Opposing Arguments", "Procedural History",
                "Jurisdiction", "Applicable Law", "Client Objectives",
            ]
        )
        mock_validate.return_value = "Sample document text"
        mock_chunk.return_value = ["Sample chunk"]
        mock_prompts.get_format_template.return_value = "Format instructions"
        mock_prompts.get_system_prompt.return_value = "System prompt"
        mock_create_prompt.return_value = "Reasoned prompt"
        mock_config.return_value = 1000
        mock_client = Mock()
        mock_client.complete.return_value = (valid, self.mock_usage)
        mock_factory.for_command.return_value = mock_client
        mock_output.return_value = "output_file.txt"
        mock_verify_content.return_value = (valid, False, "citation pattern issues")

        temp_file = tmp_path / "input.txt"
        temp_file.write_text("irrelevant content")

        # Act
        result = self.runner.invoke(extractfacts, [str(temp_file)])

        # Assert: the command must NOT claim verification was applied; it reports
        # the short-circuit and that the content was not fully verified.
        assert result.exit_code == 0
        out = result.output.lower()
        assert "short-circuited" in out
        assert "not fully verified" in out
        # The saved metadata carries the short-circuit status, not "applied".
        final_metadata = mock_output.call_args_list[-1].kwargs["metadata"]
        assert "short-circuited" in final_metadata["Verification"].lower()
