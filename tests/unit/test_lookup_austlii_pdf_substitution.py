"""
Tests for AustLII PDF -> HTML substitution in the lookup fetcher.

AustLII serves PDFs behind a Cloudflare policy that blocks every Python
transport tested (curl_cffi, Playwright + stealth variants, patchright,
nodriver, Camoufox - 16+ approaches all returned challenge body). The HTML
sibling at the same path passes curl_cffi cleanly. The fetcher rewrites
*.pdf URLs on austlii.edu.au to *.html before the HTTP fetch.

Pins production-critical behaviour:
- AustLII PDF URLs are rewritten
- Non-AustLII PDFs pass through unchanged (no false rewrite)
- HTML sibling 404 falls back to Jina (failure-mode coverage)
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


def _good_html(title: str = "Test article", body_text: str = "Substantial article body. " * 20) -> str:
    paragraphs = "\n".join(f"<p>{body_text}</p>" for _ in range(10))
    return (
        "<!doctype html><html><head>"
        f"<title>{title}</title>"
        "</head><body>"
        f"{paragraphs}"
        "</body></html>"
    )


class TestAustliiPdfSubstitution:
    def setup_method(self, _):
        fetchers._last_austlii_completion = 0

    def test_austlii_pdf_url_is_rewritten_to_html(self):
        pdf_url = "https://www.austlii.edu.au/au/journals/AukULawRw/1992/5.pdf"
        expected_html = "https://www.austlii.edu.au/au/journals/AukULawRw/1992/5.html"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(pdf_url, timeout=15)

        assert captured["url"] == expected_html
        assert content
        assert expected_html in content

    def test_non_austlii_pdf_url_is_not_rewritten(self):
        pdf_url = "https://www.finance.gov.au/sites/default/files/some-report.pdf"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, content=b"%PDF-1.4 some bytes")

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch), \
                patch.object(fetchers, "_extract_pdf_text", return_value="[pdf body]"):
            fetchers._fetch_url_content(pdf_url, timeout=15)

        assert captured["url"] == pdf_url

    def test_austlii_pdf_substitution_404_falls_back_to_jina(self):
        """bill_em PDFs have no HTML sibling -> 404 -> chain falls to Jina."""
        pdf_url = "https://www.austlii.edu.au/au/legis/cth/bill_em/etab2011346.pdf"

        def fake_fetch(url, timeout=10):
            return _build_response(status=404, text="<!doctype html><title>404</title>")

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch), \
                patch.object(fetchers, "_fetch_via_jina", return_value="") as jina:
            content = fetchers._fetch_url_content(pdf_url, timeout=15)

        assert jina.called
        assert content == ""

    def test_austlii_pdf_url_with_query_and_fragment_is_rewritten(self):
        """Regression for review finding: substitution uses urlsplit so
        query strings and fragments do not defeat the .pdf detection.
        Path is rewritten; query and fragment are preserved on the new URL."""
        pdf_url = "https://www.austlii.edu.au/au/journals/Foo/2020/1.pdf?download=1#page=2"
        expected_html = "https://www.austlii.edu.au/au/journals/Foo/2020/1.html?download=1#page=2"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            fetchers._fetch_url_content(pdf_url, timeout=15)

        assert captured["url"] == expected_html, (
            f"Query/fragment-bearing PDF URL must still be rewritten: got {captured['url']!r}"
        )
