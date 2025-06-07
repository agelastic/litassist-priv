"""
Tests for the lookup command functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from litassist.commands.lookup import lookup, format_lookup_output


class TestLookupCommand:
    """Test the lookup command functionality."""

    def test_format_lookup_output_default(self):
        """Test default formatting (fixes Gemini markdown issues)."""
        # Test content with broken markdown headers
        content = "### **Summary*\n*\nSome content here"
        result = format_lookup_output(content)
        
        # Should fix broken markdown
        assert "### **Summary**" in result
        assert "*\n*" not in result

    def test_format_lookup_output_citations(self):
        """Test citation extraction."""
        content = """
        Some legal analysis with [2021] FCA 737 and [2020] HCA 123.
        Also references Property Act 1958 (Vic) s 42.
        """
        result = format_lookup_output(content, extract="citations")
        
        assert "CITATIONS FOUND:" in result
        assert "[2021] FCA 737" in result
        assert "[2020] HCA 123" in result

    def test_format_lookup_output_principles(self):
        """Test legal principles extraction."""
        content = """
        The court must consider the best interests of the child.
        A defendant requires proof beyond reasonable doubt.
        The principle of proportionality establishes limits.
        """
        result = format_lookup_output(content, extract="principles")
        
        assert "LEGAL PRINCIPLES:" in result
        assert "must consider" in result
        assert "requires proof" in result

    def test_format_lookup_output_checklist(self):
        """Test checklist extraction."""
        content = """
        You must establish the following elements:
        1. Duty of care must be proven
        2. Evidence should include witness statements
        3. Plaintiff needs to demonstrate causation
        """
        result = format_lookup_output(content, extract="checklist")
        
        assert "PRACTICAL CHECKLIST:" in result
        assert "□" in result
        assert "must be proven" in result

    @patch("googleapiclient.discovery.build")
    @patch("litassist.llm.LLMClientFactory.for_command")
    def test_lookup_command_standard_mode(self, mock_factory, mock_build):
        """Test lookup command in standard mode."""
        # Mock the CSE service
        mock_cse_service = Mock()
        mock_build.return_value = mock_cse_service
        mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
            "items": [
                {"link": "https://jade.io/article/123"},
                {"link": "https://jade.io/article/456"},
            ]
        }
        
        # Mock the LLM client
        mock_client = Mock()
        mock_client.complete.return_value = ("Legal analysis content", {"total_tokens": 100})
        mock_factory.return_value = mock_client
        
        # Mock save functions
        with patch("litassist.commands.lookup.save_command_output") as mock_save_output, \
             patch("litassist.commands.lookup.save_log") as mock_save_log:
            
            mock_save_output.return_value = "output_file.txt"
            
            runner = CliRunner()
            result = runner.invoke(lookup, ["contract formation"])
            
            assert result.exit_code == 0
            assert "Found links:" in result.output
            assert "✅ Lookup complete!" in result.output
            assert "Standard search: 2 sources analyzed" in result.output

    @patch("googleapiclient.discovery.build")
    @patch("litassist.llm.LLMClientFactory.for_command")
    def test_lookup_command_comprehensive_mode(self, mock_factory, mock_build):
        """Test lookup command in comprehensive mode."""
        # Mock the CSE service to return multiple results for different queries
        mock_cse_service = Mock()
        mock_build.return_value = mock_cse_service
        mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
            "items": [
                {"link": "https://jade.io/article/123"},
                {"link": "https://jade.io/article/456"},
                {"link": "https://jade.io/article/789"},
            ]
        }
        
        # Mock the LLM client
        mock_client = Mock()
        mock_client.complete.return_value = ("Comprehensive analysis", {"total_tokens": 500})
        mock_factory.return_value = mock_client
        
        # Mock save functions
        with patch("litassist.commands.lookup.save_command_output") as mock_save_output, \
             patch("litassist.commands.lookup.save_log") as mock_save_log:
            
            mock_save_output.return_value = "output_file.txt"
            
            runner = CliRunner()
            result = runner.invoke(lookup, ["contract formation", "--comprehensive"])
            
            assert result.exit_code == 0
            assert "Exhaustive search:" in result.output
            # Should make multiple search queries in comprehensive mode
            assert mock_cse_service.cse.return_value.list.call_count >= 4

    @patch("googleapiclient.discovery.build") 
    @patch("litassist.llm.LLMClientFactory.for_command")
    def test_lookup_command_with_extraction(self, mock_factory, mock_build):
        """Test lookup command with extract option."""
        # Mock the CSE service
        mock_cse_service = Mock()
        mock_build.return_value = mock_cse_service
        mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
            "items": [{"link": "https://jade.io/article/123"}]
        }
        
        # Mock the LLM client
        mock_client = Mock()
        mock_client.complete.return_value = ("Content with [2021] FCA 123", {"total_tokens": 100})
        mock_factory.return_value = mock_client
        
        # Mock save functions
        with patch("litassist.commands.lookup.save_command_output") as mock_save_output, \
             patch("litassist.commands.lookup.save_log") as mock_save_log:
            
            mock_save_output.return_value = "output_file.txt"
            
            runner = CliRunner()
            result = runner.invoke(lookup, ["contract law", "--extract", "citations"])
            
            assert result.exit_code == 0
            assert "Citations extracted" in result.output

    def test_lookup_command_irac_vs_broad_mode(self):
        """Test that IRAC and broad modes use different LLM parameters."""
        with patch("googleapiclient.discovery.build") as mock_build, \
             patch("litassist.llm.LLMClientFactory.for_command") as mock_factory, \
             patch("litassist.commands.lookup.save_command_output"), \
             patch("litassist.commands.lookup.save_log"):
            
            # Mock CSE
            mock_cse_service = Mock()
            mock_build.return_value = mock_cse_service
            mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
                "items": [{"link": "https://jade.io/article/123"}]
            }
            
            # Mock LLM client
            mock_client = Mock()
            mock_client.complete.return_value = ("Analysis", {"total_tokens": 100})
            mock_factory.return_value = mock_client
            
            runner = CliRunner()
            
            # Test IRAC mode (default)
            result = runner.invoke(lookup, ["test question"])
            assert result.exit_code == 0
            
            # Should be called with low temperature for precision
            call_args = mock_factory.call_args
            assert call_args[0][0] == "lookup"
            assert call_args[1]["temperature"] == 0
            assert call_args[1]["top_p"] == 0.1
            
            # Reset mock
            mock_factory.reset_mock()
            
            # Test broad mode
            result = runner.invoke(lookup, ["test question", "--mode", "broad"])
            assert result.exit_code == 0
            
            # Should be called with higher temperature for creativity
            call_args = mock_factory.call_args
            assert call_args[1]["temperature"] == 0.5
            assert call_args[1]["top_p"] == 0.9


class TestLookupCommandIntegration:
    """Integration tests for lookup command."""
    
    def test_comprehensive_mode_parameters(self):
        """Test that comprehensive mode uses correct parameters."""
        with patch("googleapiclient.discovery.build") as mock_build, \
             patch("litassist.llm.LLMClientFactory.for_command") as mock_factory, \
             patch("litassist.commands.lookup.save_command_output"), \
             patch("litassist.commands.lookup.save_log"):
            
            # Mock CSE
            mock_cse_service = Mock()
            mock_build.return_value = mock_cse_service
            mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
                "items": [{"link": "https://jade.io/article/123"}]
            }
            
            # Mock LLM client
            mock_client = Mock()
            mock_client.complete.return_value = ("Analysis", {"total_tokens": 100})
            mock_factory.return_value = mock_client
            
            runner = CliRunner()
            
            # Test comprehensive + IRAC mode
            result = runner.invoke(lookup, ["test", "--comprehensive", "--mode", "irac"])
            assert result.exit_code == 0
            
            call_args = mock_factory.call_args
            # Should use maximum precision for comprehensive IRAC
            assert call_args[1]["temperature"] == 0
            assert call_args[1]["top_p"] == 0.05
            assert call_args[1]["max_tokens"] == 8192

    def test_no_engine_option_anymore(self):
        """Test that --engine option is no longer available."""
        runner = CliRunner()
        result = runner.invoke(lookup, ["test", "--engine", "google"])
        
        # Should fail because --engine option no longer exists
        assert result.exit_code != 0
        assert "no such option" in result.output.lower()