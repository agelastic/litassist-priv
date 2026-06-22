"""Tests for C2 option 1 wiring in fetch_citation_context.

When CSE finds nothing for an authorised-report cite like "(1999) 201 CLR 1" and the
source document prints the parallel neutral cite ("[1999] HCA 66") nearby, the
direct-AustLII fallback resolves the neutral cite, builds the AustLII URL and fetches
the document. With no source_text the prior behaviour is preserved exactly.

These tests mock the network at the `_fetch_url_content` boundary and let the REAL
`_validate_citation_match` run, so they exercise the actual validation path. The page
body uses the real AustLII header form, where the report cite is printed BARE
("[1999] HCA 66; 201 CLR 1"), so the parenthesised "(1999) 201 CLR 1" never appears
verbatim. That is why a C2-resolved fetch validates against the resolved NEUTRAL cite
(verbatim on its own page), not the original traditional cite. Confirmed against the
live AustLII page for Mann v Carnell on 22/06/2026.
"""

from unittest.mock import MagicMock, patch

from litassist.citation_context import fetch_citation_context, _validate_citation_match
from litassist.citation.austlii import construct_austlii_url

HCA_URL = construct_austlii_url("[1999] HCA 66")
PARALLEL_SOURCE = "Mann v Carnell (1999) 201 CLR 1; [1999] HCA 66 at [12] is in point."
# Real AustLII header form (report cite bare, neutral cite carries the year).
AUSTLII_PAGE = (
    "Mann v Carnell [1999] HCA 66; 201 CLR 1; 168 ALR 86; 74 ALJR 378 "
    "(21 December 1999)\nHigh Court of Australia\nJudgment text...\n"
)


def _run(citation, source_text, page_body):
    """fetch_citation_context with the network mocked at _fetch_url_content and every
    CSE search empty, so the only fetch is the direct-AustLII fallback and the REAL
    validator runs against whatever the fallback fetched."""
    mock_service = MagicMock()
    mock_service.cse.return_value.list.return_value.execute.return_value = {}
    mock_config = MagicMock(
        g_key="fake", cse_id_austlii="cx_austlii", cse_id_comprehensive="cx_comp"
    )

    with patch("googleapiclient.discovery.build", return_value=mock_service), patch(
        "litassist.citation_context.get_config", return_value=mock_config
    ), patch(
        "litassist.commands.lookup.fetchers._fetch_url_content", return_value=page_body
    ) as mock_fetch, patch(
        "litassist.citation_context.save_log"
    ), patch(
        "litassist.citation_context.time.sleep"
    ):
        context, failures = fetch_citation_context([citation], source_text)
    return context, failures, mock_fetch


def test_parallel_resolution_fetches_and_validates():
    citation = "(1999) 201 CLR 1"

    context, failures, mock_fetch = _run(citation, PARALLEL_SOURCE, AUSTLII_PAGE)

    # The neutral cite was resolved, the HCA URL fetched, and the real validator
    # accepted the page (via the neutral cite verbatim in the body).
    assert mock_fetch.call_count == 1
    assert HCA_URL in mock_fetch.call_args[0][0]
    assert citation in context
    assert context[citation]
    assert failures == []


def test_source_text_none_preserves_failure():
    """Without source_text the CLR cite has no constructible URL and is never fetched
    -- the default path is unchanged."""
    citation = "(1999) 201 CLR 1"

    context, failures, mock_fetch = _run(citation, None, AUSTLII_PAGE)

    mock_fetch.assert_not_called()
    assert context == {}
    assert len(failures) == 1
    assert failures[0][0] == citation


def test_non_australian_traditional_cite_not_false_fetched():
    """A non-Australian traditional cite (UK Appeal Cases) sitting near an unrelated
    same-year Australian neutral cite must NOT be resolved to that Australian
    judgment - the fetched page does not carry the UK cite, so it is not a parallel."""
    citation = "[2017] AC 467"  # UK; no Australian medium-neutral parallel exists
    source = "Discussed in Smith [2017] AC 467 and applied locally in Jones [2017] HCA 5."
    # An HCA page that does NOT contain "AC 467" (it is a different, Australian case).
    hca_page = (
        "Jones v Roe [2017] HCA 5; 260 CLR 100; 91 ALJR 1 (1 February 2017)\n"
        "High Court of Australia\nJudgment text...\n"
    )
    context, failures, _ = _run(citation, source, hca_page)
    assert citation not in context
    assert any(cit == citation for cit, _ in failures)


