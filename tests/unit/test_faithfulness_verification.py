"""Tests for run_faithfulness_verification (P-FAITH orchestrator).

The faithfulness checker runs three staged LLM calls (extract atomic claims -> classify
each against the supplied sources -> draft a corrective addendum when claims are
flagged). These tests mock the stage clients at the LLMClientFactory boundary (the same
pattern as the CoVe tests) and assert the staged control flow:

- the original document is NEVER modified (the addendum is a separate artifact);
- the addendum stage runs ONLY when there are flagged (unsupported/contradicted) claims;
- a malformed alignment response (no CLASSIFICATION lines) fails closed rather than
  silently scoring 100;
- a document with no extractable claims is faithful by definition and skips alignment.
"""

from unittest.mock import Mock, patch

import pytest

from litassist.verification_chain import run_faithfulness_verification

_MOCK_MODEL = "test/mock-model"
_DOC = "The contract was signed on 1 March 2020. The settlement sum was $5,000."
_SOURCES = "Deed dated 1 March 2020. Settlement sum: $5,000."


def _clients(claims_text, alignment_text, addendum_text="ADDENDUM"):
    """Build mock stage clients keyed by role name."""
    claims_client = Mock(model=_MOCK_MODEL)
    claims_client.complete.return_value = (claims_text, {"total_tokens": 10})
    align_client = Mock(model=_MOCK_MODEL)
    align_client.complete.return_value = (alignment_text, {"total_tokens": 20})
    addendum_client = Mock(model=_MOCK_MODEL)
    addendum_client.complete.return_value = (addendum_text, {"total_tokens": 30})
    mapping = {
        "faithfulness-claims": claims_client,
        "faithfulness-align": align_client,
        "faithfulness-addendum": addendum_client,
    }
    return mapping


def _run(mapping, doc=_DOC, sources=_SOURCES):
    with patch("litassist.verification_chain.LLMClientFactory") as factory, patch(
        "litassist.verification_chain.save_log"
    ), patch("litassist.verification_chain.log_task_event"):
        factory.for_command.side_effect = lambda role: mapping[role]
        content, results = run_faithfulness_verification(doc, sources, "verify")
    return content, results


def test_all_supported_no_addendum_original_unchanged():
    alignment = (
        "CLAIM: The contract was signed on 1 March 2020.\n"
        "CLASSIFICATION: SUPPORTED\n"
        'SOURCE: "Deed dated 1 March 2020"\n\n'
        "CLAIM: The settlement sum was $5,000.\n"
        "CLASSIFICATION: SUPPORTED\n"
        'SOURCE: "Settlement sum: $5,000"\n'
    )
    mapping = _clients("1. signed 1 March 2020\n2. sum $5,000", alignment)
    content, results = _run(mapping)

    data = results["faithfulness"]
    assert content == _DOC  # original never modified
    assert data["score"] == 100
    assert data["flagged_count"] == 0
    assert data["addendum"] is None
    # The addendum stage must not run when nothing is flagged.
    mapping["faithfulness-addendum"].complete.assert_not_called()


def test_unsupported_claim_triggers_addendum_and_lowers_score():
    alignment = (
        "CLAIM: The contract was signed on 1 March 2020.\n"
        "CLASSIFICATION: SUPPORTED\n"
        'SOURCE: "Deed dated 1 March 2020"\n\n'
        "CLAIM: The settlement sum was $5,000.\n"
        "CLASSIFICATION: UNSUPPORTED\n"
        "SOURCE: none\n"
    )
    mapping = _clients(
        "1. signed 1 March 2020\n2. sum $5,000", alignment, addendum_text="CORRECTION NOTE"
    )
    content, results = _run(mapping)

    data = results["faithfulness"]
    assert content == _DOC  # still unchanged -- correction is the addendum, not a rewrite
    assert data["score"] == 50
    assert data["flagged_count"] == 1
    assert data["addendum"] == "CORRECTION NOTE"
    # The flagged block fed to the addendum is the unsupported claim, not the supported one.
    assert "settlement sum was $5,000" in data["flagged_text"]
    assert "1 March 2020" not in data["flagged_text"]
    mapping["faithfulness-addendum"].complete.assert_called_once()


def test_contradicted_claim_is_flagged_and_reaches_addendum():
    # CONTRADICTED is a flagged label distinct from UNSUPPORTED: it too must lower the
    # score and be the block passed to the addendum.
    alignment = (
        "CLAIM: The settlement sum was $5,000.\n"
        "CLASSIFICATION: CONTRADICTED\n"
        'SOURCE: "Settlement sum: $8,000"\n'
    )
    mapping = _clients("1. sum $5,000", alignment, addendum_text="CORRECTION NOTE")
    content, results = _run(mapping)

    data = results["faithfulness"]
    assert content == _DOC
    assert data["score"] == 0
    assert data["contradicted"] == 1
    assert data["flagged_count"] == 1
    assert "settlement sum was $5,000" in data["flagged_text"]
    assert data["addendum"] == "CORRECTION NOTE"
    mapping["faithfulness-addendum"].complete.assert_called_once()


def test_malformed_alignment_fails_closed():
    # Claims were extracted but the alignment response has no CLASSIFICATION line.
    mapping = _clients("1. a claim", "I was unable to classify these claims.")
    with pytest.raises(ValueError):
        _run(mapping)


def test_partial_alignment_fails_closed():
    # Stage 1 extracts three claims but the alignment classifies only one. The two
    # ungraded claims could be unsupported/contradicted, so a partial alignment must
    # NOT score as fully faithful -- it fails closed.
    claims = "1. claim one\n2. claim two\n3. claim three"
    alignment = "CLAIM: claim one\nCLASSIFICATION: SUPPORTED\nSOURCE: none\n"
    mapping = _clients(claims, alignment)
    with pytest.raises(ValueError):
        _run(mapping)


def test_no_claims_skips_alignment_and_is_faithful():
    mapping = _clients("   ", "unused")
    content, results = _run(mapping)

    data = results["faithfulness"]
    assert content == _DOC
    assert data["score"] == 100
    assert data["flagged_count"] == 0
    assert data["addendum"] is None
    # With no claims, neither alignment nor addendum should be invoked.
    mapping["faithfulness-align"].complete.assert_not_called()
    mapping["faithfulness-addendum"].complete.assert_not_called()
