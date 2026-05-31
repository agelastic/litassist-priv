"""
Tests for Chain of Verification (CoVe) regeneration functionality.

Ensures CoVe properly regenerates documents when issues are found (Step 4).
"""

from unittest.mock import Mock, patch
import pytest
from litassist.verification_chain import run_cove_verification

_MOCK_MODEL = "test/mock-model"


class TestCoVeRegeneration:
    """Test the complete 4-step CoVe process including regeneration."""

    def test_cove_regenerates_content_when_issues_found(self):
        """Test that CoVe regenerates content when verification finds issues."""

        # Original content with issues
        original_content = """
        LEGAL MEMORANDUM
        
        The case of Smith v Jones [2025] FAKE 123 establishes that...
        This was decided on February 30, 2024 (invalid date).
        """

        # Mock responses for each CoVe stage
        mock_questions = """
        1. Is the citation Smith v Jones [2025] FAKE 123 valid?
        2. Is February 30, 2024 a valid date?
        """

        mock_answers = """
        1. No - This citation format is invalid. No court called FAKE exists.
        2. No - February 30 does not exist in any calendar year.
        """

        mock_issues = """
        Issues found:
        - Invalid citation: [2025] FAKE 123
        - Invalid date: February 30, 2024
        """

        regenerated_content = """
        LEGAL MEMORANDUM
        
        The case of Smith v Jones [citation to be verified] establishes that...
        This was decided on [date to be confirmed].
        """

        with patch("litassist.verification_chain.LLMClientFactory") as mock_factory:
            # Create mock clients for each stage
            mock_questions_client = Mock()
            mock_answers_client = Mock()
            mock_verify_client = Mock()
            mock_final_client = Mock()

            # Set up mock responses
            mock_questions_client.complete.return_value = (
                mock_questions,
                {"total_tokens": 50},
            )
            mock_questions_client.model = _MOCK_MODEL

            mock_answers_client.complete.return_value = (
                mock_answers,
                {"total_tokens": 60},
            )
            mock_answers_client.model = _MOCK_MODEL

            mock_verify_client.complete.return_value = (
                mock_issues,
                {"total_tokens": 40},
            )
            mock_verify_client.model = _MOCK_MODEL

            mock_final_client.complete.return_value = (
                regenerated_content,
                {"total_tokens": 100},
            )
            mock_final_client.model = _MOCK_MODEL

            # Configure factory to return appropriate clients
            def get_client(command):
                if command == "cove-questions":
                    return mock_questions_client
                elif command == "cove-answers":
                    return mock_answers_client
                elif command == "cove-verify":
                    return mock_verify_client
                elif command == "cove-final":
                    return mock_final_client

            mock_factory.for_command.side_effect = get_client

            # Mock save_log and fetch_citation_context to avoid file operations and PDF processing
            with patch("litassist.verification_chain.save_log"):
                with patch(
                    "litassist.verification_chain.fetch_citation_context"
                ) as mock_fetch:
                    mock_fetch.return_value = (
                        {}, []
                    )  # Return empty dict and no failures
                    # Run CoVe verification
                    final_content, results = run_cove_verification(
                        original_content, "test"
                    )

            # Assertions
            assert final_content != original_content, "Content should be regenerated"
            assert (
                final_content == regenerated_content
            ), "Should return regenerated content"
            assert not results["cove"]["passed"], "Should indicate issues were found"
            assert results["cove"][
                "regenerated"
            ], "Should indicate regeneration occurred"
            assert (
                "[citation to be verified]" in final_content
            ), "Should have placeholder for bad citation"
            assert (
                "[date to be confirmed]" in final_content
            ), "Should have placeholder for bad date"

            # Verify all 4 stages were called
            assert mock_factory.for_command.call_count == 4
            mock_factory.for_command.assert_any_call("cove-questions")
            mock_factory.for_command.assert_any_call("cove-answers")
            mock_factory.for_command.assert_any_call("cove-verify")
            mock_factory.for_command.assert_any_call("cove-final")

    def test_cove_skips_regeneration_when_no_issues(self):
        """Test that CoVe doesn't regenerate when no issues are found."""

        original_content = """
        LEGAL MEMORANDUM
        
        The case of Mabo v Queensland (No 2) (1992) 175 CLR 1 establishes...
        This was decided on June 3, 1992.
        """

        mock_questions = """
        1. Is Mabo v Queensland (No 2) (1992) 175 CLR 1 a valid citation?
        2. Is June 3, 1992 a valid date?
        """

        mock_answers = """
        1. Yes - This is a valid High Court of Australia citation.
        2. Yes - June 3, 1992 is a valid date.
        """

        # Structured verdict required: literal "No issues found" used to pass
        # by substring match alone, which leaked through quoted / negated text.
        mock_no_issues = "Issues: none\nVERDICT: PASS"

        with patch("litassist.verification_chain.LLMClientFactory") as mock_factory:
            # Create mock clients
            mock_questions_client = Mock()
            mock_answers_client = Mock()
            mock_verify_client = Mock()
            mock_final_client = Mock()

            # Set up mock responses
            mock_questions_client.complete.return_value = (
                mock_questions,
                {"total_tokens": 50},
            )
            mock_questions_client.model = _MOCK_MODEL

            mock_answers_client.complete.return_value = (
                mock_answers,
                {"total_tokens": 60},
            )
            mock_answers_client.model = _MOCK_MODEL

            mock_verify_client.complete.return_value = (
                mock_no_issues,
                {"total_tokens": 20},
            )
            mock_verify_client.model = _MOCK_MODEL

            # Configure factory
            def get_client(command):
                if command == "cove-questions":
                    return mock_questions_client
                elif command == "cove-answers":
                    return mock_answers_client
                elif command == "cove-verify":
                    return mock_verify_client
                elif command == "cove-final":
                    return mock_final_client

            mock_factory.for_command.side_effect = get_client

            # Mock save_log and fetch_citation_context to avoid file operations and PDF processing
            with patch("litassist.verification_chain.save_log"):
                with patch(
                    "litassist.verification_chain.fetch_citation_context"
                ) as mock_fetch:
                    mock_fetch.return_value = (
                        {}, []
                    )  # Return empty dict and no failures
                    # Run CoVe verification
                    final_content, results = run_cove_verification(
                        original_content, "test"
                    )

            # Assertions
            assert (
                final_content == original_content
            ), "Content should not change when no issues"
            assert results["cove"]["passed"], "Should indicate no issues found"
            assert not results["cove"]["regenerated"], "Should indicate no regeneration"

            # Verify only 3 stages called (no regeneration)
            assert mock_factory.for_command.call_count == 3
            mock_factory.for_command.assert_any_call("cove-questions")
            mock_factory.for_command.assert_any_call("cove-answers")
            mock_factory.for_command.assert_any_call("cove-verify")
            # Should NOT call cove-final
            mock_final_client.complete.assert_not_called()

    def test_verification_chain_uses_regenerated_content(self):
        """Test that verification_chain no longer automatically runs CoVe."""

        from litassist.verification_chain import run_verification_chain

        original_content = "Document with [2025] FAKE 999 citation"

        with (
            patch(
                "litassist.verification_chain.validate_citation_patterns"
            ) as mock_patterns,
            patch(
                "litassist.verification_chain.verify_all_citations"
            ) as mock_verify_citations,
            patch("litassist.verification_chain.LLMClientFactory") as mock_factory,
        ):
            # Mock pattern validation passes
            mock_patterns.return_value = []

            # Mock citation verification passes
            mock_verify_citations.return_value = ([], [])

            # Mock LLM client
            mock_client = Mock()
            mock_client.verify.return_value = (original_content, {})
            mock_factory.for_command.return_value = mock_client

            # Run verification chain for extractfacts (NO auto CoVe anymore)
            final_content, results = run_verification_chain(
                original_content, "extractfacts"
            )

            # Assertions - CoVe is no longer automatic in verification_chain
            assert (
                final_content == original_content
            ), "Should keep original content (no CoVe in verification_chain)"
            assert (
                "cove" not in results
            ), "CoVe should not be in results (removed from verification_chain)"

            # Verify LLM verification was called
            mock_factory.for_command.assert_called_with("verification")


