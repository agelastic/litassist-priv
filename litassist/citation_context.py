"""
Fetch complete legal documents for citations using CSE fallback strategy.

This module provides functionality to fetch full legal documents from AustLII
and government sources for use in Chain-of-Verification (CoVe) processes.
It implements a fallback strategy from AustLII to comprehensive government sources.
"""

from typing import Callable, Dict, List, Optional
from litassist.config import get_config
from litassist.logging import save_log
from litassist.citation.cache import (
    _citation_cache,
    _cache_lock,
)
from litassist.citation.legislation import normalize_citation
from litassist.citation.austlii import (
    construct_austlii_url,
    is_traditional_citation_format,
    resolve_neutral_from_parallel,
)
from litassist.citation.trust import is_trusted_legal_host
import time
import re
import random
import click
from litassist.utils.formatting import success_message, error_message

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

# Jurisdiction parenthetical in an act citation -> (AustLII /au/legis/ path
# segment, jurisdiction prose as it appears on AustLII act-page headers,
# e.g. "New South Wales Consolidated Acts"). Used to scope the AustLII CSE
# link filter and the legislation validation strategy: without this the WA
# Civil Liability Act was fetched and (correctly) rejected for an (NSW)
# citation, while the correct NSW page could never validate because act
# pages head with the bare title, never the "(NSW)" literal.
LEGISLATION_JURISDICTIONS = {
    "(cth)": ("cth", "commonwealth"),
    "(nsw)": ("nsw", "new south wales"),
    "(vic)": ("vic", "victoria"),
    "(qld)": ("qld", "queensland"),
    "(sa)": ("sa", "south australia"),
    "(wa)": ("wa", "western australia"),
    "(tas)": ("tas", "tasmania"),
    "(act)": ("act", "australian capital territory"),
    "(nt)": ("nt", "northern territory"),
}


def _jurisdiction_markers(lower_citation: str) -> list:
    """Jurisdiction markers present in a lowercased citation. "(act)" is the
    only jurisdiction token that also occurs inside act NAMES ("Civil Law
    (ACT) Act 2000 (NSW)"), so when any other marker co-occurs, "(act)"
    belongs to the name and is dropped from the marker list."""
    markers = [m for m in LEGISLATION_JURISDICTIONS if m in lower_citation]
    if "(act)" in markers and len(markers) > 1:
        markers.remove("(act)")
    return markers


def _parse_legislation_jurisdiction(citation: str):
    """Return (austlii_path_segment, header_prose_name) for the jurisdiction
    parenthetical in an act citation, or None when no marker is present
    (case citations and bare titles)."""
    markers = _jurisdiction_markers(citation.lower())
    if markers:
        return LEGISLATION_JURISDICTIONS[markers[0]]
    return None


def _legislation_austlii_link_ok(link: str, jurisdiction) -> bool:
    """Link filter for the AustLII legislation CSE step. When the citation
    names a jurisdiction, only that jurisdiction's /au/legis/ subtree is
    accepted; otherwise the generic legislation-path check applies."""
    if not is_trusted_legal_host(link):
        return False
    if jurisdiction:
        return f"/au/legis/{jurisdiction[0]}/" in link
    return "/au/legis/" in link


def _instrument_title(citation: str) -> str:
    """Lowercased instrument title with ONLY the jurisdiction parenthetical
    removed. Name parentheticals ("Civil Law (Wrongs) Act 2002") are kept
    so titles match AustLII headers verbatim and two acts whose names
    differ only by parenthetical can never collapse to the same string.
    A NAME parenthetical of "(ACT)" is kept whenever another jurisdiction
    marker is present (see _jurisdiction_markers). Known limitation (Codex
    review 11/06/2026, narrowed 12/06/2026): an "(ACT)"-named act of the
    ACT jurisdiction itself ("X (ACT) Act 2000 (ACT)") still has both
    occurrences stripped; no real act title with that shape has been
    observed."""
    title = citation.lower()
    for marker in _jurisdiction_markers(title):
        title = title.replace(marker, "")
    return re.sub(r"\s+", " ", title).strip()


