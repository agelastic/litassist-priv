"""
Unorthodox strategy generation for brainstorm command.

Generates creative and unconventional legal strategies with automatic verification.
"""

import click
import logging
import re

from litassist.llm.factory import LLMClientFactory
from litassist.utils.legal_reasoning import create_reasoning_prompt
from litassist.utils.formatting import (
    verifying_message,
    success_message,
    warning_message,
)
from litassist.prompts import PROMPTS
from litassist.logging import log_task_event


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
        unorthodox_content, unorthodox_usage = unorthodox_client.complete(
            unorthodox_messages
        )
    except Exception as e:
        raise click.ClickException(f"Error generating unorthodox strategies: {str(e)}")

    # Verify the unorthodox strategies for legal accuracy
    try:
        log_task_event(
            "brainstorm",
            "unorthodox-verify",
            "start",
            "Verifying unorthodox strategies",
        )
    except Exception:
        pass
    click.echo(verifying_message("Verifying unorthodox strategies..."))
    verify_client = LLMClientFactory.for_command("verification")
    verification_result, _ = verify_client.verify(unorthodox_content)

    # Try to extract just the verified document part
    match = re.search(
        r"## Verified and Corrected Document\s*\n(.*)", verification_result, re.DOTALL
    )

    if match:
        # Successfully extracted the verified document section
        verified_content = match.group(1).strip()
        unorthodox_content = verified_content
        click.echo(success_message("Unorthodox strategies verified"))
    else:
        # Could not find expected format - log error and use whole output
        logging.error(
            "Unexpected verification format - expected '## Verified and Corrected Document' header"
        )
        # Use the whole verification result as-is
        unorthodox_content = verification_result
        click.echo(
            warning_message("Verification format unexpected - using complete output")
        )
    try:
        log_task_event(
            "brainstorm", "unorthodox-verify", "end", "Unorthodox verification complete"
        )
    except Exception:
        pass

    # Validate citations
    try:
        log_task_event(
            "brainstorm",
            "unorthodox-citations",
            "start",
            "Validating citations in unorthodox strategies",
        )
    except Exception:
        pass
    unorthodox_citation_issues = unorthodox_client.validate_citations(
        unorthodox_content
    )
    try:
        log_task_event(
            "brainstorm",
            "unorthodox-citations",
            "end",
            "Unorthodox citation validation complete",
            {
                "issues": (
                    len(unorthodox_citation_issues) if unorthodox_citation_issues else 0
                )
            },
        )
    except Exception:
        pass

    return unorthodox_content, unorthodox_usage, unorthodox_citation_issues
