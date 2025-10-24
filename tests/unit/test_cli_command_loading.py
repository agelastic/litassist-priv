"""
Test CLI command loading and initialization with real config.

These tests use config.yaml.template to ensure commands can load properly
without making external API calls. This would have caught the CONFIG bug.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from click.testing import CliRunner


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def test_config_file():
    """
    Create a temporary config.yaml from template for testing.
    This ensures tests work both locally and in GitHub CI.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        template_path = Path(__file__).parent.parent.parent / "config.yaml.template"

        if template_path.exists():
            # Use the actual template file
            template_content = template_path.read_text()
            f.write(template_content)
        else:
            # Fallback for CI if template is missing
            f.write(
                """
openrouter:
  api_key: "TEST_OPENROUTER_KEY"
  api_base: "https://openrouter.ai/api/v1"
openai:
  api_key: "TEST_OPENAI_KEY"  
  embedding_model: "text-embedding-3-small"
google_cse:
  api_key: "TEST_GOOGLE_KEY"
  cse_id: "TEST_CSE_ID"
pinecone:
  api_key: "TEST_PINECONE_KEY"
  environment: "TEST_ENV"
  index_name: "test-index"
llm:
  use_token_limits: true
general:
  heartbeat_interval: 10
  max_chars: 200000
  rag_max_chars: 8000
  log_format: "json"
citation_validation:
  offline_validation: false
web_scraping:
  fetch_timeout: 10
  max_fetch_time: 300
  selenium_enabled: true
  selenium_timeout_multiplier: 2
"""
            )
        config_path = Path(f.name)

    # Save the original mocked config module from conftest.py
    import sys

    original_config_module = sys.modules.get("litassist.config")

    # Clear any mocked config module from conftest.py
    if "litassist.config" in sys.modules:
        del sys.modules["litassist.config"]

    # Now import the real config module
    import litassist.config

    # Patch config finding to use our test file
    with patch.object(
        litassist.config.Config, "_find_config_file", return_value=str(config_path)
    ):
        # Clear any cached config instance
        if hasattr(litassist.config, "_config_instance"):
            litassist.config._config_instance = None

        yield config_path

    # Cleanup - delete temp file and restore original mock
    config_path.unlink(missing_ok=True)

    # CRITICAL: Restore the original mocked module for other tests
    if original_config_module:
        sys.modules["litassist.config"] = original_config_module


@pytest.fixture
def mock_external_apis():
    """Mock all external API calls but NOT config or file I/O."""
    with patch("googleapiclient.discovery.build") as mock_google, patch(
        "openai.OpenAI"
    ) as mock_openai, patch("requests.get") as mock_requests, patch(
        "requests.post"
    ) as mock_requests_post, patch(
        "pinecone.init"
    ) as mock_pinecone_init, patch(
        "pinecone.Index"
    ) as mock_pinecone_index, patch(
        "litassist.llm.factory.LLMClientFactory.for_command"
    ) as mock_llm_factory:

        # Setup mock LLM client
        mock_client = Mock()
        mock_client.complete.return_value = ("Test response", {"total_tokens": 100})
        mock_client.verify.return_value = ("No issues", "test-model")
        mock_client.model = "test-model"
        mock_llm_factory.return_value = mock_client

        # Setup mock OpenAI
        mock_openai_instance = Mock()
        mock_openai_instance.models.list.return_value = Mock(data=[])
        mock_openai_instance.embeddings.create.return_value = Mock(
            data=[Mock(embedding=[0.1] * 1536)]
        )
        mock_openai.return_value = mock_openai_instance

        # Setup mock requests
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_response.text = ""
        mock_requests.return_value = mock_response
        mock_requests_post.return_value = mock_response

        yield {
            "google": mock_google,
            "openai": mock_openai,
            "requests": mock_requests,
            "requests_post": mock_requests_post,
            "pinecone_init": mock_pinecone_init,
            "pinecone_index": mock_pinecone_index,
            "llm_factory": mock_llm_factory,
            "llm_client": mock_client,
        }


# ============================================================================
# TEST: IMPORTS AND CONFIG LOADING
# ============================================================================


