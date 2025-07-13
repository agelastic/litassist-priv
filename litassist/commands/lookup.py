"""
Rapid case-law lookup via Jade CSE + Gemini.

This module implements the 'lookup' command which searches for legal information
via Jade.io database using Google Custom Search, then processes the results with Google Gemini
to produce a structured legal answer citing relevant cases.
"""

import click
import warnings
import os
import logging
import time

from litassist.config import CONFIG
from litassist.utils import (
    save_log, heartbeat, timed, save_command_output, process_extraction_response,
    warning_message, success_message, saved_message, stats_message,
    info_message, verifying_message, tip_message
)
from litassist.llm import LLMClientFactory
from litassist.prompts import PROMPTS

# Suppress Google API cache warning
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
warnings.filterwarnings("ignore", message=".*file_cache.*")




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
    help="Use exhaustive analysis with maximum sources (40 instead of 5)",
)
@click.option(
    "--context",
    type=str,
    help="Contextual information to guide the lookup analysis",
)
@timed
def lookup(question, mode, extract, comprehensive, context):
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
        comprehensive: Use exhaustive analysis with 20 sources instead of 5.

    Raises:
        click.ClickException: If there are errors with the search or LLM API calls.
    """
    # Determine search parameters based on comprehensive flag
    if comprehensive:
        max_sources = 20
    else:
        max_sources = 5

    # Fetch case links using Jade CSE
    try:
        from googleapiclient.discovery import build

        service = build(
            "customsearch", "v1", developerKey=CONFIG.g_key, cache_discovery=False
        )

        if comprehensive:
            # Comprehensive Jade CSE search - 2 calls for 20 results
            all_links = []
            queries = [
                question,
                f"{question} case law",
            ]

            for query in queries:
                res = (
                    service.cse()
                    .list(
                        q=query, cx=CONFIG.cse_id
                    )
                    .execute()
                )
                all_links.extend([item.get("link") for item in res.get("items", [])])

            # Remove duplicates while preserving order
            seen = set()
            links = []
            for link in all_links:
                if link and link not in seen:
                    seen.add(link)
                    links.append(link)
                    if len(links) >= max_sources:
                        break
        else:
            # Standard Jade CSE search
            res = (
                service.cse()
                .list(
                    q=question, cx=CONFIG.cse_id
                )
                .execute()
            )
            links = [item.get("link") for item in res.get("items", [])][:max_sources]

    except Exception as e:
        raise click.ClickException(f"Search error: {e}")

    # Add comprehensive CSE search if configured
    if comprehensive and CONFIG.cse_id_comprehensive:
        try:
            # Reuse the service instance for the comprehensive search
            res_comp = (
                service.cse()
                .list(q=question, cx=CONFIG.cse_id_comprehensive)
                .execute()
            )
            links.extend([item.get("link") for item in res_comp.get("items", [])])
        except Exception as e:
            click.echo(f"Warning: Secondary CSE search failed: {e}")
            logging.exception("Secondary CSE search failed", exc_info=e)
            # Continue with existing links from primary search

    # Display found links
    click.echo("Found links:")
    for link in links:
        click.echo(f"- {link}")

    # Prepare prompt
    prompt = f"Question: {question}\nLinks:\n" + "\n".join(links)
    if context:
        prompt = f"Context: {context}\n\n{prompt}"

    # Add extraction-specific instructions
    if extract:
        if extract == "citations":
            prompt += f"\n\n{PROMPTS.get('lookup.extraction_instructions.citations')}"
        elif extract == "principles":
            prompt += f"\n\n{PROMPTS.get('lookup.extraction_instructions.principles')}"
        elif extract == "checklist":
            prompt += f"\n\n{PROMPTS.get('lookup.extraction_instructions.checklist')}"
    # Set parameters based on mode and comprehensive flag
    if comprehensive:
        if mode == "irac":
            overrides = {
                "temperature": 0,
                "top_p": 0.05,
                "max_tokens": 8192,
            }  # Maximum precision
        else:  # broad
            overrides = {
                "temperature": 0.3,
                "top_p": 0.7,
                "max_tokens": 8192,
            }  # Controlled creativity
    else:
        # Standard parameters
        if mode == "irac":
            overrides = {"temperature": 0, "top_p": 0.1}
        else:
            overrides = {"temperature": 0.5, "top_p": 0.9}

    # Use LLMClientFactory to create the client
    client = LLMClientFactory.for_command("lookup", **overrides)
    call_with_hb = heartbeat(CONFIG.heartbeat_interval)(client.complete)

    # Set system prompt based on mode
    base_system = PROMPTS.get("base.australian_law")
    
    # Special system prompt for extraction mode
    if extract:
        extraction_system = PROMPTS.get("lookup.extraction_system")
        system_content = f"{base_system}\n\n{extraction_system}"
    elif comprehensive:
        requirements = PROMPTS.get("lookup.comprehensive_analysis.requirements")
        citation_requirements = PROMPTS.get(
            "lookup.comprehensive_analysis.citation_requirements"
        )
        output_structure = PROMPTS.get("lookup.comprehensive_analysis.output_structure")
        system_content = f"""{base_system} Provide exhaustive legal analysis.

