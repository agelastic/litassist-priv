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


def generate_unorthodox_strategies(facts: str, side: str, area: str):
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

    # Use centralized unorthodox prompt template
    unorthodox_template = PROMPTS.get("strategies.brainstorm.unorthodox_prompt")
    # Build unorthodox base prompt from template
    unorthodox_base_content = PROMPTS.get(
        "strategies.brainstorm.unorthodox_base"
    ).format(facts=facts, side=side, area=area, research=unorthodox_template)

    unorthodox_base_prompt = PROMPTS.get(
        "strategies.brainstorm.unorthodox_output_format"
    ).format(content=unorthodox_base_content)

    # Add reasoning trace to unorthodox prompt
    unorthodox_prompt = create_reasoning_prompt(
        unorthodox_base_prompt, "brainstorm-unorthodox"
    )
    unorthodox_messages = [
        {
            "role": "system",
            "content": PROMPTS.get("commands.brainstorm.unorthodox_system"),
        },
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
            unorthodox_messages
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
