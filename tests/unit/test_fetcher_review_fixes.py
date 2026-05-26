"""
Regression tests for review fixes 26/05/2026 (codex pass on fix-lookups).

Each test pins one fix:
- Content-Type guard rejects non-HTML payloads before BS4 extraction
- legislation.gov.au ToC-follow uses parsed hostname, not substring match
- Jina failure logs render content_size and error in the markdown formatter
"""

import io
from unittest.mock import MagicMock, patch

from litassist.commands.lookup import fetchers
from litassist.logging.markdown_writers import write_fetch_log_markdown


def _build_response(status=200, text="", content=None, content_type="text/html"):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.content = content if content is not None else text.encode("utf-8")
    r.headers = {"content-type": content_type} if content_type else {}
    return r


def _render(payload):
    buf = io.StringIO()
    write_fetch_log_markdown(buf, "fetch_attempt", "20260526-160000", payload)
    return buf.getvalue()


class TestContentTypeGuard:
    def setup_method(self, _):
        fetchers._last_austlii_completion = 0

    def test_application_javascript_response_falls_back_to_jina(self):
        """If curl_cffi accidentally returns a JS bundle (e.g. via redirect),
        BS4 would treat it as HTML and pass the gibberish length check.
        Content-Type guard rejects before BS4."""
        js_body = "(function(){var x=" + ("a" * 500) + ";})();"
        captured = {"jina_called": False}

        def fake_curl(url, timeout=10):
            return _build_response(
                status=200, text=js_body, content_type="application/javascript",
            )

        def fake_jina(url, timeout=10):
            captured["jina_called"] = True
            return ""

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_curl), \
                patch.object(fetchers, "_fetch_via_jina", side_effect=fake_jina):
            fetchers._fetch_url_content("https://example.gov.au/bundle.js")

        assert captured["jina_called"], (
            "application/javascript response must fall back to Jina"
        )

    def test_application_json_response_falls_back_to_jina(self):
        json_body = '{"data": ' + ('"item",' * 100) + '}'
        captured = {"jina_called": False}

        def fake_curl(url, timeout=10):
            return _build_response(
                status=200, text=json_body, content_type="application/json",
            )

        def fake_jina(url, timeout=10):
            captured["jina_called"] = True
            return ""

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_curl), \
                patch.object(fetchers, "_fetch_via_jina", side_effect=fake_jina):
            fetchers._fetch_url_content("https://example.gov.au/api")

        assert captured["jina_called"]

    def test_text_html_response_is_processed_normally(self):
        html_body = "<!doctype html><html><body>" + ("<p>real content here. </p>" * 50) + "</body></html>"
        captured = {"jina_called": False}

        def fake_curl(url, timeout=10):
            return _build_response(
                status=200, text=html_body, content_type="text/html; charset=utf-8",
            )

        def fake_jina(url, timeout=10):
            captured["jina_called"] = True
            return ""

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_curl), \
                patch.object(fetchers, "_fetch_via_jina", side_effect=fake_jina):
            content = fetchers._fetch_url_content("https://example.gov.au/page")

        assert not captured["jina_called"], "text/html must NOT trigger fallback"
        assert "real content" in content.lower()

    def test_missing_content_type_header_is_accepted(self):
        """Some responses lack Content-Type; chain must still process them
        rather than rejecting blindly."""
        html_body = "<!doctype html><html><body>" + ("<p>content. </p>" * 50) + "</body></html>"
        captured = {"jina_called": False}

        def fake_curl(url, timeout=10):
            return _build_response(status=200, text=html_body, content_type=None)

        def fake_jina(url, timeout=10):
            captured["jina_called"] = True
            return ""

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_curl), \
                patch.object(fetchers, "_fetch_via_jina", side_effect=fake_jina):
            fetchers._fetch_url_content("https://example.gov.au/no-ct")

        assert not captured["jina_called"]


class TestLegislationHostnameMatching:
    def setup_method(self, _):
        fetchers._last_austlii_completion = 0

    def test_legitimate_legislation_gov_au_url_follows_toc(self):
        """Real legislation.gov.au /latest/text URL still triggers the
        ToC-link follow when the regex matches. The hostname check rewrite
        must not regress this behaviour."""
        url = "https://www.legislation.gov.au/C2004A02562/latest/text"
        # Note: ToC regex requires double-quoted href attribute - matches
        # the real legislation.gov.au markup.
        toc_body = (
            '<!doctype html><html><body>'
            '<a href="/OEBPS/document_1/document_1.html">Document</a>'
            + ("<p>filler.</p>" * 50)
            + "</body></html>"
        )
        doc_body = "<!doctype html><html><body>" + ("<p>real doc text. </p>" * 100) + "</body></html>"

        def fake_fetch(target_url, timeout=10):
            if "document_1" in target_url:
                return _build_response(status=200, text=doc_body)
            return _build_response(status=200, text=toc_body)

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(url)

        assert "real doc text" in content.lower()

    def test_malicious_url_with_legislation_substring_does_not_trigger_follow(self):
        """A URL where 'legislation.gov.au' and '/latest/text' appear only as
        query parameters or path-of-other-host must NOT trigger the
        OEBPS/document_1 link follow on this attacker-controlled page."""
        # Attacker's host, with our trigger substrings embedded in query
        url = "https://evil.example.com/article?ref=legislation.gov.au/latest/text"

        attack_body = (
            "<!doctype html><html><body>"
            # If hostname check missing, this href would be followed
            "<a href='https://evil.example.com/OEBPS/document_1/document_1.html'>Drive-by</a>"
            + ("<p>filler.</p>" * 50)
            + "</body></html>"
        )
        fetched_urls = []

        def fake_fetch(target_url, timeout=10):
            fetched_urls.append(target_url)
            return _build_response(status=200, text=attack_body)

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            fetchers._fetch_url_content(url)

        # Only the original URL should have been fetched. If the legislation
        # ToC-follow code triggered, evil.example.com/OEBPS/... would appear
        # in fetched_urls.
        assert len(fetched_urls) == 1, (
            f"Expected one fetch (no ToC follow), got {fetched_urls}"
        )
        assert "OEBPS" not in fetched_urls[0]


class TestJinaFailureLogRendering:
    def test_jina_failure_payload_renders_content_size_and_error(self):
        """Regression for the review finding that Jina failure payloads
        previously used response_size/error_message which the formatter
        silently dropped. The fix renames them to content_size/error so the
        formatter renders the fields."""
        rendered = _render({
            "url": "https://example.com/blocked",
            "method": "jina_reader",
            "status": "failed",
            "http_status": 403,
            "content_size": 5782,
            "error": "Cloudflare interstitial body",
            "timestamp": 1716690000,
        })
        assert "Content Size" in rendered
        assert "5,782" in rendered
        assert "Error" in rendered
        assert "Cloudflare interstitial body" in rendered
