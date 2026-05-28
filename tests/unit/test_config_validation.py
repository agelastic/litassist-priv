"""Tests for litassist.config validation edge cases."""

import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _use_real_config_module():
    """conftest mocks `litassist.config`; these tests need the real module."""
    original = sys.modules.get("litassist.config")
    if "litassist.config" in sys.modules:
        del sys.modules["litassist.config"]
    yield
    if original is not None:
        sys.modules["litassist.config"] = original


def _write_config(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "config.yaml"
    path.write_text(body)
    return path


_REST_OK = (
    "google_cse:\n"
    "  api_key: 'x'\n"
    "  cse_id: 'x'\n"
)


@pytest.mark.parametrize(
    "first_section,expected_in_msg",
    [
        # Null section header (e.g. `openrouter:` with no body) parses as None;
        # the validator used to subscript None and raise TypeError, which the
        # CLI didn't surface as a config problem.
        ("openrouter:\n", "openrouter"),
        # Scalar where a mapping is expected.
        ("openrouter: 'oops a string'\n", "openrouter"),
    ],
)
def test_invalid_top_level_section_raises_config_error(
    tmp_path, first_section, expected_in_msg
):
    from litassist.config import Config, ConfigError

    cfg = _write_config(tmp_path, first_section + _REST_OK)
    with pytest.raises(ConfigError) as exc_info:
        Config(str(cfg))
    assert expected_in_msg in str(exc_info.value).lower()


pytestmark = [pytest.mark.unit, pytest.mark.offline]
