"""Tests for verify_faithfulness handler (P-FAITH).

Pins the user-facing contract that the corrective addendum is saved as a SEPARATE
file and only when claims are flagged -- the original document is never rewritten.
The orchestrator is mocked; only the handler's save/return behaviour is exercised.
"""

from unittest.mock import patch

from litassist.commands.verify.faithfulness_handler import verify_faithfulness


def _results(flagged_count, addendum):
    data = {
        "score": 50 if flagged_count else 100,
        "supported": 1,
        "unsupported": flagged_count,
        "contradicted": 0,
        "placeholder": 0,
        "flagged_count": flagged_count,
        "total": 1 + flagged_count,
        "claims": "1. a claim",
        "alignment": "CLAIM: a claim\nCLASSIFICATION: SUPPORTED\nSOURCE: none",
        "flagged_text": "CLAIM: bad\nCLASSIFICATION: UNSUPPORTED" if flagged_count else "",
        "addendum": addendum,
    }
    return ("DOC", {"faithfulness": data})


def _run(flagged_count, addendum):
    with patch(
        "litassist.commands.verify.faithfulness_handler.run_faithfulness_verification",
        return_value=_results(flagged_count, addendum),
    ), patch(
        "litassist.commands.verify.faithfulness_handler.save_command_output",
        side_effect=lambda prefix, content, slug, metadata=None: f"/out/{prefix}.md",
    ) as mock_save, patch(
        "litassist.commands.verify.faithfulness_handler.log_task_event"
    ):
        result = verify_faithfulness("DOC", "doc.md", "SOURCES")
    return result, mock_save


def test_addendum_saved_as_separate_file_when_flagged():
    (data, score, report_file, addendum_file), mock_save = _run(1, "ADDENDUM TEXT")

    assert mock_save.call_count == 2
    assert addendum_file is not None
    prefixes = [call.args[0] for call in mock_save.call_args_list]
    assert "verify_faithfulness" in prefixes
    assert "verify_faithfulness_addendum" in prefixes
    # The addendum file content is the addendum text, not a rewritten document.
    addendum_call = next(
        c for c in mock_save.call_args_list if c.args[0] == "verify_faithfulness_addendum"
    )
    assert addendum_call.args[1] == "ADDENDUM TEXT"


def test_no_addendum_when_nothing_flagged():
    (data, score, report_file, addendum_file), mock_save = _run(0, None)

    assert mock_save.call_count == 1  # report only
    assert addendum_file is None
    assert score == 100
