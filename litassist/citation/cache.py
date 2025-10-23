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


def add_to_cache(citation: str, exists: bool, url: str, reason: str) -> None:
    """
    Add a citation verification result to the cache.

    Args:
        citation: Normalized citation
        exists: Whether the citation exists
        url: URL where found (if exists)
        reason: Reason string (verification source or error message)
    """
    with _cache_lock:
        _citation_cache[citation] = {
            "exists": exists,
            "url": url,
            "reason": reason,
        }


def get_verification_stats() -> Dict:
    """
    Get statistics about citation verification cache.

    Returns:
        Dictionary with cache statistics
    """
    with _cache_lock:
        total = len(_citation_cache)
        verified = sum(1 for entry in _citation_cache.values() if entry["exists"])
        unverified = total - verified

        return {
            "total_checked": total,
            "verified": verified,
            "unverified": unverified,
            "cache_hit_rate": f"{(verified / total * 100):.1f}%" if total > 0 else "0%",
        }


def clear_verification_cache():
    """Clear the citation verification cache."""
    with _cache_lock:
        _citation_cache.clear()