def test_cross_jurisdiction_rejected_by_page_parallel_group():
    """A UK cite next to an unrelated AU neutral cite resolves (nearest), is fetched,
    but is rejected because "AC 467" is not in the HCA page's own parallel-citation
    group - even though the page mentions it later in the body, after the judgment
    date that bounds the group."""
    citation = "[2017] AC 467"
    source = "Smith [2017] AC 467; [2017] HCA 5 considered it."
    hca_page = (
        "Jones v Roe [2017] HCA 5; 260 CLR 100 (1 February 2017)\n"
        "High Court of Australia. The Court discussed Smith [2017] AC 467 at length.\n"
    )
    context, _failures, mock_fetch = _run(citation, source, hca_page)
    assert citation not in context
    assert mock_fetch.called  # fetch attempted, content dropped by the guard


def test_false_pairing_rejected_by_page_parallel_group():
    """A different same-year case's neutral cite is nearest, so the resolver returns it
    and it is fetched, but the page's parallel group does not list the traditional
    cite's report form, so it is rejected (no wrong case content served)."""
    citation = "(2001) 207 CLR 1"
    source = "A (2001) 207 CLR 1; [2005] HCA 5; B (2005) 223 CLR 1"
    hca_page = "B v Anor [2005] HCA 5; 223 CLR 1 (1 March 2005)\nHigh Court...\n"
    context, _failures, mock_fetch = _run(citation, source, hca_page)
    assert citation not in context
    assert mock_fetch.called


def test_collision_series_rejected_when_not_in_page_parallel_group():
    # "IR" is both Australian Industrial Reports and Irish Reports. The resolver returns
    # the nearest neutral cite regardless; the header-group guard rejects it when the
    # fetched AU page does not list the report form among the neutral cite's parallels.
    citation = "[2010] 2 IR 1"  # Irish Reports, here
    source = "Foo [2010] 2 IR 1; [2010] HCA 5 considered."
    hca_page = "Roe v Doe [2010] HCA 5; 240 CLR 1 (1 January 2010)\nHigh Court...\n"
    context, _failures, mock_fetch = _run(citation, source, hca_page)
    assert citation not in context
    assert mock_fetch.called  # fetch attempted, content dropped by the guard


def test_australian_industrial_reports_resolves_when_parallel_on_page():
    # Same "IR" abbreviation, but genuinely Australian: its report form IS one of the
    # neutral cite's parallels on the page, so it resolves.
    citation = "(2010) 200 IR 1"
    source = "Bar (2010) 200 IR 1; [2010] FCA 5 applied."
    fca_page = "Union v Employer [2010] FCA 5; 200 IR 1 (1 January 2010)\nFederal Court...\n"
    context, _failures, _ = _run(citation, source, fca_page)
    assert citation in context


def test_report_form_matched_as_token_not_substring():
    """The report form must match as a whole token: "20 CLR 1" must not be accepted by
    a different cite "120 CLR 1" in the page's parallel group (digit concatenation)."""
    citation = "(1999) 20 CLR 1"
    source = "Foo (1999) 20 CLR 1; [1999] HCA 66 considered."
    hca_page = "Bar v Baz [1999] HCA 66; 120 CLR 1 (1 January 1999)\nHigh Court...\n"
    context, _failures, mock_fetch = _run(citation, source, hca_page)
    assert citation not in context
    assert mock_fetch.called


def test_validation_targets_neutral_cite_not_parenthesised_report_cite():
    # The real AustLII header: the report cite is bare "201 CLR 1" and the neutral
    # cite carries the year, so the parenthesised traditional cite is absent.
    assert _validate_citation_match(AUSTLII_PAGE, "[1999] HCA 66") is True
    # The parenthesised "(1999) 201 CLR 1" does NOT validate against this page, which
    # is precisely why a C2-resolved fetch validates against the resolved neutral cite.
    assert _validate_citation_match(AUSTLII_PAGE, "(1999) 201 CLR 1") is False
