"""
Case-specific litigation workflow planning.

This module implements the 'caseplan' command which analyzes case facts
and generates a customized, efficient litigation workflow plan.
"""

import os
import sys

import click

from litassist.llm.factory import LLMClientFactory
from litassist.logging import log_task_event
from litassist.timing import timed
from litassist.utils.case_facts import resolve_case_facts_file
from litassist.utils.file_ops import validate_file_size_limit
from litassist.utils.formatting import info_message, tip_message, warning_message

from .budget_assessor import assess_budget
from .plan_generator import generate_full_plan


def _is_interactive() -> bool:
    """True when stdin is a terminal - a human is present to answer a prompt."""
    return sys.stdin.isatty()


def discover_source_files(facts_name=None) -> list:
    """List candidate source documents in the working directory (top level).

    Lists the legal source document types so the planner references REAL filenames
    instead of inventing them. The case-facts file is excluded (resolved/seeded
    separately): both the exact ``facts_name`` caseplan was given and any
    ``case_facts*`` variant. Only regular files are returned (a directory/symlink
    named like a document is skipped) and the extension is matched case-insensitively
    (so ``scan.PDF`` counts). Fully local - no contents are read. Subdirectories
    (``outputs/``, ``logs/``) are not scanned; scope by running from a folder that
    holds just the relevant files.
    """
    exts = (".pdf", ".docx", ".doc", ".rtf", ".txt")
    excluded = {os.path.basename(facts_name)} if facts_name else set()
    found = []
    for entry in os.scandir("."):
        name = entry.name
        if not entry.is_file():
            continue
        if (
            name.lower().endswith(exts)
            and not name.startswith("case_facts")
            and name not in excluded
        ):
            found.append(name)
    return sorted(found)


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
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip the pre-generation confirmation prompt (for non-interactive use).",
)
@timed
def caseplan(case_facts, context, budget, output, verify, noverify, yes):
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
        # Budget assessment mode (Sonnet) - does not reference source files.
        assess_budget(facts_content, case_facts.name, context, output)
    else:
        # Full plan mode (Opus). Show the source-document inventory the plan will
        # reference, then let a human abort BEFORE the paid call if the prep is
        # wrong (only prompt at a terminal; --yes / non-interactive proceeds).
        source_files = discover_source_files(case_facts.name)
        if source_files:
            click.echo(
                info_message(
                    f"Source documents the plan will reference ({len(source_files)}):"
                )
            )
            for name in source_files:
                click.echo(f"  - {name}")
        else:
            click.echo(
                warning_message("No source documents found in the working directory.")
            )
        click.echo(
            tip_message(
                "Confirm these are the right documents, named descriptively by role. "
                "If not, re-run from a directory holding just the relevant files."
            )
        )
        if not yes and _is_interactive():
            click.confirm(
                "Proceed with plan generation? (this makes a paid LLM call)",
                abort=True,
            )
        generate_full_plan(
            facts_content,
            case_facts.name,
            context,
            budget,
            output,
            source_files=source_files,
        )

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
