"""Tests for lookup fetch status messages."""

from concurrent.futures import Future
from unittest.mock import MagicMock, patch

from litassist.commands.lookup import processors
from litassist.commands.lookup.fetchers import FetchedContent, PendingOcrContent
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

    def test_fetches_pdf_first_and_collects_ocr_after_other_sources(self, capsys):
        ocr_future: Future[str] = Future()
        calls = []

        def fake_fetch(url, timeout=10, ocr_executor=None):
            calls.append(url)
            if url.endswith(".pdf"):
                assert ocr_executor is not None
                return PendingOcrContent(url=url, future=ocr_future, num_pages=2)

            ocr_future.set_result(
                FetchedContent(
                    "[OCR DOCUMENT EXTRACTED - 2 pages]\n"
                    "[Source: https://example.gov.au/file.pdf]\n"
                    "ocr text",
                    "ocrmypdf/Tesseract",
                )
            )
            return FetchedContent(
                "[Source: https://example.gov.au/page]\n\nbody", "curl_cffi"
            )

        with patch.object(processors, "_fetch_url_content", side_effect=fake_fetch), \
                patch.object(LookupProcessor, "_save_fetched_content"), \
                patch("litassist.commands.lookup.processors.time.sleep"):
            # sleep patched out: both URLs share a domain, which would otherwise
            # trigger the real 0.5s same-domain fetch pacing (not under test here).
            contents = _processor().fetch_content(
                [
                    "https://example.gov.au/page",
                    "https://example.gov.au/file.pdf",
                ],
                all_snippets=[],
                no_fetch=False,
            )

        output = capsys.readouterr().out
        assert calls == [
            "https://example.gov.au/file.pdf",
            "https://example.gov.au/page",
        ]
        assert len(contents) == 2
        assert "via curl_cffi" in output
        assert "OCR extracted text from PDF at example.gov.au" in output

    def test_reports_background_ocr_empty_result_as_pdf_skip(self, capsys):
        ocr_future: Future[str] = Future()
        ocr_future.set_result("")

        def fake_fetch(url, timeout=10, ocr_executor=None):
            assert ocr_executor is not None
            return PendingOcrContent(url=url, future=ocr_future, num_pages=1)

        with patch.object(processors, "_fetch_url_content", side_effect=fake_fetch):
            contents = _processor().fetch_content(
                ["https://example.gov.au/file.pdf"],
                all_snippets=[],
                no_fetch=False,
            )

        output = capsys.readouterr().out
        assert contents == []
        assert "PDF skipped after OCR attempt at example.gov.au" in output
        assert "Failed to fetch from example.gov.au" not in output
