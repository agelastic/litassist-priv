"""
Tests for jurisdiction-aware legislation retrieval and validation in
citation_context.

Regression coverage for the 11/06/2026 P-JUDGE finding: whole-act citations
like "Civil Liability Act 2002 (NSW)" were structurally unfetchable - the
AustLII CSE link filter accepted any /au/legis/ link (the WA act and a
Regulation were fetched for an NSW Act citation), and no validation strategy
could pass on a correct act page, whose header carries the bare title plus
the jurisdiction prose ("New South Wales Consolidated Acts"), never the
"(NSW)" literal.
"""

from litassist.citation_context import (
    _legislation_austlii_link_ok,
    _parse_legislation_jurisdiction,
    _validate_citation_match,
)

NSW_ACT_PAGE = (
    "CIVIL LIABILITY ACT 2002\n"
    "AustLII Search\n"
    "New South Wales Consolidated Acts\n"
    "Search AustLII\n"
    "Table of Provisions\n"
)

WA_ACT_PAGE = (
    "CIVIL LIABILITY ACT 2002\n"
    "AustLII Search\n"
    "Western Australian Current Acts\n"
    "Search AustLII\n"
)

NSW_REGULATION_PAGE = (
    "Civil Liability Regulation 2009 (2009-436) LW 28 August 2009\n"
    "AustLII Search\n"
    "New South Wales Consolidated Regulations\n"
)


class TestParseLegislationJurisdiction:
    def test_nsw(self):
        assert _parse_legislation_jurisdiction("Civil Liability Act 2002 (NSW)") == (
            "nsw",
            "new south wales",
        )

    def test_cth_case_insensitive(self):
        assert _parse_legislation_jurisdiction(
            "Competition and Consumer Act 2010 (CTH)"
        ) == ("cth", "commonwealth")

    def test_no_marker_returns_none(self):
        assert _parse_legislation_jurisdiction("Fallas v Mourlas [2006] NSWCA 32") is None

    def test_case_parenthetical_is_not_jurisdiction(self):
        assert (
            _parse_legislation_jurisdiction(
                "Miwa Pty Ltd v Siantan Properties Pte Ltd (No 2) [2011] NSWCA 344"
            )
            is None
        )


class TestLegislationLinkFilter:
    NSW = ("nsw", "new south wales")

    def test_correct_jurisdiction_link_accepted(self):
        assert _legislation_austlii_link_ok(
            "https://www.austlii.edu.au/au/legis/nsw/consol_act/ca200294/", self.NSW
        )

    def test_wrong_jurisdiction_link_rejected(self):
        assert not _legislation_austlii_link_ok(
            "https://www.austlii.edu.au/au/legis/wa/consol_act/cla2002161/", self.NSW
        )

    def test_no_jurisdiction_keeps_generic_filter(self):
        assert _legislation_austlii_link_ok(
            "https://www.austlii.edu.au/au/legis/wa/consol_act/cla2002161/", None
        )

    def test_untrusted_host_rejected(self):
        assert not _legislation_austlii_link_ok(
            "https://evil.example.com/au/legis/nsw/consol_act/ca200294/", self.NSW
        )


class TestLegislationValidation:
    CITATION = "Civil Liability Act 2002 (NSW)"

    def test_correct_act_page_validates(self):
        assert _validate_citation_match(NSW_ACT_PAGE, self.CITATION)

    def test_wrong_jurisdiction_page_rejected(self):
        assert not _validate_citation_match(WA_ACT_PAGE, self.CITATION)

    def test_regulation_page_rejected_for_act_citation(self):
        assert not _validate_citation_match(NSW_REGULATION_PAGE, self.CITATION)

    def test_case_citations_unaffected(self):
        # existing exact-match strategy still validates case headers
        content = "Fallas v Mourlas [2006] NSWCA 32\nCourt of Appeal\n"
        assert _validate_citation_match(content, "Fallas v Mourlas [2006] NSWCA 32")
