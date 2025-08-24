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
        
        with patch('litassist.verification_chain.LLMClientFactory') as mock_factory:
            # Create mock clients for each stage
            mock_questions_client = Mock()
            mock_answers_client = Mock()
            mock_verify_client = Mock()
            mock_final_client = Mock()
            
            # Set up mock responses
            mock_questions_client.complete.return_value = (mock_questions, {"total_tokens": 50})
            mock_questions_client.model = "anthropic/claude-sonnet-4"
            
            mock_answers_client.complete.return_value = (mock_answers, {"total_tokens": 60})
            mock_answers_client.model = "anthropic/claude-sonnet-4"
            
            mock_verify_client.complete.return_value = (mock_issues, {"total_tokens": 40})
            mock_verify_client.model = "anthropic/claude-sonnet-4"
            
            mock_final_client.complete.return_value = (regenerated_content, {"total_tokens": 100})
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
            with patch('litassist.verification_chain.save_log'):
                # Run CoVe verification
                final_content, results = run_cove_verification(original_content, 'test')
            
            # Assertions
            assert final_content != original_content, "Content should be regenerated"
            assert final_content == regenerated_content, "Should return regenerated content"
            assert not results['cove']['passed'], "Should indicate issues were found"
            assert results['cove']['regenerated'], "Should indicate regeneration occurred"
            assert "[citation to be verified]" in final_content, "Should have placeholder for bad citation"
            assert "[date to be confirmed]" in final_content, "Should have placeholder for bad date"
            
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
        
        with patch('litassist.verification_chain.LLMClientFactory') as mock_factory:
            # Create mock clients
            mock_questions_client = Mock()
            mock_answers_client = Mock()
            mock_verify_client = Mock()
            mock_final_client = Mock()
            
            # Set up mock responses
            mock_questions_client.complete.return_value = (mock_questions, {"total_tokens": 50})
            mock_questions_client.model = "anthropic/claude-sonnet-4"
            
            mock_answers_client.complete.return_value = (mock_answers, {"total_tokens": 60})
            mock_answers_client.model = "anthropic/claude-sonnet-4"
            
            mock_verify_client.complete.return_value = (mock_no_issues, {"total_tokens": 20})
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
            with patch('litassist.verification_chain.save_log'):
                # Run CoVe verification
                final_content, results = run_cove_verification(original_content, 'test')
            
            # Assertions
            assert final_content == original_content, "Content should not change when no issues"
            assert results['cove']['passed'], "Should indicate no issues found"
            assert not results['cove']['regenerated'], "Should indicate no regeneration"
            
            # Verify only 3 stages called (no regeneration)
            assert mock_factory.for_command.call_count == 3
            mock_factory.for_command.assert_any_call("cove-questions")
            mock_factory.for_command.assert_any_call("cove-answers")
            mock_factory.for_command.assert_any_call("cove-verify")
            # Should NOT call cove-final
            mock_final_client.complete.assert_not_called()
    
    def test_verification_chain_uses_regenerated_content(self):
        """Test that verification_chain properly uses regenerated content from CoVe."""
        
        from litassist.verification_chain import run_verification_chain
        
        original_content = "Document with [2025] FAKE 999 citation"
        regenerated_content = "Document with [citation to be verified]"
        
        with patch('litassist.verification_chain.validate_citation_patterns') as mock_patterns, \
             patch('litassist.verification_chain.run_cove_verification') as mock_cove, \
             patch('litassist.verification_chain.LLMClientFactory'):
            
            # Mock pattern validation passes
            mock_patterns.return_value = []
            
            # Mock CoVe finds issues and regenerates
            mock_cove.return_value = (regenerated_content, {
                'cove': {
                    'passed': False,
                    'regenerated': True,
                    'issues': 'Invalid citation found'
                }
            })
            
            # Run verification chain for extractfacts (auto CoVe)
            final_content, results = run_verification_chain(
                original_content, 
                'extractfacts',
                skip_stages={'database', 'llm'}  # Skip other stages for test
            )
            
            # Assertions
            assert final_content == regenerated_content, "Should use regenerated content"
            assert results['cove_regenerated'], "Should mark as regenerated"
            assert results['cove_issues_found'], "Should mark issues found"
            
            # Verify CoVe was called
            mock_cove.assert_called_once()


class TestCommandCoVeIntegration:
    """Test that commands properly handle regenerated content from CoVe."""
    
    @patch('litassist.verification_chain.run_cove_verification')
    @patch('litassist.commands.draft.LLMClientFactory')
    @patch('litassist.commands.draft.click')
    def test_draft_command_handles_regeneration(self, mock_click, mock_factory, mock_cove):
        """Test draft command properly handles CoVe regeneration."""
        
        from litassist.commands.draft import draft
        from click.testing import CliRunner
        
        # Mock LLM client
        mock_client = Mock()
        mock_client.complete.return_value = ("Original draft content", {"total_tokens": 100})
        mock_factory.for_command.return_value = mock_client
        
        # Mock CoVe regeneration
        mock_cove.return_value = ("Regenerated draft content", {
            'cove': {
                'passed': False,
                'regenerated': True,
                'issues': 'Fixed citation issues'
            }
        })
        
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create test file
            with open('test.txt', 'w') as f:
                f.write("Test input")
            
            # Run draft with --cove flag
            result = runner.invoke(draft, ['test.txt', 'Draft a memo', '--cove'])
            
            # Verify CoVe was called
            mock_cove.assert_called_once()
            
            # Check that success message was shown (not warning)
            # This would be in the click.echo calls but mocked


# Test markers
pytestmark = [pytest.mark.unit, pytest.mark.cove, pytest.mark.offline]