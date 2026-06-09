"""
Unorthodox strategy generation for brainstorm command.

Generates creative and unconventional legal strategies.
"""

import click
import logging

from litassist.llm.factory import LLMClientFactory
from litassist.utils.legal_reasoning import create_reasoning_prompt
from litassist.prompts import PROMPTS
from litassist.logging import log_task_event


def generate_unorthodox_strategies(
    facts: str, side: str, area: str, matter_posture: str = ""
):
    """
    Generate unorthodox legal strategies.

    Args:
        facts: Case facts content
        side: Which side (plaintiff/defendant/etc)
        area: Legal area (civil/criminal/etc)

    Returns:
        Tuple of (content, usage)
    """
    click.echo("Generating unorthodox strategies...")
    unorthodox_client = LLMClientFactory.for_command("brainstorm", "unorthodox")

    # Log model usage for future reference (no user-facing message)
    if "grok" in unorthodox_client.model.lower():
        logging.debug(f"Using {unorthodox_client.model} for unorthodox strategies")

    # Use centralized unorthodox prompt template with format instructions
    unorthodox_prompt_template = PROMPTS.get("strategies.brainstorm.unorthodox_prompt")

    # Build the complete prompt by combining template with context
    # The unorthodox_prompt contains format instructions, unorthodox_base adds facts/side/area
    facts_and_context = PROMPTS.get("strategies.brainstorm.unorthodox_base").format(
        facts=facts,
        side=side,
        area=area,
        research=""  # No research context for unorthodox strategies
    )

    # Combine the format instructions with the facts/context
    combined_content = facts_and_context + "\n\n" + unorthodox_prompt_template

    # Wrap in output format
    unorthodox_base_prompt = PROMPTS.get(
        "strategies.brainstorm.unorthodox_output_format"
    ).format(content=combined_content)

    # Add reasoning trace to unorthodox prompt
    unorthodox_prompt = create_reasoning_prompt(
        unorthodox_base_prompt, "brainstorm-unorthodox"
    )
    unorthodox_system = PROMPTS.get("commands.brainstorm.unorthodox_system")
    if matter_posture:
        unorthodox_system = matter_posture + "\n\n" + unorthodox_system
    unorthodox_messages = [
        {"role": "system", "content": unorthodox_system},
        {"role": "user", "content": unorthodox_prompt},
    ]

    # Execute the query for unorthodox strategies
    try:
        log_task_event(
            "brainstorm",
            "unorthodox",
            "llm_call",
            "Sending unorthodox strategies prompt to LLM",
            {"model": unorthodox_client.model}
        )
    except Exception:
        pass

    try:
        unorthodox_content, unorthodox_usage = unorthodox_client.complete(
            unorthodox_messages, skip_citation_verification=True
        )

        try:
            log_task_event(
                "brainstorm",
                "unorthodox",
                "llm_response",
                "Unorthodox strategies LLM response received",
                {"model": unorthodox_client.model}
            )
        except Exception:
            pass
    except Exception as e:
        raise click.ClickException(f"Error generating unorthodox strategies: {str(e)}")

    return unorthodox_content, unorthodox_usage
