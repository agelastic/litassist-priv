"""
End-to-end workflow tests for LitAssist.
"""

import pytest
from unittest.mock import patch, Mock
from click.testing import CliRunner
import os

from litassist import cli


class TestEndToEndWorkflows:
    """Test complete workflows from start to finish."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("litassist.cli.validate_credentials")
    @patch("litassist.commands.extractfacts.LLMClient")
    @patch("litassist.commands.brainstorm.LLMClient")
    @patch("litassist.commands.strategy.LLMClient")
    def test_full_litigation_workflow(
        self, mock_strategy_llm, mock_brainstorm_llm, mock_extract_llm, mock_validate
    ):
        """Test complete workflow from PDF to strategy."""
        # Mock credential validation
        mock_validate.return_value = None

        # Setup mocks for each stage
        self._setup_extractfacts_mock(mock_extract_llm)
        self._setup_brainstorm_mock(mock_brainstorm_llm)
        self._setup_strategy_mock(mock_strategy_llm)

        with self.runner.isolated_filesystem():
            # Create test PDF
            with open("case_document.pdf", "w") as f:
                f.write("Mock PDF content with case details")

            # Step 1: Extract facts from PDF
            result = self.runner.invoke(cli.cli, ["extractfacts", "case_document.pdf"])
            assert result.exit_code == 0
            assert os.path.exists("case_facts.txt")
            print(f"Step 1 - Extract facts: {result.exit_code}")

            # Step 2: Brainstorm strategies
            result = self.runner.invoke(
                cli.cli,
                [
                    "brainstorm",
                    "case_facts.txt",
                    "--side",
                    "plaintiff",
                    "--area",
                    "civil",
                ],
            )
            assert result.exit_code == 0
            assert "Civil Law Strategies" in result.output
            print(f"Step 2 - Brainstorm: {result.exit_code}")

            # Step 3: Generate detailed strategy
            result = self.runner.invoke(
                cli.cli,
                ["strategy", "case_facts.txt", "--outcome", "Obtain injunction"],
            )
            assert result.exit_code == 0
            assert "STRATEGIC OPTIONS" in result.output
            print(f"Step 3 - Strategy: {result.exit_code}")

            # Verify audit logs were created
            assert os.path.exists("logs")
            log_files = os.listdir("logs")
            assert any("extractfacts" in f for f in log_files)
            assert any("brainstorm" in f for f in log_files)
            assert any("strategy" in f for f in log_files)

    @patch("litassist.cli.validate_credentials")
    @patch("litassist.commands.lookup.build")
    @patch("litassist.commands.lookup.LLMClient")
    def test_research_workflow(self, mock_lookup_llm, mock_google_build, mock_validate):
        """Test legal research workflow."""
        # Mock credential validation
        mock_validate.return_value = None

        # Mock Google CSE
        mock_service = Mock()
        mock_service.cse().list().execute.return_value = {
            "items": [
                {"link": "http://example.com/case1"},
                {"link": "http://example.com/case2"},
                {"link": "http://example.com/case3"},
            ]
        }
        mock_google_build.return_value = mock_service

        # Mock LLM response
        mock_llm_instance = Mock()
        mock_llm_instance.complete.return_value = (
            "Legal analysis with citations",
            {"tokens": 100},
        )
        mock_lookup_llm.return_value = mock_llm_instance

        # Run lookup command
        result = self.runner.invoke(
            cli.cli, ["lookup", "What are the elements of breach of contract?"]
        )

        assert result.exit_code == 0
        assert "Found links:" in result.output
        assert "http://example.com/case1" in result.output

    @patch("litassist.cli.validate_credentials")
    def test_workflow_with_invalid_parameters(self, mock_validate):
        """Test workflow with various invalid parameters."""
        mock_validate.return_value = None

        with self.runner.isolated_filesystem():
            # Test with non-existent file
            result = self.runner.invoke(cli.cli, ["extractfacts", "nonexistent.pdf"])
            assert result.exit_code != 0

            # Test with invalid command combination
            result = self.runner.invoke(
                cli.cli,
                ["brainstorm", "facts.txt", "--side", "prosecutor", "--area", "civil"],
            )
            assert result.exit_code != 0

            # Test with missing required parameters
            result = self.runner.invoke(
                cli.cli, ["strategy", "facts.txt"]  # Missing --outcome
            )
            assert result.exit_code != 0

    def _setup_extractfacts_mock(self, mock_llm):
        """Helper to setup extractfacts mock."""
        valid_facts = """Parties:
Plaintiff: Test Plaintiff
Defendant: Test Defendant

Background:
Test background information

Key Events:
1. Event one
2. Event two

Legal Issues:
1. Issue one
2. Issue two

Evidence Available:
1. Document A
2. Document B

Opposing Arguments:
1. Defense argument

Procedural History:
Case filed in 2024

Jurisdiction:
Federal Court

Applicable Law:
Contract law

Client Objectives:
Obtain injunction"""

        mock_instance = Mock()
        mock_instance.complete.return_value = (valid_facts, {"tokens": 200})
        mock_llm.return_value = mock_instance

    def _setup_brainstorm_mock(self, mock_llm):
        """Helper to setup brainstorm mock."""
        mock_instance = Mock()
        mock_instance.complete.return_value = (
            """1. Orthodox Strategies:
               - Strategy 1: File for injunction
               - Strategy 2: Seek damages
               
               2. Unorthodox Strategies:
               - Strategy 3: Alternative dispute resolution
               
               3. Most Likely to Succeed:
               - Strategy 1 has highest probability""",
            {"tokens": 300},
        )
        mock_llm.return_value = mock_instance

    def _setup_strategy_mock(self, mock_llm):
        """Helper to setup strategy mock."""
        mock_instance = Mock()
        mock_instance.complete.side_effect = [
            # Strategic options
            (
                '{"options": [{"title": "Injunction Application", "probability": 85, '
                '"hurdles": ["Standing requirement", "Irreparable harm"]}]}',
                {"tokens": 200},
            ),
            # Next steps
            (
                '{"steps": ["File application", "Prepare affidavits", "Serve defendant"]}',
                {"tokens": 100},
            ),
            # Document
            (
                '{"doc_type": "application", "content": "Application for injunction"}',
                {"tokens": 150},
            ),
        ]
        mock_llm.return_value = mock_instance
