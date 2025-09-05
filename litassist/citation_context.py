"""
Fetch complete legal documents for citations using CSE fallback strategy.

This module provides functionality to fetch full legal documents from AustLII
and government sources for use in Chain-of-Verification (CoVe) processes.
It implements a fallback strategy from AustLII to comprehensive government sources.
"""

from typing import Dict, List, Optional
from litassist.config import get_config
from litassist.logging_utils import save_log
from litassist.citation_verify import _citation_cache, _cache_lock, normalize_citation
import time
import re
import requests


def fetch_citation_context(
    citations: List[str]
) -> Dict[str, str]:
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
        save_log("cove_cse_init_error", {"error": str(e)})
        return context

    # Get CSE IDs
    config = get_config()
    cse_austlii = getattr(config, "cse_id_austlii", None)
    cse_comprehensive = getattr(config, "cse_id_comprehensive", None)

    for citation in citations:  # Fetch ALL citations - NO LIMITS
        # Check cache first for URL from verification
        url = None
        with _cache_lock:
            normalized = normalize_citation(citation)
            if normalized in _citation_cache:
                cached_url = _citation_cache[normalized].get("url", "")
                if cached_url:
                    url = cached_url
        
        # Determine if this is legislation or case law
        citation_lower = citation.lower()
        is_legislation = any(term in citation_lower for term in [
            'act', 'regulation', 'regulations', 'code', 'rules', 
            'ordinance', 'statute', '(cth)', '(qld)', '(nsw)', '(vic)',
            '(sa)', '(wa)', '(tas)', '(act)', '(nt)'
        ])
        
        # STRATEGY: Legislation -> Gov sites first, Case law -> AustLII first
        if not url:
            if is_legislation and cse_comprehensive:
                # Try government sites FIRST for legislation
                try:
                    res = service.cse().list(q=citation, cx=cse_comprehensive, num=5).execute()
                    if "items" in res:
                        for item in res["items"]:
                            link = item.get("link", "")
                            # Prefer government sources for legislation
                            if ".gov.au" in link:
                                url = link
                                save_log("cove_found_gov_source", {
                                    "citation": citation,
                                    "url": url,
                                    "source": "comprehensive_cse"
                                })
                                break
                except Exception as e:
                    save_log(
                        "cove_comprehensive_search_error",
                        {"citation": citation, "error": str(e)},
                    )
                
                # Fallback to AustLII if no gov source found
                if not url and cse_austlii:
                    try:
                        res = service.cse().list(q=citation, cx=cse_austlii, num=5).execute()
                        if "items" in res:
                            for item in res["items"]:
                                link = item.get("link", "")
                                if "/au/legis/" in link:
                                    url = link
                                    save_log("cove_fallback_austlii", {
                                        "citation": citation,
                                        "url": url,
                                        "reason": "no_gov_source"
                                    })
                                    break
                    except Exception as e:
                        save_log(
                            "cove_austlii_search_error", {"citation": citation, "error": str(e)}
                        )
            else:
                # Case law - try AustLII FIRST
                if cse_austlii:
                    try:
                        res = service.cse().list(q=citation, cx=cse_austlii, num=5).execute()
                        if "items" in res:
                            for item in res["items"]:
                                link = item.get("link", "")
                                if "/au/cases/" in link:
                                    url = link
                                    save_log("cove_found_austlii_case", {
                                        "citation": citation,
                                        "url": url
                                    })
                                    break
                    except Exception as e:
                        save_log(
                            "cove_austlii_search_error", {"citation": citation, "error": str(e)}
                        )
                
                # Fallback to comprehensive for case law
                if not url and cse_comprehensive:
                    try:
                        res = service.cse().list(q=citation, cx=cse_comprehensive, num=5).execute()
                        if "items" in res:
                            for item in res["items"]:
                                link = item.get("link", "")
                                # Accept any non-jade.io source
                                if ".gov.au" in link or "austlii.edu.au" in link:
                                    url = link
                                    save_log("cove_fallback_comprehensive_case", {
                                        "citation": citation,
                                        "url": url
                                    })
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
