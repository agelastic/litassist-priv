"""
Rapid case-law lookup via Jade CSE + Gemini.

This module provides backward compatibility by importing the main lookup command
from the modular implementation.
"""

from litassist.commands.lookup import lookup

__all__ = ["lookup"]
