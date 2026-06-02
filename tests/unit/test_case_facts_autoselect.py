"""Auto-resolution of the case-facts file when the argument is omitted.

caseplan and brainstorm cover this elsewhere; these pin the remaining commands
that take case facts (strategy, barbrief, draft). Each is invoked with NO
case-facts argument in an isolated filesystem containing a valid case_facts.txt.

The resolver echoes "Using case facts: <name>" only on a successful pick, and it
runs at the very top of each command (before any LLM call), so asserting that
line is in the output proves the omitted argument was made optional and the
latest case_facts*.txt was resolved. Full downstream execution is covered by
each command's own tests; here LLMClientFactory is mocked only to keep the run
offline.
"""

from unittest.mock import patch, MagicMock

from click.testing import CliRunner

from litassist.commands.strategy import strategy
from litassist.commands.barbrief import barbrief
from litassist.commands.draft import draft

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
VALID_FACTS = "\n".join(f"{h}: placeholder" for h in _HEADINGS)


def _mock_factory(mock_factory, content):
    client = MagicMock()
    client.complete.return_value = (content, {"total_tokens": 100})
    mock_factory.for_command.return_value = client


def _write_valid_facts():
    with open("case_facts.txt", "w") as f:
        f.write(VALID_FACTS)


@patch("litassist.commands.strategy.core.LLMClientFactory")
def test_strategy_auto_resolves_case_facts(mock_factory):
    _mock_factory(mock_factory, "## STRATEGIC OPTIONS\nx")
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_valid_facts()
        result = runner.invoke(strategy, ["--outcome", "Win", "--noverify"])
    assert "Using case facts: case_facts.txt" in result.output
    assert "Missing argument" not in result.output


@patch("litassist.commands.barbrief.core.LLMClientFactory")
def test_barbrief_auto_resolves_case_facts(mock_factory):
    _mock_factory(mock_factory, "Brief content")
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_valid_facts()
        result = runner.invoke(barbrief, ["--hearing-type", "trial"])
    assert "Using case facts: case_facts.txt" in result.output
    assert "Missing argument" not in result.output


@patch("litassist.commands.draft.core.LLMClientFactory")
def test_draft_auto_resolves_case_facts(mock_factory):
    _mock_factory(mock_factory, "Draft content")
    runner = CliRunner()
    with runner.isolated_filesystem():
        _write_valid_facts()
        result = runner.invoke(draft, ["Draft a statement of claim", "--noverify"])
    assert "Using case facts: case_facts.txt" in result.output
    assert "Missing argument" not in result.output


def test_resolver_searches_env_dir_when_set(tmp_path, monkeypatch):
    # Inside a caseplan runner, auto-resolution looks in the per-run dir, not the
    # cwd - so a cwd decoy is never chosen over the run's own case_facts.
    from litassist.utils.case_facts import resolve_case_facts_file

    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "outputs" / "run_x"
    run_dir.mkdir(parents=True)
    (run_dir / "case_facts.txt").write_text("run facts")
    (tmp_path / "case_facts.txt").write_text("cwd decoy")
    monkeypatch.setenv("LITASSIST_OUTPUT_DIR", str(run_dir))

    assert resolve_case_facts_file() == str(run_dir / "case_facts.txt")
    # The env-UNSET cwd path is covered by the command-level auto-resolve tests
    # above (each runs with no LITASSIST_OUTPUT_DIR), so it is not re-asserted here.


def test_resolver_finds_md_and_prefers_newest(tmp_path, monkeypatch):
    # case_facts is now written as .md; the resolver must find .md files, and when
    # both a legacy .txt and a newer timestamped .md exist, recency decides.
    from litassist.utils.case_facts import resolve_case_facts_file

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LITASSIST_OUTPUT_DIR", raising=False)

    # Only a .md present -> it is found without needing any .txt fallback.
    (tmp_path / "case_facts.md").write_text(VALID_FACTS)
    assert resolve_case_facts_file() == "case_facts.md"

    # A future-dated timestamped .md outranks a plain legacy .txt by recency
    # (filename timestamp beats mtime), proving both extensions are globbed.
    (tmp_path / "case_facts.txt").write_text(VALID_FACTS)
    (tmp_path / "case_facts_20990101_000000.md").write_text(VALID_FACTS)
    assert resolve_case_facts_file() == "case_facts_20990101_000000.md"