def test_all_commands_import_with_real_config(test_config_file):
    """
    Test that all command modules import successfully with real config.
    This WOULD HAVE CAUGHT the CONFIG AttributeError bug immediately.
    """
    # Import all commands - this triggers real config loading
    from litassist.commands import (  # noqa: F401
        lookup,
        digest,
        brainstorm,
        extractfacts,
        draft,
        strategy,
        verify,
        counselnotes,
        barbrief,
        caseplan,
    )
    from litassist.config import get_config

    # Verify config actually loaded and has required attributes
    config = get_config()
    assert config is not None, "Config should not be None"
    assert hasattr(config, "max_chars"), "Config missing max_chars attribute"
    assert hasattr(config, "or_key"), "Config missing or_key attribute"
    assert hasattr(config, "log_format"), "Config missing log_format attribute"
    assert hasattr(config, "oa_key"), "Config missing oa_key attribute"

    # Verify values from template
    assert config.max_chars == 200000, "max_chars should be 200000 from template"
    assert config.log_format == "json", "log_format should be json from template"

    # Verify placeholder detection works
    placeholders = config.using_placeholders()
    assert isinstance(placeholders, dict), "using_placeholders should return dict"


def test_config_singleton_pattern(test_config_file):
    """Test that get_config() returns the same instance (singleton)."""
    from litassist.config import get_config

    config1 = get_config()
    config2 = get_config()
    config3 = get_config()

    assert config1 is config2, "get_config should return same instance"
    assert config2 is config3, "get_config should be consistent"
    assert id(config1) == id(config3), "All configs should be same object"


def test_command_registration(test_config_file, mock_external_apis):
    """Test all commands are properly registered with the CLI."""
    from litassist.cli import cli
    from litassist.commands import register_commands

    # Clear and re-register
    cli.commands = {}
    register_commands(cli)

    expected_commands = {
        "barbrief",
        "brainstorm",
        "caseplan",
        "counselnotes",
        "digest",
        "draft",
        "extractfacts",
        "lookup",
        "strategy",
        "verify",
        "verify-cove",
    }  # 'test' is added directly in cli.py, not via register_commands

    actual_commands = set(cli.commands.keys())

    assert (
        expected_commands == actual_commands
    ), f"Missing commands: {expected_commands - actual_commands}"


# ============================================================================
# TEST: HELP MESSAGES
# ============================================================================


def test_main_cli_help(test_config_file, mock_external_apis):
    """Test main CLI --help works with real config."""
    from litassist.cli import cli
    from litassist.commands import register_commands

    register_commands(cli)
    runner = CliRunner()

    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0, f"Main help failed: {result.output}"
    assert "LitAssist" in result.output
    assert "Commands:" in result.output


def test_all_commands_show_help(test_config_file, mock_external_apis):
    """Test --help works for ALL commands with real config loading."""
    from litassist.cli import cli
    from litassist.commands import register_commands

    register_commands(cli)
    runner = CliRunner()

    all_commands = [
        "barbrief",
        "brainstorm",
        "caseplan",
        "counselnotes",
        "digest",
        "draft",
        "extractfacts",
        "lookup",
        "strategy",
        "verify",
        "verify-cove",  # 'test' is in cli.py directly
    ]

    for cmd in all_commands:
        result = runner.invoke(cli, [cmd, "--help"])

        assert result.exit_code == 0, f"{cmd} --help failed: {result.output}"
        assert cmd in result.output.lower(), f"{cmd} not in help output"
        assert (
            "Options:" in result.output or "Usage:" in result.output
        ), f"{cmd} missing Options/Usage section"

        # Ensure no errors
        assert "AttributeError" not in result.output
        assert "NoneType" not in result.output
        assert "ConfigError" not in result.output


# ============================================================================
# TEST: FILE-BASED COMMANDS
# ============================================================================


@patch("litassist.utils.text_processing.create_embeddings")
@patch("litassist.helpers.retriever.get_pinecone_client")
def test_file_processing_commands(
    mock_pinecone, mock_embeddings, test_config_file, mock_external_apis, tmp_path
):
    """
    Test commands that process files: extractfacts, digest, counselnotes.
    Uses real files and real config loading.
    """
    # Setup mocks
    mock_embeddings.return_value = [Mock(embedding=[0.1] * 1536)]
    mock_pinecone.return_value = Mock()

    from litassist.cli import cli
    from litassist.commands import register_commands

    register_commands(cli)
    runner = CliRunner()

    # Create test document
    test_doc = tmp_path / "test_document.txt"
    test_doc.write_text(
        """
    This is a test legal document.
    It contains multiple paragraphs.
    
    The purpose is to test file processing.
    """
    )

    # Test extractfacts
    result = runner.invoke(cli, ["extractfacts", str(test_doc), "--noverify"])
    assert result.exit_code in [
        0,
        1,
    ], f"extractfacts failed unexpectedly: {result.output}"
    assert "AttributeError" not in result.output
    assert "'NoneType' object has no attribute" not in result.output

    # Test digest
    result = runner.invoke(cli, ["digest", str(test_doc), "--mode", "summary"])
    assert result.exit_code in [0, 1], f"digest failed unexpectedly: {result.output}"
    assert "AttributeError" not in result.output

    # Test counselnotes
    result = runner.invoke(cli, ["counselnotes", str(test_doc)])
    assert result.exit_code in [
        0,
        1,
    ], f"counselnotes failed unexpectedly: {result.output}"
    assert "AttributeError" not in result.output


