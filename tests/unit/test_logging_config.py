"""Tests for logging configuration.

Guards that setup_logging keeps chatty third-party libraries out of litassist's
DEBUG file handler. pdfminer logs per token while parsing PDFs; leaving it at the
root DEBUG level both bloats the audit log and opens a reentrancy window where a
GC-finalised OpenAI/httpx client logging from __del__ during a pdfminer flush
raises "RuntimeError: reentrant call inside BufferedWriter".
"""

import logging

import pytest

from litassist.logging.config import setup_logging

_NOISY = ("pdfminer", "pdfplumber", "httpx", "httpcore", "openai", "urllib3")


@pytest.fixture
def restore_root_logging():
    """setup_logging mutates the global root logger; save and restore around the test."""
    root = logging.getLogger()
    saved_handlers = root.handlers[:]
    saved_level = root.level
    saved_levels = {name: logging.getLogger(name).level for name in _NOISY}
    try:
        yield
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)
        for name, lvl in saved_levels.items():
            logging.getLogger(name).setLevel(lvl)


def test_setup_logging_silences_noisy_third_party_loggers(tmp_path, restore_root_logging):
    setup_logging(log_dir=str(tmp_path))
    for name in _NOISY:
        assert logging.getLogger(name).getEffectiveLevel() >= logging.WARNING, (
            f"{name} must be >= WARNING so its DEBUG output never reaches "
            "litassist's log file (prevents the pdfminer reentrant-flush crash)"
        )
