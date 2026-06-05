"""Tests for logging configuration.

Guards that setup_logging keeps chatty third-party libraries out of litassist's
DEBUG file handler. pdfminer logs per token while parsing PDFs; leaving it at the
root DEBUG level both bloats the audit log and opens a reentrancy window where a
GC-finalised OpenAI/httpx client logging from __del__ during a pdfminer flush
raises "RuntimeError: reentrant call inside BufferedWriter".
"""

import logging
import os

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


def test_setup_logging_falls_back_when_log_dir_unwritable(
    monkeypatch, tmp_path, restore_root_logging
):
    """A read-only primary log dir must not crash startup.

    When litassist is installed into a read-only location and no LITASSIST_LOG_DIR
    is set, makedirs on the default dir raises PermissionError. setup_logging must
    fall back to a writable location instead of crashing the CLI on startup.
    """
    primary = tmp_path / "readonly_logs"
    monkeypatch.setenv("LITASSIST_LOG_DIR", str(primary))
    monkeypatch.chdir(tmp_path)  # so the cwd/logs fallback lands under tmp

    import litassist.logging.config as cfg

    real_makedirs = os.makedirs

    def fake_makedirs(path, *args, **kwargs):
        if os.path.realpath(path) == os.path.realpath(str(primary)):
            raise PermissionError("read-only location")
        return real_makedirs(path, *args, **kwargs)

    monkeypatch.setattr(cfg.os, "makedirs", fake_makedirs)

    log_file = setup_logging(verbose=False)  # must not raise

    assert os.path.isdir(os.path.dirname(log_file))
    assert os.path.realpath(str(primary)) != os.path.realpath(os.path.dirname(log_file))
