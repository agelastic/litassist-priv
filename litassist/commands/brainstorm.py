"""
Generate comprehensive legal strategies via Grok.

This module implements the 'brainstorm' command which uses Grok's creative capabilities
to generate both orthodox and unorthodox litigation strategies based on provided case facts,
tailored to the specified party (plaintiff/defendant) and legal area.
"""

import click
import os
import re
import logging
import glob

from litassist.config import CONFIG
from litassist.utils import (
    read_document,
    save_log,
    heartbeat,
    timed,
    create_reasoning_prompt,
    parse_strategies_file,
    validate_side_area_combination,
    validate_file_size_limit,
    save_command_output,
    warning_message,
    success_message,
    saved_message,
    stats_message,
    info_message,
    verifying_message,
    tip_message,
    count_tokens_and_words,
)
from litassist.llm import LLMClientFactory, LLMClient
from litassist.prompts import PROMPTS


def analyze_research_size(research_contents: list, research_paths: list) -> dict:
    """
    Analyze the total size of research content and provide user feedback.

    Args:
        research_contents: List of research file contents
        research_paths: List of research file paths for reporting

    Returns:
        Dictionary with analysis results and combined content
    """
    if not research_contents:
        return {
            "combined_content": "",
            "total_tokens": 0,
            "total_words": 0,
            "file_count": 0,
            "exceeds_threshold": False,
        }

    # Combine all research content
    combined_content = "\n\nRESEARCH CONTEXT:\n" + "\n\n".join(research_contents)

    # Count tokens and words
    total_tokens, total_words = count_tokens_and_words(combined_content)

    # Define threshold (128k tokens as conservative estimate)
    TOKEN_THRESHOLD = 128_000
    exceeds_threshold = total_tokens > TOKEN_THRESHOLD

    # Display analysis to user
    click.echo(
        info_message(
            f"Research files loaded: {len(research_contents)} files, "
            f"{total_words:,} words, {total_tokens:,} tokens"
        )
    )

    if exceeds_threshold:
        click.echo(
            warning_message(
                f"Research content is very large ({total_tokens:,} tokens). "
                f"This may impact verification due to context window limits, but proceeding anyway."
            )
        )
        click.echo(
            info_message(
                "Consider using fewer or smaller research files if you encounter verification issues."
            )
        )

    return {
        "combined_content": combined_content,
        "total_tokens": total_tokens,
        "total_words": total_words,
        "file_count": len(research_contents),
        "exceeds_threshold": exceeds_threshold,
    }


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
    original_content = re.sub(
        r"##\s+\w+\s+STRATEGIES\s*\n+", "", original_content.strip()
    )
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
            info_message(
                f"Regeneration attempt {retry_attempt + 1}: {len(strategies_to_regenerate)} strategies need fixing"
            )
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

[Detailed explanation including implementation approach, anticipated challenges, and supporting precedents - aim for 3-5 paragraphs that thoroughly explore the strategy]

Key principles: [Comprehensive legal principles or precedents with full case citations and pinpoint references]
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
                        warning_message(
                            f"    Strategy {strategy_num}: Still has citation issues after regeneration"
                        )
                    )
                    remaining_to_regenerate.append((strategy_num, bad_strategy))
                else:
                    click.echo(
                        success_message(
                            f"    Strategy {strategy_num}: Successfully regenerated with clean citations"
                        )
                    )
                    # Strip any headers from the regenerated strategy
                    new_strategy = re.sub(
                        r"##\s+\w+\s+STRATEGIES\s*\n+", "", new_strategy.strip()
                    )
                    strategy_results[strategy_num] = new_strategy

            except Exception as e:
                click.echo(
                    f"    [FAILED] Strategy {strategy_num}: Regeneration failed - {str(e)}"
                )
                remaining_to_regenerate.append((strategy_num, bad_strategy))

        strategies_to_regenerate = remaining_to_regenerate

    # Report final status
    if strategies_to_regenerate:
        click.echo(
            warning_message(
                f"  {len(strategies_to_regenerate)} {strategy_type} strategies still have citation issues after {max_retries} attempts"
            )
        )
        click.echo(
            info_message(
                f"    Excluding these strategies: {[num for num, _ in strategies_to_regenerate]}"
            )
        )
    else:
        click.echo(
            success_message(
                f"  All {strategy_type} strategies now have verified citations"
            )
        )

    click.echo(
        stats_message(
            f"  Final result: {len(strategy_results)} verified {strategy_type} strategies"
        )
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
        header = (
            "## ORTHODOX STRATEGIES"
            if strategy_type == "orthodox"
            else "## UNORTHODOX STRATEGIES"
        )
        return f"{header}\n\n" + "\n\n".join(renumbered_strategies)
    else:
        return (
            f"No {strategy_type} strategies could be generated with verified citations."
        )


def expand_glob_patterns(ctx, param, value):
    """Expand glob patterns in file paths."""
    if not value:
        return value

    expanded_paths = []
    for pattern in value:
        # Check if it's a glob pattern (contains *, ?, or [)
        if any(char in pattern for char in ["*", "?", "["]):
            # Expand the glob pattern
            matches = glob.glob(pattern)
            if not matches:
                raise click.BadParameter(f"No files matching pattern: {pattern}")
            expanded_paths.extend(matches)
        else:
            # Not a glob pattern, just verify the file exists
            if not os.path.exists(pattern):
                raise click.BadParameter(f"File not found: {pattern}")
            expanded_paths.append(pattern)

    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in expanded_paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)

    return tuple(unique_paths)


