"""
Legal strategy generation for Australian civil proceedings.

This module implements the 'strategy' command which analyzes case facts and
generates procedural options, strategic recommendations, and draft legal
documents for Australian civil litigation matters.
"""

import click
from typing import List
import re
import time

from litassist.config import CONFIG
from litassist.utils import (
    save_log,
    heartbeat,
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
    save_command_output,
    verify_content_if_needed,
)
from litassist.llm import LLMClientFactory
from litassist.prompts import PROMPTS


def validate_case_facts_format(text: str) -> bool:
    """
    Validates that the case facts file follows the required 10-heading structure.

    Args:
        text: The content of the case facts file.

    Returns:
        True if valid, False if not valid.
    """
    required_headings = [
        "Parties",
        "Background",
        "Key Events",
        "Legal Issues",
        "Evidence Available",
        "Opposing Arguments",
        "Procedural History",
        "Jurisdiction",
        "Applicable Law",
        "Client Objectives",
    ]

    missing_headings = []

    # Check if all required headings exist in the text (less restrictive)
    for heading in required_headings:
        # Look for heading with flexible formatting:
        # - Can have non-alphabetical chars before/after
        # - Case insensitive
        # - Must be on its own line (but can have punctuation)
        pattern = r"^\s*[^a-zA-Z]*" + re.escape(heading) + r"[^a-zA-Z]*\s*$"
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            missing_headings.append(heading)

    if missing_headings:
        import click

        click.echo(f"Missing required headings: {', '.join(missing_headings)}")
        click.echo("Note: Headings are now case-insensitive and can have punctuation.")
        return False

    return True


def extract_legal_issues(case_text: str) -> List[str]:
    """
    Extract legal issues from the case facts text.

    Args:
        case_text: Full text of the case facts.

    Returns:
        List of identified legal issues.
    """
    # Extract the "Legal Issues" section (less restrictive)
    # Look for "Legal Issues" with flexible formatting
    match = re.search(
        r"[^a-zA-Z]*Legal\s+Issues[^a-zA-Z]*\s*\n(.*?)(?:\n\s*[^a-zA-Z]*(?:Evidence\s+Available|Opposing\s+Arguments)[^a-zA-Z]*)",
        case_text,
        re.DOTALL | re.IGNORECASE,
    )

    if not match:
        return []

    # Extract individual issues (assuming one per line or bullet point)
    issues_text = match.group(1).strip()
    issues = [
        issue.strip().strip("•-*")
        for issue in re.split(r"\n+|•|\*|-", issues_text)
        if issue.strip()
    ]

    return issues


