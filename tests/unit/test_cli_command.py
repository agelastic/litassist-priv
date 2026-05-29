"""
Behavioural tests for the `litassist test` command helpers in
`litassist/cli.py`. Offline; all external probes are mocked.
"""

from unittest.mock import MagicMock

import pytest


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
