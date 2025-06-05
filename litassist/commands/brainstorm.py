"""
Generate comprehensive legal strategies via Grok.

This module implements the 'brainstorm' command which uses Grok's creative capabilities
to generate both orthodox and unorthodox litigation strategies based on provided case facts,
tailored to the specified party (plaintiff/defendant) and legal area.
"""

import click
import os
import time

from litassist.config import CONFIG
from litassist.utils import (
    read_document,
    save_log,
    heartbeat,
    OUTPUT_DIR,
    create_reasoning_prompt,
    extract_reasoning_trace,
    save_reasoning_trace,
)
from litassist.llm import LLMClient


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
    "--verify",
    is_flag=True,
    help="Enable self-critique pass (auto-enabled for Grok models)",
)
def brainstorm(facts_file, side, area, verify):
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
        verify: Whether to run a self-critique verification pass on the generated ideas.

    Raises:
        click.ClickException: If there are errors reading the facts file or with the LLM API call.
    """
    # Check for potentially incompatible side/area combinations
    valid_combinations = {
        "criminal": ["accused"],
        "civil": ["plaintiff", "defendant"],
        "family": ["plaintiff", "defendant", "respondent"],
        "commercial": ["plaintiff", "defendant"],
        "administrative": ["plaintiff", "defendant", "respondent"],
    }

    if area in valid_combinations and side not in valid_combinations[area]:
        warning_msg = click.style(
            f"Warning: '{side}' is not typically used in {area} matters. ",
            fg="yellow",
            bold=True,
        )
        suggestion = click.style(
            f"Standard options for {area} are: {', '.join(valid_combinations[area])}\n",
            fg="yellow",
        )
        click.echo(warning_msg + suggestion)

        # Add specific warnings for common mistakes
        if side == "plaintiff" and area == "criminal":
            click.echo(
                click.style(
                    "Note: Criminal cases use 'accused' instead of 'plaintiff/defendant'\n",
                    fg="yellow",
                )
            )
        elif side == "accused" and area != "criminal":
            click.echo(
                click.style(
                    "Note: 'Accused' is typically only used in criminal matters\n",
                    fg="yellow",
                )
            )

    # Read the structured facts file
    facts = read_document(facts_file)

    # Check file size to prevent token limit issues
    if len(facts) > 50000:  # ~10,000 words
        raise click.ClickException(
            f"Case facts file too large ({len(facts):,} characters). "
            "Please provide a concise summary under 50,000 characters (~10,000 words). "
            "Consider using 'extractfacts' command to create a structured summary first."
        )

    # Auto-verify for Grok due to hallucination tendency
    if "grok" in "x-ai/grok-3-beta".lower():
        verify = True  # Force verification for Grok models

    # Generate Orthodox Strategies (conservative approach)
    click.echo("Generating orthodox strategies...")
    orthodox_client = LLMClient("x-ai/grok-3-beta", temperature=0.3, top_p=0.7)
    orthodox_client.command_context = "brainstorm-orthodox"

    orthodox_base_prompt = f"""Facts:
{facts}

I am representing the {side} in this {area} law matter.

Generate 10 ORTHODOX legal strategies - established, conservative approaches with strong legal precedent.

Please provide output in EXACTLY this format:

## ORTHODOX STRATEGIES

1. [Strategy Title]
   [Brief explanation (1-2 sentences)]
   Key principles: [Legal principles or precedents with citations]

2. [Strategy Title]
   [Brief explanation]
   Key principles: [Legal principles with citations]

[Continue for 10 orthodox strategies]

Focus on well-established legal approaches with clear precedential support."""

    orthodox_prompt = orthodox_base_prompt
    orthodox_messages = [
        {
            "role": "system",
            "content": "Australian law only. Provide conservative, well-established legal strategies with strong precedential support. Cite relevant case law or legislation for each strategy. Focus on proven approaches with minimal legal risk.",
        },
        {"role": "user", "content": orthodox_prompt},
    ]

    call_with_hb = heartbeat(CONFIG.heartbeat_interval)(orthodox_client.complete)
    try:
        orthodox_content, orthodox_usage = call_with_hb(orthodox_messages)
    except Exception as e:
        raise click.ClickException(f"Error generating orthodox strategies: {e}")

    # Validate orthodox citations immediately
    orthodox_citation_issues = orthodox_client.validate_citations(orthodox_content)
    if orthodox_citation_issues:
        click.echo(f"  ⚠️  Found {len(orthodox_citation_issues)-1} citation issues in orthodox strategies")

    # Generate Unorthodox Strategies (creative approach)
    click.echo("Generating unorthodox strategies...")
    unorthodox_client = LLMClient("x-ai/grok-3-beta", temperature=0.9, top_p=0.95)
    unorthodox_client.command_context = "brainstorm-unorthodox"

    unorthodox_base_prompt = f"""Facts:
{facts}

I am representing the {side} in this {area} law matter.

Generate 10 UNORTHODOX legal strategies - creative, innovative approaches that push legal boundaries.

Please provide output in EXACTLY this format:

## UNORTHODOX STRATEGIES

1. [Strategy Title]
   [Brief explanation (1-2 sentences)]
   Key principles: [Legal principles or novel arguments]

2. [Strategy Title]
   [Brief explanation]
   Key principles: [Legal principles or innovative theories]

[Continue for 10 unorthodox strategies]

