"""
Multi-chunk fact extraction for extractfacts command.

Handles two-stage extraction when input requires multiple chunks:
Stage 1: Extract facts from each chunk
Stage 2: Organize and synthesize into structured format
"""

import click
from typing import Dict, List, Tuple

from litassist.prompts import PROMPTS
from litassist.utils.legal_reasoning import create_reasoning_prompt
from litassist.utils.formatting import info_message
from litassist.logging import log_task_event


def extract_chunk_facts(client, chunks: List[str]) -> List[str]:
    """
    Extract facts from each chunk separately.

    Args:
        client: LLM client for fact extraction
        chunks: List of text chunks to extract from

    Returns:
        List of extracted facts (one per chunk)

    Raises:
        click.ClickException: If extraction fails
    """
    click.echo(
        info_message(
            "Processing large document in sections for comprehensive fact extraction..."
        )
    )
    accumulated_facts = []

    # First, extract relevant facts from each chunk
    with click.progressbar(chunks, label="Extracting facts from sections") as bar:
        for idx, chunk in enumerate(bar, 1):
            chunk_template = PROMPTS.get("processing.extraction.chunk_facts_prompt")
            prompt = PROMPTS.get("analysis.extraction.chunk_prompt").format(
                chunk_template=chunk_template.format(
                    chunk_num=idx, total_chunks=len(chunks)
                ),
                chunk=chunk,
            )

            try:
                log_task_event(
                    "extractfacts",
                    "extraction",
                    "llm_call",
                    f"Extracting facts from section {idx}/{len(chunks)}",
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
                                "processing.extraction.chunk_system_prompt"
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ]
                )

                try:
                    log_task_event(
                        "extractfacts",
                        "extraction",
                        "llm_response",
                        f"Section {idx}/{len(chunks)} extraction complete",
                        {"model": client.model}
                    )
                except Exception:
                    pass

            except Exception as e:
                raise click.ClickException(f"Error processing chunk {idx}: {e}")
            accumulated_facts.append(content.strip())

    return accumulated_facts


def organize_facts(client, accumulated_facts: List[str]) -> Tuple[str, Dict]:
    """
    Organize accumulated facts into structured 10-heading format.

    Args:
        client: LLM client for fact organization
        accumulated_facts: List of extracted facts from each chunk

    Returns:
        Tuple of (organized_facts, usage_stats)

    Raises:
        click.ClickException: If organization fails
    """
    # Enhanced organization phase with better synthesis
    click.echo(
        info_message("Organizing and synthesizing facts into structured format...")
    )
    # Join accumulated facts with clear === separators for each chunk
    # Add END marker after each chunk's facts
    facts_with_markers = []
    for idx, facts in enumerate(accumulated_facts, 1):
        facts_with_markers.append(
            f"=== CHUNK {idx} FACTS ===\n{facts}\n=== END CHUNK {idx} FACTS ==="
        )
    all_facts = "\n\n".join(facts_with_markers)

    # Use centralized format template for organizing
    format_instructions = PROMPTS.get_format_template("case_facts_10_heading")
    organize_template = PROMPTS.get("processing.extraction.organize_facts_prompt")
    base_organize_prompt = organize_template.format(
        format_instructions=format_instructions, all_facts=all_facts
    )

    # Add reasoning trace to organize prompt
    organize_prompt = create_reasoning_prompt(base_organize_prompt, "extractfacts")

    try:
        log_task_event(
            "extractfacts",
            "consolidation",
            "llm_call",
            "Sending consolidation prompt to LLM",
            {"model": client.model}
        )
    except Exception:
        pass

    try:
        combined, usage = client.complete(
            [
                {
                    "role": "system",
                    "content": PROMPTS.get_system_prompt("extractfacts"),
                },
                {"role": "user", "content": organize_prompt},
            ]
        )

        try:
            log_task_event(
                "extractfacts",
                "consolidation",
                "llm_response",
                "Consolidation LLM response received",
                {"model": client.model}
            )
        except Exception:
            pass

        return combined, usage

    except Exception as e:
        raise click.ClickException(f"Error organizing facts: {e}")


def extract_multi_chunk(client, chunks: List[str]) -> Tuple[str, Dict]:
    """
    Extract facts from multiple chunks using two-stage approach.

    Stage 1: Extract facts from each chunk
    Stage 2: Organize and synthesize into structured format

    Args:
        client: LLM client for fact extraction
        chunks: List of text chunks to extract from

    Returns:
        Tuple of (extracted_facts, final_usage_stats)

    Raises:
        click.ClickException: If extraction or organization fails
    """
    # Stage 1: Extract facts from each chunk
    accumulated_facts = extract_chunk_facts(client, chunks)

    # Stage 2: Organize into structured format
    combined, usage = organize_facts(client, accumulated_facts)

    return combined, usage
