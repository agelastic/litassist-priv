"""
Mass-document digestion via Claude.

This module implements the 'digest' command which processes large documents by splitting
them into manageable chunks and using Claude to either summarize content chronologically
or identify potential legal issues in each section.
"""

import click
import os

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
@click.argument("file", type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["summary", "issues"]), default="summary")
@click.option(
    "--hint",
    type=str,
    default=None,
    help="Optional hint to focus the analysis on specific topics.",
)
@timed
def digest(file, mode, hint):
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

    # Process content based on chunking needs
    if len(chunks) == 1:
        # Single chunk - process normally with unified analysis
        chunk = chunks[0]

        # Use centralized digest prompts for unified analysis
        if mode == "summary":
            if hint:
                hint_instruction = PROMPTS.get(
                    "processing.digest.summary_mode_hint_instruction_with_hint",
                    hint=hint,
                )
            else:
                hint_instruction = PROMPTS.get(
                    "processing.digest.summary_mode_hint_instruction_no_hint"
                )
            digest_prompt = PROMPTS.get(
                "processing.digest.summary_mode",
                hint_instruction=hint_instruction,
            )
            prompt = f"{digest_prompt}\n\n{chunk}"
        else:  # issues mode
            if hint:
                hint_instruction = PROMPTS.get(
                    "processing.digest.issues_mode_hint_instruction_with_hint",
                    hint=hint,
                )
            else:
                hint_instruction = PROMPTS.get(
                    "processing.digest.issues_mode_hint_instruction_no_hint"
                )
            digest_prompt = PROMPTS.get(
                "processing.digest.issues_mode",
                hint_instruction=hint_instruction,
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
            raise click.ClickException(f"LLM error in digest: {e}")

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
            {"chunk": 1, "content": content, "usage": usage}
        )

        # Accumulate usage statistics
        for key in comprehensive_log["total_usage"]:
            comprehensive_log["total_usage"][key] += usage.get(key, 0)

        all_output.append(content)

    else:
        # Multiple chunks - need consolidation approach
        chunk_analyses = []

        with click.progressbar(
            chunks, label="Analyzing document sections"
        ) as chunks_bar:
            for idx, chunk in enumerate(chunks_bar, start=1):
                # Use chunk-specific prompt for partial analysis
                chunk_prompt = PROMPTS.get(
                    f"processing.digest.chunk_analysis_{mode}",
                    documents=chunk,
                    chunk_num=idx,
                    total_chunks=len(chunks),
                    hint=hint or "general analysis",
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
                except Exception as e:
                    raise click.ClickException(f"LLM error in digest chunk {idx}: {e}")

                chunk_analyses.append(content)

                # Collect data for comprehensive log
                comprehensive_log["responses"].append(
                    {"chunk": idx, "content": content, "usage": usage}
                )

                # Accumulate usage statistics
                for key in comprehensive_log["total_usage"]:
                    comprehensive_log["total_usage"][key] += usage.get(key, 0)

        # Now consolidate all chunk analyses into unified digest
        click.echo("🔄 Consolidating analyses into unified digest...")

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
            hint=hint or "comprehensive analysis",
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
            raise click.ClickException(f"LLM error in digest consolidation: {e}")

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
            {"chunk": "consolidation", "content": final_content, "usage": final_usage}
        )

        # Accumulate final usage statistics
        for key in comprehensive_log["total_usage"]:
            comprehensive_log["total_usage"][key] += final_usage.get(key, 0)

        all_output.append(final_content)

    # Save output using utility
    content = "\n".join(all_output)
    output_file = save_command_output(
        f"digest_{mode}",
        content,
        os.path.basename(file),
        metadata={"Mode": mode.title(), "Source File": file},
    )

    # Save comprehensive audit log
    save_log(
        f"digest_{mode}",
        {
            "inputs": {
                "file": file,
                "mode": mode,
                "hint": hint,
                "chunks_processed": len(chunks),
            },
            "params": f"mode={mode}, max_chars={CONFIG.max_chars}, hint={hint}",
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
        "Total tokens": comprehensive_log["total_usage"]["total_tokens"],
    }

    show_command_completion(f"digest {mode}", output_file, None, stats)
