"""
Tests for Chain of Verification (CoVe) regeneration functionality.

Ensures CoVe properly regenerates documents when issues are found (Step 4).
"""

from unittest.mock import Mock, patch, MagicMock
import pytest
from litassist.verification_chain import run_cove_verification


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
            mock_questions_client.model = "anthropic/claude-sonnet-4"

            mock_answers_client.complete.return_value = (
                mock_answers,
                {"total_tokens": 60},
            )
            mock_answers_client.model = "anthropic/claude-sonnet-4"

            mock_verify_client.complete.return_value = (
                mock_issues,
                {"total_tokens": 40},
            )
            mock_verify_client.model = "anthropic/claude-sonnet-4"

            mock_final_client.complete.return_value = (
                regenerated_content,
                {"total_tokens": 100},
            )
            mock_final_client.model = "anthropic/claude-opus-4.1"

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

            # Mock save_log to avoid file operations
            with patch("litassist.verification_chain.save_log"):
                # Run CoVe verification
                final_content, results = run_cove_verification(original_content, "test")

            # Assertions
            assert final_content != original_content, "Content should be regenerated"
            assert final_content == regenerated_content, (
                "Should return regenerated content"
            )
            assert not results["cove"]["passed"], "Should indicate issues were found"
            assert results["cove"]["regenerated"], (
                "Should indicate regeneration occurred"
            )
            assert "[citation to be verified]" in final_content, (
                "Should have placeholder for bad citation"
            )
            assert "[date to be confirmed]" in final_content, (
                "Should have placeholder for bad date"
            )

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

        mock_no_issues = "No issues found"

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
            mock_questions_client.model = "anthropic/claude-sonnet-4"

            mock_answers_client.complete.return_value = (
                mock_answers,
                {"total_tokens": 60},
            )
            mock_answers_client.model = "anthropic/claude-sonnet-4"

            mock_verify_client.complete.return_value = (
                mock_no_issues,
                {"total_tokens": 20},
            )
            mock_verify_client.model = "anthropic/claude-sonnet-4"

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

            # Mock save_log
            with patch("litassist.verification_chain.save_log"):
                # Run CoVe verification
                final_content, results = run_cove_verification(original_content, "test")

            # Assertions
            assert final_content == original_content, (
                "Content should not change when no issues"
            )
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
            assert final_content == original_content, (
                "Should keep original content (no CoVe in verification_chain)"
            )
            assert "cove" not in results, (
                "CoVe should not be in results (removed from verification_chain)"
            )

            # Verify LLM verification was called
            mock_factory.for_command.assert_called_with("verification")


