"""
Digest command module for mass-document processing.

This module provides functionality to process large documents by splitting
them into chunks and using LLMs to summarize or identify legal issues.
"""

from .core import digest

__all__ = ["digest"]
