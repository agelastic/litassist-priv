"""
Core orchestration for brainstorm command.

Coordinates generation of orthodox, unorthodox, and analysis strategies.
"""

import click
import logging
import re
import json
import time

from litassist.utils.file_ops import (
    read_document,
    validate_file_size_limit,
)
from litassist.timing import timed
from litassist.utils.core import (
    extract_verified_document,
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
    log_task_event,
)
from litassist.llm.factory import LLMClientFactory
from litassist.prompts import PROMPTS
from litassist.utils.case_facts import (
    resolve_case_facts_file,
    resolve_matter_type,
    matter_type_posture,
)

# Import from submodules
from .research_handler import analyze_research_size
from litassist.utils.file_ops import (
    expand_glob_patterns_callback as expand_glob_patterns,
)
from .orthodox_generator import generate_orthodox_strategies
from .unorthodox_generator import generate_unorthodox_strategies
from .analysis_generator import generate_analysis


def _extract_strategies(content: str, strategy_type: str) -> list[str]:
    """Extract individual numbered strategies from content."""
    # Pattern: "### Strategy 1:" or "### 1." or "## STRATEGY 1:" or "1. Strategy Title"
    # Capture entire strategy INCLUDING the header
    pattern = r'((?:###\s+Strategy\s+\d+:|###\s+\d+\.|##\s*STRATEGY\s*\d+:|\d+\.)[^\n]*\n.*?)(?=(?:\n(?:###\s+Strategy\s+\d+:|###\s+\d+\.|##\s*STRATEGY\s*\d+:|\d+\.))|$)'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

    # No fallback: if the model returned no recognisable strategy headers (e.g. a
    # refusal or malformed output), surface zero strategies rather than fabricating
    # chunks by splitting on blank lines. The caller detects the empty result and
    # warns loudly (CLAUDE.md: fail fast, no fallback parsing).
    return [match.strip() for match in matches]


def _extract_citations_from_strategy(strategy: str) -> list[str]:
    """Extract all citations from a strategy text."""
    from litassist.citation_patterns import extract_citations
    return extract_citations(strategy)


def _annotate_strategies_with_verification(
    strategies: list[str],
    verified_set: set[str],
    unverified_dict: dict[str, str],
    plausibility_assessments: dict[str, dict],
    strategy_type: str,
    verified_snippets: dict[str, str] | None = None,
) -> list[str]:
    """Add citation verification annotations to each strategy."""
    annotated = []

    for i, strategy in enumerate(strategies, 1):
        strategy_id = f"{strategy_type}_{i}"
        citations = _extract_citations_from_strategy(strategy)

        if not citations:
            # No citations - no annotation needed
            annotated.append(strategy)
            continue

        # Build citation status annotation
        annotation_lines = ["\n**CITATION STATUS:**"]

        for citation in citations:
            if citation in verified_set:
                annotation_lines.append(f"  [VERIFIED]: {citation}")
                # Add snippet if available
                if verified_snippets and citation in verified_snippets:
                    snippet = verified_snippets[citation]
                    if snippet:
                        annotation_lines.append(f"    Context: {snippet}")
            elif citation in unverified_dict:
                reason = unverified_dict[citation]

                # Get plausibility assessment if available
                assessment = plausibility_assessments.get(strategy_id, {})
                risk_level = assessment.get("risk", "UNKNOWN")
                explanation = assessment.get("explanation", reason)
                confidence = assessment.get("confidence")

                # Add confidence if available (Verbalised Sampling)
                confidence_text = f" (confidence: {confidence}%)" if confidence else ""

                annotation_lines.append(
                    f"  [NOT VERIFIED]: {citation} - {risk_level} RISK{confidence_text} - {explanation}"
                )

        # Append annotation to strategy
        annotated_strategy = strategy + "\n" + "\n".join(annotation_lines)
        annotated.append(annotated_strategy)

    return annotated


