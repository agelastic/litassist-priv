"""
Formatting utilities for terminal output.

This module provides ANSI color codes and message formatting functions
for consistent terminal output throughout LitAssist.
"""


class Colors:
    """ANSI color codes for terminal output."""

    # Color codes
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def colored_message(prefix: str, message: str, color: str) -> str:
    """Format a message with colored prefix."""
    return f"{color}{prefix}{Colors.RESET} {message}"


def success_message(message: str) -> str:
    """Format a success message with green [SUCCESS] prefix."""
    return colored_message("[SUCCESS]", message, Colors.GREEN)


def warning_message(message: str) -> str:
    """Format a warning message with yellow [WARNING] prefix."""
    return colored_message("[WARNING]", message, Colors.YELLOW)


def error_message(message: str) -> str:
    """Format an error message with red [ERROR] prefix."""
    return colored_message("[ERROR]", message, Colors.RED)


def info_message(message: str) -> str:
    """Format an info message with blue [INFO] prefix."""
    return colored_message("[INFO]", message, Colors.BLUE)


def stats_message(message: str) -> str:
    """Format a stats message with cyan [STATS] prefix."""
    return colored_message("[STATS]", message, Colors.CYAN)


def tip_message(message: str) -> str:
    """Format a tip message with magenta [TIP] prefix."""
    return colored_message("[TIP]", message, Colors.MAGENTA)


def saved_message(message: str) -> str:
    """Format a saved file message with blue [SAVED] prefix."""
    return colored_message("[SAVED]", message, Colors.BLUE)


def verifying_message(message: str) -> str:
    """Format a verifying message with blue [VERIFYING] prefix."""
    return colored_message("[VERIFYING]", message, Colors.BLUE)
