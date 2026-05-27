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


class TestConfigValidation:
    def _load(self, path):
        from litassist.config import Config

        return Config(str(path))
    def test_null_openrouter_section_raises_config_error(self, tmp_path):
        # Regression: an empty section header (e.g. `openrouter:` with no
        # body) parses as None. The validator used to do `cfg["openrouter"]
        # ["api_key"]` and raise TypeError/AttributeError, which the CLI
        # didn't recognise. Must raise ConfigError naming the section.
        cfg = _write_config(
            tmp_path,
            "openrouter:\n"
            "openai:\n"
            "  api_key: 'x'\n"
            "google_cse:\n"
            "  api_key: 'x'\n"
            "  cse_id: 'x'\n"
            "pinecone:\n"
            "  api_key: 'x'\n"
            "  environment: 'x'\n"
            "  index_name: 'x'\n",
        )
        from litassist.config import ConfigError

        with pytest.raises(ConfigError) as exc_info:
            self._load(cfg)
        assert "openrouter" in str(exc_info.value).lower()

    def test_null_pinecone_section_raises_config_error(self, tmp_path):
        cfg = _write_config(
            tmp_path,
            "openrouter:\n"
            "  api_key: 'x'\n"
            "openai:\n"
            "  api_key: 'x'\n"
            "google_cse:\n"
            "  api_key: 'x'\n"
            "  cse_id: 'x'\n"
            "pinecone:\n",
        )
        from litassist.config import ConfigError

        with pytest.raises(ConfigError) as exc_info:
            self._load(cfg)
        assert "pinecone" in str(exc_info.value).lower()

    def test_section_of_wrong_type_raises_config_error(self, tmp_path):
        # A scalar value where a mapping is expected is a config error too.
        cfg = _write_config(
            tmp_path,
            "openrouter: 'oops a string'\n"
            "openai:\n"
            "  api_key: 'x'\n"
            "google_cse:\n"
            "  api_key: 'x'\n"
            "  cse_id: 'x'\n"
            "pinecone:\n"
            "  api_key: 'x'\n"
            "  environment: 'x'\n"
            "  index_name: 'x'\n",
        )
        from litassist.config import ConfigError

        with pytest.raises(ConfigError):
            self._load(cfg)


pytestmark = [pytest.mark.unit, pytest.mark.offline]
