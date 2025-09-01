"""
Unorthodox strategy generation for brainstorm command.

Generates creative and unconventional legal strategies with automatic verification.
"""

import click
import logging

from litassist.llm import LLMClientFactory
from litassist.utils import create_reasoning_prompt
from litassist.prompts import PROMPTS


def generate_unorthodox_strategies(facts: str, side: str, area: str):
    """
    Generate unorthodox legal strategies with automatic verification.
    
    Args:
        facts: Case facts content
        side: Which side (plaintiff/defendant/etc)
        area: Legal area (civil/criminal/etc)
    
    Returns:
        Tuple of (content, usage, citation_issues, verification_result)
    """
    click.echo("Generating unorthodox strategies...")
    unorthodox_client = LLMClientFactory.for_command("brainstorm", "unorthodox")

    # Log model usage for future reference (no user-facing message)
    if "grok" in unorthodox_client.model.lower():
        logging.debug(f"Using {unorthodox_client.model} for unorthodox strategies")

    # Use centralized unorthodox prompt template
    unorthodox_template = PROMPTS.get("strategies.brainstorm.unorthodox_prompt")
    # Build unorthodox base prompt from template
    unorthodox_base_content = PROMPTS.get("strategies.brainstorm.unorthodox_base").format(
        facts=facts,
        side=side,
        area=area,
        research=unorthodox_template
    )
    
    unorthodox_base_prompt = PROMPTS.get("strategies.brainstorm.unorthodox_output_format").format(
        content=unorthodox_base_content
    )

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
        unorthodox_content, unorthodox_usage = unorthodox_client.complete(unorthodox_messages)
    except Exception as e:
        raise click.ClickException(
            f"Error generating unorthodox strategies: {str(e)}"
        )

    # Validate citations
    unorthodox_citation_issues = unorthodox_client.validate_citations(
        unorthodox_content
    )
    
    return unorthodox_content, unorthodox_usage, unorthodox_citation_issues