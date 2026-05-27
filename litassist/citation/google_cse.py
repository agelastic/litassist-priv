"""
Google Custom Search Engine citation verification.

This module provides functions for verifying citations using Google Custom Search
Engine to search legal databases like Jade.io and AustLII.
"""

import re
import time

from litassist.logging import save_log
from litassist.config import get_config
from .trust import is_trusted_legal_host


def search_legal_database_via_cse(
    citation: str, cse_id: str = None, cse_name: str = "Jade.io", timeout: int = 10
) -> tuple[bool, str, str]:
    """
    Search legal databases for a citation using Google Custom Search Engine.

    Args:
        citation: The citation to search for
        cse_id: The CSE ID to use (if None, uses default Jade CSE)
        cse_name: Name of the CSE for logging (e.g., "Jade.io", "Comprehensive", "AustLII")
        timeout: Request timeout in seconds

    Returns:
        Tuple of (success: bool, url: str, snippet: str)
        - success: True if citation is found
        - url: URL where citation was found (empty if not found)
        - snippet: Text snippet from search result (empty if not found)
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
        found_snippet = ""
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
                raw_link = item.get("link", "")
                # Match against title + snippet only. The URL is excluded
                # because it is attacker-controllable (a CSE result on an
                # untrusted host can carry the citation tokens in its path or
                # query string and otherwise spoof a match).
                combined_text = f"{title} {snippet}"

                # Trust gate: require the result link to resolve to a known
                # authoritative legal host. Without this, a CSE hit on
                # example.invalid would verify a fabricated citation.
                if not is_trusted_legal_host(raw_link):
                    continue

                # Check for exact citation match in any variation
                for variation in citation_variations:
                    if variation in combined_text:
                        success = True
                        found_url = raw_link
                        found_snippet = item.get("snippet", "").replace("\n", " ")
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
                        found_url = raw_link
                        found_snippet = item.get("snippet", "").replace("\n", " ")
                        break

    except Exception as e:
        success = False
        found_url = ""
        found_snippet = ""
        save_log(
            "google_cse_search_error",
            {
                "citation": citation,
                "cse_name": cse_name,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )

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
            "snippet": found_snippet if found_snippet else None,
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "timeout": timeout,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )

    return (success, found_url, found_snippet)
