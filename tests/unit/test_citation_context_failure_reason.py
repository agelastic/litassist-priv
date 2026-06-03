"""Tests for fetch_citation_context failure-reason attribution.

When Google CSE returns a result and the document is fetched but fails
citation-match validation, the failure reason must say so -- not the misleading
"URL not found - CSE returned no results", which implies CSE found nothing. The
two cases are distinct and must be reported distinctly, and a later empty
fallback search must not erase the fact that an earlier search fetched a document.
"""

from unittest.mock import MagicMock, patch

from litassist.citation_context import fetch_citation_context

CASE_LINK = "https://www.austlii.edu.au/au/cases/cth/HCA/1999/66.html"


def _run(citation, execute_returns):
    """Run fetch_citation_context with the network boundary mocked.

    _try_fetch_and_validate returns None to simulate a document that was fetched
    but failed citation-match validation. execute_returns is a list of dicts, one
    per CSE .execute() call (consumed in order via side_effect).
    """
    mock_service = MagicMock()
    mock_service.cse.return_value.list.return_value.execute.side_effect = list(
        execute_returns
    )
    mock_config = MagicMock(
        g_key="fake", cse_id_austlii="cx_austlii", cse_id_comprehensive="cx_comp"
    )

    with patch("googleapiclient.discovery.build", return_value=mock_service), patch(
        "litassist.citation_context.get_config", return_value=mock_config
    ), patch(
        "litassist.citation_context._try_fetch_and_validate", return_value=None
    ), patch(
        "litassist.citation_context.is_trusted_legal_host", return_value=True
    ), patch(
        "litassist.citation_context.construct_austlii_url", return_value=""
    ), patch(
        "litassist.citation_context.save_log"
    ), patch(
        "litassist.citation_context.time.sleep"
    ):
        return fetch_citation_context([citation])


def test_fetched_but_unvalidated_reports_validation_failure():
    """A CSE hit that is fetched but fails validation reports a fetch/validation
    failure, not a missing URL."""
    citation = "(1999) 201 CLR 1"
    items = {"items": [{"link": CASE_LINK}]}

    # Case law: AustLII search then comprehensive fallback (both return the hit).
    context, failures = _run(citation, [items, items])

    assert context == {}
    assert len(failures) == 1
    cit, reason = failures[0]
    assert cit == citation
    assert reason == "Document fetch or content validation failed"


def test_empty_fallback_does_not_erase_earlier_fetch():
    """When an earlier search fetches a document (validation fails) and a later
    fallback search returns no results, the reason must still reflect the fetch,
    not be reset to 'URL not found'."""
    citation = "(1999) 201 CLR 1"
    items = {"items": [{"link": CASE_LINK}]}

    # AustLII returns the hit (fetched, fails validation); comprehensive fallback
    # returns no items at all.
    context, failures = _run(citation, [items, {}])

    assert context == {}
    assert len(failures) == 1
    _, reason = failures[0]
    assert reason == "Document fetch or content validation failed"


def test_no_cse_results_reports_url_not_found():
    """Guard: when every search returns no items, the reason remains the accurate
    'URL not found' message."""
    citation = "(1999) 201 CLR 1"

    context, failures = _run(citation, [{}, {}])

    assert context == {}
    assert len(failures) == 1
    _, reason = failures[0]
    assert reason == "URL not found - CSE returned no results"
