"""
Comprehensive tests for the strategy command functionality.

Tests cover validation, extraction, generation, document creation, and error handling.
All tests run offline using mocked dependencies.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from click.testing import CliRunner
import click

from litassist.commands.strategy import strategy
from litassist.commands.strategy.validators import (
    validate_case_facts_format,
    extract_legal_issues,
)
from litassist.commands.strategy.ranker import create_consolidated_reasoning_trace


class TestCaseFactsValidation:
    """Test case facts format validation functionality."""

    def test_validate_case_facts_format_case_insensitive(self):
        """Test validation is case insensitive."""
        content = """
        parties:
        John Smith v ABC Corporation
        
        background:
        Test background
        
        key events:
        Timeline
        
        legal issues:
        Contract breach
        
        evidence available:
        Documents
        
        opposing arguments:
        Defense
        
        procedural history:
        History
        
        jurisdiction:
        Federal Court
        
        applicable law:
        Contract law
        
        client objectives:
        Damages
        """
        assert validate_case_facts_format(content) is True

    def test_validate_case_facts_format_empty_content(self):
        """Test validation with empty content."""
        assert validate_case_facts_format("") is False

    def test_validate_case_facts_format_whitespace_only(self):
        """Test validation with whitespace-only content."""
        assert validate_case_facts_format("   \n\n   \t   ") is False


class TestLegalIssuesExtraction:
    """Test legal issues extraction functionality."""

    def test_extract_legal_issues_success_standard(self):
        """Test successful extraction from standard format."""
        content = """
        Parties:
        John Smith v ABC Corporation
        
        Legal Issues:
        1. Breach of contract
        2. Professional negligence
        3. Misleading and deceptive conduct
        
        Evidence Available:
        Documents and witnesses
        """
        issues = extract_legal_issues(content)
        # The actual function returns numbered items, so adjust expectations
        expected = [
            "1. Breach of contract",
            "2. Professional negligence",
            "3. Misleading and deceptive conduct",
        ]
        assert issues == expected

    def test_extract_legal_issues_success_bullet_points(self):
        """Test extraction with bullet point formatting."""
        content = """
        Legal Issues:
        • Contract breach claim
        • Negligence in professional duty
        • Statutory compensation claim
        
        Evidence Available:
        Documents
        """
        issues = extract_legal_issues(content)
        expected = [
            "Contract breach claim",
            "Negligence in professional duty",
            "Statutory compensation claim",
        ]
        assert issues == expected

    def test_extract_legal_issues_success_mixed_formatting(self):
        """Test extraction with mixed formatting."""
        content = """
        Legal Issues:
        - Primary issue: Contract breach
        * Secondary issue: Negligence
        1. Tertiary issue: Statutory claims
        
        Evidence Available:
        Documents
        """
        issues = extract_legal_issues(content)
        assert len(issues) == 3
        assert "Primary issue: Contract breach" in issues
        assert "Secondary issue: Negligence" in issues
        assert "1. Tertiary issue: Statutory claims" in issues

    def test_extract_legal_issues_missing_section(self):
        """Test extraction when Legal Issues section is missing."""
        content = """
        Parties:
        John Smith v ABC Corporation
        
        Background:
        Test background
        
        Evidence Available:
        Documents
        """
        issues = extract_legal_issues(content)
        assert issues == []

    def test_extract_legal_issues_empty_section(self):
        """Test extraction when Legal Issues section is empty."""
        content = """
        Legal Issues:
        
        Evidence Available:
        Documents
        
        """
        issues = extract_legal_issues(content)
        assert issues == []

    def test_extract_legal_issues_case_insensitive(self):
        """Test extraction is case insensitive."""
        content = """
        legal issues:
        1. Contract breach
        2. Negligence claim
        
        evidence available:
        Documents
        """
        issues = extract_legal_issues(content)
        assert len(issues) == 2
        assert "1. Contract breach" in issues
        assert "2. Negligence claim" in issues

    def test_extract_legal_issues_numbered_bold_inline(self):
        """extractfacts numbered/bold format with the issue inline on the heading
        line: capture the inline issue and stop at the next (also inline) heading
        rather than grabbing subsequent sections."""
        content = (
            "1. **Parties**: Smith v Jones\n"
            "2. **Background**: A contract dispute\n"
            "4. **Legal Issues**: Whether the contract was breached\n"
            "5. **Evidence Available**: The signed contract and emails\n"
            "6. **Opposing Arguments**: Denies breach\n"
        )
        issues = extract_legal_issues(content)
        assert issues == ["Whether the contract was breached"]


class TestStrategyGeneration:
    """Test strategy generation functionality."""

    @patch("litassist.commands.strategy.core.LLMClientFactory.for_command")
    @patch("litassist.commands.strategy.file_handler.save_command_output")
    @patch("litassist.commands.strategy.file_handler.save_log")
    @patch("litassist.commands.strategy.core.verify_content_if_needed")
    @patch("litassist.commands.strategy.core.PROMPTS")
    def test_strategy_generation_success(
        self,
        mock_prompts,
        mock_verify,
        mock_save_log,
        mock_save_output,
        mock_llm_factory,
    ):
        """Test successful strategy generation."""
        # Mock prompts
        mock_prompts.get.return_value = "Test prompt"

        # Mock verification
        mock_verify.return_value = ("Verified content", False, None)

        # Mock LLM client
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "## OPTION 1: Apply for Interim Injunction\nDetailed strategy content...",
            {"total_tokens": 500, "prompt_tokens": 300, "completion_tokens": 200},
        )
        mock_client.validate_citations.return_value = []
        mock_llm_factory.return_value = mock_client
        mock_save_output.return_value = "outputs/strategy_test.txt"

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
            with runner.isolated_filesystem():
                result = runner.invoke(
                    strategy,
                    [facts_file, "--outcome", "Obtain interim injunction"],
                    obj={"premium": False},
                )

            assert result.exit_code == 0
            assert "Strategy generation complete!" in result.output
            # Output format changed, just verify it succeeded
            assert "Strategic options saved to:" in result.output

            # Verify LLM was called
            mock_client.complete.assert_called()
            mock_client.validate_citations.assert_called()

        finally:
            Path(facts_file).unlink()

    @patch("litassist.commands.strategy.core.LLMClientFactory.for_command")
    @patch("litassist.commands.strategy.file_handler.save_command_output")
    @patch("litassist.commands.strategy.file_handler.save_log")
    @patch("litassist.commands.strategy.core.verify_content_if_needed")
    @patch("litassist.commands.strategy.core.PROMPTS")
    def test_strategy_short_circuit_recorded_not_complete(
        self,
        mock_prompts,
        mock_verify,
        mock_save_log,
        mock_save_output,
        mock_llm_factory,
    ):
        """A verification short-circuit must be recorded in the saved metadata,
        not reported as completed verification."""
        mock_prompts.get.return_value = "Test prompt"
        # Verification short-circuited before the LLM stage.
        mock_verify.return_value = ("Strategy content", False, "citation pattern issues")
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "## OPTION 1: Something\nDetail...",
            {"total_tokens": 10, "prompt_tokens": 5, "completion_tokens": 5},
        )
        mock_client.validate_citations.return_value = []
        mock_llm_factory.return_value = mock_client
        mock_save_output.return_value = "outputs/strategy_test.txt"

        facts = "\n".join(
            f"{h}: x"
            for h in [
                "Parties", "Background", "Key Events", "Legal Issues",
                "Evidence Available", "Opposing Arguments", "Procedural History",
                "Jurisdiction", "Applicable Law", "Client Objectives",
            ]
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(facts)
            facts_file = f.name
        try:
            runner = CliRunner()
            with runner.isolated_filesystem():
                result = runner.invoke(
                    strategy, [facts_file, "--outcome", "Win"], obj={"premium": False}
                )
            assert result.exit_code == 0
            assert "short-circuited" in result.output.lower()
            # The saved strategy metadata records the short-circuit, not "Standard verification".
            verifications = [
                call.kwargs["metadata"]["Verification"]
                for call in mock_save_output.call_args_list
                if call.kwargs.get("metadata", {}).get("Verification")
            ]
            assert any("short-circuited" in v.lower() for v in verifications), verifications
        finally:
            Path(facts_file).unlink()

    @patch("litassist.commands.strategy.core.LLMClientFactory.for_command")
    def test_strategy_generation_invalid_facts(self, mock_llm_factory):
        """Test strategy generation with invalid case facts."""
        # Create invalid case facts file (missing required headings)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Invalid case facts content without proper headings")
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(strategy, [facts_file, "--outcome", "Test outcome"])

            assert result.exit_code != 0
            assert "must follow the required 10-heading structure" in result.output

        finally:
            Path(facts_file).unlink()

    @patch("litassist.commands.strategy.core.LLMClientFactory.for_command")
    def test_strategy_generation_no_legal_issues(self, mock_llm_factory):
        """Test strategy generation when no legal issues can be extracted."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                """
            Parties:
            John Smith v ABC Corporation
            
            Background:
            Test background
            
            Key Events:
            Test events
            
            Legal Issues:
            
            Evidence Available:
            Documents
            
            Opposing Arguments:
            Defense
            
            Procedural History:
            History
            
            Jurisdiction:
            Federal Court
            
            Applicable Law:
            Contract law
            
            Client Objectives:
            Damages
            """
            )
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(
                strategy,
                [facts_file, "--outcome", "Test outcome"],
                obj={"premium": False},
            )

            assert result.exit_code != 0
            # The error message may vary - just check that it indicates an issue with legal issues or LLM generation
            # Check for error about legal issues extraction
            assert result.exit_code != 0
            assert "Could not extract legal issues" in result.output

        finally:
            Path(facts_file).unlink()


class TestReasoningTrace:
    """Test reasoning trace functionality."""

    def test_create_consolidated_reasoning_trace_success(self):
        """Test creation of consolidated reasoning trace."""
        # Mock reasoning trace data
        trace_data = [
            {
                "option_number": 1,
                "trace": Mock(
                    issue="Contract breach",
                    applicable_law="Contract law principles",
                    application="Facts support breach claim",
                    conclusion="Strong case for damages",
                    confidence=85,
                    sources=["Smith v Jones [2020] FCA 123"],
                ),
            },
            {
                "option_number": 2,
                "trace": Mock(
                    issue="Negligence claim",
                    applicable_law="Tort law principles",
                    application="Duty of care established",
                    conclusion="Moderate prospects",
                    confidence=70,
                    sources=["Brown v Green [2019] HCA 456"],
                ),
            },
        ]

        result = create_consolidated_reasoning_trace(trace_data, "Obtain damages")

        assert "CONSOLIDATED REASONING" in result
        assert "Strategic Options for: Obtain damages" in result
        assert "STRATEGIC OPTION 1 - REASONING" in result
        assert "STRATEGIC OPTION 2 - REASONING" in result
        assert "Contract breach" in result
        assert "Negligence claim" in result
        assert "85%" in result
        assert "70%" in result

    def test_create_consolidated_reasoning_trace_empty_traces(self):
        """Test consolidated trace with empty reasoning traces."""
        trace_data = [
            {"option_number": 1, "trace": None},
            {"option_number": 2, "trace": None},
        ]

        result = create_consolidated_reasoning_trace(trace_data, "Test outcome")

        assert "CONSOLIDATED REASONING" in result
        assert "No reasoning trace available" in result


class TestErrorHandling:
    """Test error handling scenarios."""

    @patch("litassist.commands.strategy.core.LLMClientFactory.for_command")
    def test_strategy_generation_llm_failure(self, mock_llm_factory):
        """Test handling of LLM generation failures."""
        # Mock LLM client that raises exception
        mock_client = MagicMock()
        mock_client.complete.side_effect = Exception("LLM service unavailable")
        mock_llm_factory.return_value = mock_client

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(
                """
            Parties:
            John Smith v ABC Corporation
            
            Background:
            Test background
            
            Key Events:
            Test events
            
            Legal Issues:
            Contract breach
            
            Evidence Available:
            Documents
            
            Opposing Arguments:
            Defense
            
            Procedural History:
            History
            
            Jurisdiction:
            Federal Court
            
            Applicable Law:
            Contract law
            
            Client Objectives:
            Damages
            """
            )
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(strategy, [facts_file, "--outcome", "Test outcome"])

            # An LLM API failure must surface as a non-zero exit, not silent success.
            assert result.exit_code != 0

        finally:
            Path(facts_file).unlink()

    @patch("litassist.commands.strategy.core.validate_file_size_limit")
    def test_strategy_generation_file_size_limit(self, mock_validate_size):
        """Test handling of file size limit exceeded."""
        mock_validate_size.side_effect = click.ClickException("File size exceeds limit")

        valid_case_facts = """
        1. PARTIES:
        John Smith v ABC Corporation

        2. BACKGROUND:
        Test background

        3. KEY EVENTS:
        Timeline

        4. LEGAL ISSUES:
        Contract breach

        5. EVIDENCE AVAILABLE:
        Documents

        6. OPPOSING ARGUMENTS:
        Defense position

        7. PROCEDURAL HISTORY:
        Court history

        8. JURISDICTION:
        Federal Court

        9. APPLICABLE LAW:
        Contract law

        10. CLIENT OBJECTIVES:
        Damages
        """

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(valid_case_facts)
            facts_file = f.name

        try:
            runner = CliRunner()
            result = runner.invoke(strategy, [facts_file, "--outcome", "Test outcome"])

            assert result.exit_code != 0
            assert "File size exceeds limit" in result.output

        finally:
            Path(facts_file).unlink()


class TestStrategyFileIntegration:
    """Test integration with brainstorm strategy files."""

    def test_parse_strategies_file_counts_bold_most_likely(self):
        """The analysis prompt emits most-likely entries as '**N. Title**'
        (strategies.yaml), so the parser must count those bold-numbered items -
        not just bare '1.' lines."""
        from litassist.utils.core import parse_strategies_file

        content = (
            "## MOST LIKELY TO SUCCEED\n"
            "**1. Alpha**\nJustification: a\n"
            "**2. Beta**\nJustification: b\n"
            "**3. Gamma**\nJustification: c\n"
            "**4. Delta**\nJustification: d\n"
            "**5. Epsilon**\nJustification: e\n"
        )

        assert parse_strategies_file(content)["most_likely_count"] == 5

    def test_parse_strategies_files_merges_counts_and_labels(self):
        """Multiple brainstorm sets: counts SUM, content joined under labels."""
        from litassist.utils.core import parse_strategies_files

        creative = (
            "# Side: plaintiff\n# Area: civil\n\n"
            "## ORTHODOX STRATEGIES\n"
            "### Strategy 1: Alpha\nx\n### Strategy 2: Beta\nx\n\n"
            "## UNORTHODOX STRATEGIES\n### Strategy 1: Gamma\nx\n\n"
            "## MOST LIKELY TO SUCCEED\n1. Do alpha\n"
        )
        research = (
            "# Side: plaintiff\n# Area: civil\n\n"
            "## ORTHODOX STRATEGIES\n"
            "### Strategy 1: Delta\nx\n### Strategy 2: Epsilon\nx\n"
            "### Strategy 3: Zeta\nx\n\n"
            "## UNORTHODOX STRATEGIES\n"
            "### Strategy 1: Eta\nx\n### Strategy 2: Theta\nx\n\n"
            "## MOST LIKELY TO SUCCEED\n1. Do delta\n2. Do epsilon\n"
        )

        result = parse_strategies_files(
            [
                ("brainstorm_creative.txt", creative),
                ("brainstorm_research.txt", research),
            ]
        )

        # Counts summed across both sets (creative 2/1/1 + research 3/2/2).
        assert result["orthodox_count"] == 5
        assert result["unorthodox_count"] == 3
        assert result["most_likely_count"] == 3
        # First file's metadata is kept.
        assert result["metadata"]["side"] == "plaintiff"
        assert result["metadata"]["area"] == "civil"
        # Both bodies present, each under its === label === separator.
        assert "=== brainstorm_creative.txt ===" in result["raw_content"]
        assert "=== brainstorm_research.txt ===" in result["raw_content"]
        assert "Alpha" in result["raw_content"]
        assert "Zeta" in result["raw_content"]


_VALID_CASE_FACTS = """
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


