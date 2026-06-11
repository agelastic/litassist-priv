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

# Real shape from the 11/06/2026 audit logs: an arbitrary section page of the
# right act, which must NOT validate a whole-act citation.
CTH_SECTION_PAGE = (
    "COMPETITION AND CONSUMER ACT 2010 - SECT 87CC\n"
    "Certain concurrent wrongdoers not to have benefit of apportionment\n"
    "AustLII Search\n"
    "Commonwealth Consolidated Acts\n"
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

    def test_section_page_rejected_for_whole_act_citation(self):
        # an arbitrary section of the right act is not the act: validating it
        # would overstate retrieval for whole-act citations
        assert not _validate_citation_match(
            CTH_SECTION_PAGE, "Competition and Consumer Act 2010 (Cth)"
        )

    def test_section_page_rejected_for_bare_whole_act_citation(self):
        # without a jurisdiction parenthetical the exact-match strategies see
        # the title verbatim in the section-page header; the component-page
        # guard must still refuse it
        content = (
            "CIVIL LIABILITY ACT 2002 - SECT 16\n"
            "Determination of damages for non-economic loss\n"
            "AustLII Search\n"
            "New South Wales Consolidated Acts\n"
        )
        assert not _validate_citation_match(content, "Civil Liability Act 2002")

    def test_section_citing_citation_not_blocked_by_guard(self):
        # a citation that names the section may validate a page whose first
        # 500 chars carry the full citation string (exact-match strategy)
        content = (
            "Civil Liability Act 2002 (NSW) s 16 commentary\n"
            "Some annotated discussion of the provision.\n"
        )
        assert _validate_citation_match(content, "Civil Liability Act 2002 (NSW) s 16")

    def test_parenthetical_act_title_section_page_rejected(self):
        # acts with parentheticals in their NAME ("Civil Law (Wrongs) Act
        # 2002") must not evade the guard: the citation-side strip used to
        # produce a title the component header could never match
        content = (
            "CIVIL LAW (WRONGS) ACT 2002 - SECT 5\n"
            "Definitions\n"
            "AustLII Search\n"
            "Australian Capital Territory Consolidated Acts\n"
        )
        assert not _validate_citation_match(content, "Civil Law (Wrongs) Act 2002")
        assert not _validate_citation_match(
            content, "Civil Law (Wrongs) Act 2002 (ACT)"
        )

    def test_same_year_parenthetical_sibling_act_not_cross_matched(self):
        # name parentheticals are kept in the derived title, so two
        # same-jurisdiction same-year acts differing only by parenthetical
        # can never collapse to the same string and cross-validate
        content = (
            "CIVIL LAW (COSTS) ACT 2002\n"
            "AustLII Search\n"
            "Australian Capital Territory Consolidated Acts\n"
            "Table of Provisions\n"
        )
        assert not _validate_citation_match(
            content, "Civil Law (Wrongs) Act 2002 (ACT)"
        )

    def test_parenthetical_act_title_act_root_validates(self):
        # the same paren-stripping blindness also false-negatived the
        # legitimate act-root page for such acts
        content = (
            "CIVIL LAW (WRONGS) ACT 2002\n"
            "AustLII Search\n"
            "Australian Capital Territory Consolidated Acts\n"
            "Table of Provisions\n"
        )
        assert _validate_citation_match(content, "Civil Law (Wrongs) Act 2002 (ACT)")

    def test_guard_contract_on_genuine_component_header(self):
        # the guard fires for the whole-act form but structurally cannot fire
        # for the section-citing form: its derived title keeps the section
        # ref, so the title-then-component pattern cannot match
        from litassist.citation_context import _component_page_for_whole_citation

        header = (
            "CIVIL LIABILITY ACT 2002 - SECT 16\n"
            "Determination of damages for non-economic loss\n"
        )
        assert _component_page_for_whole_citation(header, "Civil Liability Act 2002")
        assert not _component_page_for_whole_citation(
            header, "Civil Liability Act 2002 s 16"
        )
