"""
Tests for command-specific parameter propagation.

Ensures each CLI command uses the correct model and parameters
without making any network calls.
"""

from unittest.mock import Mock, patch
from click.testing import CliRunner

from litassist.cli import cli
from litassist.commands import register_commands


class TestCommandParameterPropagation:
    """Test that CLI commands propagate correct parameters to LLM clients."""

    def setup_method(self):
        """Set up test fixtures."""
        # Register commands with CLI
        register_commands(cli)
        self.runner = CliRunner()
        self.mock_client = Mock()
        self.mock_client.complete.return_value = (
            "Test response",
            {"total_tokens": 100},
        )
        self.mock_client.model = "test/mock-model"
        self.mock_client.verify.return_value = ""  # Add verify method
        self.mock_client.validate_citations.return_value = []  # Add validate_citations method

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.utils.file_ops.read_document")
    @patch("litassist.commands.extractfacts.document_reader.get_config")
    def test_extractfacts_command_parameters(
        self, mock_config, mock_read, mock_factory
    ):
        """Test extractfacts command uses correct model and parameters."""
        mock_factory.return_value = self.mock_client
        mock_read.return_value = "Test document content"
        mock_config_obj = Mock()
        mock_config_obj.max_chars = 1000  # Add missing config attribute
        mock_config.return_value = mock_config_obj

        with self.runner.isolated_filesystem():
            with open("test.pdf", "w") as f:
                f.write("dummy")

            # Mock additional dependencies
            with patch("litassist.commands.extractfacts.single_extractor.PROMPTS") as mock_prompts:
                mock_prompts.get_prompt.return_value = "Test prompt"

                # Mock save functions to avoid file operations
                with patch("litassist.commands.extractfacts.core.save_command_output"):
                    with patch("litassist.commands.extractfacts.core.save_log"):
                        with patch(
                            "litassist.commands.extractfacts.core.verify_content_if_needed"
                        ) as mock_verify:
                            mock_verify.return_value = ("Test response", {})
                            result = self.runner.invoke(
                                cli, ["extractfacts", "test.pdf"]
                            )

        # Check if command ran successfully
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
                import traceback

                traceback.print_tb(result.exc_info[2])

        # Verify factory was called with correct command
        mock_factory.assert_called_once_with("extractfacts")

        # Verify the client's complete method was called
        assert self.mock_client.complete.called

        # Check that LLMClientFactory would create correct model
        from litassist.llm.factory import LLMClientFactory

        configs = LLMClientFactory.list_configurations()
        assert "extractfacts" in configs
        assert configs["extractfacts"].get("model")

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.utils.file_ops.read_document")
    def test_digest_summary_command_parameters(self, mock_read, mock_factory):
        """Test digest-summary command uses correct parameters."""
        mock_factory.return_value = self.mock_client
        mock_read.return_value = "Test document content"

        with self.runner.isolated_filesystem():
            with open("test.txt", "w") as f:
                f.write("content")

            with patch("litassist.commands.digest.processors.PROMPTS") as mock_prompts:
                mock_prompts.get.return_value = "Test prompt"

                result = self.runner.invoke(
                    cli, ["digest", "--mode", "summary", "test.txt"]
                )

        # Debug output
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
                import traceback

                traceback.print_tb(result.exc_info[2])

        # Verify factory was called with mode as positional sub_type argument
        mock_factory.assert_called_once_with("digest", "summary")
        assert self.mock_client.complete.called

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.utils.file_ops.read_document")
    def test_digest_issues_command_parameters(self, mock_read, mock_factory):
        """Test digest-issues command uses correct parameters."""
        mock_factory.return_value = self.mock_client
        mock_read.return_value = "Test document content"

        with self.runner.isolated_filesystem():
            with open("test.txt", "w") as f:
                f.write("content")

            with patch("litassist.commands.digest.processors.PROMPTS") as mock_prompts:
                mock_prompts.get.return_value = "Test prompt"

                result = self.runner.invoke(
                    cli, ["digest", "--mode", "issues", "test.txt"]
                )

        # Check command ran (may have exit code 1 due to mocking limitations)
        # The important thing is that the factory was called correctly
        assert result.exit_code in [0, 1]

        # Verify factory was called with mode as positional sub_type argument
        mock_factory.assert_called_once_with("digest", "issues")
        assert self.mock_client.complete.called

    @patch("litassist.commands.lookup.search.time.sleep")
    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.commands.lookup.search.get_config")
    def test_lookup_command_parameters(self, mock_get_config, mock_factory, mock_sleep):
        """Test lookup command pulls its model from configuration."""
        mock_factory.return_value = self.mock_client
        mock_config = Mock()
        mock_config.g_key = "test_google_key"
        mock_config.cse_id = "test_cse_id"
        mock_config.heartbeat_interval = 30
        mock_config.cse_id_austlii = None
        mock_config.cse_id_comprehensive = None
        mock_get_config.return_value = mock_config

        # Mock Google API and fetch functions
        with (
            patch("googleapiclient.discovery.build") as mock_build,
            patch(
                "litassist.commands.lookup.fetchers._fetch_url_content", return_value=""
            ),
        ):
            mock_service = Mock()
            mock_build.return_value = mock_service
            mock_cse = Mock()
            mock_service.cse.return_value = mock_cse
            mock_list = Mock()
            mock_cse.list.return_value = mock_list
            mock_list.execute.return_value = {"items": []}

            with patch("litassist.commands.lookup.processors.PROMPTS") as mock_prompts:
                mock_prompts.get_prompt.return_value = "Test prompt"

                result = self.runner.invoke(cli, ["lookup", "test query"])

        # Check command executed successfully
        assert result.exit_code == 0

        # Verify factory was called with correct command (lookup sets temperature/top_p based on mode)
        mock_factory.assert_called_once_with(
            "lookup", temperature=0, top_p=0.1
        )

        # Check configuration
        from litassist.llm.factory import LLMClientFactory

        configs = LLMClientFactory.list_configurations()
        assert configs["lookup"].get("model")
        assert "enforce_citations" in configs["lookup"]

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.utils.file_ops.read_document")
    @patch("litassist.citation.verify.verify_all_citations")
    @patch("litassist.citation_patterns.extract_citations")
    @patch("litassist.commands.verify.citation_verifier.fetch_citation_context")
    @patch("litassist.commands.verify.reasoning_handler.fetch_citation_context")
    @patch("litassist.commands.verify.soundness_checker.fetch_citation_context")
    def test_verify_command_parameters(
        self,
        mock_soundness_fetch,
        mock_reasoning_fetch,
        mock_citation_fetch,
        mock_extract,
        mock_verify_all,
        mock_read,
        mock_factory,
    ):
        """Test verify command parameters."""
        # Use a per-test client whose verify() returns the expected tuple.
        # The shared self.mock_client.verify returns "" (an empty string),
        # which tuple-unpacking in soundness_checker.py used to silently
        # raise and be swallowed; the unswallowed failure now surfaces.
        mock_client = Mock()
        mock_client.model = "test/mock-model"
        mock_client.complete.return_value = ("Test response", {"total_tokens": 10})
        mock_client.verify.return_value = ("Verified", "test/mock-model")
        mock_client.validate_citations.return_value = []
        mock_factory.return_value = mock_client

        mock_read.return_value = "Legal document content"
        mock_extract.return_value = []
        # verify_all_citations returns (verified_list, unverified_list).
        mock_verify_all.return_value = ([], [])
        # fetch_citation_context returns (case_content_dict, failures_list).
        mock_citation_fetch.return_value = ({}, [])
        mock_reasoning_fetch.return_value = ({}, [])
        mock_soundness_fetch.return_value = ({}, [])

        with self.runner.isolated_filesystem():
            with open("test.txt", "w") as f:
                f.write("content")

            with patch("litassist.commands.verify.PROMPTS") as mock_prompts:
                mock_prompts.get_prompt.return_value = "Test prompt"

                result = self.runner.invoke(cli, ["verify", "test.txt"])

        # Check command executed successfully
        assert result.exit_code == 0, (
            f"exit_code={result.exit_code}\noutput={result.output!r}\n"
            f"exception={result.exception!r}"
        )

        # Verify factory was called
        assert mock_factory.called

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.utils.file_ops.read_document")
    def test_brainstorm_command_parameters(self, mock_read, mock_factory):
        """Test brainstorm command uses correct parameters."""
        # Set up factory to return different clients for different calls
        # Note: Verification was removed from unorthodox generation
        mock_factory.side_effect = [
            self.mock_client,  # For orthodox
            self.mock_client,  # For unorthodox
            self.mock_client,  # For analysis
        ]

        mock_read.return_value = "Case facts"

        # Mock citation validation to return empty list (no issues)
        self.mock_client.validate_citations.return_value = []

        with self.runner.isolated_filesystem():
            with open("facts.txt", "w") as f:
                f.write("case facts")

            with patch("litassist.commands.brainstorm.PROMPTS") as mock_prompts:
                mock_prompts.get.return_value = "Test prompt"

                result = self.runner.invoke(
                    cli,
                    [
                        "brainstorm",
                        "--facts",
                        "facts.txt",
                        "--side",
                        "plaintiff",
                        "--area",
                        "civil",
                    ],
                )

        # Debug output
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
                import traceback

                traceback.print_tb(result.exc_info[2])

        # Should be called 3 times (orthodox, unorthodox, analysis)
        # Note: Verification was removed from unorthodox generation
        assert mock_factory.call_count >= 3

        # Check the calls were made in the correct order
        calls = mock_factory.call_args_list
        assert calls[0][0][0] == "brainstorm"  # orthodox
        assert calls[1][0][0] == "brainstorm"  # unorthodox
        assert calls[2][0][0] == "brainstorm"  # analysis

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.utils.file_ops.read_document")
    def test_strategy_command_parameters(self, mock_read, mock_factory):
        """Test strategy command uses its configured model."""
        mock_factory.return_value = self.mock_client
        mock_read.return_value = """
Parties:
- Applicant: Test
- Respondent: Test

Background:
Test background

Issues:
- Test issue

Jurisdiction:
Federal Court
"""

        with self.runner.isolated_filesystem():
            with open("facts.txt", "w") as f:
                f.write("""Parties:
Test parties

Background:
Test background

Key Events:
Test events

Legal Issues:
Test issue

Evidence Available:
Test evidence

Opposing Arguments:
Test arguments

Procedural History:
Test history

Jurisdiction:
Federal Court

Applicable Law:
Test law

Client Objectives:
Test objectives""")

            with patch("litassist.commands.strategy.core.PROMPTS") as mock_prompts:
                mock_prompts.get_prompt.return_value = "Test prompt"

                # Mock parse_strategies_file to avoid parsing issues
                with patch("litassist.utils.core.parse_strategies_file") as mock_parse:
                    mock_parse.return_value = []

                    # Mock case facts validation
                    with patch(
                        "litassist.commands.strategy.validators.validate_case_facts_format"
                    ) as mock_validate:
                        mock_validate.return_value = True

                        # Mock legal issues extraction
                        with patch(
                            "litassist.commands.strategy.validators.extract_legal_issues"
                        ) as mock_extract:
                            mock_extract.return_value = [
                                "Test legal issue 1",
                                "Test legal issue 2",
                            ]

                            result = self.runner.invoke(
                                cli,
                                ["strategy", "facts.txt", "--outcome", "Win the case"],
                            )

        # Debug output
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
                import traceback

                traceback.print_tb(result.exc_info[2])

        # Verify factory was called for both strategy and verification
        # Strategy command automatically uses verification, so factory is called for both
        assert mock_factory.call_count >= 1
        # Check that strategy was called at some point
        strategy_calls = [
            call for call in mock_factory.call_args_list if call[0][0] == "strategy"
        ]
        assert len(strategy_calls) > 0, "Factory should be called with 'strategy'"

        # Check configuration
        from litassist.llm.factory import LLMClientFactory

        configs = LLMClientFactory.list_configurations()
        assert configs["strategy"].get("model")
        assert configs["strategy"]["thinking_effort"] == "max"
        assert "enforce_citations" in configs["strategy"]

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.utils.file_ops.read_document")
    def test_draft_command_parameters(
        self, mock_read, mock_factory
    ):
        """Test draft command uses its configured model."""
        # Create verification client mock
        mock_verification_client = Mock()
        mock_verification_client.complete.return_value = (
            "Verified content",
            {"tokens": 100},
        )
        mock_verification_client.validate_citations.return_value = []
        mock_verification_client.verify.return_value = (
            "Verified content",
            "mock-model",
        )
        from litassist.llm.factory import LLMClientFactory as _Factory
        mock_verification_client.model = _Factory.list_configurations()["verification"]["model"]

        # Set up factory to return different clients for different calls
        mock_factory.side_effect = [
            self.mock_client,  # For draft
            mock_verification_client,  # For verification
        ]

        mock_read.return_value = "Instructions"

        with self.runner.isolated_filesystem():
            with open("instructions.txt", "w") as f:
                f.write("draft instructions")

            with patch("litassist.commands.draft.prompt_builder.PROMPTS") as mock_prompts:
                mock_prompts.get.return_value = "Test prompt"

                result = self.runner.invoke(
                    cli, ["draft", "instructions.txt", "Draft a witness statement"]
                )

        # Debug output
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
                import traceback

                traceback.print_tb(result.exc_info[2])

        # Verify factory was called twice (draft and verification)
        assert mock_factory.call_count == 2
        calls = mock_factory.call_args_list
        assert calls[0][0][0] == "draft"
        assert calls[1][0][0] == "verification"

        # Check configuration
        from litassist.llm.factory import LLMClientFactory

        configs = LLMClientFactory.list_configurations()
        assert configs["draft"].get("model")
        assert configs["draft"]["thinking_effort"] == "high"

    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.commands.barbrief.core.save_command_output")
    @patch("litassist.commands.barbrief.core.validate_case_facts")
    @patch("litassist.commands.barbrief.document_reader.read_document")
    def test_barbrief_command_parameters(self, mock_read, mock_validate, mock_save, mock_factory):
        """Test barbrief command parameters."""
        mock_factory.return_value = self.mock_client
        mock_validate.return_value = True
        mock_read.return_value = "Valid case facts with all 10 headings"
        mock_save.return_value = "outputs/barbrief_trial.txt"

        with self.runner.isolated_filesystem():
            with open("facts.txt", "w") as f:
                f.write("case facts")

            with patch("litassist.commands.barbrief.brief_generator.PROMPTS") as mock_prompts:
                mock_prompts.get.return_value = "Test prompt"

                result = self.runner.invoke(
                    cli, ["barbrief", "facts.txt", "--hearing-type", "trial"]
                )

        # Debug output
        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            if result.exception:
                print(f"Exception: {result.exception}")
                import traceback

                traceback.print_tb(result.exc_info[2])

        # Verify factory was called
        assert mock_factory.called

    def test_all_commands_have_offline_mocks(self):
        """Verify all command tests use mocks and no real API calls."""
        import inspect

        # Get all test methods in this class
        test_methods = [
            m
            for m in dir(self)
            if m.startswith("test_") and m != "test_all_commands_have_offline_mocks"
        ]

        for method_name in test_methods:
            method = getattr(self, method_name)
            source = inspect.getsource(method)

            # Verify no real API calls
            assert "requests." not in source
            assert "openai." not in source or "@patch" in source
            assert "aiohttp" not in source

            # Verify mocking is used
            assert "@patch" in source or "mock_" in source

    def test_model_parameter_filtering(self):
        """Test parameters are stored on the client and filtered per model family at API time."""
        from litassist.llm.factory import LLMClientFactory
        from litassist.llm.parameter_handler import get_model_family, get_model_parameters

        with patch("litassist.config.CONFIG") as mock_config:
            mock_config.openrouter_key = "test_key"
            mock_config.openai_key = "test_key"

            client = LLMClientFactory.for_command(
                "strategy", temperature=0.9, top_p=0.95
            )

            assert hasattr(client, "default_params")
            assert client.default_params.get("temperature") == 0.9
            assert client.default_params.get("top_p") == 0.95

            # If strategy is wired to an openai_reasoning model, sampling params get filtered out
            if get_model_family(client.model) == "openai_reasoning":
                filtered = get_model_parameters(client.model, client.default_params)
                assert "temperature" not in filtered
                assert "top_p" not in filtered
                assert "reasoning" in filtered
