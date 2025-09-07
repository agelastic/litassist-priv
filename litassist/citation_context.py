"""
Fetch complete legal documents for citations using CSE fallback strategy.

This module provides functionality to fetch full legal documents from AustLII
and government sources for use in Chain-of-Verification (CoVe) processes.
It implements a fallback strategy from AustLII to comprehensive government sources.
"""

from typing import Dict, List, Optional
from litassist.config import get_config
from litassist.logging_utils import save_log
from litassist.citation_verify import _citation_cache, _cache_lock, normalize_citation, construct_austlii_url
import time
import re
import click


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
        click.echo(f"[CITATION] Fetching: {citation}")
        # Check cache first for URL from verification
        url = None
        with _cache_lock:
            normalized = normalize_citation(citation)
            if normalized in _citation_cache:
                cached_url = _citation_cache[normalized].get("url", "")
                # Skip jade.io URLs from cache - they can't be fetched
                if cached_url and 'jade.io' not in cached_url.lower():
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
                                click.echo(f"  → Found gov source: {url}")
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
                                    click.echo(f"  → Fallback to AustLII: {url}")
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
                                    click.echo(f"  → Found AustLII case: {url}")
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
                                    click.echo(f"  → Fallback comprehensive: {url}")
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
                        save_log("citation_content_mismatch", {
                            "citation": citation,
                            "url": url,
                            "reason": "Downloaded content doesn't contain expected citation"
                        })
                        content = ""
                        url = None
            except Exception as e:
                save_log("cove_fetch_error", {"citation": citation, "url": url, "error": str(e)})
                content = ""
        
        # If validation failed for legislation, try PDF-specific search
        if not content_valid and is_legislation and cse_comprehensive:
            click.echo(f"  → Searching for PDF version of {citation}")
            try:
                # Search with "PDF" added to query
                pdf_query = f'{citation} PDF'
                res = service.cse().list(q=pdf_query, cx=cse_comprehensive, num=5).execute()
                if "items" in res:
                    for item in res["items"]:
                        link = item.get("link", "")
                        # Prefer .pdf URLs from government sources
                        if ".gov.au" in link and (".pdf" in link.lower() or "/PDF/" in link):
                            click.echo(f"  → Found PDF: {link}")
                            try:
                                from litassist.commands.lookup.fetchers import _fetch_url_content
                                content = _fetch_url_content(link, timeout=15)
                                if content and _validate_citation_match(content, citation):
                                    url = link
                                    content_valid = True
                                    click.echo("  ✓ Valid PDF found")
                                    save_log("cove_pdf_search_success", {
                                        "citation": citation,
                                        "url": link,
                                        "source": "pdf_search"
                                    })
                                    break
                                else:
                                    click.echo("  ✗ PDF doesn't match citation")
                            except Exception as e:
                                save_log("cove_pdf_fetch_error", {
                                    "citation": citation,
                                    "url": link,
                                    "error": str(e)
                                })
            except Exception as e:
                save_log("cove_pdf_search_error", {
                    "citation": citation,
                    "error": str(e)
                })
        
        # If still no valid content and it's legislation, try AustLII
        if not content_valid and is_legislation and cse_austlii:
            click.echo(f"  → Trying AustLII for {citation}")
            try:
                res = service.cse().list(q=citation, cx=cse_austlii, num=5).execute()
                if "items" in res:
                    for item in res["items"]:
                        link = item.get("link", "")
                        if "/au/legis/" in link:
                            click.echo(f"  → Found AustLII: {link}")
                            try:
                                from litassist.commands.lookup.fetchers import _fetch_url_content
                                content = _fetch_url_content(link, timeout=15)
                                if content and _validate_citation_match(content, citation):
                                    url = link
                                    content_valid = True
                                    click.echo("  ✓ Valid AustLII content")
                                    save_log("cove_austlii_fallback_success", {
                                        "citation": citation,
                                        "url": link
                                    })
                                    break
                                else:
                                    click.echo("  ✗ AustLII content doesn't match")
                            except Exception as e:
                                save_log("cove_austlii_fetch_error", {
                                    "citation": citation,
                                    "url": link,
                                    "error": str(e)
                                })
            except Exception as e:
                save_log("cove_austlii_search_error", {
                    "citation": citation,
                    "error": str(e)
                })
        
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
                        save_log("cove_austlii_direct_success", {
                            "citation": citation,
                            "url": austlii_url
                        })
                except Exception as e:
                    save_log("cove_austlii_direct_error", {
                        "citation": citation,
                        "url": austlii_url,
                        "error": str(e)
                    })
        
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
                "cove_document_fetched",
                {
                    "citation": citation,
                    "url": url,
                    "size_chars": len(context[citation]),
                },
            )
        else:
            click.echo(f"  ✗ No valid content found for {citation}")
            save_log(
                "cove_no_valid_content",
                {
                    "citation": citation,
                    "tried_cse": bool(url),
                    "tried_austlii": bool(austlii_url) if 'austlii_url' in locals() else False,
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
    Validate that downloaded content contains the citation we searched for.
    """
    # Skip multi-line "citations" (not real citations)
    if '\n' in citation:
        return False
    
    # Check if this is legislation
    is_legislation = any(term in citation for term in ['Act', 'Regulation', 'Code', 'Rules', 'Ordinance'])
    
    if is_legislation:
        # Strip jurisdiction suffix for matching
        # "Freedom of Information Act 1982 (Cth)" -> "Freedom of Information Act 1982"
        core_citation = re.sub(r'\s*\([A-Z][a-z]+\)$', '', citation).strip()
        normalized_core = core_citation.replace(" ", "").replace("[", "").replace("]", "")
        content_start = content[:5000].replace(" ", "").replace("[", "").replace("]", "")
        
        if normalized_core in content_start:
            return True
            
        # Check for year and key terms (handles abbreviations like "FOI Act")
        year_match = re.search(r'\b(19|20)\d{2}\b', citation)
        if year_match and year_match.group() in content[:2000]:
            # Extract significant words and check if any appear
            words = re.findall(r'\b[A-Z][a-z]+', citation)
            if words and any(word in content[:2000] for word in words[:3]):
                return True
    else:
        # Existing case law validation (unchanged)
        normalized_citation = citation.replace(" ", "").replace("[", "").replace("]", "")
        content_start = content[:5000].replace(" ", "").replace("[", "").replace("]", "")
        
        if normalized_citation in content_start:
            return True
            
        # For case citations, check components separately
        match = re.search(r'\[(\d{4})\]\s*([A-Z]+)\s*(\d+)', citation)
        if match:
            year, court, number = match.groups()
            # Check if all components appear near each other
            if year in content_start and court in content_start and number in content_start:
                # Verify they're in reasonable proximity (case header)
                pattern = f"{court}.*{number}"
                if re.search(pattern, content_start[:2000]):
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
