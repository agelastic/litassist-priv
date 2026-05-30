"""
Case-specific litigation workflow planning.

This module implements the 'caseplan' command which analyzes case facts
and generates a customized, efficient litigation workflow plan.
"""

import click

from litassist.llm.factory import LLMClientFactory
from litassist.logging import log_task_event
from litassist.timing import timed
from litassist.utils.case_facts import resolve_case_facts_file
from litassist.utils.file_ops import validate_file_size_limit
from litassist.utils.formatting import warning_message

from .budget_assessor import assess_budget
from .plan_generator import generate_full_plan


@click.command()
@click.argument("case_facts", required=False, type=click.File("r"))
@click.option("--context", help="Additional context to guide the analysis")
@click.option(
    "--budget",
    type=click.Choice(["minimal", "standard", "comprehensive"]),
    default=None,
    help="Budget constraint level (if not specified, LLM will recommend)",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.option(
    "--verify",
    is_flag=True,
    help="Not supported - caseplan outputs are not verified. Use 'litassist verify' command for verification.",
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Not supported - caseplan has no internal verification.",
)
@timed
def caseplan(case_facts, context, budget, output, verify, noverify):
    """
    Generate customized litigation workflow plan based on case facts.

    If --budget is not specified, performs a rapid assessment using Claude Sonnet
    4.6 and outputs a short summary, budget recommendation, and justification.
    If --budget is specified, generates a full plan using Claude Opus 4.7.

    Args:
        case_facts: Path to case facts file (10-heading structure). Optional - if
            omitted, the latest case_facts*.txt in the current directory is used.

    Examples:
        litassist caseplan                       # auto-selects latest case_facts*.txt
        litassist caseplan case_facts.txt
        litassist caseplan case_facts.txt --context "property dispute"
        litassist caseplan --budget minimal
    """
    # Handle unsupported verification flags
    if verify:
        click.echo(
            warning_message(
                "--verify not supported: This command has no internal verification. Use 'litassist verify' for post-processing verification."
            )
        )
    if noverify:
        click.echo(
            warning_message(
                "--noverify not supported: This command has no verification to skip."
            )
        )

    # Command start log
    try:
        log_task_event(
            "caseplan",
            "init",
            "start",
            f"Starting caseplan - mode: {'assessment' if budget is None else 'full plan'}",
            {"budget": budget, "context": context}
        )
    except Exception:
        pass

    # Read case facts
    try:
        log_task_event(
            "caseplan",
            "reading",
            "start",
            "Reading case facts file"
        )
    except Exception:
        pass

    if case_facts is None:
        case_facts = open(resolve_case_facts_file())

    facts_content = case_facts.read()
    if not facts_content.strip():
        raise click.ClickException("Case facts file is empty.")
    # Cap derives from the caseplan model's input window so we don't blow
    # the context when the user routes caseplan to a smaller-window model.
    validate_file_size_limit(
        facts_content,
        LLMClientFactory.get_input_budget_for_command("caseplan"),
        "Case facts",
    )

    try:
        log_task_event(
            "caseplan",
            "reading",
            "end",
            f"Case facts read: {len(facts_content)} characters"
        )
    except Exception:
        pass

    if budget is None:
        # Budget assessment mode (Sonnet)
        assess_budget(facts_content, case_facts.name, context, output)
    else:
        # Full plan mode (Opus)
        generate_full_plan(facts_content, case_facts.name, context, budget, output)

    # Command end log
    try:
        log_task_event(
            "caseplan",
            "init",
            "end",
            f"Caseplan command complete - mode: {'assessment' if budget is None else 'full plan'}"
        )
    except Exception:
        pass
