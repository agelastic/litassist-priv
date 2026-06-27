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
from litassist.utils.file_ops import expand_glob_single_callback
from .core import run_verification_workflow


@click.command()
@click.argument("file", type=click.Path(), callback=expand_glob_single_callback)
@click.option("--citations", is_flag=True, help="Verify citations only")
@click.option("--soundness", is_flag=True, help="Verify legal soundness only")
@click.option("--reasoning", is_flag=True, help="Verify/generate reasoning trace only")
@click.option("--cove", is_flag=True, help="Add Chain of Verification as final check")
@click.option(
    "--faithfulness",
    is_flag=True,
    help="Check the document's factual claims are grounded in the --reference source documents (requires --reference)."
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.option(
    "--reference",
    type=str,
    help="Glob pattern for the source documents (the ground truth), used as context across stages and, with --faithfulness, the documents the claims are checked against (e.g., '*.txt', 'docs/*.pdf'). Supports PDF and text files."
)
@click.option(
    "--cove-reference",
    type=str,
    help="Glob pattern for reference files to include in CoVe answer stage (e.g., 'exhibits/*.pdf', 'affidavits/*.txt'). Requires --cove flag."
)
@click.option(
    "--heavy",
    is_flag=True,
    help="Use verification-heavy mode (max thinking effort for reasoning and soundness stages)"
)
@timed
def verify(file, citations, soundness, reasoning, cove, faithfulness, output, reference, cove_reference, heavy):
    """
    Verify legal text for citations, soundness, and reasoning.

    By default, performs citations, soundness, and reasoning.
    Use flags to run specific verifications only. --faithfulness is opt-in and
    requires --reference source documents.
    """
    # If no specific verification flags are set, enable the default three. --faithfulness
    # counts as a selection so that "verify FILE --faithfulness" runs ONLY faithfulness.
    if not any([citations, soundness, reasoning, faithfulness]):
        citations = soundness = reasoning = True

    # Faithfulness checks the document against supplied sources; without them there is
    # nothing to check against, so fail fast rather than silently degrade.
    if faithfulness and not reference:
        raise click.ClickException(
            "--faithfulness requires --reference source documents to check the document against."
        )

    # Run the verification workflow
    run_verification_workflow(
        file=file,
        citations=citations,
        soundness=soundness,
        reasoning=reasoning,
        cove=cove,
        faithfulness=faithfulness,
        output=output,
        reference=reference,
        cove_reference=cove_reference,
        heavy=heavy,
    )
