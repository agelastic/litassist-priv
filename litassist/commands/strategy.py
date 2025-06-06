"""
Legal strategy generation for Australian civil proceedings.

This module implements the 'strategy' command which analyzes case facts and
generates procedural options, strategic recommendations, and draft legal
documents for Australian civil litigation matters.
"""

import click
from typing import Dict, List, Any, Tuple
import re
import time
import os

from litassist.config import CONFIG
from litassist.utils import (
    save_log, heartbeat, OUTPUT_DIR,
    create_reasoning_prompt, extract_reasoning_trace, save_reasoning_trace, LegalReasoningTrace
)
from litassist.llm import LLMClient


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


def parse_strategies_file(strategies_text: str) -> Dict[str, Any]:
    """
    Parse the strategies.txt file to extract basic counts and metadata.
    
    Since we pass the full content to the LLM anyway, we just need rough counts
    for the user display, not detailed parsing.
    
    Args:
        strategies_text: Content of the strategies.txt file.
        
    Returns:
        Dictionary containing basic strategies information.
    """
    parsed = {
        "metadata": {},
        "orthodox_count": 0,
        "unorthodox_count": 0,
        "most_likely_count": 0,
        "raw_content": strategies_text
    }
    
    # Extract metadata from header comments
    metadata_match = re.search(r"# Side: (.+)\n# Area: (.+)", strategies_text)
    if metadata_match:
        parsed["metadata"]["side"] = metadata_match.group(1).strip()
        parsed["metadata"]["area"] = metadata_match.group(2).strip()
    
    # Extract and count each section separately to avoid cross-contamination
    
    # Find ORTHODOX STRATEGIES section
    orthodox_match = re.search(r'## ORTHODOX STRATEGIES\n(.*?)(?=## [A-Z]|===|\Z)', strategies_text, re.DOTALL)
    if orthodox_match:
        orthodox_text = orthodox_match.group(1)
        parsed["orthodox_count"] = len(re.findall(r'^\d+\.', orthodox_text, re.MULTILINE))
    
    # Find UNORTHODOX STRATEGIES section  
    unorthodox_match = re.search(r'## UNORTHODOX STRATEGIES\n(.*?)(?=## [A-Z]|===|\Z)', strategies_text, re.DOTALL)
    if unorthodox_match:
        unorthodox_text = unorthodox_match.group(1)
        parsed["unorthodox_count"] = len(re.findall(r'^\d+\.', unorthodox_text, re.MULTILINE))
    
    # Find MOST LIKELY TO SUCCEED section
    likely_match = re.search(r'## MOST LIKELY TO SUCCEED\n(.*?)(?====|\Z)', strategies_text, re.DOTALL)
    if likely_match:
        likely_text = likely_match.group(1)
        parsed["most_likely_count"] = len(re.findall(r'^\d+\.', likely_text, re.MULTILINE))
    
    return parsed


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


