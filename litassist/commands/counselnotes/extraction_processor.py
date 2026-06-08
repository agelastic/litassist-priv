"""
Extraction mode processing for counselnotes command.

Handles structured extraction of citations, principles, and checklists.
"""

import click
from typing import Dict, List, Tuple

from litassist.prompts import PROMPTS
from litassist.logging import log_task_event
from litassist.utils.formatting import format_citation_warnings


def process_extraction_mode(
    chunks: List[str],
    extract: str,
    verify: bool,
    client,
    comprehensive_log: Dict,
    matter_posture: str = "",
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

    system_prompt = PROMPTS.get("processing.counselnotes.system_prompt")
    if matter_posture:
        system_prompt = matter_posture + "\n\n" + system_prompt

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
                        {"role": "system", "content": system_prompt},
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


def consolidate_extraction_results(
    results: List[str], verify: bool, client, matter_posture: str = ""
) -> Tuple[str, Dict]:
    """
    Consolidate multiple chunk extractions into one final response via an LLM
    reduce, mirroring the analysis mode's consolidate_analyses.

    Only invoked when the input was chunked (len(results) > 1); the single-chunk
    case is returned verbatim by the caller without calling this. Merges the
    partial extractions (which already carry the correct per-mode headings) into
    one structured response rather than concatenating them.

    Args:
        results: List of per-chunk extraction results
        verify: Whether to verify citations in the consolidated output
        client: LLM client instance

    Returns:
        Tuple of (final_content, usage)

    Raises:
        click.ClickException: If LLM processing fails
    """
    consolidated_input = "\n\n".join(
        f"=== EXTRACTION FROM DOCUMENT SECTION {i + 1} ===\n{result}\n=== END EXTRACTION FROM DOCUMENT SECTION {i + 1} ==="
        for i, result in enumerate(results)
    )

    consolidation_prompt = PROMPTS.get(
        "processing.counselnotes.extraction.consolidation",
        partials=consolidated_input,
        total_chunks=len(results),
    )

    try:
        log_task_event(
            "counselnotes",
            "consolidation",
            "llm_call",
            "Consolidating chunk extractions",
            {"model": client.model},
        )
    except Exception:
        pass

    system_prompt = PROMPTS.get("processing.counselnotes.system_prompt")
    if matter_posture:
        system_prompt = matter_posture + "\n\n" + system_prompt

    try:
        final_content, final_usage = client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": consolidation_prompt},
            ]
        )

        try:
            log_task_event(
                "counselnotes",
                "consolidation",
                "llm_response",
                "Consolidation complete",
                {"model": client.model},
            )
        except Exception:
            pass

    except Exception as e:
        raise click.ClickException(f"LLM error in extraction consolidation: {e}")

    # Citation verification if requested
    if verify:
        citation_issues = client.validate_citations(final_content)
        if citation_issues:
            final_content = format_citation_warnings(citation_issues) + final_content

    return final_content, final_usage