def _legislation_title_jurisdiction_match(header: str, citation: str) -> bool:
    """Legislation-aware validation: AustLII act pages head with the bare
    title ("CIVIL LIABILITY ACT 2002") and name the jurisdiction in prose
    ("New South Wales Consolidated Acts"), never the "(NSW)" literal, so
    the exact-string strategies cannot validate a whole-act citation.
    Requires BOTH the title (sans the jurisdiction parenthetical) and the
    jurisdiction marker in the header; a right-title/wrong-jurisdiction
    page still fails."""
    jurisdiction = _parse_legislation_jurisdiction(citation)
    if not jurisdiction:
        return False
    path_abbrev, prose_name = jurisdiction
    title = _instrument_title(citation)
    if not title:
        return False
    header_norm = re.sub(r"\s+", " ", header.lower())
    if title not in header_norm:
        return False
    return prose_name in header_norm or f"({path_abbrev})" in header_norm


def _component_page_for_whole_citation(header: str, citation: str) -> bool:
    """True when the header is an AustLII component page ("ACT NAME YEAR -
    SECT 5B", or SCHED/REG/RULE/CL plus an identifier) for an instrument the
    citation names as a whole. Validating an arbitrary component as the
    whole instrument overstates retrieval, so _validate_citation_match
    refuses these outright - for any strategy, with or without a
    jurisdiction parenthetical. Citations that themselves name a section
    keep the component reference inside the derived title, so the pattern
    cannot match and they are never blocked here. Only the jurisdiction
    parenthetical is stripped from the citation, so acts with parenthetical
    names ("Civil Law (Wrongs) Act 2002") match their headers verbatim."""
    title = _instrument_title(citation)
    if not title:
        return False
    header_norm = re.sub(r"\s+", " ", header.lower())
    return bool(
        re.search(
            re.escape(title) + r"\s*-\s*(sect|sched|schedule|reg|rule|cl)\b\s*\S+",
            header_norm,
        )
    )


