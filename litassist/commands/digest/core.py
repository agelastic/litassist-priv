"""
Core digest command implementation.

This module contains the main digest function that orchestrates
document processing using the chunker, processors, and emergency handler.
"""

import click
from litassist.logging import save_log, save_command_output, log_task_event
from litassist.timing import timed
from litassist.utils.core import show_command_completion
from litassist.utils.formatting import info_message, warning_message
from litassist.llm.factory import LLMClientFactory
from litassist.llm.api_handlers import NonRetryableAPIError
from litassist.prompts import PROMPTS

from .chunker import (
    determine_chunk_size,
    warn_if_reduced_chunk_size,
    calculate_total_document_size,
    warn_if_large_processing,
    prepare_chunks_for_processing,
)
from .processors import (
    process_single_chunk,
    process_multiple_chunks,
    consolidate_chunk_outputs,
    validate_citations_if_needed,
)
from .emergency_handler import create_emergency_handler


@click.command()
@click.argument("file", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["summary", "issues"]), default="summary")
@click.option(
    "--context",
    type=str,
    default=None,
    help="Additional context to guide the analysis.",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.option(
    "--verify",
    is_flag=True,
    help="Not supported - digest summaries are not verified. Use 'litassist verify' command for verification.",
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Not supported - digest has no internal verification.",
)
@click.pass_context
@timed
def digest(ctx, file, mode, context, output, verify, noverify):
    """
    Mass-document digestion via Claude.

    Processes one or more documents by splitting them into manageable chunks
    and using Claude to either summarize content chronologically or
    identify potential legal issues in each section.

    Note: Verification removed as this is low-stakes content summarization.

    Args:
        file: Path(s) to document(s) (PDF or text) to analyze. Accepts multiple files.
        mode: Type of analysis to perform - 'summary' for chronological summaries
              or 'issues' to identify potential legal problems.

    Raises:
        click.ClickException: If there are errors with file reading, processing,
                             or LLM API calls.
    """
    # Handle unsupported verification flags
    if verify:
        click.echo(
            warning_message(
                "--verify not supported: This command has no internal verification. Use 'litassist verify' for post-processing verification."
            )
        )
    if noverify:
        click.echo(
            warning_message(
                "--noverify not supported: This command has no verification to skip."
            )
        )

    # Process all files
    all_documents_output = []
    all_chunk_errors = []  # Track errors across all files

    # Emergency save functionality
    emergency_handler = create_emergency_handler()
    emergency_handler.setup(
        metadata={"mode": mode, "context": context, "files": list(file)},
        output_prefix=output or f"digest_{mode}",
    )

    # Create client using factory with mode-specific configuration
    llm_client = LLMClientFactory.for_command("digest", mode)
    
    # Command start log
    try:
        log_task_event(
            "digest",
            "init",
            "start",
            "Starting digest command",
            {"mode": mode, "files": len(file), "model": llm_client.model}
        )
    except Exception:
        pass

    # Determine chunk size based on model
    model_family = (
        llm_client.model.split("/")[0] if "/" in llm_client.model else "openai"
    )
    model_chunk_limit = determine_chunk_size(model_family)

    # Warn user if using reduced chunk size
    warn_if_reduced_chunk_size(model_family, model_chunk_limit)

    # Collect comprehensive log data for all files
    all_usage = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
        "files_processed": 0,
        "chunks_processed": 0,
        "errors": [],
    }

    # Calculate total size and warn if large
    total_size, total_chars = calculate_total_document_size(list(file))
    warn_if_large_processing(total_chars)

    # Process each file
    for file_path in file:
        click.echo(f"\nProcessing: {file_path}")
        
        try:
            log_task_event(
                "digest",
                "file_processing",
                "start",
                f"Processing file: {file_path}"
            )
        except Exception:
            pass

        # Update metadata for emergency save
        emergency_handler.update_metadata("current_file", file_path)

        # Read and split the document
        try:
            content, chunks, chunk_count = prepare_chunks_for_processing(
                file_path, model_chunk_limit, mode
            )
            
            try:
                log_task_event(
                    "digest",
                    "file_processing",
                    "chunked",
                    f"Document chunked: {len(chunks)} chunks"
                )
            except Exception:
                pass
        except Exception as e:
            error_msg = f"Failed to read {file_path}: {str(e)}"
            click.echo(click.style(error_msg, fg="red"))
            all_chunk_errors.append(error_msg)
            continue

        # Collect output for this file
        file_output = f"\n{'=' * 80}\nFILE: {file_path}\n{'=' * 80}\n"

        # Process content based on chunking needs
        if len(chunks) == 1:
            # Single chunk - process normally with unified analysis
            click.echo("  Processing as single document...")

            try:
                log_task_event(
                    "digest",
                    "single_chunk",
                    "start",
                    "Processing single chunk"
                )
            except Exception:
                pass

            try:
                response, usage = process_single_chunk(
                    content, mode, context, llm_client, file_path
                )

                # Citation validation for issues mode
                if mode == "issues":
                    response, _ = validate_citations_if_needed(
                        response, mode, llm_client
                    )

                file_output += response

                # Collect data for comprehensive log
                all_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
                all_usage["completion_tokens"] += usage.get("completion_tokens", 0)
                all_usage["total_tokens"] += usage.get("total_tokens", 0)
                all_usage["chunks_processed"] += 1
                
                try:
                    log_task_event(
                        "digest",
                        "single_chunk",
                        "end",
                        "Single chunk processing complete"
                    )
                except Exception:
                    pass

            except NonRetryableAPIError as e:
                error_msg = f"[ERROR] Failed to process {file_path}: {str(e)}"
                click.echo(click.style(error_msg, fg="red"))
                file_output += f"\n[PROCESSING FAILED]\nError: {str(e)}\n"
                all_chunk_errors.append(error_msg)

        else:
            # Multiple chunks - process each chunk
            try:
                log_task_event(
                    "digest",
                    "multi_chunk",
                    "start",
                    f"Processing {len(chunks)} chunks"
                )
            except Exception:
                pass
            
            chunk_outputs, prompt_tokens, completion_tokens, chunk_errors = (
                process_multiple_chunks(chunks, mode, context, llm_client, file_path)
            )

            # Add chunk errors to global error list
            all_chunk_errors.extend(chunk_errors)

            # Accumulate usage statistics
            all_usage["prompt_tokens"] += prompt_tokens
            all_usage["completion_tokens"] += completion_tokens
            all_usage["total_tokens"] += prompt_tokens + completion_tokens
            all_usage["chunks_processed"] += len(chunks)
            
            try:
                log_task_event(
                    "digest",
                    "multi_chunk",
                    "end",
                    f"Multi-chunk processing complete - {len(chunks)} chunks"
                )
            except Exception:
                pass

            # Consolidate chunks if possible
            if chunk_outputs and len(chunk_errors) < len(chunks):
                try:
                    click.echo("  Consolidating chunk results...")
                    
                    try:
                        log_task_event(
                            "digest",
                            "consolidation",
                            "start",
                            f"Consolidating {len(chunk_outputs)} chunk outputs"
                        )
                    except Exception:
                        pass
                    
                    consolidated, consolidation_usage = consolidate_chunk_outputs(
                        chunk_outputs, mode, llm_client, context
                    )

                    # Citation validation for consolidated issues
                    if mode == "issues":
                        consolidated, _ = validate_citations_if_needed(
                            consolidated, mode, llm_client
                        )

                    file_output += consolidated

                    # Add consolidation usage
                    all_usage["prompt_tokens"] += consolidation_usage.get(
                        "prompt_tokens", 0
                    )
                    all_usage["completion_tokens"] += consolidation_usage.get(
                        "completion_tokens", 0
                    )
                    all_usage["total_tokens"] += consolidation_usage.get(
                        "total_tokens", 0
                    )
                    
                    try:
                        log_task_event(
                            "digest",
                            "consolidation",
                            "end",
                            "Consolidation complete"
                        )
                    except Exception:
                        pass

                except Exception as e:
                    # Fall back to raw chunks if consolidation fails
                    click.echo(
                        click.style(f"Consolidation failed: {str(e)}", fg="yellow")
                    )
                    file_output += "\n".join(chunk_outputs)
            else:
                # Too many errors or no outputs - just use what we have
                file_output += (
                    "\n".join(chunk_outputs)
                    if chunk_outputs
                    else "[No output generated]"
                )

        all_documents_output.append(file_output)
        all_usage["files_processed"] += 1

        # Update emergency save with current progress
        emergency_handler.update_output(file_output)
        
        try:
            log_task_event(
                "digest",
                "file_processing",
                "end",
                f"File processing complete: {file_path}"
            )
        except Exception:
            pass

    # Combine all file outputs
    final_output = "\n".join(all_documents_output)

    # Add cross-file consolidation if multiple files
    if len(file) > 1:
        click.echo(info_message("Consolidating across all files..."))
        
        try:
            log_task_event(
                "digest",
                "cross_file",
                "start",
                f"Starting cross-file consolidation for {len(file)} files"
            )
        except Exception:
            pass
        
        try:
            # Build consolidation prompt using mode-specific template
            # Comment: Using f-string to avoid if/elif blocks for mode selection
            prompt_key = f"processing.digest.consolidation_cross_file_{mode}"
            consolidation_prompt = PROMPTS.get(
                prompt_key,
                file_count=len(file),
                file_digests="\n\n".join(all_documents_output),
            )

            # Make consolidation call
            messages = [
                {
                    "role": "system",
                    "content": PROMPTS.get("processing.digest.system_prompt"),
                },
                {"role": "user", "content": consolidation_prompt},
            ]
            cross_file_summary, usage = llm_client.complete(messages)

            # Append to output
            final_output += f"\n\n{'=' * 80}\nCROSS-FILE CONSOLIDATION\n{'=' * 80}\n{cross_file_summary}"

            # Update usage stats
            all_usage["prompt_tokens"] += usage.get("prompt_tokens", 0)
            all_usage["completion_tokens"] += usage.get("completion_tokens", 0)
            all_usage["total_tokens"] += usage.get("total_tokens", 0)
            
            try:
                log_task_event(
                    "digest",
                    "cross_file",
                    "end",
                    "Cross-file consolidation complete"
                )
            except Exception:
                pass
        except Exception as e:
            click.echo(warning_message(f"Cross-file consolidation skipped: {str(e)}"))

    # Add error summary if there were chunk failures
    if all_chunk_errors:
        error_summary = f"\n{'=' * 80}\nERRORS ENCOUNTERED\n{'=' * 80}\n"
        error_summary += "\n".join(all_chunk_errors)
        final_output += error_summary
        all_usage["errors"] = all_chunk_errors

    # Save the final output
    output_file = save_command_output(
        output or f"digest_{mode}",
        final_output,
        context or "",
        metadata={
            "mode": mode,
            "files": list(file),
            "context": context,
            "total_chunks": all_usage["chunks_processed"],
            "errors": len(all_chunk_errors),
        },
    )

    # Save comprehensive log
    log_content = {
        "command": "digest",
        "mode": mode,
        "files": list(file),
        "context": context or f"{mode} analysis",
        "usage": all_usage,
        "output_file": output_file,
        "output": final_output,
        "errors": all_chunk_errors,
    }
    save_log("digest", log_content)

    # Disable emergency save since we completed successfully
    emergency_handler.disable()

    # Show completion message
    show_command_completion(
        command_name=f"digest_{mode}",
        output_file=output_file,
        stats={
            "Files processed": all_usage["files_processed"],
            "Total chunks": all_usage["chunks_processed"],
            "Total tokens": f"{all_usage['total_tokens']:,}",
            "Errors": len(all_chunk_errors),
        },
        ctx=ctx,
    )

    # Command end log
    try:
        log_task_event(
            "digest",
            "init",
            "end",
            f"Digest command complete - {all_usage['files_processed']} files, {all_usage['chunks_processed']} chunks"
        )
    except Exception:
        pass
    
    return final_output, all_usage
