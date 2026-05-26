"""
Regression tests for the gibberish heuristic in _fetch_url_content.

Previous behaviour rejected curl_cffi responses if either:
  (a) extracted text < 100 chars, OR
  (b) text.count("\\n") < 5

Condition (b) was too aggressive on Nuxt-style server-pre-rendered pages
that use Unicode word-joiner separators (U+2060) instead of newlines.
Verified empirically 26/05/2026 against triplezero.vic.gov.au: curl_cffi
returned 25,839 chars of real legal content (78% vocabulary overlap with
Jina, all substantive contract phrases present), but the newline-count
condition fired and the chain fell back to Jina unnecessarily.

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
        """Nuxt-pre-rendered Nuxt page pattern: > 100 chars of extracted text
        but zero newlines (word-joiner separators throughout). Must not
        fall back to Jina."""
        # Pad raw HTML > 3 KB to clear SPA shell size floor and provide
        # plausible page envelope. Use word-joiner U+2060 as separator,
        # mimicking the actual triplezero behaviour.
        word_joiner = "⁠"
        prose_parts = [
            "Standard purchase order terms and conditions",
            "Triple zero process",
            "About us",
            "These terms apply to all purchase orders",
            "The Supplier shall indemnify the Buyer against all liabilities",
            "Intellectual property rights remain with the Supplier",
            "Confidentiality obligations survive termination",
            "Applicable law is the law of Victoria",
        ] * 30  # ~5 KB of text content
        prose = word_joiner.join(prose_parts)
        body = (
            f"<!doctype html><html><body><div id=\"__nuxt\">"
            f"<main>{prose}</main>"
            "</div></body></html>"
        )

        captured = {"jina_called": False}

        def fake_curl(url, timeout=10):
            return _build_response(status=200, text=body)

        def fake_jina(url, timeout=10):
            captured["jina_called"] = True
            return "should not be reached"

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_curl), \
                patch.object(fetchers, "_fetch_via_jina", side_effect=fake_jina):
            content = fetchers._fetch_url_content("https://example.gov.au/contract")

        assert not captured["jina_called"], (
            "Long text without newlines must NOT trigger Jina fallback"
        )
        assert "indemnify" in content.lower()
        assert "purchase order" in content.lower()

    def test_short_text_still_falls_back_to_jina(self):
        """The length check survives. A page with under 100 chars of
        extracted text is still treated as gibberish."""
        # Body with substantial HTML but trivial extracted text after script
        # stripping. > 3 KB raw to avoid challenge-page-too-short rejection.
        body = (
            "<!doctype html><html><body>"
            "<p>Hello.</p>"
            "<script>" + ("a" * 4000) + "</script>"
            "</body></html>"
        )

        captured = {"jina_called": False, "url_seen_by_jina": None}

        def fake_curl(url, timeout=10):
            return _build_response(status=200, text=body)

        def fake_jina(url, timeout=10):
            captured["jina_called"] = True
            captured["url_seen_by_jina"] = url
            return "[Source: ...]\n\nfallback content"

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_curl), \
                patch.object(fetchers, "_fetch_via_jina", side_effect=fake_jina):
            fetchers._fetch_url_content("https://example.gov.au/stub")

        assert captured["jina_called"], "Short text must still fall back to Jina"

    def test_long_text_with_few_newlines_is_accepted(self):
        """A real-content page with 2-3 newlines (not the previous threshold
        of 5) must now be accepted. Catches the case where text has some
        structure but not the magic number of newlines."""
        body = (
            "<!doctype html><html><body>"
            "<p>" + ("This is substantive content. " * 40) + "</p>"
            "<p>" + ("More legal text follows here. " * 30) + "</p>"
            "</body></html>"
        )

        captured = {"jina_called": False}

        def fake_curl(url, timeout=10):
            return _build_response(status=200, text=body)

        def fake_jina(url, timeout=10):
            captured["jina_called"] = True
            return ""

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_curl), \
                patch.object(fetchers, "_fetch_via_jina", side_effect=fake_jina):
            content = fetchers._fetch_url_content("https://example.gov.au/article")

        assert not captured["jina_called"], (
            "Text with substantive content but few newlines must be accepted"
        )
        assert "substantive content" in content.lower()