@timed
def create_consolidated_reasoning_trace(option_traces, outcome):
    """Create a consolidated reasoning trace from multiple strategy options."""

    consolidated_content = "# CONSOLIDATED REASONING\n"
    consolidated_content += f"# Strategic Options for: {outcome}\n"
    consolidated_content += f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    for trace_data in option_traces:
        option_num = trace_data["option_number"]
        trace = trace_data["trace"]

        consolidated_content += (
            f"## STRATEGIC OPTION {option_num} - REASONING\n\n"
        )

        if trace:
            consolidated_content += f"**Issue:** {trace.issue}\n\n"
            consolidated_content += f"**Applicable Law:** {trace.applicable_law}\n\n"
            consolidated_content += f"**Application to Facts:** {trace.application}\n\n"
            consolidated_content += f"**Conclusion:** {trace.conclusion}\n\n"
            consolidated_content += f"**Confidence:** {trace.confidence}%\n\n"
            if trace.sources:
                consolidated_content += f"**Sources:** {', '.join(trace.sources)}\n\n"
        else:
            consolidated_content += "No reasoning trace available for this option.\n\n"

        consolidated_content += "-" * 80 + "\n\n"

    return consolidated_content


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
@timed
def strategy(case_facts, outcome, strategies, verify):
    """
    Generate legal strategy options and draft documents for Australian civil matters.

    Analyses the provided case facts according to the ten-heading LitAssist structure
    and produces strategic options, recommended next steps, and appropriate draft
    legal documents to achieve the desired outcome.

    Args:
        case_facts: Path to the case facts text file (structured with 10 LitAssist headings).
        outcome: A single sentence describing the desired outcome.

    Examples:
        litassist strategy case_facts.txt --outcome "Obtain interim relocation orders"
        litassist strategy case_facts.txt --outcome "Set aside default judgment"
    """
    # Read and validate case facts
    facts_content = case_facts.read()

    # Check file size to prevent token limit issues
    validate_file_size_limit(facts_content, 50000, "Case facts")

    if not validate_case_facts_format(facts_content):
        raise click.ClickException(
            "Case facts file does not follow the required 10-heading structure."
        )

    # Extract legal issues from case facts
    legal_issues = extract_legal_issues(facts_content)
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

    # strategy always needs verification as it creates foundational strategic documents
    if verify:
        click.echo(
            warning_message(
                "Note: --verify flag ignored - strategy command always uses verification for accuracy"
            )
        )
    elif not verify:
        click.echo(
            info_message(
                "Note: Strategy command automatically uses verification for accuracy"
            )
        )
    verify = True  # Force verification for critical accuracy

    # Generate strategic options
    system_prompt = PROMPTS.get("commands.strategy.system")

    # Enhance prompt if strategies are provided
    if parsed_strategies and parsed_strategies["most_likely_count"] > 0:
        system_prompt += f"\n\nYou have been provided with brainstormed strategies including {parsed_strategies['most_likely_count']} strategies marked as most likely to succeed. Pay particular attention to these when developing your strategic options."
    elif parsed_strategies:
        system_prompt += "\n\nYou have been provided with brainstormed strategies including orthodox and unorthodox approaches. Consider these when developing your strategic options, but focus on those most relevant to the specific outcome requested."

    # Use centralized strategic options instructions
    strategic_instructions = PROMPTS.get(
        "strategies.strategy.strategic_options_instructions"
    )
    system_prompt += f"\n\n{strategic_instructions}"

    base_user_prompt = f"""CASE FACTS:
{facts_content}

DESIRED OUTCOME:
{outcome}

IDENTIFIED LEGAL ISSUES:
{', '.join(legal_issues)}
"""

    # Add strategies content if provided
    if parsed_strategies:
        base_user_prompt += "\nBRAINSTORMED STRATEGIES PROVIDED:\n"
        base_user_prompt += (
            f"- {parsed_strategies['orthodox_count']} orthodox strategies\n"
        )
        base_user_prompt += (
            f"- {parsed_strategies['unorthodox_count']} unorthodox strategies\n"
        )
        base_user_prompt += f"- {parsed_strategies['most_likely_count']} marked as most likely to succeed\n"
        base_user_prompt += f"\nFULL BRAINSTORMED CONTENT:\n{strategies_content}\n"
        base_user_prompt += "\nBuild upon the strategies marked as most likely to succeed, and consider how the orthodox strategies can be refined for the specific outcome requested.\n"

    # Add reasoning trace to the prompt
    user_prompt = create_reasoning_prompt(base_user_prompt, "strategy")

    # Generate strategic options - prioritize brainstormed strategies if available
    click.echo("Generating strategic options...")
    valid_options = []
    option_reasoning_traces = []  # Store reasoning traces for each option
    total_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    call_with_hb = heartbeat(CONFIG.heartbeat_interval)(llm_client.complete)

    # Extract and rank strategies using LLM analysis
    priority_strategies = []
    target_options = 4  # Target 3-5 options, need this defined early

    if parsed_strategies:
        # First, extract all available strategies from the content
        all_strategies = []

        # Extract from "MOST LIKELY TO SUCCEED" section if it exists
        if parsed_strategies["most_likely_count"] > 0:
            likely_match = re.search(
                r"## MOST LIKELY TO SUCCEED\n(.*?)(?====|\Z)",
                strategies_content,
                re.DOTALL,
            )
            if likely_match:
                likely_text = likely_match.group(1)
                strategy_patterns = re.findall(
                    r"(^\d+\..*?)(?=^\d+\.|\Z)", likely_text, re.DOTALL | re.MULTILINE
                )
                for pattern in strategy_patterns:
                    strategy_title = re.search(r"\d+\.\s*([^\n]+)", pattern)
                    if strategy_title and len(pattern.strip()) > 50:
                        all_strategies.append(
                            {
                                "title": strategy_title.group(1).strip(),
                                "content": pattern.strip(),
                                "source": "most_likely",
                            }
                        )

        # Extract from ORTHODOX section
        if parsed_strategies["orthodox_count"] > 0:
            orthodox_match = re.search(
                r"## ORTHODOX STRATEGIES\n(.*?)(?=## [A-Z]|===|\Z)",
                strategies_content,
                re.DOTALL,
            )
            if orthodox_match:
                orthodox_text = orthodox_match.group(1)
                strategy_patterns = re.findall(
                    r"(^\d+\..*?)(?=^\d+\.|\Z)", orthodox_text, re.DOTALL | re.MULTILINE
                )
                for pattern in strategy_patterns:
                    strategy_title = re.search(r"\d+\.\s*([^\n]+)", pattern)
                    if strategy_title and len(pattern.strip()) > 50:
                        all_strategies.append(
                            {
                                "title": strategy_title.group(1).strip(),
                                "content": pattern.strip(),
                                "source": "orthodox",
                            }
                        )

        # Extract from UNORTHODOX section
        if parsed_strategies["unorthodox_count"] > 0:
            unorthodox_match = re.search(
                r"## UNORTHODOX STRATEGIES\n(.*?)(?=## [A-Z]|===|\Z)",
                strategies_content,
                re.DOTALL,
            )
            if unorthodox_match:
                unorthodox_text = unorthodox_match.group(1)
                strategy_patterns = re.findall(
                    r"(^\d+\..*?)(?=^\d+\.|\Z)",
                    unorthodox_text,
                    re.DOTALL | re.MULTILINE,
                )
                for pattern in strategy_patterns:
                    strategy_title = re.search(r"\d+\.\s*([^\n]+)", pattern)
                    if strategy_title and len(pattern.strip()) > 50:
                        all_strategies.append(
                            {
                                "title": strategy_title.group(1).strip(),
                                "content": pattern.strip(),
                                "source": "unorthodox",
                            }
                        )

        # Fallback: Extract any numbered strategies if no structured sections found
        if not all_strategies and strategies_content:
            click.echo(
                info_message(
                    "  No structured sections found - extracting any numbered strategies"
                )
            )
            all_strategy_patterns = re.findall(
                r"(^\d+\..*?)(?=^\d+\.|\Z)",
                strategies_content,
                re.DOTALL | re.MULTILINE,
            )
            valid_patterns = [p for p in all_strategy_patterns if len(p.strip()) > 50]

            for pattern in valid_patterns:
                strategy_title = re.search(r"\d+\.\s*([^\n]+)", pattern)
                if strategy_title:
                    all_strategies.append(
                        {
                            "title": strategy_title.group(1).strip(),
                            "content": pattern.strip(),
                            "source": "unstructured",
                        }
                    )

        # Use LLM ranking only if no "most likely to succeed" strategies are available
        if all_strategies:
            # Check if we have "most likely to succeed" strategies already identified
            most_likely_strategies = [
                s for s in all_strategies if s["source"] == "most_likely"
            ]

            if most_likely_strategies:
                # Use the pre-analyzed "most likely" strategies directly - no need to re-analyze
                click.echo(
                    info_message(
                        f"  Using {len(most_likely_strategies)} pre-analyzed 'most likely to succeed' strategies"
                    )
                )
                priority_strategies = most_likely_strategies[:target_options]

                # Fill remaining slots with other strategies if needed
                if len(priority_strategies) < target_options:
                    # Get strategies not already used, avoiding duplicates by title
                    used_titles = {
                        s["title"].lower().strip() for s in priority_strategies
                    }
                    other_strategies = [
                        s
                        for s in all_strategies
                        if s["source"] != "most_likely"
                        and s["title"].lower().strip() not in used_titles
                    ]
                    remaining_needed = target_options - len(priority_strategies)

                    if other_strategies and remaining_needed > 0:
                        # Intelligently select additional strategies rather than just taking first N
                        click.echo(
                            info_message(
                                f"    Analyzing remaining {len(other_strategies)} unique strategies to fill {remaining_needed} slots..."
                            )
                        )
                        if len(other_strategies) < len(
                            [s for s in all_strategies if s["source"] != "most_likely"]
                        ):
                            click.echo(
                                info_message(
                                    "    Excluded duplicate strategy titles already in 'most likely' selection"
                                )
                            )

                        # Create ranking prompt for remaining strategies
                        remaining_strategies_list = ""
                        for i, strategy in enumerate(other_strategies, 1):
                            remaining_strategies_list += f"\n{i}. {strategy['title']} (from {strategy['source']} strategies)\n{strategy['content'][:200]}...\n"

                        remaining_ranking_prompt = f"""CASE FACTS:
{facts_content}

DESIRED OUTCOME:
{outcome}

We have already selected {len(priority_strategies)} 'most likely to succeed' strategies. Now rank these remaining strategies by likelihood of success for achieving "{outcome}":

{remaining_strategies_list}

Rank them using the same criteria: legal merit, factual support, precedential strength, and judicial likelihood for this specific outcome.

Output format:
RANKING: [comma-separated list of strategy numbers in order of likelihood, e.g., "2,1,4"]
REASONING: [brief explanation for top selections]"""

                        try:
                            analysis_client = LLMClientFactory.for_command(
                                "strategy", "analysis"
                            )

                            remaining_response, _ = analysis_client.complete(
                                [
                                    {
                                        "role": "system",
                                        "content": PROMPTS.get(
                                            "commands.strategy.ranking_system"
                                        ),
                                    },
                                    {
                                        "role": "user",
                                        "content": remaining_ranking_prompt,
                                    },
                                ]
                            )

                            # Parse the ranking for remaining strategies
                            remaining_match = re.search(
                                r"RANKING:\s*([0-9,\s]+)", remaining_response
                            )
                            if remaining_match:
                                remaining_ranking_str = remaining_match.group(1).strip()
                                remaining_indices = [
                                    int(x.strip()) - 1
                                    for x in remaining_ranking_str.split(",")
                                    if x.strip().isdigit()
                                ]

                                # Add top-ranked remaining strategies
                                for idx in remaining_indices[:remaining_needed]:
                                    if 0 <= idx < len(other_strategies):
                                        strategy = other_strategies[idx].copy()
                                        strategy["supplemental_ranked"] = True
                                        priority_strategies.append(strategy)

                                click.echo(
                                    stats_message(
                                        f"    Intelligently selected {len(priority_strategies) - len(most_likely_strategies)} additional strategies"
                                    )
                                )
                            else:
                                # Fallback to first N if parsing fails
                                priority_strategies.extend(
                                    other_strategies[:remaining_needed]
                                )
                                click.echo(
                                    info_message(
                                        f"    Added {min(remaining_needed, len(other_strategies))} additional strategies (fallback)"
                                    )
                                )

                        except Exception:
                            # Fallback to first N if analysis fails
                            priority_strategies.extend(
                                other_strategies[:remaining_needed]
                            )
                            click.echo(
                                info_message(
                                    f"    Added {min(remaining_needed, len(other_strategies))} additional strategies (analysis failed)"
                                )
                            )

            else:
                # No "most likely" pre-analysis available - run intelligent ranking
                click.echo(
                    info_message(
                        f"  No 'most likely' strategies found - analyzing {len(all_strategies)} strategies for '{outcome}'..."
                    )
                )

                # Create ranking prompt
                strategies_list = ""
                for i, strategy in enumerate(all_strategies, 1):
                    strategies_list += f"\n{i}. {strategy['title']} (from {strategy['source']} strategies)\n{strategy['content'][:200]}...\n"

                ranking_prompt = f"""CASE FACTS:
{facts_content}

DESIRED OUTCOME:
{outcome}

AVAILABLE STRATEGIES:
{strategies_list}

Analyze all {len(all_strategies)} strategies above and rank them by likelihood of success for achieving the specific outcome "{outcome}" given these case facts.

Use the SAME criteria as brainstorm command's "most likely to succeed" analysis:
- Legal merit and strength of legal foundation
- Factual support from the case materials provided
- Precedential strength and established legal principles
- Likelihood of judicial acceptance in Australian courts

Additional focus for this specific outcome:
- Direct relevance to achieving "{outcome}"
- Procedural feasibility for this specific result
- Practical implementation steps available

Output format:
RANKING: [comma-separated list of strategy numbers in order of likelihood, e.g., "3,1,7,2"]
REASONING: [brief explanation focusing on legal merit, factual support, precedential strength, and judicial likelihood for the top strategies]"""

                try:
                    # Use dedicated analysis model for consistency with brainstorm command
                    analysis_client = LLMClientFactory.for_command(
                        "strategy", "analysis"
                    )

                    ranking_response, _ = analysis_client.complete(
                        [
                            {
                                "role": "system",
                                "content": PROMPTS.get(
                                    "commands.brainstorm.analysis_system"
                                ),
                            },
                            {"role": "user", "content": ranking_prompt},
                        ]
                    )

                    # Parse the ranking
                    ranking_match = re.search(
                        r"RANKING:\s*([0-9,\s]+)", ranking_response
                    )
                    if ranking_match:
                        ranking_str = ranking_match.group(1).strip()
                        try:
                            # Parse comma-separated numbers
                            strategy_indices = [
                                int(x.strip()) - 1
                                for x in ranking_str.split(",")
                                if x.strip().isdigit()
                            ]

                            # Reorder strategies based on LLM ranking, take top target_options
                            for idx in strategy_indices[:target_options]:
                                if 0 <= idx < len(all_strategies):
                                    strategy = all_strategies[idx].copy()
                                    strategy["llm_ranked"] = True
                                    priority_strategies.append(strategy)

                            click.echo(
                                stats_message(
                                    f"    Selected top {len(priority_strategies)} strategies based on legal analysis"
                                )
                            )

                            # Show reasoning if available
                            reasoning_match = re.search(
                                r"REASONING:\s*(.*?)(?:\n\n|\Z)",
                                ranking_response,
                                re.DOTALL,
                            )
                            if reasoning_match:
                                reasoning = reasoning_match.group(1).strip()
                                click.echo(
                                    tip_message(f"    Analysis: {reasoning[:150]}...")
                                    if len(reasoning) > 150
                                    else tip_message(f"    Analysis: {reasoning}")
                                )

                        except (ValueError, IndexError):
                            click.echo(
                                warning_message(
                                    "    Could not parse strategy ranking, using fallback selection"
                                )
                            )
                            # Fallback to first target_options strategies
                            priority_strategies = all_strategies[:target_options]
                    else:
                        click.echo(
                            warning_message(
                                "    No ranking found in response, using fallback selection"
                            )
                        )
                        priority_strategies = all_strategies[:target_options]

                except Exception as e:
                    click.echo(
                        warning_message(
                            f"    Strategy ranking failed ({str(e)}), using fallback selection"
                        )
                    )
                    priority_strategies = all_strategies[:target_options]

        else:
            click.echo(info_message("  No strategies found in provided file"))

    # Target 3-5 options, prioritizing brainstormed strategies
    max_attempts = 7
    # target_options already defined above

    for attempt in range(1, max_attempts + 1):
        if len(valid_options) >= target_options:
            break

        click.echo(info_message(f"  Generating option {attempt}..."))

        # Determine if we should use a specific brainstormed strategy
        use_brainstormed = False
        specific_strategy = None

        if priority_strategies and attempt <= len(priority_strategies):
            # Use one of the priority strategies as foundation
            specific_strategy = priority_strategies[attempt - 1]
            use_brainstormed = True
            strategy_source = specific_strategy.get("source", "brainstormed")
            click.echo(
                info_message(
                    f"    Building on {strategy_source} strategy: '{specific_strategy['title']}'"
                )
            )

        # Individual option prompt
        if use_brainstormed and specific_strategy:
            individual_prompt = (
                user_prompt
                + f"""

SPECIFIC INSTRUCTION: Transform the following brainstormed strategy into a detailed strategic option for the specific outcome "{outcome}":

BRAINSTORMED STRATEGY TO DEVELOP:
{specific_strategy['content']}

Generate ONE strategic option based on this brainstormed strategy (this will be option #{len(valid_options) + 1}). Use the exact format specified for a single OPTION, but develop this specific brainstormed strategy into concrete strategic steps for achieving "{outcome}".

{PROMPTS.get('strategies.strategy.unique_title_requirement')}

Focus on:
- How this brainstormed strategy applies specifically to achieving "{outcome}"
- Concrete legal steps to implement this strategy
- Specific hurdles and missing facts for this approach
- Probability assessment based on this strategy's legal foundation
- Ensure the OPTION title clearly distinguishes this approach from other strategies"""
            )
        else:
            # Generate fresh strategic option if no brainstormed strategies or we've used them all
            individual_prompt = (
                user_prompt
                + f"\n\nGenerate ONE strategic option (this will be option #{len(valid_options) + 1}) to achieve the desired outcome. Use the exact format specified for a single OPTION."
            )
            individual_prompt += (
                f"\n\n{PROMPTS.get('strategies.strategy.unique_title_requirement')}"
            )
            if parsed_strategies:
                individual_prompt += f"\n\nConsider the brainstormed strategies provided but develop a new approach that complements the {len(valid_options)} options already generated."

        # If we already have options, tell the LLM to avoid duplication
        if valid_options:
            existing_titles = []
            for existing_option in valid_options:
                title_match = re.search(r"## OPTION \d+: (.+)", existing_option)
                if title_match:
                    existing_titles.append(title_match.group(1).strip())

            if existing_titles:
                individual_prompt += (
                    f"\n\nEXISTING OPTION TITLES TO AVOID: {', '.join(existing_titles)}"
                )
            individual_prompt += f"\n\nPreviously generated {len(valid_options)} options. Generate a DIFFERENT strategic approach with a UNIQUE TITLE that has not been covered yet."

        try:
            option_content, option_usage = call_with_hb(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": individual_prompt},
                ]
            )

            # Validate citations immediately
            citation_issues = llm_client.validate_citations(option_content)
            if citation_issues:
                click.echo(
                    error_message(
                        f"    Option {attempt}: Found {len(citation_issues)-1} citation issues - discarding"
                    )
                )
                continue
            else:
                click.echo(
                    success_message(
                        f"    Option {attempt}: Citations verified - keeping"
                    )
                )

                # Extract reasoning trace from this option before cleaning
                option_trace = extract_reasoning_trace(option_content, "strategy")
                if option_trace:
                    option_reasoning_traces.append(
                        {"option_number": len(valid_options) + 1, "trace": option_trace}
                    )

                # Keep reasoning trace in option content (it's also saved separately)
                clean_option_content = option_content

                valid_options.append(clean_option_content)

                # Accumulate usage stats
                for key in total_usage:
                    total_usage[key] += option_usage.get(key, 0)

        except Exception as e:
            click.echo(f"    💥 Option {attempt}: Generation failed - {str(e)}")
            continue

    # Combine valid options into final strategy content
    if valid_options:
        strategy_header = f"# STRATEGIC OPTIONS FOR: {outcome.upper()}\n\n"

        # Renumber options sequentially
        numbered_options = []
        for i, option in enumerate(valid_options, 1):
            # Clean up the option content and add proper numbering
            clean_option = option.strip()

            # Remove duplicate strategy header if present
            header_pattern = r"^#\s*STRATEGIC OPTIONS FOR:.*?\n\n"
            clean_option = re.sub(header_pattern, "", clean_option, flags=re.IGNORECASE)
            clean_option = clean_option.strip()

            if not clean_option.startswith("## OPTION"):
                clean_option = f"## OPTION {i}: [Generated Strategy]\n{clean_option}"
            else:
                # Replace existing numbering
                clean_option = re.sub(
                    r"^## OPTION \d+:", f"## OPTION {i}:", clean_option
                )
            numbered_options.append(clean_option)

        strategy_content = strategy_header + "\n\n".join(numbered_options)
        usage = total_usage

        click.echo(
            stats_message(
                f"  Successfully generated {len(valid_options)} verified strategic options"
            )
        )
    else:
        # No valid options could be generated
        strategy_content = f"# STRATEGIC OPTIONS FOR: {outcome.upper()}\n\n## NO VALID OPTIONS GENERATED\n\nUnable to generate strategic options with verified citations after {max_attempts} attempts. Please refine the case facts or desired outcome and try again."
        usage = total_usage
        click.echo(
            warning_message(
                f"  Could not generate any options with verified citations after {max_attempts} attempts"
            )
        )

    # Generate recommended next steps using centralized prompt
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

    # Determine appropriate document type based on outcome
    doc_type = "claim"  # Default
    if any(
        term in outcome.lower()
        for term in ["injunction", "order", "interim", "stay", "restraint"]
    ):
        doc_type = "application"
    elif any(
        term in outcome.lower()
        for term in ["affidavit", "evidence", "witness", "sworn"]
    ):
        doc_type = "affidavit"

    # Generate draft document
    doc_formats = {
        "claim": PROMPTS.get("documents.statement_of_claim"),
        "application": PROMPTS.get("documents.originating_application"),
        "affidavit": PROMPTS.get("documents.affidavit"),
    }

    # Use centralized document generation context
    doc_context = PROMPTS.get("strategies.strategy.document_generation_context")
    doc_prompt = f"""{doc_context.format(recommended_strategy=f"draft a {doc_type.upper()} to achieve the outcome: '{outcome}'")}

{doc_formats.get(doc_type, doc_formats['claim'])}"""

    try:
        document_content, _ = llm_client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": strategy_content},
                {"role": "user", "content": doc_prompt},
            ]
        )
    except Exception as e:
        raise click.ClickException(f"LLM document generation error: {e}")

    # Combine all outputs
    output = (
        strategy_content
        + "\n\n"
        + next_steps_content
        + "\n\n"
        + "--- DRAFT DOCUMENT ---\n\n"
        + document_content
    )

    # CRITICAL: Validate citations immediately to prevent cascade errors
    citation_issues = llm_client.validate_citations(output)
    if citation_issues:
        # Prepend warnings prominently
        citation_warning = "--- CITATION VALIDATION WARNINGS ---\n"
        citation_warning += "\n".join(citation_issues)
        citation_warning += "\n" + "-" * 40 + "\n\n"
        output = citation_warning + output

    # Apply verification (always required for strategy)
    output, _ = verify_content_if_needed(
        llm_client, output, "strategy", verify_flag=True
    )

    # Create consolidated reasoning trace from all options
    consolidated_reasoning = None
    if option_reasoning_traces:
        consolidated_reasoning = create_consolidated_reasoning_trace(
            option_reasoning_traces, outcome
        )

    # Save output using utility
    metadata = {"Desired Outcome": outcome, "Case Facts File": case_facts.name}
    if strategies:
        metadata["Strategies File"] = strategies.name

    output_file = save_command_output("strategy", output, outcome, metadata=metadata)

    # Reasoning trace is embedded in the main output, not saved separately

    # Save audit log
    save_log(
        "strategy",
        {
            "inputs": {"case_facts": facts_content, "outcome": outcome},
            "params": {
                "model": "openai/gpt-4o",
                "temperature": 0.2,
                "top_p": 0.9,
                "verification": "auto-enabled (heavy)",
            },
            "usage": usage,
            "response": output,
            "output_file": output_file,
        },
    )

    # Show summary instead of full output
    click.echo(f"\n{success_message('Strategy generation complete!')}")
    click.echo(saved_message(f'Output saved to: "{output_file}"'))
    if consolidated_reasoning:
        click.echo(
            info_message(
                f"Reasoning traces: open \"{output_file.replace('.txt', '_reasoning.txt')}\""
            )
        )

    # Show what was generated
    msg = stats_message(
        f"Generated {len(valid_options)} strategic options for: {outcome}"
    )
    click.echo(f"\n{msg}")

    # Brief preview of options
    click.echo(f"\n{info_message('Strategic options generated:')}")
    for i, option in enumerate(valid_options, 1):
        # Extract option title
        title_match = re.search(r"## OPTION \d+: (.+)", option)
        if title_match:
            click.echo(f"   {i}. {title_match.group(1)}")

    msg = tip_message(f'View full strategy: open "{output_file}"')
    click.echo(f"\n{msg}")
