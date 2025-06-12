"""
Simple tests for citation verification functionality.
"""

from unittest.mock import Mock, patch
from litassist.citation_patterns import extract_citations
from litassist.citation_verify import search_jade_via_google_cse


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

    @patch("litassist.citation_verify.CONFIG")
    @patch("googleapiclient.discovery.build")
    def test_search_jade_via_google_cse_not_found(self, mock_build, mock_config):
        """Test Jade search when nothing found."""
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse_id"

        mock_service = Mock()
        mock_build.return_value = mock_service

        # Mock empty result
        mock_service.cse.return_value.list.return_value.execute.return_value = {
            "items": []
        }

        result = search_jade_via_google_cse("[2099] FCA 999")
        assert result is False

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
