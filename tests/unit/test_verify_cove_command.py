# noqa: E402
"""
Unit tests for the standalone 'verify-cove' command.

Covers:
- CLI registration of the 'verify-cove' command (with hyphen)
- Basic invocation flow and interactions (read, run_cove_verification, save outputs)
"""

from unittest.mock import patch
from click.testing import CliRunner


class TestVerifyCoveCommand:
    """Tests for verify-cove command behavior."""

    def test_command_is_registered_in_cli(self):
        """Verify that 'verify-cove' is registered via register_commands."""
        from litassist.cli import cli  # litassist/cli.py:main()
        from litassist.commands import (
            register_commands,
        )  # litassist/commands/__init__.py

        # Clear and re-register commands
        cli.commands = {}
        register_commands(cli)

        assert "verify-cove" in cli.commands, "verify-cove command should be registered"

    def test_verify_cove_basic_invocation(self, tmp_path):
        """Verify that 'verify-cove' runs and saves outputs."""
        # Prepare temp file
        file_path = tmp_path / "document.txt"
        file_path.write_text("Test content for CoVe")

        # Build CLI with commands
        from litassist.cli import cli
        from litassist.commands import register_commands

        cli.commands = {}
        register_commands(cli)

        # Mock dependencies inside command module
        with (
            patch("litassist.commands.verify_cove.document_reader.read_document") as mock_read,
            patch("litassist.commands.verify_cove.cove_runner.run_cove_verification") as mock_cove,
            patch("litassist.commands.verify_cove.cove_runner.save_command_output") as mock_save,
            patch("litassist.commands.verify_cove.core.save_log") as _mock_log,
        ):
            mock_read.return_value = "Original content to verify"

            # Mock CoVe result to force regeneration path
            cove_results = {
                "cove": {
                    "passed": False,
                    "regenerated": True,
                    "issues": "Found issues",
                    "questions": "Q",
                    "answers": "A",
                }
            }
            mock_cove.return_value = ("Regenerated content", cove_results)
            mock_save.return_value = "output.txt"

            runner = CliRunner()
            result = runner.invoke(cli, ["verify-cove", str(file_path)])

        # Assertions
        assert result.exit_code == 0, f"verify-cove failed: {result.output}"
        # The command echoes a status line with 'Chain of Verification complete'
        assert "Chain of Verification complete" in result.output
        # Should call CoVe pipeline once
        mock_cove.assert_called_once()
        # Should save at least the CoVe report (and regenerated doc in this branch)
        assert mock_save.call_count >= 1

    def test_verify_cove_with_reference_option(self, tmp_path):
        """Verify that '--reference' is accepted and forwarded to processing."""
        file_path = tmp_path / "document.txt"
        file_path.write_text("Test content")

        from litassist.cli import cli
        from litassist.commands import register_commands

        cli.commands = {}
        register_commands(cli)

        with (
            patch("litassist.commands.verify_cove.document_reader.read_document") as mock_read,
            patch(
                "litassist.commands.verify_cove.document_reader.process_reference_files"
            ) as mock_refs,
            patch("litassist.commands.verify_cove.cove_runner.run_cove_verification") as mock_cove,
            patch("litassist.commands.verify_cove.cove_runner.save_command_output") as mock_save,
            patch("litassist.commands.verify_cove.core.save_log") as _mock_log,
        ):
            mock_read.return_value = "Original content"
            mock_refs.return_value = ("=== ref.txt ===\n\nRef content\n\n", ["ref.txt"])

            mock_cove.return_value = (
                "Verified content",
                {"cove": {"passed": True, "regenerated": False, "issues": None}},
            )
            mock_save.return_value = "output.txt"

            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["verify-cove", str(file_path), "--reference", "refs/*.txt"],
            )

        assert result.exit_code == 0, (
            f"verify-cove with --reference failed: {result.output}"
        )
        mock_refs.assert_called_once()
        mock_cove.assert_called_once()
        assert mock_save.call_count >= 1
