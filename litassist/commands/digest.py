"""
Mass-document digestion via Claude.

This module implements the 'digest' command which processes large documents by splitting
them into manageable chunks and using Claude to either summarize content chronologically
or identify potential legal issues in each section.
"""

import click
import os
import sys
import atexit
import signal

from litassist.config import CONFIG
from litassist.prompts import PROMPTS
from litassist.utils import (
    read_document,
    chunk_text,
    save_log,
    timed,
    save_command_output,
    show_command_completion,
    saved_message, info_message, warning_message, error_message, success_message,
)
from litassist.llm import LLMClientFactory, NonRetryableAPIError


@click.command()
@click.argument("file", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["summary", "issues"]), default="summary")
@click.option(
    "--context",
    type=str,
    default=None,
    help="Additional context to guide the analysis.",
)
@timed
def digest(file, mode, context):
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
    # Process all files
    all_documents_output = []
    source_files = []
    all_chunk_errors = []  # Track errors across all files
    
    # Emergency save functionality
    partial_save_data = {
        'chunks': [],
        'metadata': {'mode': mode, 'context': context}
    }
    
    def emergency_save():
        """Save partial results on unexpected exit"""
        if partial_save_data['chunks']:
            try:
                content = "\n\n".join([
                    f"=== Partial Result {i+1} ===\n{chunk}" 
                    for i, chunk in enumerate(partial_save_data['chunks'])
                ])
                emergency_file = save_command_output(
                    f"digest_{mode}_partial",
                    content + "\n\n[INCOMPLETE - Process interrupted]",
                    "emergency_save",
                    metadata=partial_save_data['metadata']
                )
                click.echo(warning_message(f"\nPartial results saved to: {emergency_file}"))
            except Exception as e:
                # Use stderr for last-resort logging as stdout may be redirected
                print(f"\n[EMERGENCY SAVE FAILED] Could not save partial results: {e}", file=sys.stderr)
    
    # Register handlers for emergency save
    atexit.register(emergency_save)
    
    def signal_handler(signum, frame):
        emergency_save()
        sys.exit(1)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create client using factory with mode-specific configuration
    client = LLMClientFactory.for_command("digest", mode)
    
    # Model-aware chunk sizing
    MODEL_CHUNK_LIMITS = {
        "google": 30000,          # Conservative for Gemini
        "anthropic": 150000,      # Claude handles larger chunks
        "openai": 100000,         # GPT-4 limit
        "x-ai": 100000,           # Grok limit
    }
    
    # Determine appropriate chunk size
    model_family = client.model.split('/')[0] if '/' in client.model else 'openai'
    model_chunk_limit = MODEL_CHUNK_LIMITS.get(model_family, 100000)  # Default 100K for unknown models
    effective_chunk_size = min(CONFIG.max_chars, model_chunk_limit)
    
    # Warn user if using reduced chunk size
    if effective_chunk_size < CONFIG.max_chars:
        click.echo(info_message(
            f"Using reduced chunk size of {effective_chunk_size:,} characters "
            f"for {client.model} (configured: {CONFIG.max_chars:,})"
        ))
    
    # Collect comprehensive log data for all files
    comprehensive_log = {
        "files": list(file),
        "mode": mode,
        "total_chunks_processed": 0,
        "responses": [],
        "total_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    
    # Calculate total size and warn if large
    total_chars = 0
    for f in file:
        try:
            total_chars += len(read_document(f))
        except Exception:
            pass  # Skip files that can't be read
    
    if total_chars > 500000:
        click.echo(warning_message(
            f"Large input detected ({total_chars:,} characters). "
            "Processing will continue even if some chunks fail."
        ))
        click.echo(info_message("Partial results will be saved in case of errors."))
    
    # Process each file
    for file_path in file:
        msg = saved_message(f'Processing: {file_path}')
        click.echo(f"\n{msg}")
        source_files.append(os.path.basename(file_path))
        
        # Update metadata for emergency save
        partial_save_data['metadata']['Source Files'] = source_files
        
        # Read and split the document
        text = read_document(file_path)
        chunks = chunk_text(text, max_chars=effective_chunk_size)
        comprehensive_log["total_chunks_processed"] += len(chunks)
        
        # Collect output for this file
        file_output = []

        # Process content based on chunking needs
        if len(chunks) == 1:
            # Single chunk - process normally with unified analysis
            chunk = chunks[0]

            # Use centralized digest prompts for unified analysis
            if mode == "summary":
                if context:
                    context_instruction = PROMPTS.get(
                        "processing.digest.summary_mode_context_instruction_with_context",
                        context=context,
                    )
                else:
                    context_instruction = PROMPTS.get(
                        "processing.digest.summary_mode_context_instruction_no_context"
                    )
                digest_prompt = PROMPTS.get(
                    "processing.digest.summary_mode",
                    context_instruction=context_instruction,
                )
                prompt = f"{digest_prompt}\n\n{chunk}"
            else:  # issues mode
                if context:
                    context_instruction = PROMPTS.get(
                        "processing.digest.issues_mode_context_instruction_with_context",
                        context=context,
                    )
                else:
                    context_instruction = PROMPTS.get(
                        "processing.digest.issues_mode_context_instruction_no_context"
                    )
                digest_prompt = PROMPTS.get(
                    "processing.digest.issues_mode",
                    context_instruction=context_instruction,
                )
                prompt = f"{digest_prompt}\n\n{chunk}"

            # Call the LLM
            try:
                content, usage = client.complete(
                    [
                        {
                            "role": "system",
                            "content": PROMPTS.get("processing.digest.system_prompt"),
                        },
                        {"role": "user", "content": prompt},
                    ]
                )
            except Exception as e:
                raise click.ClickException(f"LLM error in digest for {file_path}: {e}")

            # Citation validation for issues mode
            if mode == "issues":  # Legal issues mode is more likely to contain citations
                citation_issues = client.validate_citations(content)
                if citation_issues:
                    citation_warning = "--- CITATION WARNINGS ---\n"
                    citation_warning += "\n".join(citation_issues)
                    citation_warning += "\n" + "-" * 40 + "\n\n"
                    content = citation_warning + content

            # Collect data for comprehensive log
            comprehensive_log["responses"].append(
                {"file": file_path, "chunk": 1, "content": content, "usage": usage}
            )

            # Accumulate usage statistics
            for key in comprehensive_log["total_usage"]:
                comprehensive_log["total_usage"][key] += usage.get(key, 0)

            file_output.append(content)

        else:
            # Multiple chunks - need consolidation approach
            chunk_analyses = []
            failed_chunks = []
            chunk_errors = []

            with click.progressbar(
                chunks, label=f"Analyzing sections of {os.path.basename(file_path)}"
            ) as chunks_bar:
                for idx, chunk in enumerate(chunks_bar, start=1):
                    # Use chunk-specific prompt for partial analysis
                    chunk_prompt = PROMPTS.get(
                        f"processing.digest.chunk_analysis_{mode}",
                        documents=chunk,
                        chunk_num=idx,
                        total_chunks=len(chunks),
                        context=context or "general analysis",
                    )

                    try:
                        content, usage = client.complete(
                            [
                                {
                                    "role": "system",
                                    "content": PROMPTS.get(
                                        "processing.digest.system_prompt"
                                    ),
                                },
                                {"role": "user", "content": chunk_prompt},
                            ]
                        )
                        chunk_analyses.append(content)
                        
                        # Update partial save data
                        partial_save_data['chunks'].append(f"File: {os.path.basename(file_path)}, Chunk {idx}\n{content}")

                        # Collect data for comprehensive log
                        comprehensive_log["responses"].append(
                            {"file": file_path, "chunk": idx, "content": content, "usage": usage}
                        )

                        # Accumulate usage statistics
                        for key in comprehensive_log["total_usage"]:
                            comprehensive_log["total_usage"][key] += usage.get(key, 0)
                    
                    except NonRetryableAPIError as e:
                        # Don't retry, but continue processing other chunks
                        click.echo(error_message(f"\nChunk {idx} too large: {e}"))
                        failed_chunks.append(idx)
                        chunk_errors.append((idx, str(e)))
                        
                        # Try to process with smaller sub-chunks
                        if len(chunk) > 50000:
                            click.echo(info_message(f"Attempting to process chunk {idx} in smaller pieces..."))
                            sub_chunks = chunk_text(chunk, max_chars=30000)
                            sub_results = []
                            
                            for sub_idx, sub_chunk in enumerate(sub_chunks, 1):
                                try:
                                    sub_prompt = PROMPTS.get(
                                        f"processing.digest.chunk_analysis_{mode}",
                                        documents=sub_chunk,
                                        chunk_num=f"{idx}.{sub_idx}",
                                        total_chunks=len(chunks),
                                        context=context or "general analysis",
                                    )
                                    sub_content, sub_usage = client.complete(
                                        [
                                            {
                                                "role": "system",
                                                "content": PROMPTS.get("processing.digest.system_prompt"),
                                            },
                                            {"role": "user", "content": sub_prompt},
                                        ]
                                    )
                                    sub_results.append(sub_content)
                                    
                                    # Log sub-chunk usage
                                    for key in comprehensive_log["total_usage"]:
                                        comprehensive_log["total_usage"][key] += sub_usage.get(key, 0)
                                        
                                except Exception as sub_e:
                                    click.echo(warning_message(f"Skipping sub-chunk {idx}.{sub_idx}: {sub_e}"))
                            
                            if sub_results:
                                combined_sub_result = f"[Chunk {idx} processed in {len(sub_results)} parts]\n" + "\n---\n".join(sub_results)
                                chunk_analyses.append(combined_sub_result)
                                failed_chunks.remove(idx)  # It partially succeeded
                                
                                # Update partial save data
                                partial_save_data['chunks'].append(f"File: {os.path.basename(file_path)}, Chunk {idx} (sub-chunks)\n{combined_sub_result}")
                                
                                comprehensive_log["responses"].append({
                                    "file": file_path, 
                                    "chunk": f"{idx} (sub-chunks)", 
                                    "content": combined_sub_result, 
                                    "usage": {"note": "See individual sub-chunks"}
                                })
                        continue
                        
                    except Exception as e:
                        # Other errors - log but continue
                        click.echo(error_message(f"\nError in chunk {idx}: {e}"))
                        failed_chunks.append(idx)
                        chunk_errors.append((idx, str(e)))
                        continue

            # After processing all chunks, check if we have any results
            if not chunk_analyses:
                raise click.ClickException("All chunks failed to process. Please try with smaller files or adjust max_chars in config.")
            
            # Store errors for later display
            if chunk_errors:
                all_chunk_errors.extend([(file_path, idx, err) for idx, err in chunk_errors])
            
            # Show summary
            if failed_chunks:
                click.echo(warning_message(
                    f"\nProcessed {len(chunk_analyses)} of {len(chunks)} chunks successfully. "
                    f"Failed chunks: {failed_chunks}"
                ))
            else:
                click.echo(success_message(f"\nAll {len(chunks)} chunks processed successfully!"))
            
            # Now consolidate all chunk analyses into unified digest
            click.echo(info_message(f"Consolidating analyses for {os.path.basename(file_path)}..."))

            consolidated_content = "\n\n".join(
                [
                    f"=== Analysis from Document Section {i+1} ===\n{analysis}"
                    for i, analysis in enumerate(chunk_analyses)
                ]
            )

            consolidation_prompt = PROMPTS.get(
                f"processing.digest.consolidation_{mode}",
                chunk_analyses=consolidated_content,
                total_chunks=len(chunks),
                context=context or "comprehensive analysis",
            )

            try:
                final_content, final_usage = client.complete(
                    [
                        {
                            "role": "system",
                            "content": PROMPTS.get("processing.digest.system_prompt"),
                        },
                        {"role": "user", "content": consolidation_prompt},
                    ]
                )
            except Exception as e:
                raise click.ClickException(f"LLM error in digest consolidation for {file_path}: {e}")

            # Citation validation for issues mode
            if mode == "issues":
                citation_issues = client.validate_citations(final_content)
                if citation_issues:
                    citation_warning = "--- CITATION WARNINGS ---\n"
                    citation_warning += "\n".join(citation_issues)
                    citation_warning += "\n" + "-" * 40 + "\n\n"
                    final_content = citation_warning + final_content

            # Log consolidation response
            comprehensive_log["responses"].append(
                {"file": file_path, "chunk": "consolidation", "content": final_content, "usage": final_usage}
            )

            # Accumulate final usage statistics
            for key in comprehensive_log["total_usage"]:
                comprehensive_log["total_usage"][key] += final_usage.get(key, 0)

            file_output.append(final_content)
        
        # Add file header and content to overall output
        all_documents_output.append(f"=== SOURCE: {os.path.basename(file_path)} ===\n\n" + "\n".join(file_output))

    # Combine all file outputs
    if len(file) > 1:
        # Multiple files - add consolidation header
        content = f"=== DIGEST {mode.upper()} FOR {len(file)} FILES ===\n\n"
        content += "\n\n".join(all_documents_output)
    else:
        # Single file - use content directly
        content = "\n\n".join(all_documents_output)
    
    # Save output using utility
    output_file = save_command_output(
        f"digest_{mode}",
        content,
        f"{len(source_files)} files",
        metadata={
            "Mode": mode.title(), 
            "Source Files": source_files,
            "Context": context or "None"
        },
    )

    # Save comprehensive audit log
    save_log(
        f"digest_{mode}",
        {
            "inputs": {
                "files": list(file),
                "mode": mode,
                "context": context,
                "total_chunks_processed": comprehensive_log["total_chunks_processed"],
            },
            "params": f"mode={mode}, max_chars={CONFIG.max_chars}, context={context}",
            "responses": comprehensive_log["responses"],
            "usage": comprehensive_log["total_usage"],
            "output_file": output_file,
        },
    )

    # Show completion
    mode_description = (
        "chronological summaries" if mode == "summary" else "legal issue identification"
    )
    stats = {
        "Documents": f"{len(source_files)} files",
        "Mode": mode_description,
        "Total chunks processed": comprehensive_log["total_chunks_processed"],
        "Total tokens": comprehensive_log["total_usage"]["total_tokens"],
    }

    show_command_completion(f"digest {mode}", output_file, None, stats)
    
    # Display any chunk processing errors
    if all_chunk_errors:
        click.echo("\n" + error_message("=== CHUNK PROCESSING ERRORS ==="))
        for file_path, chunk_idx, error in all_chunk_errors:
            click.echo(f"{os.path.basename(file_path)} - Chunk {chunk_idx}: {error}")
        click.echo(info_message("\nDespite errors, partial results have been saved."))
    
    # Unregister emergency save since we completed successfully
    atexit.unregister(emergency_save)
    signal.signal(signal.SIGINT, signal.SIG_DFL)
