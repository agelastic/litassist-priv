"""
Regression tests for review fixes 26/05/2026 (codex pass on fix-lookups).

Each test pins one fix:
- Content-Type guard rejects non-HTML payloads before BS4 extraction
- legislation.gov.au ToC-follow uses parsed hostname, not substring match
- HTTP 404 is terminal and does not spend a Jina fallback request
- Jina failure logs render content_size and error in the markdown formatter
"""

import io
from unittest.mock import MagicMock, patch

from litassist.commands.lookup import fetchers
from litassist.logging.markdown_writers import write_fetch_log_markdown


def _build_response(
    status=200, text="", content=None, content_type: str | None = "text/html"
):
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
        assert getattr(content, "fetch_method") == "curl_cffi"

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


class TestHttpNotFoundHandling:
    def setup_method(self, _):
        fetchers._last_austlii_completion = 0

    def test_http_404_skips_jina_fallback(self):
        url = "https://example.gov.au/dead-link"

        def fake_curl(target_url, timeout=10):
            return _build_response(
                status=404, text="<!doctype html><title>Not found</title>"
            )

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_curl), \
                patch.object(fetchers, "_fetch_via_jina", return_value="") as jina:
            content = fetchers._fetch_url_content(url, timeout=15)

        jina.assert_not_called()
        assert content == ""


class TestPdfExtractionReporting:
    def test_pdf_without_extractable_text_reports_skipped(self, capsys):
        class FakePage:
            def extract_text(self):
                return None

        class FakePdf:
            pages = [FakePage()]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_pdfplumber = MagicMock()
        fake_pdfplumber.open.return_value = FakePdf()

        with patch.dict("sys.modules", {"pdfplumber": fake_pdfplumber}), \
                patch("shutil.which", return_value=None), \
                patch.object(fetchers, "save_log") as save_log:
            content = fetchers._extract_pdf_text(
                "https://example.gov.au/scanned.pdf", b"%PDF-1.4"
            )

        output = capsys.readouterr().out
        assert content == ""
        assert "PDF skipped: no extractable text" in output
        assert save_log.call_count == 2
        assert save_log.call_args.args[1]["method"] == "pdf"
        assert save_log.call_args.args[1]["status"] == "skipped"
        assert "no extractable text" in save_log.call_args.args[1]["reason"]

    def test_pdf_without_extractable_text_uses_ocr_when_available(self, capsys):
        class FakePage:
            def extract_text(self):
                return None

        class FakePdf:
            pages = [FakePage(), FakePage()]

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        fake_pdfplumber = MagicMock()
        fake_pdfplumber.open.return_value = FakePdf()

        def fake_run(cmd, **kwargs):
            sidecar_path = cmd[cmd.index("--sidecar") + 1]
            with open(sidecar_path, "w", encoding="utf-8") as f:
                f.write("OCR text from scanned PDF")
            result = MagicMock()
            result.returncode = 0
            result.stderr = ""
            result.stdout = ""
            return result

        with patch.dict("sys.modules", {"pdfplumber": fake_pdfplumber}), \
                patch("shutil.which", return_value="/usr/bin/ocrmypdf"), \
                patch("subprocess.run", side_effect=fake_run), \
                patch.object(fetchers, "save_log") as save_log:
            content = fetchers._extract_pdf_text(
                "https://example.gov.au/scanned.pdf", b"%PDF-1.4"
            )

        output = capsys.readouterr().out
        assert "OCR extracted PDF text" in output
        assert isinstance(content, str)
        assert "[OCR DOCUMENT EXTRACTED - 2 pages]" in content
        assert "OCR text from scanned PDF" in content
        assert getattr(content, "fetch_method") == "ocrmypdf/Tesseract"
        save_log.assert_called_once()
        assert save_log.call_args.args[1]["method"] == "ocr"
        assert save_log.call_args.args[1]["status"] == "success"


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
