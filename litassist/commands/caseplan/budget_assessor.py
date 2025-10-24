"""
Budget assessment workflow for caseplan command.

Handles rapid budget recommendation using Claude Sonnet.
"""

import click
from typing import Dict, Tuple

from litassist.logging import save_log, save_command_output, log_task_event
from litassist.utils.core import timed
from litassist.llm.factory import LLMClientFactory
from litassist.utils.formatting import saved_message, tip_message
from litassist.prompts import PROMPTS


def assess_budget(
    facts_content: str,
    case_facts_name: str,
    context: str,
    output: str
) -> Tuple[str, Dict]:
    """
    Perform budget assessment and save results.

    Args:
        facts_content: Case facts content
        case_facts_name: Name of the case facts file
        context: Additional context (if provided)
        output: Custom output prefix (if provided)

    Returns:
        Tuple of (output_file, usage)

    Raises:
        click.ClickException: If LLM processing fails
    """
    click.echo("Analyzing case to recommend appropriate budget level...")

    try:
        log_task_event(
            "caseplan",
            "assessment",
            "start",
            "Starting budget assessment"
        )
    except Exception:
        pass

    llm_client = LLMClientFactory.for_command("caseplan", "assessment")

    system_prompt = PROMPTS.get("commands.caseplan.budget_assessment_system")
    # Use base case facts template for budget assessment
    user_prompt = PROMPTS.get("analysis.base_case_facts_prompt").format(
        facts_content=facts_content
    )

    user_prompt += (
        f"\n\n{PROMPTS.get('commands.caseplan.budget_assessment_instructions')}"
    )

    @timed
    def _assess_budget():
        try:
            log_task_event(
                "caseplan",
                "assessment",
                "llm_call",
                "Sending budget assessment prompt to LLM",
                {"model": llm_client.model}
            )
        except Exception:
            pass

        result = llm_client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        try:
            log_task_event(
                "caseplan",
                "assessment",
                "llm_response",
                "Budget assessment LLM response received",
                {"model": llm_client.model}
            )
        except Exception:
            pass

        return result

    try:
        assessment, usage = _assess_budget()
    except Exception as e:
        raise click.ClickException(f"Budget assessment error: {e}")

    output_file = save_command_output(
        f"{output}_assessment" if output else "caseplan-assessment",
        assessment,
        "" if output else case_facts_name,
        metadata={"Type": "Budget Assessment"},
    )

    save_log(
        "caseplan-assessment",
        {
            "inputs": {"case_facts": facts_content},
            "params": {"model": llm_client.model},
            "usage": usage,
            # Response content removed - already logged by LLMClient separately
            "output_file": output_file,
        },
    )

    click.echo("\n" + "=" * 60)
    click.echo("BUDGET RECOMMENDATION")
    click.echo("=" * 60)
    click.echo(assessment)
    click.echo("=" * 60)
    msg = saved_message(f'Recommendation saved to: "{output_file}"')
    click.echo(f"\n{msg}")
    click.echo(
        f"\n{tip_message('To generate full plan, run again with recommended budget:')}"
    )
    click.echo("   e.g., litassist caseplan case_facts.txt --budget standard")

    try:
        log_task_event(
            "caseplan",
            "assessment",
            "end",
            "Budget assessment complete"
        )
    except Exception:
        pass

    return output_file, usage
