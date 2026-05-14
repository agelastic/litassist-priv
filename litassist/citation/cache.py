"""
Citation verification cache management.

This module provides thread-safe caching of citation verification results
to avoid redundant API calls and improve performance.
"""

import threading
from typing import Dict, Optional

# Cache for verified citations to avoid repeated requests
_citation_cache: Dict[str, Dict] = {}
_cache_lock = threading.Lock()


def get_from_cache(citation: str) -> Optional[Dict]:
    """
    Get a citation from the cache.

    Args:
        citation: Normalized citation to look up

    Returns:
        Cached entry dict or None if not in cache
    """
    with _cache_lock:
        return _citation_cache.get(citation)


def add_to_cache(
    citation: str, exists: bool, url: str, reason: str, snippet: str = ""
) -> None:
    """
    Add a citation verification result to the cache.

    Args:
        citation: Normalized citation
        exists: Whether the citation exists
        url: URL where found (if exists)
        reason: Reason string (verification source or error message)
        snippet: Text snippet from search result (optional, from Google CSE)
    """
    with _cache_lock:
        _citation_cache[citation] = {
            "exists": exists,
            "url": url,
            "reason": reason,
            "snippet": snippet,
        }
