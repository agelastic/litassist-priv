"""
Rapid case-law lookup via Jade CSE + Gemini.

This module implements the 'lookup' command which searches for legal information
via Jade.io database using Google Custom Search, then processes the results with Google Gemini
to produce a structured legal answer citing relevant cases.
"""

import click
from litassist.utils import save_log, timed
from .search import perform_cse_searches
from .processors import LookupProcessor


@click.command()
@click.argument("question")
@click.option("--mode", type=click.Choice(["irac", "broad"]), default="irac")
@click.option(
    "--extract",
    type=click.Choice(["citations", "principles", "checklist"]),
    help="Extract specific information in a structured format",
)
@click.option(
    "--comprehensive",
    is_flag=True,
    help=(
        "Enable comprehensive mode: standard searches yield up to 5 results each from Jade and AustLII; "
        "comprehensive mode yields up to 10 results each from Jade, AustLII, and a secondary CSE."
    ),
)
@click.option(
    "--context",
    type=str,
    help="Contextual information to guide the lookup analysis",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.option("--no-fetch", is_flag=True, help="Skip content fetching, use URLs only")
@timed
def lookup(question, mode, extract, comprehensive, context, output, no_fetch):
    """
    Rapid case-law lookup via Jade CSE + Gemini.

    Searches for legal information using Jade.io database via Custom Search Engine,
    then processes the results with Google Gemini to produce a structured
    legal answer citing relevant cases.

    Args:
        question: The legal question to search for.
        mode: Answer format - 'irac' (Issue, Rule, Application, Conclusion) for
              structured analysis, or 'broad' for more creative exploration.
        extract: Extract specific information - 'citations' for case references,
                'principles' for legal rules, or 'checklist' for practical items.
        comprehensive: If True, switches to comprehensive mode: standard searches yield up to
            5 results each from Jade and AustLII; comprehensive searches yield up to
            10 results each from Jade, AustLII, and an additional CSE.

    Raises:
        click.ClickException: If there are errors with the search or LLM API calls.
    """
    # Initialize search service and perform searches
    links, all_snippets = perform_cse_searches(question, comprehensive, context)
    
    # Display found links
    click.echo("Found links:")
    for link in links:
        click.echo(f"- {link}")

    # Initialize processor and fetch content
    from litassist.config import CONFIG
    processor = LookupProcessor(CONFIG)
    contents = processor.fetch_content(links, all_snippets, no_fetch)
    
    # Build prompt and get LLM response
    content_text, estimated_tokens = processor.prepare_content(contents)
    prompt = processor.build_prompt(
        question, mode, extract, comprehensive, context, 
        links, contents, content_text
    )
    
    # Get LLM client with appropriate parameters
    client = processor.get_llm_client(mode, comprehensive)
    system_content = processor.build_system_prompt(extract, comprehensive)
    
    # Execute LLM request with retry logic
    content, usage = processor.execute_llm_request(
        client, system_content, prompt, estimated_tokens, contents
    )
    
    # Save the output
    output_file = processor.save_output(
        content, question, mode, extract, comprehensive, context, output
    )

    # Save audit log
    params_str = f"mode={mode}"
    if extract:
        params_str += f", extract={extract}"
    if comprehensive:
        params_str += ", comprehensive=True"

    save_log(
        "lookup",
        {
            "params": params_str,
            "inputs": {
                "question": question,
                "links": "\n".join(links),
                "context": context,
                "prompt": prompt,
            },
            "response": content,
            "usage": usage,
            "output_file": output_file,
        },
    )

    # Display completion summary
    processor.display_completion_summary(
        output_file, question, extract, comprehensive, context, links
    )