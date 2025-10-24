"""
Fetch complete legal documents for citations using CSE fallback strategy.

This module provides functionality to fetch full legal documents from AustLII
and government sources for use in Chain-of-Verification (CoVe) processes.
It implements a fallback strategy from AustLII to comprehensive government sources.
"""

from typing import Dict, List, Optional
from litassist.config import get_config
from litassist.logging import save_log
from litassist.citation.cache import (
    _citation_cache,
    _cache_lock,
)
from litassist.citation.legislation import normalize_citation
from litassist.citation.austlii import construct_austlii_url
import time
import re
import random
import click

# Track last AustLII request completion time for rate limiting
_last_austlii_completion = 0

# Hardcoded URLs for specific legislation that Google searches often miss
HARDCODED_LEGISLATION_URLS = {
    # Freedom of Information Act 1982 (Cth) - often confused with FOI disclosure documents
    "Freedom of Information Act 1982": "https://www.legislation.gov.au/C2004A02562/2025-02-21/2025-02-21/text/original/pdf",
    "Freedom of Information Act 1982 (Cth)": "https://www.legislation.gov.au/C2004A02562/2025-02-21/2025-02-21/text/original/pdf",
    "FOI Act 1982": "https://www.legislation.gov.au/C2004A02562/2025-02-21/2025-02-21/text/original/pdf",
    "FOI Act 1982 (Cth)": "https://www.legislation.gov.au/C2004A02562/2025-02-21/2025-02-21/text/original/pdf",
    "Freedom of Information Act 1982 (Commonwealth)": "https://www.legislation.gov.au/C2004A02562/2025-02-21/2025-02-21/text/original/pdf",
}


