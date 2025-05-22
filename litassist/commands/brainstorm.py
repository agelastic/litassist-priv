"""
Generate comprehensive legal strategies via Grok.

This module implements the 'brainstorm' command which uses Grok's creative capabilities
to generate both orthodox and unorthodox litigation strategies based on provided case facts,
tailored to the specified party (plaintiff/defendant) and legal area.
"""

import click

from litassist.utils import read_document, save_log, heartbeat
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
@click.option("--verify", is_flag=True, help="Enable self-critique pass (auto-enabled for Grok models)")
def brainstorm(facts_file, side, area, verify):
    """
    Generate comprehensive legal strategies via Grok.

    Uses Grok's creative capabilities to generate:
    - 10 orthodox legal strategies
    - 10 unorthodox but potentially effective strategies
    - A list of strategies most likely to succeed

    All strategies are tailored to your specified party side and legal area.

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

    # Initialize the LLM for creative ideation
    client = LLMClient("x-ai/grok-3-beta", temperature=0.9, top_p=0.95)
    client.command_context = "brainstorm"  # Set command context
    
    # Auto-verify for Grok due to hallucination tendency
    if "grok" in client.model.lower():
        verify = True  # Force verification for Grok models

    # Build and send the prompt
    prompt = f"""Facts:
{facts}

I am representing the {side} in this {area} law matter.

Please provide THREE distinct sections:
1. List 10 "orthodox" litigation strategies commonly used in this type of case.
2. List 10 "unorthodox but potentially effective" strategies that are not commonly raised but could work.
3. Identify which 3-5 strategies (from either list) are most likely to succeed given the facts.

For each strategy, provide:
- A clear title
- Brief explanation (1-2 sentences)
- Key legal principles or precedents that support it
"""
    messages = [
        {
            "role": "system",
            "content": "Australian law only. Provide practical, actionable legal strategies. Balance creativity with factual accuracy. When suggesting strategies, clearly distinguish between established legal approaches and more innovative options. For orthodox strategies, cite relevant case law or legislation. For unorthodox strategies, acknowledge any legal uncertainties or risks. Maintain logical structure throughout your response. End with a clear, definitive recommendation section without open-ended statements.",
        },
        {"role": "user", "content": prompt},
    ]
    call_with_hb = heartbeat(30)(client.complete)
    try:
        content, usage = call_with_hb(messages)
    except Exception as e:
        raise click.ClickException(f"Grok brainstorming error: {e}")

    # Smart verification - auto-enabled for Grok or when requested
    if verify or client.should_auto_verify(content, "brainstorm"):
        try:
            # Use medium verification for creative brainstorming
            correction = client.verify_with_level(content, "medium")
            if correction.strip():  # Only append if there are actual corrections
                content = content + "\n\n--- Strategic Review ---\n" + correction
                
            # Run citation validation for any legal references
            citation_issues = client.validate_citations(content)
            if citation_issues:
                content += "\n\n--- Citation Warnings ---\n" + "\n".join(citation_issues)
                
        except Exception as e:
            raise click.ClickException(
                f"Verification error during brainstorming: {e}"
            )

    # Save audit log
    save_log(
        "brainstorm",
        {
            "inputs": {"facts_file": facts_file, "prompt": prompt},
            "params": f"verify={verify} (auto-enabled for Grok)",
            "response": content,
            "usage": usage,
        },
    )

    # Display the ideas
    click.echo(
        f"--- {area.capitalize()} Law Strategies for {side.capitalize()} ---\n{content}"
    )
