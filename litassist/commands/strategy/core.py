"""
Core strategy command implementation.

This module contains the main strategy function that orchestrates
legal strategy generation for Australian civil proceedings.
"""

import click
import re

from litassist.utils.core import (
    timed,
    parse_strategies_file,
)
from litassist.utils.file_ops import validate_file_size_limit
from litassist.utils.legal_reasoning import (
    create_reasoning_prompt,
    extract_reasoning_trace,
    verify_content_if_needed,
)
from litassist.utils.formatting import (
    success_message,
    saved_message,
    stats_message,
    info_message,
    tip_message,
)
from litassist.llm.factory import LLMClientFactory
from litassist.prompts import PROMPTS
from litassist.logging import log_task_event, save_command_output

from .validators import validate_case_facts_format, extract_legal_issues
from .ranker import create_consolidated_reasoning_trace
from .document_generator import determine_document_type, generate_draft_document
from .file_handler import save_strategy_outputs, save_strategy_log


@click.command()
@click.argument("case_facts", type=click.File("r"))
@click.option("--outcome", required=True, help="Desired outcome (single sentence)")
@click.option(
    "--strategies",
    type=click.File("r"),
    help="Optional strategies file from brainstorm command",
)
@click.option(
    "--verify", is_flag=True, help="Enable self-critique pass (default: auto-enabled)"
)
@click.option(
    "--heavy",
    is_flag=True,
    help="Use verification-heavy mode (gpt-5-pro instead of gpt-5)",
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Skip verification stage (not recommended for legal work)",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def strategy(case_facts, outcome, strategies, verify, heavy, noverify, output):
    """
    Generate legal strategy options and draft documents for Australian civil matters.

    Analyzes case facts to produce strategic options for achieving a specific legal
    outcome, including recommended next steps and a draft legal document.

    Args:
        case_facts: Path to case facts file following the 10-heading structure
        outcome: Desired legal outcome (single sentence description)
        strategies: Optional strategies file from brainstorm command
        verify: Enable self-critique pass (always on by default)
        heavy: Use verification-heavy mode (gpt-5-pro instead of gpt-5)
        output: Custom output filename prefix

    Raises:
        click.ClickException: If case facts are invalid or LLM errors occur

    Note:
        For Chain of Verification (CoVe), run `litassist verify-cove` on the output file.
    """

    # Command start log
    try:
        log_task_event(
            "strategy",
            "init",
            "start",
            "Starting strategy generation",
            {"model": LLMClientFactory.get_model_for_command("strategy")},
        )
    except Exception:
        pass

    # Read and validate case facts
    click.echo(info_message("Validating case facts format..."))
    case_text = case_facts.read()

    if not validate_case_facts_format(case_text):
        raise click.ClickException(
            "Case facts file must follow the required 10-heading structure. Run 'litassist extractfacts' first."
        )

    # Extract legal issues
    click.echo(info_message("Extracting legal issues..."))
    legal_issues = extract_legal_issues(case_text)
    if not legal_issues:
        raise click.ClickException(
            "Could not extract legal issues from the case facts file."
        )

    # Initialize LLM client using factory
    llm_client = LLMClientFactory.for_command("strategy")

    # Read and parse strategies file if provided
    strategies_content = ""
    parsed_strategies = None
    if strategies:
        click.echo(info_message("Reading strategies from brainstorm file..."))
        strategies_content = strategies.read()

        # Check combined input size when strategies provided
        validate_file_size_limit(
            case_text + strategies_content,
            600000,
            "Combined case facts and strategies"
        )

        parsed_strategies = parse_strategies_file(strategies_content)

        # Display what was found
        click.echo("Using strategies from brainstorm:")
        click.echo(f"  - {parsed_strategies['orthodox_count']} orthodox strategies")
        click.echo(f"  - {parsed_strategies['unorthodox_count']} unorthodox strategies")
        click.echo(
            f"  - {parsed_strategies['most_likely_count']} marked as most likely to succeed"
        )

        if parsed_strategies["metadata"]:
            click.echo(
                f"  - Generated for: {parsed_strategies['metadata'].get('side', 'unknown')} in {parsed_strategies['metadata'].get('area', 'unknown')} law"
            )

        # Show warning if no "most likely to succeed" found
        if parsed_strategies["most_likely_count"] == 0:
            click.echo(
                "  - Warning: No strategies marked as 'most likely to succeed' found"
            )
    else:
        # Check case facts size when no strategies file
        validate_file_size_limit(case_text, 600000, "Case facts")

    # Generate strategic options
    try:
        log_task_event(
            "strategy",
            "options",
            "start",
            "Generating strategic options",
            {"model": LLMClientFactory.get_model_for_command("strategy")},
        )
    except Exception:
        pass
    click.echo(info_message("Generating strategic options..."))
    system_prompt = PROMPTS.get("commands.strategy.system")

    # Enhance prompt if strategies are provided
    if parsed_strategies and parsed_strategies["most_likely_count"] > 0:
        system_prompt += "\n\n" + PROMPTS.get(
            "strategies.brainstorm.brainstormed_strategies_context"
        ).format(most_likely_count=parsed_strategies["most_likely_count"])
    elif parsed_strategies:
        system_prompt += "\n\n" + PROMPTS.get(
            "strategies.brainstorm.brainstormed_strategies_context_generic"
        )

    # Use centralized strategic options instructions
    strategic_instructions = PROMPTS.get(
        "strategies.strategy.strategic_options_instructions"
    )

    # Build the user prompt with case facts
    base_user_prompt = PROMPTS.get("analysis.case_facts_prompt").format(
        facts_content=case_text, outcome=outcome, legal_issues=legal_issues
    )
    base_user_prompt += f"\n\n{strategic_instructions}"

    # Add strategies content if provided
    if parsed_strategies:
        base_user_prompt += "\n" + PROMPTS.get(
            "strategies.brainstorm.brainstormed_strategies_details"
        ).format(
            orthodox_count=parsed_strategies["orthodox_count"],
            unorthodox_count=parsed_strategies["unorthodox_count"],
            most_likely_count=parsed_strategies["most_likely_count"],
            strategies_content=strategies_content,
        )

    # Create reasoning prompt
    user_prompt = create_reasoning_prompt(base_user_prompt, "strategy")

    # Generate strategic options with reasoning
    try:
        # Explicit on-screen LLM call event with model name
        try:
            log_task_event(
                "strategy",
                "options",
                "llm_call",
                "Sending options prompt to LLM",
                {"model": llm_client.model},
            )
        except Exception:
            pass

        strategy_content, strategy_usage = llm_client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        # Explicit on-screen LLM response event with model name
        try:
            log_task_event(
                "strategy",
                "options",
                "llm_response",
                "Options LLM response received",
                {"model": llm_client.model},
            )
        except Exception:
            pass

        try:
            log_task_event(
                "strategy",
                "options",
                "end",
                "Strategic options generated",
                {"model": llm_client.model},
            )
        except Exception:
            pass
    except Exception as e:
        raise click.ClickException(f"LLM strategy generation error: {e}")

    # Extract reasoning traces for each option
    click.echo(info_message("Extracting reasoning traces..."))
    option_traces = []

    # Extract options from the strategy content
    # Note: We look for OPTIONS (plural) sections to avoid capturing the overall Strategic Reasoning
    option_pattern = r"## OPTION (\d+):(.*?)(?=## OPTION \d+:|## RECOMMENDED NEXT STEPS|## UNORTHODOX|## Overall Strategic Reasoning|$)"
    options = re.findall(option_pattern, strategy_content, re.DOTALL)

    for option_num, option_content in options:
        trace = extract_reasoning_trace(option_content)
        option_traces.append({"option_number": int(option_num), "trace": trace})

    # Extract overall strategic reasoning (if present)
    overall_pattern = r"## Overall Strategic Reasoning\s*\n(.*?)(?:===|$)"
    overall_match = re.search(overall_pattern, strategy_content, re.DOTALL)
    overall_reasoning = None
    if overall_match:
        overall_reasoning = extract_reasoning_trace(overall_match.group(0))

    # Create consolidated reasoning trace
    reasoning_trace = create_consolidated_reasoning_trace(
        option_traces, outcome, overall_reasoning
    )

    # Validate citations in strategic options
    try:
        log_task_event(
            "strategy",
            "citations",
            "start",
            "Validating citations",
            {"model": LLMClientFactory.get_model_for_command("strategy")},
        )
    except Exception:
        pass
    click.echo(info_message("Validating citations..."))
    citation_issues = llm_client.validate_citations(strategy_content)
    try:
        log_task_event(
            "strategy",
            "citations",
            "end",
            "Citation validation complete",
            {
                "issues": len(citation_issues) if citation_issues else 0,
                "model": llm_client.model,
            },
        )
    except Exception:
        pass

    # Warn if both --noverify and --heavy are specified
    if noverify and heavy:
        from litassist.utils.formatting import warning_message
        click.echo(warning_message("--heavy flag ignored when --noverify is specified"))

    if not noverify:
        # Save raw pre-verification output for audit trail (before warnings prepended)
        raw_metadata = {
            "Desired Outcome": outcome,
            "Case Facts File": case_facts.name,
            "Verification": "Not yet applied (raw output)",
        }
        if strategies:
            raw_metadata["Strategies File"] = strategies.name
        save_command_output(
            output if output else "strategy",
            strategy_content,
            "" if output else outcome,
            metadata=raw_metadata,
            suffix="_raw",
        )

        # Prepend citation warnings (if any) before verification
        if citation_issues:
            citation_warning = "--- CITATION VALIDATION WARNINGS ---\n"
            citation_warning += "\n".join(citation_issues)
            citation_warning += "\n" + "-" * 40 + "\n\n"
            strategy_content = citation_warning + strategy_content

        # Apply standard verification before generating next steps and draft
        try:
            log_task_event(
                "strategy",
                "verification",
                "start",
                "Applying standard verification",
                {"model": LLMClientFactory.get_model_for_command("verification")},
            )
        except Exception:
            pass
        click.echo(info_message("Applying standard verification..."))
        strategy_content, _ = verify_content_if_needed(
            llm_client, strategy_content, "strategy", verify_flag=True, heavy=heavy
        )
        verification_mode = "verification-heavy (gpt-5-pro)" if heavy else "Standard verification"
        click.echo(info_message(f"{verification_mode} complete"))
        try:
            log_task_event(
                "strategy",
                "verification",
                "end",
                "Verification complete",
                {"model": LLMClientFactory.get_model_for_command("verification")},
            )
        except Exception:
            pass
    else:
        # No verification - still prepend citation warnings if any
        if citation_issues:
            citation_warning = "--- CITATION VALIDATION WARNINGS ---\n"
            citation_warning += "\n".join(citation_issues)
            citation_warning += "\n" + "-" * 40 + "\n\n"
            strategy_content = citation_warning + strategy_content
        click.echo(info_message("Standard verification skipped"))

    # Generate recommended next steps (using verified strategic options)
    try:
        log_task_event(
            "strategy",
            "next-steps",
            "start",
            "Generating recommended next steps",
            {"model": LLMClientFactory.get_model_for_command("strategy")},
        )
    except Exception:
        pass
    click.echo(info_message("Generating recommended next steps..."))
    next_steps_prompt = PROMPTS.get("strategies.strategy.next_steps_prompt")

    try:
        try:
            log_task_event(
                "strategy",
                "next-steps",
                "llm_call",
                "Sending next-steps prompt to LLM",
                {"model": llm_client.model},
            )
        except Exception:
            pass

        next_steps_content, _ = llm_client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": strategy_content},
                {"role": "user", "content": next_steps_prompt},
            ]
        )

        try:
            log_task_event(
                "strategy",
                "next-steps",
                "llm_response",
                "Next-steps LLM response received",
                {"model": llm_client.model},
            )
        except Exception:
            pass

        try:
            log_task_event(
                "strategy",
                "next-steps",
                "end",
                "Next steps generated",
                {"model": llm_client.model},
            )
        except Exception:
            pass
    except Exception as e:
        raise click.ClickException(f"LLM next steps generation error: {e}")

    # Determine document type and generate draft (using verified strategic options)
    click.echo(info_message("Determining document type..."))
    doc_type = determine_document_type(outcome)
    try:
        log_task_event(
            "strategy",
            "draft",
            "start",
            f"Generating draft {doc_type}",
            {"model": LLMClientFactory.get_model_for_command("strategy")},
        )
    except Exception:
        pass
    click.echo(info_message(f"Generating draft {doc_type}..."))
    document_content = generate_draft_document(
        llm_client, system_prompt, user_prompt, strategy_content, outcome, doc_type
    )
    try:
        log_task_event(
            "strategy",
            "draft",
            "end",
            f"Draft {doc_type} generated",
            {"model": llm_client.model},
        )
    except Exception:
        pass

    # Save all outputs
    click.echo(info_message("Saving strategy outputs..."))
    strategy_file, steps_file, draft_file, trace_file = save_strategy_outputs(
        strategy_content=strategy_content,
        next_steps_content=next_steps_content,
        document_content=document_content,
        reasoning_trace=reasoning_trace,
        outcome=outcome,
        case_facts_name=case_facts.name,
        doc_type=doc_type,
        output_prefix=output,
        strategies_name=strategies.name if strategies else None,
        citation_issues=citation_issues,
        llm_model=llm_client.model,
        noverify=noverify,
        heavy=heavy,
    )

    # Save log
    save_strategy_log(outcome, strategy_content, strategy_usage)

    # Show completion message
    click.echo()
    try:
        log_task_event("strategy", "init", "end", "Strategy generation complete")
    except Exception:
        pass
    click.echo(success_message("Strategy generation complete!"))
    click.echo(saved_message(f"Strategic options: {strategy_file}"))
    click.echo(saved_message(f"Next steps: {steps_file}"))
    click.echo(saved_message(f"Draft document: {draft_file}"))
    click.echo(saved_message(f"Reasoning trace: {trace_file}"))
    click.echo()
    click.echo(stats_message(f"Total tokens used: {strategy_usage['total_tokens']:,}"))
    click.echo()
    click.echo(tip_message(f"View strategic options: open {strategy_file}"))
