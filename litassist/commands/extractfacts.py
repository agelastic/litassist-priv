"""
Auto-generate case_facts.txt under ten structured headings.

This module implements the 'extractfacts' command which processes a document
to extract relevant case facts and organizes them into a structured format
with ten standard headings.
"""

import click

from litassist.utils import read_document, chunk_text, save_log
from litassist.llm import LLMClient


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
def extractfacts(file, verify):
    """
    Auto-generate case_facts.txt under ten structured headings.

    Processes a document to extract relevant case facts and organizes them
    into a structured format with ten standard headings. This provides a
    foundation for other commands like 'brainstorm' and 'strategy' which require structured facts.

    Args:
        file: Path to the document (PDF or text) to extract facts from.
        verify: Whether to run a self-critique verification pass on the extracted facts.

    Raises:
        click.ClickException: If there are errors reading the file, processing chunks,
                             or with the LLM API calls.
    """
    # Read and chunk the document
    text = read_document(file)
    chunks = chunk_text(text)

    # Initialize the LLM client with deterministic settings
    client = LLMClient(
        "anthropic/claude-3-sonnet", temperature=0, top_p=0.15, max_tokens=2000
    )

    assembled = []
    # Process each chunk with a progress bar
    with click.progressbar(chunks, label="Extracting facts") as bar:
        for chunk in bar:
            prompt = (
                "Extract under these headings (include all relevant details):\n"
                "1. Parties (include roles and relationships)\n"
                "2. Background (include commercial/policy context if relevant)\n"
                "3. Key Events (in chronological order)\n"
                "4. Legal Issues\n"
                "5. Evidence Available (prioritize key evidence)\n"
                "6. Opposing Arguments (include known weaknesses/gaps)\n"
                "7. Procedural History (current status and past proceedings)\n"
                "8. Jurisdiction (include specific court/forum)\n"
                "9. Applicable Law\n"
                "10. Client Objectives (include any constraints/limitations)\n\n" + chunk
            )
            try:
                content, usage = client.complete(
                    [
                        {"role": "system", "content": "Australian law only."},
                        {"role": "user", "content": prompt},
                    ]
                )
            except Exception as e:
                raise click.ClickException(f"Error extracting facts in chunk: {e}")
            assembled.append(content.strip())

    # Combine all chunks into a single facts file
    combined = "\n\n".join(assembled)

    # Optional self-critique verification
    if verify:
        try:
            correction = client.verify(combined)
            combined = combined + "\n\n--- Corrections ---\n" + correction
        except Exception as e:
            raise click.ClickException(
                f"Self-verification error during fact extraction: {e}"
            )

    with open("case_facts.txt", "w", encoding="utf-8") as f:
        f.write(combined)

    # Audit log
    save_log(
        "extractfacts",
        {
            "inputs": {"source_file": file, "chunks": len(chunks)},
            "params": f"verify={verify}",
            "response": combined,
        },
    )
    click.echo("case_facts.txt created successfully.")
