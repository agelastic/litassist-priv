"""
Citation verification exceptions and test utilities.

This module contains exception classes used throughout the citation verification
system, along with utilities for test mode detection.
"""

import os


class CitationVerificationError(Exception):
    """Raised when citation verification fails and output cannot proceed."""

    pass


class TestVerificationError(CitationVerificationError):
    """Raised for expected verification errors in tests - no console output."""

    def __str__(self):
        return ""


def in_test_mode():
    """Check if running in test mode."""
    return os.environ.get("LITASSIST_TEST_MODE") == "1"
