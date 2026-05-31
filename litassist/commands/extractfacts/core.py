"""
Main CLI orchestration for extractfacts command.

Produces structured 10-heading case facts (saved as outputs/extractfacts_*.txt) by
processing documents and organizing facts using single-chunk or multi-chunk
extraction. The usual next step is the 'updatefacts' command, which folds this
output into a downstream-ready case_facts file.
"""

import click

from litassist.timing import timed
from litassist.utils.core import (
    show_command_completion,
)
from litassist.utils.legal_reasoning import verify_content_if_needed
from litassist.utils.formatting import info_message, warning_message
from litassist.utils.case_facts import validate_case_facts_format
from litassist.utils.file_ops import expand_glob_patterns_callback as expand_glob_patterns
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
@click.argument(
    "file", nargs=-1, required=True, type=click.Path(), callback=expand_glob_patterns
)
@click.option(
    "--heavy",
    is_flag=True,
    help="Use verification-heavy mode (max thinking effort)",
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Skip verification stage (not recommended for legal work)",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def extractfacts(file, heavy, noverify, output):
    """
    Produce structured 10-heading case facts from one or more documents.

    Extracts relevant facts and organizes them under the ten standard headings,
    saving the result as outputs/extractfacts_*.txt. The usual next step is
    'updatefacts' to fold this into a downstream-ready case_facts file for
    commands like 'brainstorm', 'strategy', and 'barbrief'.

    Args:
        file: Path(s) to the document(s) (PDF or text) to extract facts from.

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

    # Read and combine all files (combined_text is unused here; chunks drive extraction)
    _, source_files, chunks = read_and_combine_files(file)

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

    # Process content based on chunking needs (now most documents will be single chunk).
    # Per-call token usage/cost is logged inside LLMClient.complete(), so the usage
    # returned here is intentionally discarded.
    if len(chunks) == 1:
        combined, _ = extract_single_chunk(client, chunks[0])
    else:
        combined, _ = extract_multi_chunk(client, chunks)

    # Note: Citation verification now handled automatically in LLMClient.complete()

    # Prepare slug and warn if conflicting flags
    slug = "_".join(source_files[:3])  # Use first 3 files for slug
    if len(source_files) > 3:
        slug += f"_and_{len(source_files) - 3}_more"

    # Warn if both --noverify and --heavy are specified
    if noverify and heavy:
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

        combined, corrections_made = verify_content_if_needed(
            client, combined, "extractfacts", verify_flag=True, heavy=heavy
        )
        base_mode = "verification-heavy (max thinking effort)" if heavy else "Standard verification"
        # Reflect whether the verifier actually changed anything. (A short-circuit
        # is announced separately by run_verification_chain.)
        verification_mode = (
            f"{base_mode} (corrections applied)"
            if corrections_made
            else f"{base_mode} (no corrections)"
        )
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

    # Producer-side check: warn (but still save) if the extracted facts are
    # missing any of the ten required headings, so the user can fix them before
    # feeding the file to downstream commands that reject the wrong shape.
    if not validate_case_facts_format(combined):
        click.echo(
            warning_message(
                "Extracted facts are missing one or more required headings (see "
                "above). Saving anyway - review before using downstream."
            )
        )

    # Save final output using utility (reasoning trace remains inline)
    output_file = save_command_output(
        output if output else "extractfacts",
        combined,
        "" if output else slug,
        metadata=final_metadata,
    )

    # Audit log (without response content)
    # Build params based on flags
    if noverify:
        params_str = "noverify=True"
    elif heavy:
        params_str = "verify=True (auto-enabled), heavy=True"
    else:
        params_str = "verify=True (auto-enabled)"

    save_log(
        "extractfacts",
        {
            "inputs": {"source_files": list(file), "chunks": len(chunks)},
            "params": params_str,
            # Response content removed - already logged by LLMClient separately
            "output_file": output_file,
        },
    )

    # Show completion
    chunk_desc = f"{len(chunks)} chunks" if len(chunks) > 1 else "single document"
    source_desc = ", ".join(source_files[:3])
    if len(source_files) > 3:
        source_desc += f" + {len(source_files) - 3} more"
    # Use verification status from metadata (set in the verification block above)
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
        info_message(
            f"Next step: run 'litassist updatefacts {output_file}' to fold this "
            "into a case_facts file that brainstorm/strategy/draft/barbrief pick "
            "up automatically."
        )
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
