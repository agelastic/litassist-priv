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
        # Console keeps the BUDGET RECOMMENDATION banner so users see a
        # clear "done" marker, but the assessment body itself is no
        # longer echoed -- the body lives in the saved file. Pin all
        # three behaviours:
        #   1. file-pointer message is on the console
        #   2. banner header is on the console
        #   3. assessment body is NOT on the console
        # Then pin that the saved content carries both the banner and
        # the body.
        assert "Recommendation saved to" in result.output
        assert "BUDGET RECOMMENDATION" in result.output
        assert "RECOMMENDATION: standard" not in result.output
        saved_content = mock_save_output.call_args[0][1]
        assert "BUDGET RECOMMENDATION" in saved_content
        assert "RECOMMENDATION: standard" in saved_content
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
            "# Litigation Plan\n## Case Assessment\nComplexity: MEDIUM\n\n"
            '```bash\nlitassist lookup "contract breach" --mode irac\n```\n',
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
            "# Litigation Plan\n## Case Assessment\nComplexity: MEDIUM\n\n"
            '```bash\nlitassist lookup "contract breach" --mode irac\n```\n',
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
        """Test rejection of oversized files.

        The cap derives from the caseplan model's input window via
        LLMClientFactory.get_input_budget_for_command, so build an input
        deliberately larger than that runtime cap rather than hardcoding a
        size that may drift as models change.
        """
        from litassist.llm.factory import LLMClientFactory

        budget = LLMClientFactory.get_input_budget_for_command("caseplan")
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("A" * (budget + 1000))

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

    # Removed test_command_registration (duplicate of
    # test_cli_command_loading.py::test_command_registration) and
    # test_invalid_budget_choice (exercised Click's own Choice validation, not
    # any caseplan logic).

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

    @patch("litassist.commands.caseplan.plan_generator.LLMClientFactory")
    @patch("litassist.commands.caseplan.plan_generator.save_command_output")
    @patch("litassist.commands.caseplan.plan_generator.save_log")
    def test_zero_commands_warns_and_skips_script(
        self, mock_save_log, mock_save_output, mock_factory, tmp_path
    ):
        """A plan with no executable commands must warn and not save a script."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("Parties: Test v Test\nBackground: Dispute...")

        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "# Litigation Plan\nNarrative only, no runnable commands.",
            {"total_tokens": 1000},
        )
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_123.txt"

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts), "--budget", "minimal"])

        assert result.exit_code == 0
        # Only the plan is saved, not a header-only command script.
        assert mock_save_output.call_count == 1
        assert "Execute commands: bash" not in result.output
        assert "no executable commands" in result.output.lower()

    @patch("litassist.commands.caseplan.plan_generator.LLMClientFactory")
    @patch("litassist.commands.caseplan.plan_generator.save_command_output")
    @patch("litassist.commands.caseplan.plan_generator.save_log")
    def test_rejected_commands_are_reported(
        self, mock_save_log, mock_save_output, mock_factory, tmp_path
    ):
        """A plan with a valid command + an unsafe one saves the script and warns."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("Parties: Test v Test\nBackground: Dispute...")

        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "# Plan\n\n```bash\n"
            'litassist lookup "ok" --mode irac\n'
            'litassist lookup "unbalanced\n'
            "```\n",
            {"total_tokens": 1000},
        )
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_123.txt"

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts), "--budget", "minimal"])

        assert result.exit_code == 0
        # Valid command extracted -> plan + commands file both saved.
        assert mock_save_output.call_count == 2
        assert "excluded from the script" in result.output
        assert 'litassist lookup "unbalanced' in result.output

    @patch("litassist.commands.caseplan.budget_assessor.LLMClientFactory")
    @patch("litassist.commands.caseplan.budget_assessor.save_command_output")
    @patch("litassist.commands.caseplan.budget_assessor.save_log")
    def test_assessment_includes_context(
        self, mock_save_log, mock_save_output, mock_factory, tmp_path
    ):
        """Assessment mode must pass --context to the LLM as analysis guidance."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("Parties: Test v Test\nBackground: Dispute...")

        mock_client = MagicMock()
        mock_client.complete.return_value = ("assessment body", {"total_tokens": 100})
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_assessment_123.txt"

        runner = CliRunner()
        result = runner.invoke(
            caseplan, [str(case_facts), "--context", "property dispute"]
        )

        assert result.exit_code == 0
        user_msgs = [
            m["content"]
            for m in mock_client.complete.call_args[0][0]
            if m["role"] == "user"
        ]
        assert any(
            "USER ANALYSIS GUIDANCE" in c and "property dispute" in c for c in user_msgs
        )

    @patch("litassist.commands.caseplan.budget_assessor.LLMClientFactory")
    @patch("litassist.commands.caseplan.budget_assessor.save_command_output")
    @patch("litassist.commands.caseplan.budget_assessor.save_log")
    def test_autoselects_case_facts_when_omitted(
        self, mock_save_log, mock_save_output, mock_factory
    ):
        """No positional case_facts -> resolve the latest case_facts*.txt in cwd."""
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "RECOMMENDATION: standard",
            {"total_tokens": 100},
        )
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_assessment_1.txt"

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("case_facts.txt", "w") as f:
                f.write("Parties: A v B\nBackground: dispute")
            result = runner.invoke(caseplan, [])

        assert result.exit_code == 0
        assert "Using case facts: case_facts.txt" in result.output

    def test_empty_case_facts_rejected(self, tmp_path):
        """An empty/whitespace case facts file must fail before any LLM call."""
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("   \n\t\n")

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts)])

        assert result.exit_code == 1
        assert "empty" in result.output.lower()

    def test_full_plan_routes_to_opus(self):
        """Full plan mode must use an Opus model; assessment stays Sonnet."""
        from pathlib import Path
        import yaml
        import litassist.llm

        cfg_path = Path(litassist.llm.__file__).parent / "model_configs.yaml"
        data = yaml.safe_load(cfg_path.read_text())
        assert "opus" in data["caseplan"]["model"].lower()
        assert "sonnet" in data["caseplan-assessment"]["model"].lower()


class TestCaseplanRunner:
    """The generated commands file is an executable Python runner.

    It isolates each execution under a fresh outputs/run_<ts>/ by setting
    LITASSIST_OUTPUT_DIR; consumer globs and case_facts are rewritten to that dir,
    while --output prefixes (routed by the sink) stay literal.
    """

    @patch("litassist.commands.caseplan.plan_generator.LLMClientFactory")
    @patch("litassist.commands.caseplan.plan_generator.save_command_output")
    @patch("litassist.commands.caseplan.plan_generator.save_log")
    def test_commands_file_is_python_runner(
        self, mock_save_log, mock_save_output, mock_factory, tmp_path
    ):
        case_facts = tmp_path / "case_facts.txt"
        case_facts.write_text("Parties: Test v Test\nBackground: Dispute...")

        plan = (
            "# Litigation Plan\n## Phase 9\n"
            "```bash\n"
            "litassist brainstorm --side plaintiff --area civil "
            "--facts case_facts.txt --output brainstorm_creative\n"
            "litassist strategy case_facts.txt --outcome \"Win\" "
            "--strategies 'outputs/brainstorm_creative_*.txt'\n"
            "```\n"
        )
        mock_client = MagicMock()
        mock_client.complete.return_value = (plan, {"total_tokens": 1000})
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_123.txt"

        runner = CliRunner()
        result = runner.invoke(caseplan, [str(case_facts), "--budget", "minimal"])
        assert result.exit_code == 0, result.output

        # The run hint points at python, not bash (the artifact is a Python runner).
        assert 'python "' in result.output
        assert "bash " not in result.output

        # 2nd save is the runner, written header-less so it stays valid Python.
        commands_call = mock_save_output.call_args_list[1]
        assert commands_call.kwargs.get("include_header") is False
        saved_runner = commands_call.args[1]
        compile(saved_runner, "<runner>", "exec")
        assert saved_runner.startswith("#!/usr/bin/env python3")
        assert 'os.environ["LITASSIST_OUTPUT_DIR"] = run_dir' in saved_runner
        # consumer glob + case_facts rewritten to the run dir; --output prefix not.
        # A legacy case_facts.txt token normalises to the seeded run_dir/case_facts.md.
        assert "os.path.join(run_dir, 'brainstorm_creative_*.md')" in saved_runner
        assert "os.path.join(run_dir, 'case_facts.md')" in saved_runner
        assert "os.path.join(run_dir, 'case_facts.txt')" not in saved_runner
        assert "'brainstorm_creative'" in saved_runner


def _user_prompt(mock_client):
    return next(
        m["content"]
        for m in mock_client.complete.call_args[0][0]
        if m["role"] == "user"
    )


class TestCaseplanSourceFiles:
    """caseplan sends the real source-file inventory so the model references actual
    filenames instead of inventing them, with a confirm gate before the paid call."""

    def test_discover_lists_docs_excluding_facts_md_and_subdirs(
        self, tmp_path, monkeypatch
    ):
        from litassist.commands.caseplan.core import discover_source_files

        monkeypatch.chdir(tmp_path)
        for name in ["affidavit_smith.pdf", "invoice_repairs.pdf", "witness.txt", "scan.PDF"]:
            (tmp_path / name).write_text("x")
        (tmp_path / "notes.md").write_text("x")  # .md included - read as UTF-8 text
        (tmp_path / "config.yaml").write_text("x")  # .yaml excluded by type
        (tmp_path / "brief.docx").write_text("x")  # Word - litassist can't read it, excluded
        (tmp_path / "case_facts.txt").write_text("x")  # case_facts* prefix - excluded
        (tmp_path / "Case_facts.txt").write_text("x")  # case-insensitive prefix - excluded
        (tmp_path / "case_facts_20260101_000000.txt").write_text("x")
        (tmp_path / "facts.txt").write_text("x")  # the ACTUAL facts file - excluded by name
        (tmp_path / "evidence.pdf").mkdir()  # a directory named like a doc - skipped
        (tmp_path / "outputs").mkdir()
        (tmp_path / "outputs" / "ignored.pdf").write_text("x")  # subdir - not scanned

        assert set(discover_source_files("facts.txt")) == {
            "affidavit_smith.pdf",
            "invoice_repairs.pdf",
            "witness.txt",
            "scan.PDF",  # extension matched case-insensitively
            "notes.md",
        }

    @patch("litassist.commands.caseplan.plan_generator.LLMClientFactory")
    @patch("litassist.commands.caseplan.plan_generator.save_command_output")
    @patch("litassist.commands.caseplan.plan_generator.save_log")
    def test_prompt_includes_discovered_source_files(
        self, mock_save_log, mock_save_output, mock_factory
    ):
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            '# Plan\n```bash\nlitassist lookup "x" --mode irac\n```\n',
            {"total_tokens": 100},
        )
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_123.txt"

        runner = CliRunner()
        # No --yes needed: CliRunner stdin isatty() is False, so no prompt fires.
        with runner.isolated_filesystem():
            with open("case_facts.txt", "w") as f:
                f.write("Parties: A v B\nBackground: dispute")
            with open("affidavit_smith.pdf", "w") as f:
                f.write("x")
            with open("invoice_repairs.pdf", "w") as f:
                f.write("x")
            result = runner.invoke(caseplan, ["case_facts.txt", "--budget", "minimal"])
            assert result.exit_code == 0, result.output
            user_msg = _user_prompt(mock_client)

        assert "AVAILABLE SOURCE FILES" in user_msg
        assert "affidavit_smith.pdf" in user_msg
        assert "invoice_repairs.pdf" in user_msg

    @patch("litassist.commands.caseplan.core._is_interactive", return_value=True)
    @patch("litassist.commands.caseplan.plan_generator.LLMClientFactory")
    def test_confirm_gate_aborts_before_paid_call(
        self, mock_factory, _mock_interactive
    ):
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("case_facts.txt", "w") as f:
                f.write("Parties: A v B\nBackground: dispute")
            # Interactive + declining at the confirm -> Abort before any LLM call.
            result = runner.invoke(
                caseplan, ["case_facts.txt", "--budget", "minimal"], input="n\n"
            )

        assert result.exit_code != 0
        mock_factory.for_command.assert_not_called()

    @patch("litassist.commands.caseplan.core._is_interactive", return_value=True)
    @patch("litassist.commands.caseplan.plan_generator.LLMClientFactory")
    @patch("litassist.commands.caseplan.plan_generator.save_command_output")
    @patch("litassist.commands.caseplan.plan_generator.save_log")
    def test_yes_flag_skips_confirm(
        self, mock_save_log, mock_save_output, mock_factory, _mock_interactive
    ):
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            '# Plan\n```bash\nlitassist lookup "x" --mode irac\n```\n',
            {"total_tokens": 100},
        )
        mock_factory.for_command.return_value = mock_client
        mock_save_output.return_value = "outputs/caseplan_123.txt"

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("case_facts.txt", "w") as f:
                f.write("Parties: A v B\nBackground: dispute")
            # --yes proceeds even though _is_interactive() is True and no input.
            result = runner.invoke(
                caseplan, ["case_facts.txt", "--budget", "minimal", "--yes"]
            )

        assert result.exit_code == 0, result.output
        mock_factory.for_command.assert_called()
