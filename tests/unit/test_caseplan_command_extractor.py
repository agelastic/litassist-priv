"""Unit tests for caseplan generated-command extraction (Python runner).

extract_cli_commands turns LLM plan text into an executable PYTHON runner that
isolates each execution under a fresh outputs/run_<ts>/ dir. Steps run via
subprocess.run(args) with shell=False, so shell metacharacters are inert literal
arguments; every accepted command becomes a `run([...])` call with `outputs/` and
`case_facts` path tokens rewritten to os.path.join(run_dir, ...). The function
still reports the accepted count and the rejected (would-be) lines so the caller
can fail loud instead of saving an empty runner.
"""

from litassist.commands.caseplan.command_extractor import extract_cli_commands


def _join(plan_lines):
    return "\n".join(plan_lines)


def _script(plan):
    script, accepted, rejected = extract_cli_commands(plan)
    compile(script, "<runner>", "exec")  # the generated runner must be valid Python
    return script, accepted, rejected


class TestRunnerScaffold:
    def test_emitted_script_is_valid_python_with_run_dir_setup(self):
        script, _, _ = _script(
            _join(["```bash", 'litassist lookup "x" --mode irac', "```"])
        )
        assert script.startswith("#!/usr/bin/env python3")
        assert 'run_dir = os.path.join("outputs", "run_"' in script
        assert "os.makedirs(run_dir)" in script
        assert 'os.environ["LITASSIST_OUTPUT_DIR"] = run_dir' in script
        # seeds a baseline case_facts (the cwd source is copied, not mutated)
        assert "_seed = next(" in script
        assert 'shutil.copy(_seed, os.path.join(run_dir, "case_facts.txt"))' in script
        # runs steps without a shell -> metacharacters stay inert
        assert "subprocess.run(args)" in script
        assert "shell=True" not in script

    def test_seed_uses_the_given_case_facts_file(self):
        # The runner seeds the EXACT facts file caseplan was given (the facts the
        # plan was built for), falling back to a stable ./case_facts.txt.
        script, _, _ = extract_cli_commands(
            _join(["```bash", 'litassist lookup "x" --mode irac', "```"]),
            seed_facts="inputs/my_case_facts.txt",
        )
        compile(script, "<runner>", "exec")
        assert "'inputs/my_case_facts.txt'" in script
        assert '"case_facts.txt"' in script  # fallback baseline still present

    def test_count_and_rejected(self):
        script, accepted, rejected = _script(
            _join(
                ["```bash", 'litassist lookup "contract breach" --mode irac', "```"]
            )
        )
        assert accepted == 1
        assert rejected == []
        assert "run([" in script


class TestTokenRewriting:
    def test_outputs_glob_space_form_routed_to_run_dir(self):
        script, _, _ = _script(
            _join(
                [
                    "```bash",
                    "litassist counselnotes outputs/lookup_*.txt --extract all",
                    "```",
                ]
            )
        )
        assert "os.path.join(run_dir, 'lookup_*.txt')" in script
        assert "'outputs/lookup_*.txt'" not in script

    def test_strategies_and_case_facts_space_form_routed(self):
        script, _, _ = _script(
            _join(
                [
                    "```bash",
                    'litassist strategy case_facts.txt --outcome "win" '
                    "--strategies 'outputs/brainstorm_research_*.txt'",
                    "```",
                ]
            )
        )
        assert "os.path.join(run_dir, 'brainstorm_research_*.txt')" in script
        assert "os.path.join(run_dir, 'case_facts.txt')" in script

    def test_equals_form_path_option_routed(self):
        script, _, _ = _script(
            _join(
                [
                    "```bash",
                    "litassist brainstorm --facts case_facts.txt "
                    "--research=outputs/lookup_*.txt --output brainstorm_research",
                    "```",
                ]
            )
        )
        assert "'--research=' + os.path.join(run_dir, 'lookup_*.txt')" in script

    def test_output_prefix_not_rewritten_space_form(self):
        script, _, _ = _script(
            _join(
                [
                    "```bash",
                    "litassist brainstorm --facts case_facts.txt "
                    "--output brainstorm_creative",
                    "```",
                ]
            )
        )
        assert "'brainstorm_creative'" in script
        assert "os.path.join(run_dir, 'brainstorm_creative')" not in script

    def test_output_prefix_not_rewritten_equals_form(self):
        script, _, _ = _script(
            _join(
                [
                    "```bash",
                    "litassist brainstorm --facts case_facts.txt "
                    "--output=brainstorm_creative",
                    "```",
                ]
            )
        )
        assert "'--output=brainstorm_creative'" in script

    def test_dot_slash_outputs_normalised(self):
        script, _, _ = _script(
            _join(
                [
                    "```bash",
                    "litassist counselnotes ./outputs/lookup_x.txt --extract all",
                    "```",
                ]
            )
        )
        assert "os.path.join(run_dir, 'lookup_x.txt')" in script

    def test_source_doc_input_stays_literal(self):
        script, _, _ = _script(
            _join(["```bash", "litassist extractfacts bank_statements.pdf", "```"])
        )
        assert "'bank_statements.pdf'" in script
        assert "run_dir, 'bank_statements.pdf'" not in script