class TestCoVeVerdictParsing:
    """Regression tests: CoVe must use structured VERDICT lines rather than
    substring match against 'no issues found', which previously passed
    quoted / negated text."""

    def _run_cove_with_verify_response(self, verify_response: str):
        from unittest.mock import Mock, patch
        from litassist.verification_chain import run_cove_verification

        with patch("litassist.verification_chain.LLMClientFactory") as mock_factory:
            mock_questions_client = Mock()
            mock_answers_client = Mock()
            mock_verify_client = Mock()
            mock_final_client = Mock()

            mock_questions_client.complete.return_value = ("1. Q?", {"total_tokens": 1})
            mock_questions_client.model = _MOCK_MODEL
            mock_answers_client.complete.return_value = ("1. A.", {"total_tokens": 1})
            mock_answers_client.model = _MOCK_MODEL
            mock_verify_client.complete.return_value = (verify_response, {"total_tokens": 1})
            mock_verify_client.model = _MOCK_MODEL
            mock_final_client.complete.return_value = ("REGENERATED", {"total_tokens": 1})
            mock_final_client.model = _MOCK_MODEL

            def get_client(command):
                return {
                    "cove-questions": mock_questions_client,
                    "cove-answers": mock_answers_client,
                    "cove-verify": mock_verify_client,
                    "cove-final": mock_final_client,
                }[command]

            mock_factory.for_command.side_effect = get_client

            with patch("litassist.verification_chain.save_log"):
                with patch(
                    "litassist.verification_chain.fetch_citation_context"
                ) as mock_fetch:
                    mock_fetch.return_value = ({}, [])
                    _, results = run_cove_verification("Some document", "test")
            return results

    def test_negated_no_issues_found_does_not_pass(self):
        # Verifier text containing "no issues found" inside a negation must
        # not be parsed as a PASS. Substring matching allowed this through.
        response = (
            'The verifier reports: the answer is not "no issues found".\n'
            "Multiple inconsistencies were detected.\n"
            "VERDICT: FAIL"
        )
        results = self._run_cove_with_verify_response(response)
        assert results["cove"]["passed"] is False
        assert results["cove"]["regenerated"] is True

    def test_missing_verdict_fails_closed(self):
        # No VERDICT line at all: must fail closed (treat as FAIL) rather
        # than accidentally passing.
        response = "Reviewed the document. All clear."
        results = self._run_cove_with_verify_response(response)
        assert results["cove"]["passed"] is False, (
            "Missing VERDICT line must fail closed; substring match used to "
            "accidentally pass anything containing 'no issues found' or "
            "anything without it (depending on phrasing)."
        )

    def test_structured_pass_verdict_passes(self):
        response = "Issues: none\nVERDICT: PASS"
        results = self._run_cove_with_verify_response(response)
        assert results["cove"]["passed"] is True
        assert results["cove"]["regenerated"] is False