def test_barbrief_with_case_facts(test_config_file, mock_external_apis, tmp_path):
    """Test barbrief command with case_facts.txt file."""
    from litassist.cli import cli
    from litassist.commands import register_commands

    register_commands(cli)
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create case_facts.txt in working directory
        Path("case_facts.txt").write_text(
            """
Parties:
- Applicant: John Smith
- Respondent: ABC Corporation

Background:
Contract dispute regarding software development.

Jurisdiction:
Federal Court of Australia
"""
        )

        result = runner.invoke(
            cli, ["barbrief", "case_facts.txt", "--hearing-type", "trial"]
        )

        assert result.exit_code in [0, 1], f"barbrief failed: {result.output}"
        assert "AttributeError" not in result.output
        assert "'NoneType' object" not in result.output


# ============================================================================
# TEST: TEXT/QUESTION COMMANDS
# ============================================================================


@patch("litassist.commands.lookup.perform_cse_searches")
@patch("litassist.commands.lookup.fetchers._fetch_url_content")
def test_question_based_commands(mock_fetch, mock_cse, test_config_file, mock_external_apis):
    """Test commands that take text/question arguments: lookup, draft."""
    mock_fetch.return_value = "Test content"
    mock_cse.return_value = ["https://test.com/result"]

    from litassist.cli import cli
    from litassist.commands import register_commands

    register_commands(cli)
    runner = CliRunner()

    # Test lookup
    result = runner.invoke(cli, ["lookup", "What is the test for negligence?"])
    assert result.exit_code in [0, 1], f"lookup failed: {result.output}"
    assert "AttributeError" not in result.output

    # Test draft with RAG - requires documents and query
    with patch("litassist.helpers.retriever.Retriever"), patch(
        "litassist.utils.text_processing.create_embeddings"
    ):
        # Create a test file
        with runner.isolated_filesystem():
            Path("case_facts.txt").write_text("Test facts")
            result = runner.invoke(
                cli, ["draft", "case_facts.txt", "draft a statement of claim"]
            )
            assert result.exit_code in [0, 1], f"draft failed: {result.output}"
            assert "AttributeError" not in result.output


def test_verify_with_file(test_config_file, mock_external_apis, tmp_path):
    """Test verify command with file input."""
    from litassist.cli import cli
    from litassist.commands import register_commands

    register_commands(cli)
    runner = CliRunner()

    # Create test file
    test_file = tmp_path / "test_verify.txt"
    test_file.write_text(
        """
    The High Court in Mabo v Queensland (No 2) [1992] HCA 23 established
    the principle of native title in Australian law.
    """
    )

    result = runner.invoke(cli, ["verify", str(test_file)])

    assert result.exit_code in [0, 1], f"verify failed: {result.output}"
    assert "AttributeError" not in result.output


# ============================================================================
# TEST: CASE_FACTS DEPENDENT COMMANDS
# ============================================================================


def test_strategy_brainstorm_caseplan_with_facts(test_config_file, mock_external_apis):
    """Test commands that use case_facts.txt: brainstorm, strategy, caseplan."""
    from litassist.cli import cli
    from litassist.commands import register_commands

    register_commands(cli)
    runner = CliRunner()

    with runner.isolated_filesystem():
        # Create minimal case_facts.txt
        Path("case_facts.txt").write_text(
            """
Parties:
- Applicant: Test Party A
- Respondent: Test Party B

Background:
Test legal matter for command testing.

Issues:
- Test issue one
"""
        )

        # Test brainstorm - requires --side and --area
        result = runner.invoke(
            cli, ["brainstorm", "--side", "plaintiff", "--area", "civil"]
        )
        assert result.exit_code in [0, 1], f"brainstorm failed: {result.output}"
        assert "AttributeError" not in result.output

        # Test strategy - requires case_facts and --outcome
        result = runner.invoke(
            cli, ["strategy", "case_facts.txt", "--outcome", "settlement"]
        )
        assert result.exit_code in [0, 1], f"strategy failed: {result.output}"
        assert "AttributeError" not in result.output

        # Test caseplan - requires case_facts argument
        result = runner.invoke(cli, ["caseplan", "case_facts.txt"])
        assert result.exit_code in [0, 1], f"caseplan failed: {result.output}"
        assert "AttributeError" not in result.output


