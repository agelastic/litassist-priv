"""
Rapid case-law lookup via Jade CSE + Gemini.

This module implements the 'lookup' command which searches for legal information
via Jade.io database using Google Custom Search, then processes the results with Google Gemini
to produce a structured legal answer citing relevant cases.
"""

import click
import json
import re
import warnings
import os
import logging

from litassist.config import CONFIG
from litassist.utils import save_log, heartbeat, timed, save_command_output
from litassist.llm import LLMClientFactory
from litassist.prompts import PROMPTS

# Suppress Google API cache warning
os.environ["GOOGLE_API_USE_CLIENT_CERTIFICATE"] = "false"
warnings.filterwarnings("ignore", message=".*file_cache.*")


@timed
def format_lookup_output(content: str, extract: str = None) -> str:
    """
    Add basic structure to lookup output or extract specific information.

    Args:
        content: The raw LLM response
        extract: Type of extraction - 'citations', 'principles', or 'checklist'

    Returns:
        Formatted output based on extraction type
    """
    if extract:
        # Try JSON parsing first for structured output
        try:
            json_data = json.loads(content)
            if isinstance(json_data, dict) and extract in json_data:
                items = json_data[extract]
                if isinstance(items, list) and items:
                    # Format based on extract type
                    if extract == "citations":
                        return "CITATIONS FOUND:\n" + "\n".join(items)
                    elif extract == "principles":
                        return "LEGAL PRINCIPLES:\n" + "\n".join(
                            f"• {item}" for item in items
                        )
                    elif extract == "checklist":
                        return "PRACTICAL CHECKLIST:\n" + "\n".join(
                            f"□ {item}" for item in items
                        )
        except (json.JSONDecodeError, TypeError, KeyError):
            # Fall back to regex-based extraction if JSON parsing fails
            pass

    # Fallback regex-based extraction (original logic)
    if extract == "citations":
        # Extract citations using multiple regex patterns
        citations = set()

        # Pattern 1: [Year] Court abbreviation number
        citations.update(re.findall(r"\[\d{4}\]\s+[A-Z]+[A-Za-z]*\s+\d+", content))

        # Pattern 2: (Year) volume court page
        citations.update(
            re.findall(r"\(\d{4}\)\s+\d+\s+[A-Z]+[A-Za-z]*\s+\d+", content)
        )

        # Pattern 3: Act references
        citations.update(re.findall(r"[A-Za-z\s]+Act\s+\d{4}\s*\([A-Z]+\)", content))

        # Pattern 4: Section references with acts
        citations.update(
            re.findall(
                r"[A-Za-z\s]+Act\s+\d{4}\s*\([A-Z]+\)\s+s\s*\d+[A-Za-z]*", content
            )
        )

        if citations:
            return "CITATIONS FOUND:\n" + "\n".join(sorted(citations))
        else:
            return "No clear citations found in the response."

    elif extract == "principles":
        # Extract sentences that contain legal principles
        # First try to split by common delimiters
        principles = []

        # Try multiple splitting strategies
        # 1. First try newlines
        lines = content.split("\n")

        # If no newlines or very few lines, try splitting by sentences
        if len(lines) <= 2:
            # Split by sentence endings followed by capital letter or number
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", content)
            lines = sentences

        # Also split by bullet points or numbering patterns
        for line in lines:
            # Further split by common list patterns
            sub_lines = re.split(r"(?:^|\s)(?:\d+\.|[•*-])\s*", line)
            for sub_line in sub_lines:
                sub_line = sub_line.strip()
                # Look for lines that contain key legal terms
                if sub_line and any(
                    term in sub_line.lower()
                    for term in [
                        "must",
                        "requires",
                        "establishes",
                        "principle",
                        "rule",
                        "test",
                        "elements",
                        "duty",
                        "breach",
                        "standard",
                        "defendant",
                        "plaintiff",
                        "court",
                    ]
                ):
                    if len(sub_line) > 20:  # Filter out very short lines
                        # Clean up the line
                        clean_line = re.sub(
                            r"^\d+\.\s*", "", sub_line
                        )  # Remove numbering
                        clean_line = re.sub(
                            r"^[•*-]\s*", "", clean_line
                        )  # Remove bullets
                        if clean_line and clean_line not in principles:
                            principles.append(clean_line)

        if principles:
            return "LEGAL PRINCIPLES:\n" + "\n".join(
                f"• {p}" for p in principles[:10]
            )  # Limit to 10
        else:
            return "No clear legal principles extracted from the response."

    elif extract == "checklist":
        # Extract actionable items or requirements
        checklist_items = []

        # Try multiple splitting strategies
        lines = content.split("\n")

        # If no newlines or very few lines, try splitting by sentences
        if len(lines) <= 2:
            # Split by sentence endings
            sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", content)
            lines = sentences

        # Process all lines
        for line in lines:
            # Further split by common list patterns
            sub_lines = re.split(r"(?:^|\s)(?:\d+\.|[•*-])\s*", line)
            for sub_line in sub_lines:
                sub_line = sub_line.strip()
                # Look for lines that suggest requirements or steps
                if sub_line and any(
                    word in sub_line.lower()
                    for word in [
                        "must",
                        "should",
                        "require",
                        "need",
                        "evidence",
                        "prove",
                        "establish",
                        "demonstrate",
                        "ensure",
                        "verify",
                        "confirm",
                        "check",
                        "assess",
                    ]
                ):
                    if len(sub_line) > 15 and not sub_line.startswith(
                        "http"
                    ):  # Filter out URLs and short lines
                        # Clean up the line
                        clean_line = re.sub(
                            r"^[-•*]\s*", "", sub_line
                        )  # Remove bullet points
                        clean_line = re.sub(
                            r"^\d+\.\s*", "", clean_line
                        )  # Remove numbering
                        clean_line = clean_line.strip()
                        # Split very long lines at sentence boundaries
                        if len(clean_line) > 150:
                            sub_sentences = re.split(
                                r"(?<=[.!?])\s+(?=[A-Z])", clean_line
                            )
                            for sub_sent in sub_sentences:
                                if (
                                    len(sub_sent) > 10
                                    and sub_sent not in checklist_items
                                ):
                                    checklist_items.append(sub_sent)
                        elif len(clean_line) > 10 and clean_line not in checklist_items:
                            checklist_items.append(clean_line)

        if checklist_items:
            return "PRACTICAL CHECKLIST:\n" + "\n".join(
                f"□ {item}" for item in checklist_items[:15]
            )  # Limit to 15
        else:
            return "No clear checklist items extracted from the response."

    else:
        # Default: Fix Gemini-specific formatting issues
        formatted = content

        # Fix Gemini's broken markdown headers where closing ** appears on next line
        # Pattern: "### **Summary*\n*" -> "### **Summary**"
        formatted = re.sub(r"(\*)\n(\*)", r"\1\2", formatted)

        # Also fix cases where there's extra spacing
        formatted = re.sub(r"(\*)\s*\n\s*(\*)", r"\1\2", formatted)

        return formatted


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
                comp_service.cse()
                .list(q=question, cx=CONFIG.cse_id_comprehensive)
                .execute()
            )
            links.extend([item.get("link") for item in res_comp.get("items", [])])
        except Exception as e:
            click.echo(f"Warning: Comprehensive search failed: {e}")
            logging.exception("Comprehensive search failed with secondary CSE", exc_info=e)
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

    # Set system prompt based on comprehensive flag
    base_system = PROMPTS.get("base.australian_law")
    if comprehensive:
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
        system_content = f"{base_system} {standard_instructions}"

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
            click.echo("⚠️  Citation verification issues detected")
            # The error contains the citations that failed - we can still proceed with warnings
            raise click.ClickException(f"LLM error during lookup: {e}")
        else:
            raise click.ClickException(f"LLM error during lookup: {e}")

    # Apply formatting based on extract option
    formatted_content = format_lookup_output(content, extract)

    # Save output using utility
    command_name = f"lookup_{extract}" if extract else "lookup"
    metadata = {"Mode": mode}
    if context:
        metadata["Context"] = context
    if extract:
        metadata["Extract"] = extract
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
    click.echo("\n✅ Lookup complete!")
    click.echo(f'📄 Output saved to: "{output_file}"')

    # Show what was found
    if extract:
        extract_type = extract.capitalize()
        click.echo(f"\n📊 {extract_type} extracted from search results")
    else:
        analysis_type = "Exhaustive" if comprehensive else "Standard"
        click.echo(f"\n📊 {analysis_type} legal analysis for: {question}")

    # Show context if provided
    if context:
        click.echo(f"ℹ️  Context: '{context}'")

    # Show links that were searched
    if comprehensive:
        click.echo(f"\n🔍 Exhaustive search: {len(links)} sources analyzed")
    else:
        click.echo(f"\n🔍 Standard search: {len(links)} sources analyzed")

    for i, link in enumerate(links, 1):
        click.echo(f"   {i}. {link}")

    click.echo(f'\n💡 View full analysis: open "{output_file}"')