def assess_legal_plausibility_bulk(
    strategies_with_unverified: list[tuple[str, str, list[tuple[str, str]]]],
    verified_snippets: dict[str, str] | None = None,
) -> dict[str, dict]:
    """
    ONE bulk LLM call to assess plausibility of ALL unverified citations.

    Args:
        strategies_with_unverified: List of (strategy_id, strategy_text, unverified_citations)
            Example: [("orthodox_1", "Strategy text...", [("[2024] HCA 123", "not found")]), ...]
        verified_snippets: Optional dict mapping verified citation -> snippet text

    Returns:
        Dict mapping strategy_id to assessment:
            {"orthodox_1": {"risk": "MEDIUM", "explanation": "Principle sound..."}, ...}

    Uses: brainstorm-analysis config (see model_configs.yaml).
    Token cost: ~5k (vs ~10k for per-strategy calls)
    """
    click.echo(
        info_message(
            f"Assessing plausibility of unverified citations in {len(strategies_with_unverified)} strategies..."
        )
    )

    # Build comprehensive prompt with ALL strategies
    strategies_section = []
    for strategy_id, strategy_text, unverified_cits in strategies_with_unverified:
        # Extract just the strategy title and core legal reasoning
        strategy_preview = strategy_text[:500] + "..." if len(strategy_text) > 500 else strategy_text

        # Build verified citations section with snippets for this strategy
        verified_section = ""
        if verified_snippets:
            strategy_citations = _extract_citations_from_strategy(strategy_text)
            verified_in_strategy = []
            for citation in strategy_citations:
                if citation in verified_snippets:
                    snippet = verified_snippets[citation]
                    verified_in_strategy.append(f"  - {citation}\n    Context: {snippet}")

            if verified_in_strategy:
                verified_section = "\n\nVerified Citations (legal context):\n" + "\n".join(verified_in_strategy)

        # Build unverified citations list
        citations_list = "\n".join([
            f"  - {cit} (Reason: {reason})"
            for cit, reason in unverified_cits
        ])

        strategies_section.append(
            f"**{strategy_id.upper()}:**\n{strategy_preview}{verified_section}\n\nUnverified Citations:\n{citations_list}"
        )

    bulk_prompt = PROMPTS.get("strategies.brainstorm.plausibility_prompt").format(
        num_strategies=len(strategies_with_unverified),
        strategies_section="\n\n".join(strategies_section)
    )

    # ONE LLM call for all assessments
    analysis_client = LLMClientFactory.for_command("brainstorm", "analysis")

    messages = [
        {
            "role": "system",
            "content": PROMPTS.get("commands.brainstorm.plausibility_system"),
        },
        {"role": "user", "content": bulk_prompt},
    ]

    try:
        response, _ = analysis_client.complete(messages, skip_citation_verification=True)

        logging.info(f"Plausibility LLM call completed, response length: {len(response)}")
        logging.debug(f"Plausibility response preview: {response[:500]}")

        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            logging.warning("No JSON found in plausibility response")
            click.echo(warning_message("Could not parse plausibility assessments - using defaults"))
            return {}

        try:
            assessments = json.loads(json_match.group(0))
            logging.info(f"Successfully parsed {len(assessments)} risk assessments")

            # Save comprehensive audit log
            save_log(
                "plausibility_assessment",
                {
                    "strategies_assessed": len(strategies_with_unverified),
                    "citations_evaluated": sum(
                        len(unverified_cits)
                        for _, _, unverified_cits in strategies_with_unverified
                    ),
                    "prompt": bulk_prompt,
                    "response": response,
                    "assessments": assessments,
                    "metadata": {
                        "model": analysis_client.model,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                },
            )

            return assessments
        except json.JSONDecodeError as e:
            logging.error(f"Plausibility assessment JSON parsing failed: {e}")
            click.echo(warning_message(f"Failed to parse plausibility JSON: {e}"))
            return {}

    except Exception as e:
        logging.error(f"Plausibility assessment LLM call failed: {e}")
        click.echo(warning_message(f"Plausibility assessment failed: {e}"))
        return {}


def verify_and_annotate_strategies(
    orthodox_content: str, unorthodox_content: str
) -> tuple[str, str, str]:
    """
    Verify citations in all strategies and add annotations.

    Args:
        orthodox_content: Generated orthodox strategies
        unorthodox_content: Generated unorthodox strategies

    Returns:
        Tuple of (annotated_orthodox, annotated_unorthodox, summary_stats)
    """
    # Local imports - citation chain loads unittest.mock (19ms) + other heavy modules
    # PEP 8 permits this to avoid loading modules that might not be used
    from litassist.citation.verify import verify_all_citations

    # Extract individual strategies
    orthodox_strategies = _extract_strategies(orthodox_content, "orthodox")
    unorthodox_strategies = _extract_strategies(unorthodox_content, "unorthodox")

    logging.info(f"Extracted {len(orthodox_strategies)} orthodox, {len(unorthodox_strategies)} unorthodox strategies")

    # Verify all citations in one pass
    all_text = orthodox_content + "\n\n" + unorthodox_content
    verified_details, unverified_citations = verify_all_citations(all_text)

    # Build citation lookup maps (using returned details, no redundant cache lookups)
    verified_set = {v["citation"] for v in verified_details}
    unverified_dict = {cit: reason for cit, reason in unverified_citations}

    # Build snippet map directly from returned details
    verified_snippets = {
        v["citation"]: v["snippet"] for v in verified_details if v.get("snippet")
    }

    # Collect strategies with unverified citations for bulk plausibility
    strategies_for_plausibility = []

    # Process orthodox strategies
    for i, strategy in enumerate(orthodox_strategies, 1):
        strategy_citations = _extract_citations_from_strategy(strategy)
        unverified_in_strategy = [
            (cit, unverified_dict[cit])
            for cit in strategy_citations
            if cit in unverified_dict
        ]

        if unverified_in_strategy:
            strategies_for_plausibility.append(
                (f"orthodox_{i}", strategy, unverified_in_strategy)
            )

    # Process unorthodox strategies
    for i, strategy in enumerate(unorthodox_strategies, 1):
        strategy_citations = _extract_citations_from_strategy(strategy)
        unverified_in_strategy = [
            (cit, unverified_dict[cit])
            for cit in strategy_citations
            if cit in unverified_dict
        ]

        if unverified_in_strategy:
            strategies_for_plausibility.append(
                (f"unorthodox_{i}", strategy, unverified_in_strategy)
            )

    # Count total unverified citations
    total_unverified_count = sum(
        len(unverified_cits) for _, _, unverified_cits in strategies_for_plausibility
    )

    logging.info(
        f"Collected {len(strategies_for_plausibility)} strategies with "
        f"{total_unverified_count} unverified citations for plausibility assessment"
    )

    # ONE bulk LLM call for plausibility assessment
    plausibility_assessments = {}
    if strategies_for_plausibility:
        plausibility_assessments = assess_legal_plausibility_bulk(
            strategies_for_plausibility, verified_snippets
        )

    # Annotate orthodox strategies
    annotated_orthodox = _annotate_strategies_with_verification(
        orthodox_strategies,
        verified_set,
        unverified_dict,
        plausibility_assessments,
        "orthodox",
        verified_snippets,
    )

    # Annotate unorthodox strategies
    annotated_unorthodox = _annotate_strategies_with_verification(
        unorthodox_strategies,
        verified_set,
        unverified_dict,
        plausibility_assessments,
        "unorthodox",
        verified_snippets,
    )

    # Rebuild content with annotations, preserving headers if present
    # Check if original content has a header
    orthodox_header = ""
    if orthodox_content.strip().startswith("## "):
        header_end = orthodox_content.find("\n")
        if header_end > 0:
            orthodox_header = orthodox_content[:header_end] + "\n\n"

    unorthodox_header = ""
    if unorthodox_content.strip().startswith("## "):
        header_end = unorthodox_content.find("\n")
        if header_end > 0:
            unorthodox_header = unorthodox_content[:header_end] + "\n\n"

    # Add default headers if not present
    if not orthodox_header:
        orthodox_header = "## ORTHODOX STRATEGIES\n\n"
    if not unorthodox_header:
        unorthodox_header = "## UNORTHODOX STRATEGIES\n\n"

    annotated_orthodox_content = orthodox_header + "\n\n".join(annotated_orthodox)
    annotated_unorthodox_content = unorthodox_header + "\n\n".join(annotated_unorthodox)

    # Summary stats
    total_verified = len(verified_details)
    total_unverified = len(unverified_citations)

    # Count risk levels if plausibility was assessed
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "UNKNOWN": 0}
    for assessment in plausibility_assessments.values():
        risk = assessment.get("risk", "UNKNOWN")
        risk_counts[risk] += 1

    summary = f"{total_verified} verified, {total_unverified} unverified"
    if plausibility_assessments:
        summary += f" | Risk: LOW={risk_counts['LOW']}, MEDIUM={risk_counts['MEDIUM']}, HIGH={risk_counts['HIGH']}"
        if risk_counts['UNKNOWN'] > 0:
            summary += f", UNKNOWN={risk_counts['UNKNOWN']}"

    return annotated_orthodox_content, annotated_unorthodox_content, summary


