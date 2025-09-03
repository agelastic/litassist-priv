"""
Fetch complete legal documents for citations using CSE fallback strategy.

This module provides functionality to fetch full legal documents from AustLII
and government sources for use in Chain-of-Verification (CoVe) processes.
It implements a fallback strategy from AustLII to comprehensive government sources.
"""

from typing import Dict, List, Optional
from googleapiclient.discovery import build
from litassist.config import get_config
from litassist.utils import save_log
import time
import re
import requests


def fetch_citation_context(
    citations: List[str], max_citations: int = 3
) -> Dict[str, str]:
    """
    Fetch COMPLETE legal documents for citations with multi-CSE fallback.

    Strategy:
    1. Try AustLII CSE first (if configured)
    2. Fall back to Comprehensive CSE for gov.au sources
    3. Skip Jade.io results (unscrapeable)

    Args:
        citations: List of citations to fetch
        max_citations: Maximum number to fetch (default 3 to control tokens)

    Returns:
        Dict mapping citations to FULL document text
    """
    context = {}

    if not citations:
        return context

    # Build service once
    try:
        service = build(
            "customsearch", "v1", developerKey=get_config().g_key, cache_discovery=False
        )
    except Exception as e:
        save_log("cove_cse_init_error", {"error": str(e)})
        return context

    # Get CSE IDs
    config = get_config()
    cse_austlii = getattr(config, "cse_id_austlii", None)
    cse_comprehensive = getattr(config, "cse_id_comprehensive", None)

    for citation in citations[:max_citations]:  # Limit for token management
        # Try AustLII first
        url = None

        if cse_austlii:
            try:
                res = service.cse().list(q=citation, cx=cse_austlii, num=5).execute()
                if "items" in res:
                    # Look for primary sources only
                    for item in res["items"]:
                        link = item.get("link", "")
                        if "/au/cases/" in link or "/au/legis/" in link:
                            # Test if URL works (use browser User-Agent to avoid anti-bot blocks)
                            try:
                                headers = {
                                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                                }
                                r = requests.head(
                                    link,
                                    timeout=10,
                                    allow_redirects=True,
                                    headers=headers,
                                )
                                if (
                                    r.status_code == 200 or r.status_code == 302
                                ):  # Accept redirects too
                                    url = link
                                    break
                            except Exception:
                                continue
            except Exception as e:
                save_log(
                    "cove_austlii_search_error", {"citation": citation, "error": str(e)}
                )

        # Fallback to comprehensive CSE
        if not url and cse_comprehensive:
            try:
                res = (
                    service.cse()
                    .list(q=citation, cx=cse_comprehensive, num=5)
                    .execute()
                )
                if "items" in res:
                    for item in res["items"]:
                        link = item.get("link", "")
                        # Prefer government sources
                        if ".gov.au" in link and "jade.io" not in link:
                            url = link
                            break
            except Exception as e:
                save_log(
                    "cove_comprehensive_search_error",
                    {"citation": citation, "error": str(e)},
                )

        # Fetch COMPLETE content if we found a URL
        if url:
            try:
                # Lazy import to avoid circular dependency
                from litassist.commands.lookup.fetchers import _fetch_url_content
                content = _fetch_url_content(url, timeout=15)
                if content:
                    # Clean up garbage at the end but keep full document
                    cleaned_content = _clean_document(content)

                    # For statutes with section references, extract relevant section with context
                    if "section" in citation.lower() or "s " in citation.lower():
                        section_content = _extract_section(cleaned_content, citation)
                        if section_content:
                            # Provide section WITH context (include surrounding sections)
                            context[citation] = section_content
                        else:
                            # Provide full act if section not found
                            context[citation] = cleaned_content
                    else:
                        # Provide FULL document for cases
                        context[citation] = cleaned_content

                    # Log size for monitoring
                    save_log(
                        "cove_document_fetched",
                        {
                            "citation": citation,
                            "url": url,
                            "size_chars": len(context[citation]),
                        },
                    )
            except Exception as e:
                save_log(
                    "cove_fetch_error",
                    {"citation": citation, "url": url, "error": str(e)},
                )
        else:
            save_log(
                "cove_no_url_found",
                {
                    "citation": citation,
                    "austlii_cse": bool(cse_austlii),
                    "comprehensive_cse": bool(cse_comprehensive),
                },
            )

        # Rate limiting between searches
        time.sleep(0.5)

    return context


def _clean_document(text: str) -> str:
    """
    Remove only true garbage from end of document.
    Keep all substantive legal content.
    """
    # Remove common website footer patterns
    garbage_patterns = [
        r"\n+(?:Copyright|©).*?(?:All rights reserved|$).*$",
        r"\n+(?:Privacy|Terms of use|Disclaimer|Contact us).*$",
        r"\n+Page \d+ of \d+.*$",
        r"\n+\[Home\]\[Index\]\[Search\].*$",
        r"\n+Last updated:.*$",
        r"\n+This document is available at.*$",
        r"\n+Skip to main.*$",
        r"\n+AIATSIS acknowledges.*$",
        r"\n+Federal Register of Legislation.*$",
    ]

    cleaned = text
    for pattern in garbage_patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE | re.MULTILINE)

    # Remove excessive whitespace but preserve structure
    cleaned = re.sub(r"\n{4,}", "\n\n\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)

    return cleaned.strip()


def _extract_section(text: str, citation: str) -> Optional[str]:
    """
    Extract specific section WITH surrounding context.
    Returns section plus one section before and after for context.
    """
    # Extract section number from citation
    match = re.search(r"(?:section|s\.?)\s+(\d+[A-Z]?)", citation, re.I)
    if not match:
        return None

    section_num = match.group(1)

    # Find all section boundaries in the text
    # Try multiple patterns to match different formatting styles
    section_patterns = [
        r"^(?:\d+[A-Z]?\.?\s+|\s*Section\s+\d+[A-Z]?\.?\s+)[A-Z]",  # Standard format
        r"\n(?:\d+[A-Z]?\.?\s+|\s*Section\s+\d+[A-Z]?\.?\s+)",  # Alternative format
        rf"\n{section_num}\s+[A-Z]",  # Direct section number match
        rf"\nSection\s+{section_num}\b",  # "Section X" format
    ]

    sections = []
    for pattern in section_patterns:
        sections = list(re.finditer(pattern, text, re.MULTILINE))
        if sections:
            break

    if not sections:
        # Try to find the section by simpler search
        simple_match = re.search(
            rf"\b{section_num}\b.*?(?:misleading|deceptive|conduct)",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if simple_match:
            # Extract a reasonable chunk around the match
            start = max(0, simple_match.start() - 500)
            end = min(len(text), simple_match.end() + 2000)
            return f"[Extracted: Section {section_num} area]\n\n" + text[start:end]
        return None

    # Find our target section
    target_idx = None
    for i, section_match in enumerate(sections):
        if section_num in section_match.group():
            target_idx = i
            break

    if target_idx is None:
        # Section not found in structured format
        return None

    # Extract section with context (previous and next sections)
    start_idx = max(0, target_idx - 1)
    end_idx = min(len(sections) - 1, target_idx + 1)

    # Get text bounds
    start_pos = sections[start_idx].start()
    if end_idx < len(sections) - 1:
        end_pos = sections[end_idx + 1].start()
    else:
        end_pos = len(text)

    # Extract and return with section context
    section_with_context = text[start_pos:end_pos]

    # Add header to clarify what was extracted
    header = f"[Extracted: Section {section_num} with surrounding context]\n\n"
    return header + section_with_context