@click.command()
@click.option(
    "--facts",
    multiple=True,
    type=click.Path(),  # Remove exists=True since we'll check in callback
    callback=expand_glob_patterns,
    help="Facts files to analyze. Supports glob patterns. Use multiple times: --facts file1.txt --facts 'case_*.txt'. Defaults to case_facts.txt if it exists.",
)
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
    type=click.Path(),  # Remove exists=True since we'll check in callback
    callback=expand_glob_patterns,
    help="Optional: Lookup report files to inform orthodox strategies. Supports glob patterns. "
    "Use multiple times: --research file1.txt --research 'outputs/lookup_*.txt'. "
    "Large research files (>128k tokens) may impact verification performance.",
)
@timed
def brainstorm(facts, side, area, research):
    """
    Generate comprehensive legal strategies via Grok.

    Uses Grok's creative capabilities to generate:
    - 10 orthodox legal strategies
    - 10 unorthodox but potentially effective strategies
    - A list of strategies most likely to succeed

    All strategies are tailored to your specified party side and legal area.
    The output is automatically saved with a timestamp for use in other commands.

    Usage:
        # With default case_facts.txt (if exists in current directory)
        litassist brainstorm --side plaintiff --area civil

        # With single facts file
        litassist brainstorm --facts case_facts.txt --side plaintiff --area civil

        # With multiple facts files
        litassist brainstorm --facts facts1.txt --facts facts2.txt --side plaintiff --area civil

        # With multiple research files
        litassist brainstorm --side plaintiff --area civil --research lookup1.txt --research lookup2.txt

        # With glob patterns for research files
        litassist brainstorm --side plaintiff --area civil --research 'outputs/lookup_*gift*.txt'

    Note: Verification is automatically performed on all brainstorm outputs to ensure citation accuracy and legal soundness.

    Raises:
        click.ClickException: If there are errors reading the facts files or with the LLM API call.
    """
    # Check for potentially incompatible side/area combinations
    validate_side_area_combination(side, area)

    # Handle facts files - use default case_facts.txt if no facts provided
    if not facts:
        default_facts = "case_facts.txt"
        if os.path.exists(default_facts):
            facts = (default_facts,)
            click.echo(f"Using default facts file: {default_facts}")
        else:
            raise click.ClickException(
                "No facts files provided and case_facts.txt not found in current directory. "
                "Use --facts to specify one or more facts files."
            )

    # Combine multiple facts files if provided
    facts_contents = []
    facts_sources = []
    for facts_file in facts:
        content = read_document(facts_file)
        facts_contents.append(content)
        facts_sources.append(facts_file)

    # Log which facts files are being used
    if len(facts_sources) == 1:
        click.echo(f"Using facts from: {facts_sources[0]}")
    else:
        click.echo(f"Using facts from {len(facts_sources)} files:")
        for source in facts_sources:
            click.echo(f"  • {source}")

    # Combine facts with source attribution if multiple files
    if len(facts_contents) == 1:
        combined_facts = facts_contents[0]
    else:
        combined_parts = []
        for i, (source, content) in enumerate(zip(facts_sources, facts_contents)):
            combined_parts.append(f"=== SOURCE: {source} ===\n{content}")
        combined_facts = "\n\n".join(combined_parts)

    facts = combined_facts

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

        # Analyze research size and provide user feedback
        research_analysis = analyze_research_size(research_contexts, list(research))
        research_context = research_analysis["combined_content"]

        # Log research analysis for debugging
        logging.debug(f"Research analysis: {research_analysis}")
    else:
        research_context = ""
        research_analysis = {
            "total_tokens": 0,
            "total_words": 0,
            "file_count": 0,
            "exceeds_threshold": False,
        }

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
   [Detailed explanation including implementation approach, anticipated challenges, and supporting precedents - aim for 3-5 paragraphs that thoroughly explore the strategy]
   Key principles: [Comprehensive legal principles or precedents with full case citations and pinpoint references]

