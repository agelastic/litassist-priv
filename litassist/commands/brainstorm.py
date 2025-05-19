"""
Generate novel legal strategies via Grok.

This module implements the 'brainstorm' command which uses Grok's creative capabilities
to generate unorthodox litigation arguments or remedies based on provided case facts.
"""

import click

from litassist.utils import read_document, save_log, heartbeat
from litassist.llm import LLMClient


@click.command()
@click.argument("facts_file", type=click.Path(exists=True))
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
def brainstorm(facts_file, verify):
    """
    Generate novel legal strategies via Grok.

    Uses Grok's creative capabilities to generate ten unorthodox litigation
    arguments or remedies based on the facts provided. Particularly useful
    for brainstorming alternative legal approaches.

    Args:
        facts_file: Path to a text file containing structured case facts.
        verify: Whether to run a self-critique verification pass on the generated ideas.

    Raises:
        click.ClickException: If there are errors reading the facts file or with the LLM API call.
    """
    # Read the structured facts file
    facts = read_document(facts_file)

    # Initialize the LLM for creative ideation
    client = LLMClient("x-ai/grok-3-beta", temperature=0.9, top_p=0.95, max_tokens=1200)

    # Build and send the prompt
    prompt = f"Facts:\n{facts}\n\nList ten unorthodox litigation arguments or remedies not commonly raised."
    messages = [
        {"role": "system", "content": "Australian law only."},
        {"role": "user", "content": prompt},
    ]
    call_with_hb = heartbeat(30)(client.complete)
    try:
        content, usage = call_with_hb(messages)
    except Exception as e:
        raise click.ClickException(f"Grok brainstorming error: {e}")

    # Optional self-critique verification
    if verify:
        try:
            correction = client.verify(content)
            content = content + "\n\n--- Corrections ---\n" + correction
        except Exception as e:
            raise click.ClickException(f"Self-verification error during brainstorming: {e}")

    # Save audit log
    save_log(
        "brainstorm",
        {
            "inputs": {"facts_file": facts_file, "prompt": prompt},
            "params": f"verify={verify}",
            "response": content,
            "usage": usage,
        },
    )

    # Display the ideas
    click.echo(f"--- Ideas ---\n{content}")