def _try_fetch_and_validate(url: str, citation: str) -> Optional[str]:
    """
    Fetch URL content and validate it matches citation.

    Returns content if validation succeeds, None if validation fails.
    Handles all exceptions internally.

    Args:
        url: URL to fetch
        citation: Citation to validate against

    Returns:
        Validated content or None
    """
    try:
        from litassist.commands.lookup.fetchers import (
            _fetch_url_content,
            PendingOcrContent,
        )

        content = _fetch_url_content(url, timeout=15)
        # PendingOcrContent is an async OCR future from the lookup pipeline;
        # synchronous citation validation cannot await it, so treat as miss.
        if isinstance(content, PendingOcrContent):
            save_log(
                "citation_fetch_pending_ocr_skipped",
                {"url": url, "citation": citation},
            )
            return None
        if content and _validate_citation_match(content, citation):
            return content
        else:
            # Validation failed
            save_log(
                "citation_validation_failed",
                {"url": url, "citation": citation, "reason": "Content validation failed"},
            )
            return None
    except Exception as e:
        # Fetch failed - log for security audit trail
        save_log(
            "citation_fetch_exception",
            {
                "url": url,
                "citation": citation,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return None


def _search_and_validate(
    service,
    cse_id: str,
    query: str,
    citation: str,
    link_filter_func: Callable[[str], bool],
    log_name: str,
    success_msg_template: str,
    apply_rate_limit: bool = False,
) -> tuple[Optional[str], bool, Optional[str]]:
    """
    Execute CSE search and validate results.

    Performs a Google Custom Search, iterates through top results, filters
    links using provided function, and validates content against citation.

    Args:
        service: Google CSE service instance
        cse_id: Custom Search Engine ID
        query: Search query string
        citation: Citation being searched for
        link_filter_func: Function that returns True if link should be processed
        log_name: Name for success log event (e.g., "citation_pdf_validated")
        success_msg_template: Template for success message (use {rank} and {url} placeholders)
        apply_rate_limit: Whether to apply AustLII rate limiting (2-3 second delay)

    Returns:
        Tuple of (url, content_valid, content):
        - url: URL of validated content, or None if no valid content found
        - content_valid: True if validation succeeded, False otherwise
        - content: Fetched content if valid, None otherwise
    """
    global _last_austlii_completion

    # Apply rate limiting if requested (for AustLII searches)
    if apply_rate_limit:
        time_since_last = time.time() - _last_austlii_completion
        if time_since_last < 2.0:
            delay = random.uniform(2.0, 3.0) - time_since_last
            if delay > 0:
                time.sleep(delay)

    try:
        results = service.cse().list(q=query, cx=cse_id, num=5).execute()
        if "items" not in results:
            return None, False, None

        # Track the last link we actually fetch-attempted, so the caller can tell
        # "CSE returned nothing" apart from "fetched a document but it failed
        # validation". Stays None if no result passed the filter.
        attempted_link = None
        # Process top 3 results
        for result_rank, item in enumerate(results["items"][:3], start=1):
            link = item.get("link", "")

            # Apply link filter
            if not link_filter_func(link):
                continue

            # Try to fetch and validate
            attempted_link = link
            content = _try_fetch_and_validate(link, citation)
            if content:
                # Success - log and return
                save_log(
                    log_name,
                    {
                        "citation": citation,
                        "url": link,
                        "result_rank": result_rank,
                        "source_length": len(content),
                    },
                )
                click.echo(success_message(success_msg_template.format(rank=result_rank, url=link)))

                # Update rate limit timestamp if applicable
                if apply_rate_limit:
                    _last_austlii_completion = time.time()

                return link, True, content

        # Update rate limit timestamp even if no valid content found
        if apply_rate_limit:
            _last_austlii_completion = time.time()

        # If we fetched a document (attempted_link set) it just failed validation;
        # return the URL so the caller reports a validation failure, not a missing
        # URL. attempted_link is None when no result passed the filter.
        return attempted_link, False, None

    except Exception as e:
        save_log(
            "citation_cse_search_error",
            {
                "citation": citation,
                "cse_id": cse_id,
                "query": query,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        # Update rate limit timestamp to prevent rapid retries on errors
        if apply_rate_limit:
            _last_austlii_completion = time.time()
        return None, False, None


def fetch_citation_context(
    citations: List[str], source_text: Optional[str] = None
) -> tuple[Dict[str, str], List[tuple[str, str]]]:
    """
    Fetch COMPLETE legal documents for citations with smart source prioritization.

    Strategy:
    - LEGISLATION (Acts, Regulations, etc): Prefer government sites via Comprehensive CSE
      (they have full text in HTML/PDF), fallback to AustLII
    - CASE LAW: Prefer AustLII first (better structured), fallback to Comprehensive CSE
    - Skip Jade.io results (blocked by scrapers)

    Args:
        citations: List of citations to fetch
        source_text: optional raw document the citations were extracted from. When
            given, an authorised-report cite (e.g. "(1999) 201 CLR 1") that has no
            constructible AustLII URL is resolved to a medium-neutral cite printed
            parallel to it in source_text (C2 option 1), enabling the direct-AustLII
            fallback. Omitted/None preserves the prior behaviour exactly.

    Returns:
        Tuple of (successful_fetches, failed_citations):
        - successful_fetches: Dict mapping citations to FULL document text
        - failed_citations: List of (citation, reason) tuples for failures
    """
    context = {}
    failures = []

    if not citations:
        return context, failures

    # Build service once
    try:
        # Lazy import to avoid loading googleapiclient when not needed
        from googleapiclient.discovery import build

        service = build(
            "customsearch", "v1", developerKey=get_config().g_key, cache_discovery=False
        )
    except Exception as e:
        save_log("citation_cse_init_error", {"error": str(e)})
        # CSE initialization failed - all citations fail
        failures = [(cit, "CSE initialization failed") for cit in citations]
        return context, failures

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
                click.echo(f"  -> Using hardcoded URL for {citation}")
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
        content_valid = False  # Track if we successfully validated content
        content = None  # Track fetched content
        if not url:
            if is_legislation:
                # STEP 1: Try PDF search FIRST (most likely to have complete document)
                if cse_comprehensive:
                    found, content_valid, content = _search_and_validate(
                        service,
                        cse_comprehensive,
                        f"{citation} PDF",
                        citation,
                        lambda link: is_trusted_legal_host(link) and (".pdf" in link.lower() or "/PDF/" in link),
                        "citation_pdf_validated",
                        "Validated PDF (rank {rank}/3): {url}",
                        apply_rate_limit=False,
                    )
                    # Preserve any URL actually fetched; a later empty fallback
                    # search returns None and must not erase it.
                    url = found or url

                # STEP 2: Try AustLII if no valid content found yet
                if not content_valid and cse_austlii:
                    jurisdiction = _parse_legislation_jurisdiction(citation)
                    found, content_valid, content = _search_and_validate(
                        service,
                        cse_austlii,
                        normalize_citation(citation),
                        citation,
                        lambda link, _j=jurisdiction: _legislation_austlii_link_ok(link, _j),
                        "citation_austlii_legis_validated",
                        "Validated AustLII legis (rank {rank}/3): {url}",
                        apply_rate_limit=True,
                    )
                    url = found or url

                # STEP 3: Try plain comprehensive CSE as final fallback
                if not content_valid and cse_comprehensive:
                    found, content_valid, content = _search_and_validate(
                        service,
                        cse_comprehensive,
                        normalize_citation(citation),
                        citation,
                        lambda link: is_trusted_legal_host(link),
                        "citation_comprehensive_legis_validated",
                        "Validated comprehensive legis (rank {rank}/3): {url}",
                        apply_rate_limit=False,
                    )
                    url = found or url
            else:
                # Case law - try AustLII FIRST
                if cse_austlii:
                    found, content_valid, content = _search_and_validate(
                        service,
                        cse_austlii,
                        normalize_citation(citation),
                        citation,
                        lambda link: is_trusted_legal_host(link) and "/au/cases/" in link,
                        "citation_austlii_case_validated",
                        "Validated AustLII case (rank {rank}/3): {url}",
                        apply_rate_limit=True,
                    )
                    url = found or url

                # Fallback to comprehensive for case law
                if not content_valid and cse_comprehensive:
                    found, content_valid, content = _search_and_validate(
                        service,
                        cse_comprehensive,
                        normalize_citation(citation),
                        citation,
                        lambda link: is_trusted_legal_host(link),
                        "citation_comprehensive_case_validated",
                        "Validated comprehensive case (rank {rank}/3): {url}",
                        apply_rate_limit=False,
                    )
                    url = found or url

        # Content already fetched and validated in CSE loops above
        # If still no valid content, try direct AustLII URL construction as final fallback (case law only)
        if not content_valid and not is_legislation:
            austlii_url = construct_austlii_url(citation)
            # The page we fetch is identified by whatever cite built the URL, so that
            # is the cite we validate the fetched page against (default: the original).
            validate_cite = citation
            # C2 option 1: an authorised-report cite (e.g. "(1999) 201 CLR 1") has no
            # neutral form to build a URL from. If the source document prints the
            # parallel medium-neutral cite nearby, recover it and build the URL from
            # that. The fetched page is the NEUTRAL cite's page (AustLII prints the
            # report cite bare, e.g. "[1999] HCA 66; 201 CLR 1", so the parenthesised
            # "(1999) 201 CLR 1" never appears verbatim) - so validate against the
            # neutral cite, then map the document back to the original citation key.
            if not austlii_url and source_text and is_traditional_citation_format(citation):
                neutral_cite = resolve_neutral_from_parallel(citation, source_text)
                if neutral_cite:
                    austlii_url = construct_austlii_url(neutral_cite)
                    if austlii_url:
                        validate_cite = neutral_cite
                        save_log(
                            "citation_neutral_resolved_from_parallel",
                            {
                                "citation": citation,
                                "neutral_cite": neutral_cite,
                                "url": austlii_url,
                            },
                        )
            if austlii_url:
                click.echo("  -> Trying direct AustLII URL")
                content = _try_fetch_and_validate(austlii_url, validate_cite)
                if content:
                    url = austlii_url
                    content_valid = True
                    click.echo(success_message("Validated via direct AustLII URL"))
                    save_log(
                        "citation_austlii_direct_success",
                        {"citation": citation, "url": austlii_url},
                    )

        # Process content if we got valid content
        if content_valid and url and content:
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
            click.echo(success_message(f"Fetched {len(context[citation])} chars"))
            save_log(
                "citation_document_fetched",
                {
                    "citation": citation,
                    "url": url,
                    "size_chars": len(context[citation]),
                },
            )
        else:
            click.echo(error_message(f"No valid content found for {citation}"))
            # Determine more specific failure reason
            if not url and not austlii_url:
                reason = "URL not found - CSE returned no results"
            elif url and not content_valid:
                reason = "Document fetch or content validation failed"
            else:
                reason = "All retrieval strategies failed"

            save_log(
                "citation_no_valid_content",
                {
                    "citation": citation,
                    "tried_cse": bool(url),
                    "tried_austlii": bool(austlii_url),
                    "reason": reason,
                },
            )
            # Track failure if not already tracked
            if not any(cit == citation for cit, _ in failures):
                failures.append((citation, reason))

        # Rate limiting between searches
        time.sleep(0.5)

    return context, failures


def _clean_document(text: str) -> str:
    """
    Remove only true garbage from end of document.
    Keep all substantive legal content.
    """
    # Remove common website footer patterns
    garbage_patterns = [
        r"\n+(?:Copyright|\xa9).*?(?:All rights reserved|$).*$",
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


def _extract_metadata_header(content: str) -> str:
    """
    Extract only metadata header before judgment/catchwords begins.
    Alternative citations appear here, NOT in judgment body.

    Returns the header section (up to 1000 chars) before judgment text starts.
    """
    judgment_markers = [
        r'\n\s*(?:JUDGMENT|REASONS FOR JUDGMENT|REASONS|DECISION)\s*\n',
        r'\n\s*(?:CATCHWORDS|HEADNOTE)\s*\n',
        r'\n\s*\[\d+\]\s+',  # Paragraph [1], [2]
        r'\n[A-Z\s]{10,}:\s*\n',  # Headers like "JUDGE:" "FACTS:"
    ]

    earliest_pos = len(content)
    for marker in judgment_markers:
        match = re.search(marker, content[:2000], re.IGNORECASE | re.MULTILINE)
        if match:
            earliest_pos = min(earliest_pos, match.start())

    return content[:min(earliest_pos, 1000)]


def _check_alternative_citations_section(header: str, citation: str) -> bool:
    """
    Search for alternative citations ONLY in metadata header.
    Generalized patterns catch: "Cite as:", "Citation:", "Reported:",
    "Alternative citation:", "Parallel citation:", etc.
    """
    heading_patterns = [
        # Matches: "cite as:", "citation:", "citations:", "alternative citation:", etc.
        r'(?:^|\n)\s*(?:\w+\s+)?cit(?:e|ation|ations?)\s*(?:\w+\s*)?:(.+?)(?:\n\n|\n\w+:)',
        # Matches: "reported:", "reported in:", "reported as:", "also reported:", etc.
        r'(?:^|\n)\s*(?:\w+\s+)?report(?:ed)?\s*(?:\w+\s*)?:(.+?)(?:\n\n|\n\w+:)',
        # Matches: "parallel citations:", "alternative citations:", etc.
        r'(?:^|\n)\s*(?:parallel|alternative)\s+(?:citation|reported).*?:(.+?)(?:\n\n|\n\w+:)',
    ]

    for pattern in heading_patterns:
        match = re.search(pattern, header, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            alt_text = match.group(1).strip()
            # Normalize and check
            normalized_cit = citation.lower().replace(" ", "").replace("[", "").replace("]", "")
            normalized_alt = alt_text.lower().replace(" ", "").replace("[", "").replace("]", "")
            if normalized_cit in normalized_alt:
                return True
    return False


def _check_header_parallel_citations(header: str, citation: str) -> bool:
    """
    Check for semicolon-separated parallel citations in header ONLY.
    Format: "[2022] HCA 34; 234 CLR 123; (2022) 96 ALJR 567"
    Semicolons indicate parallel cites, NOT judgment references.
    """
    # Pattern: multiple citations separated by semicolons
    citation_group_pattern = r'(?:[^.!?]{0,200})\[?\d{4}\]?\s+[A-Z]{2,}\s+\d+\s*(?:;[^.!?]*?\[?\d{4}\]?\s+[A-Z]{2,}\s+\d+)+'

    matches = re.finditer(citation_group_pattern, header)
    for match in matches:
        group = match.group(0)
        if ';' in group:
            normalized_cit = citation.lower().replace(" ", "").replace("[", "").replace("]", "")
            normalized_group = group.lower().replace(" ", "").replace("[", "").replace("]", "")
            if normalized_cit in normalized_group:
                # Safety check: not part of sentence ("held in", "following", etc.)
                if not any(word in group.lower() for word in ['held', 'stated', 'following', 'applying', 'see']):
                    return True
    return False


def _case_name_match(header: str, citation: str) -> bool:
    """Match by case name extracted from document header."""
    # Extract case name from header: "SMITH v JONES" or "Smith and Jones"
    patterns = [
        r'([A-Z][A-Za-z\s]+)\s+v\.?\s+([A-Z][A-Za-z\s]+)',
        r'([A-Z][A-Za-z\s]+)\s+and\s+([A-Z][A-Za-z\s]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, header[:500])
        if match:
            case_name = f"{match.group(1)} v {match.group(2)}"
            # Check if case name components appear in citation
            name_parts = [p.strip() for p in case_name.lower().split() if len(p.strip()) > 2]
            if any(part in citation.lower() for part in name_parts):
                return True
    return False


def _validate_by_components(header: str, citation: str) -> bool:
    """Validate by matching citation components in header."""
    match = re.match(r"\[(\d{4})\]\s+([A-Z]+)\s+(\d+)", citation)
    if not match:
        return False

    year, court, number = match.groups()
    header_lower = header.lower()

    # All three components must appear
    has_year = year in header_lower
    has_court = court.lower() in header_lower
    has_number = number in header_lower

    return has_year and has_court and has_number


def _validate_citation_match(content: str, citation: str) -> bool:
    """
    Conservative structure-aware validation.
    Only searches metadata header to avoid false positives from citations in judgment.

    Uses progressive fallback validation strategies:
    1. Exact match in first 500 chars (primary citation location)
    2. Alternative citations heading in metadata header
    3. Parallel citations (semicolon-separated) in header
    4. Case name matching in header
    5. Component matching (year + court + number) in header
    6. Extended search in first 2000 chars

    Returns True if citation is validated, False otherwise.
    """
    # Skip multi-line "citations" (not real citations)
    if "\n" in citation:
        return False

    # Extract metadata header once for efficiency
    header = _extract_metadata_header(content)

    # Fail closed before any strategy runs: a component page (SECT/SCHED/
    # REG/RULE/CL) must never validate a whole-instrument citation, however
    # the strategies below would match it.
    if _component_page_for_whole_citation(header, citation):
        save_log(
            "citation_validation_failure",
            {
                "citation": citation,
                "strategies_tried": ["component_page_guard"],
                "header_preview": header[:300] if header else content[:300],
            },
        )
        return False

    # Define validation strategies in order of reliability
    strategies = [
        ("exact_primary_location", lambda: citation.lower() in content[:500].lower()),
        ("legislation_title_jurisdiction_header", lambda: _legislation_title_jurisdiction_match(header, citation)),
        ("alternative_citations_header", lambda: _check_alternative_citations_section(header, citation)),
        ("parallel_citations_header", lambda: _check_header_parallel_citations(header, citation)),
        ("case_name_header", lambda: _case_name_match(header, citation)),
        ("components_header_only", lambda: _validate_by_components(header, citation)),
        ("exact_match_extended_header", lambda: citation.lower() in content[:2000].lower()),
    ]

    # Try each strategy until one succeeds
    for strategy_name, strategy_func in strategies:
        try:
            if strategy_func():
                save_log("citation_validation_success", {
                    "citation": citation,
                    "strategy": strategy_name,
                    "header_length": len(header)
                })
                return True
        except Exception as e:
            # Strategy failed, log it and try next
            save_log(
                "citation_validation_strategy_error",
                {
                    "citation": citation,
                    "strategy": strategy_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            continue

    # All strategies failed
    save_log("citation_validation_failure", {
        "citation": citation,
        "strategies_tried": [s[0] for s in strategies],
        "header_preview": header[:300] if header else content[:300]
    })
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