2. [Strategy Title]
   [Detailed explanation with same depth as above]
   Key principles: [Comprehensive legal principles with full citations]

[Continue for 10 orthodox strategies with similar detail]"""

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
            info_message(
                f"Found {len(orthodox_citation_issues)-1} citation issues in orthodox strategies - fixing..."
            )
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
   [Detailed explanation exploring the creative approach, implementation pathway, potential obstacles, and transformative impact - aim for 3-5 paragraphs that fully develop the innovative strategy]
   Key principles: [Comprehensive legal principles or novel arguments with supporting authorities and creative interpretations]

2. [Strategy Title]
   [Detailed explanation with same depth as above]
   Key principles: [Comprehensive legal principles or innovative theories with full analysis]

[Continue for 10 unorthodox strategies with similar detail]"""

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
            info_message(
                f"Found {len(unorthodox_citation_issues)-1} citation issues in unorthodox strategies - fixing..."
            )
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

    # Run verification on all brainstorm outputs
    click.echo(verifying_message("Verifying brainstorm strategies..."))

    # Always verify brainstorm outputs
    try:
        # Use medium verification for creative brainstorming
        correction = analysis_client.verify(combined_content)

        # The verification model returns the full, corrected text.
        # We should replace the content, not append to it.
        if correction.strip() and not correction.lower().startswith(
            "no corrections needed"
        ):
            # Trust the well-prompted LLM to return the correct format
            # Following CLAUDE.md: "minimize local parsing through better prompt engineering"
            combined_content = correction

        # Run citation validation on the potentially corrected content
        citation_issues = analysis_client.validate_citations(combined_content)
        if citation_issues:
            # Citation warnings are shown in console but not saved separately
            click.echo(
                warning_message(f"{len(citation_issues)} citation warnings found")
            )

    except Exception as e:
        raise click.ClickException(f"Verification error during brainstorming: {e}")

    # Save to timestamped file only (reasoning traces remain inline in the content)
    output_file = save_command_output(
        f"brainstorm_{area}_{side}",
        combined_content,
        f"{side} in {area} law",
        metadata={
            "Side": side.capitalize(),
            "Area": area.capitalize(),
            "Source": (
                ", ".join(facts_sources) if len(facts_sources) > 1 else facts_sources[0]
            ),
        },
    )

    click.echo(
        "\nTo use these strategies with other commands, manually create or update strategies.txt"
    )

    # Save comprehensive audit log
    save_log(
        "brainstorm",
        {
            "inputs": {
                "facts_files": facts_sources,
                "research_files": list(research) if research else [],
                "research_analysis": research_analysis,
            },
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
    click.echo(f"\n{success_message('Brainstorm complete!')}")
    click.echo(saved_message(f'Strategies saved to: "{output_file}"'))

    # Parse the actual strategies generated
    parsed_result = parse_strategies_file(combined_content)

    msg = stats_message(
        f"Generated strategies for {side.capitalize()} in {area.capitalize()} law:"
    )
    click.echo(f"\n{msg}")
    click.echo(f"   • Orthodox strategies: {parsed_result.get('orthodox_count', 0)}")
    click.echo(
        f"   • Unorthodox strategies: {parsed_result.get('unorthodox_count', 0)}"
    )
    click.echo(
        f"   • Most likely to succeed: {parsed_result.get('most_likely_count', 0)}"
    )

    tip_msg = tip_message(f'View full strategies: open "{output_file}"')
    click.echo(f"\n{tip_msg}")
    info_msg = info_message(
        "To use with strategy command, manually copy to strategies.txt"
    )
    click.echo(f"\n{info_msg}")
