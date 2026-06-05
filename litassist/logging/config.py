"""
Logging configuration for LitAssist.

Handles setup of file and console logging with appropriate formatters.
"""

import os
import time
import logging


def setup_logging(verbose: bool = False, log_dir: str = None) -> str:
    """
    Configure logging with file output and optional console output.

    Args:
        verbose: If True, enable console logging at DEBUG level
        log_dir: Directory for log files (defaults to logs/)

    Returns:
        Path to the created log file
    """
    # Use provided log_dir, else an explicit LITASSIST_LOG_DIR override (honoured
    # by save_log/save_command_output too, so a caseplan runner or test can
    # isolate a run), else the package-relative logs/ default. When the env var
    # is unset, production behaviour is unchanged.
    if log_dir is None:
        log_dir = os.environ.get("LITASSIST_LOG_DIR") or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "..", "logs"
        )

    os.makedirs(log_dir, exist_ok=True)

    # Create timestamped log file
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"litassist_{timestamp}.log")

    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set root logger level
    root_logger.setLevel(logging.DEBUG)

    # File handler - always at DEBUG level
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # Console handler - only if verbose
    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter("%(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

    # Silence chatty third-party libraries so their DEBUG/INFO does not flood
    # litassist's DEBUG file handler. pdfminer logs per token while parsing PDFs,
    # which both bloats the audit log and opens a reentrancy window: a
    # GC-finalised OpenAI/httpx client logging from __del__ during a pdfminer
    # flush triggers "RuntimeError: reentrant call inside BufferedWriter".
    # litassist's own request/response and task-event logging is unaffected (it
    # uses its own loggers, still at DEBUG).
    for noisy in ("pdfminer", "pdfplumber", "httpx", "httpcore", "openai", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return log_file
