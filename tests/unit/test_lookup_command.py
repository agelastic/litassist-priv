"""
Tests for the lookup command functionality.
"""

from unittest.mock import Mock, patch
from click.testing import CliRunner


class TestLookupCommand:
    """Test the lookup command functionality."""

    @patch("litassist.commands.lookup.get_config")
    @patch("litassist.commands.lookup.search.get_config")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    @patch("googleapiclient.discovery.build")
    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    def test_lookup_command_standard_mode(
        self,
        mock_factory,
        mock_build,
        mock_sleep,
        mock_fetch,
        mock_search_get_config,
        mock_init_get_config,
    ):
        """Test lookup command in standard mode."""
        from litassist.commands.lookup import lookup

        # Mock config with all required attributes
        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_austlii = None
        mock_config.cse_id_comprehensive = None
        mock_config.max_fetch_time = 60
        mock_config.fetch_timeout = 10
        mock_search_get_config.return_value = mock_config
        mock_init_get_config.return_value = mock_config

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
        with (
            patch(
                "litassist.commands.lookup.processors.save_command_output"
            ) as mock_save_output,
            patch("litassist.commands.lookup.save_log") as _mock_save_log,
        ):
            mock_save_output.return_value = "output_file.txt"

            runner = CliRunner()
            result = runner.invoke(lookup, ["contract formation"])

            assert result.exit_code == 0
            assert "Found links:" in result.output
            assert "[SUCCESS] Lookup complete!" in result.output
            assert "Standard search: 2 sources analyzed" in result.output

    @patch("litassist.commands.lookup.get_config")
    @patch("litassist.commands.lookup.search.get_config")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    @patch("googleapiclient.discovery.build")
    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    def test_lookup_command_comprehensive_mode(
        self,
        mock_factory,
        mock_build,
        mock_sleep,
        mock_fetch,
        mock_search_get_config,
        mock_init_get_config,
    ):
        """Test lookup command in comprehensive mode."""
        from litassist.commands.lookup import lookup

        # Mock config with all required attributes
        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_austlii = None
        mock_config.cse_id_comprehensive = None
        mock_config.max_fetch_time = 60
        mock_config.fetch_timeout = 10
        mock_search_get_config.return_value = mock_config
        mock_init_get_config.return_value = mock_config

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
        with (
            patch(
                "litassist.commands.lookup.processors.save_command_output"
            ) as mock_save_output,
            patch("litassist.commands.lookup.save_log") as _mock_save_log,
        ):
            mock_save_output.return_value = "output_file.txt"

            runner = CliRunner()
            result = runner.invoke(lookup, ["contract formation", "--comprehensive"])

            assert result.exit_code == 0
            assert "Exhaustive search:" in result.output

    @patch("litassist.commands.lookup.get_config")
    @patch("litassist.commands.lookup.search.get_config")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    @patch("googleapiclient.discovery.build")
    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    def test_lookup_command_with_extraction(
        self,
        mock_factory,
        mock_build,
        mock_sleep,
        mock_fetch,
        mock_search_get_config,
        mock_init_get_config,
    ):
        """Test lookup command with extract option."""
        from litassist.commands.lookup import lookup

        # Mock config with all required attributes
        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_austlii = None
        mock_config.cse_id_comprehensive = None
        mock_config.max_fetch_time = 60
        mock_config.fetch_timeout = 10
        mock_search_get_config.return_value = mock_config
        mock_init_get_config.return_value = mock_config

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
        with (
            patch(
                "litassist.commands.lookup.processors.save_command_output"
            ) as mock_save_output,
            patch("litassist.commands.lookup.save_log") as _mock_save_log,
        ):
            mock_save_output.return_value = "output_file.txt"

            # Mock the LLM to return formatted text directly
            mock_client.complete.return_value = (
                "CITATIONS FOUND:\n• [2021] FCA 123",
                {"total_tokens": 100},
            )

            runner = CliRunner()
            result = runner.invoke(lookup, ["contract law", "--extract", "citations"])

            assert result.exit_code == 0
            assert "Citations extracted" in result.output

            # Verify save_command_output was called with formatted text
            mock_save_output.assert_called_once()

    @patch("litassist.commands.lookup.get_config")
    @patch("litassist.commands.lookup.search.get_config")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    def test_lookup_command_irac_vs_broad_mode(
        self,
        mock_sleep,
        mock_fetch,
        mock_search_get_config,
        mock_init_get_config,
    ):
        """Test that IRAC and broad modes use different LLM parameters."""
        from litassist.commands.lookup import lookup

        # Mock config with all required attributes
        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_austlii = None
        mock_config.cse_id_comprehensive = None
        mock_config.max_fetch_time = 60
        mock_config.fetch_timeout = 10
        mock_search_get_config.return_value = mock_config
        mock_init_get_config.return_value = mock_config

        with (
            patch("googleapiclient.discovery.build") as mock_build,
            patch("litassist.llm.factory.LLMClientFactory.for_command") as mock_factory,
            patch("litassist.commands.lookup.processors.save_command_output"),
            patch("litassist.commands.lookup.save_log"),
        ):
            # Mock CSE
            mock_cse_service = Mock()
            mock_build.return_value = mock_cse_service
            mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
                "items": [{"link": "https://jade.io/article/123"}]
            }

            # Mock LLM client
            mock_client = Mock()
            mock_client.model = (
                "test-model"  # Add model attribute for token limit checks
            )
            mock_client.complete.return_value = ("Analysis", {"total_tokens": 100})
            mock_factory.return_value = mock_client

            runner = CliRunner()

            # Test IRAC mode (default).
            # processors.get_llm_client routes the mode to the YAML sub-type;
            # `lookup-irac` carries temperature=0, top_p=0.1.
            result = runner.invoke(lookup, ["test question"])
            assert result.exit_code == 0

            call_args = mock_factory.call_args
            assert call_args[0] == ("lookup", "irac")

            # Reset mock
            mock_factory.reset_mock()

            # Test broad mode -- routes to `lookup-broad`
            # (temperature=0.4, top_p=0.8 per model_configs.yaml).
            result = runner.invoke(lookup, ["test question", "--mode", "broad"])
            assert result.exit_code == 0

            call_args = mock_factory.call_args
            assert call_args[0] == ("lookup", "broad")

    @patch("litassist.commands.lookup.get_config")
    @patch("litassist.commands.lookup.search.get_config")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    def test_unsupported_verify_noverify_flags_warn(
        self,
        mock_sleep,
        mock_fetch,
        mock_search_get_config,
        mock_init_get_config,
    ):
        """lookup has no internal verification: --verify/--noverify must warn (not
        error) while the command still completes. Real invocation - replaces two
        earlier tests that only checked the warning_message helper round-trip
        without ever running lookup."""
        from litassist.commands.lookup import lookup

        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_austlii = None
        mock_config.cse_id_comprehensive = None
        mock_config.max_fetch_time = 60
        mock_config.fetch_timeout = 10
        mock_search_get_config.return_value = mock_config
        mock_init_get_config.return_value = mock_config

        with (
            patch("googleapiclient.discovery.build") as mock_build,
            patch("litassist.llm.factory.LLMClientFactory.for_command") as mock_factory,
            patch("litassist.commands.lookup.processors.save_command_output"),
            patch("litassist.commands.lookup.save_log"),
        ):
            mock_cse_service = Mock()
            mock_build.return_value = mock_cse_service
            mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
                "items": [{"link": "https://jade.io/article/123"}]
            }
            mock_client = Mock()
            mock_client.model = "test-model"
            mock_client.complete.return_value = ("Analysis", {"total_tokens": 100})
            mock_factory.return_value = mock_client

            runner = CliRunner()

            result = runner.invoke(lookup, ["test question", "--verify"])
            assert result.exit_code == 0, result.output
            assert "--verify not supported" in result.output

            result = runner.invoke(lookup, ["test question", "--noverify"])
            assert result.exit_code == 0, result.output
            assert "--noverify not supported" in result.output


