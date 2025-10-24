"""
Extraction mode processing for counselnotes command.

Handles structured extraction of citations, principles, and checklists.
"""

import click
from typing import List, Dict

from litassist.prompts import PROMPTS
from litassist.logging import log_task_event


def process_extraction_mode(
    chunks: List[str],
    extract: str,
    verify: bool,
    client,
    comprehensive_log: Dict
) -> List[str]:
    """
    Process structured extraction mode.

    Args:
        chunks: List of document chunks to process
        extract: Extraction mode (all/citations/principles/checklist)
        verify: Whether to verify citations
        client: LLM client instance
        comprehensive_log: Dict to update with responses and usage

    Returns:
        List of extraction results

    Raises:
        click.ClickException: If LLM processing fails
    """
    extraction_results = []

    with click.progressbar(
        chunks, label="Extracting structured data"
    ) as chunks_bar:
        for idx, chunk in enumerate(chunks_bar, start=1):
            # Get extraction prompt based on mode
            extraction_prompt = PROMPTS.get(
                f"processing.counselnotes.extraction.{extract}", documents=chunk
            )

            try:
                log_task_event(
                    "counselnotes",
                    "extraction",
                    "llm_call",
                    f"Extracting {extract} from chunk {idx}/{len(chunks)}",
                    {"model": client.model}
                )
            except Exception:
                pass

            try:
                content, usage = client.complete(
                    [
                        {
                            "role": "system",
                            "content": PROMPTS.get(
                                "processing.counselnotes.system_prompt"
                            ),
                        },
                        {"role": "user", "content": extraction_prompt},
                    ]
                )

                try:
                    log_task_event(
                        "counselnotes",
                        "extraction",
                        "llm_response",
                        f"Chunk {idx}/{len(chunks)} extraction complete",
                        {"model": client.model}
                    )
                except Exception:
                    pass

            except Exception as e:
                raise click.ClickException(
                    f"LLM error in extraction chunk {idx}: {e}"
                )

            # Process this chunk's extraction (will be aggregated later)
            extraction_results.append(content)

            # Citation verification if requested
            if verify:
                citation_issues = client.validate_citations(content)
                if citation_issues:
                    click.echo(f"Citation warnings found in chunk {idx}:")
                    for issue in citation_issues:
                        click.echo(f"  - {issue}")

            # Log response data
            comprehensive_log["responses"].append(
                {
                    "chunk": idx,
                    "content": content,
                    "usage": usage,
                }
            )

            # Accumulate usage statistics
            for key in comprehensive_log["total_usage"]:
                comprehensive_log["total_usage"][key] += usage.get(key, 0)

    return extraction_results


def consolidate_extraction_results(results: List[str]) -> str:
    """
    Consolidate multiple extraction results.

    Args:
        results: List of extraction results from chunks

    Returns:
        Consolidated final content
    """
    if len(results) > 1:
        # Multiple chunks - consolidate text directly
        consolidated_text = "\n\n---\n\n".join(results)
        # Add header to indicate consolidation
        final_content = f"[Consolidated from {len(results)} document chunks]\n\n{consolidated_text}"
    else:
        # Single chunk - use as is
        final_content = (
            results[0]
            if results
            else "No extraction results."
        )

    return final_content
