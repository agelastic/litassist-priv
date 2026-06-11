"""
Tests for construct_austlii_url.

Regression coverage for the 11/06/2026 P-JUDGE finding: the neutral-cite
parser was anchored to the start of the string, so citations carrying their
case name (the form every command output uses) silently returned "" and the
direct-AustLII fallback in fetch_citation_context never ran.
"""

from litassist.citation.austlii import construct_austlii_url

NSWCA_32_URL = "https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/nsw/NSWCA/2006/32.html"


class TestConstructAustliiUrl:
    def test_bare_neutral_citation(self):
        assert construct_austlii_url("[2006] NSWCA 32") == NSWCA_32_URL

    def test_named_neutral_citation(self):
        assert (
            construct_austlii_url("Fallas v Mourlas [2006] NSWCA 32")
            == NSWCA_32_URL
        )

    def test_named_citation_with_parenthetical(self):
        assert construct_austlii_url(
            "Miwa Pty Ltd v Siantan Properties Pte Ltd (No 2) [2011] NSWCA 344"
        ) == (
            "https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/nsw/NSWCA/2011/344.html"
        )

    def test_named_hca_citation(self):
        assert construct_austlii_url(
            "Roads and Traffic Authority of NSW v Dederer [2007] HCA 42"
        ) == ("https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/HCA/2007/42.html")

    def test_unknown_court_returns_empty(self):
        assert construct_austlii_url("[2006] NOTACOURT 32") == ""

    def test_authorised_report_only_returns_empty(self):
        # CLR-only citations have no neutral cite to construct from (TODO C1/C2)
        assert construct_austlii_url("(1999) 201 CLR 1") == ""