class TestLookupCommandIntegration:
    """Integration tests for lookup command."""

    @patch("litassist.commands.lookup.get_config")
    @patch("litassist.commands.lookup.search.get_config")
    @patch("litassist.commands.lookup.fetchers._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    def test_comprehensive_mode_parameters(
        self,
        mock_sleep,
        mock_fetch,
        mock_search_get_config,
        mock_init_get_config,
    ):
        """Test that comprehensive mode uses correct parameters."""
        from litassist.commands.lookup import lookup

        # Mock config with all required attributes
        mock_config = Mock()
        mock_config.g_key = "test_key"
        mock_config.cse_id = "test_cse"
        mock_config.cse_id_austlii = None
        mock_config.cse_id_comprehensive = None
        mock_config.max_fetch_time = 60
        mock_config.fetch_timeout = 10
        mock_search_get_config.return_value = mock_config
        mock_init_get_config.return_value = mock_config

        with (
            patch("googleapiclient.discovery.build") as mock_build,
            patch("litassist.llm.factory.LLMClientFactory.for_command") as mock_factory,
            patch("litassist.commands.lookup.processors.save_command_output"),
            patch("litassist.commands.lookup.save_log"),
        ):
            # Mock CSE
            mock_cse_service = Mock()
            mock_build.return_value = mock_cse_service
            mock_cse_service.cse.return_value.list.return_value.execute.return_value = {
                "items": [{"link": "https://jade.io/article/123"}]
            }

            # Mock LLM client
            mock_client = Mock()
            mock_client.model = (
                "test-model"  # Add model attribute for token limit checks
            )
            mock_client.complete.return_value = ("Analysis", {"total_tokens": 100})
            mock_factory.return_value = mock_client

            runner = CliRunner()

            # Test --comprehensive + --mode irac.
            # The `--comprehensive` flag controls CSE search depth (in
            # litassist/commands/lookup/search.py), not LLM parameters. The
            # mode still routes to the YAML sub-type `lookup-irac`.
            result = runner.invoke(
                lookup, ["test", "--comprehensive", "--mode", "irac"]
            )
            assert result.exit_code == 0

            call_args = mock_factory.call_args
            assert call_args[0] == ("lookup", "irac")

    def test_no_engine_option_anymore(self):
        """Test that --engine option is no longer available."""
        from litassist.commands.lookup import lookup

        runner = CliRunner()
        result = runner.invoke(lookup, ["test", "--engine", "google"])

        # Should fail because --engine option no longer exists
        assert result.exit_code != 0
        assert "no such option" in result.output.lower()
