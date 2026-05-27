"""
Simple tests for citation verification functionality.
"""

from unittest.mock import Mock, patch
from litassist.citation_patterns import extract_citations
from litassist.citation.google_cse import search_legal_database_via_cse


class TestCitationVerificationBasic:
    """Basic tests for citation verification."""

    def test_extract_citations_finds_modern_format(self):
        """Test that modern citation formats are found."""
        text = "The court in Smith v Jones [2021] FCA 123 held that..."
        citations = extract_citations(text)

        # Should find at least one citation
        assert len(citations) >= 1
        # Should contain the citation we expect
        found_fca = any("FCA" in str(c) and "2021" in str(c) for c in citations)
        assert found_fca

    def test_extract_citations_handles_empty_text(self):
        """Test extraction handles empty text gracefully."""
        citations = extract_citations("")
        assert isinstance(citations, list)

    @patch("litassist.citation.google_cse.get_config")
    @patch("googleapiclient.discovery.build")
    def test_cse_hit_on_untrusted_domain_is_rejected(self, mock_build, mock_get_config):
        # Regression: CSE results on untrusted domains used to verify a citation
        # purely on substring match of the citation tokens against
        # title/snippet/link.
        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse_id"
        mock_get_config.return_value = mock_config

        mock_service = Mock()
        mock_build.return_value = mock_service
        # Hit has the citation text in title+snippet but on an attacker domain.
        mock_service.cse.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "title": "Smith v Jones [2099] FCA 999 - cached",
                    "snippet": "The court in Smith v Jones [2099] FCA 999 held that...",
                    "link": "https://example.invalid/spoofed/[2099] FCA 999.html",
                }
            ]
        }

        success, url, snippet = search_legal_database_via_cse("[2099] FCA 999")
        assert success is False, (
            f"CSE hit on untrusted host example.invalid must not verify, got url={url}"
        )

    @patch("litassist.citation.google_cse.get_config")
    @patch("googleapiclient.discovery.build")
    def test_cse_hit_on_trusted_domain_verifies(self, mock_build, mock_get_config):
        # Conversely: a CSE hit on a real trusted host must still verify.
        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse_id"
        mock_get_config.return_value = mock_config

        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_service.cse.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "title": "Smith v Jones [2099] FCA 999",
                    "snippet": "Federal Court of Australia decision in Smith v Jones [2099] FCA 999",
                    "link": "https://www.austlii.edu.au/au/cases/cth/FCA/2099/999.html",
                }
            ]
        }

        success, url, snippet = search_legal_database_via_cse("[2099] FCA 999")
        assert success is True
        assert "austlii.edu.au" in url

    @patch("litassist.citation.google_cse.get_config")
    @patch("googleapiclient.discovery.build")
    def test_cse_link_only_match_is_rejected(self, mock_build, mock_get_config):
        # Citation tokens appearing only in the link (not title/snippet) must
        # not be enough to verify. Previously combined_text included the link.
        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse_id"
        mock_get_config.return_value = mock_config

        mock_service = Mock()
        mock_build.return_value = mock_service
        mock_service.cse.return_value.list.return_value.execute.return_value = {
            "items": [
                {
                    "title": "Unrelated page about contract law",
                    "snippet": "This page discusses general principles, nothing case-specific.",
                    "link": "https://www.austlii.edu.au/q?ref=[2099] FCA 999",
                }
            ]
        }

        success, _url, _snippet = search_legal_database_via_cse("[2099] FCA 999")
        assert success is False, (
            "Citation tokens in link-only must not verify (URL is attacker-controllable)"
        )

    @patch("litassist.citation.google_cse.get_config")
    @patch("googleapiclient.discovery.build")
    def test_search_legal_database_via_cse_not_found(self, mock_build, mock_get_config):
        """Test CSE legal-database search when nothing found."""
        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse_id"
        mock_get_config.return_value = mock_config

        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock empty result
        mock_service.cse.return_value.list.return_value.execute.return_value = {
            "items": []
        }

        success, url, snippet = search_legal_database_via_cse("[2099] FCA 999")
        assert success is False

    def test_citation_extraction_integration(self):
        """Test that citation extraction works with real legal text."""
        legal_text = """
        The High Court in Mabo v Queensland (No 2) [1992] HCA 23 established
        the principle of native title. This was later developed in
        Wik Peoples v Queensland [1996] HCA 40.
        """

        citations = extract_citations(legal_text)

        # Should find multiple citations
        assert len(citations) >= 1

        # Should find HCA citations
        hca_citations = [c for c in citations if "HCA" in str(c)]
        assert len(hca_citations) >= 1


