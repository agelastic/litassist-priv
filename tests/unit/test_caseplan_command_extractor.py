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

    def test_orphan_option_line_not_merged_but_surfaced(self):
        # An option line with no trailing backslash is a separate (would-be) shell
        # line in bash, not a continuation. It must not be merged into the command
        # (which would change the workflow) nor silently dropped - it is surfaced.
        plan = _join(
            ["```bash", 'litassist lookup "contract"', "  --mode irac --comprehensive", "```"]
        )
        script, accepted_count, rejected = extract_cli_commands(plan)
        assert accepted_count == 1
        body = script.split("# End of extracted")[0]
        assert "--mode irac" not in body
        assert "litassist lookup contract" in body
        assert any("--mode irac" in r for r in rejected)

    def test_quoted_standalone_line_not_merged(self):
        # A standalone quoted line is its own (would-be) shell line, not an arg
        # of the preceding command; it must not be merged.
        plan = _join(
            [
                "```bash",
                'litassist lookup "x" --mode irac',
                '"some standalone note"',
                "```",
            ]
        )
        script, accepted_count, rejected = extract_cli_commands(plan)
        assert accepted_count == 1
        body = script.split("# End of extracted")[0]
        assert "some standalone note" not in body
        assert "litassist lookup x --mode irac" in body
        # Surfaced (fail-loud), not silently dropped.
        assert any("some standalone note" in r for r in rejected)

    def test_non_litassist_fenced_line_not_merged(self):
        # A bare-word line in a fence (a separate shell command in bash) must NOT
        # be merged into the preceding litassist command.
        plan = _join(
            [
                "```bash",
                'litassist lookup "x" --mode irac',
                "rm -rf outputs",
                "```",
            ]
        )
        script, accepted_count, _ = extract_cli_commands(plan)
        assert accepted_count == 1
        body = script.split("# End of extracted")[0]
        assert "rm -rf outputs" not in body
        assert "litassist lookup x --mode irac" in body

    def test_fence_comment_does_not_join_command(self):
        # A shell comment line inside a fence ends the command; it is not merged.
        plan = _join(
            [
                "```bash",
                "litassist lookup contract --mode irac",
                "# switch rationale: irac for structure",
                "```",
            ]
        )
        script, accepted_count, _ = extract_cli_commands(plan)
        assert accepted_count == 1
        assert "litassist lookup contract --mode irac" in script
        assert "switch rationale" not in script.split("# End of extracted")[0]

    def test_wrapped_arg_starting_with_litassist_not_split(self):
        # A wrapped arg/path that merely starts with "litassist" (e.g. a filename)
        # is NOT a new command; it must stay part of the command, not be split off.
        plan = _join(
            [
                "```bash",
                "litassist draft case_facts.txt",
                "  litassist_notes.txt --verify",
                "```",
            ]
        )
        script, accepted_count, rejected = extract_cli_commands(plan)
        # Only the draft command is accepted; the litassist_notes.txt line is a
        # would-be separate line - surfaced, not merged into the draft command.
        assert accepted_count == 1
        assert "litassist draft case_facts.txt" in script
        assert "litassist_notes.txt" not in script.split("# End of extracted")[0]
        assert any("litassist_notes.txt" in r for r in rejected)

    def test_separate_indented_commands_not_merged(self):
        # Two indented litassist commands are distinct, not a continuation.
        plan = _join(
            [
                "```bash",
                '  litassist lookup "a" --mode irac',
                '  litassist lookup "b" --mode irac',
                "```",
            ]
        )
        _, accepted_count, _ = extract_cli_commands(plan)
        assert accepted_count == 2

    def test_glob_pattern_is_quoted_for_internal_expansion(self):
        raw = "litassist counselnotes outputs/lookup_*.txt --extract all"
        plan = _join(["```bash", raw, "```"])
        script, accepted_count, _ = extract_cli_commands(plan)
        assert accepted_count == 1
        # shlex.join quotes the glob so litassist's own expander receives the
        # literal pattern (see expand_glob_patterns_callback).
        assert "'outputs/lookup_*.txt'" in script
