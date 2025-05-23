"""
Auto-generate case_facts.txt under ten structured headings.

This module implements the 'extractfacts' command which processes a document
to extract relevant case facts and organizes them into a structured format
with ten standard headings.
"""

import click
import os
import time

from litassist.config import CONFIG
from litassist.utils import read_document, chunk_text, save_log, OUTPUT_DIR
from litassist.llm import LLMClient


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--verify", is_flag=True, help="Enable self-critique pass (default: auto-enabled)")
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
    chunks = chunk_text(text, max_chars=CONFIG.max_chars)

    # Initialize the LLM client with deterministic settings
    client = LLMClient("anthropic/claude-3-sonnet", temperature=0, top_p=0.15)
    client.command_context = "extractfacts"  # Set command context for auto-verification
    
    # extractfacts always needs verification as it creates foundational documents
    verify = True  # Force verification for critical accuracy

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
                "10. Client Objectives (include any constraints/limitations)\n\n"
                + chunk
            )
            try:
                content, usage = client.complete(
                    [
                        {
                            "role": "system",
                            "content": "Australian law only. Extract factual information precisely under the requested headings. Focus on being comprehensive, accurate, and well-organized. Use clear paragraph structure and bullet points where appropriate. Maintain a neutral, factual tone throughout. Ensure all extracted information follows Australian legal terminology and conventions.",
                        },
                        {"role": "user", "content": prompt},
                    ]
                )
            except Exception as e:
                raise click.ClickException(f"Error extracting facts in chunk: {e}")
            assembled.append(content.strip())

    # Combine all chunks into a single facts file
    combined = "\n\n".join(assembled)

    # Mandatory heavy verification for extractfacts (creates foundational documents)
    try:
        # Use heavy verification to ensure legal accuracy and proper structure
        correction = client.verify_with_level(combined, "heavy")
        if correction.strip():  # Only append if there are actual corrections
            combined = combined + "\n\n--- Legal Accuracy Review ---\n" + correction
        
        # Also run citation validation
        citation_issues = client.validate_citations(combined)
        if citation_issues:
            combined += "\n\n--- Citation Warnings ---\n" + "\n".join(citation_issues)
            
    except Exception as e:
        raise click.ClickException(
            f"Verification error during fact extraction: {e}"
        )

    # Save to timestamped file only
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    # Extract base filename without extension for the output name
    base_filename = os.path.splitext(os.path.basename(file))[0]
    # Create a slug from the filename
    filename_slug = base_filename.lower().replace(' ', '_')[:30]
    output_file = os.path.join(OUTPUT_DIR, f"extractfacts_{filename_slug}_{timestamp}.txt")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"# Extracted Facts from: {file}\n")
        f.write(f"# Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 80 + "\n\n")
        f.write(combined)
    
    click.echo(f"Extraction saved to: {output_file}")
    click.echo("\nTo use these facts with other commands, manually create or update case_facts.txt")

    # Audit log
    save_log(
        "extractfacts",
        {
            "inputs": {"source_file": file, "chunks": len(chunks)},
            "params": "verify=True (auto-enabled)",
            "response": combined,
            "output_file": output_file,
        },
    )
    click.echo("Extraction completed with legal accuracy verification.")
