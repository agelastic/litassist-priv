"""
Citation verification logic for verify command.

This module handles citation extraction, verification against legal databases,
and fetching full case content for verified citations.
"""

import os
import click
from litassist.citation.verify import verify_all_citations
from litassist.citation_patterns import extract_citations
from litassist.citation_context import fetch_citation_context
from litassist.logging import save_command_output, log_task_event
from litassist.utils.formatting import verifying_message, success_message
from .formatters import format_citation_report


def verify_citations(content: str, file: str, output: str = None) -> tuple:
    """
    Verify citations in content and fetch full case content.

    Args:
        content: Document content to verify
        file: Original file path
        output: Optional custom output filename prefix

    Returns:
        tuple: (citation_report, case_content, citation_file, verified, unverified)
    """
    click.echo(verifying_message("Starting citation verification..."))

    try:
        log_task_event(
            "verify",
            "citations",
            "start",
            "Starting citation verification"
        )
    except Exception:
        pass

    # Verify citations
    verified, unverified = verify_all_citations(content)
    citation_report = format_citation_report(
        verified, unverified, total_found=len(extract_citations(content))
    )

    # Fetch FULL case content for ALL verified citations
    case_content = {}
    if verified:
        click.echo(verifying_message(f"Fetching full content for {len(verified)} verified cases..."))

        try:
            log_task_event(
                "verify",
                "citations",
                "fetching_start",
                f"Fetching content for {len(verified)} verified cases"
            )
        except Exception:
            pass

        case_content = fetch_citation_context(verified)

        if case_content:
            click.echo(success_message(f"Fetched content for {len(case_content)} cases"))

            try:
                log_task_event(
                    "verify",
                    "citations",
                    "fetching_end",
                    f"Fetched content for {len(case_content)} cases"
                )
            except Exception:
                pass

    # Save citation report
    base_name = os.path.splitext(file)[0]
    citation_file = save_command_output(
        f"{output}_citations" if output else "verify_citations",
        citation_report,
        "" if output else os.path.basename(base_name),
        metadata={
            "Type": "Citation Verification",
            "File": file,
            "Total Citations": str(len(extract_citations(content))),
            "Verified": str(len(verified)),
            "Unverified": str(len(unverified)),
            "Status": "[VERIFIED]" if not unverified else "[WARNING]",
        },
    )

    # Display results
    status = "[VERIFIED]" if not unverified else "[WARNING]"
    click.echo(f"\n{status} Citation verification complete")
    click.echo(
        f"   - {len(verified)} citations verified, {len(unverified)} unverified"
    )
    click.echo(f"   - Details: {citation_file}")

    try:
        log_task_event(
            "verify",
            "citations",
            "end",
            f"Citation verification complete - {len(verified)} verified, {len(unverified)} unverified"
        )
    except Exception:
        pass

    return citation_report, case_content, citation_file, verified, unverified