def fetch_citation_context(citations: List[str]) -> Dict[str, str]:
    """
    Fetch COMPLETE legal documents for citations with smart source prioritization.

    Strategy:
    - LEGISLATION (Acts, Regulations, etc): Prefer government sites via Comprehensive CSE
      (they have full text in HTML/PDF), fallback to AustLII
    - CASE LAW: Prefer AustLII first (better structured), fallback to Comprehensive CSE
    - Skip Jade.io results (blocked by scrapers)

    Args:
        citations: List of citations to fetch

    Returns:
        Dict mapping citations to FULL document text
    """
    context = {}

    if not citations:
        return context

    # Build service once
    try:
        # Lazy import to avoid loading googleapiclient when not needed
        from googleapiclient.discovery import build

        service = build(
            "customsearch", "v1", developerKey=get_config().g_key, cache_discovery=False
        )
    except Exception as e:
        save_log("citation_cse_init_error", {"error": str(e)})
        return context

    # Get CSE IDs
    config = get_config()
    cse_austlii = getattr(config, "cse_id_austlii", None)
    cse_comprehensive = getattr(config, "cse_id_comprehensive", None)

    # Declare global at function level, not in loops
    global _last_austlii_completion

    for citation in citations:  # Fetch ALL citations - NO LIMITS
        austlii_url = None  # Initialize to ensure variable always exists
        click.echo(f"[CITATION] Fetching: {citation}")
        # Check cache first for URL from verification
        url = None
        with _cache_lock:
            normalized = normalize_citation(citation)
            if normalized in _citation_cache:
                cached_url = _citation_cache[normalized].get("url", "")
                # Skip jade.io URLs from cache - they can't be fetched
                if cached_url and "jade.io" not in cached_url.lower():
                    url = cached_url

        # Check for hardcoded URLs for specific legislation
        if not url:
            # Clean citation for matching
            clean_citation = citation.strip()
            if clean_citation in HARDCODED_LEGISLATION_URLS:
                url = HARDCODED_LEGISLATION_URLS[clean_citation]
                click.echo(f"  → Using hardcoded URL for {citation}")
                save_log(
                    "citation_hardcoded_url",
                    {
                        "citation": citation,
                        "url": url,
                        "reason": "Hardcoded URL for legislation that Google searches often miss",
                    },
                )

        # Determine if this is legislation or case law
        citation_lower = citation.lower()
        is_legislation = any(
            term in citation_lower
            for term in [
                "act",
                "regulation",
                "regulations",
                "code",
                "rules",
                "ordinance",
                "statute",
                "(cth)",
                "(qld)",
                "(nsw)",
                "(vic)",
                "(sa)",
                "(wa)",
                "(tas)",
                "(act)",
                "(nt)",
            ]
        )

        # STRATEGY: Legislation -> PDF first, AustLII second, plain CSE last. Case law -> AustLII first
        if not url:
            if is_legislation:
                # STEP 1: Try PDF search FIRST (most likely to have complete document)
                if cse_comprehensive:
                    try:
                        pdf_query = f"{citation} PDF"
                        res = (
                            service.cse()
                            .list(q=pdf_query, cx=cse_comprehensive, num=5)
                            .execute()
                        )
                        if "items" in res:
                            for item in res["items"]:
                                link = item.get("link", "")
                                # Look for PDF URLs from government sources
                                if ".gov.au" in link and (
                                    ".pdf" in link.lower() or "/PDF/" in link
                                ):
                                    url = link
                                    click.echo(f"  → Found PDF: {url}")
                                    save_log(
                                        "citation_pdf_primary",
                                        {
                                            "citation": citation,
                                            "url": url,
                                            "source": "pdf_search_primary",
                                        },
                                    )
                                    break
                    except Exception as e:
                        save_log(
                            "citation_pdf_search_error",
                            {"citation": citation, "error": str(e)},
                        )

                # STEP 2: Try AustLII if no PDF found
                if not url and cse_austlii:
                    # Rate limit AustLII searches
                    current_time = time.time()
                    if _last_austlii_completion > 0:
                        elapsed = current_time - _last_austlii_completion
                        delay = random.uniform(2.0, 3.0)
                        if elapsed < delay:
                            time.sleep(delay - elapsed)

                    try:
                        res = (
                            service.cse()
                            .list(q=citation, cx=cse_austlii, num=5)
                            .execute()
                        )
                        _last_austlii_completion = (
                            time.time()
                        )  # Update AFTER completion
                        if "items" in res:
                            for item in res["items"]:
                                link = item.get("link", "")
                                if "/au/legis/" in link:
                                    url = link
                                    click.echo(f"  → Found AustLII: {url}")
                                    save_log(
                                        "citation_austlii_secondary",
                                        {
                                            "citation": citation,
                                            "url": url,
                                            "source": "austlii_secondary",
                                        },
                                    )
                                    break
                    except Exception as e:
                        save_log(
                            "citation_austlii_search_error",
                            {"citation": citation, "error": str(e)},
                        )

                # STEP 3: Try plain comprehensive CSE as final fallback
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
                                if ".gov.au" in link:
                                    url = link
                                    click.echo(f"  → Found gov source: {url}")
                                    save_log(
                                        "citation_comprehensive_fallback",
                                        {
                                            "citation": citation,
                                            "url": url,
                                            "source": "comprehensive_fallback",
                                        },
                                    )
                                    break
                    except Exception as e:
                        save_log(
                            "citation_comprehensive_search_error",
                            {"citation": citation, "error": str(e)},
                        )
            else:
                # Case law - try AustLII FIRST
                if cse_austlii:
                    # Rate limit AustLII searches
                    current_time = time.time()
                    if _last_austlii_completion > 0:
                        elapsed = current_time - _last_austlii_completion
                        delay = random.uniform(2.0, 3.0)
                        if elapsed < delay:
                            time.sleep(delay - elapsed)

                    try:
                        res = (
                            service.cse()
                            .list(q=citation, cx=cse_austlii, num=5)
                            .execute()
                        )
                        _last_austlii_completion = (
                            time.time()
                        )  # Update AFTER completion
                        if "items" in res:
                            for item in res["items"]:
                                link = item.get("link", "")
                                if "/au/cases/" in link:
                                    url = link
                                    click.echo(f"  → Found AustLII case: {url}")
                                    save_log(
                                        "citation_found_austlii_case",
                                        {"citation": citation, "url": url},
                                    )
                                    break
                    except Exception as e:
                        save_log(
                            "citation_austlii_search_error",
                            {"citation": citation, "error": str(e)},
                        )

                # Fallback to comprehensive for case law
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
                                # Accept any non-jade.io source
                                if ".gov.au" in link or "austlii.edu.au" in link:
                                    url = link
                                    click.echo(f"  → Fallback comprehensive: {url}")
                                    save_log(
                                        "citation_fallback_comprehensive_case",
                                        {"citation": citation, "url": url},
                                    )
                                    break
                    except Exception as e:
                        save_log(
                            "citation_comprehensive_search_error",
                            {"citation": citation, "error": str(e)},
                        )

        # Fetch COMPLETE content if we found a URL
        content_valid = False
        if url:
            try:
                # Lazy import to avoid circular dependency
                from litassist.commands.lookup.fetchers import _fetch_url_content

                content = _fetch_url_content(url, timeout=15)
                if content:
                    # Validate we got the right document
                    if _validate_citation_match(content, citation):
                        content_valid = True
                    else:
                        click.echo(f"  ✗ Wrong content: doesn't match {citation}")
                        save_log(
                            "citation_content_mismatch",
                            {
                                "citation": citation,
                                "url": url,
                                "reason": "Downloaded content doesn't contain expected citation",
                            },
                        )
                        content = ""
                        url = None
            except Exception as e:
                save_log(
                    "citation_fetch_error",
                    {"citation": citation, "url": url, "error": str(e)},
                )
                content = ""

        # If no valid content yet, try direct AustLII URL construction (case law only)
        if not content_valid and not is_legislation:
            austlii_url = construct_austlii_url(citation)
            if austlii_url:
                click.echo("  → Trying direct AustLII URL")
                try:
                    from litassist.commands.lookup.fetchers import _fetch_url_content

                    content = _fetch_url_content(austlii_url, timeout=15)
                    if content and _validate_citation_match(content, citation):
                        url = austlii_url
                        content_valid = True
                        click.echo("  ✓ Found via direct AustLII URL")
                        save_log(
                            "citation_austlii_direct_success",
                            {"citation": citation, "url": austlii_url},
                        )
                except Exception as e:
                    save_log(
                        "citation_austlii_direct_error",
                        {"citation": citation, "url": austlii_url, "error": str(e)},
                    )

        # Process content if we got valid content
        if content_valid and url:
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
            click.echo(f"  ✓ Fetched {len(context[citation])} chars")
            save_log(
                "citation_document_fetched",
                {
                    "citation": citation,
                    "url": url,
                    "size_chars": len(context[citation]),
                },
            )
        else:
            click.echo(f"  ✗ No valid content found for {citation}")
            save_log(
                "citation_no_valid_content",
                {
                    "citation": citation,
                    "tried_cse": bool(url),
                    "tried_austlii": bool(austlii_url),
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


def _validate_citation_match(content: str, citation: str) -> bool:
    """
    Validate that citation/name appears prominently at document beginning.
    For both legislation and case law, the citation/name must appear in the first ~500 chars.
    """
    # Skip multi-line "citations" (not real citations)
    if "\n" in citation:
        return False

    # First 500 chars must contain the citation/name
    content_beginning = content[:500] if len(content) > 500 else content

    # Check if this is legislation (case-insensitive)
    is_legislation = any(
        term.lower() in citation.lower()
        for term in ["Act", "Regulation", "Code", "Rules", "Ordinance"]
    )

    if is_legislation:
        # Strip jurisdiction suffix for core name
        # "Freedom of Information Act 1982 (Cth)" -> "Freedom of Information Act 1982"
        core_citation = re.sub(r"\s*\([A-Za-z]+\)$", "", citation).strip()

        # Must appear at beginning (case-insensitive)
        if core_citation.lower() in content_beginning.lower():
            return True

        # Handle abbreviated citations (e.g., "FOI Act 1982")
        year_match = re.search(r"\b(19|20)\d{2}\b", citation)
        if year_match and year_match.group() in content_beginning:
            # Get first significant words
            words = re.findall(r"\b[A-Z][A-Za-z]*", citation)
            if words and any(
                word.lower() in content_beginning.lower() for word in words[:2]
            ):
                return True

        return False
    else:
        # Case law - check normalized citation
        normalized_citation = (
            citation.replace(" ", "").replace("[", "").replace("]", "")
        )
        normalized_beginning = (
            content_beginning.replace(" ", "").replace("[", "").replace("]", "")
        )

        if normalized_citation in normalized_beginning:
            return True

        # Check components for medium neutral citations
        match = re.search(r"\[(\d{4})\]\s*([A-Z]+)\s*(\d+)", citation)
        if match:
            year, court, number = match.groups()
            # All components must appear in the beginning
            if all(part in content_beginning for part in [year, court, number]):
                return True

        return False


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
