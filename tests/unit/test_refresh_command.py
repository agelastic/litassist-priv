"""
Tests for the `litassist refresh` command helpers.

The command itself is one HTTP fetch + one YAML write away from real
external state. These tests exercise each helper in isolation against
a synthetic OpenRouter `/models` payload so the regeneration logic is
pinned without touching the network.
"""

from pathlib import Path
from unittest.mock import patch

import click
import pytest
import yaml

from litassist.commands.refresh import (
    DEFAULT_OPENROUTER_MODELS_URL,
    _build_capabilities,
    _distinct_model_ids,
    _resolve_models_url,
    _write_capabilities_yaml,
)


@pytest.mark.unit
@pytest.mark.offline
class TestDistinctModelIds:
    def test_extracts_unique_models_sorted(self):
        configs = {
            "draft": {"model": "openai/o3-pro"},
            "extractfacts": {"model": "anthropic/claude-sonnet-4.6"},
            "barbrief": {"model": "openai/o3-pro"},  # duplicate
            "lookup-irac": {"model": "google/gemini-3.5-flash"},
        }
        assert _distinct_model_ids(configs) == [
            "anthropic/claude-sonnet-4.6",
            "google/gemini-3.5-flash",
            "openai/o3-pro",
        ]

    def test_ignores_non_model_entries(self):
        """Entries that aren't dicts (e.g. top-level YAML comments
        accidentally promoted to keys) or that lack a 'model' field
        must not break extraction."""
        configs = {
            "draft": {"model": "openai/o3-pro"},
            "comment_entry": "this is a string not a dict",
            "incomplete": {"temperature": 0.5},  # no model
        }
        assert _distinct_model_ids(configs) == ["openai/o3-pro"]


@pytest.mark.unit
@pytest.mark.offline
class TestBuildCapabilities:
    def _sample_or_data(self):
        return {
            "data": [
                {
                    "id": "openai/o3-pro",
                    "context_length": 200_000,
                    "pricing": {"prompt": "0.00002", "completion": "0.00008"},
                    "supported_parameters": ["max_tokens", "reasoning"],
                },
                {
                    "id": "anthropic/claude-sonnet-4.6",
                    "context_length": 1_000_000,
                    "pricing": {"prompt": "0.000003", "completion": "0.000015"},
                    "supported_parameters": [
                        "temperature",
                        "top_p",
                        "max_tokens",
                    ],
                },
            ]
        }

    def test_builds_expected_shape_for_configured_models(self):
        caps = _build_capabilities(
            ["openai/o3-pro", "anthropic/claude-sonnet-4.6"],
            self._sample_or_data(),
        )
        # Per-token $ → per-MTok $ conversion = ×1_000_000 then rounded.
        assert caps["openai/o3-pro"] == {
            "context_window": 200_000,
            "input_price_per_mtok": 20.0,
            "output_price_per_mtok": 80.0,
            "supported_parameters": ["max_tokens", "reasoning"],
        }
        assert caps["anthropic/claude-sonnet-4.6"]["context_window"] == 1_000_000
        assert caps["anthropic/claude-sonnet-4.6"]["input_price_per_mtok"] == 3.0
        # supported_parameters comes back sorted regardless of input order.
        assert caps["anthropic/claude-sonnet-4.6"]["supported_parameters"] == [
            "max_tokens",
            "temperature",
            "top_p",
        ]

    def test_missing_model_raises_click_exception(self):
        """If a model id from model_configs.yaml is absent from OR's
        response, refresh must fail loudly so the user notices a
        silent deprecation. Error message names the missing model."""
        with pytest.raises(click.ClickException) as exc_info:
            _build_capabilities(
                ["openai/o3-pro", "fake/never-existed-model"],
                self._sample_or_data(),
            )
        assert "fake/never-existed-model" in str(exc_info.value.message)

    def test_handles_missing_pricing_fields_gracefully(self):
        """OpenRouter sometimes lists models without pricing data (e.g.
        free preview models). Capability entry stays parseable; price
        fields become None rather than raising."""
        or_data = {
            "data": [
                {
                    "id": "free/preview-model",
                    "context_length": 128_000,
                    "pricing": {},
                    "supported_parameters": ["temperature"],
                }
            ]
        }
        caps = _build_capabilities(["free/preview-model"], or_data)
        assert caps["free/preview-model"]["input_price_per_mtok"] is None
        assert caps["free/preview-model"]["output_price_per_mtok"] is None

    def test_null_context_length_fails_loudly(self):
        """OpenRouter occasionally lists preview / custom models with
        `context_length: null`. Silently substituting 0 would cascade
        into zero-sized chunk budgets everywhere downstream, so the
        helper must fail with a message naming the offending model
        (gemini-code-assist PR #77 review)."""
        or_data = {
            "data": [
                {
                    "id": "broken/preview-model",
                    "context_length": None,
                    "pricing": {"prompt": "0.0", "completion": "0.0"},
                    "supported_parameters": [],
                }
            ]
        }
        with pytest.raises(click.ClickException) as exc_info:
            _build_capabilities(["broken/preview-model"], or_data)
        msg = str(exc_info.value.message)
        assert "broken/preview-model" in msg
        assert "missing context_length" in msg

    def test_non_numeric_context_length_fails_loudly(self):
        """If OpenRouter returns a non-numeric `context_length` (e.g.
        the string \"unknown\" for a preview model), the loop must
        surface the bad value rather than blowing up with TypeError
        mid-iteration."""
        or_data = {
            "data": [
                {
                    "id": "weird/model",
                    "context_length": "unknown",
                    "pricing": {"prompt": "0.0", "completion": "0.0"},
                    "supported_parameters": [],
                }
            ]
        }
        with pytest.raises(click.ClickException) as exc_info:
            _build_capabilities(["weird/model"], or_data)
        assert "weird/model" in str(exc_info.value.message)
        assert "non-numeric context_length" in str(exc_info.value.message)


