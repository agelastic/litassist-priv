"""
Strategic analysis processing for counselnotes command.

Handles non-extraction strategic analysis mode with single and multi-chunk processing.
"""

import click
from typing import List, Dict, Tuple

from litassist.prompts import PROMPTS
from litassist.logging import log_task_event
from litassist.utils.formatting import format_citation_warnings


def analyze_single_chunk(
    chunk: str, verify: bool, client, matter_posture: str = ""
) -> Tuple[str, Dict]:
    """
    Analyze a single document chunk.

    Args:
        chunk: Document content
        verify: Whether to verify citations
        client: LLM client instance

    Returns:
        Tuple of (content, usage)

    Raises:
        click.ClickException: If LLM processing fails
    """
    strategic_prompt = PROMPTS.get(
        "processing.counselnotes.strategic_analysis", documents=chunk
    )
    system_prompt = PROMPTS.get("processing.counselnotes.system_prompt")
    if matter_posture:
        system_prompt = matter_posture + "\n\n" + system_prompt

    try:
        log_task_event(
            "counselnotes",
            "analysis",
            "llm_call",
            "Analyzing single document",
            {"model": client.model}
        )
    except Exception:
        pass

    try:
        content, usage = client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": strategic_prompt},
            ]
        )

        try:
            log_task_event(
                "counselnotes",
                "analysis",
                "llm_response",
                "Single document analysis complete",
                {"model": client.model}
            )
        except Exception:
            pass

    except Exception as e:
        raise click.ClickException(f"LLM error in analysis: {e}")

    # Citation verification if requested
    if verify:
        citation_issues = client.validate_citations(content)
        if citation_issues:
            content = format_citation_warnings(citation_issues) + content

    return content, usage


def analyze_multiple_chunks(
    chunks: List[str], client, matter_posture: str = ""
) -> List[Tuple[str, Dict]]:
    """
    Analyze multiple document chunks separately.

    Args:
        chunks: List of document chunks
        client: LLM client instance

    Returns:
        List of (content, usage) tuples

    Raises:
        click.ClickException: If LLM processing fails
    """
    chunk_analyses = []

    system_prompt = PROMPTS.get("processing.counselnotes.system_prompt")
    if matter_posture:
        system_prompt = matter_posture + "\n\n" + system_prompt

    with click.progressbar(
        chunks, label="Analyzing document chunks"
    ) as chunks_bar:
        for idx, chunk in enumerate(chunks_bar, start=1):
            # Use chunk-specific prompt for partial analysis
            chunk_prompt = PROMPTS.get(
                "processing.counselnotes.chunk_analysis",
                documents=chunk,
                chunk_num=idx,
                total_chunks=len(chunks),
            )

            try:
                log_task_event(
                    "counselnotes",
                    "chunk_analysis",
                    "llm_call",
                    f"Analyzing chunk {idx}/{len(chunks)}",
                    {"model": client.model}
                )
            except Exception:
                pass

            try:
                content, usage = client.complete(
                    [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": chunk_prompt},
                    ]
                )

                try:
                    log_task_event(
                        "counselnotes",
                        "chunk_analysis",
                        "llm_response",
                        f"Chunk {idx}/{len(chunks)} analysis complete",
                        {"model": client.model}
                    )
                except Exception:
                    pass

            except Exception as e:
                raise click.ClickException(
                    f"LLM error in analysis chunk {idx}: {e}"
                )

            chunk_analyses.append((content, usage))

    return chunk_analyses


def process_strategic_analysis(
    chunks: List[str],
    verify: bool,
    client,
    comprehensive_log: Dict,
    matter_posture: str = "",
) -> Tuple[List[str], bool]:
    """
    Process strategic analysis mode.

    Args:
        chunks: List of document chunks
        verify: Whether to verify citations
        client: LLM client instance
        comprehensive_log: Dict to update with responses and usage

    Returns:
        Tuple of (analysis_results, needs_consolidation)

    Raises:
        click.ClickException: If LLM processing fails
    """
    if len(chunks) == 1:
        # Single chunk - process normally
        content, usage = analyze_single_chunk(
            chunks[0], verify, client, matter_posture=matter_posture
        )

        # Log response data
        comprehensive_log["responses"].append(
            {"chunk": 1, "content": content, "usage": usage}
        )

        # Accumulate usage statistics
        for key in comprehensive_log["total_usage"]:
            comprehensive_log["total_usage"][key] += usage.get(key, 0)

        return [content], False

    else:
        # Multiple chunks - need consolidation
        chunk_results = analyze_multiple_chunks(
            chunks, client, matter_posture=matter_posture
        )

        all_analyses = []

        for idx, (content, usage) in enumerate(chunk_results, start=1):
            all_analyses.append(content)

            # Log response data
            comprehensive_log["responses"].append(
                {"chunk": idx, "content": content, "usage": usage}
            )

            # Accumulate usage statistics
            for key in comprehensive_log["total_usage"]:
                comprehensive_log["total_usage"][key] += usage.get(key, 0)

        return all_analyses, True