_CREATIVE_SET = (
    "## ORTHODOX STRATEGIES\n"
    "### Strategy 1: Alpha\nx\n### Strategy 2: Beta\nx\n\n"
    "## UNORTHODOX STRATEGIES\n### Strategy 1: Gamma\nx\n\n"
    "## MOST LIKELY TO SUCCEED\n1. Do alpha\n"
)
_RESEARCH_SET = (
    "## ORTHODOX STRATEGIES\n"
    "### Strategy 1: Delta\nx\n### Strategy 2: Epsilon\nx\n### Strategy 3: Zeta\nx\n\n"
    "## UNORTHODOX STRATEGIES\n### Strategy 1: Eta\nx\n### Strategy 2: Theta\nx\n\n"
    "## MOST LIKELY TO SUCCEED\n1. Do delta\n2. Do epsilon\n"
)


class TestStrategiesMultipleFiles:
    """--strategies is repeatable: strategy consumes BOTH brainstorm sets.

    The dual-brainstorm design produces a creative AND a research set. Passing
    one --strategies flag per set must MERGE both: the displayed counts are the
    SUM across files (creative 2/1/1 + research 3/2/2 = 5/3/3), proving neither
    set was dropped. PROMPTS is mocked to a constant here, so the merged CONTENT
    never reaches the prompt; the on-screen counts are the observable proof of
    consumption. Reaching exit 0 also proves the tuple -> string substitution at
    the two metadata sites (core.py:330/495 that used the path value directly).
    """

    @patch("litassist.commands.strategy.core.LLMClientFactory.for_command")
    @patch("litassist.commands.strategy.file_handler.save_command_output")
    @patch("litassist.commands.strategy.file_handler.save_log")
    @patch("litassist.commands.strategy.core.verify_content_if_needed")
    @patch("litassist.commands.strategy.core.PROMPTS")
    def test_two_flags_merge_both_sets(
        self,
        mock_prompts,
        mock_verify,
        mock_save_log,
        mock_save_output,
        mock_llm_factory,
    ):
        mock_prompts.get.return_value = "Test prompt"
        mock_verify.return_value = ("Verified content", False, None)
        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "## OPTION 1: Do the thing\nContent...",
            {"total_tokens": 10},
        )
        mock_client.validate_citations.return_value = []
        mock_llm_factory.return_value = mock_client
        mock_save_output.return_value = "outputs/strategy_test.txt"

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(_VALID_CASE_FACTS)
            facts_file = f.name

        try:
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open(
                    "brainstorm_creative_20260101_000000_000000000.txt", "w"
                ) as fh:
                    fh.write(_CREATIVE_SET)
                with open(
                    "brainstorm_research_20260102_000000_000000000.txt", "w"
                ) as fh:
                    fh.write(_RESEARCH_SET)

                result = runner.invoke(
                    strategy,
                    [
                        facts_file,
                        "--outcome",
                        "Obtain damages",
                        "--strategies",
                        "brainstorm_creative_*.txt",
                        "--strategies",
                        "brainstorm_research_*.txt",
                    ],
                    obj={"premium": False},
                )

                assert result.exit_code == 0, result.output
                # Summed across BOTH sets - neither was dropped.
                assert "5 orthodox strategies" in result.output
                assert "3 unorthodox strategies" in result.output
                assert "3 marked as most likely" in result.output
        finally:
            Path(facts_file).unlink()


# Integration test markers
pytestmark = [pytest.mark.unit, pytest.mark.strategy, pytest.mark.offline]
