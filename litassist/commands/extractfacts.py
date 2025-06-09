"""
Auto-generate case_facts.txt under ten structured headings.

This module implements the 'extractfacts' command which processes a document
to extract relevant case facts and organizes them into a structured format
with ten standard headings.
"""

import click
import os

from litassist.config import CONFIG
from litassist.prompts import PROMPTS
from litassist.utils import (
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
        # Use centralized format template
        format_instructions = PROMPTS.get_format_template('case_facts_10_heading')
        base_prompt = f"Extract under these headings (include all relevant details):\n{format_instructions}\n\n{chunks[0]}"

        # Add reasoning trace to prompt
        prompt = create_reasoning_prompt(base_prompt, "extractfacts")
        try:
            combined, usage = client.complete(
                [
                    {
                        "role": "system",
                        "content": PROMPTS.get_system_prompt('extractfacts'),
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
                chunk_template = PROMPTS.get('processing.extraction.chunk_facts_prompt')
                prompt = f"{chunk_template.format(chunk_num=idx, total_chunks=len(chunks))}\n\n{chunk}"

                try:
                    content, usage = client.complete(
                        [
                            {
                                "role": "system",
                                "content": PROMPTS.get('processing.extraction.chunk_system_prompt'),
                            },
                            {"role": "user", "content": prompt},
                        ]
                    )
                except Exception as e:
                    raise click.ClickException(f"Error processing chunk {idx}: {e}")
                accumulated_facts.append(content.strip())

        # Now organize all accumulated facts into the required structure
        all_facts = "\n\n".join(accumulated_facts)
        # Use centralized format template for organizing
        format_instructions = PROMPTS.get_format_template('case_facts_10_heading')
        organize_template = PROMPTS.get('processing.extraction.organize_facts_prompt')
        base_organize_prompt = organize_template.format(
            format_instructions=format_instructions,
            all_facts=all_facts
        )

        # Add reasoning trace to organize prompt
        organize_prompt = create_reasoning_prompt(base_organize_prompt, "extractfacts")

        try:
            combined, usage = client.complete(
                [
                    {
                        "role": "system",
                        "content": PROMPTS.get_system_prompt('extractfacts'),
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
