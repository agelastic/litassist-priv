"""Tests for matter-type posture (Phase 1): parsing, resolution, posture, B1.

Covers the helpers in litassist.utils.case_facts plus the B1 fix that lets the
10-heading validator tolerate parenthetical heading qualifiers.
"""

from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from litassist.commands.strategy.core import strategy
from litassist.commands.barbrief import barbrief
from litassist.commands.caseplan import caseplan
from litassist.commands.counselnotes import counselnotes
from litassist.commands.brainstorm import brainstorm
from litassist.utils.case_facts import (
    KNOWN_MATTER_TYPES,
    DEFAULT_MATTER_TYPE,
    read_matter_type,
    resolve_matter_type,
    normalise_matter_type,
    matter_type_posture,
    validate_case_facts_format,
)
from litassist.prompts import PROMPTS


# --- read_matter_type ------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("Matter type: disciplinary", "disciplinary"),
        ("## 8. Jurisdiction\nMatter type: FOI\nOLSC", "foi"),
        ("8. **Matter type**: Civil\n", "civil"),
        ("MATTER TYPE : criminal", "criminal"),
        ("no matter type line here", None),
        ("", None),
    ],
)
def test_read_matter_type(text, expected):
    assert read_matter_type(text) == expected


# --- resolve_matter_type (case_facts path) ---------------------------------

def test_resolve_known_returns_no_warning():
    mt, warning = resolve_matter_type("Matter type: disciplinary")
    assert mt == "disciplinary"
    assert warning is None


def test_resolve_absent_defaults_civil_with_warning():
    mt, warning = resolve_matter_type("Parties: ...\nJurisdiction: NCAT")
    assert mt == DEFAULT_MATTER_TYPE == "civil"
    assert warning and "civil" in warning
    # case_facts path remedy mentions the file, not the flag
    assert "case facts" in warning.lower()


def test_resolve_unknown_defaults_civil_with_warning():
    mt, warning = resolve_matter_type("Matter type: bankruptcy")
    assert mt == "civil"
    assert warning and "bankruptcy" in warning


# --- normalise_matter_type (flag path) -------------------------------------

def test_normalise_valid():
    assert normalise_matter_type("foi") == ("foi", None)


def test_normalise_none_defaults_civil_warns_about_flag():
    mt, warning = normalise_matter_type(None)
    assert mt == "civil"
    assert warning and "--matter-type" in warning


def test_normalise_unknown_defaults_civil():
    mt, warning = normalise_matter_type("widgets")
    assert mt == "civil"
    assert warning and "widgets" in warning


# --- matter_type_posture ----------------------------------------------------

def test_all_known_types_have_a_posture():
    for mt in KNOWN_MATTER_TYPES:
        posture = matter_type_posture(mt)
        assert isinstance(posture, str) and posture.strip()


def test_unknown_posture_falls_back_to_civil():
    assert matter_type_posture("nonsense") == matter_type_posture("civil")


# --- B1: validator tolerates parenthetical qualifiers ----------------------

def test_validator_accepts_parenthetical_qualifiers():
    facts = (
        "## 1. Parties:\n"
        "## 2. Background:\n"
        "## 3. Key Events (Chronological):\n"
        "## 4. Legal Issues:\n"
        "## 5. Evidence Available:\n"
        "## 6. **Opposing Arguments (DTL's Position)**:\n"
        "## 7. Procedural History:\n"
        "## 8. Jurisdiction:\nMatter type: disciplinary\n"
        "## 9. Applicable Law:\n"
        "## 10. Client Objectives:\n"
    )
    assert validate_case_facts_format(facts) is True


# --- contract carries the Matter type line ---------------------------------

def test_format_contract_includes_matter_type():
    contract = PROMPTS.get_format_template("case_facts_10_heading")
    assert "Matter type:" in contract


# --- command-level: posture reaches the system message (real prompts) ------

_DISCIPLINARY_FACTS = (
    "# Matter Extraction\n"
    "## 1. Parties:\nComplainant v Solicitor\n"
    "## 2. Background:\nFee and conduct dispute with a former solicitor\n"
    "## 3. Key Events:\nComplaint lodged with the regulator\n"
    "## 4. Legal Issues:\nWhether the conduct was unsatisfactory professional conduct\n"
    "## 5. Evidence Available:\nInvoices and correspondence\n"
    "## 6. Opposing Arguments:\nThe solicitor denies wrongdoing\n"
    "## 7. Procedural History:\nNo court proceedings\n"
    "## 8. Jurisdiction:\nMatter type: disciplinary\nNSW Office of the Legal Services Commissioner\n"
    "## 9. Applicable Law:\nLegal Profession Uniform Law (NSW)\n"
    "## 10. Client Objectives:\nA costs refund and a conduct finding\n"
)


