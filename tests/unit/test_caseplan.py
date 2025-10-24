"""Unit tests for the caseplan command."""

from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from litassist.commands.caseplan import caseplan


class TestCaseplanCommand:
    """Test cases for caseplan command functionality."""

    @patch("litassist.commands.caseplan.budget_assessor.LLMClientFactory")
    @patch("litassist.commands.caseplan.budget_assessor.save_command_output")
    @patch("litassist.commands.caseplan.budget_assessor.save_log")
    def test_budget_assessment_mode(
        self, mock_save_log, mock_save_output, mock_factory, tmp_path
    ):
        """Test budget assessment mode (no --budget)."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("Parties: Test v Test\nBackground: Dispute...")

        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "SUMMARY: Medium complexity\nRECOMMENDATION: standard\nJUSTIFICATION: ...",
            {"total_tokens": 500},
        )
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_assessment_123.txt"

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts)])

        assert result.exit_code == 0
        assert "BUDGET RECOMMENDATION" in result.output
        assert "RECOMMENDATION: standard" in result.output
        mock_factory.for_command.assert_called_once_with("caseplan", "assessment")
        mock_save_output.assert_called_once()
        mock_save_log.assert_called_once()

    @patch("litassist.commands.caseplan.plan_generator.LLMClientFactory")
    @patch("litassist.commands.caseplan.plan_generator.save_command_output")
    @patch("litassist.commands.caseplan.plan_generator.save_log")
    def test_full_plan_mode(
        self, mock_save_log, mock_save_output, mock_factory, tmp_path
    ):
        """Test full plan mode (--budget specified)."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("Parties: Test v Test\nBackground: Dispute...")

        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "# Litigation Plan\n## Case Assessment\nComplexity: MEDIUM...",
            {"total_tokens": 1000},
        )
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_123.txt"

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts), "--budget", "minimal"])

        assert result.exit_code == 0
        assert "Litigation plan generated successfully" in result.output
        mock_factory.for_command.assert_called_once_with("caseplan")
        # Now saves two files: the plan and the extracted commands
        assert mock_save_output.call_count == 2
        mock_save_log.assert_called_once()

    @patch("litassist.commands.caseplan.plan_generator.LLMClientFactory")
    @patch("litassist.commands.caseplan.plan_generator.save_command_output")
    @patch("litassist.commands.caseplan.plan_generator.save_log")
    def test_context_option(
        self, mock_save_log, mock_save_output, mock_factory, tmp_path
    ):
        """Test --context option is included in prompt."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("Parties: Test v Test\nBackground: Dispute...")

        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "# Litigation Plan\n## Case Assessment\nComplexity: MEDIUM...",
            {"total_tokens": 1000},
        )
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_123.txt"

        runner = CliRunner()
        result = runner.invoke(
            caseplan, [str(case_facts), "--budget", "minimal", "--context", "property"]
        )

        assert result.exit_code == 0
        call_args = mock_client.complete.call_args[0][0]
        assert any(
            "USER ANALYSIS GUIDANCE" in msg["content"] and "property" in msg["content"]
            for msg in call_args
            if msg["role"] == "user"
        )

    def test_file_size_validation(self, tmp_path):
        """Test rejection of oversized files."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("A" * 60000)  # 60KB

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts)])

        assert result.exit_code == 1
        assert "Case facts" in result.output and "too large" in result.output

    @patch("litassist.commands.caseplan.budget_assessor.LLMClientFactory")
    @patch("litassist.commands.caseplan.budget_assessor.save_command_output")
    @patch("litassist.commands.caseplan.budget_assessor.save_log")
    def test_llm_error_handling(
        self, mock_save_log, mock_save_output, mock_factory, tmp_path
    ):
        """Test graceful handling of LLM API errors."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("Parties: Test v Test\nBackground: Dispute...")

        mock_client = MagicMock()
        mock_client.complete.side_effect = Exception("LLM error")
        mock_factory.for_command.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts)])

        assert result.exit_code == 1
        # Accept either our error message or a KeyError from missing prompt
        assert "Budget assessment error" in result.output

    def test_command_registration(self):
        """Test that caseplan is properly registered as a CLI command."""
        from litassist.cli import cli
        from litassist.commands import register_commands

        register_commands(cli)
        command_names = list(cli.commands.keys())
        assert "caseplan" in command_names

    def test_invalid_budget_choice(self, tmp_path):
        """Test Click validation of budget choices."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("Parties: Test v Test\nBackground: Dispute...")

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts), "--budget", "invalid"])

        assert result.exit_code == 2
        assert "Invalid value for '--budget'" in result.output

    @patch("litassist.commands.caseplan.budget_assessor.LLMClientFactory")
    def test_verify_flag_not_supported(self, mock_factory, tmp_path):
        """Test that --verify flag shows appropriate warning."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text(
            "1. Parties: Test\n2. Background: Test\n3. Key Events: Test\n4. Legal Issues: Test\n5. Evidence: Test\n6. Arguments: Test\n7. Procedural History: Test\n8. Jurisdiction: Test\n9. Applicable Law: Test\n10. Client's Objectives: Test"
        )

        mock_client = MagicMock()
        mock_client.complete.return_value = ("Test assessment", {"total_tokens": 100})
        mock_factory.for_command.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts), "--verify"])

        assert result.exit_code == 0
        assert "--verify not supported" in result.output
        assert "Use 'litassist verify'" in result.output

    @patch("litassist.commands.caseplan.budget_assessor.LLMClientFactory")
    def test_noverify_flag_not_supported(self, mock_factory, tmp_path):
        """Test that --noverify flag shows appropriate warning."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text(
            "1. Parties: Test\n2. Background: Test\n3. Key Events: Test\n4. Legal Issues: Test\n5. Evidence: Test\n6. Arguments: Test\n7. Procedural History: Test\n8. Jurisdiction: Test\n9. Applicable Law: Test\n10. Client's Objectives: Test"
        )

        mock_client = MagicMock()
        mock_client.complete.return_value = ("Test assessment", {"total_tokens": 100})
        mock_factory.for_command.return_value = mock_client

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts), "--noverify"])

        assert result.exit_code == 0
        assert "--noverify not supported" in result.output
        assert "no verification to skip" in result.output
