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
