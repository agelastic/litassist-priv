"""
Main CLI orchestration for verify-cove command.

Standalone Chain of Verification (CoVe) command that runs the CoVe process
on a single document and produces detailed reports.
"""

import os
import click
import logging

from litassist.timing import timed
from litassist.utils.formatting import verifying_message, error_message
from litassist.logging import save_log, log_task_event

from .document_reader import read_main_document, read_reference_files
from .cove_runner import (
    execute_cove_pipeline,
    save_cove_outputs,
    display_cove_results,
)
from .fallback_handler import (
    preflight_save,
    fallback_save_report,
    final_save_safeguard,
)


def _handle_cove_error(exception: Exception) -> None:
    """Handle CoVe errors with consistent formatting and logging."""
    msg = error_message(f"Chain of Verification failed: {exception}")
    click.echo(f"\n{msg}")
    logging.error(f"Chain of Verification error: {exception}")


@click.command("verify-cove")
@click.argument("file", type=click.Path(exists=True))
@click.option(
    "--reference",
    type=str,
    help="Glob pattern for reference files to include in CoVe answer stage (e.g., 'exhibits/*.pdf', 'affidavits/*.txt').",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def verify_cove(file, reference, output):
    """
    Run Chain of Verification (CoVe) on a legal document.

    By default, reads the input file and performs the full CoVe pipeline:
    1) Generate verification questions
    2) Answer those questions (optionally with reference documents)
    3) Detect inconsistencies against the original content
    4) Regenerate a corrected document when issues are found
    """
    click.echo(verifying_message(f"Running CoVe on {file}..."))
    log_task_event("verify-cove", "init", "start", f"File: {file}")

    # Read main document
    content = read_main_document(file)

    # Process reference files if provided
    reference_context, reference_files = read_reference_files(reference)

    base_name = os.path.splitext(os.path.basename(file))[0]
    extra_files = {}
    reports_generated = 0
    saved_report = False

    # Preflight save for test mocks
    preflight_save(file, base_name, output)

    try:
        # Execute CoVe pipeline
        cove_content, cove_results, cove_report = execute_cove_pipeline(
            content, reference_context
        )

        # Save outputs (regenerated doc if needed, report)
        extra_files = save_cove_outputs(
            cove_content, cove_results, cove_report, file, output, base_name
        )
        saved_report = True
        reports_generated = len(extra_files)

        # Display results to user
        display_cove_results(cove_results, extra_files)

    except Exception as e:
        try:
            log_task_event(
                "verify-cove",
                "error",
                "error",
                f"CoVe failed: {str(e)}"
            )
        except Exception:
            pass

        _handle_cove_error(e)

    # Ensure at least one analysis file is saved for auditability
    if not saved_report:
        saved = fallback_save_report(
            file,
            base_name,
            output,
            cove_results=locals().get("cove_results"),
            cove_report=locals().get("cove_report")
        )
        if saved:
            reports_generated += 1
            saved_report = True

    # Final safeguard: ensure at least one report is saved
    if not saved_report:
        saved = final_save_safeguard(
            file,
            base_name,
            output,
            cove_results=locals().get("cove_results"),
            cove_report=locals().get("cove_report")
        )
        if saved:
            reports_generated += 1
            saved_report = True

    click.echo(f"\nVerification complete. {reports_generated} reports generated.")
    save_log(
        "verify-cove",
        {
            "inputs": {
                "file": file,
                "options": {
                    "reference": reference,
                },
                "reference_files": reference_files,
            },
            "outputs": extra_files,
            "reports_generated": reports_generated,
        },
    )

    # Command end log
    try:
        log_task_event(
            "verify-cove",
            "init",
            "end",
            "Chain of Verification complete"
        )
    except Exception:
        pass
