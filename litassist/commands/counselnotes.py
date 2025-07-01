"""
Strategic counsel's notes generation for legal documents.

This module implements the 'counselnotes' command which generates strategic analysis,
tactical insights, and structured extractions from legal documents using an advocate's
perspective, complementing the neutral analysis provided by the digest command.
"""

import click
import os
import json
from datetime import datetime

from litassist.config import CONFIG
from litassist.prompts import PROMPTS
from litassist.utils import (
    read_document,
    chunk_text,
    save_log,
    timed,
    save_command_output,
    show_command_completion,
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
    # Validate that at least one file is provided
    if not files:
        raise click.ClickException("At least one input file must be provided.")

    # Read and consolidate all documents
    all_content = []
    file_info = []

    for file_path in files:
        try:
            content = read_document(file_path)
            all_content.append(
                f"=== Document: {os.path.basename(file_path)} ===\n{content}"
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
    if len(combined_content) > CONFIG.max_chars:
        # For large content, chunk and process separately then synthesize
        chunks = chunk_text(combined_content, max_chars=CONFIG.max_chars)
        processing_mode = "chunked"
    else:
        # Process all content together for better synthesis
        chunks = [combined_content]
        processing_mode = "unified"

    # Create client using factory
    client = LLMClientFactory.for_command("counselnotes")

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
                except Exception as e:
                    raise click.ClickException(
                        f"LLM error in extraction chunk {idx}: {e}"
                    )

                # Parse JSON-first, fallback to regex if needed
                try:
                    # Attempt JSON parsing first (following June 2025 patterns)
                    if content.strip().startswith("{") and content.strip().endswith(
                        "}"
                    ):
                        extracted_data = json.loads(content.strip())
                    else:
                        # Fallback to text content if not JSON
                        extracted_data = {"extracted_content": content}
                except json.JSONDecodeError:
                    # Keep as text content if JSON parsing fails
                    extracted_data = {"extracted_content": content}

                extraction_results.append(extracted_data)

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
                        "extracted_data": extracted_data,
                        "usage": usage,
                    }
                )

                # Accumulate usage statistics
                for key in comprehensive_log["total_usage"]:
                    comprehensive_log["total_usage"][key] += usage.get(key, 0)

        # Synthesize extraction results if multiple chunks
        if len(extraction_results) > 1:
            # Combine extracted data intelligently
            if extract == "all":
                combined_data = {
                    "strategic_summary": "",
                    "key_citations": [],
                    "legal_principles": [],
                    "tactical_checklist": [],
                    "risk_assessment": "",
                    "recommendations": [],
                }
                for result in extraction_results:
                    if isinstance(result, dict):
                        for key in combined_data.keys():
                            if key in result:
                                if isinstance(combined_data[key], list):
                                    if isinstance(result[key], list):
                                        combined_data[key].extend(result[key])
                                    else:
                                        combined_data[key].append(result[key])
                                else:
                                    combined_data[key] += f"\n{result[key]}"
                final_output = json.dumps(combined_data, indent=2)
            else:
                # For other extraction modes, combine list-based results from each chunk.
                key = extract
                combined_list = []
                for r in extraction_results:
                    if isinstance(r, dict) and isinstance(r.get(key), list):
                        combined_list.extend(r[key])
                final_output = json.dumps({key: combined_list}, indent=2)
        else:
            final_output = (
                json.dumps(extraction_results[0], indent=2)
                if extraction_results
                else "{}"
            )

        all_output.append(final_output)

    else:
        # Strategic analysis mode (non-extraction)
        if len(chunks) == 1:
            # Single chunk - process normally
            chunk = chunks[0]
            strategic_prompt = PROMPTS.get(
                "processing.counselnotes.strategic_analysis", documents=chunk
            )

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
                "🔄 Consolidating analyses into comprehensive strategic notes..."
            )

            consolidated_content = "\n\n".join(
                [
                    f"=== Analysis from Document Section {i+1} ===\n{analysis}"
                    for i, analysis in enumerate(chunk_analyses)
                ]
            )

            consolidation_prompt = PROMPTS.get(
                "processing.counselnotes.consolidation",
                chunk_analyses=consolidated_content,
                total_chunks=len(chunks),
            )

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

    # Add document summary header
    files_summary = ", ".join([info["name"] for info in file_info])
    mode_description = f"extraction ({extract})" if extract else "strategic analysis"

    header = f"# Counsel's Notes - {mode_description.title()}\n\n"
    header += f"**Documents Analyzed:** {files_summary}\n"
    header += f"**Analysis Date:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
    header += f"**Processing Mode:** {processing_mode}\n"
    if verify:
        header += "**Citation Verification:** Enabled\n"
    header += "\n---\n\n"

    final_content = header + final_content

    # Save output using utility
    output_prefix = output if output else "counselnotes"
    if extract:
        output_prefix += f"_{extract}"

    output_file = save_command_output(
        output_prefix,
        final_content,
        files_summary,
        metadata={
            "Mode": mode_description,
            "Documents": len(files),
            "Extraction Type": extract or "None",
            "Citation Verification": verify,
        },
    )

    # Save comprehensive audit log
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
            "responses": comprehensive_log["responses"],
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