# ============================================================================
# TEST: API TEST COMMAND
# ============================================================================


@patch("litassist.cli.validate_credentials")
@patch("litassist.cli.test_scraping_capabilities")
def test_api_test_command(
    mock_scraping, mock_validate, test_config_file, mock_external_apis
):
    """Test the 'test' command that validates API connectivity."""
    # Mock the validation functions
    mock_validate.return_value = None
    mock_scraping.return_value = None

    from litassist.cli import test

    # Note: test command is defined directly in cli.py, not via register_commands
    runner = CliRunner()

    # Test the test command directly
    result = runner.invoke(test)

    # Command should run (even if APIs are mocked)
    assert result.exit_code in [0, 1], f"test command failed: {result.output}"
    assert "AttributeError" not in result.output


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================


def test_commands_with_missing_required_arguments(test_config_file, mock_external_apis):
    """Test commands fail appropriately when required arguments are missing."""
    from litassist.cli import cli
    from litassist.commands import register_commands

    register_commands(cli)
    runner = CliRunner()

    # Commands that require arguments should fail with exit code 2
    missing_arg_tests = [
        ("lookup", []),  # Missing QUESTION
        ("draft", []),  # Missing QUESTION
        ("extractfacts", []),  # Missing FILE
        ("digest", []),  # Missing FILE
        ("counselnotes", []),  # Missing FILE
    ]

    for cmd, args in missing_arg_tests:
        result = runner.invoke(cli, [cmd] + args)

        assert result.exit_code == 2, f"{cmd} should fail with missing args"
        assert "Error" in result.output or "Usage" in result.output
        # Should NOT have attribute errors
        assert "AttributeError" not in result.output
        assert "'NoneType' object" not in result.output


def test_config_missing_error_handling():
    """Test graceful failure when config file cannot be found."""
    # Save and clear any existing module
    import sys

    original_config_module = sys.modules.get("litassist.config")

    if "litassist.config" in sys.modules:
        del sys.modules["litassist.config"]

    try:
        from litassist.config import ConfigError

        with patch("os.path.exists", return_value=False), patch(
            "pathlib.Path.exists", return_value=False
        ):
            # Clear cached instance
            import litassist.config

            if hasattr(litassist.config, "_config_instance"):
                litassist.config._config_instance = None

            # Should raise ConfigError, not AttributeError
            with pytest.raises(ConfigError) as exc_info:
                from litassist.config import get_config

                get_config()

            assert "config" in str(exc_info.value).lower()
    finally:
        # CRITICAL: Restore the original mocked module for other tests
        if original_config_module:
            sys.modules["litassist.config"] = original_config_module


# ============================================================================
# TEST: SPECIFIC BUG PREVENTION
# ============================================================================


def test_would_have_caught_config_none_bug(test_config_file):
    """
    Specific test that would have caught the CONFIG=None AttributeError bug.
    This simulates the exact failure mode that occurred.
    """
    # Clear any cached config
    import litassist.config

    litassist.config._config_instance = None

    # Import a command (this would trigger the error with old code)
    # Testing that import doesn't raise AttributeError
    from litassist.config import get_config

    # This would have raised: AttributeError: 'NoneType' object has no attribute 'max_chars'
    config = get_config()
    assert config is not None, "Config should not be None"
    assert hasattr(config, "max_chars"), "Config should have max_chars"

    # Try to access the attribute (this was the failure point)
    max_chars_value = config.max_chars
    assert max_chars_value == 200000, "Should get value from template"


# ============================================================================
# TEST: REFACTORED MODULES
# ============================================================================


def test_refactored_utils_imports(test_config_file):
    """Test that refactored utils modules import correctly."""
    # These were refactored from litassist.utils to submodules
    from litassist.utils.core import heartbeat, parse_strategies_file  # noqa: F401
    from litassist.utils.formatting import success_message, error_message  # noqa: F401
    from litassist.utils.text_processing import (
        chunk_text,
    )  # noqa: F401
    from litassist.utils.file_ops import read_document, validate_file_size  # noqa: F401
    from litassist.utils.legal_reasoning import create_reasoning_prompt  # noqa: F401
    from litassist.timing import timed

    # Verify they're callable
    assert callable(heartbeat)
    assert callable(success_message)
    assert callable(chunk_text)
    assert callable(timed)
