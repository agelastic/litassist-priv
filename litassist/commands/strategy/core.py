"""
Core strategy command implementation.

This module contains the main strategy function that orchestrates
legal strategy generation for Australian civil proceedings.
"""

import click
import re

from litassist.utils import (
    save_log,
    timed,
    create_reasoning_prompt,
    extract_reasoning_trace,
    warning_message,
    success_message,
    saved_message,
    stats_message,
    info_message,
    error_message,
    tip_message,
    parse_strategies_file,
    validate_file_size_limit,
    verify_content_if_needed,
)
from litassist.llm import LLMClientFactory
from litassist.prompts import PROMPTS
from litassist.verification_chain import run_cove_verification

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
@click.option("--noverify", is_flag=True, help="Skip standard verification (does not affect --cove)")
@click.option("--cove", is_flag=True, help="Use Chain of Verification instead of standard verification")
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def strategy(case_facts, outcome, strategies, verify, noverify, cove, output):
    """
    Generate legal strategy options and draft documents for Australian civil matters.

    Analyzes case facts to produce strategic options for achieving a specific legal
    outcome, including recommended next steps and a draft legal document.

    Args:
        case_facts: Path to case facts file following the 10-heading structure
        outcome: Desired legal outcome (single sentence description)
        strategies: Optional strategies file from brainstorm command
        verify: Enable self-critique pass (always on by default)
        noverify: Skip standard verification (does not affect --cove)
        cove: Use Chain of Verification instead of standard verification
        output: Custom output filename prefix

    Raises:
        click.ClickException: If case facts are invalid or LLM errors occur
    """
    # Read and validate case facts
    case_text = case_facts.read()
    
    # Check case facts file size
    validate_file_size_limit(case_text, 100000, "Case facts")
    
    if not validate_case_facts_format(case_text):
        raise click.ClickException(
            "Case facts file must follow the required 10-heading structure. Run 'litassist extractfacts' first."
        )
    
    # Extract legal issues
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
        strategies_content = strategies.read()
        
        # Check strategies file size
        validate_file_size_limit(strategies_content, 100000, "Strategies")
        
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
    
    # Generate strategic options
    system_prompt = PROMPTS.get("commands.strategy.system")
    
    # Enhance prompt if strategies are provided
    if parsed_strategies and parsed_strategies["most_likely_count"] > 0:
        system_prompt += "\n\n" + PROMPTS.get("strategies.brainstorm.brainstormed_strategies_context").format(
            most_likely_count=parsed_strategies['most_likely_count']
        )
    elif parsed_strategies:
        system_prompt += "\n\n" + PROMPTS.get("strategies.brainstorm.brainstormed_strategies_context_generic")
    
    # Use centralized strategic options instructions
    strategic_instructions = PROMPTS.get(
        "strategies.strategy.strategic_options_instructions"
    )
    
    # Build the user prompt with case facts
    base_user_prompt = PROMPTS.get("analysis.case_facts_prompt").format(
        facts_content=case_text,
        outcome=outcome,
        legal_issues=legal_issues
    )
    base_user_prompt += f"\n\n{strategic_instructions}"
    
    # Add strategies content if provided
    if parsed_strategies:
        base_user_prompt += "\n" + PROMPTS.get("strategies.brainstorm.brainstormed_strategies_details").format(
            orthodox_count=parsed_strategies['orthodox_count'],
            unorthodox_count=parsed_strategies['unorthodox_count'],
            most_likely_count=parsed_strategies['most_likely_count'],
            strategies_content=strategies_content
        )
    
    # Create reasoning prompt
    user_prompt = create_reasoning_prompt(base_user_prompt, "strategy")
    
    # Generate strategic options with reasoning
    try:
        strategy_content, strategy_usage = llm_client.complete(
            [{"role": "system", "content": system_prompt}, 
             {"role": "user", "content": user_prompt}]
        )
    except Exception as e:
        raise click.ClickException(f"LLM strategy generation error: {e}")
    
    # Extract reasoning traces for each option
    option_traces = []
    
    # Extract options from the strategy content
    option_pattern = r"## OPTION (\d+):(.*?)(?=## OPTION \d+:|## RECOMMENDED NEXT STEPS|## UNORTHODOX|$)"
    options = re.findall(option_pattern, strategy_content, re.DOTALL)
    
    for option_num, option_content in options:
        trace = extract_reasoning_trace(option_content)
        option_traces.append({"option_number": int(option_num), "trace": trace})
    
    # Create consolidated reasoning trace
    reasoning_trace = create_consolidated_reasoning_trace(option_traces, outcome)
    
    # Generate recommended next steps
    next_steps_prompt = PROMPTS.get("strategies.strategy.next_steps_prompt")
    
    try:
        next_steps_content, _ = llm_client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": strategy_content},
                {"role": "user", "content": next_steps_prompt},
            ]
        )
    except Exception as e:
        raise click.ClickException(f"LLM next steps generation error: {e}")
    
    # Determine document type and generate draft
    doc_type = determine_document_type(outcome)
    document_content = generate_draft_document(
        llm_client,
        system_prompt,
        user_prompt,
        strategy_content,
        outcome,
        doc_type
    )
    
    # Validate and verify strategy content (most important)
    citation_issues = llm_client.validate_citations(strategy_content)
    if citation_issues:
        # Prepend warnings to strategy content
        citation_warning = "--- CITATION VALIDATION WARNINGS ---\n"
        citation_warning += "\n".join(citation_issues)
        citation_warning += "\n" + "-" * 40 + "\n\n"
        strategy_content = citation_warning + strategy_content
    
    # Apply verification - either CoVe or standard
    cove_results = None
    if cove:
        # Use CoVe INSTEAD of standard verification
        click.echo(info_message("Running Chain of Verification..."))
        original_content = strategy_content
        strategy_content, cove_results = run_cove_verification(strategy_content, 'strategy')
        
        if not cove_results['cove']['passed']:
            click.echo(success_message("CoVe corrected issues - strategies regenerated"))
            save_log("strategy_cove_regeneration", {
                "original_length": len(original_content),
                "regenerated_length": len(strategy_content),
                "issues_fixed": cove_results['cove']['issues'],
                "model": "See cove_strategy_summary.json for model details"
            })
        else:
            click.echo(success_message("CoVe verification passed - no issues found"))
    elif not noverify:
        # Use standard verification (current behavior)
        strategy_content, _ = verify_content_if_needed(
            llm_client, strategy_content, "strategy", verify_flag=True
        )
        click.echo(info_message("Standard verification applied"))
    else:
        click.echo(info_message("Standard verification skipped by --noverify flag"))
    
    # Save all outputs
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
        cove_results=cove_results,
        cove=cove,
        llm_model=llm_client.model
    )
    
    # Save log
    save_strategy_log(outcome, strategy_content, strategy_usage, cove_results)
    
    # Show completion message
    click.echo()
    click.echo(success_message("Strategy generation complete!"))
    click.echo(saved_message(f"Strategic options: {strategy_file}"))
    click.echo(saved_message(f"Next steps: {steps_file}"))
    click.echo(saved_message(f"Draft document: {draft_file}"))
    click.echo(saved_message(f"Reasoning trace: {trace_file}"))
    click.echo()
    click.echo(stats_message(f"Total tokens used: {strategy_usage['total_tokens']:,}"))
    click.echo()
    click.echo(tip_message(f"View strategic options: open {strategy_file}"))