@patch("litassist.commands.strategy.core.LLMClientFactory.for_command")
@patch("litassist.commands.strategy.file_handler.save_command_output")
@patch("litassist.commands.strategy.file_handler.save_log")
@patch("litassist.commands.strategy.core.verify_content_if_needed")
def test_strategy_prepends_matter_posture_to_system_message(
    mock_verify, mock_save_log, mock_save_output, mock_factory
):
    """The disciplinary posture must appear in the system message strategy sends
    (real prompts, capturing mock client)."""
    mock_verify.return_value = ("verified content", False, None)
    mock_save_output.return_value = "outputs/strategy_test.md"

    mock_client = MagicMock()
    mock_client.model = "test-model"
    mock_client.complete.return_value = (
        "## OPTION 1: Lodge the complaint\nDetailed content...",
        {"total_tokens": 100, "prompt_tokens": 60, "completion_tokens": 40},
    )
    mock_client.validate_citations.return_value = []
    mock_factory.return_value = mock_client

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("case_facts.md", "w") as f:
            f.write(_DISCIPLINARY_FACTS)
        result = runner.invoke(
            strategy, ["case_facts.md", "--outcome", "Obtain a costs refund"]
        )

    assert result.exit_code == 0, result.output
    system_messages = [
        call.args[0][0]["content"] for call in mock_client.complete.call_args_list
    ]
    assert system_messages, "strategy never called client.complete"
    assert any(
        "not a court" in s.lower() and "commissioner" in s.lower()
        for s in system_messages
    ), "disciplinary posture not found in any system message"


# --- command-level: posture reaches the OTHER framing commands ---------------
#
# Each command resolves matter_type and prepends the posture into a
# {"role": "system"} message its generator sends. These tests run the real
# command with a capturing mock client (real prompts) and assert the
# disciplinary posture lands on the wire -- guarding BOTH seams offline:
#   (1) core resolves matter_type and threads the posture, and
#   (2) the generator actually prepends it to the system message.
# A broken seam OR a deleted regulator framing in matter_types.yaml fails here.


def _system_messages(mock_client):
    """Every system-role message content passed to a mock client's complete()."""
    messages = []
    for call in mock_client.complete.call_args_list:
        sent = call.args[0]
        for entry in sent:
            if isinstance(entry, dict) and entry.get("role") == "system":
                messages.append(entry["content"])
    return messages


def _assert_disciplinary_posture(system_messages):
    assert system_messages, "command never called client.complete with a system message"
    assert any(
        "not a court" in s.lower() and "commissioner" in s.lower()
        for s in system_messages
    ), "disciplinary posture did not reach any system message"


@patch("litassist.commands.barbrief.document_reader.read_document")
@patch("litassist.commands.barbrief.core.LLMClientFactory")
@patch("litassist.commands.barbrief.core.save_command_output")
def test_barbrief_prepends_matter_posture(mock_save, mock_factory, mock_read):
    mock_read.return_value = _DISCIPLINARY_FACTS
    mock_save.return_value = "outputs/barbrief_directions_123.txt"

    mock_client = MagicMock()
    mock_client.model = "test-model"
    mock_client.complete.return_value = ("Brief content", {"total_tokens": 1000})
    mock_client.validate_citations.return_value = []
    mock_factory.for_command.return_value = mock_client

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("case_facts.md", "w") as f:
            f.write("dummy")  # read_document is mocked
        result = runner.invoke(
            barbrief, ["case_facts.md", "--hearing-type", "directions"]
        )

    assert result.exit_code == 0, result.output
    _assert_disciplinary_posture(_system_messages(mock_client))


@patch("litassist.commands.caseplan.budget_assessor.LLMClientFactory")
@patch("litassist.commands.caseplan.budget_assessor.save_command_output")
@patch("litassist.commands.caseplan.budget_assessor.save_log")
def test_caseplan_assessment_prepends_matter_posture(
    mock_save_log, mock_save_output, mock_factory, tmp_path
):
    case_facts = tmp_path / "case_facts.md"
    case_facts.write_text(_DISCIPLINARY_FACTS)

    mock_client = MagicMock()
    mock_client.complete.return_value = (
        "SUMMARY: Medium complexity\nRECOMMENDATION: standard\nJUSTIFICATION: ...",
        {"total_tokens": 500},
    )
    mock_factory.for_command.return_value = mock_client
    mock_save_output.return_value = "outputs/caseplan_assessment_123.txt"

    result = CliRunner().invoke(caseplan, [str(case_facts)])

    assert result.exit_code == 0, result.output
    _assert_disciplinary_posture(_system_messages(mock_client))


