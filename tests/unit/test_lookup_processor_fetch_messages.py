"""Tests for lookup fetch status messages."""

from unittest.mock import MagicMock, patch

from litassist.commands.lookup import processors
from litassist.commands.lookup.fetchers import FetchedContent
from litassist.commands.lookup.processors import LookupProcessor


def _processor():
    config = MagicMock()
    config.max_fetch_time = 30
    config.fetch_timeout = 10
    return LookupProcessor(config)


class TestLookupFetchMessages:
    def test_reports_curl_cffi_instead_of_http_jina_boilerplate(self, capsys):
        content = FetchedContent(
            "[Source: https://example.gov.au/page]\n\n" + ("body " * 30),
            "curl_cffi",
        )

        with patch.object(processors, "_fetch_url_content", return_value=content), \
                patch.object(LookupProcessor, "_save_fetched_content"):
            _processor().fetch_content(
                ["https://example.gov.au/page"], all_snippets=[], no_fetch=False
            )

        output = capsys.readouterr().out
        assert "via curl_cffi" in output
        assert "HTTP/Jina" not in output

    def test_reports_pdf_extraction_method(self, capsys):
        content = FetchedContent(
            "[PDF DOCUMENT EXTRACTED - 1 pages]\n"
            "[Source: https://example.gov.au/file.pdf]\n"
            "text",
            "pdfplumber",
        )

        with patch.object(processors, "_fetch_url_content", return_value=content), \
                patch.object(LookupProcessor, "_save_fetched_content"):
            _processor().fetch_content(
                ["https://example.gov.au/file.pdf"], all_snippets=[], no_fetch=False
            )

        output = capsys.readouterr().out
        assert "Extracted text from PDF at example.gov.au via pdfplumber" in output
