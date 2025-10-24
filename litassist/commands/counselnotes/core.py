"""
Strategic counsel's notes generation for legal documents.

This module implements the 'counselnotes' command which generates strategic analysis,
tactical insights, and structured extractions from legal documents using an advocate's
perspective, complementing the neutral analysis provided by the digest command.
"""

import click

from litassist.utils.core import (
    timed,
    show_command_completion,
)
from litassist.logging import (
    save_log,
    save_command_output,
    log_task_event,
)
from litassist.llm.factory import LLMClientFactory

from .document_processor import read_and_consolidate_documents, prepare_chunks
from .extraction_processor import process_extraction_mode, consolidate_extraction_results
from .analysis_processor import process_strategic_analysis
from .consolidator import consolidate_analyses


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

    # Read and consolidate documents
    combined_content, file_info = read_and_consolidate_documents(files)

    # Prepare chunks
    chunks, processing_mode = prepare_chunks(combined_content)

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
        extraction_results = process_extraction_mode(
            chunks, extract, verify, client, comprehensive_log
        )

        # Consolidate extraction results
        final_content = consolidate_extraction_results(extraction_results)
        all_output.append(final_content)

    else:
        # Strategic analysis mode
        analysis_results, needs_consolidation = process_strategic_analysis(
            chunks, verify, client, comprehensive_log
        )

        if needs_consolidation:
            # Multiple chunks - consolidate analyses
            final_content, final_usage = consolidate_analyses(
                analysis_results, verify, client
            )

            # Log consolidation response
            comprehensive_log["responses"].append(
                {"consolidation": True, "content": final_content, "usage": final_usage}
            )

            # Accumulate final usage
            for key in comprehensive_log["total_usage"]:
                comprehensive_log["total_usage"][key] += final_usage.get(key, 0)

            all_output.append(final_content)
        else:
            # Single chunk - use as is
            all_output.extend(analysis_results)

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