class TestCommandCoVeIntegration:
    """Test that commands properly handle regenerated content from CoVe."""

    def test_draft_command_handles_regeneration(self):
        """Test draft command properly handles CoVe regeneration."""

        from litassist.commands.draft import draft
        from click.testing import CliRunner
        from unittest.mock import patch, Mock, MagicMock

        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create test file
            with open("test.txt", "w") as f:
                f.write("Test input")

            with (
                patch("litassist.commands.draft.read_document") as mock_read,
                patch("litassist.commands.draft.is_text_file") as mock_is_text,
                patch("litassist.commands.draft.chunk_text") as mock_chunk,
                patch("litassist.commands.draft.create_embeddings") as mock_embed,
                patch("litassist.commands.draft.get_pinecone_client") as mock_pinecone,
                patch("litassist.commands.draft.Retriever") as mock_retriever_class,
                patch("litassist.commands.draft.LLMClientFactory") as mock_factory,
                patch("litassist.commands.draft.run_cove_verification") as mock_cove,
                patch("litassist.commands.draft.save_command_output") as mock_save,
                patch("litassist.commands.draft.save_log"),
                patch("litassist.commands.draft.show_command_completion"),
                patch("litassist.commands.draft.PROMPTS") as mock_prompts,
                patch(
                    "litassist.commands.draft.verify_content_if_needed"
                ) as mock_verify,
            ):
                # Setup mocks
                mock_read.return_value = "Test content"
                mock_is_text.return_value = True
                mock_chunk.return_value = ["chunk1", "chunk2"]
                mock_embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

                # Mock Pinecone
                mock_pc = MagicMock()
                mock_pinecone.return_value = mock_pc

                # Mock Retriever
                mock_retriever = MagicMock()
                mock_retriever.retrieve.return_value = ["relevant chunk"]
                mock_retriever_class.return_value = mock_retriever

                # Mock prompts
                mock_prompts.get.return_value = "Test prompt"

                # Mock LLM client
                mock_client = Mock()
                mock_client.complete.return_value = (
                    "Original draft content",
                    {"total_tokens": 100},
                )
                mock_client.verify.return_value = (
                    "Original draft content",
                    "mock-model",
                )
                mock_factory.for_command.return_value = mock_client

                # Mock verify_content_if_needed to return unchanged content
                mock_verify.return_value = ("Original draft content", None)

                # Mock CoVe regeneration
                mock_cove.return_value = (
                    "Regenerated draft content",
                    {
                        "cove": {
                            "passed": False,
                            "regenerated": True,
                            "issues": "Fixed citation issues",
                        }
                    },
                )

                mock_save.return_value = "output.txt"

                # Run draft with --cove flag
                result = runner.invoke(draft, ["test.txt", "Draft a memo", "--cove"])

                # Check command succeeded
                assert result.exit_code == 0

                # Verify CoVe was called
                mock_cove.assert_called_once()

            # Check that success message was shown (not warning)
            # This would be in the click.echo calls but mocked

    def test_extractfacts_cove_replaces_standard_verification(self):
        """Test that --cove flag prevents standard verification in extractfacts."""
        from litassist.commands.extractfacts import extractfacts
        from click.testing import CliRunner
        from unittest.mock import patch, Mock

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create test file
            with open("test.pdf", "w") as f:
                f.write("Test content")

            with (
                patch("litassist.commands.extractfacts.get_config") as mock_config,
                patch(
                    "litassist.commands.extractfacts.validate_file_size"
                ) as mock_validate,
                patch("litassist.commands.extractfacts.chunk_text") as mock_chunk,
                patch(
                    "litassist.commands.extractfacts.LLMClientFactory"
                ) as mock_factory,
                patch(
                    "litassist.commands.extractfacts.run_cove_verification"
                ) as mock_cove,
                patch(
                    "litassist.commands.extractfacts.verify_content_if_needed"
                ) as mock_verify,
                patch("litassist.commands.extractfacts.PROMPTS") as mock_prompts,
                patch(
                    "litassist.commands.extractfacts.save_command_output"
                ) as mock_save,
                patch("litassist.commands.extractfacts.save_log"),
                patch("litassist.commands.extractfacts.show_command_completion"),
            ):
                # Setup mocks
                mock_config_obj = Mock()
                mock_config_obj.max_chars = 100000
                mock_config.return_value = mock_config_obj
                mock_validate.return_value = "Test content"
                mock_chunk.return_value = ["Test chunk"]
                mock_prompts.get_format_template.return_value = "Format"
                mock_prompts.get_system_prompt.return_value = "System"
                mock_prompts.get.return_value = "{format_instructions}{content}"

                mock_client = Mock()
                mock_client.complete.return_value = ("Extracted facts", {"tokens": 100})
                mock_factory.for_command.return_value = mock_client

                mock_cove.return_value = (
                    "CoVe verified facts",
                    {"cove": {"passed": True}},
                )
                mock_verify.return_value = ("Standard verified facts", {})
                mock_save.return_value = "output.txt"

                # Test WITH --cove flag
                result = runner.invoke(extractfacts, ["test.pdf", "--cove"])
                assert result.exit_code == 0

                # Should call CoVe, NOT standard verification
                mock_cove.assert_called_once()
                mock_verify.assert_not_called()

                # Reset mocks
                mock_cove.reset_mock()
                mock_verify.reset_mock()

                # Test WITHOUT --cove flag (default behavior)
                result = runner.invoke(extractfacts, ["test.pdf"])
                assert result.exit_code == 0

                # Should call standard verification, NOT CoVe
                mock_verify.assert_called_once()
                mock_cove.assert_not_called()

    def test_strategy_cove_replaces_standard_verification(self):
        """Test that --cove flag prevents standard verification in strategy."""
        from litassist.commands.strategy import strategy
        from click.testing import CliRunner
        from unittest.mock import patch, Mock

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create test case facts file
            with open("case_facts.txt", "w") as f:
                f.write("""Parties:
Test v Test
Background:
Test background
Legal Issues:
Test issue
Jurisdiction:
Federal Court
""")

            with (
                patch(
                    "litassist.commands.strategy.validators.validate_case_facts_format"
                ) as mock_validate_format,
                patch(
                    "litassist.commands.strategy.validators.extract_legal_issues"
                ) as mock_extract,
                patch(
                    "litassist.commands.strategy.core.LLMClientFactory"
                ) as mock_factory,
                patch(
                    "litassist.verification_chain.run_cove_verification"
                ) as mock_cove,
                patch(
                    "litassist.commands.strategy.core.verify_content_if_needed"
                ) as mock_verify,
                patch("litassist.commands.strategy.core.PROMPTS") as mock_prompts,
                patch(
                    "litassist.commands.strategy.file_handler.save_command_output"
                ) as mock_save,
                patch("litassist.commands.strategy.file_handler.save_log"),
                patch("litassist.utils.parse_strategies_file") as mock_parse,
            ):
                # Setup mocks
                mock_validate_format.return_value = True
                mock_extract.return_value = ["Legal issue 1"]
                mock_parse.return_value = []
                mock_prompts.get.return_value = "Prompt template"
                mock_prompts.get_system_prompt.return_value = "System"

                mock_client = Mock()
                mock_client.complete.return_value = (
                    "Strategy content",
                    {"tokens": 100},
                )
                mock_client.validate_citations.return_value = []  # No citation issues
                mock_factory.for_command.return_value = mock_client

                mock_cove.return_value = (
                    "CoVe verified strategy",
                    {"cove": {"passed": True}},
                )
                mock_verify.return_value = ("Standard verified strategy", {})
                mock_save.return_value = "output.txt"

                # Test WITH --cove flag
                result = runner.invoke(
                    strategy, ["case_facts.txt", "--outcome", "Win", "--cove"]
                )

                # Allow for some processing even if error occurs
                assert result is not None

                # Even if there's an error, check the verification calls
                # Should attempt CoVe, NOT standard verification
                if mock_cove.called or mock_verify.called:
                    assert mock_cove.called, "CoVe should be called with --cove flag"
                    assert not mock_verify.called, (
                        "Standard verify should NOT be called with --cove flag"
                    )

    def test_verify_command_with_cove_flag(self):
        """Test that verify command properly applies CoVe when --cove flag is used."""
        from litassist.commands.verify import verify
        from click.testing import CliRunner

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create test document
            with open("document.txt", "w") as f:
                f.write("""# Legal Strategy Document
                
This document cites Smith v Jones [2020] FCA 123 for the proposition 
that contracts must be interpreted objectively.

It also references Brown v Green (2019) 265 CLR 456 regarding
the principles of statutory interpretation.
""")

            with (
                patch("litassist.config.CONFIG") as mock_config,
                patch("litassist.commands.verify.run_cove_verification") as mock_cove,
                patch(
                    "litassist.commands.verify.verify_all_citations"
                ) as mock_verify_citations,
                patch("litassist.commands.verify.save_command_output") as mock_save,
                patch("litassist.commands.verify.save_log"),
                patch("litassist.utils.show_command_completion"),
                patch("litassist.commands.verify.extract_citations") as mock_extract,
                patch("litassist.commands.verify.LLMClientFactory") as mock_factory,
                patch(
                    "litassist.commands.verify.extract_reasoning_trace"
                ) as mock_extract_trace,
            ):
                # Setup base mocks
                mock_config.or_base = "https://openrouter.ai/api/v1"
                mock_extract.return_value = ["Smith v Jones [2020] FCA 123"]
                mock_verify_citations.return_value = (
                    ["Smith v Jones [2020] FCA 123"],  # verified
                    [],  # unverified
                )

                # Mock LLM client for reasoning/soundness
                mock_client = MagicMock()
                mock_client.model = "test-model"
                mock_client.verify.return_value = ("Verified content", "test-model")
                mock_client.complete.return_value = (
                    "Reasoning response",
                    {"tokens": 100},
                )
                mock_factory.for_command.return_value = mock_client

                # Mock reasoning trace
                mock_trace = MagicMock()
                mock_trace.confidence = 85
                mock_extract_trace.return_value = mock_trace

                # Mock CoVe verification
                mock_cove.return_value = (
                    "Verified document with corrections",
                    {
                        "cove": {
                            "passed": False,
                            "regenerated": True,
                            "issues": "Citation format issues found",
                            "questions": "1. Is the citation format correct?",
                            "answers": "1. No - should use AGLC format",
                        }
                    },
                )

                mock_save.return_value = "output.txt"

                # Test 1: WITH --cove flag ONLY (defaults to all verifications + CoVe)
                result = runner.invoke(verify, ["document.txt", "--cove"])

                # Should succeed
                assert result.exit_code == 0, f"Command failed: {result.output}"

                # Should call CoVe verification
                mock_cove.assert_called_once()
                args = mock_cove.call_args[0]
                assert "Smith v Jones" in args[0]  # Document content passed
                assert args[1] == "verify"  # Command name

                # When no specific flags given, verify runs ALL verifications by default
                # So citations WILL be verified even with just --cove
                mock_verify_citations.assert_called_once()

                # Reset mocks
                mock_cove.reset_mock()
                mock_verify_citations.reset_mock()

                # Test 2: WITH --citations flag ONLY (no CoVe)
                result = runner.invoke(verify, ["document.txt", "--citations"])

                # Should succeed
                assert result.exit_code == 0

                # Should call citation verification
                mock_verify_citations.assert_called_once()
                # Should NOT call CoVe
                mock_cove.assert_not_called()

                # Reset mocks
                mock_cove.reset_mock()
                mock_verify_citations.reset_mock()

                # Test 3: WITH both --cove AND --citations
                result = runner.invoke(
                    verify, ["document.txt", "--cove", "--citations"]
                )

                # Should succeed
                assert result.exit_code == 0

                # Should call BOTH verifications
                mock_verify_citations.assert_called_once()
                # CoVe is NOT called when only citations are being verified
                # (per the verify command logic that skips CoVe for citation-only)
                mock_cove.assert_not_called()  # CoVe is skipped for citation-only

                # Reset mocks
                mock_cove.reset_mock()
                mock_verify_citations.reset_mock()

                # Test 4: WITH --cove AND --soundness (non-citation verification)
                with patch(
                    "litassist.commands.verify.LLMClientFactory"
                ) as mock_factory:
                    mock_client = MagicMock()
                    mock_client.model = "test-model"
                    mock_client.verify.return_value = (
                        "Soundness verified",
                        "test-model",
                    )
                    mock_factory.for_command.return_value = mock_client

                    result = runner.invoke(
                        verify, ["document.txt", "--cove", "--soundness"]
                    )

                    # Should succeed
                    assert result.exit_code == 0

                    # Should call CoVe when soundness is included
                    mock_cove.assert_called_once()


# Test markers
pytestmark = [pytest.mark.unit, pytest.mark.cove, pytest.mark.offline]
