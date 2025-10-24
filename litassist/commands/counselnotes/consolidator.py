"""
Analysis consolidation for counselnotes command.

Handles consolidation of multiple chunk analyses into final strategic notes.
"""

import click
from typing import List, Dict, Tuple

from litassist.prompts import PROMPTS
from litassist.utils.formatting import info_message
from litassist.logging import log_task_event


def consolidate_analyses(
    chunk_analyses: List[str],
    verify: bool,
    client
) -> Tuple[str, Dict]:
    """
    Consolidate multiple chunk analyses into final strategic notes.

    Args:
        chunk_analyses: List of analysis results from chunks
        verify: Whether to verify citations
        client: LLM client instance

    Returns:
        Tuple of (final_content, final_usage)

    Raises:
        click.ClickException: If LLM processing fails
    """
    click.echo(
        info_message(
            "Consolidating analyses into comprehensive strategic notes..."
        )
    )

    consolidated_content = "\n\n".join(
        [
            f"=== ANALYSIS FROM DOCUMENT SECTION {i + 1} ===\n{analysis}\n=== END ANALYSIS FROM DOCUMENT SECTION {i + 1} ==="
            for i, analysis in enumerate(chunk_analyses)
        ]
    )

    consolidation_prompt = PROMPTS.get(
        "processing.counselnotes.consolidation",
        chunk_analyses=consolidated_content,
        total_chunks=len(chunk_analyses),
    )

    try:
        log_task_event(
            "counselnotes",
            "consolidation",
            "llm_call",
            "Consolidating chunk analyses",
            {"model": client.model}
        )
    except Exception:
        pass

    try:
        final_content, final_usage = client.complete(
            [
                {
                    "role": "system",
                    "content": PROMPTS.get(
                        "processing.counselnotes.system_prompt"
                    ),
                },
                {"role": "user", "content": consolidation_prompt},
            ]
        )

        try:
            log_task_event(
                "counselnotes",
                "consolidation",
                "llm_response",
                "Consolidation complete",
                {"model": client.model}
            )
        except Exception:
            pass

    except Exception as e:
        raise click.ClickException(f"LLM error in consolidation: {e}")

    # Citation verification if requested
    if verify:
        citation_issues = client.validate_citations(final_content)
        if citation_issues:
            citation_warning = "--- CITATION WARNINGS ---\n"
            citation_warning += "\n".join(citation_issues)
            citation_warning += "\n" + "-" * 40 + "\n\n"
            final_content = citation_warning + final_content

    return final_content, final_usage
