"""
Command registration and config-loading error paths.

Guards that register_commands() wires every command into the CLI group and that
each command's --help loads, plus the config error paths and the CONFIG=None
regression. Uses config.yaml.template so the real config module is exercised
offline, without external API calls.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch


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
google_cse:
  api_key: "TEST_GOOGLE_KEY"
  cse_id: "TEST_CSE_ID"
llm:
general:
  heartbeat_interval: 10
  max_chars: 200000
  log_format: "json"
citation_validation:
  offline_validation: false
web_scraping:
  fetch_timeout: 10
  max_fetch_time: 300
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


# ============================================================================
# TEST: COMMAND REGISTRATION
# ============================================================================


def test_all_commands_registered_in_cli_group():
    """register_commands() must wire every command into the CLI group.

    The per-command test files invoke each command object directly, so none of
    them catches a command being dropped from (or never added to) the group.
    This is the sole guard on the group's command set, and the --help loop is a
    cheap loadability smoke that each command's Click decorators import and parse
    (--help short-circuits before any config load or API call).
    """
    import click
    from click.testing import CliRunner
    from litassist.commands import register_commands

    group = click.Group()
    register_commands(group)

    # 'test' is registered directly in cli.py, not via register_commands.
    expected = {
        "barbrief",
        "brainstorm",
        "caseplan",
        "counselnotes",
        "digest",
        "draft",
        "extractfacts",
        "updatefacts",
        "lookup",
        "refresh",
        "strategy",
        "verify",
        "verify-cove",
    }
    assert set(group.commands) == expected

    runner = CliRunner()
    for name, command in group.commands.items():
        result = runner.invoke(command, ["--help"])
        assert result.exit_code == 0, f"{name} --help failed: {result.output}"


# ============================================================================
# TEST: ERROR HANDLING
# ============================================================================


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
