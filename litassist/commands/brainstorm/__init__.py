"""
Brainstorm command module for generating legal strategies.

This module provides comprehensive legal strategy generation including
orthodox, unorthodox, and most-likely-to-succeed analysis.
"""

from .core import brainstorm
from .research_handler import analyze_research_size
from litassist.utils.file_ops import expand_glob_patterns_callback as expand_glob_patterns
from .citation_regenerator import regenerate_bad_strategies

# Import PROMPTS to make it available at module level for tests
from litassist.prompts import PROMPTS

__all__ = [
    "brainstorm",
    "analyze_research_size",
    "expand_glob_patterns",
    "regenerate_bad_strategies",
    "PROMPTS",
]
