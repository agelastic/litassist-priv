"""
Core orchestration for brainstorm command.

Coordinates generation of orthodox, unorthodox, and analysis strategies.
"""

import click
import os
import logging
import re

from litassist.utils.file_ops import (
    read_document,
    validate_file_size_limit,
)
from litassist.utils.core import (
    timed,
    parse_strategies_file,
    validate_side_area_combination,
)
from litassist.utils.formatting import (
    warning_message,
    success_message,
    saved_message,
    stats_message,
    info_message,
    verifying_message,
    tip_message,
)
from litassist.logging import (
    save_log,
    save_command_output,
)
from litassist.llm.factory import LLMClientFactory
from litassist.prompts import PROMPTS

# Import from submodules
from .research_handler import analyze_research_size
from litassist.utils.file_ops import (
    expand_glob_patterns_callback as expand_glob_patterns,
)
from .orthodox_generator import generate_orthodox_strategies
from .unorthodox_generator import generate_unorthodox_strategies
from .analysis_generator import generate_analysis
from .citation_regenerator import regenerate_bad_strategies


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
@click.option(
    "--verify",
    is_flag=True,
    help="Verify complete output (default: verify unorthodox only)",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def brainstorm(facts, side, area, research, verify, output):
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

    # Command-level start log
    try:
        from litassist.logging import (
            log_task_event,
        )  # safe re-import in case of test contexts

        log_task_event("brainstorm", "init", "start", "Starting brainstorm")
    except Exception:
        pass

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
        for source, content in zip(facts_sources, facts_contents):
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

    # Generate Orthodox Strategies
    try:
        log_task_event(
            "brainstorm", "orthodox", "start", "Generating orthodox strategies"
        )
    except Exception:
        pass
    orthodox_content, orthodox_usage, orthodox_citation_issues = (
        generate_orthodox_strategies(facts, side, area, research_context)
    )
    try:
        log_task_event("brainstorm", "orthodox", "end", "Orthodox strategies generated")
    except Exception:
        pass

    # Selectively regenerate orthodox strategies with citation issues
    if orthodox_citation_issues:
        click.echo(
            info_message(
                f"Found {len(orthodox_citation_issues) - 1} citation issues in orthodox strategies - fixing..."
            )
        )
        orthodox_client = LLMClientFactory.for_command("brainstorm", "orthodox")
        # Rebuild the base prompt for regeneration
        orthodox_template = PROMPTS.get(
            "strategies.brainstorm.orthodox_prompt", research_context=research_context
        )
        orthodox_base_content = PROMPTS.get(
            "strategies.brainstorm.orthodox_base"
        ).format(facts=facts, side=side, area=area, research=orthodox_template)
        orthodox_base_prompt = PROMPTS.get(
            "strategies.brainstorm.orthodox_output_format"
        ).format(content=orthodox_base_content)
        try:
            log_task_event(
                "brainstorm",
                "orthodox-repair",
                "start",
                "Fixing citation issues in orthodox strategies",
            )
        except Exception:
            pass
        orthodox_content = regenerate_bad_strategies(
            orthodox_client, orthodox_content, orthodox_base_prompt, "orthodox"
        )
        try:
            log_task_event(
                "brainstorm", "orthodox-repair", "end", "Orthodox citation issues fixed"
            )
        except Exception:
            pass

    # Generate Unorthodox Strategies
    try:
        log_task_event(
            "brainstorm", "unorthodox", "start", "Generating unorthodox strategies"
        )
    except Exception:
        pass
    unorthodox_content, unorthodox_usage, unorthodox_citation_issues = (
        generate_unorthodox_strategies(facts, side, area)
    )
    try:
        log_task_event(
            "brainstorm", "unorthodox", "end", "Unorthodox strategies generated"
        )
    except Exception:
        pass

    # Selectively regenerate unorthodox strategies with citation issues
    if unorthodox_citation_issues:
        click.echo(
            info_message(
                f"Found {len(unorthodox_citation_issues) - 1} citation issues in unorthodox strategies - fixing..."
            )
        )
        unorthodox_client = LLMClientFactory.for_command("brainstorm", "unorthodox")
        # Rebuild the base prompt for regeneration
        unorthodox_template = PROMPTS.get("strategies.brainstorm.unorthodox_prompt")
        unorthodox_base_content = PROMPTS.get(
            "strategies.brainstorm.unorthodox_base"
        ).format(facts=facts, side=side, area=area, research=unorthodox_template)
        unorthodox_base_prompt = PROMPTS.get(
            "strategies.brainstorm.unorthodox_output_format"
        ).format(content=unorthodox_base_content)
        try:
            log_task_event(
                "brainstorm",
                "unorthodox-repair",
                "start",
                "Fixing citation issues in unorthodox strategies",
            )
        except Exception:
            pass
        unorthodox_content = regenerate_bad_strategies(
            unorthodox_client, unorthodox_content, unorthodox_base_prompt, "unorthodox"
        )
        try:
            log_task_event(
                "brainstorm",
                "unorthodox-repair",
                "end",
                "Unorthodox citation issues fixed",
            )
        except Exception:
            pass

    # Generate Most Likely to Succeed analysis
    try:
        log_task_event(
            "brainstorm", "analysis", "start", "Analyzing most promising strategies"
        )
    except Exception:
        pass
    analysis_content, analysis_usage = generate_analysis(
        facts, side, area, orthodox_content, unorthodox_content
    )
    try:
        log_task_event("brainstorm", "analysis", "end", "Analysis completed")
    except Exception:
        pass

    # Note: Citation issues now handled automatically in LLMClient.complete()
    # Combine all sections - headers already included in LLM output
    combined_content = f"""{orthodox_content}

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

    # Collect all critiques for appending to output
    critiques = []

    # Add orthodox citation issues if any
    if orthodox_citation_issues:
        critiques.append(
            ("Orthodox Strategy Citation Issues", "\n".join(orthodox_citation_issues))
        )

    # Add unorthodox citation issues if any
    if unorthodox_citation_issues:
        critiques.append(
            (
                "Unorthodox Strategy Citation Issues",
                "\n".join(unorthodox_citation_issues),
            )
        )

    # Conditional full verification based on --verify flag
    full_verification_result = None
    final_citation_issues = None

    if verify:
        click.echo(verifying_message("Verifying complete brainstorm output..."))

        try:
            try:
                log_task_event(
                    "brainstorm",
                    "final-verify",
                    "start",
                    "Verifying complete brainstorm output",
                )
            except Exception:
                pass
            # Use verification config for full document
            verify_client = LLMClientFactory.for_command("verification")
            correction, _ = verify_client.verify(combined_content)
            full_verification_result = correction  # Keep full result for critique

            # Try to extract just the verified document part
            match = re.search(
                r"## Verified and Corrected Document\s*\n(.*)", correction, re.DOTALL
            )

            if match:
                # Successfully extracted the document
                combined_content = match.group(1).strip()
                click.echo(success_message("Full output verified and corrected"))
            else:
                # Could not find expected format - use whole output
                logging.warning(
                    "Could not extract verified document section - using complete verification output"
                )
                combined_content = correction
                click.echo(
                    warning_message(
                        "Verification format unexpected - using complete output"
                    )
                )

            # Also run citation validation
            citation_issues = verify_client.validate_citations(combined_content)
            if citation_issues:
                final_citation_issues = citation_issues  # Capture for critique section
                click.echo(
                    warning_message(f"{len(citation_issues)} citation warnings found")
                )
            try:
                log_task_event(
                    "brainstorm",
                    "final-verify",
                    "end",
                    "Full brainstorm output verified",
                )
            except Exception:
                pass

        except Exception as e:
            raise click.ClickException(f"Verification error during brainstorming: {e}")
    else:
        # Unorthodox was verified independently, just do citation check
        click.echo(
            info_message(
                "Skipping full document verification (unorthodox was verified independently)"
            )
        )
        try:
            log_task_event(
                "brainstorm",
                "final-verify",
                "progress",
                "Skipping full document verification (unorthodox was verified independently)",
            )
        except Exception:
            pass
        try:
            # Quick citation check using the analysis client
            analysis_client = LLMClientFactory.for_command("brainstorm", "analysis")
            citation_issues = analysis_client.validate_citations(combined_content)
            if citation_issues:
                final_citation_issues = citation_issues  # Capture for critique section
                click.echo(
                    warning_message(f"{len(citation_issues)} citation warnings found")
                )
        except Exception:
            pass  # Non-critical if citation check fails

    # Add full verification result if available
    if full_verification_result:
        critiques.append(("Full Document Verification", full_verification_result))

    # Add final citation issues if any
    if final_citation_issues:
        critiques.append(
            ("Final Citation Validation", "\n".join(final_citation_issues))
        )

    # Save to timestamped file with critiques appended
    # Build metadata with all input files
    metadata = {
        "Side": side.capitalize(),
        "Area": area.capitalize(),
        "Source": (
            ", ".join(facts_sources) if len(facts_sources) > 1 else facts_sources[0]
        ),
    }
    
    # Add research files if provided
    if research:
        metadata["Research Files"] = ", ".join(list(research))
    
    output_file = save_command_output(
        output if output else f"brainstorm_{area}_{side}",
        combined_content,
        "" if output else f"{side} in {area} law",
        metadata=metadata,
        critique_sections=critiques if critiques else None,
    )

    click.echo(
        "\nTo use these strategies with other commands, manually create or update strategies.txt"
    )

    # Save comprehensive audit log (without massive content blobs)
    save_log(
        "brainstorm",
        {
            "inputs": {
                "facts_files": facts_sources,
                "research_files": list(research) if research else [],
                "research_analysis": {
                    # Only log metadata, not the combined_content
                    "total_tokens": research_analysis.get("total_tokens", 0),
                    "total_words": research_analysis.get("total_words", 0),
                    "file_count": research_analysis.get("file_count", 0),
                    "exceeds_threshold": research_analysis.get(
                        "exceeds_threshold", False
                    ),
                },
            },
            "params": f"verify={'full' if verify else 'unorthodox-only'}, orthodox_temp=0.3, unorthodox_temp=0.9, analysis_temp=0.4",
            # Response content removed - already logged by LLMClient separately
            "output_file": output_file,
            "usage": usage,
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

    # Command-level end log
    try:
        log_task_event("brainstorm", "init", "end", "Brainstorm complete")
    except Exception:
        pass
