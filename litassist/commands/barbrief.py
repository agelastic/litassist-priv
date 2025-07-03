"""
Generate comprehensive barrister's brief for Australian litigation.

This module implements the 'barbrief' command which consolidates case materials
into a structured brief suitable for briefing counsel. It combines case facts,
strategies, research, and supporting documents into a comprehensive document
with proper citations and Australian legal formatting.
"""

import click
import os
from typing import List, Optional, Dict, Any

from litassist.config import CONFIG
from litassist.prompts import PROMPTS
from litassist.utils import (
    read_document,
    save_log,
    heartbeat,
    timed,
    create_reasoning_prompt,
    extract_reasoning_trace,
    save_reasoning_trace,
    save_command_output,
    show_command_completion,
    verify_content_if_needed,
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
    instructions: Optional[str],
    hearing_type: str,
) -> Dict[str, Any]:
    """
    Prepare the sections and content for the barrister's brief.
    
    Args:
        case_facts: Structured case facts content
        strategies: Optional brainstormed strategies
        research_docs: List of research/lookup reports
        supporting_docs: List of supporting documents
        instructions: Optional specific instructions
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
        "instructions": instructions or "No specific instructions provided.",
    }
    
    return sections


@click.command()
@click.argument("case_facts", type=click.Path(exists=True))
@click.option(
    "--strategies",
    type=click.Path(exists=True),
    help="Brainstormed strategies file",
)
@click.option(
    "--research",
    multiple=True,
    type=click.Path(exists=True),
    help="Lookup/research reports (can specify multiple)",
)
@click.option(
    "--documents",
    multiple=True,
    type=click.Path(exists=True),
    help="Supporting documents (can specify multiple)",
)
@click.option(
    "--instructions",
    type=str,
    help="Specific instructions for counsel",
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
@click.pass_context
@timed
def barbrief(
    ctx,
    case_facts,
    strategies,
    research,
    documents,
    instructions,
    hearing_type,
    verify,
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
        instructions: Optional specific instructions for counsel
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
    strategies_content = None
    if strategies:
        click.echo("Reading strategies...")
        strategies_content = read_document(strategies)
    
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
        instructions,
        hearing_type,
    )
    
    # Get LLM client
    client = LLMClientFactory.get_client("barbrief")
    
    # Create reasoning-enabled prompt
    base_prompt = PROMPTS.get_prompt("barbrief", "main", **sections)
    prompt_with_reasoning = create_reasoning_prompt(base_prompt)
    
    # Generate the brief
    click.echo("\nGenerating barrister's brief...")
    heartbeat()
    
    messages = [
        {"role": "system", "content": PROMPTS.get_prompt("barbrief", "system")},
        {"role": "user", "content": prompt_with_reasoning},
    ]
    
    content, usage = client.complete(messages, skip_citation_verification=True)
    
    click.echo(f"\nGenerated brief ({usage.get('total_tokens', 'N/A')} tokens used)")
    
    # Extract and save reasoning trace
    reasoning_trace = extract_reasoning_trace(content)
    if reasoning_trace:
        reasoning_file = save_reasoning_trace(
            reasoning_trace, "barbrief", "brief_generation"
        )
        click.echo(f"Reasoning trace saved: {reasoning_file}")
        content = reasoning_trace["conclusion"]
    
    # Run citation verification if requested
    if verify:
        click.echo("\nVerifying citations...")
        verified, unverified = verify_all_citations(content)
        
        if unverified:
            click.echo(
                f"Warning: {len(unverified)} citations could not be verified"
            )
            # Save verification report
            verification_content = (
                f"CITATION VERIFICATION REPORT\n\n"
                f"Valid Citations: {len(verified)}\n"
                f"Invalid Citations: {len(unverified)}\n\n"
            )
            if unverified:
                verification_content += "INVALID CITATIONS:\n"
                for cit, reason in unverified:
                    verification_content += f"- {cit}: {reason}\n"
            
            verify_file = save_command_output(
                verification_content, "barbrief", "citation_verification"
            )
            click.echo(f"Verification report saved: {verify_file}")
    
    # Save the brief
    output_file = save_command_output(content, "barbrief", hearing_type)
    
    # Show completion message
    show_command_completion(
        "Barrister's brief generated",
        output_file,
        usage.get("total_tokens"),
    )
    
    # Final verification if needed
    verify_content_if_needed(ctx, content, client.command_context)