Be creative and innovative while acknowledging any legal uncertainties or risks."""

    unorthodox_prompt = unorthodox_base_prompt
    unorthodox_messages = [
        {
            "role": "system",
            "content": "Australian law only. Provide creative, innovative legal strategies that push boundaries. Acknowledge legal uncertainties and risks. Suggest novel approaches while maintaining ethical boundaries.",
        },
        {"role": "user", "content": unorthodox_prompt},
    ]

    try:
        unorthodox_content, unorthodox_usage = call_with_hb(unorthodox_messages)
    except Exception as e:
        raise click.ClickException(f"Error generating unorthodox strategies: {e}")

    # Validate unorthodox citations immediately
    unorthodox_citation_issues = unorthodox_client.validate_citations(unorthodox_content)
    if unorthodox_citation_issues:
        click.echo(f"  ⚠️  Found {len(unorthodox_citation_issues)-1} citation issues in unorthodox strategies")

    # Generate Most Likely to Succeed analysis
    click.echo("Analyzing most promising strategies...")
    analysis_client = LLMClient("x-ai/grok-3-beta", temperature=0.4, top_p=0.8)
    analysis_client.command_context = "brainstorm-analysis"

    analysis_base_prompt = f"""Facts:
{facts}

I am representing the {side} in this {area} law matter.

ORTHODOX STRATEGIES GENERATED:
{orthodox_content}

UNORTHODOX STRATEGIES GENERATED:
{unorthodox_content}

Analyze ALL the strategies above and select the 3-5 most likely to succeed.

Please provide output in EXACTLY this format:

## MOST LIKELY TO SUCCEED

1. [Strategy Title from above]
   [Why this strategy is most likely to succeed]

2. [Strategy Title from above]
   [Why this strategy is most likely to succeed]

[List 3-5 strategies total that are most likely to succeed]

Consider both orthodox and unorthodox options. Base selections on legal merit, factual support, and likelihood of judicial acceptance."""

    analysis_prompt = create_reasoning_prompt(
        analysis_base_prompt, "brainstorm-analysis"
    )
    analysis_messages = [
        {
            "role": "system",
            "content": "Australian law only. Analyze strategies objectively. Consider legal merit, factual support, precedential strength, and judicial likelihood. Provide clear reasoning for selections.",
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

    # Store original content before verification
    original_content = combined_content
    usage = total_usage
    verification_notes = []

    # Smart verification - auto-enabled for Grok or when requested
    # Use analysis_client for verification since it has balanced settings
    if verify or analysis_client.should_auto_verify(original_content, "brainstorm"):
        try:
            # Use medium verification for creative brainstorming
            correction = analysis_client.verify_with_level(original_content, "medium")
            if correction.strip():  # Only append if there are actual corrections
                verification_notes.append("--- Strategic Review ---\n" + correction)

            # Run citation validation for any legal references
            citation_issues = analysis_client.validate_citations(original_content)
            if citation_issues:
                verification_notes.append(
                    "--- Citation Warnings ---\n" + "\n".join(citation_issues)
                )

        except Exception as e:
            raise click.ClickException(f"Verification error during brainstorming: {e}")

    # Extract reasoning trace before saving
    reasoning_trace = extract_reasoning_trace(original_content, "brainstorm")

    # Save audit log (with full content including verification)
    full_content = original_content
    if verification_notes:
        full_content += "\n\n" + "\n\n".join(verification_notes)

    save_log(
        "brainstorm",
        {
            "inputs": {"facts_file": facts_file, "method": "three-stage approach"},
            "params": f"verify={verify} (auto-enabled for Grok), orthodox_temp=0.3, unorthodox_temp=0.9, analysis_temp=0.4",
            "response": full_content,
            "usage": usage,
            "stages": {
                "orthodox": {"usage": orthodox_usage, "temperature": 0.3},
                "unorthodox": {"usage": unorthodox_usage, "temperature": 0.9},
                "analysis": {"usage": analysis_usage, "temperature": 0.4},
            },
        },
    )

    # Save to timestamped file only
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"brainstorm_{area}_{side}_{timestamp}.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Legal Strategies\n")
        f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# Side: {side.capitalize()}\n")
        f.write(f"# Area: {area.capitalize()}\n")
        f.write(f"# Source: {facts_file}\n\n")
        f.write(original_content)

    click.echo(f"Strategies saved to: {output_file}")

    # Save reasoning trace if extracted
    if reasoning_trace:
        reasoning_file = save_reasoning_trace(reasoning_trace, output_file)
        click.echo(f"Legal reasoning trace saved to: {reasoning_file}")

    click.echo(
        "\nTo use these strategies with other commands, manually create or update strategies.txt"
    )

    # Save verification notes separately if any exist
    if verification_notes:
        verification_file = os.path.join(
            OUTPUT_DIR, f"brainstorm_verification_{area}_{side}_{timestamp}.txt"
        )
        with open(verification_file, "w", encoding="utf-8") as f:
            f.write(f"# Verification Notes for Strategies\n")
            f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("\n\n".join(verification_notes))
        click.echo(f"Verification notes saved to {verification_file}")

    # Display the ideas with verification
    display_content = original_content
    if verification_notes:
        display_content += "\n\n" + "\n\n".join(verification_notes)

    click.echo(
        f"\n--- {area.capitalize()} Law Strategies for {side.capitalize()} ---\n{display_content}"
    )