class TestCitationVerificationExistenceChecks:
    """Regression tests: legislation and international citations must require
    positive source evidence, not be auto-verified by pattern match alone."""

    def _clear_cache(self):
        from litassist.citation.cache import _citation_cache
        _citation_cache.clear()

    @patch("litassist.citation.verify.verify_via_austlii_direct")
    @patch("litassist.citation.verify.search_legal_database_via_cse")
    @patch("litassist.citation.verify.get_config")
    def test_imaginary_legislation_is_not_auto_verified(
        self, mock_get_config, mock_cse, mock_austlii
    ):
        # Imaginary acts ("Imaginary Aliens Act 2099 (Cth)") used to short-circuit
        # to exists=True on pattern match alone. They must now require positive
        # source evidence.
        self._clear_cache()
        mock_config = Mock()
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_comprehensive = None
        mock_config.cse_id_austlii = None
        mock_get_config.return_value = mock_config

        mock_cse.return_value = (False, "", "")
        mock_austlii.return_value = (False, "", "")

        from litassist.citation.verify import verify_single_citation

        exists, url, reason, snippet = verify_single_citation(
            "Imaginary Aliens Act 2099 (Cth)"
        )

        assert exists is False, (
            f"Expected exists=False for fabricated legislation, got True with reason: {reason}"
        )

    @patch("litassist.citation.verify.verify_via_austlii_direct")
    @patch("litassist.citation.verify.search_legal_database_via_cse")
    @patch("litassist.citation.verify.get_config")
    def test_imaginary_international_is_not_auto_verified(
        self, mock_get_config, mock_cse, mock_austlii
    ):
        # Imaginary UK/International citations ([2099] UKSC 999) used to
        # short-circuit to exists=True. They must now require positive source
        # evidence.
        self._clear_cache()
        mock_config = Mock()
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_comprehensive = None
        mock_config.cse_id_austlii = None
        mock_get_config.return_value = mock_config

        mock_cse.return_value = (False, "", "")
        mock_austlii.return_value = (False, "", "")

        from litassist.citation.verify import verify_single_citation

        exists, url, reason, snippet = verify_single_citation("[2099] UKSC 999")

        assert exists is False, (
            f"Expected exists=False for fabricated international cite, got True with reason: {reason}"
        )

    @patch("litassist.citation.verify.verify_via_austlii_direct")
    @patch("litassist.citation.verify.search_legal_database_via_cse")
    @patch("litassist.citation.verify.get_config")
    def test_transient_verification_failure_does_not_poison_cache(
        self, mock_get_config, mock_cse, mock_austlii
    ):
        # Regression: a network/CSE error during verification used to be
        # swallowed by `except Exception: pass`, mark the citation as
        # exists=False, and cache that negative for the rest of the process.
        # A recovered network would never re-verify the citation.
        self._clear_cache()
        mock_config = Mock()
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_comprehensive = None
        mock_config.cse_id_austlii = None
        mock_get_config.return_value = mock_config

        # First call raises (transient network failure).
        mock_cse.side_effect = ConnectionError("CSE timeout")

        from litassist.citation.verify import verify_single_citation
        from litassist.citation.cache import _citation_cache

        exists1, _, reason1, _ = verify_single_citation("[2099] FCA 999")
        assert exists1 is False
        assert "transient" in reason1.lower(), (
            f"Transient failure must be reported as such; got: {reason1!r}"
        )
        assert "[2099] FCA 999" not in _citation_cache, (
            "Transient failure must not poison the cache; the next call "
            "would otherwise short-circuit to the cached negative result"
        )

        # Network recovers - second call must actually retry CSE.
        mock_cse.side_effect = None
        mock_cse.return_value = (
            True,
            "https://www.austlii.edu.au/au/cases/cth/FCA/2099/999.html",
            "Smith v Jones [2099] FCA 999",
        )
        exists2, _, _, _ = verify_single_citation("[2099] FCA 999")
        assert exists2 is True

    @patch("litassist.citation.verify.verify_via_austlii_direct")
    @patch("litassist.citation.verify.search_legal_database_via_cse")
    @patch("litassist.citation.verify.get_config")
    def test_known_legislation_verifies_when_cse_returns_hit(
        self, mock_get_config, mock_cse, mock_austlii
    ):
        # Conversely: legitimate legislation must still verify when a trusted
        # CSE source returns a hit. Guard against over-correction.
        self._clear_cache()
        mock_config = Mock()
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_comprehensive = None
        mock_config.cse_id_austlii = None
        mock_get_config.return_value = mock_config

        mock_cse.return_value = (
            True,
            "https://www.legislation.gov.au/Series/C1958A00062",
            "Migration Act 1958",
        )
        mock_austlii.return_value = (False, "", "")

        from litassist.citation.verify import verify_single_citation

        exists, url, reason, snippet = verify_single_citation("Migration Act 1958")

        assert exists is True, (
            f"Expected exists=True for real legislation with CSE hit, got False: {reason}"
        )
        assert "legislation.gov.au" in url
