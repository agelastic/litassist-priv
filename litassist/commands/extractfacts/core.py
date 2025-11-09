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
    "--heavy",
    is_flag=True,
    help="Use verification-heavy mode (gpt-5-pro instead of gpt-5)",
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Skip verification stage (not recommended for legal work)",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def extractfacts(file, verify, heavy, noverify, output):
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

    # Prepare slug and warn if conflicting flags
    slug = "_".join(source_files[:3])  # Use first 3 files for slug
    if len(source_files) > 3:
        slug += f"_and_{len(source_files) - 3}_more"

    # Warn if both --noverify and --heavy are specified
    if noverify and heavy:
        from litassist.utils.formatting import warning_message
        click.echo(warning_message("--heavy flag ignored when --noverify is specified"))

    if noverify:
        click.echo(info_message("Standard verification skipped"))

    # Prepare metadata
    final_metadata = {"Source Files": ", ".join(source_files)}

    if not noverify:
        # Save raw pre-verification output for audit trail
        raw_metadata = {
            "Source Files": ", ".join(source_files),
            "Verification": "Not yet applied (raw output)",
        }
        save_command_output(
            output if output else "extractfacts",
            combined,
            "" if output else slug,
            metadata=raw_metadata,
            suffix="_raw",
        )

        # Apply standard verification (CoVe moved to standalone 'verify-cove' command)
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
            client, combined, "extractfacts", verify_flag=True, heavy=heavy
        )
        verification_mode = "verification-heavy (gpt-5-pro)" if heavy else "Standard verification"
        final_metadata["Verification"] = verification_mode
        final_metadata["Model"] = client.model
        click.echo(info_message(f"{verification_mode} applied"))

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
        # No verification
        final_metadata["Verification"] = "Skipped (--noverify)"
        final_metadata["Model"] = client.model

    # Save final output using utility (reasoning trace remains inline)
    output_file = save_command_output(
        output if output else "extractfacts",
        combined,
        "" if output else slug,
        metadata=final_metadata,
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
    # Use verification status from metadata (correctly set at lines 142 or 157)
    verification_status = final_metadata["Verification"]
    stats = {
        "Sources": (
            f"{len(source_files)} files" if len(source_files) > 1 else source_files[0]
        ),
        "Processed": chunk_desc,
        "Structure": "10 structured headings",
        "Verification": verification_status,
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
