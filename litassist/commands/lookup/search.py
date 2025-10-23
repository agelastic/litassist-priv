"""
Google Custom Search Engine functionality for the lookup command.

This module handles all CSE search operations including primary Jade.io searches,
secondary AustLII searches, and comprehensive search engine queries.
"""

import click
import warnings
import os
import logging
import time
from litassist.config import get_config
from litassist.utils.formatting import info_message
from litassist.logging import LOG_DIR, log_task_event

# Suppress Google API cache warning
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
warnings.filterwarnings("ignore", message=".*file_cache.*")


def _perform_cse_search(service, query, cse_id, limit, primary=False):
    """Perform a Google Custom Search Engine lookup and return links with snippets."""
    from googleapiclient.errors import Error as GoogleApiError

    if not cse_id:
        return [], []
    try:
        res = service.cse().list(q=query, cx=cse_id, num=limit).execute()
        items = res.get("items", [])
        links = [item.get("link") for item in items]
        snippets = []
        for item in items:
            title = item.get("title", "")
            snippet = item.get("snippet", "").replace("\n", " ")
            link = item.get("link", "")
            # Collect ALL snippets from search results
            snippets.append(f"[{title}]\n{link}\n{snippet}")
        return links, snippets
    except GoogleApiError as e:
        msg = f"CSE search failed for '{cse_id}': {e}"
        if primary:
            raise click.ClickException(msg)
        click.echo(f"Warning: {msg}")
        logging.exception(msg)
        return [], []


def perform_cse_searches(question, comprehensive, context):
    """
    Perform all configured Custom Search Engine searches.

    Args:
        question: The search query
        comprehensive: Whether to use comprehensive mode
        context: Additional context to include in comprehensive search

    Returns:
        tuple: (links, all_snippets) - combined results from all searches
    """
    # Initialize Google Custom Search service
    try:
        from googleapiclient.discovery import build

        config = get_config()
        service = build(
            "customsearch", "v1", developerKey=config.g_key, cache_discovery=False
        )
    except Exception as e:
        raise click.ClickException(f"Search initialization error: {e}")
    
    try:
        log_task_event(
            "lookup",
            "cse",
            "start",
            "Starting Custom Search Engine searches"
        )
    except Exception:
        pass

    # Collect links and snippets from configured Custom Search Engines
    links = []
    all_snippets = []  # Collect all search snippets from Google CSE

    # Determine per-source limits
    if comprehensive:
        jade_limit = austlii_limit = comp_limit = 10
    else:
        jade_limit = austlii_limit = 5

    # Primary Jade CSE search
    jade_links, jade_snippets = _perform_cse_search(
        service, question, config.cse_id, jade_limit, primary=True
    )
    links.extend(jade_links)
    all_snippets.extend(jade_snippets)
    
    try:
        log_task_event(
            "lookup",
            "cse",
            "jade_complete",
            f"Jade CSE search complete - {len(jade_links)} results"
        )
    except Exception:
        pass

    # Rate limit delay between CSE calls
    cse_delay = float(os.environ.get("CSE_RATE_LIMIT_DELAY", "1.5"))
    if cse_delay > 0 and (getattr(config, "cse_id_austlii", None) or comprehensive):
        click.echo(f"Rate limiting: waiting {cse_delay}s...")
        time.sleep(cse_delay)

    # AustLII CSE search (optional)
    austlii_links, austlii_snippets = _perform_cse_search(
        service, question, getattr(config, "cse_id_austlii", None), austlii_limit
    )
    links.extend(austlii_links)
    all_snippets.extend(austlii_snippets)
    
    try:
        log_task_event(
            "lookup",
            "cse",
            "austlii_complete",
            f"AustLII CSE search complete - {len(austlii_links)} results"
        )
    except Exception:
        pass

    # Rate limit delay before comprehensive search
    if cse_delay > 0 and comprehensive:
        click.echo(f"Rate limiting: waiting {cse_delay}s...")
        time.sleep(cse_delay)

    # Comprehensive CSE search (optional)
    if comprehensive:
        # Combine question with context for comprehensive CSE if context provided
        if context:
            click.echo(f"Comprehensive search will include context: '{context}'")
            comp_query = f"{question} {context}"
        else:
            comp_query = question

        comp_links, comp_snippets = _perform_cse_search(
            service,
            comp_query,
            getattr(config, "cse_id_comprehensive", None),
            comp_limit,
        )
        links.extend(comp_links)
        all_snippets.extend(comp_snippets)
        
        try:
            log_task_event(
                "lookup",
                "cse",
                "comprehensive_complete",
                f"Comprehensive CSE search complete - {len(comp_links)} results"
            )
        except Exception:
            pass

    # Remove duplicate and empty links while preserving order
    links = list(dict.fromkeys(filter(None, links)))

    # Save search snippets if any were collected
    if all_snippets:
        _save_search_snippets(all_snippets, question, context, comprehensive)
        click.echo(info_message(f"Saved {len(all_snippets)} search snippet(s) to logs"))

    return links, all_snippets


def _save_search_snippets(all_snippets, question, context, comprehensive):
    """Save all search snippets to a log file for reference."""
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    snippet_file = os.path.join(LOG_DIR, f"cse_snippets_{timestamp}.txt")
    with open(snippet_file, "w", encoding="utf-8") as f:
        f.write(f"Query: {question}\n")
        if context:
            f.write(f"Context: {context}\n")
        if comprehensive and context:
            f.write(f"Comprehensive CSE searched with combined: {question} {context}\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")
        f.write("GOOGLE CSE SEARCH SNIPPETS\n")
        f.write("-" * 40 + "\n\n")

        # Group snippets by domain for better organization
        snippet_by_domain = {}
        for snippet in all_snippets:
            # Extract domain from the link line in the snippet
            lines = snippet.split("\n")
            link_line = next((line for line in lines if line.startswith("http")), "")
            domain = (
                link_line.split("/")[2] if link_line and "/" in link_line else "unknown"
            )

            if domain not in snippet_by_domain:
                snippet_by_domain[domain] = []
            snippet_by_domain[domain].append(snippet)

        # Write snippets grouped by domain
        for domain in sorted(snippet_by_domain.keys()):
            f.write(f"=== {domain.upper()} ===\n\n")
            for snippet in snippet_by_domain[domain]:
                f.write(snippet + "\n\n" + "-" * 40 + "\n\n")
