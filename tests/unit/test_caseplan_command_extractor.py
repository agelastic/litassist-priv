"""Unit tests for caseplan generated-command extraction and safety.

extract_cli_commands turns LLM plan text into an executable bash script. Because
the user is told to `bash` that script, every accepted command is round-tripped
through shlex so shell control characters cannot survive as live operators, and
the function reports how many real commands it accepted so the caller can fail
loud instead of saving a header-only script.
"""

import shlex

from litassist.commands.caseplan.command_extractor import extract_cli_commands


def _join(plan_lines):
    return "\n".join(plan_lines)


class TestExtractCliCommands:
    def test_returns_script_count_and_rejected(self):
        plan = _join(["```bash", 'litassist lookup "contract breach" --mode irac', "```"])
        script, accepted_count, rejected = extract_cli_commands(plan)
        assert isinstance(script, str)
        assert accepted_count == 1
        assert rejected == []
        # shlex.join drops redundant quotes around safe words
        assert "litassist lookup 'contract breach' --mode irac" in script

    def test_extracts_from_commands_label(self):
        """The prompt's worked examples use 'Commands: litassist ...' on one line."""
        plan = "Commands: litassist counselnotes outputs/lookup_x.txt --extract all"
        script, accepted_count, _ = extract_cli_commands(plan)
        assert accepted_count == 1
        assert "litassist counselnotes outputs/lookup_x.txt --extract all" in script

    def test_command_separator_is_neutralised(self):
        raw = 'litassist lookup "x"; rm -rf outputs'
        plan = _join(["```bash", raw, "```"])
        script, _, _ = extract_cli_commands(plan)
        # The dangerous separator must not survive as a live ' ; rm'
        assert "; rm" not in script
        # Whatever is written must be exactly the shlex round-trip of the input
        assert shlex.join(shlex.split(raw)) in script

    def test_command_substitution_is_neutralised(self):
        raw = 'litassist lookup "$(cat secret)"'
        plan = _join(["```bash", raw, "```"])
        script, _, _ = extract_cli_commands(plan)
        # The substitution is quoted inert, never written as a live $(...)
        assert shlex.join(shlex.split(raw)) in script
        assert '"$(cat secret)"' not in script

    def test_non_litassist_line_not_executable(self):
        plan = _join(["```bash", "echo hello", "rm -rf /", "```"])
        script, accepted_count, _ = extract_cli_commands(plan)
        assert accepted_count == 0
        assert "rm -rf /" not in script
        assert "echo hello" not in script

    def test_zero_commands_reported(self):
        plan = "# Litigation Plan\n## Case Assessment\nComplexity: MEDIUM\nNo commands here."
        _, accepted_count, _ = extract_cli_commands(plan)
        assert accepted_count == 0

    def test_trailing_backslash_before_fence_not_absorbed(self):
        # A command line ending with a stray backslash right before the closing
        # fence must not merge the fence into the command as an argument.
        plan = _join(
            ["```bash", 'litassist lookup "contract breach" --mode irac \\', "```"]
        )
        script, accepted_count, _ = extract_cli_commands(plan)
        assert accepted_count == 1
        assert "```" not in script.split("# End of extracted commands")[0]
        assert "litassist lookup 'contract breach' --mode irac" in script

    def test_glob_pattern_is_quoted_for_internal_expansion(self):
        raw = "litassist counselnotes outputs/lookup_*.txt --extract all"
        plan = _join(["```bash", raw, "```"])
        script, accepted_count, _ = extract_cli_commands(plan)
        assert accepted_count == 1
        # shlex.join quotes the glob so litassist's own expander receives the
        # literal pattern (see expand_glob_patterns_callback).
        assert "'outputs/lookup_*.txt'" in script
