"""
Behavioural tests for the `litassist test` command helpers in
`litassist/cli.py`. Offline; all external probes are mocked.
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
class TestJinaProbeRemoved:
    """The Jina Reader probe was removed because failures on the
    free-tier `r.jina.ai` endpoint were non-diagnostic of LitAssist
    health: Jina is a fallback transport only exercised on Cloudflare
    challenges / SPA shells, not on the happy path."""

    def test_scraping_test_does_not_invoke_jina(self, monkeypatch):
        """`test_scraping_capabilities` must not call
        `_fetch_via_jina`. If a future change resurrects the probe this
        regression test should fail."""
        from litassist import cli

        calls: list[tuple] = []

        def _record(*args, **_kwargs):
            calls.append((args, _kwargs))
            return ""

        monkeypatch.setattr(
            "litassist.commands.lookup.fetchers._fetch_via_jina", _record
        )
        # Stub the two remaining probes so the function executes cleanly.
        monkeypatch.setattr(
            "litassist.commands.lookup.fetchers._fetch_url_content",
            lambda _url, timeout=5: "x" * 2000,
        )

        fake_head = MagicMock()
        fake_head.status_code = 200
        fake_head.headers = {"content-type": "application/pdf"}
        fake_get = MagicMock()
        fake_get.status_code = 200
        fake_get.content = b"%PDF body " * 50
        monkeypatch.setattr("requests.head", lambda *_a, **_kw: fake_head)
        monkeypatch.setattr("requests.get", lambda *_a, **_kw: fake_get)

        cli.test_scraping_capabilities()

        assert calls == [], (
            "Jina probe must not be invoked from `litassist test`; the "
            "fallback transport's health surfaces on the first lookup "
            "that hits a Cloudflare challenge."
        )


@pytest.mark.unit
@pytest.mark.offline
class TestAuthEndpoint:
    """`validate_credentials` must probe OpenRouter's current `/key`
    endpoint, not the legacy `/auth/key` alias. Both still resolve;
    the migration aligns with current OpenRouter API docs."""

    def test_auth_probe_targets_key_not_auth_key(self, monkeypatch):
        from litassist import cli

        called_urls = _stub_auth_and_catalogue(monkeypatch, [])
        # Catalogue check needs to find every configured model. Empty
        # configured set means the missing-models guard never fires.
        monkeypatch.setattr(
            "litassist.llm.factory.LLMClientFactory.list_configurations",
            lambda: {},
        )

        cli.validate_credentials(show_progress=False)

        # Auth probe hits /key (no /models, no /auth/key suffix).
        auth_calls = [u for u in called_urls if u.endswith("/key")]
        legacy_calls = [u for u in called_urls if u.endswith("/auth/key")]
        assert auth_calls, (
            "Expected at least one GET to OpenRouter's /key endpoint; "
            f"saw: {called_urls!r}"
        )
        assert not legacy_calls, (
            "Auth probe must not target the legacy /auth/key alias; "
            f"saw: {called_urls!r}"
        )


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
        names appear on the same line, not in separate blocks."""
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
