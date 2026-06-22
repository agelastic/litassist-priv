"""
Tests for resolve_neutral_from_parallel (C2 option 1).

Closes the retrieval gap for authorised-report cites: a CLR-only string like
`(1999) 201 CLR 1` has no medium-neutral form for `construct_austlii_url` to build
from, so the direct-AustLII fallback never fires. When the source document prints
both forms together (the common real-draft case, `... (1999) 201 CLR 1; [1999] HCA
66`), this resolver recovers the adjacent neutral cite so the existing fetch path can
run.

The resolver is purely positional: it returns the NEAREST AustLII-constructible
neutral cite within the window, on either side. It does no jurisdiction or year
filtering - whether the cite is genuinely the same case is confirmed downstream
against the fetched page's own parallel-citation list (see
test_citation_context_parallel_resolution.py). Cases here cover: bidirectional
window, split-year pairs, nearest-wins on multiple pairs, out-of-window not paired,
and non-AustLII neutral forms (UK/NZ etc.) excluded because they are not constructible.
"""

from litassist.citation.austlii import resolve_neutral_from_parallel


class TestResolveNeutralFromParallel:
    def test_neutral_follows_traditional(self):
        source = "Mann v Carnell (1999) 201 CLR 1; [1999] HCA 66 at [12] held that..."
        assert (
            resolve_neutral_from_parallel("(1999) 201 CLR 1", source) == "[1999] HCA 66"
        )

    def test_neutral_precedes_traditional(self):
        # Codex check 5: the neutral cite frequently precedes in judgments/headnotes.
        source = "see [1999] HCA 66; (1999) 201 CLR 1 per Gleeson CJ"
        assert (
            resolve_neutral_from_parallel("(1999) 201 CLR 1", source) == "[1999] HCA 66"
        )

    def test_split_year_pair_still_resolves(self):
        # Judgment year and report year can differ; the resolver does no year filtering,
        # so the adjacent neutral cite resolves regardless of the one-year gap.
        source = "X v Y [1995] HCA 10; (1996) 185 CLR 1 at 7"
        assert (
            resolve_neutral_from_parallel("(1996) 185 CLR 1", source) == "[1995] HCA 10"
        )

    def test_no_neutral_cite_in_window_returns_empty(self):
        source = "(1996) 185 CLR 1 and then a long passage with no neutral citation."
        assert resolve_neutral_from_parallel("(1996) 185 CLR 1", source) == ""

    def test_multiple_pairs_nearest_neutral_wins(self):
        source = (
            "First A (2001) 207 CLR 1; [2001] HCA 1 and later "
            "Second B (2005) 223 CLR 1; [2005] HCA 5 distinguished."
        )
        assert (
            resolve_neutral_from_parallel("(2005) 223 CLR 1", source) == "[2005] HCA 5"
        )
        assert (
            resolve_neutral_from_parallel("(2001) 207 CLR 1", source) == "[2001] HCA 1"
        )

    def test_out_of_window_neutral_not_paired(self):
        # Neutral cite separated from the traditional cite by far more than the
        # pairing window must not be treated as parallel.
        filler = " padding" * 80  # ~640 chars, well beyond the ~300 char window
        source = f"(1996) 185 CLR 1{filler}[1995] HCA 10"
        assert resolve_neutral_from_parallel("(1996) 185 CLR 1", source) == ""

    def test_non_austlii_neutral_excluded(self):
        # UKSC is a valid neutral-FORMAT cite but not an AustLII-constructible court,
        # so it must not be returned (construct_austlii_url would reject it anyway).
        source = "(1999) 201 CLR 1; [2016] UKSC 8"
        assert resolve_neutral_from_parallel("(1999) 201 CLR 1", source) == ""

    def test_empty_inputs_return_empty(self):
        assert resolve_neutral_from_parallel("", "some text") == ""
        assert resolve_neutral_from_parallel("(1999) 201 CLR 1", "") == ""

    def test_traditional_cite_absent_from_source(self):
        source = "totally unrelated text [1999] HCA 66 standing alone"
        assert resolve_neutral_from_parallel("(1999) 201 CLR 1", source) == ""

    def test_adjacent_parallel_preferred_over_farther(self):
        # The adjacent neutral cite ([1995] HCA 10) wins over a farther same-year cite
        # ([1996] HCA 99) - the resolver is nearest-first, nothing more.
        source = "Cited [1995] HCA 10; (1996) 185 CLR 1 then later [1996] HCA 99 elsewhere"
        assert (
            resolve_neutral_from_parallel("(1996) 185 CLR 1", source) == "[1995] HCA 10"
        )

    def test_resolver_does_no_jurisdiction_or_case_filtering(self):
        # The resolver returns the nearest constructible neutral cite WITHOUT judging
        # whether it is the same case or jurisdiction. Here a UK cite sits next to an
        # unrelated AU neutral cite: the resolver returns that neutral cite; the cross-
        # jurisdiction/false-pair REJECTION happens downstream at the page-parallel-group
        # guard (see test_citation_context_parallel_resolution.py).
        source = "A (2001) 207 CLR 1; [2005] HCA 5; B (2005) 223 CLR 1"
        assert (
            resolve_neutral_from_parallel("(2001) 207 CLR 1", source) == "[2005] HCA 5"
        )
