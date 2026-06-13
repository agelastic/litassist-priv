"""Unit tests for the verify --cross-check multi-model ensemble stage."""

import sys
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

# Mock pdfplumber to avoid import errors in the test environment (mirrors
# test_verify_command.py).
sys.modules.setdefault("pdfplumber", Mock())

from litassist.commands.verify import verify  # noqa: E402
from litassist.commands.verify.core import run_verification_workflow  # noqa: E402
from litassist.commands.verify.ensemble import (  # noqa: E402
    parse_arbiter_report,
    run_cross_check,
    PANEL_ROLES,
    ARBITER_ROLE,
)

_PANEL_MODELS = {
    "crosscheck-claude": "anthropic/claude-sonnet-4.6",
    "crosscheck-gpt5": "openai/gpt-5.5",
    "crosscheck-o3": "openai/o3-pro",
    "crosscheck-arbiter": "anthropic/claude-opus-4.7",
}

_PANEL_REVIEW = (
    "## FINDINGS\nNo issues found.\n## REASONING PATH\nStraightforward.\n"
    "## VERDICT SUMMARY\nThe document is sound."
)


def _arbiter(level="LOW", confidence="Reasonable confidence in the document."):
    return (
        "=== AGREEMENT ===\nAll reviewers agreed on the framing.\n"
        f"=== DISAGREEMENTS ===\nDISAGREEMENT LEVEL: {level}\nMinor wording only.\n"
        "=== FLAGGED FOR HUMAN REVIEW ===\nNone.\n"
        f"=== CONFIDENCE ===\n{confidence}"
    )


