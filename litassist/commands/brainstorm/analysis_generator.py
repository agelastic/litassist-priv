"""
Strategy analysis generator for brainstorm command.

Analyzes both orthodox and unorthodox strategies to identify most likely to succeed.
"""

import click

from litassist.llm.factory import LLMClientFactory
from litassist.utils.legal_reasoning import create_reasoning_prompt
from litassist.prompts import PROMPTS
from litassist.logging import log_task_event


def generate_analysis(
    facts: str,
    side: str,
    area: str,
    orthodox_content: str,
    unorthodox_content: str,
    matter_posture: str = "",
):
    """
    Analyze strategies and identify most likely to succeed.

    Args:
        facts: Case facts content
        side: Which side (plaintiff/defendant/etc)
        area: Legal area (civil/criminal/etc)
        orthodox_content: Generated orthodox strategies
        unorthodox_content: Generated unorthodox strategies

    Returns:
        Tuple of (content, usage)
    """
    click.echo("Analyzing most promising strategies...")
    analysis_client = LLMClientFactory.for_command("brainstorm", "analysis")

    # Use centralized analysis prompt template
    analysis_template = PROMPTS.get("strategies.brainstorm.analysis_prompt")
    # Build analysis base prompt from template
    analysis_base_content = PROMPTS.get("strategies.brainstorm.analysis_base").format(
        facts=facts,
        side=side,
        area=area,
        orthodox_strategies=orthodox_content,
        unorthodox_strategies=unorthodox_content,
    )

    analysis_base_prompt = f"""{analysis_base_content}

{analysis_template}"""

    analysis_prompt = create_reasoning_prompt(
        analysis_base_prompt, "brainstorm-analysis"
    )
    analysis_system = PROMPTS.get("commands.brainstorm.analysis_system")
    if matter_posture:
        analysis_system = matter_posture + "\n\n" + analysis_system
    analysis_messages = [
        {"role": "system", "content": analysis_system},
        {"role": "user", "content": analysis_prompt},
    ]

    # Execute analysis query for most promising strategies
    try:
        log_task_event(
            "brainstorm",
            "analysis",
            "llm_call",
            "Sending strategy analysis prompt to LLM",
            {"model": analysis_client.model}
        )
    except Exception:
        pass

    try:
        analysis_content, analysis_usage = analysis_client.complete(analysis_messages)

        try:
            log_task_event(
                "brainstorm",
                "analysis",
                "llm_response",
                "Strategy analysis LLM response received",
                {"model": analysis_client.model}
            )
        except Exception:
            pass
    except Exception as e:
        raise click.ClickException(f"Error analyzing strategies: {e}")

    return analysis_content, analysis_usage
