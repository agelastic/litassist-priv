"""
Behavioural tests for the `litassist test` command helpers in
`litassist/cli.py`. Offline; all external probes are mocked.

Scope: the BYOK reminder block is the only piece of `validate_credentials`
with non-trivial branching worth pinning. The Jina-probe removal and
the `/auth/key` -> `/key` migration are guarded by WHY comments at
the source sites rather than by tests, because the threat model is
weak (re-adding either is a deliberate edit a reviewer would catch)
and the defended code surface is tiny (zero lines / one URL string).
"""

from unittest.mock import MagicMock

import pytest


def _fake_config():
    cfg = MagicMock()
    cfg.or_key = "test-or-key"
    cfg.or_base = "https://openrouter.ai/api/v1"
    cfg.g_key = "test-g-key"
    cfg.cse_id = "test-cse-id"
    cfg.using_placeholders.return_value = {
        "openrouter": False,
        "google_cse": False,
    }
    return cfg


def _stub_auth_and_catalogue(monkeypatch, configured_model_ids):
    """Wire up `requests.get` and Google CSE so
    `validate_credentials` runs through all probes against a synthetic
    OpenRouter catalogue containing exactly `configured_model_ids`."""
    called_urls: list[str] = []

    def fake_get(url, **_kw):
        called_urls.append(url)
        resp = MagicMock()
        resp.status_code = 200
        if url.endswith("/models"):
            resp.json.return_value = {
                "data": [{"id": m} for m in configured_model_ids]
            }
        else:
            resp.json.return_value = {"data": {"label": "test"}}
        resp.text = ""
        return resp

    monkeypatch.setattr("requests.get", fake_get)

    fake_service = MagicMock()
    monkeypatch.setattr(
        "googleapiclient.discovery.build", lambda *_a, **_kw: fake_service
    )
    # `validate_credentials` calls `load_config()` (imported as a bare
    # name from `litassist.config`); patch the name as it lives in
    # `litassist.cli` so the alias inside the function is hit.
    monkeypatch.setattr("litassist.cli.load_config", _fake_config)
    return called_urls


@pytest.mark.unit
@pytest.mark.offline
class TestBYOKReminder:
    """`validate_credentials` must print a BYOK reminder block listing
    each configured model that appears in `BYOK_REQUIRED_MODELS`,
    alongside the commands that route to it. When no configured model
    is BYOK-required the block must stay silent.

    OpenRouter does not surface BYOK status via the API. The reminder
    is a static lookup against a hand-maintained set; misconfigured
    BYOK still fails at first call, but the reminder flags the risk
    up-front."""

    def test_reminder_fires_for_configured_byok_model(
        self, monkeypatch, capsys
    ):
        """openai/o3-pro configured for `draft` -> reminder block prints
        the model id and at least the `draft` command name."""
        from litassist import cli

        _stub_auth_and_catalogue(
            monkeypatch,
            ["openai/o3-pro", "anthropic/claude-sonnet-4.6"],
        )
        monkeypatch.setattr(
            "litassist.llm.factory.LLMClientFactory.list_configurations",
            lambda: {
                "draft": {"model": "openai/o3-pro"},
                "extractfacts": {"model": "anthropic/claude-sonnet-4.6"},
            },
        )

        cli.validate_credentials(show_progress=True)

        out = capsys.readouterr().out
        assert "BYOK reminder" in out, (
            f"Reminder block must print when a BYOK model is configured; "
            f"output was:\n{out}"
        )
        assert "openai/o3-pro" in out
        assert "draft" in out
        assert (
            "openrouter.ai/settings/integrations" in out
        ), "Reminder must point at the OpenRouter integrations URL."

    def test_reminder_silent_when_no_byok_models_configured(
        self, monkeypatch, capsys
    ):
        """When every configured model is non-BYOK (e.g. all routed to
        anthropic/claude-sonnet-4.6), no reminder block should print."""
        from litassist import cli

        _stub_auth_and_catalogue(
            monkeypatch, ["anthropic/claude-sonnet-4.6"]
        )
        monkeypatch.setattr(
            "litassist.llm.factory.LLMClientFactory.list_configurations",
            lambda: {
                "draft": {"model": "anthropic/claude-sonnet-4.6"},
                "extractfacts": {"model": "anthropic/claude-sonnet-4.6"},
            },
        )

        cli.validate_credentials(show_progress=True)

        out = capsys.readouterr().out
        assert "BYOK reminder" not in out, (
            f"No BYOK-required model is configured; reminder block must "
            f"stay silent. Output was:\n{out}"
        )

    def test_reminder_groups_multiple_commands_under_one_model(
        self, monkeypatch, capsys
    ):
        """openai/o3-pro routed by multiple commands -> all command
        names appear on the same line, not in separate blocks. Guards
        the `setdefault(model, []).append(cfg_key)` grouping logic
        against a future regression to `dict[model] = [cfg_key]`
        (overwriting instead of appending), which the single-model
        tests above would not catch."""
        from litassist import cli

        _stub_auth_and_catalogue(monkeypatch, ["openai/o3-pro"])
        monkeypatch.setattr(
            "litassist.llm.factory.LLMClientFactory.list_configurations",
            lambda: {
                "draft": {"model": "openai/o3-pro"},
                "counselnotes": {"model": "openai/o3-pro"},
                "barbrief": {"model": "openai/o3-pro"},
            },
        )

        cli.validate_credentials(show_progress=True)

        out = capsys.readouterr().out
        # Model id appears once; commands all appear on a single line.
        assert out.count("openai/o3-pro is configured for") == 1
        assert "draft" in out
        assert "counselnotes" in out
        assert "barbrief" in out
