"""
Tests for RTF text extraction helpers.

AustLII serves some judgments as .rtf and users hand in local .rtf
documents. Both the URL fetcher and the local-file reader must detect
RTF magic bytes and extract plain text, or raw control codes
({\\rtf1\\ansi\\deff0...}) leak into LLM prompts as gibberish.
"""

from unittest.mock import patch

import pytest

from litassist.utils.rtf import (
    RTF_MAGIC_BYTES,
    extract_rtf_text,
    looks_like_rtf,
)


def _minimal_rtf(body: str = "hello world") -> bytes:
    """Construct minimal valid RTF bytes."""
    return ("{\\rtf1\\ansi\\deff0 " + body + "}").encode("utf-8")


class TestRtfMagicDetection:
    def test_rtf_magic_bytes_constant(self):
        assert RTF_MAGIC_BYTES == b"{\\rtf"

    def test_detects_minimal_rtf(self):
        assert looks_like_rtf(_minimal_rtf()) is True

    def test_rejects_html(self):
        assert looks_like_rtf(b"<html><body>hi</body></html>") is False

    def test_rejects_pdf_header(self):
        assert looks_like_rtf(b"%PDF-1.4\n...") is False

    def test_rejects_empty(self):
        assert looks_like_rtf(b"") is False

    def test_rejects_partial_marker(self):
        # Must start with `{\\rtf`, no whitespace tolerance.
        assert looks_like_rtf(b" {\\rtf1") is False


class TestRtfExtraction:
    def test_minimal_rtf_extracts_text(self):
        result = extract_rtf_text("test.rtf", _minimal_rtf("hello world"))
        assert "hello world" in result
        assert "[RTF DOCUMENT EXTRACTED]" in result
        assert "[Source: test.rtf]" in result
        assert "[END OF RTF]" in result

    def test_empty_rtf_returns_empty(self):
        # `{\\rtf1\\ansi\\deff0 }` strips to whitespace -> empty.
        result = extract_rtf_text("empty.rtf", b"{\\rtf1\\ansi\\deff0 }")
        assert result == ""

    def test_missing_striprtf_returns_placeholder(self):
        # When striprtf is absent the helper must not crash; it returns a
        # placeholder string so callers can surface the issue to the user.
        with patch.dict("sys.modules", {"striprtf": None, "striprtf.striprtf": None}):
            result = extract_rtf_text("test.rtf", _minimal_rtf())
            assert "RTF DOCUMENT" in result
            assert "striprtf not installed" in result

    def test_extraction_failure_returns_placeholder(self):
        # Force striprtf.rtf_to_text to raise.
        def boom(_):
            raise ValueError("simulated parse error")

        with patch("striprtf.striprtf.rtf_to_text", side_effect=boom):
            result = extract_rtf_text("bad.rtf", _minimal_rtf())
            assert "RTF DOCUMENT" in result
            assert "RTF extraction failed" in result
            assert "simulated parse error" in result

    def test_non_utf8_bytes_handled_via_decode_replace(self):
        # Insert an invalid utf-8 byte; the helper should not raise and should
        # still extract the surrounding text.
        bytes_with_bad_byte = b"{\\rtf1\\ansi\\deff0 hello\xff world}"
        result = extract_rtf_text("bad-encoding.rtf", bytes_with_bad_byte)
        assert "[RTF DOCUMENT EXTRACTED]" in result
        assert "hello" in result


class TestReadDocumentRtf:
    def test_read_document_handles_rtf_file(self, tmp_path):
        from litassist.utils.file_ops import read_document

        rtf_path = tmp_path / "fixture.rtf"
        rtf_path.write_bytes(_minimal_rtf("hello from local file"))

        text = read_document(str(rtf_path))
        assert "[RTF DOCUMENT EXTRACTED]" in text
        assert "hello from local file" in text

    def test_read_document_empty_rtf_raises(self, tmp_path):
        import click

        from litassist.utils.file_ops import read_document

        rtf_path = tmp_path / "empty.rtf"
        rtf_path.write_bytes(b"{\\rtf1\\ansi\\deff0 }")

        with pytest.raises(click.ClickException) as exc_info:
            read_document(str(rtf_path))
        assert "No extractable text found in RTF" in str(exc_info.value)
