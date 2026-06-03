"""
Comprehensive tests for the draft command functionality.

Tests cover document generation, template handling, legal reasoning, and error scenarios.
All tests run offline using mocked dependencies.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from litassist.commands.draft.core import draft


class TestDraftCommand:
    """Test draft command functionality."""

    @patch("litassist.commands.draft.core.LLMClientFactory.for_command")
    @patch("litassist.commands.draft.core.save_command_output")
    @patch("litassist.commands.draft.core.save_log")
    @patch("litassist.commands.draft.prompt_builder.PROMPTS")
    def test_draft_statement_of_claim_success(
        self,
        mock_prompts,
        mock_save_log,
        mock_save_output,
        mock_llm_factory,
    ):
        """Test successful statement of claim generation."""
        # Mock prompts
        mock_prompts.get.return_value = "Test template"

        # Mock LLM client
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "STATEMENT OF CLAIM\n1. The plaintiff claims...",
            {"total_tokens": 800, "prompt_tokens": 500, "completion_tokens": 300},
        )
        mock_client.validate_citations.return_value = []
        mock_client.verify.return_value = (
            "STATEMENT OF CLAIM\n1. The plaintiff claims...",
            "mock-model",
        )
        mock_llm_factory.return_value = mock_client
        mock_save_output.return_value = "outputs/draft_test.txt"

        # Create test case facts file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                """
            Parties:
            John Smith v ABC Corporation
            
            Background:
            Contract dispute case
            
            Key Events:
            Contract signed and breached
            
            Legal Issues:
            Breach of contract
            
            Evidence Available:
            Contract documents
            
            Opposing Arguments:
            No breach occurred
            
            Procedural History:
            No prior proceedings
            
            Jurisdiction:
            Federal Court of Australia
            
            Applicable Law:
            Contract law
            
            Client Objectives:
            Obtain damages
            """
            )
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(
                draft,
                [facts_file, "statement_of_claim"],
                obj={"premium": False},
            )

            assert result.exit_code == 0
            assert "Draft complete!" in result.output

            # Verify LLM was called
            mock_client.complete.assert_called()

        finally:
            Path(facts_file).unlink()

    @patch("litassist.commands.draft.core.detect_factual_hallucinations")
    @patch("litassist.commands.draft.core.verify_content_if_needed")
    @patch("litassist.commands.draft.core.LLMClientFactory.for_command")
    @patch("litassist.commands.draft.core.save_command_output")
    @patch("litassist.commands.draft.core.save_log")
    @patch("litassist.commands.draft.prompt_builder.PROMPTS")
    def test_draft_short_circuit_recorded_not_applied(
        self,
        mock_prompts,
        mock_save_log,
        mock_save_output,
        mock_llm_factory,
        mock_verify,
        mock_halluc,
    ):
        """A verification short-circuit must be recorded in the draft's saved
        metadata, not reported as standard verification applied."""
        mock_prompts.get.return_value = "Test template"
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "DRAFT CONTENT",
            {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5},
        )
        mock_llm_factory.return_value = mock_client
        mock_save_output.return_value = "outputs/draft_test.txt"
        # Verification short-circuited before the LLM stage.
        mock_verify.return_value = ("DRAFT CONTENT", False, "citation pattern issues")
        mock_halluc.return_value = []

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Some source document content for drafting.")
            src = f.name
        try:
            runner = CliRunner()
            result = runner.invoke(
                draft, [src, "draft a demand letter"], obj={"premium": False}
            )
            assert result.exit_code == 0
            assert "short-circuited" in result.output.lower()
            # Final saved metadata records the short-circuit, not "Standard verification".
            final_meta = mock_save_output.call_args_list[-1].kwargs["metadata"]
            assert "short-circuited" in final_meta["Verification"].lower()
        finally:
            Path(src).unlink()

    @patch("litassist.commands.draft.core.LLMClientFactory.for_command")
    @patch("litassist.commands.draft.core.save_command_output")
    @patch("litassist.commands.draft.core.save_log")
    @patch("litassist.commands.draft.prompt_builder.PROMPTS")
    def test_draft_affidavit_success(
        self,
        mock_prompts,
        mock_save_log,
        mock_save_output,
        mock_llm_factory,
    ):
        """Test successful affidavit generation."""
        # Mock prompts
        mock_prompts.get.return_value = "Affidavit template"

        # Mock LLM client
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "AFFIDAVIT OF JOHN SMITH\nI, John Smith, make oath and say:",
            {"total_tokens": 600, "prompt_tokens": 400, "completion_tokens": 200},
        )
        mock_client.validate_citations.return_value = []
        mock_client.verify.return_value = (
            "AFFIDAVIT OF JOHN SMITH\nI, John Smith, make oath and say:",
            "mock-model",
        )
        mock_llm_factory.return_value = mock_client
        mock_save_output.return_value = "outputs/affidavit_test.txt"

        # Create test case facts file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                """
            Parties:
            John Smith v ABC Corporation
            
            Background:
            Witness to contract negotiations
            
            Key Events:
            Witnessed contract signing
            
            Legal Issues:
            Contract formation
            
            Evidence Available:
            Witness testimony
            
            Opposing Arguments:
            Witness unreliable
            
            Procedural History:
            None
            
            Jurisdiction:
            Federal Court
            
            Applicable Law:
            Evidence law
            
            Client Objectives:
            Establish facts
            """
            )
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(
                draft, [facts_file, "affidavit"], obj={"premium": False}
            )

            assert result.exit_code == 0
            assert "Draft complete!" in result.output

        finally:
            Path(facts_file).unlink()


class TestDocumentTemplates:
    """Test document template functionality."""

    def test_statement_of_claim_template_elements(self):
        """Test that statement of claim template contains required elements."""
        from litassist.prompts import PROMPTS

        template = PROMPTS.get("documents.statement_of_claim")
        assert "STATEMENT OF CLAIM" in template.upper() or "CLAIM" in template.upper()
        assert len(template) > 100  # Template should have substantial content

    def test_affidavit_template_elements(self):
        """Test that affidavit template contains required elements."""
        from litassist.prompts import PROMPTS

        template = PROMPTS.get("documents.affidavit")
        assert "AFFIDAVIT" in template.upper() or "OATH" in template.upper()
        assert len(template) > 100

    def test_originating_application_template_elements(self):
        """Test that originating application template contains required elements."""
        from litassist.prompts import PROMPTS

        template = PROMPTS.get("documents.originating_application")
        assert "APPLICATION" in template.upper() or "ORIGINATING" in template.upper()
        assert len(template) > 100


class TestDraftErrorHandling:
    """Test error handling scenarios for draft command."""

    @patch("litassist.commands.draft.core.LLMClientFactory.for_command")
    def test_llm_failure_handling(self, mock_llm_factory):
        """Test handling of LLM generation failures."""
        # Mock LLM client that raises exception
        mock_client = MagicMock()
        mock_client.complete.side_effect = Exception("LLM service unavailable")
        mock_llm_factory.return_value = mock_client

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                """
            Parties: Smith v Jones
            Background: Test case
            Key Events: Events occurred
            Legal Issues: Legal issue
            Evidence Available: Evidence
            Opposing Arguments: Arguments
            Procedural History: History
            Jurisdiction: Court
            Applicable Law: Law
            Client Objectives: Objectives
            """
            )
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(
                draft,
                [facts_file, "statement_of_claim"],
                obj={"premium": False},
            )

            assert result.exit_code != 0
            assert "error" in result.output.lower() or "fail" in result.output.lower()

        finally:
            Path(facts_file).unlink()

    @patch("litassist.commands.draft.document_processor.read_document")
    def test_file_size_limit_handling(self, mock_read_document):
        """Test handling of file reading errors."""
        import click

        mock_read_document.side_effect = click.ClickException("File size exceeds limit")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(
                draft,
                [facts_file, "statement_of_claim"],
                obj={"premium": False},
            )

            assert result.exit_code != 0
            assert "File size exceeds limit" in result.output

        finally:
            Path(facts_file).unlink()


class TestDraftIntegration:
    """Test integration scenarios for draft command."""

    @patch("litassist.citation.verify.verify_all_citations")
    @patch("litassist.citation.verify.verify_single_citation")
    @patch("litassist.commands.draft.core.LLMClientFactory.for_command")
    @patch("litassist.commands.draft.core.save_command_output")
    @patch("litassist.commands.draft.core.save_log")
    @patch("litassist.commands.draft.prompt_builder.PROMPTS")
    def test_draft_with_verification_warnings(
        self,
        mock_prompts,
        mock_save_log,
        mock_save_output,
        mock_llm_factory,
        mock_verify_single,
        mock_verify_all,
    ):
        """Test draft command with citation validation warnings."""
        # Mock citation verification to prevent real API calls
        mock_verify_all.return_value = ([], [("[2025] FAKE 999", "Citation not found")])
        mock_verify_single.return_value = (False, "", "Not found", "")

        # Mock prompts
        mock_prompts.get.return_value = "Test template"

        # Mock LLM client with citation issues
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "STATEMENT OF CLAIM\nWith invalid citation [2025] FAKE 999",
            {"total_tokens": 500},
        )
        mock_client.validate_citations.return_value = [
            "Invalid citation format detected",
            "Citation [2025] FAKE 999 could not be verified",
        ]
        mock_client.verify.return_value = (
            "STATEMENT OF CLAIM\nWith invalid citation [2025] FAKE 999",
            "mock-model",
        )
        mock_llm_factory.return_value = mock_client
        mock_save_output.return_value = "test_output.txt"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                """
            Parties: Smith v Jones
            Background: Test case
            Key Events: Events occurred
            Legal Issues: Legal issue
            Evidence Available: Evidence
            Opposing Arguments: Arguments
            Procedural History: History
            Jurisdiction: Court
            Applicable Law: Law
            Client Objectives: Objectives
            """
            )
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(
                draft,
                [facts_file, "statement_of_claim"],
                obj={"premium": False},
            )

            # Should complete but with warnings
            assert result.exit_code == 0

        finally:
            Path(facts_file).unlink()

    @patch("litassist.commands.draft.core.LLMClientFactory.for_command")
    @patch("litassist.commands.draft.core.save_command_output")
    @patch("litassist.commands.draft.core.save_log")
    @patch("litassist.commands.draft.prompt_builder.PROMPTS")
    def test_draft_premium_mode(
        self,
        mock_prompts,
        mock_save_log,
        mock_save_output,
        mock_llm_factory,
    ):
        """Test draft command in premium mode."""
        # Mock prompts
        mock_prompts.get.return_value = "Premium template"

        # Mock premium LLM client
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "PREMIUM STATEMENT OF CLAIM\nDetailed legal analysis...",
            {"total_tokens": 1200, "prompt_tokens": 800, "completion_tokens": 400},
        )
        mock_client.validate_citations.return_value = []
        mock_client.verify.return_value = (
            "PREMIUM STATEMENT OF CLAIM\nDetailed legal analysis...",
            "mock-model",
        )
        mock_llm_factory.return_value = mock_client
        mock_save_output.return_value = "outputs/premium_draft.txt"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                """
            Parties: Smith v Jones
            Background: Complex commercial dispute
            Key Events: Series of contract breaches
            Legal Issues: Multiple contract and tort issues
            Evidence Available: Extensive documentation
            Opposing Arguments: Complex defenses
            Procedural History: Prior proceedings
            Jurisdiction: Federal Court
            Applicable Law: Commercial law
            Client Objectives: Comprehensive relief
            """
            )
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(
                draft,
                [facts_file, "statement_of_claim"],
                obj={"premium": True},
            )

            assert result.exit_code == 0
            assert "Draft complete!" in result.output

            # Verify LLM factory was called twice (draft and verification)
            assert mock_llm_factory.call_count >= 1
            # First call should be for draft
            mock_llm_factory.assert_any_call("draft")

        finally:
            Path(facts_file).unlink()


# Test markers
pytestmark = [pytest.mark.unit, pytest.mark.draft, pytest.mark.offline]
