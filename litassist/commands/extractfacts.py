"""
Auto-generate case_facts.txt under ten structured headings.

This module implements the 'extractfacts' command which processes a document
to extract relevant case facts and organizes them into a structured format
with ten standard headings.
"""

import click
import os
import time

from litassist.config import CONFIG
from litassist.utils import (
    read_document,
    chunk_text,
    save_log,
    timed,
    create_reasoning_prompt,
    extract_reasoning_trace,
    save_reasoning_trace,
    save_command_output,
    show_command_completion,
    verify_content_if_needed,
    validate_file_size,
)
from litassist.llm import LLMClientFactory


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--verify", is_flag=True, help="Enable self-critique pass (default: auto-enabled)"
)
@timed
def extractfacts(file, verify):
    """
    Auto-generate case_facts.txt under ten structured headings.

    Processes a document to extract relevant case facts and organizes them
    into a structured format with ten standard headings. This provides a
    foundation for other commands like 'brainstorm' and 'strategy' which require structured facts.

    Args:
        file: Path to the document (PDF or text) to extract facts from.
        verify: Whether to run a self-critique verification pass on the extracted facts.

    Raises:
        click.ClickException: If there are errors reading the file, processing chunks,
                             or with the LLM API calls.
    """
    # Read and validate document, then chunk
    text = validate_file_size(file, max_size=50000, file_type="source")
    chunks = chunk_text(text, max_chars=CONFIG.max_chars)

    # Initialize the LLM client using factory
    client = LLMClientFactory.for_command("extractfacts")

    # extractfacts always needs verification as it creates foundational documents
    if verify:
        click.echo(
            "⚠️  Note: --verify flag ignored - extractfacts command always uses verification for accuracy"
        )
    elif not verify:
        click.echo(
            "ℹ️  Note: Extractfacts command automatically uses verification for accuracy"
        )
    verify = True  # Force verification for critical accuracy

    # For single chunk, use original approach
    if len(chunks) == 1:
        base_prompt = (
            "Extract under these headings (include all relevant details):\n"
            "1. Parties (include roles and relationships)\n"
            "2. Background (include commercial/policy context if relevant)\n"
            "3. Key Events (in chronological order)\n"
            "4. Legal Issues\n"
            "5. Evidence Available (prioritize key evidence)\n"
            "6. Opposing Arguments (include known weaknesses/gaps)\n"
            "7. Procedural History (current status and past proceedings)\n"
            "8. Jurisdiction (include specific court/forum)\n"
            "9. Applicable Law\n"
            "10. Client Objectives (include any constraints/limitations)\n\n"
            + chunks[0]
        )

        # Add reasoning trace to prompt
        prompt = create_reasoning_prompt(base_prompt, "extractfacts")
        try:
            combined, usage = client.complete(
                [
                    {
                        "role": "system",
                        "content": "Australian law only. Extract factual information precisely under the requested headings. Focus on being comprehensive, accurate, and well-organized. Use clear paragraph structure and bullet points where appropriate. Maintain a neutral, factual tone throughout. Ensure all extracted information follows Australian legal terminology and conventions.",
                    },
                    {"role": "user", "content": prompt},
                ]
            )
        except Exception as e:
            raise click.ClickException(f"Error extracting facts: {e}")

    else:
        # For multiple chunks, accumulate facts then organize
        accumulated_facts = []

        # First, extract relevant facts from each chunk
        with click.progressbar(chunks, label="Processing document chunks") as bar:
            for idx, chunk in enumerate(bar, 1):
                prompt = f"""From this excerpt (part {idx} of {len(chunks)}), extract any facts relevant to:
- Parties involved
- Background/context
- Key events with dates
- Legal issues raised
- Evidence mentioned
- Arguments made
- Procedural matters
- Jurisdictional details
- Applicable laws
- Client objectives

Just extract the raw facts found in this excerpt:

{chunk}"""

                try:
                    content, usage = client.complete(
                        [
                            {
                                "role": "system",
                                "content": "Extract facts from this document excerpt. Be comprehensive but only include information actually present in this excerpt.",
                            },
                            {"role": "user", "content": prompt},
                        ]
                    )
                except Exception as e:
                    raise click.ClickException(f"Error processing chunk {idx}: {e}")
                accumulated_facts.append(content.strip())

        # Now organize all accumulated facts into the required structure
        all_facts = "\n\n".join(accumulated_facts)
        base_organize_prompt = f"""Organize the following extracted facts into these 10 headings:

1. **Parties**: Identify all parties involved in the matter, including their roles and relevant characteristics
2. **Background**: Provide context about the relationship between parties and circumstances leading to the dispute
3. **Key Events**: List significant events in chronological order with dates where available
4. **Legal Issues**: Enumerate the legal questions that need to be addressed
5. **Evidence Available**: Catalog all available evidence, documents, and potential witnesses
6. **Opposing Arguments**: Summarize the other party's position and claims
7. **Procedural History**: Detail any court proceedings, orders, or legal steps taken to date
8. **Jurisdiction**: Specify the relevant court or tribunal and basis for jurisdiction
9. **Applicable Law**: List relevant statutes, regulations, and legal principles
10. **Client Objectives**: State what the client hopes to achieve

Raw facts to organize:
{all_facts}

Important: 
- Only include information that was actually in the document
- If information for a heading is not available, write "Not specified in the document"
- Maintain chronological order for events
- Be comprehensive but factual"""

        # Add reasoning trace to organize prompt
        organize_prompt = create_reasoning_prompt(base_organize_prompt, "extractfacts")

        try:
            combined, usage = client.complete(
                [
                    {
                        "role": "system",
                        "content": "Australian law only. Organize the extracted facts precisely under the requested headings. Ensure consistency and avoid duplication.",
                    },
                    {"role": "user", "content": organize_prompt},
                ]
            )
        except Exception as e:
            raise click.ClickException(f"Error organizing facts: {e}")

    # Note: Citation verification now handled automatically in LLMClient.complete()

    # Apply verification (always required for extractfacts)
    combined, _ = verify_content_if_needed(client, combined, "extractfacts", verify_flag=True)

    # Extract reasoning trace before saving
    reasoning_trace = extract_reasoning_trace(combined, "extractfacts")

    # Save output using utility
    output_file = save_command_output(
        "extractfacts",
        combined,
        os.path.basename(file),
        metadata={"Source File": file}
    )

    # Audit log
    save_log(
        "extractfacts",
        {
            "inputs": {"source_file": file, "chunks": len(chunks)},
            "params": "verify=True (auto-enabled)",
            "response": combined,
            "output_file": output_file,
        },
    )

    # Save reasoning trace if extracted
    extra_files = {}
    if reasoning_trace:
        reasoning_file = save_reasoning_trace(reasoning_trace, output_file)
        extra_files["Reasoning trace"] = reasoning_file

    # Show completion
    chunk_desc = f"{len(chunks)} chunks" if len(chunks) > 1 else "single document" 
    stats = {
        "Source": os.path.basename(file),
        "Processed": chunk_desc,
        "Structure": "10 structured headings",
        "Verification": "Legal accuracy review applied"
    }
    
    show_command_completion("extractfacts", output_file, extra_files, stats)
    click.echo("📌 To use with other commands, manually copy to case_facts.txt")
