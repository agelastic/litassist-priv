"""
Tests for the lookup command functionality.
"""

from unittest.mock import Mock, patch
from click.testing import CliRunner

from litassist.commands.lookup import lookup


class TestLookupCommand:
    """Test the lookup command functionality."""


    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content_selenium_with_timeout", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    @patch("googleapiclient.discovery.build")
    @patch("litassist.llm.LLMClientFactory.for_command")
    def test_lookup_command_standard_mode(self, mock_factory, mock_build, mock_sleep, mock_fetch_selenium, mock_fetch):
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
        mock_client.model = "test-model"  # Add model attribute for token limit checks
        mock_client.complete.return_value = (
            "Legal analysis content",
            {"total_tokens": 100},
        )
        mock_factory.return_value = mock_client

        # Mock save functions
        with patch(
            "litassist.commands.lookup.processors.save_command_output"
        ) as mock_save_output, patch(
            "litassist.commands.lookup.save_log"
        ) as _mock_save_log:

            mock_save_output.return_value = "output_file.txt"

            runner = CliRunner()
            result = runner.invoke(lookup, ["contract formation"])

            assert result.exit_code == 0
            assert "Found links:" in result.output
            assert "[SUCCESS] Lookup complete!" in result.output
            assert "Standard search: 2 sources analyzed" in result.output

    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content_selenium_with_timeout", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    @patch("googleapiclient.discovery.build")
    @patch("litassist.llm.LLMClientFactory.for_command")
    def test_lookup_command_comprehensive_mode(self, mock_factory, mock_build, mock_sleep, mock_fetch_selenium, mock_fetch):
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
        mock_client.model = "test-model"  # Add model attribute for token limit checks
        mock_client.complete.return_value = (
            "Comprehensive analysis",
            {"total_tokens": 500},
        )
        mock_factory.return_value = mock_client

        # Mock save functions
        with patch(
            "litassist.commands.lookup.processors.save_command_output"
        ) as mock_save_output, patch(
            "litassist.commands.lookup.save_log"
        ) as _mock_save_log:

            mock_save_output.return_value = "output_file.txt"

            runner = CliRunner()
            result = runner.invoke(lookup, ["contract formation", "--comprehensive"])

            assert result.exit_code == 0
            assert "Exhaustive search:" in result.output

    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content_selenium_with_timeout", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    @patch("googleapiclient.discovery.build")
    @patch("litassist.llm.LLMClientFactory.for_command")
    def test_lookup_command_with_extraction(self, mock_factory, mock_build, mock_sleep, mock_fetch_selenium, mock_fetch):
        """Test lookup command with extract option."""
        # Mock the CSE service
        mock_cse_service = Mock()
        mock_build.return_value = mock_cse_service
        mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
            "items": [{"link": "https://jade.io/article/123"}]
        }

        # Mock the LLM client
        mock_client = Mock()
        mock_client.model = "test-model"  # Add model attribute for token limit checks
        mock_client.complete.return_value = (
            "Content with [2021] FCA 123",
            {"total_tokens": 100},
        )
        mock_factory.return_value = mock_client

        # Mock save functions
        with patch(
            "litassist.commands.lookup.processors.save_command_output"
        ) as mock_save_output, patch(
            "litassist.commands.lookup.save_log"
        ) as _mock_save_log:

            mock_save_output.return_value = "output_file.txt"
            
            # Mock the LLM to return formatted text directly
            mock_client.complete.return_value = (
                "CITATIONS FOUND:\n• [2021] FCA 123",
                {"total_tokens": 100}
            )

            runner = CliRunner()
            result = runner.invoke(lookup, ["contract law", "--extract", "citations"])

            assert result.exit_code == 0
            assert "Citations extracted" in result.output
            
            # Verify save_command_output was called with formatted text
            mock_save_output.assert_called_once()

    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content_selenium_with_timeout", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    def test_lookup_command_irac_vs_broad_mode(self, mock_sleep, mock_fetch_selenium, mock_fetch):
        """Test that IRAC and broad modes use different LLM parameters."""
        with patch("googleapiclient.discovery.build") as mock_build, patch(
            "litassist.llm.LLMClientFactory.for_command"
        ) as mock_factory, patch(
            "litassist.commands.lookup.processors.save_command_output"
        ), patch(
            "litassist.commands.lookup.save_log"
        ):

            # Mock CSE
            mock_cse_service = Mock()
            mock_build.return_value = mock_cse_service
            mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
                "items": [{"link": "https://jade.io/article/123"}]
            }

            # Mock LLM client
            mock_client = Mock()
            mock_client.model = "test-model"  # Add model attribute for token limit checks
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

    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content_selenium_with_timeout", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    def test_comprehensive_mode_parameters(self, mock_sleep, mock_fetch_selenium, mock_fetch):
        """Test that comprehensive mode uses correct parameters."""
        with patch("googleapiclient.discovery.build") as mock_build, patch(
            "litassist.llm.LLMClientFactory.for_command"
        ) as mock_factory, patch(
            "litassist.commands.lookup.processors.save_command_output"
        ), patch(
            "litassist.commands.lookup.save_log"
        ):

            # Mock CSE
            mock_cse_service = Mock()
            mock_build.return_value = mock_cse_service
            mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
                "items": [{"link": "https://jade.io/article/123"}]
            }

            # Mock LLM client
            mock_client = Mock()
            mock_client.model = "test-model"  # Add model attribute for token limit checks
            mock_client.complete.return_value = ("Analysis", {"total_tokens": 100})
            mock_factory.return_value = mock_client

            runner = CliRunner()

            # Test comprehensive + IRAC mode
            result = runner.invoke(
                lookup, ["test", "--comprehensive", "--mode", "irac"]
            )
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
