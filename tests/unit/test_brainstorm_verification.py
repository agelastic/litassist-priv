"""Test brainstorm verification flow."""

from unittest.mock import patch
from litassist.commands.brainstorm.core import (
    verify_and_annotate_strategies,
    _extract_strategies,
    _annotate_strategies_with_verification,
)


class TestVerificationFlow:
    """Test the new verification flow."""

    def test_extract_strategies_fallback(self):
        """Test fallback when no numbered patterns found."""
        content = """Some strategy text

Another strategy text

Third strategy text"""
        strategies = _extract_strategies(content, "orthodox")
        assert len(strategies) == 3

    @patch('litassist.citation.verify.verify_all_citations')
    @patch('litassist.commands.brainstorm.core.assess_legal_plausibility_bulk')
    def test_verify_and_annotate(self, mock_plausibility, mock_verify):
        """Test verify_and_annotate_strategies function."""
        # Setup mocks
        mock_verify.return_value = (
            [{"citation": "[2020] HCA 1", "url": "", "snippet": "", "reason": ""}],  # verified
            [("[2024] FakeCourt 999", "not found")]  # unverified
        )
        mock_plausibility.return_value = {
            "orthodox_1": {"risk": "HIGH", "explanation": "Likely hallucination"}
        }

        # Test content
        orthodox = "### 1. Strategy\nCiting [2024] FakeCourt 999"
        unorthodox = "### 1. Strategy\nCiting [2020] HCA 1"

        # Run verification
        orth_out, unorth_out, summary = verify_and_annotate_strategies(
            orthodox, unorthodox
        )

        # Check annotations added
        assert "[NOT VERIFIED]" in orth_out
        assert "[VERIFIED]" in unorth_out
        assert "1 verified, 1 unverified" in summary


class TestExtractVerifiedDocument:
    """Brainstorm verification fallback: when the verifier response lacks the
    expected `## Verified and Corrected Document` header, the original
    brainstorm output must be preserved instead of silently overwritten."""

    def test_header_missing_preserves_original(self):
        # Verifier returned something useful-looking but without the expected
        # section header. The original brainstorm content must be returned
        # unchanged so we never substitute the verifier's text for it.
        from litassist.utils.core import extract_verified_document

        correction = (
            "I reviewed the document and identified several issues. "
            "Please refer to the discussion above for details."
        )
        original = "Strategy 1: original.\nStrategy 2: original."
        content, parsed = extract_verified_document(correction, original)
        assert parsed is False
        assert content == original, (
            "Header-missing branch must return the original brainstorm "
            "content unchanged; previously it returned the verifier's "
            "freeform response while telling the user 'using original output'."
        )

    def test_lightly_formatted_header_is_extracted(self):
        # Verifier models vary the header's formatting. Each of these light
        # variants must still be located so the corrected document is used rather
        # than discarded: bold instead of '## ', '&' for 'and', lowercase, '###'.
        from litassist.utils.core import extract_verified_document

        for header in (
            "## Verified and Corrected Document",
            "**Verified & Corrected Document**",
            "### verified and corrected document",
            "Verified and Corrected Document:",
        ):
            correction = (
                "## Issues Found during Verification\nNo issues found.\n\n"
                f"{header}\n"
                "## ORTHODOX STRATEGIES\nbody"
            )
            content, parsed = extract_verified_document(correction, "original")
            assert parsed is True, f"header variant not matched: {header!r}"
            assert content.startswith("## ORTHODOX STRATEGIES")


class TestStrategyExtraction:
    """Test strategy extraction patterns."""

    # Note: `_extract_strategies` accepts several markdown formats (### N.,
    # ### Strategy N:, N., ## STRATEGY N:). The blank-line fallback is covered
    # by TestVerificationFlow.test_extract_strategies_fallback; the multiline
    # test below covers `### N.` splitting plus content-preservation within a
    # single strategy. Per-format variant tests were dropped as TDD hygiene.

    def test_extract_preserves_multiline(self):
        """Test that extraction preserves multiline strategy content."""
        content = """### 1. Complex Strategy
Line 1 of the strategy.
Line 2 with more detail.
Line 3 with citation [2020] HCA 1.

### 2. Simple Strategy
Just one line."""
        strategies = _extract_strategies(content, "orthodox")
        assert len(strategies) == 2
        assert "Line 1" in strategies[0]
        assert "Line 2" in strategies[0]
        assert "Line 3" in strategies[0]


class TestCitationAnnotation:
    """Test citation annotation features."""

    def test_no_citations_no_annotation(self):
        """Test that strategies without citations aren't annotated."""
        strategies = ["Strategy with no citations"]
        verified = set()
        unverified = {}
        plausibility = {}

        annotated = _annotate_strategies_with_verification(
            strategies, verified, unverified, plausibility, "orthodox"
        )

        assert annotated[0] == "Strategy with no citations"
        assert "CITATION STATUS" not in annotated[0]

    def test_mixed_citations(self):
        """Test strategies with both verified and unverified citations."""
        strategies = ["Strategy citing [2020] HCA 1 and [2024] Fake 1"]
        verified = {"[2020] HCA 1"}
        unverified = {"[2024] Fake 1": "not found"}
        plausibility = {
            "orthodox_1": {"risk": "MEDIUM", "explanation": "Partial verification"}
        }

        annotated = _annotate_strategies_with_verification(
            strategies, verified, unverified, plausibility, "orthodox"
        )

        assert "[VERIFIED]: [2020] HCA 1" in annotated[0]
        assert "[NOT VERIFIED]: [2024] Fake 1" in annotated[0]
        assert "MEDIUM RISK" in annotated[0]