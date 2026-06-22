"""Tests for C2 option 1 wiring in fetch_citation_context.

When CSE finds nothing for an authorised-report cite like "(1999) 201 CLR 1" and the
source document prints the parallel neutral cite ("[1999] HCA 66") nearby, the
direct-AustLII fallback resolves the neutral cite, builds the AustLII URL and fetches
the document. With no source_text the prior behaviour is preserved exactly.

The validation-mechanism test pins WHY the fetched page validates against the
original CLR cite: the `exact_primary_location` strategy (verbatim string in the page
body), NOT `_check_header_parallel_citations`, which is dead for CLR/ALR forms. A
refactor that reorders or drops `exact_primary_location` would silently break C2, so
this guards it.
"""

from unittest.mock import MagicMock, patch

from litassist.citation_context import (
    fetch_citation_context,
    _validate_citation_match,
    _check_header_parallel_citations,
)
from litassist.citation.austlii import construct_austlii_url

HCA_URL = construct_austlii_url("[1999] HCA 66")
PARALLEL_SOURCE = "Mann v Carnell (1999) 201 CLR 1; [1999] HCA 66 at [12] is in point."


def _run(citation, source_text, fetch_returns):
    """fetch_citation_context with the network mocked and every CSE search empty.

    With no CSE items the search loops return without fetching, so the only
    _try_fetch_and_validate call is the direct-AustLII fallback. construct_austlii_url
    is NOT patched -- the real one returns "" for the CLR cite and the HCA URL for the
    resolved neutral cite, which is exactly what C2 depends on.
    """
    mock_service = MagicMock()
    mock_service.cse.return_value.list.return_value.execute.return_value = {}
    mock_config = MagicMock(
        g_key="fake", cse_id_austlii="cx_austlii", cse_id_comprehensive="cx_comp"
    )

    with patch("googleapiclient.discovery.build", return_value=mock_service), patch(
        "litassist.citation_context.get_config", return_value=mock_config
    ), patch(
        "litassist.citation_context._try_fetch_and_validate", return_value=fetch_returns
    ) as mock_fetch, patch(
        "litassist.citation_context.save_log"
    ), patch(
        "litassist.citation_context.time.sleep"
    ):
        context, failures = fetch_citation_context([citation], source_text)
    return context, failures, mock_fetch


def test_parallel_resolution_enables_austlii_fetch():
    citation = "(1999) 201 CLR 1"
    body = f"{citation}; [1999] HCA 66\nHigh Court of Australia. Judgment text..."

    context, failures, mock_fetch = _run(citation, PARALLEL_SOURCE, body)

    # The neutral cite was resolved and the HCA URL fetched.
    mock_fetch.assert_called_once_with(HCA_URL, citation)
    assert citation in context
    assert context[citation]
    assert failures == []


def test_source_text_none_preserves_failure():
    """Without source_text the CLR cite has no constructible URL and still fails -- the
    default path is unchanged."""
    citation = "(1999) 201 CLR 1"

    context, failures, mock_fetch = _run(citation, None, "doc body")

    mock_fetch.assert_not_called()
    assert context == {}
    assert len(failures) == 1
    assert failures[0][0] == citation


def test_validation_uses_exact_primary_location_not_parallel_header():
    # A fetched AustLII page whose body prints the verbatim traditional cite.
    citation = "(1998) 194 CLR 355"
    header = (
        "Project Blue Sky Inc v Australian Broadcasting Authority "
        "[1998] HCA 28; (1998) 194 CLR 355"
    )
    body = header + "\n\nHigh Court of Australia\nJudgment...\n"

    # Validation passes -- via the verbatim string in the body.
    assert _validate_citation_match(body, citation) is True
    # ...and NOT via the parallel-citation header strategy, which cannot see CLR forms.
    assert _check_header_parallel_citations(header, citation) is False