@pytest.mark.unit
@pytest.mark.offline
class TestResolveModelsUrl:
    def test_returns_public_default_when_or_base_empty(self):
        """No configured base → public OpenRouter endpoint."""
        with patch("litassist.config.get_config") as mock:
            mock.return_value.or_base = ""
            assert _resolve_models_url() == DEFAULT_OPENROUTER_MODELS_URL

    def test_respects_configured_or_base(self):
        """Custom proxy/mirror → refresh hits the same host every
        other LLM call uses. Trailing slash on or_base is normalised."""
        with patch("litassist.config.get_config") as mock:
            mock.return_value.or_base = "https://proxy.example.com/openrouter/v1/"
            assert (
                _resolve_models_url()
                == "https://proxy.example.com/openrouter/v1/models"
            )

    def test_falls_back_when_config_unloadable(self):
        """Running outside a configured env (e.g. dev import) must
        not crash refresh -- fall through to the public default."""
        with patch(
            "litassist.config.get_config",
            side_effect=RuntimeError("no config"),
        ):
            assert _resolve_models_url() == DEFAULT_OPENROUTER_MODELS_URL


@pytest.mark.unit
@pytest.mark.offline
class TestWriteCapabilitiesYaml:
    def test_writes_deterministic_sorted_yaml(self, tmp_path: Path):
        """Capability YAML must round-trip cleanly and order keys
        deterministically -- the file is regenerated on every refresh
        and noisy diffs from unordered output would obscure real
        changes."""
        output = tmp_path / "model_capabilities.yaml"
        # Intentionally unsorted input order to verify deterministic
        # output regardless of caller key order.
        caps = {
            "zzz/last-model": {"context_window": 1, "supported_parameters": []},
            "aaa/first-model": {"context_window": 2, "supported_parameters": []},
        }
        _write_capabilities_yaml(output, caps, "https://example.com/models")
        text = output.read_text()
        assert text.startswith("---\n")
        assert "# Auto-generated by `litassist refresh`." in text
        assert "Source: https://example.com/models" in text
        # safe_dump emits keys in sorted order with sort_keys=True (the
        # default for safe_dump); verify by re-loading and comparing
        # the iteration order.
        loaded = yaml.safe_load(text)
        assert list(loaded.keys()) == ["aaa/first-model", "zzz/last-model"]
