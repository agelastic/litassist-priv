"""
Generate comprehensive legal strategies via Grok.

This module implements the 'brainstorm' command which uses Grok's creative capabilities
to generate both orthodox and unorthodox litigation strategies based on provided case facts,
tailored to the specified party (plaintiff/defendant) and legal area.
"""

import click
import os
import re
import time
import logging

from litassist.config import CONFIG
from litassist.utils import (
    read_document,
    save_log,
    heartbeat,
    timed,
    OUTPUT_DIR,
    create_reasoning_prompt,
    extract_reasoning_trace,
    parse_strategies_file,
    validate_side_area_combination,
    validate_file_size_limit,
    save_command_output,
)
from litassist.llm import LLMClientFactory, LLMClient
from litassist.prompts import PROMPTS


def regenerate_bad_strategies(
    client: LLMClient,
    original_content: str,
    base_prompt: str,
    strategy_type: str,
    max_retries: int = 2,
) -> str:
    """
    Selectively regenerate only strategies with citation issues.

    Args:
        client: LLMClient instance to use for regeneration
        original_content: Original strategy content with potential citation issues
        base_prompt: Base prompt used for generation
        strategy_type: Type of strategies ("orthodox" or "unorthodox") for logging
        max_retries: Maximum regeneration attempts

    Returns:
        Clean content with verified strategies only
    """
    click.echo(
        PROMPTS.get(
            "system_feedback.status.progress.analyzing_strategies",
            strategy_type=strategy_type,
        )
    )

    # Split content into individual strategies using a robust regex
    # This pattern finds all numbered list items (e.g., "1. Strategy Title...")
    # and treats each one as a separate strategy.
    # Remove any section headers before processing
    original_content = re.sub(r'^##\s+\w+\s+STRATEGIES\s*\n+', '', original_content.strip())
    strategies = re.split(r"\n(?=\d+\.\s+)", original_content.strip())
    # The first item might be a header, so filter it out if it doesn't start with a number
    strategies = [s.strip() for s in strategies if re.match(r"^\d+\.", s.strip())]

    # Validate each strategy individually and track their final state
    strategy_results = {}  # Maps original position to final strategy content
    strategies_to_regenerate = []

    for i, strategy in enumerate(strategies, 1):
        if not strategy.strip():
            continue

        citation_issues = client.validate_citations(strategy)
        if citation_issues:
            click.echo(
                PROMPTS.get(
                    "system_feedback.status.completion.strategy_issues_found",
                    strategy_num=i,
                    issue_count=len(citation_issues) - 1,
                )
            )
            strategies_to_regenerate.append((i, strategy))
        else:
            click.echo(
                PROMPTS.get(
                    "system_feedback.status.completion.strategy_verified",
                    strategy_num=i,
                )
            )
            strategy_results[i] = strategy

    # Regenerate problematic strategies
    for retry_attempt in range(max_retries):
        if not strategies_to_regenerate:
            break

        click.echo(
            f"  🔄 Regeneration attempt {retry_attempt + 1}: {len(strategies_to_regenerate)} strategies need fixing"
        )

        remaining_to_regenerate = []

        for strategy_num, bad_strategy in strategies_to_regenerate:
            # Create focused regeneration prompt
            # Use centralized regeneration prompt template
            regen_template = PROMPTS.get("strategies.brainstorm.regeneration_prompt")
            citation_instructions = PROMPTS.get(
                "verification.citation_retry_instructions"
            )
            regen_prompt = f"""{base_prompt}

{regen_template.format(feedback=f"Strategy #{strategy_num} contained unverifiable citations", citation_instructions=citation_instructions)}

Generate ONLY strategy #{strategy_num} in the exact format:

{strategy_num}. [Strategy Title]
[Strategy content...]
"""

            try:
                # Generate single replacement strategy
                new_strategy, _ = client.complete(
                    [{"role": "user", "content": regen_prompt}]
                )

                # Validate the regenerated strategy
                new_citation_issues = client.validate_citations(new_strategy)
                if new_citation_issues:
                    click.echo(
                        f"    ⚠️  Strategy {strategy_num}: Still has citation issues after regeneration"
                    )
                    remaining_to_regenerate.append((strategy_num, bad_strategy))
                else:
                    click.echo(
                        f"    ✅ Strategy {strategy_num}: Successfully regenerated with clean citations"
                    )
                    strategy_results[strategy_num] = new_strategy

            except Exception as e:
                click.echo(
                    f"    💥 Strategy {strategy_num}: Regeneration failed - {str(e)}"
                )
                remaining_to_regenerate.append((strategy_num, bad_strategy))

        strategies_to_regenerate = remaining_to_regenerate

    # Report final status
    if strategies_to_regenerate:
        click.echo(
            f"  ⚠️  {len(strategies_to_regenerate)} {strategy_type} strategies still have citation issues after {max_retries} attempts"
        )
        click.echo(
            f"    📋 Excluding these strategies: {[num for num, _ in strategies_to_regenerate]}"
        )
    else:
        click.echo(f"  ✅ All {strategy_type} strategies now have verified citations")

    click.echo(
        f"  📊 Final result: {len(strategy_results)} verified {strategy_type} strategies"
    )

    # Reconstruct content with final verified strategies only
    if strategy_results:
        # Get strategies in their final positions and renumber sequentially
        renumbered_strategies = []
        for i, (original_pos, strategy) in enumerate(
            sorted(strategy_results.items()), 1
        ):
            # Replace the original numbering with sequential numbering
            strategy_lines = strategy.split("\n")
            if strategy_lines and re.match(r"^\d+\.\s+", strategy_lines[0].strip()):
                # Replace first line numbering
                strategy_lines[0] = re.sub(r"^\d+\.", f"{i}.", strategy_lines[0])
                renumbered_strategies.append("\n".join(strategy_lines))
            else:
                renumbered_strategies.append(strategy)

        # Add the appropriate header back
        header = "## ORTHODOX STRATEGIES" if strategy_type == "orthodox" else "## UNORTHODOX STRATEGIES"
        return f"{header}\n\n" + "\n\n".join(renumbered_strategies)
    else:
        return (
            f"No {strategy_type} strategies could be generated with verified citations."
        )


