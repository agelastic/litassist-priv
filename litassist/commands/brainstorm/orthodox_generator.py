"""
Orthodox strategy generation for brainstorm command.

Generates conservative legal strategies based on established precedents.
"""

import click

from litassist.llm.factory import LLMClientFactory
from litassist.utils.legal_reasoning import create_reasoning_prompt
from litassist.prompts import PROMPTS
from litassist.logging import log_task_event


def generate_orthodox_strategies(
    facts: str, side: str, area: str, research_context: str = ""
):
    """
    Generate orthodox legal strategies.

    Args:
        facts: Case facts content
        side: Which side (plaintiff/defendant/etc)
        area: Legal area (civil/criminal/etc)
        research_context: Optional research context to inform strategies

    Returns:
        Tuple of (content, usage)
    """
    click.echo("Generating orthodox strategies...")
    orthodox_client = LLMClientFactory.for_command("brainstorm", "orthodox")

    # Use centralized orthodox prompt template with format instructions
    orthodox_prompt_template = PROMPTS.get("strategies.brainstorm.orthodox_prompt")

    # Build the complete prompt by combining template with context
    # The orthodox_prompt contains format instructions, orthodox_base adds facts/side/area
    facts_and_context = PROMPTS.get("strategies.brainstorm.orthodox_base").format(
        facts=facts,
        side=side,
        area=area,
        research=research_context if research_context else ""
    )

    # Combine the format instructions with the facts/context
    combined_content = facts_and_context + "\n\n" + orthodox_prompt_template

    # Wrap in output format
    orthodox_base_prompt = PROMPTS.get(
        "strategies.brainstorm.orthodox_output_format"
    ).format(content=combined_content)

    # Add reasoning trace to orthodox prompt
    orthodox_prompt = create_reasoning_prompt(
        orthodox_base_prompt, "brainstorm-orthodox"
    )
    orthodox_messages = [
        {
            "role": "system",
            "content": PROMPTS.get("commands.brainstorm.orthodox_system"),
        },
        {"role": "user", "content": orthodox_prompt},
    ]

    # Execute the query, heartbeat decorator handles progress notifications
    try:
        log_task_event(
            "brainstorm",
            "orthodox",
            "llm_call",
            "Sending orthodox strategies prompt to LLM",
            {"model": orthodox_client.model}
        )
    except Exception:
        pass

    try:
        orthodox_content, orthodox_usage = orthodox_client.complete(
            orthodox_messages, skip_citation_verification=True
        )

        try:
            log_task_event(
                "brainstorm",
                "orthodox",
                "llm_response",
                "Orthodox strategies LLM response received",
                {"model": orthodox_client.model}
            )
        except Exception:
            pass
    except Exception as e:
        raise click.ClickException(f"Error generating orthodox strategies: {str(e)}")

    return orthodox_content, orthodox_usage
