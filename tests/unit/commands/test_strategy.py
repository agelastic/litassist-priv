"""
Unit tests for the strategy command.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from click.testing import CliRunner
from click import ClickException

from litassist.commands.strategy import (
    strategy,
    validate_case_facts_format,
    extract_legal_issues,
    format_strategic_options,
    format_next_steps,
    format_draft_document,
)


class TestStrategyCommand:
    """Test the strategy command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.valid_case_facts = """Parties:
Plaintiff: John Smith
Defendant: ABC Corp

Background:
Test background

Key Events:
Event 1

Legal Issues:
Issue 1
Issue 2

Evidence Available:
Evidence 1

Opposing Arguments:
Argument 1

Procedural History:
History 1

Jurisdiction:
Federal Court

Applicable Law:
Contract Law

Client Objectives:
Win case"""

    @patch("litassist.commands.strategy.LLMClient")
    @patch("litassist.commands.strategy.save_log")
    def test_strategy_success(self, mock_save_log, mock_llm_client):
        """Test successful strategy generation."""
        mock_llm_instance = Mock()
        mock_llm_instance.complete.side_effect = [
            # Strategic options response
            (
                '{"options": [{"title": "Option 1", "probability": 75, "hurdles": []}]}',
                {"tokens": 100},
            ),
            # Next steps response
            ('{"steps": ["Step 1", "Step 2"]}', {"tokens": 100}),
            # Document response
            ('{"doc_type": "claim", "content": "Test claim"}', {"tokens": 100}),
        ]
        mock_llm_client.return_value = mock_llm_instance

        with self.runner.isolated_filesystem():
            with open("case_facts.txt", "w") as f:
                f.write(self.valid_case_facts)

            result = self.runner.invoke(
                strategy, ["case_facts.txt", "--outcome", "Test outcome"]
            )

            assert result.exit_code == 0
            assert "STRATEGIC OPTIONS FOR: TEST OUTCOME" in result.output
            assert "OPTION 1" in result.output
            assert "RECOMMENDED NEXT STEPS" in result.output

    def test_strategy_invalid_format(self):
        """Test strategy with invalid case facts format."""
        with self.runner.isolated_filesystem():
            with open("case_facts.txt", "w") as f:
                f.write("Invalid format")

            result = self.runner.invoke(
                strategy, ["case_facts.txt", "--outcome", "Test outcome"]
            )

            assert result.exit_code != 0
            assert "does not follow the required 10-heading structure" in result.output

    def test_strategy_missing_legal_issues(self):
        """Test strategy with missing legal issues."""
        facts_without_issues = self.valid_case_facts.replace("Legal Issues:", "Other:")

        with self.runner.isolated_filesystem():
            with open("case_facts.txt", "w") as f:
                f.write(facts_without_issues)

            result = self.runner.invoke(
                strategy, ["case_facts.txt", "--outcome", "Test outcome"]
            )

            assert result.exit_code != 0
            assert "Could not extract legal issues" in result.output

    @patch("litassist.commands.strategy.LLMClient")
    def test_strategy_llm_error(self, mock_llm_client):
        """Test error handling for LLM failure."""
        mock_llm_instance = Mock()
        mock_llm_instance.complete.side_effect = Exception("API Error")
        mock_llm_client.return_value = mock_llm_instance

        with self.runner.isolated_filesystem():
            with open("case_facts.txt", "w") as f:
                f.write(self.valid_case_facts)

            result = self.runner.invoke(
                strategy, ["case_facts.txt", "--outcome", "Test outcome"]
            )

            assert result.exit_code != 0
            assert "LLM error" in result.output


class TestStrategyUtilityFunctions:
    """Test utility functions in the strategy module."""

    def test_validate_case_facts_format_valid(self):
        """Test validation with valid format."""
        valid_facts = """Parties:
Test

Background:
Test

Key Events:
Test

Legal Issues:
Test

Evidence Available:
Test

Opposing Arguments:
Test

Procedural History:
Test

Jurisdiction:
Test

Applicable Law:
Test

Client Objectives:
Test"""
        assert validate_case_facts_format(valid_facts) is True

    def test_validate_case_facts_format_missing_heading(self):
        """Test validation with missing heading."""
        invalid_facts = """Parties:
Test

Background:
Test"""
        assert validate_case_facts_format(invalid_facts) is False

    def test_extract_legal_issues_success(self):
        """Test successful legal issue extraction."""
        case_text = """Some text
Legal Issues:
Issue 1
Issue 2
Issue 3

Evidence Available:
Some evidence"""

        issues = extract_legal_issues(case_text)
        assert len(issues) == 3
        assert "Issue 1" in issues
        assert "Issue 2" in issues
        assert "Issue 3" in issues

    def test_extract_legal_issues_not_found(self):
        """Test extraction when legal issues not found."""
        case_text = "No legal issues section here"
        issues = extract_legal_issues(case_text)
        assert issues == []

    def test_format_strategic_options(self):
        """Test formatting of strategic options."""
        options = [
            {
                "title": "Test Option",
                "probability": 75,
                "hurdles": [
                    "Hurdle 1 — Case v Case [2020] 123",
                    "Hurdle 2 — Another v Case [2021] 456",
                ],
                "missing_facts": ["Fact 1", "Fact 2"],
            }
        ]

        output = format_strategic_options(options, "Test Outcome")
        assert "STRATEGIC OPTIONS FOR: TEST OUTCOME" in output
        assert "Test Option" in output
        assert "75%" in output
        assert "Hurdle 1" in output
        assert "Fact 1" in output

    def test_format_next_steps(self):
        """Test formatting of next steps."""
        steps = [
            "Step 1: Do something",
            "Step 2: Do something else",
            "Step 3: Final step",
        ]

        output = format_next_steps(steps)
        assert "RECOMMENDED NEXT STEPS" in output
        assert "1. Step 1: Do something" in output
        assert "2. Step 2: Do something else" in output
        assert "3. Step 3: Final step" in output

    def test_format_draft_document_claim(self):
        """Test formatting of claim document."""
        document = {
            "parties": [
                {"number": 1, "description": "The plaintiff is John"},
                {"number": 2, "description": "The defendant is ABC"},
            ],
            "facts": [
                {"number": 1, "description": "Fact 1"},
                {"number": 2, "description": "Fact 2"},
            ],
            "causes": [
                {"number": 1, "description": "Breach", "authority": "Case v Case"}
            ],
            "relief": [{"number": 1, "description": "Damages"}],
        }

        output = format_draft_document("claim", document)
        assert "STATEMENT OF CLAIM" in output
        assert "PARTIES" in output
        assert "STATEMENT OF FACTS" in output
        assert "CAUSES OF ACTION" in output
        assert "RELIEF SOUGHT" in output
