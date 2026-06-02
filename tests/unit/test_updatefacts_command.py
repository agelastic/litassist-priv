"""
Basic tests for the updatefacts command.

Offline only: the LLM, file reads, output saving, and logging are mocked.
The prompt system (PROMPTS) and the case-facts resolver/validator run for
real, so these tests also prove the new YAML keys are wired correctly.
"""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from litassist.commands.updatefacts import updatefacts

_HEADINGS = [
    "Parties",
    "Background",
    "Key Events",
    "Legal Issues",
    "Evidence Available",
    "Opposing Arguments",
    "Procedural History",
    "Jurisdiction",
    "Applicable Law",
    "Client Objectives",
]
# A valid merged result: the 10 required headings plus the Notes section that
# updatefacts asks the model to add.
VALID_MERGED = (
    "\n".join(f"{i}. **{h}**: detail" for i, h in enumerate(_HEADINGS, 1))
    + "\n11. **Notes**: nothing further"
)


class TestUpdateFactsBasic:
    """Core behaviour of the updatefacts command."""

    def setup_method(self):
        self.runner = CliRunner()
        self.usage = {"total_tokens": 15}

    def _mock_factory(self, mock_factory):
        client = Mock()
        client.model = "test-model"
        client.complete.return_value = (VALID_MERGED, self.usage)
        mock_factory.for_command.return_value = client
        mock_factory.get_input_budget_for_command.return_value = 1_000_000
        mock_factory.get_model_for_command.return_value = "test-model"
        return client

    @patch("litassist.commands.updatefacts.core.show_command_completion")
    @patch("litassist.commands.updatefacts.core.save_log")
    @patch("litassist.commands.updatefacts.core.save_command_output")
    @patch("litassist.commands.updatefacts.core.validate_file_size")
    @patch("litassist.commands.updatefacts.core.LLMClientFactory")
    def test_create_from_scratch(
        self, mock_factory, mock_validate, mock_output, mock_log, mock_show
    ):
        client = self._mock_factory(mock_factory)
        mock_validate.return_value = "RAW SOURCE TEXT"
        mock_output.return_value = "case_facts_x.txt"

        with self.runner.isolated_filesystem():
            with open("source.txt", "w") as f:
                f.write("raw")
            result = self.runner.invoke(updatefacts, ["source.txt"])

        assert result.exit_code == 0, result.output
        assert "creating from scratch" in result.output.lower()
        mock_factory.for_command.assert_called_once_with("updatefacts")
        client.complete.assert_called_once()

        user_prompt = client.complete.call_args[0][0][1]["content"]
        assert "create from scratch" in user_prompt
        assert "SOURCE: source.txt" in user_prompt
        assert "RAW SOURCE TEXT" in user_prompt

        # Saved under the case_facts base name, into the current directory.
        assert mock_output.call_args[0][0] == "case_facts"
        assert mock_output.call_args.kwargs.get("output_dir")
        mock_log.assert_called_once()
        mock_show.assert_called_once()

    @patch("litassist.commands.updatefacts.core.show_command_completion")
    @patch("litassist.commands.updatefacts.core.save_log")
    @patch("litassist.commands.updatefacts.core.save_command_output")
    @patch("litassist.commands.updatefacts.core.validate_file_size")
    @patch("litassist.commands.updatefacts.core.LLMClientFactory")
    def test_writes_into_env_run_dir(
        self, mock_factory, mock_validate, mock_output, mock_log, mock_show
    ):
        # Inside a caseplan runner, LITASSIST_OUTPUT_DIR points both case_facts
        # writes (timestamped + stable) at the run dir, leaving the cwd untouched.
        import os

        self._mock_factory(mock_factory)
        mock_validate.return_value = "RAW SOURCE TEXT"
        mock_output.return_value = "outputs/run_x/case_facts_x.txt"

        with self.runner.isolated_filesystem():
            os.makedirs("outputs/run_x")
            with open("source.txt", "w") as f:
                f.write("raw")
            with patch.dict(os.environ, {"LITASSIST_OUTPUT_DIR": "outputs/run_x"}):
                result = self.runner.invoke(updatefacts, ["source.txt"])

            assert result.exit_code == 0, result.output
            assert mock_output.call_args.kwargs.get("output_dir") == "outputs/run_x"
            assert os.path.exists("outputs/run_x/case_facts.md")
            assert not os.path.exists("case_facts.md")

    @patch("litassist.commands.updatefacts.core.show_command_completion")
    @patch("litassist.commands.updatefacts.core.save_log")
    @patch("litassist.commands.updatefacts.core.save_command_output")
    @patch("litassist.commands.updatefacts.core.validate_file_size")
    @patch("litassist.commands.updatefacts.core.LLMClientFactory")
    def test_updates_explicit_facts(
        self, mock_factory, mock_validate, mock_output, mock_log, mock_show
    ):
        client = self._mock_factory(mock_factory)

        def _read(path, **kwargs):
            return "EXISTING FACTS BODY" if "case_facts" in path else "NEW SOURCE BODY"

        mock_validate.side_effect = _read
        mock_output.return_value = "case_facts_x.txt"

        with self.runner.isolated_filesystem():
            with open("existing_case_facts.md", "w") as f:
                f.write("old")
            with open("source.txt", "w") as f:
                f.write("raw")
            result = self.runner.invoke(
                updatefacts, ["source.txt", "--facts", "existing_case_facts.md"]
            )

        assert result.exit_code == 0, result.output
        user_prompt = client.complete.call_args[0][0][1]["content"]
        assert "EXISTING FACTS BODY" in user_prompt
        assert "NEW SOURCE BODY" in user_prompt

    @patch("litassist.commands.updatefacts.core.show_command_completion")
    @patch("litassist.commands.updatefacts.core.save_log")
    @patch("litassist.commands.updatefacts.core.save_command_output")
    @patch("litassist.commands.updatefacts.core.validate_file_size")
    @patch("litassist.commands.updatefacts.core.LLMClientFactory")
    def test_auto_resolves_latest_case_facts(
        self, mock_factory, mock_validate, mock_output, mock_log, mock_show
    ):
        self._mock_factory(mock_factory)
        mock_validate.return_value = "BODY"
        mock_output.return_value = "case_facts_x.txt"

        with self.runner.isolated_filesystem():
            with open("case_facts.md", "w") as f:
                f.write("old facts")
            with open("source.txt", "w") as f:
                f.write("raw")
            result = self.runner.invoke(updatefacts, ["source.txt"])

        assert result.exit_code == 0, result.output
        assert "Using case facts: case_facts.md" in result.output

    @patch("litassist.commands.updatefacts.core.show_command_completion")
    @patch("litassist.commands.updatefacts.core.save_log")
    @patch("litassist.commands.updatefacts.core.save_command_output")
    @patch("litassist.commands.updatefacts.core.validate_file_size")
    @patch("litassist.commands.updatefacts.core.LLMClientFactory")
    def test_warns_when_result_missing_headings(
        self, mock_factory, mock_validate, mock_output, mock_log, mock_show
    ):
        # Mirrors extractfacts: a merge missing headings warns but still saves
        # (exit 0). Downstream commands run the same validation and reject a
        # wrong-shaped file, so updatefacts does not special-case it.
        client = self._mock_factory(mock_factory)
        client.complete.return_value = ("just prose, no headings at all", self.usage)
        mock_validate.return_value = "BODY"
        mock_output.return_value = "case_facts_x.txt"

        with self.runner.isolated_filesystem():
            with open("source.txt", "w") as f:
                f.write("raw")
            result = self.runner.invoke(updatefacts, ["source.txt"])

        assert result.exit_code == 0, result.output
        # Assert the command's OWN warn-and-save message (not the validator's
        # echo, which prints regardless) so this fails if the warn block is removed.
        assert "Saving anyway" in result.output
        assert mock_output.call_args[0][0] == "case_facts"

    @patch("litassist.commands.updatefacts.core.show_command_completion")
    @patch("litassist.commands.updatefacts.core.save_log")
    @patch("litassist.commands.updatefacts.core.save_command_output")
    @patch("litassist.commands.updatefacts.core.validate_file_size")
    @patch("litassist.commands.updatefacts.core.LLMClientFactory")
    def test_writes_stable_case_facts_md(
        self, mock_factory, mock_validate, mock_output, mock_log, mock_show
    ):
        # updatefacts must also refresh a stable ./case_facts.md so that
        # caseplan-generated scripts referencing the literal name (e.g.
        # `brainstorm --facts case_facts.md`) resolve instead of failing with
        # "File not found: case_facts.md".
        import os

        self._mock_factory(mock_factory)
        mock_validate.return_value = "BODY"
        mock_output.return_value = "case_facts_x.txt"

        with self.runner.isolated_filesystem():
            with open("source.txt", "w") as f:
                f.write("raw")
            result = self.runner.invoke(updatefacts, ["source.txt"])
            assert result.exit_code == 0, result.output
            assert os.path.exists("case_facts.md"), (
                "updatefacts must write a stable case_facts.md in the cwd"
            )
            with open("case_facts.md", encoding="utf-8") as fh:
                assert fh.read() == VALID_MERGED

    def test_help_and_errors(self):
        assert self.runner.invoke(updatefacts, ["--help"]).exit_code == 0
        # Missing required SOURCE argument.
        assert self.runner.invoke(updatefacts, []).exit_code != 0
