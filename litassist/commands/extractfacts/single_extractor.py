"""
Single-chunk fact extraction for extractfacts command.

Handles direct extraction when input fits in a single chunk.
"""

import click
from typing import Dict, Tuple

from litassist.prompts import PROMPTS
from litassist.utils.legal_reasoning import create_reasoning_prompt
from litassist.logging import log_task_event


def extract_single_chunk(client, chunk: str) -> Tuple[str, Dict]:
    """
    Extract facts from a single chunk using direct approach.

    Args:
        client: LLM client for fact extraction
        chunk: Text chunk to extract facts from

    Returns:
        Tuple of (extracted_facts, usage_stats)

    Raises:
        click.ClickException: If extraction fails
    """
    # Use centralized format template
    format_instructions = PROMPTS.get_format_template("case_facts_10_heading")
    base_prompt = PROMPTS.get("analysis.extraction.base_prompt").format(
        format_instructions=format_instructions, content=chunk
    )

    # Add reasoning trace to prompt
    prompt = create_reasoning_prompt(base_prompt, "extractfacts")

    try:
        log_task_event(
            "extractfacts",
            "extraction",
            "llm_call",
            "Sending single-file extraction prompt to LLM",
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
                {"role": "user", "content": prompt},
            ]
        )

        try:
            log_task_event(
                "extractfacts",
                "extraction",
                "llm_response",
                "Single-file extraction LLM response received",
                {"model": client.model}
            )
        except Exception:
            pass

        return combined, usage

    except Exception as e:
        raise click.ClickException(f"Error extracting facts: {e}")
