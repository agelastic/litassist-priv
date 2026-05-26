"""
Regression tests for the gibberish heuristic in _fetch_url_content.

26/05/2026 fix: the newline-count condition was too aggressive on
Nuxt-style server-pre-rendered pages that use Unicode word-joiner
separators (U+2060) instead of newlines. Verified empirically against
triplezero.vic.gov.au: curl_cffi returned 25 KB of real content with
0 newlines, 78% vocabulary overlap with Jina.

The newline check has been removed. Only the length check survives.
"""

from unittest.mock import MagicMock, patch

from litassist.commands.lookup import fetchers


def _build_response(status=200, text="", content=None):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.content = content if content is not None else text.encode("utf-8")
    r.headers = {}
    return r


class TestGibberishHeuristic:
    def setup_method(self, _):
        fetchers._last_austlii_completion = 0

    def test_long_text_with_no_newlines_is_accepted(self):
        """Nuxt pre-render pattern: > 100 chars of text, 0 newlines (word-joiner
        separators throughout). Must not fall back to Jina."""
        word_joiner = "⁠"
        prose_parts = [
            "Standard purchase order terms and conditions",
            "These terms apply to all purchase orders",
            "The Supplier shall indemnify the Buyer against all liabilities",
            "Intellectual property rights remain with the Supplier",
            "Confidentiality obligations survive termination",
        ] * 30
        prose = word_joiner.join(prose_parts)
        body = (
            f"<!doctype html><html><body><div id=\"__nuxt\">"
            f"<main>{prose}</main></div></body></html>"
        )
        captured = {"jina_called": False}

        with patch.object(fetchers, "_fetch_via_curl_cffi",
                          side_effect=lambda u, timeout=10: _build_response(status=200, text=body)), \
                patch.object(fetchers, "_fetch_via_jina",
                             side_effect=lambda u, timeout=10: (
                                 captured.__setitem__("jina_called", True) or "unreached"
                             )):
            content = fetchers._fetch_url_content("https://example.gov.au/contract")

        assert not captured["jina_called"]
        assert "indemnify" in content.lower()

    def test_short_text_still_falls_back_to_jina(self):
        """Length floor survives: < 100 chars of extracted text is still
        treated as gibberish and falls back to Jina."""
        body = (
            "<!doctype html><html><body>"
            "<p>Hello.</p>"
            "<script>" + ("a" * 4000) + "</script>"
            "</body></html>"
        )
        captured = {"jina_called": False}

        with patch.object(fetchers, "_fetch_via_curl_cffi",
                          side_effect=lambda u, timeout=10: _build_response(status=200, text=body)), \
                patch.object(fetchers, "_fetch_via_jina",
                             side_effect=lambda u, timeout=10: (
                                 captured.__setitem__("jina_called", True) or ""
                             )):
            fetchers._fetch_url_content("https://example.gov.au/stub")

        assert captured["jina_called"]
