"""
Tests for AustLII URL normalisation in the lookup fetcher.

AustLII serves PDFs and some RTFs behind Cloudflare policies that block
Python transports in common cases. HTML siblings at the same path often pass
curl_cffi cleanly. The fetcher rewrites binary AustLII URLs to HTML siblings
before the HTTP fetch.

Pins production-critical behaviour:
- AustLII PDF URLs are rewritten
- AustLII RTF URLs are rewritten before Cloudflare can block the binary path
- AustLII cgi-bin wrapper URLs are rewritten to direct /au/... content paths
- Non-AustLII PDFs pass through unchanged (no false rewrite)
- Flat HTML sibling 404 retries /index.html before Jina
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


def _good_html(
    title: str = "Test article",
    body_text: str = "Substantial article body. " * 20,
) -> str:
    paragraphs = "\n".join(f"<p>{body_text}</p>" for _ in range(10))
    return (
        "<!doctype html><html><head>"
        f"<title>{title}</title>"
        "</head><body>"
        f"{paragraphs}"
        "</body></html>"
    )


class TestAustliiUrlNormalisation:
    def setup_method(self, _):
        fetchers._last_austlii_completion = 0

    def test_austlii_pdf_url_is_rewritten_to_html(self):
        pdf_url = "https://www.austlii.edu.au/au/journals/AukULawRw/1992/5.pdf"
        expected_html = (
            "https://www.austlii.edu.au/au/journals/AukULawRw/1992/5.html"
        )
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

        with patch.object(
            fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch
        ), patch.object(fetchers, "_extract_pdf_text", return_value="[pdf body]"):
            fetchers._fetch_url_content(pdf_url, timeout=15)

        assert captured["url"] == pdf_url

    def test_austlii_rtf_url_is_rewritten_to_html(self):
        rtf_url = (
            "https://www.austlii.edu.au/au/journals/PrecedentAULA/2016/78.rtf"
        )
        expected_html = (
            "https://www.austlii.edu.au/au/journals/PrecedentAULA/2016/78.html"
        )
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(rtf_url, timeout=15)

        assert captured["url"] == expected_html
        assert content
        assert expected_html in content

    def test_austlii_consolidated_legislation_rtf_url_is_rewritten_to_index_html(
        self,
    ):
        rtf_url = (
            "https://www.austlii.edu.au/au/legis/vic/consol_act/laa197864.rtf"
        )
        expected_html = (
            "https://www.austlii.edu.au/au/legis/vic/consol_act/"
            "laa197864/index.html"
        )
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(rtf_url, timeout=15)

        assert captured["url"] == expected_html
        assert content
        assert expected_html in content

    def test_non_austlii_rtf_url_is_not_rewritten(self):
        rtf_url = "https://example.gov.au/documents/example.rtf"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, content=b"{\\rtf1\\ansi example}")

        with patch.object(
            fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch
        ), patch("litassist.utils.rtf.extract_rtf_text", return_value="[rtf body]"):
            content = fetchers._fetch_url_content(rtf_url, timeout=15)

        assert captured["url"] == rtf_url
        assert content == "[rtf body]"

    def test_plain_austlii_html_url_is_not_rewritten(self):
        html_url = "https://www.austlii.edu.au/au/journals/Foo/2020/1.html"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(html_url, timeout=15)

        assert captured["url"] == html_url
        assert content
        assert html_url in content

    def test_plain_austlii_html_404_does_not_retry_index_html_or_jina(self):
        html_url = "https://www.austlii.edu.au/au/journals/Foo/2020/1.html"
        calls = []

        def fake_fetch(url, timeout=10):
            calls.append(url)
            return _build_response(status=404, text="<!doctype html><title>404</title>")

        with patch.object(
            fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch
        ), patch.object(fetchers, "_fetch_via_jina", return_value="") as jina:
            content = fetchers._fetch_url_content(html_url, timeout=15)

        assert calls == [html_url]
        jina.assert_not_called()
        assert content == ""

    def test_austlii_cgi_viewdoc_index_url_is_rewritten_to_direct_path(self):
        cgi_url = (
            "https://austlii.edu.au/cgi-bin/viewdoc/au/legis/vic/consol_act/"
            "lpulaa2014406/index.html"
        )
        expected_direct = (
            "https://austlii.edu.au/au/legis/vic/consol_act/"
            "lpulaa2014406/index.html"
        )
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(cgi_url, timeout=15)

        assert captured["url"] == expected_direct
        assert content
        assert expected_direct in content

    def test_austlii_cgi_viewdb_section_url_is_rewritten_to_direct_path(self):
        cgi_url = (
            "https://austlii.edu.au/cgi-bin/viewdb/au/legis/nsw/consol_act/"
            "lpulaa2014406/s122.html"
        )
        expected_direct = (
            "https://austlii.edu.au/au/legis/nsw/consol_act/lpulaa2014406/"
            "s122.html"
        )
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(cgi_url, timeout=15)

        assert captured["url"] == expected_direct
        assert content
        assert expected_direct in content

    def test_austlii_cgi_rtf_url_strips_wrapper_before_extension_rewrite(self):
        cgi_url = (
            "https://austlii.edu.au/cgi-bin/viewdoc/au/journals/Foo/2020/"
            "1.rtf"
        )
        expected_direct = "https://austlii.edu.au/au/journals/Foo/2020/1.html"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(cgi_url, timeout=15)

        assert captured["url"] == expected_direct
        assert content
        assert expected_direct in content

    def test_austlii_pdf_flat_html_404_retries_index_html(self):
        pdf_url = "https://www.austlii.edu.au/au/legis/cth/bill_em/foo.pdf"
        expected_flat = "https://www.austlii.edu.au/au/legis/cth/bill_em/foo.html"
        expected_index = (
            "https://www.austlii.edu.au/au/legis/cth/bill_em/foo/index.html"
        )
        calls = []

        def fake_fetch(url, timeout=10):
            calls.append(url)
            if url == expected_flat:
                return _build_response(status=404, text="<!doctype html>")
            return _build_response(status=200, text=_good_html())

        with patch.object(
            fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch
        ), patch.object(fetchers, "_rate_limit_austlii"), patch.object(
            fetchers, "_fetch_via_jina", return_value=""
        ) as jina:
            content = fetchers._fetch_url_content(pdf_url, timeout=15)

        assert calls == [expected_flat, expected_index]
        assert expected_index in content
        jina.assert_not_called()

    def test_austlii_rtf_flat_html_404_retries_index_html(self):
        rtf_url = "https://www.austlii.edu.au/au/legis/cth/bill_em/foo.rtf"
        expected_flat = "https://www.austlii.edu.au/au/legis/cth/bill_em/foo.html"
        expected_index = (
            "https://www.austlii.edu.au/au/legis/cth/bill_em/foo/index.html"
        )
        calls = []

        def fake_fetch(url, timeout=10):
            calls.append(url)
            if url == expected_flat:
                return _build_response(status=404, text="<!doctype html>")
            return _build_response(status=200, text=_good_html())

        with patch.object(
            fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch
        ), patch.object(fetchers, "_rate_limit_austlii"), patch.object(
            fetchers, "_fetch_via_jina", return_value=""
        ) as jina:
            content = fetchers._fetch_url_content(rtf_url, timeout=15)

        assert calls == [expected_flat, expected_index]
        assert expected_index in content
        jina.assert_not_called()

    def test_austlii_pdf_substitution_double_404_skips_jina(self):
        """If flat and index siblings both 404, Jina would only repeat 404."""
        pdf_url = "https://www.austlii.edu.au/au/legis/cth/bill_em/etab2011346.pdf"
        expected_flat = (
            "https://www.austlii.edu.au/au/legis/cth/bill_em/etab2011346.html"
        )
        expected_index = (
            "https://www.austlii.edu.au/au/legis/cth/bill_em/"
            "etab2011346/index.html"
        )
        calls = []

        def fake_fetch(url, timeout=10):
            calls.append(url)
            return _build_response(status=404, text="<!doctype html><title>404</title>")

        with patch.object(
            fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch
        ), patch.object(fetchers, "_rate_limit_austlii"), patch.object(
            fetchers, "_fetch_via_jina", return_value=""
        ) as jina:
            content = fetchers._fetch_url_content(pdf_url, timeout=15)

        assert calls == [expected_flat, expected_index]
        jina.assert_not_called()
        assert content == ""

    def test_austlii_index_retry_no_response_falls_back_to_jina(self):
        pdf_url = "https://www.austlii.edu.au/au/legis/cth/bill_em/foo.pdf"
        expected_flat = "https://www.austlii.edu.au/au/legis/cth/bill_em/foo.html"
        expected_index = (
            "https://www.austlii.edu.au/au/legis/cth/bill_em/foo/index.html"
        )
        calls = []

        def fake_fetch(url, timeout=10):
            calls.append(url)
            if url == expected_flat:
                return _build_response(status=404, text="<!doctype html>")
            return None

        with patch.object(
            fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch
        ), patch.object(fetchers, "_rate_limit_austlii"), patch.object(
            fetchers, "_fetch_via_jina", return_value="[jina]"
        ) as jina:
            content = fetchers._fetch_url_content(pdf_url, timeout=15)

        assert calls == [expected_flat, expected_index]
        jina.assert_called_once_with(expected_index, 15)
        assert content == "[jina]"

    def test_austlii_pdf_url_with_query_and_fragment_is_rewritten(self):
        """Regression for review finding: substitution uses urlsplit so
        query strings and fragments do not defeat the .pdf detection.
        Path is rewritten; query and fragment are preserved on the new URL."""
        pdf_url = (
            "https://www.austlii.edu.au/au/journals/Foo/2020/"
            "1.pdf?download=1#page=2"
        )
        expected_html = (
            "https://www.austlii.edu.au/au/journals/Foo/2020/"
            "1.html?download=1#page=2"
        )
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            fetchers._fetch_url_content(pdf_url, timeout=15)

        assert captured["url"] == expected_html, (
            "Query/fragment-bearing PDF URL must still be rewritten: "
            f"got {captured['url']!r}"
        )