@click.command()
@click.option(
    "--facts",
    multiple=True,
    type=click.Path(),  # Remove exists=True since we'll check in callback
    callback=expand_glob_patterns,
    help="Facts files to analyze. Supports glob patterns. Use multiple times: --facts file1.txt --facts 'case_*.txt'. Defaults to case_facts.md if it exists.",
)
@click.option(
    "--side",
    type=click.Choice(
        ["plaintiff", "defendant", "accused", "respondent", "complainant"]
    ),
    required=True,
    help="Specify which side you are representing (complainant = regulatory/FOI complaints)",
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
    "Use multiple times: --research file1.txt --research 'outputs/lookup_*.md'. "
    "Large research files (>128k tokens) may impact verification performance.",
)
@click.option(
    "--verify",
    is_flag=True,
    help="Add LLM content verification for legal accuracy (citations always verified). Recommended for final versions.",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def brainstorm(facts, side, area, research, verify, output):
    """
    Generate comprehensive legal strategies.

    Generates:
    - 15 orthodox legal strategies
    - 15 unorthodox but potentially effective strategies
    - Analysis selecting 10 most promising
    - Exactly 5 strategies most likely to succeed

    All strategies are tailored to your specified party side and legal area.
    The output is automatically saved with a timestamp for use in other commands.

    Usage:
        # With default case_facts.md (if exists in current directory)
        litassist brainstorm --side plaintiff --area civil

        # With single facts file
        litassist brainstorm --facts case_facts.md --side plaintiff --area civil

        # With multiple facts files
        litassist brainstorm --facts facts1.txt --facts facts2.txt --side plaintiff --area civil

        # With multiple research files
        litassist brainstorm --side plaintiff --area civil --research lookup1.txt --research lookup2.txt

        # With glob patterns for research files
        litassist brainstorm --side plaintiff --area civil --research 'outputs/lookup_*gift*.md'

    Note: Verification is automatically performed on all brainstorm outputs to ensure citation accuracy and legal soundness.

    Raises:
        click.ClickException: If there are errors reading the facts files or with the LLM API call.
    """
    # Check for potentially incompatible side/area combinations
    validate_side_area_combination(side, area)

    # Command-level start log
    try:
        log_task_event("brainstorm", "init", "start", "Starting brainstorm")
    except Exception:
        pass

    # Handle facts files - auto-select the latest case_facts*.md if none given.
    if not facts:
        facts = (resolve_case_facts_file(),)

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
            click.echo(f"  * {source}")

    # Combine facts with source attribution if multiple files
    if len(facts_contents) == 1:
        combined_facts = facts_contents[0]
    else:
        combined_parts = []
        for source, content in zip(facts_sources, facts_contents):
            combined_parts.append(f"=== SOURCE: {source} ===\n{content}")
        combined_facts = "\n\n".join(combined_parts)

    facts = combined_facts

    # Matter-type posture: default civil with a warning when absent/unknown
    # (Phase 1 - no hard gate). Posture is prepended to each generator's system
    # message; brainstorm's --side/--area axes are unchanged.
    matter_type, mt_warning = resolve_matter_type(facts)
    if mt_warning:
        click.echo(warning_message(mt_warning))
    matter_posture = matter_type_posture(matter_type)

    # Check file size to prevent token limit issues. The binding consumer is the
    # analysis stage (facts + orthodox + unorthodox go to brainstorm-analysis),
    # routed to the smallest-window model in the pipeline, so size the cap against
    # THAT stage -- not the orthodox-generation model -- or the guard cannot
    # protect the narrowest window. Reads the analysis model's window from
    # model_capabilities.yaml, so it scales with whichever model is routed.
    validate_file_size_limit(
        facts,
        LLMClientFactory.get_input_budget_for_command("brainstorm", "analysis"),
        "Case facts",
    )

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
    orthodox_content, orthodox_usage = generate_orthodox_strategies(
        facts, side, area, research_context, matter_posture=matter_posture
    )
    try:
        log_task_event("brainstorm", "orthodox", "end", "Orthodox strategies generated")
    except Exception:
        pass

    # Generate Unorthodox Strategies
    try:
        log_task_event(
            "brainstorm", "unorthodox", "start", "Generating unorthodox strategies"
        )
    except Exception:
        pass
    unorthodox_content, unorthodox_usage = generate_unorthodox_strategies(
        facts, side, area, matter_posture=matter_posture
    )
    try:
        log_task_event(
            "brainstorm", "unorthodox", "end", "Unorthodox strategies generated"
        )
    except Exception:
        pass

    # Detect empty/refused lanes before verification and surface them loudly.
    # _extract_strategies returns [] when the model produced no recognisable
    # strategy headers (e.g. a refusal); previously a refusal was silently split
    # into fabricated chunks. We do not abort - the other lane and the analysis
    # may still be useful - but the user must see that a lane produced nothing.
    orthodox_parsed = _extract_strategies(orthodox_content, "orthodox")
    unorthodox_parsed = _extract_strategies(unorthodox_content, "unorthodox")
    for lane_name, lane_content, lane_parsed in (
        ("Orthodox", orthodox_content, orthodox_parsed),
        ("Unorthodox", unorthodox_content, unorthodox_parsed),
    ):
        if not lane_parsed:
            snippet = " ".join(lane_content.split())[:200]
            click.echo(
                warning_message(
                    f"{lane_name} generation produced 0 parseable strategies "
                    "(the model may have refused or returned an unexpected format). "
                    f"Response begins: {snippet}"
                )
            )
    strategy_total = len(orthodox_parsed) + len(unorthodox_parsed)
    if strategy_total == 0:
        # Both lanes produced no parseable strategies (e.g. both models refused).
        # Abort before the expensive analysis stage rather than analysing nothing.
        raise click.ClickException(
            "Both orthodox and unorthodox generation produced 0 parseable "
            "strategies (the models may have refused). Aborting before the "
            "analysis stage - nothing to analyse."
        )

    # NEW: Verify all citations before analysis
    try:
        log_task_event(
            "brainstorm",
            "verify-citations",
            "start",
            f"Verifying citations in all {strategy_total} strategies",
        )
    except Exception:
        pass

    click.echo(verifying_message("Verifying citations in all strategies..."))

    # Verify and annotate both strategy sets
    orthodox_content, unorthodox_content, verification_summary = (
        verify_and_annotate_strategies(orthodox_content, unorthodox_content)
    )

    click.echo(success_message(f"Citation verification complete: {verification_summary}"))

    try:
        log_task_event(
            "brainstorm",
            "verify-citations",
            "end",
            "Citation verification complete",
            {"summary": verification_summary},
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
        facts, side, area, orthodox_content, unorthodox_content,
        matter_posture=matter_posture,
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

    # Conditional full verification based on --verify flag
    full_verification_result = None
    final_citation_issues = None

    if verify:
        click.echo(verifying_message("Performing full content verification..."))

        try:
            log_task_event(
                "brainstorm",
                "full-verify",
                "start",
                "Full content verification of complete output"
            )
        except Exception:
            pass

        # Use verification config for full document
        verify_client = LLMClientFactory.for_command("verification")
        correction, _ = verify_client.verify(combined_content)
        # Note: verify() returns (correction, model_name), not usage dict

        full_verification_result = correction  # Keep full result for critique

        # Try to extract just the verified document part. On parse failure
        # we must preserve the pre-verification brainstorm content rather
        # than silently replacing it with the verifier's freeform output -
        # the previous code overwrote combined_content with `correction`
        # while telling the user it was "using original output".
        combined_content, parsed_ok = extract_verified_document(
            correction, combined_content
        )

        if parsed_ok:
            click.echo(success_message("Full content verification complete"))
        else:
            logging.warning(
                "Could not extract verified document section - "
                "preserving original brainstorm output"
            )
            click.echo(
                warning_message(
                    "Verification format unexpected - preserving original output"
                )
            )

        # Also run citation validation
        citation_issues = verify_client.validate_citations(combined_content)
        if citation_issues:
            final_citation_issues = citation_issues  # Capture for critique section
            click.echo(
                warning_message(f"{len(citation_issues)} citation warnings found after verification")
            )

        try:
            log_task_event(
                "brainstorm",
                "full-verify",
                "end",
                "Full content verification complete"
            )
        except Exception:
            pass

    else:
        # Citations have already been verified, skip LLM content verification
        click.echo(
            info_message(
                "Skipping LLM content verification (use --verify for legal accuracy check)"
            )
        )
        try:
            log_task_event(
                "brainstorm",
                "full-verify",
                "skip",
                "Skipping LLM content verification",
            )
        except Exception:
            pass

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
            "params": f"verify={'full' if verify else 'unorthodox-only'}, orthodox_count=15, unorthodox_count=15, selected=10, recommended=5",
            # Response content removed - already logged by LLMClient separately
            "output_file": output_file,
            "usage": usage,
            "stages": {
                "orthodox": {"usage": orthodox_usage},
                "unorthodox": {"usage": unorthodox_usage},
                "analysis": {"usage": analysis_usage},
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
    click.echo(f"   * Orthodox strategies: {parsed_result.get('orthodox_count', 0)}")
    click.echo(
        f"   * Unorthodox strategies: {parsed_result.get('unorthodox_count', 0)}"
    )
    click.echo(
        f"   * Most likely to succeed: {parsed_result.get('most_likely_count', 0)}"
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