class TestVerificationShortCircuitVisibility:
    """run_verification_chain must surface when it bails before LLM verification,
    so callers do not report 'verification applied' for content that was only
    pattern/citation-checked."""

    def test_pattern_issue_short_circuit_is_recorded_and_announced(self, capsys):
        from litassist.verification_chain import run_verification_chain

        with patch(
            "litassist.verification_chain.validate_citation_patterns"
        ) as mock_patterns:
            mock_patterns.return_value = ["dodgy citation"]
            content = "Document with a dodgy citation"
            final, results = run_verification_chain(content, "extractfacts")

        assert final == content
        assert results.get("short_circuit") == "citation pattern issues"
        assert "short-circuit" in capsys.readouterr().out.lower()

    def test_unverified_citation_short_circuit_is_recorded_and_announced(self, capsys):
        from litassist.verification_chain import run_verification_chain

        with (
            patch(
                "litassist.verification_chain.validate_citation_patterns"
            ) as mock_patterns,
            patch(
                "litassist.verification_chain.verify_all_citations"
            ) as mock_verify,
        ):
            mock_patterns.return_value = []
            mock_verify.return_value = ([], ["Made Up v Nobody [2099] HCA 1"])
            content = "Document citing Made Up v Nobody [2099] HCA 1"
            final, results = run_verification_chain(content, "strategy")

        assert final == content
        assert results.get("short_circuit") == "unverified citations"
        assert "short-circuit" in capsys.readouterr().out.lower()


# Test markers
pytestmark = [pytest.mark.unit, pytest.mark.cove, pytest.mark.offline]
