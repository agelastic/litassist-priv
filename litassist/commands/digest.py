"""
Mass-document digestion via Claude.

This module implements the 'digest' command which processes large documents by splitting
them into manageable chunks and using Claude to either summarize content chronologically
or identify potential legal issues in each section.
"""

import click

from litassist.utils import read_document, chunk_text, save_log
from litassist.llm import LLMClient


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["summary", "issues"]), default="summary")
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
    chunks = chunk_text(text)
    # Select parameter presets based on mode
    presets = {
        "summary": {"temperature": 0, "top_p": 0},
        "issues": {"temperature": 0.2, "top_p": 0.5},
    }[mode]
    client = LLMClient("anthropic/claude-3-sonnet", **presets)

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

            # Save audit log for this chunk
            save_log(
                f"digest_{mode}",
                {
                    "file": file,
                    "chunk": idx,
                    "response": content,
                    "usage": usage,
                },
            )
            # Output to user
            click.echo(f"\n--- Chunk {idx} ---\n{content}")
