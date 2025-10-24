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
        Tuple of (content, usage, citation_issues)
    """
    click.echo("Generating orthodox strategies...")
    orthodox_client = LLMClientFactory.for_command("brainstorm", "orthodox")

    # Use centralized orthodox prompt template with research context
    orthodox_template = PROMPTS.get(
        "strategies.brainstorm.orthodox_prompt", research_context=research_context
    )
    # Build orthodox base prompt from template
    orthodox_base_content = PROMPTS.get("strategies.brainstorm.orthodox_base").format(
        facts=facts, side=side, area=area, research=orthodox_template
    )

    orthodox_base_prompt = PROMPTS.get(
        "strategies.brainstorm.orthodox_output_format"
    ).format(content=orthodox_base_content)

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
        orthodox_content, orthodox_usage = orthodox_client.complete(orthodox_messages)
    except Exception as e:
        raise click.ClickException(f"Error generating orthodox strategies: {str(e)}")

    # Validate citations
    try:
        log_task_event(
            "brainstorm",
            "orthodox-citations",
            "start",
            "Validating citations in orthodox strategies",
        )
    except Exception:
        pass
    orthodox_citation_issues = orthodox_client.validate_citations(orthodox_content)
    try:
        log_task_event(
            "brainstorm",
            "orthodox-citations",
            "end",
            "Orthodox citation validation complete",
            {
                "issues": (
                    len(orthodox_citation_issues) if orthodox_citation_issues else 0
                )
            },
        )
    except Exception:
        pass

    return orthodox_content, orthodox_usage, orthodox_citation_issues
