"""
Tests for AustLII PDF -> HTML substitution in the lookup fetcher.

AustLII's Cloudflare policy blocks every Python transport on PDF paths
(verified empirically against curl_cffi, Playwright + playwright_stealth,
patchright, nodriver, Camoufox). The HTML sibling at the same path is
served under a relaxed policy that curl_cffi clears. The fetcher rewrites
*.pdf URLs on austlii.edu.au to *.html before the HTTP fetch and never
attempts the PDF directly.
"""

from unittest.mock import MagicMock, patch

from litassist.commands.lookup import fetchers


def _build_response(status=200, text="", content=None):
    r = MagicMock()
    r.status_code = status
    r.text = text
    r.content = content if content is not None else text.encode("utf-8")
    return r


def _good_html(title: str = "Test article", body_text: str = "Substantial article body. " * 20) -> str:
    """Build an HTML response large enough to clear the gibberish threshold."""
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
        # Reset the global AustLII rate-limit timestamp so tests don't sleep.
        fetchers._last_austlii_completion = 0

    def test_austlii_pdf_url_is_rewritten_to_html(self):
        pdf_url = "https://www.austlii.edu.au/au/journals/AukULawRw/1992/5.pdf"
        expected_html = "https://www.austlii.edu.au/au/journals/AukULawRw/1992/5.html"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html("Long --- Insurable Interest"))

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(pdf_url, timeout=15)

        assert captured["url"] == expected_html, (
            f"expected substitution to {expected_html}, got {captured['url']}"
        )
        assert content, "expected non-empty content from HTML sibling"
        assert expected_html in content, "Source header should reflect rewritten URL"

    def test_austlii_html_url_is_not_rewritten(self):
        html_url = "https://www.austlii.edu.au/au/journals/CanterLawRw/2005/9.html"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html("Canterbury article"))

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            fetchers._fetch_url_content(html_url, timeout=15)

        assert captured["url"] == html_url, "HTML URLs must pass through unchanged"

    def test_non_austlii_pdf_url_is_not_rewritten(self):
        pdf_url = "https://www.finance.gov.au/sites/default/files/some-report.pdf"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            # Return PDF magic bytes so the chain routes to _extract_pdf_text path
            return _build_response(status=200, content=b"%PDF-1.4 some bytes")

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch), \
                patch.object(fetchers, "_extract_pdf_text", return_value="[pdf body]"):
            fetchers._fetch_url_content(pdf_url, timeout=15)

        assert captured["url"] == pdf_url, "Non-AustLII PDFs must NOT be rewritten"

    def test_austlii_pdf_substitution_returns_stub_content(self):
        """An HTML stub (only title + nav, no article body) still beats nothing.

        Real AustLII stub pages are ~16 KB raw (clears the 2000-char challenge-page
        size threshold) but extract to ~1 KB of text after script/style removal.
        """
        pdf_url = "https://www.austlii.edu.au/au/journals/AukULawRw/1992/5.pdf"

        # Pad to look like a real AustLII page envelope: enough raw HTML to
        # clear the challenge-page-too-short check, but extracted text is
        # navigation chrome + title (modest size, well-structured).
        nav_block = "\n".join(
            f"<a href='/db/{i}'>Database link {i}</a>" for i in range(50)
        )
        script_block = "<script>" + ("a" * 10000) + "</script>"  # scripts get decomposed
        stub_html = (
            "<!doctype html><html><head>"
            "<title>Long, Julian --- \"Insurable Interest\" [1992] AukULawRw 5; (1992) 7(1) Auckland U L Rev 80</title>"
            f"{script_block}"
            "</head><body>"
            "<header><h1>AustLII Search</h1></header>"
            f"<nav>{nav_block}</nav>"
            "<div class='content'>\n"
            "<p>Long, Julian --- \"The Concept of Insurable Interest and the Insurance Law Reform Act 1985\" [1992] AukULawRw 5</p>\n"
            "<p>Auckland University Law Review</p>\n"
            "<p>This article is available as a PDF document.</p>\n"
            "</div>"
            "</body></html>"
        )
        assert len(stub_html) > 2000, "stub fixture must clear the challenge-page size threshold"

        def fake_fetch(url, timeout=10):
            return _build_response(status=200, text=stub_html)

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            content = fetchers._fetch_url_content(pdf_url, timeout=15)

        assert content, "stub should still return citation text"
        assert "AukULawRw" in content, "citation must survive into output"

    def test_austlii_pdf_substitution_404_falls_back_to_jina(self):
        """When the HTML sibling 404s (e.g. bill_em PDFs), chain falls to Jina."""
        pdf_url = "https://www.austlii.edu.au/au/legis/cth/bill_em/etab2011346.pdf"

        def fake_fetch(url, timeout=10):
            return _build_response(status=404, text="<!doctype html><title>404</title>")

        # Jina also fails realistically for these (verified empirically).
        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch), \
                patch.object(fetchers, "_fetch_via_jina", return_value="") as jina:
            content = fetchers._fetch_url_content(pdf_url, timeout=15)

        assert jina.called, "404 on HTML sibling must fall back to Jina (per chain)"
        assert content == "", "Empty when both substitution and Jina fail"

    def test_substitution_preserves_http_scheme(self):
        """An http:// (not https://) AustLII PDF URL must produce an http:// HTML URL."""
        pdf_url = "http://www.austlii.edu.au/au/journals/VUWLawRw/2020/16.pdf"
        expected_html = "http://www.austlii.edu.au/au/journals/VUWLawRw/2020/16.html"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            fetchers._fetch_url_content(pdf_url, timeout=15)

        assert captured["url"] == expected_html

    def test_substitution_is_case_insensitive_on_extension(self):
        """A .PDF extension (uppercase) must also be rewritten."""
        pdf_url = "https://www.austlii.edu.au/au/journals/AukULawRw/1992/5.PDF"
        captured = {}

        def fake_fetch(url, timeout=10):
            captured["url"] = url
            return _build_response(status=200, text=_good_html())

        with patch.object(fetchers, "_fetch_via_curl_cffi", side_effect=fake_fetch):
            fetchers._fetch_url_content(pdf_url, timeout=15)

        # The implementation rewrites by stripping the last 4 chars then
        # adding ".html" - the case of the rewritten URL preserves the
        # original path case; just verify the substitution happened at all
        assert captured["url"].endswith(".html"), (
            f"Uppercase .PDF was not rewritten: {captured['url']!r}"
        )
