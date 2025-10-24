"""
Post-hoc verification command for legal documents.

This command performs three types of verification on legal text files:
1. Citation verification - checks all citations are real and verifiable
2. Legal soundness - validates legal accuracy and Australian law compliance
3. Reasoning trace - verifies existing or generates new IRAC-based reasoning

By default (no flags), all three verifications are performed.
"""

import click
from litassist.timing import timed
from litassist.prompts import PROMPTS  # noqa: F401
from .core import run_verification_workflow


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--citations", is_flag=True, help="Verify citations only")
@click.option("--soundness", is_flag=True, help="Verify legal soundness only")
@click.option("--reasoning", is_flag=True, help="Verify/generate reasoning trace only")
@click.option("--cove", is_flag=True, help="Add Chain of Verification as final check")
@click.option("--output", type=str, help="Custom output filename prefix")
@click.option(
    "--reference",
    type=str,
    help="Glob pattern for reference files to include as context (e.g., '*.txt', 'docs/*.pdf'). Supports PDF and text files."
)
@click.option(
    "--cove-reference",
    type=str,
    help="Glob pattern for reference files to include in CoVe answer stage (e.g., 'exhibits/*.pdf', 'affidavits/*.txt'). Requires --cove flag."
)
@timed
def verify(file, citations, soundness, reasoning, cove, output, reference, cove_reference):
    """
    Verify legal text for citations, soundness, and reasoning.

    By default, performs all three verification types.
    Use flags to run specific verifications only.
    """
    # If no specific verification flags are set, enable all
    if not any([citations, soundness, reasoning]):
        citations = soundness = reasoning = True

    # Run the verification workflow
    run_verification_workflow(
        file=file,
        citations=citations,
        soundness=soundness,
        reasoning=reasoning,
        cove=cove,
        output=output,
        reference=reference,
        cove_reference=cove_reference
    )
