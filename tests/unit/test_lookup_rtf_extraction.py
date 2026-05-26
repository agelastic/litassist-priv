"""
Tests for RTF text extraction in litassist.utils.rtf.

Pins production-critical behaviour:
- Happy path: minimal RTF bytes extract to plain text with the standard
  wrapper headers
- Graceful degradation: missing striprtf dependency returns a placeholder
  rather than crashing
- file_ops integration: read_document handles .rtf paths
"""

from unittest.mock import patch

from litassist.utils.rtf import extract_rtf_text


def _minimal_rtf(body: str = "hello world") -> bytes:
    return ("{\\rtf1\\ansi\\deff0 " + body + "}").encode("utf-8")


class TestRtfExtraction:
    def test_minimal_rtf_extracts_text(self):
        result = extract_rtf_text("test.rtf", _minimal_rtf("hello world"))
        assert "hello world" in result
        assert "[RTF DOCUMENT EXTRACTED]" in result
        assert "[Source: test.rtf]" in result
        assert "[END OF RTF]" in result

    def test_missing_striprtf_returns_placeholder(self):
        """striprtf is an optional dependency; helper must not crash if absent."""
        with patch.dict("sys.modules", {"striprtf": None, "striprtf.striprtf": None}):
            result = extract_rtf_text("test.rtf", _minimal_rtf())
            assert "RTF DOCUMENT" in result
            assert "striprtf not installed" in result


class TestReadDocumentRtf:
    def test_read_document_handles_rtf_file(self, tmp_path):
        from litassist.utils.file_ops import read_document

        rtf_path = tmp_path / "fixture.rtf"
        rtf_path.write_bytes(_minimal_rtf("hello from local file"))

        text = read_document(str(rtf_path))
        assert "[RTF DOCUMENT EXTRACTED]" in text
        assert "hello from local file" in text
