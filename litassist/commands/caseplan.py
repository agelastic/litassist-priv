"""
Case-specific litigation workflow planning.

This module implements the 'caseplan' command which analyzes case facts
and generates a customized, efficient litigation workflow plan.
"""

import click
from litassist.config import CONFIG
from litassist.utils import (
    save_log,
    heartbeat,
    timed,
    validate_file_size_limit,
    save_command_output,
)
from litassist.llm import LLMClientFactory
from litassist.prompts import PROMPTS


@click.command()
@click.argument("case_facts", type=click.File("r"))
@click.option("--focus", help="Specific area to focus the plan on")
@click.option(
    "--budget",
    type=click.Choice(["minimal", "standard", "comprehensive"]),
    default=None,
    help="Budget constraint level (if not specified, LLM will recommend)",
)
@timed
def caseplan(case_facts, focus, budget):
    """
    Generate customized litigation workflow plan based on case facts.

    If --budget is not specified, performs a rapid assessment using Claude Sonnet 4
    and outputs a short summary, budget recommendation, and justification.
    If --budget is specified, generates a full plan using Claude Opus 4.

    Args:
        case_facts: Path to case facts file (10-heading structure)

    Examples:
        litassist caseplan case_facts.txt
        litassist caseplan case_facts.txt --focus "property dispute"
        litassist caseplan case_facts.txt --budget minimal
    """
    facts_content = case_facts.read()
    validate_file_size_limit(facts_content, 50000, "Case facts")

    if budget is None:
        # Budget assessment mode (Sonnet)
        click.echo("Analyzing case to recommend appropriate budget level...")

        llm_client = LLMClientFactory.for_command("caseplan", "assessment")

        system_prompt = PROMPTS.get("commands.caseplan.budget_assessment_system")
        user_prompt = f"""CASE FACTS:
{facts_content}

{PROMPTS.get("commands.caseplan.budget_assessment_instructions")}
"""

        @timed
        def assess_budget():
            return llm_client.complete(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )

        try:
            assessment, usage = assess_budget()
        except Exception as e:
            raise click.ClickException(f"Budget assessment error: {e}")

        output_file = save_command_output(
            "caseplan-assessment",
            assessment,
            case_facts.name,
            metadata={"Type": "Budget Assessment"},
        )

        save_log(
            "caseplan-assessment",
            {
                "inputs": {"case_facts": facts_content},
                "params": {"model": llm_client.model},
                "usage": usage,
                "response": assessment,
                "output_file": output_file,
            },
        )

        click.echo("\n" + "=" * 60)
        click.echo("BUDGET RECOMMENDATION")
        click.echo("=" * 60)
        click.echo(assessment)
        click.echo("=" * 60)
        click.echo(f'\n📄 Recommendation saved to: "{output_file}"')
        click.echo("\n💡 To generate full plan, run again with recommended budget:")
        click.echo("   e.g., litassist caseplan case_facts.txt --budget standard")

    else:
        # Full plan mode (Opus)
        click.echo("Analyzing case and generating litigation plan...")

        llm_client = LLMClientFactory.for_command("caseplan")

        system_prompt = PROMPTS.get("commands.caseplan.system").format(
            litassist_capabilities=PROMPTS.get("capabilities.litassist_capabilities")
        )

        # Build the main user prompt
        prompt_parts = [
            f"CASE FACTS:\n{facts_content}",
            f"BUDGET LEVEL: {budget}",
        ]
        if focus:
            prompt_parts.append(f"FOCUS AREA: {focus}")

        prompt_parts.append(PROMPTS.get("commands.caseplan.analysis_instructions"))
        user_prompt = "\n\n".join(prompt_parts)

        # Add glob help section if available
        try:
            glob_help = PROMPTS.get("glob_help_section")
            user_prompt = f"{user_prompt}\n\n{glob_help}"
        except KeyError:
            pass  # Glob help addon not available

        @timed
        def generate_plan():
            call_with_hb = heartbeat(CONFIG.heartbeat_interval)(llm_client.complete)
            return call_with_hb(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )

        try:
            plan_content, usage = generate_plan()
        except Exception as e:
            raise click.ClickException(f"Plan generation error: {e}")

        metadata = {"Case Facts File": case_facts.name, "Budget Level": budget}
        if focus:
            metadata["Focus Area"] = focus

        output_file = save_command_output(
            "caseplan", plan_content, case_facts.name, metadata=metadata
        )

        save_log(
            "caseplan",
            {
                "inputs": {"case_facts": facts_content},
                "params": {"model": llm_client.model, "focus": focus, "budget": budget},
                "usage": usage,
                "response": plan_content,
                "output_file": output_file,
            },
        )

        click.echo("\n✅ Litigation plan generated successfully!")
        click.echo(f'📄 Output saved to: "{output_file}"')
        click.echo(f'\n💡 View plan: open "{output_file}"')
