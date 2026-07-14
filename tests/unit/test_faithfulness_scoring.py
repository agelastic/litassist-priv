"""Tests for score_faithfulness (P-FAITH deterministic scoring core).

The faithfulness checker classifies each atomic claim in a verified document against
the supplied source documents as one of SUPPORTED / UNSUPPORTED / CONTRADICTED /
PLACEHOLDER. This pure function aggregates those per-claim labels into a single
auditable score, with no I/O, so it is directly unit-testable offline (mirrors the
P-JUDGE pure-scoring-core pattern).

Scoring contract:
- PLACEHOLDER claims (the sanctioned `[... TO BE PROVIDED]` convention) are NEUTRAL and
  excluded from the score denominator -- they are correctly-marked missing data, not a
  faithfulness failure.
- score = round(100 * supported / (supported + unsupported + contradicted)); when that
  denominator is 0 the score is 100 (nothing substantive to ground).
- flagged_count = unsupported + contradicted (the claims that drive the report's flagged
  section and gate addendum generation).
"""

import pytest

from litassist.verification_chain import score_faithfulness


def test_all_supported_scores_100():
    result = score_faithfulness(["SUPPORTED", "SUPPORTED", "SUPPORTED"])
    assert result["score"] == 100
    assert result["supported"] == 3
    assert result["flagged_count"] == 0


def test_mixed_counts_round_to_nearest_percent():
    # 2 of 3 substantive claims grounded -> round(100 * 2/3) == 67.
    result = score_faithfulness(["SUPPORTED", "SUPPORTED", "UNSUPPORTED"])
    assert result["score"] == 67
    assert result["supported"] == 2
    assert result["unsupported"] == 1
    assert result["flagged_count"] == 1


def test_contradicted_counts_as_flagged_and_lowers_score():
    result = score_faithfulness(["SUPPORTED", "CONTRADICTED"])
    assert result["score"] == 50
    assert result["contradicted"] == 1
    # Both unsupported and contradicted feed the flagged set.
    assert result["flagged_count"] == 1


def test_placeholders_are_neutral_excluded_from_denominator():
    # 2 supported, 2 placeholder -> denominator is 2, not 4; score is 100.
    result = score_faithfulness(
        ["SUPPORTED", "PLACEHOLDER", "SUPPORTED", "PLACEHOLDER"]
    )
    assert result["score"] == 100
    assert result["placeholder"] == 2
    assert result["supported"] == 2
    assert result["flagged_count"] == 0


def test_placeholder_beside_failing_claim_stays_neutral():
    # A placeholder next to a failing claim must not change the score: denominator is
    # the two substantive claims (1 supported, 1 unsupported) -> 50, one flagged. The
    # lowercase label also pins case-insensitivity for PLACEHOLDER specifically.
    result = score_faithfulness(["SUPPORTED", "UNSUPPORTED", "placeholder"])
    assert result["score"] == 50
    assert result["flagged_count"] == 1
    assert result["placeholder"] == 1


def test_all_placeholder_denominator_zero_scores_100():
    # Nothing substantive to ground -> score 100, no flags.
    result = score_faithfulness(["PLACEHOLDER", "PLACEHOLDER"])
    assert result["score"] == 100
    assert result["flagged_count"] == 0


def test_empty_input_scores_100():
    result = score_faithfulness([])
    assert result["score"] == 100
    assert result["supported"] == 0
    assert result["flagged_count"] == 0


def test_labels_normalised_case_insensitively():
    result = score_faithfulness(["supported", "Unsupported", "contradicted"])
    assert result["supported"] == 1
    assert result["unsupported"] == 1
    assert result["contradicted"] == 1
    assert result["flagged_count"] == 2


def test_unknown_label_raises():
    # The upstream parse restricts labels to the four valid tokens; an unknown label
    # is a contract violation, so the pure function fails loud rather than silently
    # miscounting.
    with pytest.raises(ValueError):
        score_faithfulness(["SUPPORTED", "MAYBE"])