def _make_factory(arbiter_text=None, panel_text=_PANEL_REVIEW, store=None):
    """Return a for_command side-effect producing per-role mock clients."""
    arbiter_text = arbiter_text if arbiter_text is not None else _arbiter()

    def for_command(role):
        client = Mock()
        client.model = _PANEL_MODELS[role]
        text = arbiter_text if role == ARBITER_ROLE else panel_text
        client.complete.return_value = (
            text,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        if store is not None:
            store.append((role, client))
        return client

    return for_command


# --------------------------------------------------------------------------- #
# parse_arbiter_report (pure)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("level", ["NONE", "LOW", "MEDIUM", "HIGH"])
def test_parse_happy_path(level):
    sections, parsed = parse_arbiter_report(_arbiter(level=level))
    assert parsed == level
    assert sections["confidence"] == "Reasonable confidence in the document."
    assert set(sections) == {"agreement", "disagreements", "flagged", "confidence"}


def test_parse_tolerates_leading_prose_and_case():
    text = "Here is my report.\n" + _arbiter(level="high")
    sections, parsed = parse_arbiter_report(text)
    assert parsed == "HIGH"
    assert "agreed on the framing" in sections["agreement"]


@pytest.mark.parametrize(
    "marker",
    [
        "=== AGREEMENT ===",
        "=== DISAGREEMENTS ===",
        "=== FLAGGED FOR HUMAN REVIEW ===",
        "=== CONFIDENCE ===",
    ],
)
def test_parse_missing_section_raises(marker):
    broken = _arbiter().replace(marker, "=== REMOVED ===")
    with pytest.raises(ValueError):
        parse_arbiter_report(broken)


def test_parse_out_of_order_raises():
    swapped = (
        "=== DISAGREEMENTS ===\nDISAGREEMENT LEVEL: LOW\nx\n"
        "=== AGREEMENT ===\ny\n"
        "=== FLAGGED FOR HUMAN REVIEW ===\nNone.\n"
        "=== CONFIDENCE ===\nok"
    )
    with pytest.raises(ValueError):
        parse_arbiter_report(swapped)


def test_parse_missing_level_line_raises():
    no_level = _arbiter().replace("DISAGREEMENT LEVEL: LOW\n", "")
    with pytest.raises(ValueError):
        parse_arbiter_report(no_level)


def test_parse_malformed_level_raises():
    bad = _arbiter().replace("DISAGREEMENT LEVEL: LOW", "DISAGREEMENT LEVEL: SEVERE")
    with pytest.raises(ValueError):
        parse_arbiter_report(bad)


def test_parse_stray_pre_agreement_disagreements_raises():
    # A stray DISAGREEMENTS block carrying HIGH before the real AGREEMENT must not
    # be silently downgraded to the later LOW: duplicate markers are rejected.
    spoof = (
        "=== DISAGREEMENTS ===\nDISAGREEMENT LEVEL: HIGH\nstray\n"
        + _arbiter(level="LOW")
    )
    with pytest.raises(ValueError):
        parse_arbiter_report(spoof)


def test_parse_two_level_lines_raises():
    doubled = _arbiter(level="LOW").replace(
        "DISAGREEMENT LEVEL: LOW\n",
        "DISAGREEMENT LEVEL: LOW\nDISAGREEMENT LEVEL: HIGH\n",
    )
    with pytest.raises(ValueError):
        parse_arbiter_report(doubled)


# --------------------------------------------------------------------------- #
# run_cross_check (mocked factory)
# --------------------------------------------------------------------------- #

@patch("litassist.commands.verify.ensemble.save_command_output", return_value="outputs/verify_crosscheck.md")
@patch("litassist.commands.verify.ensemble.LLMClientFactory")
def test_panel_uses_fixed_roles_and_skips_citation_verification(mock_factory, _mock_save):
    store = []
    mock_factory.for_command.side_effect = _make_factory(store=store)

    run_cross_check("the document", "doc.md", None, None)

    requested = [role for role, _ in store]
    assert requested == list(PANEL_ROLES) + [ARBITER_ROLE]
    for _role, client in store:
        _args, kwargs = client.complete.call_args
        assert kwargs.get("skip_citation_verification") is True


@patch("litassist.commands.verify.ensemble.save_command_output", return_value="outputs/verify_crosscheck.md")
@patch("litassist.commands.verify.ensemble.LLMClientFactory")
def test_high_disagreement_warns(mock_factory, _mock_save, capsys):
    mock_factory.for_command.side_effect = _make_factory(arbiter_text=_arbiter(level="HIGH"))
    result = run_cross_check("doc", "doc.md", None, None)
    assert result["disagreement_level"] == "HIGH"
    out = capsys.readouterr().out
    assert "HIGH disagreement" in out


@patch("litassist.commands.verify.ensemble.save_command_output", return_value="outputs/verify_crosscheck.md")
@patch("litassist.commands.verify.ensemble.LLMClientFactory")
def test_none_disagreement_no_warning(mock_factory, _mock_save, capsys):
    mock_factory.for_command.side_effect = _make_factory(arbiter_text=_arbiter(level="NONE"))
    run_cross_check("doc", "doc.md", None, None)
    assert "HIGH disagreement" not in capsys.readouterr().out


@patch("litassist.commands.verify.ensemble.save_command_output")
@patch("litassist.commands.verify.ensemble.LLMClientFactory")
def test_report_naming_default_and_output_prefix(mock_factory, mock_save):
    mock_save.return_value = "outputs/x.md"
    mock_factory.for_command.side_effect = _make_factory()

    run_cross_check("doc", "mydoc.md", None, None)
    assert mock_save.call_args.args[0] == "verify_crosscheck"

    mock_save.reset_mock()
    mock_factory.for_command.side_effect = _make_factory()
    run_cross_check("doc", "mydoc.md", None, "myprefix")
    assert mock_save.call_args.args[0] == "myprefix_crosscheck"


@patch("litassist.commands.verify.ensemble.save_command_output", return_value="outputs/verify_crosscheck.md")
@patch("litassist.commands.verify.ensemble.LLMClientFactory")
def test_reference_context_reaches_panel(mock_factory, _mock_save):
    store = []
    mock_factory.for_command.side_effect = _make_factory(store=store)
    run_cross_check("doc", "doc.md", "EXHIBIT A says X", None)
    # First panel client's user message should contain the reference text.
    _role, first_client = store[0]
    user_msg = first_client.complete.call_args.args[0][1]["content"]
    assert "EXHIBIT A says X" in user_msg


@patch("litassist.commands.verify.ensemble.save_command_output", return_value="outputs/verify_crosscheck.md")
@patch("litassist.commands.verify.ensemble.LLMClientFactory")
def test_totals_and_cost_printed(mock_factory, _mock_save, capsys):
    mock_factory.for_command.side_effect = _make_factory()
    result = run_cross_check("doc", "doc.md", None, None)
    # 4 calls * 150 tokens.
    assert result["total_usage"]["total_tokens"] == 600
    out = capsys.readouterr().out
    assert "Cross-check total tokens used: 600" in out
    assert "[COST]" in out


# --------------------------------------------------------------------------- #
# core.py stage integration
# --------------------------------------------------------------------------- #

@patch("litassist.commands.verify.core.save_log")
@patch("litassist.commands.verify.ensemble.save_command_output", return_value="outputs/verify_crosscheck.md")
@patch("litassist.commands.verify.ensemble.LLMClientFactory")
def test_malformed_arbiter_fails_stage_nonzero(mock_factory, _mock_save, _mock_log, tmp_path):
    mock_factory.for_command.side_effect = _make_factory(arbiter_text="not a valid report")
    doc = tmp_path / "doc.md"
    doc.write_text("Some legal content.")
    with pytest.raises(Exception) as exc:
        run_verification_workflow(
            file=str(doc),
            citations=False,
            soundness=False,
            reasoning=False,
            cove=False,
            cross_check=True,
        )
    assert "Cross-check" in str(exc.value)


# --------------------------------------------------------------------------- #
# CLI composition
# --------------------------------------------------------------------------- #

def test_bare_cross_check_runs_core_and_ensemble(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("Some legal content for review.")
    runner = CliRunner()
    with (
        patch("litassist.commands.verify.core.verify_citations") as m_cit,
        patch("litassist.commands.verify.core.verify_reasoning") as m_rea,
        patch("litassist.commands.verify.core.verify_soundness") as m_snd,
        patch("litassist.commands.verify.core.run_cross_check") as m_cc,
    ):
        m_cit.return_value = ("cit report", {}, "cit.md", [], [])
        m_rea.return_value = ("reasoning", "rea.md", None)
        m_snd.return_value = ("soundness", [], "snd.md")
        m_cc.return_value = {"crosscheck_file": "cc.md"}
        result = runner.invoke(verify, [str(doc), "--cross-check"])
    assert result.exit_code == 0, result.output
    assert m_cit.called and m_rea.called and m_snd.called and m_cc.called


def test_citations_and_cross_check_compose(tmp_path):
    doc = tmp_path / "doc.md"
    doc.write_text("Some legal content for review.")
    runner = CliRunner()
    with (
        patch("litassist.commands.verify.core.verify_citations") as m_cit,
        patch("litassist.commands.verify.core.verify_soundness") as m_snd,
        patch("litassist.commands.verify.core.run_cross_check") as m_cc,
    ):
        m_cit.return_value = ("cit report", {}, "cit.md", [], [])
        m_snd.return_value = ("soundness", [], "snd.md")
        m_cc.return_value = {"crosscheck_file": "cc.md"}
        result = runner.invoke(verify, [str(doc), "--citations", "--cross-check"])
    assert result.exit_code == 0, result.output
    # --citations means soundness is NOT a default; only citations + cross-check run.
    assert m_cit.called and m_cc.called
    assert not m_snd.called