class TestSafety:
    def test_separator_is_inert_single_command(self):
        script, accepted, _ = _script(
            _join(["```bash", 'litassist lookup "x" ; rm -rf outputs', "```"])
        )
        assert accepted == 1
        assert script.count("run([") == 1  # one command, not two
        assert "subprocess.run(args)" in script and "shell=True" not in script
        assert "';'" in script  # separator is a literal arg, not an operator

    def test_command_substitution_inert(self):
        script, _, _ = _script(
            _join(["```bash", 'litassist lookup "$(cat secret)"', "```"])
        )
        assert "'$(cat secret)'" in script  # literal arg, never a live $(...)
        assert "shell=True" not in script

    def test_non_litassist_lines_not_executable(self):
        script, accepted, _ = _script(
            _join(["```bash", "echo hello", "rm -rf /", "```"])
        )
        assert accepted == 0
        assert "rm -rf /" not in script
        assert "echo hello" not in script


class TestParsingContracts:
    def test_commands_label(self):
        _, accepted, _ = _script(
            "Commands: litassist counselnotes outputs/lookup_x.txt --extract all"
        )
        assert accepted == 1

    def test_zero_commands(self):
        _, accepted, _ = _script("# Plan\nNo commands here.")
        assert accepted == 0

    def test_trailing_backslash_before_fence(self):
        script, accepted, _ = _script(
            _join(
                ["```bash", 'litassist lookup "contract breach" --mode irac \\', "```"]
            )
        )
        assert accepted == 1
        assert "```" not in script

    def test_orphan_option_surfaced_not_merged(self):
        script, accepted, rejected = _script(
            _join(
                [
                    "```bash",
                    'litassist lookup "contract"',
                    "  --mode irac --comprehensive",
                    "```",
                ]
            )
        )
        assert accepted == 1
        assert "--mode irac" not in script
        assert any("--mode irac" in r for r in rejected)

    def test_quoted_standalone_surfaced(self):
        script, accepted, rejected = _script(
            _join(
                [
                    "```bash",
                    'litassist lookup "x" --mode irac',
                    '"some standalone note"',
                    "```",
                ]
            )
        )
        assert accepted == 1
        assert "some standalone note" not in script
        assert any("some standalone note" in r for r in rejected)

    def test_fence_comment_ends_command(self):
        script, accepted, _ = _script(
            _join(
                [
                    "```bash",
                    "litassist lookup contract --mode irac",
                    "# switch rationale",
                    "```",
                ]
            )
        )
        assert accepted == 1
        assert "switch rationale" not in script

    def test_wrapped_litassist_arg_not_split(self):
        script, accepted, rejected = _script(
            _join(
                [
                    "```bash",
                    "litassist draft case_facts.txt",
                    "  litassist_notes.txt --verify",
                    "```",
                ]
            )
        )
        assert accepted == 1
        assert "litassist_notes.txt" not in script
        assert any("litassist_notes.txt" in r for r in rejected)

    def test_two_indented_commands(self):
        _, accepted, _ = _script(
            _join(
                [
                    "```bash",
                    '  litassist lookup "a" --mode irac',
                    '  litassist lookup "b" --mode irac',
                    "```",
                ]
            )
        )
        assert accepted == 2