{requirements}

{citation_requirements}

{output_structure}"""
    else:
        standard_instructions = PROMPTS.get("lookup.standard_analysis.instructions")
        system_content = f"{base_system}\n\n{standard_instructions}"

    try:
        content, usage = call_with_hb(
            [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ]
        )
    except Exception as e:
        # Check if it's a citation verification error
        if "Citation verification failed" in str(e):
            # Extract just the error message after any citation warnings
            click.echo(warning_message("Citation verification issues detected"))
            # The error contains the citations that failed - we can still proceed with warnings
            raise click.ClickException(f"LLM error during lookup: {e}")
        else:
            raise click.ClickException(f"LLM error during lookup: {e}")

    # Process extraction if requested
    if extract:
        # Generate output prefix for files
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_prefix = f"lookup_{extract}_{timestamp}"
        
        # Use shared extraction utility
        formatted_content, json_data, json_file = process_extraction_response(
            content, extract, output_prefix, "lookup"
        )
        
        # Save the formatted text output
        command_name = f"lookup_{extract}"
        metadata = {"Mode": mode, "Extract": extract}
        if context:
            metadata["Context"] = context
        if comprehensive:
            metadata["Comprehensive"] = "True"
        metadata["JSON File"] = json_file
        
        output_file = save_command_output(
            command_name, formatted_content, question, metadata=metadata
        )
    else:
        # Non-extraction mode - save content as-is
        formatted_content = content
        command_name = "lookup"
        metadata = {"Mode": mode}
        if context:
            metadata["Context"] = context
        if comprehensive:
            metadata["Comprehensive"] = "True"
        
        output_file = save_command_output(
            command_name, formatted_content, question, metadata=metadata
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
            "formatted_output": formatted_content,
            "usage": usage,
            "output_file": output_file,
        },
    )

    # Show summary instead of full content
    click.echo(f"\n{success_message('Lookup complete!')}")
    click.echo(saved_message(f'Output saved to: "{output_file}"'))

    # Show what was found
    if extract:
        extract_type = extract.capitalize()
        msg = stats_message(f'{extract_type} extracted from search results')
        click.echo(f"\n{msg}")
    else:
        analysis_type = "Exhaustive" if comprehensive else "Standard"
        msg = stats_message(f'{analysis_type} legal analysis for: {question}')
        click.echo(f"\n{msg}")

    # Show context if provided
    if context:
        click.echo(info_message(f"Context: '{context}'"))

    # Show links that were searched
    if comprehensive:
        msg = verifying_message(f'Exhaustive search: {len(links)} sources analyzed')
        click.echo(f"\n{msg}")
    else:
        msg = verifying_message(f'Standard search: {len(links)} sources analyzed')
        click.echo(f"\n{msg}")

    for i, link in enumerate(links, 1):
        click.echo(f"   {i}. {link}")

    tip_msg = tip_message(f'View full analysis: open "{output_file}"')
    click.echo(f"\n{tip_msg}")