@click.command()
@click.argument("facts_file", type=click.Path(exists=True))
@click.option(
    "--side",
    type=click.Choice(["plaintiff", "defendant", "accused", "respondent"]),
    required=True,
    help="Specify which side you are representing",
)
@click.option(
    "--area",
    type=click.Choice(["criminal", "civil", "family", "commercial", "administrative"]),
    required=True,
    help="Specify the legal area of the matter",
)
@click.option(
    "--research",
    multiple=True,
    type=click.Path(exists=True),
    help="Optional: One or more lookup report files to inform orthodox strategies (research-informed mode).",
)
@timed
def brainstorm(facts_file, side, area, research):
    """
    Generate comprehensive legal strategies via Grok.

    Uses Grok's creative capabilities to generate:
    - 10 orthodox legal strategies
    - 10 unorthodox but potentially effective strategies
    - A list of strategies most likely to succeed

    All strategies are tailored to your specified party side and legal area.
    The output is automatically saved to strategies.txt for use in other commands.

    Args:
        facts_file: Path to a text file containing structured case facts.
        side: Which side you are representing (plaintiff/defendant/accused/respondent).
        area: The legal area of the matter (criminal/civil/family/commercial/administrative).
    
    Note: Verification is automatically performed on all brainstorm outputs to ensure citation accuracy and legal soundness.

    Raises:
        click.ClickException: If there are errors reading the facts file or with the LLM API call.
    """
    # Check for potentially incompatible side/area combinations
    validate_side_area_combination(side, area)

    # Read the structured facts file
    facts = read_document(facts_file)

    # Check file size to prevent token limit issues
    validate_file_size_limit(facts, 50000, "Case facts")

    # Prepare research context for orthodox strategies
    if research:
        research_contexts = []
        for path in research:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    research_contexts.append(f.read().strip())
            except Exception as e:
                raise click.ClickException(f"Error reading research file '{path}': {e}")
        research_context = "\n\nRESEARCH CONTEXT:\n" + "\n\n".join(research_contexts)
    else:
        research_context = ""

    # Generate Orthodox Strategies (conservative approach)
    click.echo("Generating orthodox strategies...")
    orthodox_client = LLMClientFactory.for_command("brainstorm", "orthodox")

    # Use centralized orthodox prompt template with research context
    orthodox_template = PROMPTS.get(
        "strategies.brainstorm.orthodox_prompt", research_context=research_context
    )
    orthodox_base_prompt = f"""Facts:
{facts}

I am representing the {side} in this {area} law matter.

{orthodox_template}

Please provide output in EXACTLY this format:

## ORTHODOX STRATEGIES

1. [Strategy Title]
   [Brief explanation (1-2 sentences)]
   Key principles: [Legal principles or precedents with citations]

2. [Strategy Title]
   [Brief explanation]
   Key principles: [Legal principles with citations]

[Continue for 10 orthodox strategies]"""

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

    call_with_hb = heartbeat(CONFIG.heartbeat_interval)(orthodox_client.complete)
    try:
        orthodox_content, orthodox_usage = call_with_hb(orthodox_messages)
    except Exception as e:
        raise click.ClickException(
            PROMPTS.get(
                "system_feedback.errors.llm.generation_failed",
                operation="orthodox strategies",
                error=str(e),
            )
        )

    # Selectively regenerate orthodox strategies with citation issues
    orthodox_citation_issues = orthodox_client.validate_citations(orthodox_content)
    if orthodox_citation_issues:
        click.echo(
            f"  🔄 Found {len(orthodox_citation_issues)-1} citation issues in orthodox strategies - fixing..."
        )
        orthodox_content = regenerate_bad_strategies(
            orthodox_client, orthodox_content, orthodox_base_prompt, "orthodox"
        )

    # Generate Unorthodox Strategies (creative approach)
    click.echo("Generating unorthodox strategies...")
    unorthodox_client = LLMClientFactory.for_command("brainstorm", "unorthodox")
    
    # Log model usage for future reference (no user-facing message)
    if "grok" in unorthodox_client.model.lower():
        logging.debug(f"Using {unorthodox_client.model} for unorthodox strategies")

    # Use centralized unorthodox prompt template
    unorthodox_template = PROMPTS.get("strategies.brainstorm.unorthodox_prompt")
    unorthodox_base_prompt = f"""Facts:
{facts}

I am representing the {side} in this {area} law matter.

{unorthodox_template}

Please provide output in EXACTLY this format:

## UNORTHODOX STRATEGIES

1. [Strategy Title]
   [Brief explanation (1-2 sentences)]
   Key principles: [Legal principles or novel arguments]

2. [Strategy Title]
   [Brief explanation]
   Key principles: [Legal principles or innovative theories]

[Continue for 10 unorthodox strategies]"""

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

    try:
        unorthodox_content, unorthodox_usage = call_with_hb(unorthodox_messages)
    except Exception as e:
        raise click.ClickException(
            PROMPTS.get(
                "system_feedback.errors.llm.generation_failed",
                operation="unorthodox strategies",
                error=str(e),
            )
        )

    # Selectively regenerate unorthodox strategies with citation issues
    unorthodox_citation_issues = unorthodox_client.validate_citations(
        unorthodox_content
    )
    if unorthodox_citation_issues:
        click.echo(
            f"  🔄 Found {len(unorthodox_citation_issues)-1} citation issues in unorthodox strategies - fixing..."
        )
        unorthodox_content = regenerate_bad_strategies(
            unorthodox_client, unorthodox_content, unorthodox_base_prompt, "unorthodox"
        )

    # Generate Most Likely to Succeed analysis
    click.echo("Analyzing most promising strategies...")
    analysis_client = LLMClientFactory.for_command("brainstorm", "analysis")

    # Use centralized analysis prompt template
    analysis_template = PROMPTS.get("strategies.brainstorm.analysis_prompt")
    analysis_base_prompt = f"""Facts:
{facts}

I am representing the {side} in this {area} law matter.

ORTHODOX STRATEGIES GENERATED:
{orthodox_content}

UNORTHODOX STRATEGIES GENERATED:
{unorthodox_content}

{analysis_template}

Please provide output in EXACTLY this format:

## MOST LIKELY TO SUCCEED

1. [Strategy Title from above]
   [Why this strategy is most likely to succeed]

2. [Strategy Title from above]
   [Why this strategy is most likely to succeed]

[List 3-5 strategies total that are most likely to succeed]"""

    analysis_prompt = create_reasoning_prompt(
        analysis_base_prompt, "brainstorm-analysis"
    )
    analysis_messages = [
        {
            "role": "system",
            "content": PROMPTS.get("commands.brainstorm.analysis_system"),
        },
        {"role": "user", "content": analysis_prompt},
    ]

    try:
        analysis_content, analysis_usage = call_with_hb(analysis_messages)
    except Exception as e:
        raise click.ClickException(f"Error analyzing strategies: {e}")

    # Note: Citation issues now handled automatically in LLMClient.complete()
    combined_content = ""

    combined_content += f"""{orthodox_content}

{unorthodox_content}

{analysis_content}"""

    # Combine usage statistics
    total_usage = {
        "prompt_tokens": orthodox_usage.get("prompt_tokens", 0)
        + unorthodox_usage.get("prompt_tokens", 0)
        + analysis_usage.get("prompt_tokens", 0),
        "completion_tokens": orthodox_usage.get("completion_tokens", 0)
        + unorthodox_usage.get("completion_tokens", 0)
        + analysis_usage.get("completion_tokens", 0),
        "total_tokens": orthodox_usage.get("total_tokens", 0)
        + unorthodox_usage.get("total_tokens", 0)
        + analysis_usage.get("total_tokens", 0),
    }

    # Store content before verification
    usage = total_usage
    verification_notes = []

    # Run verification on all brainstorm outputs
    click.echo("🔍 Verifying brainstorm strategies...")
    
    # Always verify brainstorm outputs
    try:
        # Use medium verification for creative brainstorming
        correction = analysis_client.verify_with_level(combined_content, "medium")

        # The verification model returns the full, corrected text.
        # We should replace the content, not append to it.
        if correction.strip() and not correction.lower().startswith(
            "no corrections needed"
        ):
            # Parse the verification output to extract only the corrected document
            # The output format is:
            # ## Issues Found during Verification
            # ...
            # ---
            # ## Verified and Corrected Document
            # [actual content]

            if "## Verified and Corrected Document" in correction:
                # Extract only the corrected document portion
                parts = correction.split("## Verified and Corrected Document")
                if len(parts) > 1:
                    corrected_content = parts[1].strip()
                    # Remove any leading system instructions that might have leaked
                    lines = corrected_content.split("\n")
                    filtered_lines = []
                    for line in lines:
                        # Skip lines that are clearly system instructions
                        if line.strip().startswith("Australian law only."):
                            continue
                        filtered_lines.append(line)
                    combined_content = "\n".join(filtered_lines).strip()
                else:
                    # Fallback if parsing fails
                    combined_content = correction
            else:
                # Fallback if expected format not found
                combined_content = correction

            verification_notes.append(
                "--- Strategic Review Applied ---\nContent was updated based on verification."
            )

        # Run citation validation on the potentially corrected content
        citation_issues = analysis_client.validate_citations(combined_content)
        if citation_issues:
            # Append warnings, but don't modify the content further here
            verification_notes.append(
                "--- Citation Warnings ---\n" + "\n".join(citation_issues)
            )

    except Exception as e:
        raise click.ClickException(f"Verification error during brainstorming: {e}")

    # Extract separate reasoning traces for each section
    orthodox_trace = extract_reasoning_trace(orthodox_content, "brainstorm-orthodox")
    unorthodox_trace = extract_reasoning_trace(
        unorthodox_content, "brainstorm-unorthodox"
    )
    analysis_trace = extract_reasoning_trace(analysis_content, "brainstorm-analysis")

    # Keep reasoning traces in main content (they're also saved separately)
    clean_content = combined_content

    # Save to timestamped file only
    output_file = save_command_output(
        f"brainstorm_{area}_{side}",
        clean_content,
        f"{side} in {area} law",
        metadata={
            "Side": side.capitalize(),
            "Area": area.capitalize(),
            "Source": facts_file,
        },
    )

    # Save separate reasoning traces if extracted
    reasoning_files = []

    if orthodox_trace:
        orthodox_reasoning_file = output_file.replace(".txt", "_orthodox_reasoning.txt")
        with open(orthodox_reasoning_file, "w", encoding="utf-8") as f:
            f.write("# ORTHODOX STRATEGIES - REASONING TRACE\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# Command: brainstorm-orthodox\n\n")
            f.write(orthodox_trace.to_markdown())
        reasoning_files.append(("Orthodox", orthodox_reasoning_file))

    if unorthodox_trace:
        unorthodox_reasoning_file = output_file.replace(
            ".txt", "_unorthodox_reasoning.txt"
        )
        with open(unorthodox_reasoning_file, "w", encoding="utf-8") as f:
            f.write("# UNORTHODOX STRATEGIES - REASONING TRACE\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# Command: brainstorm-unorthodox\n\n")
            f.write(unorthodox_trace.to_markdown())
        reasoning_files.append(("Unorthodox", unorthodox_reasoning_file))

    if analysis_trace:
        analysis_reasoning_file = output_file.replace(".txt", "_analysis_reasoning.txt")
        with open(analysis_reasoning_file, "w", encoding="utf-8") as f:
            f.write("# MOST LIKELY TO SUCCEED - REASONING TRACE\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# Command: brainstorm-analysis\n\n")
            f.write(analysis_trace.to_markdown())
        reasoning_files.append(("Most Likely Analysis", analysis_reasoning_file))

    # Report reasoning files
    if reasoning_files:
        click.echo("\n📝 Reasoning traces saved:")
        for trace_type, file_path in reasoning_files:
            click.echo(f'   {trace_type}: "{file_path}"')
    else:
        click.echo("\n📝 No reasoning traces extracted from this generation")

    click.echo(
        "\nTo use these strategies with other commands, manually create or update strategies.txt"
    )

    # Save verification notes separately if any exist
    if verification_notes:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        verification_file = os.path.join(
            OUTPUT_DIR, f"brainstorm_verification_{area}_{side}_{timestamp}.txt"
        )
        with open(verification_file, "w", encoding="utf-8") as f:
            f.write("# Verification Notes for Strategies\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("\n\n".join(verification_notes))
        click.echo(f'Verification notes saved to "{verification_file}"')

    # Save comprehensive audit log
    save_log(
        "brainstorm",
        {
            "inputs": {"facts_file": facts_file, "method": "three-stage approach"},
            "params": "verify=True (auto-enabled for Grok), orthodox_temp=0.3, unorthodox_temp=0.9, analysis_temp=0.4",
            "response": combined_content,  # Log the final, verified content
            "usage": usage,
            "output_file": output_file,
            "stages": {
                "orthodox": {"usage": orthodox_usage, "temperature": 0.3},
                "unorthodox": {"usage": unorthodox_usage, "temperature": 0.9},
                "analysis": {"usage": analysis_usage, "temperature": 0.4},
            },
        },
    )

    # Show summary instead of full content
    click.echo("\n✅ Brainstorm complete!")
    click.echo(f'📄 Strategies saved to: "{output_file}"')
    if verification_notes:
        click.echo(f'📋 Verification notes: open "{verification_file}"')

    # Parse the actual strategies generated
    parsed_result = parse_strategies_file(combined_content)

    click.echo(
        f"\n📊 Generated strategies for {side.capitalize()} in {area.capitalize()} law:"
    )
    click.echo(f"   • Orthodox strategies: {parsed_result.get('orthodox_count', 0)}")
    click.echo(
        f"   • Unorthodox strategies: {parsed_result.get('unorthodox_count', 0)}"
    )
    click.echo(
        f"   • Most likely to succeed: {parsed_result.get('most_likely_count', 0)}"
    )

    click.echo(f'\n💡 View full strategies: open "{output_file}"')
    click.echo("\n📌 To use with strategy command, manually copy to strategies.txt")