@patch("litassist.commands.caseplan.plan_generator.LLMClientFactory")
@patch("litassist.commands.caseplan.plan_generator.save_command_output")
@patch("litassist.commands.caseplan.plan_generator.save_log")
def test_caseplan_full_plan_prepends_matter_posture(
    mock_save_log, mock_save_output, mock_factory, tmp_path
):
    case_facts = tmp_path / "case_facts.md"
    case_facts.write_text(_DISCIPLINARY_FACTS)

    mock_client = MagicMock()
    mock_client.complete.return_value = (
        "# Litigation Plan\n## Case Assessment\nComplexity: MEDIUM\n",
        {"total_tokens": 1000},
    )
    mock_factory.for_command.return_value = mock_client
    mock_save_output.return_value = "outputs/caseplan_123.txt"

    result = CliRunner().invoke(caseplan, [str(case_facts), "--budget", "minimal"])

    assert result.exit_code == 0, result.output
    _assert_disciplinary_posture(_system_messages(mock_client))


@patch("litassist.commands.counselnotes.document_processor.read_document")
@patch(
    "litassist.commands.counselnotes.document_processor.LLMClientFactory.get_input_budget_for_command"
)
@patch("litassist.commands.counselnotes.core.show_command_completion")
@patch("litassist.commands.counselnotes.core.save_log")
@patch("litassist.commands.counselnotes.core.save_command_output")
@patch("litassist.commands.counselnotes.core.LLMClientFactory")
def test_counselnotes_prepends_matter_posture_from_flag(
    mock_factory, mock_save, mock_log, mock_completion, mock_budget, mock_read
):
    # counselnotes takes no case_facts, so the posture comes via --matter-type.
    mock_budget.return_value = 10000
    mock_read.return_value = "Some legal document content"
    mock_save.return_value = "output_file.md"

    mock_client = MagicMock()
    mock_client.model = "test-model"
    mock_client.complete.return_value = (
        "Strategic analysis result",
        {"total_tokens": 100, "prompt_tokens": 60, "completion_tokens": 40},
    )
    mock_client.validate_citations.return_value = []
    mock_factory.for_command.return_value = mock_client

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("doc.md", "w") as f:
            f.write("dummy")  # read_document is mocked
        result = runner.invoke(counselnotes, ["doc.md", "--matter-type", "disciplinary"])

    assert result.exit_code == 0, result.output
    _assert_disciplinary_posture(_system_messages(mock_client))


@patch("litassist.citation.verify.verify_all_citations", return_value=([], []))
@patch("litassist.commands.brainstorm.analysis_generator.LLMClientFactory")
@patch("litassist.commands.brainstorm.unorthodox_generator.LLMClientFactory")
@patch("litassist.commands.brainstorm.orthodox_generator.LLMClientFactory")
@patch("litassist.commands.brainstorm.core.LLMClientFactory")
@patch("litassist.commands.brainstorm.core.save_command_output")
@patch("litassist.commands.brainstorm.core.save_log")
def test_brainstorm_prepends_matter_posture_to_all_generators(
    mock_save_log,
    mock_save_output,
    mock_factory_core,
    mock_factory_orth,
    mock_factory_unorth,
    mock_factory_analysis,
    mock_verify_citations,
):
    """Posture must reach all three brainstorm generators; also exercises the
    new --side complainant value end-to-end."""

    def _client(content):
        client = MagicMock()
        client.model = "test/mock-model"
        client.complete.return_value = (content, {"total_tokens": 300})
        client.validate_citations.return_value = []
        return client

    orthodox_client = _client("## ORTHODOX\n### 1. Lodge the complaint\nBasis: LPUL")
    unorthodox_client = _client("## UNORTHODOX\n### 1. Media pressure\nBasis: leverage")
    analysis_client = _client("## ANALYSIS\nTop strategy: lodge the complaint")
    analysis_client.verify.return_value = "No corrections needed"

    verification_client = MagicMock()
    verification_client.model = "test/mock-model"
    verification_client.verify.return_value = ("## UNORTHODOX\n### 1. Media pressure", {})

    mock_factory_orth.for_command.return_value = orthodox_client
    mock_factory_unorth.for_command.side_effect = [
        unorthodox_client,  # generation
        verification_client,  # verification pass
    ]
    mock_factory_analysis.for_command.return_value = analysis_client
    mock_factory_core.get_input_budget_for_command.return_value = 10_000_000
    mock_factory_core.for_command.side_effect = [
        orthodox_client,  # regeneration slots / final citation check
        unorthodox_client,
        analysis_client,
    ]
    mock_save_output.side_effect = lambda *a, **k: "brainstorm_output.txt"

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("facts.md", "w") as f:
            f.write(_DISCIPLINARY_FACTS)
        result = runner.invoke(
            brainstorm,
            ["--facts", "facts.md", "--side", "complainant", "--area", "administrative"],
        )

    assert result.exit_code == 0, result.output
    # All three generators must carry the regulator posture.
    _assert_disciplinary_posture(_system_messages(orthodox_client))
    _assert_disciplinary_posture(_system_messages(unorthodox_client))
    _assert_disciplinary_posture(_system_messages(analysis_client))
