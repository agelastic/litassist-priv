"""
Unit tests for the verify command.

Tests citation verification, legal soundness checking, and reasoning trace
generation/verification functionality.
"""

import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
import pytest
from click.testing import CliRunner

from litassist.commands.verify import (
    verify,
    _format_citation_report,
    _parse_soundness_issues,
    _format_soundness_report,
    _verify_reasoning_trace,
)
from litassist.utils import LegalReasoningTrace


class TestVerifyCommand:
    """Test suite for verify command functionality."""

    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def sample_legal_text(self):
        """Sample legal text for testing."""
        return """
        In the landmark case of Mabo v Queensland (No 2) [1992] HCA 23, the High Court 
        recognized native title in Australia. This decision overturned the doctrine of 
        terra nullius.

        The principle established in Donoghue v Stevenson [1932] AC 562 regarding 
        duty of care remains fundamental to negligence law.

        As stated in Smith v Jones [2025] NSWSC 999, the test for causation requires...
        (Note: This is a fictional future case for testing)
        """

    @pytest.fixture
    def sample_text_with_reasoning(self):
        """Sample legal text with existing reasoning trace."""
        return """
        Legal analysis of contract breach...

        === LEGAL REASONING TRACE ===
        Issue: Whether the defendant breached the service contract by failing to deliver on time
        Applicable Law: Contract law principles regarding breach and remedies under Australian Consumer Law
        Application to Facts: The defendant agreed to deliver goods by March 1 but delivered on March 15
        Conclusion: The defendant materially breached the contract entitling plaintiff to damages
        Confidence: 85%
        Sources: Hadley v Baxendale (1854) 9 Exch 341; Competition and Consumer Act 2010
        """

    @pytest.fixture
    def temp_file(self, tmp_path):
        """Create a temporary file for testing."""
        temp_file = tmp_path / "test_document.txt"
        return str(temp_file)

    def test_verify_all_checks_by_default(self, runner, temp_file, sample_legal_text):
        """Test that verify runs all checks when no flags are provided."""
        # Write sample text to temp file
        with open(temp_file, 'w') as f:
            f.write(sample_legal_text)

        with patch('litassist.commands.verify.verify_all_citations') as mock_citations, \
             patch('litassist.commands.verify.LLMClientFactory') as mock_llm_factory, \
             patch('litassist.commands.verify.save_log') as mock_save_log:
            
            # Mock citation verification
            mock_citations.return_value = (
                ["Mabo v Queensland (No 2) [1992] HCA 23", "Donoghue v Stevenson [1932] AC 562"],
                [("Smith v Jones [2025] NSWSC 999", "Future citation")]
            )
            
            # Mock LLM client
            mock_client = Mock()
            mock_client.verify.return_value = "No legal issues found."
            mock_client.complete.return_value = ("Analysis with reasoning trace", {})
            mock_llm_factory.for_command.return_value = mock_client

            result = runner.invoke(verify, [temp_file])
            
            assert result.exit_code == 0
            assert "🔍 Verifying" in result.output
            assert "Citation verification complete" in result.output
            assert "2 citations verified, 1 unverified" in result.output
            assert "Legal soundness check complete" in result.output
            assert "0 issues identified" in result.output
            assert "Reasoning trace generated" in result.output
            assert "3 reports generated" in result.output

    def test_verify_citations_only(self, runner, temp_file, sample_legal_text):
        """Test citation verification only."""
        with open(temp_file, 'w') as f:
            f.write(sample_legal_text)

        with patch('litassist.commands.verify.verify_all_citations') as mock_citations, \
             patch('litassist.commands.verify.extract_citations') as mock_extract, \
             patch('litassist.commands.verify.save_log') as mock_save_log:
            
            mock_extract.return_value = ["Mabo v Queensland (No 2) [1992] HCA 23"]
            mock_citations.return_value = (
                ["Mabo v Queensland (No 2) [1992] HCA 23"],
                []
            )

            result = runner.invoke(verify, [temp_file, '--citations'])
            
            assert result.exit_code == 0
            assert "Citation verification complete" in result.output
            assert "1 citations verified, 0 unverified" in result.output
            assert "Legal soundness check" not in result.output
            assert "Reasoning trace" not in result.output
            assert "1 reports generated" in result.output

    def test_verify_soundness_only(self, runner, temp_file, sample_legal_text):
        """Test legal soundness verification only."""
        with open(temp_file, 'w') as f:
            f.write(sample_legal_text)

        with patch('litassist.commands.verify.LLMClientFactory') as mock_llm_factory, \
             patch('litassist.commands.verify.save_log') as mock_save_log:
            
            mock_client = Mock()
            mock_client.verify.return_value = "The document contains an error in citation format."
            mock_llm_factory.for_command.return_value = mock_client

            result = runner.invoke(verify, [temp_file, '--soundness'])
            
            assert result.exit_code == 0
            assert "Legal soundness check complete" in result.output
            assert "1 issues identified" in result.output
            assert "Citation verification" not in result.output
            assert "Reasoning trace" not in result.output

    def test_verify_reasoning_existing_trace(self, runner, temp_file, sample_text_with_reasoning):
        """Test verification of existing reasoning trace."""
        with open(temp_file, 'w') as f:
            f.write(sample_text_with_reasoning)

        with patch('litassist.commands.verify.save_reasoning_trace') as mock_save_trace, \
             patch('litassist.commands.verify.save_log') as mock_save_log:
            
            mock_save_trace.return_value = temp_file.replace('.txt', '_reasoning.txt')

            result = runner.invoke(verify, [temp_file, '--reasoning'])
            
            assert result.exit_code == 0
            assert "Reasoning trace verified" in result.output
            assert "IRAC structure complete" in result.output
            assert "Confidence: 85%" in result.output

    def test_verify_reasoning_generate_new(self, runner, temp_file, sample_legal_text):
        """Test generation of new reasoning trace."""
        with open(temp_file, 'w') as f:
            f.write(sample_legal_text)

        with patch('litassist.commands.verify.LLMClientFactory') as mock_llm_factory, \
             patch('litassist.commands.verify.save_reasoning_trace') as mock_save_trace, \
             patch('litassist.commands.verify.save_log') as mock_save_log:
            
            mock_client = Mock()
            mock_client.complete.return_value = (
                """Analysis of the legal text...
                
                === LEGAL REASONING TRACE ===
                Issue: Analysis of native title and negligence principles
                Applicable Law: Mabo v Queensland, Donoghue v Stevenson
                Application to Facts: The text discusses landmark cases
                Conclusion: The principles remain fundamental to Australian law
                Confidence: 90%
                Sources: Mabo v Queensland (No 2) [1992] HCA 23; Donoghue v Stevenson [1932] AC 562
                """,
                {}
            )
            mock_llm_factory.for_command.return_value = mock_client
            mock_save_trace.return_value = temp_file.replace('.txt', '_reasoning.txt')

            result = runner.invoke(verify, [temp_file, '--reasoning'])
            
            assert result.exit_code == 0
            assert "Reasoning trace generated" in result.output
            assert "IRAC structure complete" in result.output
            assert "Confidence: 90%" in result.output

    def test_verify_empty_file(self, runner, temp_file):
        """Test handling of empty file."""
        with open(temp_file, 'w') as f:
            f.write("")

        result = runner.invoke(verify, [temp_file])
        
        assert result.exit_code != 0
        assert "File is empty" in result.output

    def test_verify_nonexistent_file(self, runner):
        """Test handling of non-existent file."""
        result = runner.invoke(verify, ['nonexistent.txt'])
        
        assert result.exit_code != 0

    def test_format_citation_report(self):
        """Test citation report formatting."""
        verified = ["Case1 [2020] HCA 1", "Case2 [2021] FCA 2"]
        unverified = [("Case3 [2025] VSC 999", "Future date")]
        
        report = _format_citation_report(verified, unverified, total_found=3)
        
        assert "# Citation Verification Report" in report
        assert "**Total citations found**: 3" in report
        assert "**Verified citations**: 2" in report
        assert "**Unverified citations**: 1" in report
        assert "✅ Case1 [2020] HCA 1" in report
        assert "❌ Case3 [2025] VSC 999" in report
        assert "Future date" in report

    def test_parse_soundness_issues(self):
        """Test parsing of soundness issues from LLM response."""
        # Test with issues
        response_with_issues = """
        The document contains several errors. First, the citation format is incorrect 
        for the Queensland case. Second, the date should be 1993, not 1992. Third, 
        the principle stated needs to be clarified.
        """
        issues = _parse_soundness_issues(response_with_issues)
        assert len(issues) >= 2
        assert any("incorrect" in issue for issue in issues)
        
        # Test with no issues
        response_no_issues = "The document is legally sound with no issues found."
        issues = _parse_soundness_issues(response_no_issues)
        assert len(issues) == 0

    def test_verify_reasoning_trace_complete(self):
        """Test verification of complete reasoning trace."""
        trace = LegalReasoningTrace(
            issue="Whether contract was breached",
            applicable_law="Australian Contract Law and Consumer Protection Act",
            application="The facts clearly show a breach of the delivery terms",
            conclusion="Breach established, damages warranted",
            confidence=85,
            sources=["Contract Act", "Case Law"],
            command="verify"
        )
        
        status = _verify_reasoning_trace(trace)
        assert status["complete"] == True
        assert len(status["issues"]) == 0

    def test_verify_reasoning_trace_incomplete(self):
        """Test verification of incomplete reasoning trace."""
        trace = LegalReasoningTrace(
            issue="Issue?",  # Too short
            applicable_law="Some law",  # Too short
            application="",  # Empty
            conclusion="Yes",  # Too short
            confidence=150,  # Invalid
            sources=[],  # Empty
            command="verify"
        )
        
        status = _verify_reasoning_trace(trace)
        assert status["complete"] == False
        assert len(status["issues"]) >= 5
        assert any("Issue statement" in issue for issue in status["issues"])
        assert any("confidence score" in issue for issue in status["issues"])

    def test_verify_with_api_failure(self, runner, temp_file, sample_legal_text):
        """Test handling of API failures."""
        with open(temp_file, 'w') as f:
            f.write(sample_legal_text)

        with patch('litassist.commands.verify.verify_all_citations') as mock_citations:
            mock_citations.side_effect = Exception("API unavailable")

            result = runner.invoke(verify, [temp_file, '--citations'])
            
            assert "Citation verification failed" in result.output
            assert "API unavailable" in result.output

    def test_output_files_created(self, runner, temp_file, sample_legal_text):
        """Test that output files are created with correct names."""
        with open(temp_file, 'w') as f:
            f.write(sample_legal_text)

        base_name = os.path.splitext(temp_file)[0]
        
        with patch('litassist.commands.verify.verify_all_citations') as mock_citations, \
             patch('litassist.commands.verify.LLMClientFactory') as mock_llm_factory, \
             patch('litassist.commands.verify.save_reasoning_trace') as mock_save_trace, \
             patch('litassist.commands.verify.save_log') as mock_save_log:
            
            mock_citations.return_value = (["Case1"], [])
            mock_client = Mock()
            mock_client.verify.return_value = "No issues"
            mock_client.complete.return_value = ("Analysis", {})
            mock_llm_factory.for_command.return_value = mock_client
            mock_save_trace.return_value = f"{base_name}_reasoning.txt"

            result = runner.invoke(verify, [temp_file])
            
            # Check that file operations were attempted for all three outputs
            assert result.exit_code == 0
            assert "_citations.txt" in result.output
            assert "_soundness.txt" in result.output
            assert "_reasoning.txt" in result.output