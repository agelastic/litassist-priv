"""
Google Custom Search Engine citation verification.

This module provides functions for verifying citations using Google Custom Search
Engine to search legal databases like Jade.io and AustLII.
"""

import re
import time

from litassist.logging import save_log
from litassist.config import get_config


def search_legal_database_via_cse(
    citation: str, cse_id: str = None, cse_name: str = "Jade.io", timeout: int = 10
) -> bool:
    """
    Search legal databases for a citation using Google Custom Search Engine.

    Args:
        citation: The citation to search for
        cse_id: The CSE ID to use (if None, uses default Jade CSE)
        cse_name: Name of the CSE for logging (e.g., "Jade.io", "Comprehensive", "AustLII")
        timeout: Request timeout in seconds

    Returns:
        True if citation is found in search results via Google CSE
    """
    start_time = time.time()

    try:
        from googleapiclient.discovery import build

        config = get_config()

        # Use specified CSE or default to Jade CSE
        if cse_id is None:
            cse_id = config.cse_id

        # Use Google Custom Search to search legal databases
        service = build(
            "customsearch", "v1", developerKey=config.g_key, cache_discovery=False
        )

        # Format citation for search - clean format for better matching
        search_query = (
            citation.replace("(", "").replace(")", "").replace("[", "").replace("]", "")
        )

        # Search using specified CSE
        res = service.cse().list(q=search_query, cx=cse_id, num=10).execute()

        # Enhanced search with multiple variations to handle different citation formats
        success = False
        found_url = ""
        if "items" in res:
            # Create multiple search variations for better matching
            base_citation = (
                citation.replace("(", "")
                .replace(")", "")
                .replace("[", "")
                .replace("]", "")
            )
            citation_variations = [
                citation.lower(),  # Original format
                base_citation.lower(),  # Clean version
                citation.replace("[", "(")
                .replace("]", ")")
                .lower(),  # Convert brackets to parentheses
                citation.replace("(", "[")
                .replace(")", "]")
                .lower(),  # Convert parentheses to brackets
            ]

            # Extract components for flexible matching
            year_match = re.search(r"(\d{4})", citation)
            volume_match = re.search(
                r"\)\s*(\d+)\s+([A-Z]+)\s+(\d+)", citation
            )  # For (year) vol series page

            for item in res["items"]:
                title = item.get("title", "").lower()
                snippet = item.get("snippet", "").lower()
                link = item.get("link", "").lower()
                combined_text = f"{title} {snippet} {link}"

                # Check for exact citation match in any variation
                for variation in citation_variations:
                    if variation in combined_text:
                        success = True
                        found_url = item.get("link", "")
                        break

                if success:
                    break

                # For traditional citations, check if we can find the key components
                if year_match and volume_match:
                    year = year_match.group(1)
                    series = volume_match.group(2).lower()
                    page = volume_match.group(3)

                    # Check if year, series, and page all appear in the result
                    if (
                        year in combined_text
                        and series in combined_text
                        and page in combined_text
                    ):
                        success = True
                        found_url = item.get("link", "")
                        break

    except Exception:
        success = False

    # Log the search attempt with URL
    save_log(
        "google_cse_validation",
        {
            "method": "search_legal_database_via_cse",
            "cse_name": cse_name,
            "cse_id": cse_id,
            "citation": citation,
            "success": success,
            "url": found_url if found_url else None,
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "timeout": timeout,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )

    return (success, found_url)


def search_jade_via_google_cse(citation: str, timeout: int = 10) -> bool:
    """
    Backward compatibility wrapper for search_legal_database_via_cse.

    Args:
        citation: The citation to search for
        timeout: Request timeout in seconds

    Returns:
        True if citation is found in Jade search results via Google CSE
    """
    success, url = search_legal_database_via_cse(
        citation, cse_id=None, cse_name="Jade.io", timeout=timeout
    )
    return success
