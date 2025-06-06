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
from litassist.utils import read_document, chunk_text, save_log, timed, OUTPUT_DIR
from litassist.llm import LLMClient


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
    # Select parameter presets based on mode
    presets = {
        "summary": {"temperature": 0, "top_p": 0},
        "issues": {"temperature": 0.2, "top_p": 0.5},
    }[mode]
    client = LLMClient("anthropic/claude-3-sonnet", **presets)

    # Prepare output file
    # Extract base filename without extension
    base_filename = os.path.splitext(os.path.basename(file))[0]
    # Create a slug from the filename
    filename_slug = re.sub(r'[^\w\s-]', '', base_filename.lower())
    filename_slug = re.sub(r'[-\s]+', '_', filename_slug)
    # Limit slug length
    filename_slug = filename_slug[:30].strip('_') or 'document'
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(OUTPUT_DIR, f"digest_{mode}_{filename_slug}_{timestamp}.txt")
    
    # Collect all output
    all_output = []
    all_output.append(f"Document Digest: {file}")
    all_output.append(f"Mode: {mode}")
    all_output.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    all_output.append("-" * 80 + "\n")

    # Collect comprehensive log data
    comprehensive_log = {
        "file": file,
        "mode": mode,
        "chunks_processed": len(chunks),
        "responses": [],
        "total_usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
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
            if mode == "issues":  # Legal issues mode is more likely to contain citations
                citation_issues = client.validate_citations(content)
                if citation_issues:
                    # Prepend warnings to this chunk's content
                    citation_warning = "--- CITATION WARNINGS FOR THIS CHUNK ---\n"
                    citation_warning += "\n".join(citation_issues)
                    citation_warning += "\n" + "-" * 40 + "\n\n"
                    content = citation_warning + content

            # Collect data for comprehensive log
            comprehensive_log["responses"].append({
                "chunk": idx,
                "content": content,
                "usage": usage
            })
            
            # Accumulate usage statistics
            for key in comprehensive_log["total_usage"]:
                comprehensive_log["total_usage"][key] += usage.get(key, 0)
            
            # Collect output
            chunk_output = f"\n--- Chunk {idx} ---\n{content}"
            all_output.append(chunk_output)
    
    # Write all output to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(all_output))
    
    # Save comprehensive audit log
    save_log(
        f"digest_{mode}",
        {
            "inputs": {
                "file": file,
                "mode": mode,
                "chunks_processed": len(chunks)
            },
            "params": f"mode={mode}, max_chars={CONFIG.max_chars}",
            "responses": comprehensive_log["responses"],
            "usage": comprehensive_log["total_usage"],
            "output_file": output_file
        }
    )
    
    # Show summary instead of full content
    click.echo("\n✅ Document digest complete!")
    click.echo(f"📄 Output saved to: \"{output_file}\"")
    
    # Show what was processed
    mode_description = "chronological summaries" if mode == "summary" else "legal issue identification"
    click.echo(f"\n📊 Generated {mode_description} for {len(chunks)} chunks")
    click.echo(f"📋 Document: {os.path.basename(file)}")
    
    click.echo(f"\n💡 View full digest: open \"{output_file}\"")
