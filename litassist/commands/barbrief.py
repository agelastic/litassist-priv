"""
Generate comprehensive barrister's brief for Australian litigation.

This module implements the 'barbrief' command which consolidates case materials
into a structured brief suitable for briefing counsel. It combines case facts,
strategies, research, and supporting documents into a comprehensive document
with proper citations and Australian legal formatting.
"""

import click
from typing import List, Optional, Dict, Any

from litassist.prompts import PROMPTS
from litassist.utils.file_ops import (
    read_document,
    expand_glob_patterns_callback as expand_glob_patterns,
)
from litassist.utils.core import (
    timed,
    show_command_completion,
)
from litassist.utils.legal_reasoning import create_reasoning_prompt
from litassist.utils.formatting import (
    warning_message,
)
from litassist.utils.text_processing import count_tokens_and_words
from litassist.logging_utils import (
    save_command_output,
)
from litassist.llm import LLMClientFactory
from litassist.citation_verify import verify_all_citations


@timed
def validate_case_facts(content: str) -> bool:
    """
    Validate that case facts follow the 10-heading format.

    Args:
        content: The case facts content to validate

    Returns:
        True if valid, False otherwise
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

    content_lower = content.lower()
    return all(heading.lower() in content_lower for heading in required_headings)


@timed
def prepare_brief_sections(
    case_facts: str,
    strategies: Optional[str],
    research_docs: List[str],
    supporting_docs: List[str],
    context: Optional[str],
    hearing_type: str,
) -> Dict[str, Any]:
    """
    Prepare the sections and content for the barrister's brief.

    Args:
        case_facts: Structured case facts content
        strategies: Optional brainstormed strategies
        research_docs: List of research/lookup reports
        supporting_docs: List of supporting documents
        context: Optional additional context
        hearing_type: Type of hearing

    Returns:
        Dictionary containing prepared sections
    """
    sections = {
        "case_facts": case_facts,
        "hearing_type": hearing_type,
        "has_strategies": bool(strategies),
        "strategies": strategies or "",
        "research_count": len(research_docs),
        "research_content": "\n\n---\n\n".join(research_docs),
        "supporting_count": len(supporting_docs),
        "supporting_content": "\n\n---\n\n".join(supporting_docs),
        "context": context or "No specific context provided.",
    }

    return sections


@click.command()
@click.argument("case_facts", type=click.Path(exists=True))
@click.option(
    "--strategies",
    multiple=True,
    type=click.Path(),  # Remove exists=True since we check in callback
    callback=expand_glob_patterns,
    help="Brainstormed strategies files. Supports glob patterns. Use: --strategies 'outputs/brainstorm_*.txt'",
)
@click.option(
    "--research",
    multiple=True,
    type=click.Path(),
    callback=expand_glob_patterns,
    help="Lookup/research reports. Supports glob patterns. Use: --research 'outputs/lookup_*.txt'",
)
@click.option(
    "--documents",
    multiple=True,
    type=click.Path(),
    callback=expand_glob_patterns,
    help="Supporting documents. Supports glob patterns. Use: --documents '*.pdf'",
)
@click.option(
    "--context",
    type=str,
    help="Additional context to guide the analysis",
)
@click.option(
    "--hearing-type",
    type=click.Choice(["trial", "directions", "interlocutory", "appeal"]),
    required=True,
    help="Type of hearing",
)
@click.option(
    "--verify",
    is_flag=True,
    help="Enable citation verification",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.pass_context
@timed
def barbrief(
    ctx,
    case_facts,
    strategies,
    research,
    documents,
    context,
    hearing_type,
    verify,
    output,
):
    """
    Generate comprehensive barrister's brief for Australian litigation.

    Creates a structured brief combining case facts, legal strategies,
    research, and supporting documents. The brief follows Australian
    legal conventions and includes proper citation formatting.

    Args:
        case_facts: Path to structured case facts (10-heading format)
        strategies: Optional path to brainstormed strategies
        research: Optional research/lookup reports (multiple allowed)
        documents: Optional supporting documents (multiple allowed)
        context: Optional additional context to guide the analysis
        hearing_type: Type of hearing (trial/directions/interlocutory/appeal)
        verify: Whether to verify citations

    Raises:
        click.ClickException: If case facts are invalid or API calls fail
    """
    # Read and validate case facts
    click.echo("Reading case facts...")
    case_facts_content = read_document(case_facts)

    if not validate_case_facts(case_facts_content):
        raise click.ClickException(
            "Case facts must be in 10-heading format from extractfacts command"
        )

    # Read optional inputs
    strategies_content = ""
    if strategies:
        if len(strategies) == 1:
            click.echo("Reading strategies...")
            strategies_content = read_document(strategies[0])
        else:
            click.echo(f"Reading {len(strategies)} strategy files...")
            strategy_parts = []
            for strategy_file in strategies:
                content = read_document(strategy_file)
                strategy_parts.append(
                    f"=== SOURCE: {strategy_file} ===\n{content}\n=== END SOURCE: {strategy_file} ==="
                )
            strategies_content = "\n\n".join(strategy_parts)

    research_docs = []
    for research_file in research:
        click.echo(f"Reading research: {research_file}")
        research_docs.append(read_document(research_file))

    supporting_docs = []
    for doc_file in documents:
        click.echo(f"Reading document: {doc_file}")
        supporting_docs.append(read_document(doc_file))

    # Prepare sections
    sections = prepare_brief_sections(
        case_facts_content,
        strategies_content,
        research_docs,
        supporting_docs,
        context,
        hearing_type,
    )

    # Estimate total input size
    total_content = (
        case_facts_content
        + "\n"
        + strategies_content
        + "\n"
        + "\n".join(research_docs)
        + "\n"
        + "\n".join(supporting_docs)
    )
    total_tokens, _ = count_tokens_and_words(total_content)

    # Warn if large
    if total_tokens > 80000:
        click.echo(
            warning_message(
                f"Large input detected ({total_tokens:,} tokens). "
                f"This may exceed API limits. Consider using fewer documents."
            )
        )

    # Get LLM client
    try:
        client = LLMClientFactory.for_command("barbrief")
    except Exception as e:
        raise click.ClickException(f"Failed to initialize LLM client: {e}")

    # Create reasoning-enabled prompt
    try:
        base_prompt = PROMPTS.get("barbrief.main", **sections)
        prompt_with_reasoning = create_reasoning_prompt(base_prompt, "barbrief")
    except Exception as e:
        raise click.ClickException(f"Failed to prepare prompt: {e}")

    # Generate the brief
    click.echo("\nGenerating barrister's brief...")

    messages = [
        {"role": "system", "content": PROMPTS.get("barbrief.system")},
        {"role": "user", "content": prompt_with_reasoning},
    ]

    try:
        content, usage = client.complete(messages)
    except Exception as e:
        # Provide helpful error message for common issues
        if "timeout" in str(e).lower():
            raise click.ClickException(
                "Request timed out. The brief may be too large for a single request. "
                "Try reducing the number of input documents."
            )
        elif "rate limit" in str(e).lower():
            raise click.ClickException(
                "Rate limit exceeded. Please wait a moment and try again."
            )
        elif "api key" in str(e).lower():
            raise click.ClickException(
                "API key error. Please check your OpenAI/OpenRouter configuration."
            )
        elif "error occurred while processing" in str(e).lower():
            raise click.ClickException(
                f"API processing error (input was {total_tokens:,} tokens). "
                f"Try with fewer documents. Error: {e}"
            )
        else:
            raise click.ClickException(f"LLM API error: {e}")

    click.echo(f"\nGenerated brief ({usage.get('total_tokens', 'N/A')} tokens used)")

    # Run manual citation verification if requested
    # Note: Automatic verification already happens during generation via client.complete()
    # This provides additional detailed reporting when --verify flag is used
    if verify:
        click.echo("\nVerifying citations...")
        verified, unverified = verify_all_citations(content)

        if unverified:
            click.echo(f"Warning: {len(unverified)} citations could not be verified")
            # Save verification report
            verification_content = (
                f"CITATION VERIFICATION REPORT\n\n"
                f"Valid Citations: {len(verified)}\n"
                f"Invalid Citations: {len(unverified)}\n\n"
            )
            verification_content += "INVALID CITATIONS:\n"
            for cit, reason in unverified:
                verification_content += f"- {cit}: {reason}\n"

            verify_file = save_command_output(
                "barbrief", verification_content, "citation_verification"
            )
            click.echo(f"Verification report saved: {verify_file}")

    # Save the brief with comprehensive metadata
    metadata = {
        "Case Facts": case_facts,
        "Hearing Type": hearing_type.title(),
    }
    
    # Add optional file inputs if provided
    if strategies:
        metadata["Strategies"] = ", ".join(strategies)
    if research:
        metadata["Research"] = ", ".join(research)
    if documents:
        metadata["Documents"] = ", ".join(documents)
    if context:
        metadata["Context"] = context
    
    output_file = save_command_output(
        output if output else "barbrief", 
        content, 
        "" if output else hearing_type,
        metadata=metadata
    )

    # Show completion message
    show_command_completion(
        "Barristers brief generated",
        output_file,
        stats={"Tokens used": usage.get("total_tokens")},
    )
