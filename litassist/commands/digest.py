"""
Mass-document digestion via Claude.

This module implements the 'digest' command which processes large documents by splitting
them into manageable chunks and using Claude to either summarize content chronologically
or identify potential legal issues in each section.
"""

import click
import os
import re
import time

from litassist.config import CONFIG
from litassist.utils import (
    read_document, 
    chunk_text, 
    save_log, 
    timed, 
    save_command_output,
    show_command_completion
)
from litassist.llm import LLMClientFactory


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["summary", "issues"]), default="summary")
@timed
def digest(file, mode):
    """
    Mass-document digestion via Claude.

    Processes large documents by splitting them into manageable chunks
    and using Claude to either summarize content chronologically or
    identify potential legal issues in each section.

    Note: Verification removed as this is low-stakes content summarization.

    Args:
        file: Path to the document (PDF or text) to analyze.
        mode: Type of analysis to perform - 'summary' for chronological summaries
              or 'issues' to identify potential legal problems.

    Raises:
        click.ClickException: If there are errors with file reading, processing,
                             or LLM API calls.
    """
    # Read and split the document
    text = read_document(file)
    chunks = chunk_text(text, max_chars=CONFIG.max_chars)
    # Create client using factory with mode-specific configuration
    client = LLMClientFactory.for_command("digest", mode)

    # Collect all output content
    all_output = []

    # Collect comprehensive log data
    comprehensive_log = {
        "file": file,
        "mode": mode,
        "chunks_processed": len(chunks),
        "responses": [],
        "total_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }

    # Process each chunk with a progress bar
    with click.progressbar(chunks, label="Processing chunks") as chunks_bar:
        for idx, chunk in enumerate(chunks_bar, start=1):
            prompt = (
                "Provide a concise chronological summary:\n\n" + chunk
                if mode == "summary"
                else "Identify any potential legal issues:\n\n" + chunk
            )
            # Call the LLM
            try:
                content, usage = client.complete(
                    [
                        {
                            "role": "system",
                            "content": "Australian law only. Structure your response logically with clear headings, bullet points for key facts, and proper paragraph breaks. Focus on legal accuracy over comprehensiveness, and cite relevant legislation or cases when identified. Conclude each section with a definitive statement rather than open-ended observations.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                )
            except Exception as e:
                raise click.ClickException(f"LLM error in digest chunk {idx}: {e}")

            # Note: digest removed verification as it's low-stakes content summarization
            # However, we still need to validate citations to prevent cascade errors

            # CRITICAL: Validate citations immediately to prevent cascade errors
            # Even digest can contain legal precedents that need validation
            if (
                mode == "issues"
            ):  # Legal issues mode is more likely to contain citations
                citation_issues = client.validate_citations(content)
                if citation_issues:
                    # Prepend warnings to this chunk's content
                    citation_warning = "--- CITATION WARNINGS FOR THIS CHUNK ---\n"
                    citation_warning += "\n".join(citation_issues)
                    citation_warning += "\n" + "-" * 40 + "\n\n"
                    content = citation_warning + content

            # Collect data for comprehensive log
            comprehensive_log["responses"].append(
                {"chunk": idx, "content": content, "usage": usage}
            )

            # Accumulate usage statistics
            for key in comprehensive_log["total_usage"]:
                comprehensive_log["total_usage"][key] += usage.get(key, 0)

            # Collect output
            chunk_output = f"\n--- Chunk {idx} ---\n{content}"
            all_output.append(chunk_output)

    # Save output using utility
    content = "\n".join(all_output)
    output_file = save_command_output(
        f"digest_{mode}",
        content,
        os.path.basename(file),
        metadata={"Mode": mode.title(), "Source File": file}
    )

    # Save comprehensive audit log
    save_log(
        f"digest_{mode}",
        {
            "inputs": {"file": file, "mode": mode, "chunks_processed": len(chunks)},
            "params": f"mode={mode}, max_chars={CONFIG.max_chars}",
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
        "Document": os.path.basename(file),
        "Mode": mode_description,
        "Chunks processed": len(chunks),
        "Total tokens": comprehensive_log["total_usage"]["total_tokens"]
    }
    
    show_command_completion(f"digest {mode}", output_file, None, stats)
