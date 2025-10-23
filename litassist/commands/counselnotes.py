"""
Strategic counsel's notes generation for legal documents.

This module implements the 'counselnotes' command which generates strategic analysis,
tactical insights, and structured extractions from legal documents using an advocate's
perspective, complementing the neutral analysis provided by the digest command.
"""

import click
import os

from litassist.config import get_config
from litassist.prompts import PROMPTS
from litassist.utils.file_ops import read_document
from litassist.utils.text_processing import chunk_text
from litassist.utils.core import (
    timed,
    show_command_completion,
)
from litassist.utils.formatting import (
    info_message,
)
from litassist.logging import (
    save_log,
    save_command_output,
    log_task_event,
)
from litassist.llm import LLMClientFactory


@click.command()
@click.argument("files", nargs=-1, type=click.Path(exists=True), required=True)
@click.option(
    "--extract",
    type=click.Choice(["all", "citations", "principles", "checklist"]),
    help="Extract specific elements as structured JSON data",
)
@click.option(
    "--verify", is_flag=True, help="Enable citation verification for extracted content"
)
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def counselnotes(files, extract, verify, output):
    """
    Strategic analysis and counsel's notes for legal documents.

    Generates strategic analysis, tactical insights, and structured extractions
    from legal documents using an advocate's perspective. Supports cross-document
    synthesis and multiple extraction modes.

    Args:
        files: One or more document files (PDF or text) to analyze.
        extract: Optional structured extraction mode (all/citations/principles/checklist).
        verify: Enable citation verification for extracted content.
        output: Custom output filename prefix.

    Raises:
        click.ClickException: If there are errors with file reading, processing,
                             or LLM API calls.
    """
    # Command start log
    try:
        log_task_event(
            "counselnotes",
            "init",
            "start",
            "Starting counsel notes generation",
            {"model": LLMClientFactory.get_model_for_command("counselnotes")},
        )
    except Exception:
        pass
    
    # Validate that at least one file is provided
    if not files:
        raise click.ClickException("At least one input file must be provided.")

    # Read and consolidate all documents
    try:
        log_task_event(
            "counselnotes",
            "reading",
            "start",
            "Reading input documents"
        )
    except Exception:
        pass
    
    all_content = []
    file_info = []

    for file_path in files:
        try:
            content = read_document(file_path)
            all_content.append(
                f"=== DOCUMENT: {os.path.basename(file_path)} ===\n{content}\n=== END DOCUMENT: {os.path.basename(file_path)} ==="
            )
            file_info.append(
                {
                    "path": file_path,
                    "name": os.path.basename(file_path),
                    "size": len(content),
                }
            )
        except Exception as e:
            raise click.ClickException(f"Error reading {file_path}: {e}")

    # Combine all documents for cross-document analysis
    combined_content = "\n\n".join(all_content)

    # Check if content needs chunking
    if len(combined_content) > get_config().max_chars:
        # For large content, chunk and process separately then synthesize
        chunks = chunk_text(combined_content, max_chars=get_config().max_chars)
        processing_mode = "chunked"
    else:
        # Process all content together for better synthesis
        chunks = [combined_content]
        processing_mode = "unified"

    # Create client using factory
    client = LLMClientFactory.for_command("counselnotes")
    
    try:
        log_task_event(
            "counselnotes",
            "reading",
            "end",
            f"Read {len(files)} document(s)"
        )
    except Exception:
        pass

    # Collect all output content and comprehensive log data
    all_output = []
    comprehensive_log = {
        "files": file_info,
        "processing_mode": processing_mode,
        "extract_mode": extract,
        "verify_citations": verify,
        "chunks_processed": len(chunks),
        "responses": [],
        "total_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

    # Process content based on extraction mode
    if extract:
        # Structured extraction mode
        extraction_results = []

        with click.progressbar(
            chunks, label="Extracting structured data"
        ) as chunks_bar:
            for idx, chunk in enumerate(chunks_bar, start=1):
                # Get extraction prompt based on mode
                extraction_prompt = PROMPTS.get(
                    f"processing.counselnotes.extraction.{extract}", documents=chunk
                )

                try:
                    log_task_event(
                        "counselnotes",
                        "extraction",
                        "llm_call",
                        f"Extracting {extract} from chunk {idx}/{len(chunks)}",
                        {"model": client.model}
                    )
                except Exception:
                    pass
                
                try:
                    content, usage = client.complete(
                        [
                            {
                                "role": "system",
                                "content": PROMPTS.get(
                                    "processing.counselnotes.system_prompt"
                                ),
                            },
                            {"role": "user", "content": extraction_prompt},
                        ]
                    )
                    
                    try:
                        log_task_event(
                            "counselnotes",
                            "extraction",
                            "llm_response",
                            f"Chunk {idx}/{len(chunks)} extraction complete",
                            {"model": client.model}
                        )
                    except Exception:
                        pass
                    
                except Exception as e:
                    raise click.ClickException(
                        f"LLM error in extraction chunk {idx}: {e}"
                    )

                # Process this chunk's extraction (will be aggregated later)
                extraction_results.append(content)

                # Citation verification if requested
                if verify:
                    citation_issues = client.validate_citations(content)
                    if citation_issues:
                        click.echo(f"Citation warnings found in chunk {idx}:")
                        for issue in citation_issues:
                            click.echo(f"  - {issue}")

                # Log response data
                comprehensive_log["responses"].append(
                    {
                        "chunk": idx,
                        "content": content,
                        "usage": usage,
                    }
                )

                # Accumulate usage statistics
                for key in comprehensive_log["total_usage"]:
                    comprehensive_log["total_usage"][key] += usage.get(key, 0)

        # Process extraction results
        if len(extraction_results) > 1:
            # Multiple chunks - consolidate text directly
            consolidated_text = "\n\n---\n\n".join(extraction_results)
            # Add header to indicate consolidation
            final_content = f"[Consolidated from {len(extraction_results)} document chunks]\n\n{consolidated_text}"
        else:
            # Single chunk - use as is
            final_content = (
                extraction_results[0]
                if extraction_results
                else "No extraction results."
            )

        all_output.append(final_content)

    else:
        # Strategic analysis mode (non-extraction)
        if len(chunks) == 1:
            # Single chunk - process normally
            chunk = chunks[0]
            strategic_prompt = PROMPTS.get(
                "processing.counselnotes.strategic_analysis", documents=chunk
            )

            try:
                log_task_event(
                    "counselnotes",
                    "analysis",
                    "llm_call",
                    "Analyzing single document",
                    {"model": client.model}
                )
            except Exception:
                pass
            
            try:
                content, usage = client.complete(
                    [
                        {
                            "role": "system",
                            "content": PROMPTS.get(
                                "processing.counselnotes.system_prompt"
                            ),
                        },
                        {"role": "user", "content": strategic_prompt},
                    ]
                )
                
                try:
                    log_task_event(
                        "counselnotes",
                        "analysis",
                        "llm_response",
                        "Single document analysis complete",
                        {"model": client.model}
                    )
                except Exception:
                    pass
                
            except Exception as e:
                raise click.ClickException(f"LLM error in analysis: {e}")

            # Citation verification if requested
            if verify:
                citation_issues = client.validate_citations(content)
                if citation_issues:
                    citation_warning = "--- CITATION WARNINGS ---\n"
                    citation_warning += "\n".join(citation_issues)
                    citation_warning += "\n" + "-" * 40 + "\n\n"
                    content = citation_warning + content

            # Log response data
            comprehensive_log["responses"].append(
                {"chunk": 1, "content": content, "usage": usage}
            )

            # Accumulate usage statistics
            for key in comprehensive_log["total_usage"]:
                comprehensive_log["total_usage"][key] += usage.get(key, 0)

            all_output.append(content)

        else:
            # Multiple chunks - need consolidation
            chunk_analyses = []

            with click.progressbar(
                chunks, label="Analyzing document chunks"
            ) as chunks_bar:
                for idx, chunk in enumerate(chunks_bar, start=1):
                    # Use chunk-specific prompt for partial analysis
                    chunk_prompt = PROMPTS.get(
                        "processing.counselnotes.chunk_analysis",
                        documents=chunk,
                        chunk_num=idx,
                        total_chunks=len(chunks),
                    )

                    try:
                        log_task_event(
                            "counselnotes",
                            "chunk_analysis",
                            "llm_call",
                            f"Analyzing chunk {idx}/{len(chunks)}",
                            {"model": client.model}
                        )
                    except Exception:
                        pass
                    
                    try:
                        content, usage = client.complete(
                            [
                                {
                                    "role": "system",
                                    "content": PROMPTS.get(
                                        "processing.counselnotes.system_prompt"
                                    ),
                                },
                                {"role": "user", "content": chunk_prompt},
                            ]
                        )
                        
                        try:
                            log_task_event(
                                "counselnotes",
                                "chunk_analysis",
                                "llm_response",
                                f"Chunk {idx}/{len(chunks)} analysis complete",
                                {"model": client.model}
                            )
                        except Exception:
                            pass
                        
                    except Exception as e:
                        raise click.ClickException(
                            f"LLM error in analysis chunk {idx}: {e}"
                        )

                    chunk_analyses.append(content)

                    # Log response data
                    comprehensive_log["responses"].append(
                        {"chunk": idx, "content": content, "usage": usage}
                    )

                    # Accumulate usage statistics
                    for key in comprehensive_log["total_usage"]:
                        comprehensive_log["total_usage"][key] += usage.get(key, 0)

            # Now consolidate all chunk analyses into final strategic notes
            click.echo(
                info_message(
                    "Consolidating analyses into comprehensive strategic notes..."
                )
            )

            consolidated_content = "\n\n".join(
                [
                    f"=== ANALYSIS FROM DOCUMENT SECTION {i + 1} ===\n{analysis}\n=== END ANALYSIS FROM DOCUMENT SECTION {i + 1} ==="
                    for i, analysis in enumerate(chunk_analyses)
                ]
            )

            consolidation_prompt = PROMPTS.get(
                "processing.counselnotes.consolidation",
                chunk_analyses=consolidated_content,
                total_chunks=len(chunks),
            )

            try:
                log_task_event(
                    "counselnotes",
                    "consolidation",
                    "llm_call",
                    "Consolidating chunk analyses",
                    {"model": client.model}
                )
            except Exception:
                pass
            
            try:
                final_content, final_usage = client.complete(
                    [
                        {
                            "role": "system",
                            "content": PROMPTS.get(
                                "processing.counselnotes.system_prompt"
                            ),
                        },
                        {"role": "user", "content": consolidation_prompt},
                    ]
                )
                
                try:
                    log_task_event(
                        "counselnotes",
                        "consolidation",
                        "llm_response",
                        "Consolidation complete",
                        {"model": client.model}
                    )
                except Exception:
                    pass
                
            except Exception as e:
                raise click.ClickException(f"LLM error in consolidation: {e}")

            # Citation verification if requested
            if verify:
                citation_issues = client.validate_citations(final_content)
                if citation_issues:
                    citation_warning = "--- CITATION WARNINGS ---\n"
                    citation_warning += "\n".join(citation_issues)
                    citation_warning += "\n" + "-" * 40 + "\n\n"
                    final_content = citation_warning + final_content

            # Log consolidation response
            comprehensive_log["responses"].append(
                {
                    "chunk": "consolidation",
                    "content": final_content,
                    "usage": final_usage,
                }
            )

            # Accumulate final usage statistics
            for key in comprehensive_log["total_usage"]:
                comprehensive_log["total_usage"][key] += final_usage.get(key, 0)

            all_output.append(final_content)

    # Prepare final output
    final_content = "\n\n".join(all_output)

    # Prepare metadata for save_command_output
    files_summary = ", ".join([info["name"] for info in file_info])
    mode_description = f"extraction ({extract})" if extract else "strategic analysis"

    # Note: Header is now handled by save_command_output, not added to content

    # Save output using utility
    output_prefix = output if output else "counselnotes"
    if extract:
        output_prefix += f"_{extract}"

    output_file = save_command_output(
        output_prefix,
        final_content,
        "" if output else files_summary,  # Use empty string when custom output provided
        metadata={
            "Mode": mode_description.title(),
            "Documents Analyzed": files_summary,
            "Processing Mode": processing_mode,
            "Extraction Type": extract or "None",
            "Citation Verification": "Enabled" if verify else "Disabled",
        },
    )

    # Save comprehensive audit log (without response content)
    save_log(
        f"counselnotes_{extract if extract else 'analysis'}",
        {
            "inputs": {
                "files": [info["path"] for info in file_info],
                "extract_mode": extract,
                "verify_citations": verify,
                "output_prefix": output_prefix,
                "processing_mode": processing_mode,
                "chunks_processed": len(chunks),
            },
            "params": f"extract={extract}, verify={verify}, files={len(files)}",
            # Response content removed - already logged by LLMClient separately
            "usage": comprehensive_log["total_usage"],
            "output_file": output_file,
        },
    )

    # Show completion with statistics
    stats = {
        "Documents": len(files),
        "Mode": mode_description,
        "Processing": processing_mode,
        "Total tokens": comprehensive_log["total_usage"]["total_tokens"],
    }

    if extract:
        stats["Extraction"] = extract

    show_command_completion("counselnotes", output_file, None, stats)
    
    # Command end log
    try:
        log_task_event(
            "counselnotes",
            "init",
            "end",
            "Counsel notes generation complete"
        )
    except Exception:
        pass
