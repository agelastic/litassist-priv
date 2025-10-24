"""
Rapid case-law lookup via Jade CSE + Gemini.

This module implements the 'lookup' command which searches for legal information
via Jade.io database using Google Custom Search, then processes the results with Google Gemini
to produce a structured legal answer citing relevant cases.
"""

import click
from litassist.config import get_config
from litassist.logging import save_log, log_task_event
from litassist.timing import timed
from litassist.llm.factory import LLMClientFactory
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
@click.option(
    "--verify",
    is_flag=True,
    help="Not supported - lookup results are not verified. Use 'litassist verify' command for verification.",
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Not supported - lookup has no internal verification.",
)
@timed
def lookup(
    question, mode, extract, comprehensive, context, output, no_fetch, verify, noverify
):
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
    # Command start log
    try:
        log_task_event(
            "lookup",
            "init",
            "start",
            "Starting lookup command",
            {"model": LLMClientFactory.get_model_for_command("lookup")}
        )
    except Exception:
        pass
    
    # Handle unsupported verification flags
    if verify:
        from litassist.utils.formatting import warning_message

        click.echo(
            warning_message(
                "--verify not supported: This command has no internal verification. Use 'litassist verify' for post-processing verification."
            )
        )
    if noverify:
        from litassist.utils.formatting import warning_message

        click.echo(
            warning_message(
                "--noverify not supported: This command has no verification to skip."
            )
        )

    # Initialize search service and perform searches
    try:
        log_task_event(
            "lookup",
            "search",
            "start",
            "Starting CSE searches"
        )
    except Exception:
        pass
    
    links, all_snippets = perform_cse_searches(question, comprehensive, context)
    
    try:
        log_task_event(
            "lookup",
            "search",
            "end",
            f"CSE searches complete - found {len(links)} links"
        )
    except Exception:
        pass

    # Display found links
    click.echo("Found links:")
    for link in links:
        click.echo(f"- {link}")

    # Initialize processor and fetch content
    processor = LookupProcessor(get_config())
    
    try:
        log_task_event(
            "lookup",
            "fetching",
            "start",
            f"Starting content fetching from {len(links)} sources"
        )
    except Exception:
        pass
    
    contents = processor.fetch_content(links, all_snippets, no_fetch)
    
    try:
        log_task_event(
            "lookup",
            "fetching",
            "end",
            f"Content fetching complete - {len(contents)} documents"
        )
    except Exception:
        pass

    # Get LLM client with appropriate parameters
    client = processor.get_llm_client(mode, comprehensive)
    system_content = processor.build_system_prompt(extract, comprehensive)

    # Execute LLM request with retry logic and drop-largest truncation
    try:
        content, usage = processor.execute_llm_request(
            client, system_content, question, mode, extract, comprehensive,
            context, links, contents
        )
    except Exception as e:
        import traceback
        from litassist.utils.formatting import error_message, tip_message
        
        error_msg = str(e)
        
        # Log full error for debugging
        save_log("lookup_error", {
            "error": error_msg,
            "traceback": traceback.format_exc(),
            "question": question,
            "links_count": len(links),
            "documents_count": len(contents)
        })
        
        # Show clean error to user
        if "after dropping all documents" in error_msg:
            click.echo(error_message("Query too complex: Unable to process even without fetched content"))
            click.echo(tip_message("Try: 1) A more specific query, 2) --no-fetch flag, or 3) Fewer search terms"))
        elif "attempts" in error_msg and "remaining" in error_msg:
            click.echo(error_message(f"Processing failed: {error_msg}"))
            click.echo(tip_message("The query may be too complex for the model's context window"))
        else:
            click.echo(error_message(f"Lookup failed: {error_msg}"))
        
        # Exit cleanly without traceback
        raise click.ClickException("")

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
    
    # Command end log
    try:
        log_task_event(
            "lookup",
            "init",
            "end",
            "Lookup command complete"
        )
    except Exception:
        pass
