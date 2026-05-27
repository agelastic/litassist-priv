"""
RTF (Rich Text Format) text extraction.

AustLII serves some judgments as .rtf files and users sometimes hand in
local .rtf documents. Without extraction, raw RTF control codes
({\\rtf1\\ansi\\deff0...}) flow into LLM prompts as gibberish.

This helper lives in utils/ so both read_document (local files) and the
lookup fetcher (URL responses) can use it without creating a utils -> commands
import dependency.
"""

import logging
import time

from litassist.logging import save_log


RTF_MAGIC_BYTES = b"{\\rtf"


def looks_like_rtf(content: bytes) -> bool:
    """Return True if the byte sequence begins with the RTF magic marker."""
    return content.startswith(RTF_MAGIC_BYTES)


def extract_rtf_text(source: str, rtf_bytes: bytes) -> str:
    """
    Extract plain text from RTF bytes.

    Returns marked-up text on success, an annotated placeholder on extraction
    failure, or an empty string when the body has no extractable content.
    The `source` argument is a URL or file path used only for audit logs and
    extraction headers.
    """
    try:
        from striprtf.striprtf import rtf_to_text
    except ImportError:
        logging.warning("striprtf not installed - cannot extract RTF text")
        return (
            f"[RTF DOCUMENT at {source}]\n"
            "[Note: RTF text extraction unavailable - striprtf not installed]\n"
        )

    try:
        rtf_str = rtf_bytes.decode("utf-8", errors="replace")
        text = rtf_to_text(rtf_str)
    except Exception as e:
        logging.warning(f"Failed to extract text from RTF {source}: {e}")
        save_log(
            "fetch_attempt",
            {
                "url": source,
                "method": "rtf",
                "status": "failed",
                "error": str(e)[:200],
                "timestamp": time.time(),
            },
        )
        return (
            f"[RTF DOCUMENT at {source}]\n"
            f"[Note: RTF extraction failed - {str(e)[:100]}]\n"
        )

    if not text or not text.strip():
        logging.info(f"RTF has no extractable text: {source}")
        save_log(
            "fetch_attempt",
            {
                "url": source,
                "method": "rtf",
                "status": "skipped",
                "reason": "RTF has no extractable text",
                "content": "",
                "timestamp": time.time(),
            },
        )
        return ""

    header = (
        f"[RTF DOCUMENT EXTRACTED]\n"
        f"[Source: {source}]\n"
        f"{'=' * 80}\n"
    )
    rtf_content = header + text + "\n" + "=" * 80 + "\n[END OF RTF]"

    save_log(
        "fetch_attempt",
        {
            "url": source,
            "method": "rtf",
            "status": "success",
            "rtf_bytes": len(rtf_bytes),
            "extracted_size": len(text),
            "final_size": len(rtf_content),
            "content": rtf_content,
            "timestamp": time.time(),
        },
    )
    return rtf_content
