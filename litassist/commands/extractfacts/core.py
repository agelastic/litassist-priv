"""
Main CLI orchestration for extractfacts command.

Auto-generates case_facts.txt under ten structured headings by processing
documents and organizing facts using single-chunk or multi-chunk extraction.
"""

import click

from litassist.utils.core import (
    timed,
    show_command_completion,
)
from litassist.utils.legal_reasoning import verify_content_if_needed
from litassist.utils.formatting import info_message
from litassist.logging import (
    save_log,
    save_command_output,
    log_task_event,
)
from litassist.llm.factory import LLMClientFactory

from .document_reader import read_and_combine_files
from .single_extractor import extract_single_chunk
from .multi_extractor import extract_multi_chunk


@click.command()
@click.argument("file", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--verify", is_flag=True, help="Enable self-critique pass (default: auto-enabled)"
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Skip standard verification",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def extractfacts(file, verify, noverify, output):
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
    # Command start log
    try:
        log_task_event(
            "extractfacts",
            "init",
            "start",
            "Starting fact extraction",
            {"model": LLMClientFactory.get_model_for_command("extractfacts")},
        )
    except Exception:
        pass

    # Read and combine all files
    all_text, source_files, chunks = read_and_combine_files(file)

    # Initialize the LLM client using factory
    client = LLMClientFactory.for_command("extractfacts")

    try:
        log_task_event(
            "extractfacts",
            "reading",
            "end",
            f"Read {len(file)} document(s)"
        )
    except Exception:
        pass

    # Process content based on chunking needs (now most documents will be single chunk)
    if len(chunks) == 1:
        combined, usage = extract_single_chunk(client, chunks[0])
    else:
        combined, usage = extract_multi_chunk(client, chunks)

    # Note: Citation verification now handled automatically in LLMClient.complete()

    # Apply standard verification (CoVe moved to standalone 'verify-cove' command)
    verification_metadata = {"Source Files": ", ".join(source_files)}
    if not noverify:
        try:
            log_task_event(
                "extractfacts",
                "verification",
                "start",
                "Starting verification"
            )
        except Exception:
            pass

        combined, _ = verify_content_if_needed(
            client, combined, "extractfacts", verify_flag=True
        )
        verification_metadata["Verification"] = "Standard verification"
        verification_metadata["Model"] = client.model
        click.echo(info_message("Standard verification applied"))

        try:
            log_task_event(
                "extractfacts",
                "verification",
                "end",
                "Verification complete"
            )
        except Exception:
            pass
    else:
        verification_metadata["Verification"] = "Disabled"
        verification_metadata["Model"] = "N/A"
        click.echo(info_message("Standard verification skipped by --noverify flag"))

    # Save output using utility (reasoning trace remains inline)
    slug = "_".join(source_files[:3])  # Use first 3 files for slug
    if len(source_files) > 3:
        slug += f"_and_{len(source_files) - 3}_more"
    output_file = save_command_output(
        output if output else "extractfacts",
        combined,
        "" if output else slug,
        metadata=verification_metadata,
    )

    # Audit log (without response content)
    save_log(
        "extractfacts",
        {
            "inputs": {"source_files": list(file), "chunks": len(chunks)},
            "params": "verify=True (auto-enabled)",
            # Response content removed - already logged by LLMClient separately
            "output_file": output_file,
        },
    )

    # Show completion
    chunk_desc = f"{len(chunks)} chunks" if len(chunks) > 1 else "single document"
    source_desc = ", ".join(source_files[:3])
    if len(source_files) > 3:
        source_desc += f" + {len(source_files) - 3} more"
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

    # Command end log
    try:
        log_task_event(
            "extractfacts",
            "init",
            "end",
            "Fact extraction complete"
        )
    except Exception:
        pass
