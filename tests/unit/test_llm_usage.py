"""Offline tests for litassist.llm.usage.merge_usage."""

import pytest

from litassist.llm.usage import merge_usage


def test_sums_tokens_and_cost():
    merged = merge_usage(
        {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15, "cost": 0.5},
        {"prompt_tokens": 20, "completion_tokens": 8, "total_tokens": 28, "cost": 0.25},
    )
    assert merged["prompt_tokens"] == 30
    assert merged["completion_tokens"] == 13
    assert merged["total_tokens"] == 43
    assert merged["cost"] == 0.75


def test_collects_generation_ids_and_ignores_none():
    merged = merge_usage(
        {"cost": 0.1, "generation_id": "gen-a"},
        None,
        {},
        {"cost": 0.2, "generation_id": "gen-b"},
    )
    assert merged["cost"] == pytest.approx(0.3)
    assert merged["generation_ids"] == ["gen-a", "gen-b"]


def test_partial_cost_excludes_missing():
    # One call carries cost, the other does not: the sum is partial, not zeroed.
    merged = merge_usage({"cost": 0.4}, {"prompt_tokens": 5})
    assert merged["cost"] == 0.4
    assert merged["prompt_tokens"] == 5


def test_nested_merge_preserves_all_generation_ids():
    # Merging an already-merged usage (plural generation_ids) with a fresh leaf
    # (singular generation_id) must keep both - the citation-retry path.
    first = merge_usage(
        {"cost": 0.1, "generation_id": "gen-a"},
        {"cost": 0.1, "generation_id": "gen-b"},
    )
    assert first["generation_ids"] == ["gen-a", "gen-b"]
    combined = merge_usage(first, {"cost": 0.1, "generation_id": "gen-retry"})
    assert combined["generation_ids"] == ["gen-a", "gen-b", "gen-retry"]


def test_tracks_partial_cost():
    # A leaf without a numeric cost is counted as missing.
    merged = merge_usage({"cost": 0.4}, {"prompt_tokens": 5})
    assert merged["cost"] == 0.4
    assert merged["cost_missing"] == 1
    # The tally propagates through a further merge instead of being lost.
    again = merge_usage(merged, {"cost": 0.2})
    assert again["cost"] == pytest.approx(0.6)
    assert again["cost_missing"] == 1


def test_no_cost_missing_key_when_complete():
    merged = merge_usage({"cost": 0.4}, {"cost": 0.2})
    assert "cost_missing" not in merged


def test_empty_inputs():
    assert merge_usage() == {}
    assert merge_usage(None, {}) == {}
