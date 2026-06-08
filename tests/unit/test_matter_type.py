"""Tests for matter-type posture (Phase 1): parsing, resolution, posture, B1.

Covers the helpers in litassist.utils.case_facts plus the B1 fix that lets the
10-heading validator tolerate parenthetical heading qualifiers.
"""

from unittest.mock import patch, MagicMock

import pytest
from click.testing import CliRunner

from litassist.commands.strategy.core import strategy
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


def test_disciplinary_posture_is_regulator_framed():
    posture = matter_type_posture("disciplinary").lower()
    assert "commissioner" in posture
    assert "not a court" in posture


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


def test_validator_still_rejects_missing_heading():
    facts = "## 1. Parties:\n## 2. Background:\n"  # missing the rest
    assert validate_case_facts_format(facts) is False


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
