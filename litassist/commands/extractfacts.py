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
    save_command_output,
    show_command_completion,
    warning_message,
    info_message,
    verifying_message,
    validate_file_size,
)
from litassist.llm import LLMClientFactory


@click.command()
@click.argument("file", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--verify", is_flag=True, help="Enable self-critique pass (default: auto-enabled)"
)
@timed
def extractfacts(file, verify):
    """
    Auto-generate case_facts.txt under ten structured headings.

    Processes one or more documents to extract relevant case facts and organizes them
    into a structured format with ten standard headings. This provides a
    foundation for other commands like 'brainstorm' and 'strategy' which require structured facts.

    Args:
        file: Path(s) to the document(s) (PDF or text) to extract facts from.
        verify: Whether to run a self-critique verification pass on the extracted facts.

    Raises:
        click.ClickException: If there are errors reading the file, processing chunks,
                             or with the LLM API calls.
    """
    # Process all files
    all_text = ""
    source_files = []
    for f in file:
        text = validate_file_size(f, max_size=3000000, file_type="source")
        source_files.append(os.path.basename(f))
        all_text += f"\n\n--- SOURCE: {os.path.basename(f)} ---\n\n{text}"

    # Use existing chunking on combined text
    chunks = chunk_text(all_text, max_chars=CONFIG.max_chars)

    # Initialize the LLM client using factory
    client = LLMClientFactory.for_command("extractfacts")

    # extractfacts always needs verification as it creates foundational documents
    if verify:
        click.echo(
            warning_message(
                "Note: --verify flag ignored - extractfacts command always uses verification for accuracy"
            )
        )
    elif not verify:
        click.echo(
            info_message(
                "Note: Extractfacts command automatically uses verification for accuracy"
            )
        )
    verify = True  # Force verification for critical accuracy

    # Process content based on chunking needs (now most documents will be single chunk)
    if len(chunks) == 1:
        # Single chunk - unified extraction approach
        # Use centralized format template
        format_instructions = PROMPTS.get_format_template("case_facts_10_heading")
        base_prompt = f"Extract under these headings (include all relevant details):\n{format_instructions}\n\n{chunks[0]}"

        # Add reasoning trace to prompt
        prompt = create_reasoning_prompt(base_prompt, "extractfacts")
        try:
            combined, usage = client.complete(
                [
                    {
                        "role": "system",
                        "content": PROMPTS.get_system_prompt("extractfacts"),
                    },
                    {"role": "user", "content": prompt},
                ]
            )
        except Exception as e:
            raise click.ClickException(f"Error extracting facts: {e}")

    else:
        # Multiple chunks - enhanced two-stage approach with better context preservation
        click.echo(
            info_message(
                "Processing large document in sections for comprehensive fact extraction..."
            )
        )
        accumulated_facts = []

        # First, extract relevant facts from each chunk
        with click.progressbar(chunks, label="Extracting facts from sections") as bar:
            for idx, chunk in enumerate(bar, 1):
                chunk_template = PROMPTS.get("processing.extraction.chunk_facts_prompt")
                prompt = f"{chunk_template.format(chunk_num=idx, total_chunks=len(chunks))}\n\n{chunk}"

                try:
                    content, usage = client.complete(
                        [
                            {
                                "role": "system",
                                "content": PROMPTS.get(
                                    "processing.extraction.chunk_system_prompt"
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ]
                    )
                except Exception as e:
                    raise click.ClickException(f"Error processing chunk {idx}: {e}")
                accumulated_facts.append(content.strip())

        # Enhanced organization phase with better synthesis
        click.echo(
            info_message("Organizing and synthesizing facts into structured format...")
        )
        all_facts = "\n\n".join(accumulated_facts)

        # Use centralized format template for organizing
        format_instructions = PROMPTS.get_format_template("case_facts_10_heading")
        organize_template = PROMPTS.get("processing.extraction.organize_facts_prompt")
        base_organize_prompt = organize_template.format(
            format_instructions=format_instructions, all_facts=all_facts
        )

        # Add reasoning trace to organize prompt
        organize_prompt = create_reasoning_prompt(base_organize_prompt, "extractfacts")

        try:
            combined, usage = client.complete(
                [
                    {
                        "role": "system",
                        "content": PROMPTS.get_system_prompt("extractfacts"),
                    },
                    {"role": "user", "content": organize_prompt},
                ]
            )
        except Exception as e:
            raise click.ClickException(f"Error organizing facts: {e}")

    # Note: Citation verification now handled automatically in LLMClient.complete()

    # Apply verification (always required for extractfacts)
    click.echo(verifying_message("Verifying extracted facts..."))
    try:
        correction = client.verify(combined)
        if correction.strip() and not correction.lower().startswith(
            "no corrections needed"
        ):
            # Replace content to preserve structure and reasoning trace
            combined = correction
    except Exception as e:
        raise click.ClickException(f"Verification error during extractfacts: {e}")

    # Save output using utility (reasoning trace remains inline)
    slug = "_".join(source_files[:3])  # Use first 3 files for slug
    if len(source_files) > 3:
        slug += f"_and_{len(source_files)-3}_more"
    output_file = save_command_output(
        "extractfacts",
        combined,
        slug,
        metadata={"Source Files": ", ".join(source_files)},
    )

    # Audit log
    save_log(
        "extractfacts",
        {
            "inputs": {"source_files": list(file), "chunks": len(chunks)},
            "params": "verify=True (auto-enabled)",
            "response": combined,
            "output_file": output_file,
        },
    )

    # Show completion
    chunk_desc = f"{len(chunks)} chunks" if len(chunks) > 1 else "single document"
    source_desc = ", ".join(source_files[:3])
    if len(source_files) > 3:
        source_desc += f" + {len(source_files)-3} more"
    stats = {
        "Sources": (
            f"{len(source_files)} files" if len(source_files) > 1 else source_files[0]
        ),
        "Processed": chunk_desc,
        "Structure": "10 structured headings",
        "Verification": "Legal accuracy review applied",
    }

    show_command_completion("extractfacts", output_file, None, stats)
    click.echo(
        info_message("To use with other commands, manually copy to case_facts.txt")
    )