def create_consolidated_reasoning_trace(option_traces, outcome):
    """Create a consolidated reasoning trace from multiple strategy options."""
    
    consolidated_content = f"# CONSOLIDATED LEGAL REASONING TRACE\n"
    consolidated_content += f"# Strategic Options for: {outcome}\n"
    consolidated_content += f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for trace_data in option_traces:
        option_num = trace_data["option_number"]
        trace = trace_data["trace"]
        
        consolidated_content += f"## STRATEGIC OPTION {option_num} - REASONING TRACE\n\n"
        
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
@click.option("--strategies", type=click.File("r"), help="Optional strategies file from brainstorm command")
@click.option("--verify", is_flag=True, help="Enable self-critique pass (default: auto-enabled)")
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
    if len(facts_content) > 50000:  # ~10,000 words
        raise click.ClickException(
            f"Case facts file too large ({len(facts_content):,} characters). "
            "Please provide a structured summary under 50,000 characters (~10,000 words). "
            "The strategy command expects concise, well-organized facts under 10 headings."
        )
    
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

    # Initialize LLM client
    llm_client = LLMClient(
        "openai/gpt-4o",
        temperature=0.2,
        top_p=0.9,
        presence_penalty=0.0,
        frequency_penalty=0.0,
    )
    llm_client.command_context = "strategy"  # Set command context
    
    # Read and parse strategies file if provided
    strategies_content = ""
    parsed_strategies = None
    if strategies:
        strategies_content = strategies.read()
        
        # Check strategies file size
        if len(strategies_content) > 100000:  # ~20,000 words, larger limit for strategies
            raise click.ClickException(
                f"Strategies file too large ({len(strategies_content):,} characters). "
                "Please provide a file under 100,000 characters (~20,000 words)."
            )
        
        parsed_strategies = parse_strategies_file(strategies_content)
        
        # Display what was found
        click.echo(f"Using strategies from brainstorm:")
        click.echo(f"  - {parsed_strategies['orthodox_count']} orthodox strategies")
        click.echo(f"  - {parsed_strategies['unorthodox_count']} unorthodox strategies")
        click.echo(f"  - {parsed_strategies['most_likely_count']} marked as most likely to succeed")
        
        if parsed_strategies['metadata']:
            click.echo(f"  - Generated for: {parsed_strategies['metadata'].get('side', 'unknown')} in {parsed_strategies['metadata'].get('area', 'unknown')} law")
        
        # Show warning if no "most likely to succeed" found
        if parsed_strategies['most_likely_count'] == 0:
            click.echo("  - Warning: No strategies marked as 'most likely to succeed' found")
    
    # strategy always needs verification as it creates foundational strategic documents
    if not verify:
        click.echo("ℹ️  Note: --verify flag ignored - strategy command always uses verification for accuracy")
    verify = True  # Force verification for critical accuracy

    # Generate strategic options
    system_prompt = """You are an Australian legal expert specializing in civil litigation strategy.
You must analyze case facts and produce strategic options for achieving a specific outcome."""
    
    # Enhance prompt if strategies are provided
    if parsed_strategies and parsed_strategies['most_likely_count'] > 0:
        system_prompt += f"\n\nYou have been provided with brainstormed strategies including {parsed_strategies['most_likely_count']} strategies marked as most likely to succeed. Pay particular attention to these when developing your strategic options."
    elif parsed_strategies:
        system_prompt += "\n\nYou have been provided with brainstormed strategies including orthodox and unorthodox approaches. Consider these when developing your strategic options, but focus on those most relevant to the specific outcome requested."
    
    system_prompt += """

For the strategic options section, use EXACTLY this format:

# STRATEGIC OPTIONS FOR: [OUTCOME IN CAPS]

## OPTION 1: [Title of Strategy]
* **Probability of Success**: [X]%
* **Principal Hurdles**:
  1. [Description of hurdle] — *[Case citation with pinpoint reference]*
  2. [Description of hurdle] — *[Case citation with pinpoint reference]*
* **Critical Missing Facts**:
  - [Missing fact 1]
  - [Missing fact 2]

## OPTION 2: [Title of Strategy]
[Same format as above]

[Continue for 3-5 options total]

Requirements:
- Australian law only
- Use real case citations with pinpoint references (e.g., Smith v Jones [2015] HCA 5 [27])
- Be specific about probability percentages based on precedents
- Identify genuine hurdles based on the case facts provided
- Note actual missing facts from the case materials
- Do not introduce facts not in the case materials
"""

    base_user_prompt = f"""CASE FACTS:
{facts_content}

DESIRED OUTCOME:
{outcome}

IDENTIFIED LEGAL ISSUES:
{', '.join(legal_issues)}
"""
    
    # Add strategies content if provided
    if parsed_strategies:
        base_user_prompt += f"\nBRAINSTORMED STRATEGIES PROVIDED:\n"
        base_user_prompt += f"- {parsed_strategies['orthodox_count']} orthodox strategies\n"
        base_user_prompt += f"- {parsed_strategies['unorthodox_count']} unorthodox strategies\n"
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
        if parsed_strategies['most_likely_count'] > 0:
            likely_match = re.search(r'## MOST LIKELY TO SUCCEED\n(.*?)(?====|\Z)', strategies_content, re.DOTALL)
            if likely_match:
                likely_text = likely_match.group(1)
                strategy_patterns = re.findall(r'(\d+\..*?)(?=\d+\.|$)', likely_text, re.DOTALL)
                for pattern in strategy_patterns:
                    strategy_title = re.search(r'\d+\.\s*([^\n]+)', pattern)
                    if strategy_title and len(pattern.strip()) > 50:
                        all_strategies.append({
                            'title': strategy_title.group(1).strip(),
                            'content': pattern.strip(),
                            'source': 'most_likely'
                        })
        
        # Extract from ORTHODOX section
        if parsed_strategies['orthodox_count'] > 0:
            orthodox_match = re.search(r'## ORTHODOX STRATEGIES\n(.*?)(?=## [A-Z]|===|\Z)', strategies_content, re.DOTALL)
            if orthodox_match:
                orthodox_text = orthodox_match.group(1)
                strategy_patterns = re.findall(r'(\d+\..*?)(?=\d+\.|$)', orthodox_text, re.DOTALL)
                for pattern in strategy_patterns:
                    strategy_title = re.search(r'\d+\.\s*([^\n]+)', pattern)
                    if strategy_title and len(pattern.strip()) > 50:
                        all_strategies.append({
                            'title': strategy_title.group(1).strip(),
                            'content': pattern.strip(),
                            'source': 'orthodox'
                        })
        
        # Extract from UNORTHODOX section
        if parsed_strategies['unorthodox_count'] > 0:
            unorthodox_match = re.search(r'## UNORTHODOX STRATEGIES\n(.*?)(?=## [A-Z]|===|\Z)', strategies_content, re.DOTALL)
            if unorthodox_match:
                unorthodox_text = unorthodox_match.group(1)
                strategy_patterns = re.findall(r'(\d+\..*?)(?=\d+\.|$)', unorthodox_text, re.DOTALL)
                for pattern in strategy_patterns:
                    strategy_title = re.search(r'\d+\.\s*([^\n]+)', pattern)
                    if strategy_title and len(pattern.strip()) > 50:
                        all_strategies.append({
                            'title': strategy_title.group(1).strip(),
                            'content': pattern.strip(),
                            'source': 'unorthodox'
                        })
        
        # Fallback: Extract any numbered strategies if no structured sections found
        if not all_strategies and strategies_content:
            click.echo("  📋 No structured sections found - extracting any numbered strategies")
            all_strategy_patterns = re.findall(r'(\d+\..*?)(?=\d+\.|$)', strategies_content, re.DOTALL)
            valid_patterns = [p for p in all_strategy_patterns if len(p.strip()) > 50]
            
            for pattern in valid_patterns:
                strategy_title = re.search(r'\d+\.\s*([^\n]+)', pattern)
                if strategy_title:
                    all_strategies.append({
                        'title': strategy_title.group(1).strip(),
                        'content': pattern.strip(),
                        'source': 'unstructured'
                    })
        
        # Use LLM ranking only if no "most likely to succeed" strategies are available
        if all_strategies:
            # Check if we have "most likely to succeed" strategies already identified
            most_likely_strategies = [s for s in all_strategies if s['source'] == 'most_likely']
            
            if most_likely_strategies:
                # Use the pre-analyzed "most likely" strategies directly - no need to re-analyze
                click.echo(f"  📋 Using {len(most_likely_strategies)} pre-analyzed 'most likely to succeed' strategies")
                priority_strategies = most_likely_strategies[:target_options]
                
                # Fill remaining slots with other strategies if needed
                if len(priority_strategies) < target_options:
                    # Get strategies not already used, avoiding duplicates by title
                    used_titles = {s['title'].lower().strip() for s in priority_strategies}
                    other_strategies = [s for s in all_strategies 
                                      if s['source'] != 'most_likely' 
                                      and s['title'].lower().strip() not in used_titles]
                    remaining_needed = target_options - len(priority_strategies)
                    
                    if other_strategies and remaining_needed > 0:
                        # Intelligently select additional strategies rather than just taking first N
                        click.echo(f"    🧠 Analyzing remaining {len(other_strategies)} unique strategies to fill {remaining_needed} slots...")
                        if len(other_strategies) < len([s for s in all_strategies if s['source'] != 'most_likely']):
                            click.echo(f"    📎 Excluded duplicate strategy titles already in 'most likely' selection")
                        
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
                            analysis_client = LLMClient("anthropic/claude-3.5-sonnet", temperature=0.2, top_p=0.8)
                            analysis_client.command_context = "strategy-analysis-remaining"
                            
                            remaining_response, _ = analysis_client.complete([
                                {"role": "system", "content": "Australian law only. Rank strategies objectively for the specific outcome."},
                                {"role": "user", "content": remaining_ranking_prompt}
                            ])
                            
                            # Parse the ranking for remaining strategies
                            remaining_match = re.search(r'RANKING:\s*([0-9,\s]+)', remaining_response)
                            if remaining_match:
                                remaining_ranking_str = remaining_match.group(1).strip()
                                remaining_indices = [int(x.strip()) - 1 for x in remaining_ranking_str.split(',') if x.strip().isdigit()]
                                
                                # Add top-ranked remaining strategies
                                for idx in remaining_indices[:remaining_needed]:
                                    if 0 <= idx < len(other_strategies):
                                        strategy = other_strategies[idx].copy()
                                        strategy['supplemental_ranked'] = True
                                        priority_strategies.append(strategy)
                                
                                click.echo(f"    📊 Intelligently selected {len(priority_strategies) - len(most_likely_strategies)} additional strategies")
                            else:
                                # Fallback to first N if parsing fails
                                priority_strategies.extend(other_strategies[:remaining_needed])
                                click.echo(f"    📎 Added {min(remaining_needed, len(other_strategies))} additional strategies (fallback)")
                                
                        except Exception as e:
                            # Fallback to first N if analysis fails
                            priority_strategies.extend(other_strategies[:remaining_needed])
                            click.echo(f"    📎 Added {min(remaining_needed, len(other_strategies))} additional strategies (analysis failed)")
            
            else:
                # No "most likely" pre-analysis available - run intelligent ranking
                click.echo(f"  🧠 No 'most likely' strategies found - analyzing {len(all_strategies)} strategies for '{outcome}'...")
                
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
                    analysis_client = LLMClient("anthropic/claude-3.5-sonnet", temperature=0.2, top_p=0.8)
                    analysis_client.command_context = "strategy-analysis"
                    
                    ranking_response, _ = analysis_client.complete([
                        {"role": "system", "content": "Australian law only. Analyze strategies objectively. Consider legal merit, factual support, precedential strength, and judicial likelihood. Provide clear reasoning for selections."},
                        {"role": "user", "content": ranking_prompt}
                    ])
                    
                    # Parse the ranking
                    ranking_match = re.search(r'RANKING:\s*([0-9,\s]+)', ranking_response)
                    if ranking_match:
                        ranking_str = ranking_match.group(1).strip()
                        try:
                            # Parse comma-separated numbers
                            strategy_indices = [int(x.strip()) - 1 for x in ranking_str.split(',') if x.strip().isdigit()]
                            
                            # Reorder strategies based on LLM ranking, take top target_options
                            for idx in strategy_indices[:target_options]:
                                if 0 <= idx < len(all_strategies):
                                    strategy = all_strategies[idx].copy()
                                    strategy['llm_ranked'] = True
                                    priority_strategies.append(strategy)
                            
                            click.echo(f"    📊 Selected top {len(priority_strategies)} strategies based on legal analysis")
                            
                            # Show reasoning if available
                            reasoning_match = re.search(r'REASONING:\s*(.*?)(?:\n\n|\Z)', ranking_response, re.DOTALL)
                            if reasoning_match:
                                reasoning = reasoning_match.group(1).strip()
                                click.echo(f"    💡 Analysis: {reasoning[:150]}..." if len(reasoning) > 150 else f"    💡 Analysis: {reasoning}")
                        
                        except (ValueError, IndexError) as e:
                            click.echo(f"    ⚠️  Could not parse strategy ranking, using fallback selection")
                            # Fallback to first target_options strategies
                            priority_strategies = all_strategies[:target_options]
                    else:
                        click.echo(f"    ⚠️  No ranking found in response, using fallback selection")
                        priority_strategies = all_strategies[:target_options]
                        
                except Exception as e:
                    click.echo(f"    ⚠️  Strategy ranking failed ({str(e)}), using fallback selection")
                    priority_strategies = all_strategies[:target_options]
        
        else:
            click.echo("  📋 No strategies found in provided file")
    
    # Target 3-5 options, prioritizing brainstormed strategies
    max_attempts = 7
    # target_options already defined above
    
    for attempt in range(1, max_attempts + 1):
        if len(valid_options) >= target_options:
            break
            
        click.echo(f"  🎯 Generating option {attempt}...")
        
        # Determine if we should use a specific brainstormed strategy
        use_brainstormed = False
        specific_strategy = None
        
        if priority_strategies and attempt <= len(priority_strategies):
            # Use one of the priority strategies as foundation
            specific_strategy = priority_strategies[attempt - 1]
            use_brainstormed = True
            strategy_source = specific_strategy.get('source', 'brainstormed')
            click.echo(f"    📋 Building on {strategy_source} strategy: '{specific_strategy['title']}'")
        
        # Individual option prompt
        if use_brainstormed and specific_strategy:
            individual_prompt = user_prompt + f"""

SPECIFIC INSTRUCTION: Transform the following brainstormed strategy into a detailed strategic option for the specific outcome "{outcome}":

BRAINSTORMED STRATEGY TO DEVELOP:
{specific_strategy['content']}

Generate ONE strategic option based on this brainstormed strategy (this will be option #{len(valid_options) + 1}). Use the exact format specified for a single OPTION, but develop this specific brainstormed strategy into concrete strategic steps for achieving "{outcome}".

Focus on:
- How this brainstormed strategy applies specifically to achieving "{outcome}"
- Concrete legal steps to implement this strategy
- Specific hurdles and missing facts for this approach
- Probability assessment based on this strategy's legal foundation"""
        else:
            # Generate fresh strategic option if no brainstormed strategies or we've used them all
            individual_prompt = user_prompt + f"\n\nGenerate ONE strategic option (this will be option #{len(valid_options) + 1}) to achieve the desired outcome. Use the exact format specified for a single OPTION."
            if parsed_strategies:
                individual_prompt += f"\n\nConsider the brainstormed strategies provided but develop a new approach that complements the {len(valid_options)} options already generated."
        
        # If we already have options, tell the LLM to avoid duplication
        if valid_options:
            individual_prompt += f"\n\nPreviously generated {len(valid_options)} options. Generate a DIFFERENT strategic approach that has not been covered yet."
        
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
                click.echo(f"    ❌ Option {attempt}: Found {len(citation_issues)-1} citation issues - discarding")
                continue
            else:
                click.echo(f"    ✅ Option {attempt}: Citations verified - keeping")
                
                # Extract reasoning trace from this option before cleaning
                option_trace = extract_reasoning_trace(option_content, "strategy")
                if option_trace:
                    option_reasoning_traces.append({
                        "option_number": len(valid_options) + 1,
                        "trace": option_trace
                    })
                
                # Remove reasoning trace from option content
                trace_pattern = r"=== LEGAL REASONING TRACE ===\s*\n(.*?)(?=\n\n|\n=|$)"
                clean_option_content = re.sub(trace_pattern, '', option_content, flags=re.DOTALL | re.IGNORECASE).strip()
                
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
            if not clean_option.startswith("## OPTION"):
                clean_option = f"## OPTION {i}: [Generated Strategy]\n{clean_option}"
            else:
                # Replace existing numbering
                clean_option = re.sub(r'^## OPTION \d+:', f'## OPTION {i}:', clean_option)
            numbered_options.append(clean_option)
        
        strategy_content = strategy_header + "\n\n".join(numbered_options)
        usage = total_usage
        
        click.echo(f"  📊 Successfully generated {len(valid_options)} verified strategic options")
    else:
        # No valid options could be generated
        strategy_content = f"# STRATEGIC OPTIONS FOR: {outcome.upper()}\n\n## NO VALID OPTIONS GENERATED\n\nUnable to generate strategic options with verified citations after {max_attempts} attempts. Please refine the case facts or desired outcome and try again."
        usage = total_usage
        click.echo(f"  ⚠️  Could not generate any options with verified citations after {max_attempts} attempts")

    # Generate recommended next steps
    next_steps_prompt = """Based on the strategic options above, provide EXACTLY 5 immediate next steps.

Format your response as:

# RECOMMENDED NEXT STEPS

1. [Specific action with reference to relevant rules/requirements]
2. [Specific action with reference to relevant rules/requirements]
3. [Specific action with reference to relevant rules/requirements]
4. [Specific action with reference to relevant rules/requirements]
5. [Specific action with reference to relevant rules/requirements]

Focus on evidence gathering, required notices, preliminary applications, or other procedural steps required by Australian court rules. Be specific to this case."""

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
    if any(term in outcome.lower() for term in ["injunction", "order", "interim", "stay", "restraint"]):
        doc_type = "application"
    elif any(term in outcome.lower() for term in ["affidavit", "evidence", "witness", "sworn"]):
        doc_type = "affidavit"

    # Generate draft document
    doc_formats = {
        "claim": """Draft a STATEMENT OF CLAIM using this exact format:

# DRAFT STATEMENT OF CLAIM

## PARTIES

1. [Description of plaintiff including relevant characteristics]

2. [Description of defendant including relevant characteristics]

## FACTS RELIED UPON

1. [Chronological fact 1]

2. [Chronological fact 2]

[Continue numbering for all relevant facts]

## CAUSES OF ACTION

### FIRST CAUSE OF ACTION - [Name]
[X]. [Description of cause of action]
     *[Authority with pinpoint reference]*

### SECOND CAUSE OF ACTION - [Name]
[Y]. [Description of cause of action]
     *[Authority with pinpoint reference]*

[Continue for all causes of action]

## RELIEF SOUGHT

The plaintiff claims:

1. [Specific relief sought]

2. [Specific relief sought]

3. Interest pursuant to [relevant statutory provision]

4. Costs

5. Such further or other relief as the Court deems just""",

        "application": """Draft an ORIGINATING APPLICATION using this exact format:

# DRAFT ORIGINATING APPLICATION

**IN THE [COURT NAME]**
**[DIVISION IF APPLICABLE]**

**File No:**

**Applicant**: [Full name and description]

**Respondent**: [Full name and description]

## THE APPLICANT APPLIES FOR:

1. [Specific order sought with reference to enabling provision]

2. [Additional order if applicable]

3. Such further or other orders as the Court deems just

4. Costs

## GROUNDS OF APPLICATION:

The grounds on which the application is made are:

1. [First ground with factual basis]
   *[Authority with pinpoint reference]*

2. [Second ground with factual basis]
   *[Authority with pinpoint reference]*

[Continue for all grounds]

## AFFIDAVIT EVIDENCE:

This application is supported by the affidavit of [name] sworn/affirmed [date]""",

        "affidavit": """Draft an AFFIDAVIT OUTLINE using this exact format:

# DRAFT AFFIDAVIT

**[COURT NAME]**
**[DIVISION IF APPLICABLE]**

**File No:**

**AFFIDAVIT OF [FULL NAME]**

I, [Full Name], of [Address], [Occupation], state on oath/affirm:

1. I am [position/relationship to proceedings] and have personal knowledge of the matters deposed to herein except where otherwise stated.

2. [Factual paragraph - one fact per paragraph]

3. [Factual paragraph - one fact per paragraph]

[Continue numbering for all relevant facts]

**Exhibits:**
[List any documents to be exhibited]

**Sworn/Affirmed at:** [Location]
**Date:** [Date]
**Before me:** [Commissioner for Affidavits/Solicitor]

**Deponent's signature:** _______________"""
    }

    doc_prompt = f"""Based on the case facts and strategic options, draft a {doc_type.upper()} to achieve the outcome: "{outcome}"

{doc_formats.get(doc_type, doc_formats['claim'])}

Requirements:
- Use formal Australian legal drafting style
- Include specific facts from the case materials
- Reference actual parties and dates from the case facts
- Cite relevant authorities with pinpoint references
- Do not invent facts not in the case materials"""

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
    output = strategy_content + "\n\n" + next_steps_content + "\n\n" + document_content
    
    # CRITICAL: Validate citations immediately to prevent cascade errors
    citation_issues = llm_client.validate_citations(output)
    if citation_issues:
        # Prepend warnings prominently
        citation_warning = "--- CITATION VALIDATION WARNINGS ---\n"
        citation_warning += "\n".join(citation_issues)
        citation_warning += "\n" + "-" * 40 + "\n\n"
        output = citation_warning + output
    
    # Mandatory verification for strategy (creates critical strategic guidance)
    click.echo("🔍 Running verification (mandatory for strategy command)")
    try:
        # Use heavy verification for strategic legal advice
        correction = llm_client.verify_with_level(output, "heavy")
        if correction.strip() and not correction.lower().startswith("no corrections needed"):
            output = output + "\n\n--- Strategic Legal Review ---\n" + correction
        
        # Run citation validation
        citation_issues = llm_client.validate_citations(output)
        if citation_issues:
            output += "\n\n--- Citation Warnings ---\n" + "\n".join(citation_issues)
            
    except Exception as e:
        raise click.ClickException(f"Verification error during strategy generation: {e}")

    # Create consolidated reasoning trace from all options
    consolidated_reasoning = None
    if option_reasoning_traces:
        consolidated_reasoning = create_consolidated_reasoning_trace(option_reasoning_traces, outcome)

    # Save output to timestamped file
    # Create a slug from the outcome for the filename
    outcome_slug = re.sub(r'[^\w\s-]', '', outcome.lower())
    outcome_slug = re.sub(r'[-\s]+', '_', outcome_slug)
    # Limit slug length and ensure it's not empty
    outcome_slug = outcome_slug[:40].strip('_') or 'strategy'
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"strategy_{outcome_slug}_{timestamp}.txt")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"Strategy Generation\n")
        f.write(f"Desired Outcome: {outcome}\n")
        f.write(f"Case Facts File: {case_facts.name}\n")
        if strategies:
            f.write(f"Strategies File: {strategies.name}\n")
        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 80 + "\n\n")
        f.write(output)
    
    click.echo(f"\nOutput saved to: \"{output_file}\"")
    
    # Save consolidated reasoning trace if we have option traces
    if consolidated_reasoning:
        reasoning_file = output_file.replace('.txt', '_reasoning.txt')
        with open(reasoning_file, 'w', encoding='utf-8') as f:
            f.write(consolidated_reasoning)
        click.echo(f"Legal reasoning trace saved to: \"{reasoning_file}\"")

    # Save audit log
    save_log(
        "strategy",
        {
            "inputs": {"case_facts": facts_content, "outcome": outcome},
            "params": {
                "model": "openai/gpt-4o",
                "temperature": 0.2,
                "top_p": 0.9,
                "verification": "auto-enabled (heavy)"
            },
            "usage": usage,
            "response": output,
            "output_file": output_file,
        },
    )

    # Show summary instead of full output
    click.echo("\n✅ Strategy generation complete!")
    click.echo(f"📄 Main output: \"{output_file}\"")
    if consolidated_reasoning:
        click.echo(f"📝 Reasoning traces: open \"{output_file.replace('.txt', '_reasoning.txt')}\"")
    
    # Show what was generated
    click.echo(f"\n📊 Generated {len(valid_options)} strategic options for: {outcome}")
    
    # Brief preview of options
    click.echo("\n📋 Strategic options generated:")
    for i, option in enumerate(valid_options, 1):
        # Extract option title
        title_match = re.search(r'## OPTION \d+: (.+)', option)
        if title_match:
            click.echo(f"   {i}. {title_match.group(1)}")
    
    click.echo(f"\n💡 View full strategy: open \"{output_file}\"")