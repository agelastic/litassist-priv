"""
Core orchestration logic for verify command.

This module coordinates the verification workflow, manages reference files,
and handles Chain of Verification (CoVe) as the final verification stage.
"""

import os
import re
import logging
import click
from litassist.utils.file_ops import read_document, process_reference_files
from litassist.utils.formatting import (
    verifying_message,
    error_message,
    warning_message,
)
from litassist.logging import save_command_output, save_log, log_task_event
from litassist.verification_chain import run_cove_verification, format_cove_report
from .citation_verifier import verify_citations
from .reasoning_handler import verify_reasoning
from .soundness_checker import verify_soundness


def handle_verification_error(step_name: str, exception: Exception) -> None:
    """Handle verification step errors with consistent formatting and logging."""
    msg = error_message(f"{step_name} failed: {exception}")
    click.echo(f"\n{msg}")
    logging.error(f"{step_name} error: {exception}")


def run_verification_workflow(
    file: str,
    citations: bool,
    soundness: bool,
    reasoning: bool,
    cove: bool,
    output: str = None,
    reference: str = None,
    cove_reference: str = None
) -> dict:
    """
    Run the complete verification workflow.

    Args:
        file: Path to file to verify
        citations: Whether to verify citations
        soundness: Whether to verify soundness
        reasoning: Whether to verify reasoning
        cove: Whether to run Chain of Verification
        output: Optional custom output filename prefix
        reference: Optional reference file glob pattern
        cove_reference: Optional CoVe reference file glob pattern

    Returns:
        dict: Workflow results including files generated and reports
    """
    # Command start log
    try:
        log_task_event(
            "verify",
            "init",
            "start",
            "Starting verification command",
            {"stages": f"citations={citations}, soundness={soundness}, reasoning={reasoning}, cove={cove}"}
        )
    except Exception:
        pass

    click.echo(verifying_message(f"Verifying {file}..."))

    # Read input document
    try:
        log_task_event(
            "verify",
            "reading",
            "start",
            "Reading input document"
        )
    except Exception:
        pass

    try:
        content = read_document(file)
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(f"Error reading file: {e}")

    if not content.strip():
        raise click.ClickException("File is empty")

    try:
        log_task_event(
            "verify",
            "reading",
            "end",
            f"Document read: {len(content)} characters"
        )
    except Exception:
        pass

    # Process reference files if provided
    reference_context, reference_files = process_reference_files(
        reference,
        purpose="reference",
        show_char_count=True
    )

    if reference_files:
        try:
            log_task_event(
                "verify",
                "reference",
                "processed",
                f"Processed {len(reference_files)} reference files"
            )
        except Exception:
            pass

    # Process CoVe reference files if provided
    cove_reference_context, cove_reference_files = process_reference_files(
        cove_reference,
        purpose="CoVe answers",
        require_flag="--cove",
        flag_enabled=cove,
        show_char_count=True
    )

    if cove_reference_files:
        try:
            log_task_event(
                "verify",
                "cove_reference",
                "processed",
                f"Processed {len(cove_reference_files)} CoVe reference files"
            )
        except Exception:
            pass

    reports_generated = 0
    extra_files = {}
    citation_report = None
    reasoning_response = None
    case_content = {}

    # 1. Citation Verification
    if citations:
        try:
            (citation_report, case_content, citation_file,
             verified, unverified) = verify_citations(content, file, output)
            extra_files["Citation report"] = citation_file
            reports_generated += 1
        except Exception as e:
            handle_verification_error("Citation verification", e)

    # 2. Reasoning Trace Verification/Generation
    if reasoning:
        try:
            reasoning_response, reasoning_file, existing_trace = verify_reasoning(
                content, file, case_content, reference_context, citation_report, output
            )
            extra_files["Reasoning analysis"] = reasoning_file
            reports_generated += 1
        except Exception as e:
            handle_verification_error("Reasoning trace verification", e)

    # 3. Legal Soundness Verification
    if soundness:
        try:
            soundness_result, issues, soundness_file = verify_soundness(
                content, file, case_content, reference_context,
                citation_report, reasoning_response, output
            )
            extra_files["Soundness report"] = soundness_file
            reports_generated += 1
        except Exception as e:
            handle_verification_error("Legal soundness check", e)

    # 4. Chain of Verification (Final Stage)
    if cove:
        # Skip CoVe if only citations are being verified
        if citations and not soundness and not reasoning:
            click.echo(
                warning_message(
                    "CoVe skipped: --cove flag is ignored when only verifying citations"
                )
            )
        else:
            click.echo(verifying_message("Starting Chain of Verification..."))

            try:
                log_task_event(
                    "verify",
                    "cove",
                    "start",
                    "Starting Chain of Verification"
                )
            except Exception:
                pass

            try:
                # Use the most refined version of content available
                final_content = content
                if soundness and "soundness_result" in locals():
                    # Extract corrected document from soundness result if available
                    match = re.search(
                        r"## Verified and Corrected Document\s*\n(.*)",
                        soundness_result,
                        re.DOTALL,
                    )
                    if match:
                        final_content = match.group(1).strip()

                # Build prior contexts including any CoVe reference files
                prior_contexts_dict = {
                    "citations": citation_report,
                    "reasoning": reasoning_response,
                    "soundness": issues if soundness and "issues" in locals() else None,
                    "reference_files": reference_context if reference_context else None,
                }

                # Add CoVe reference files if available
                if cove_reference_context:
                    prior_contexts_dict["cove_reference_files"] = cove_reference_context

                cove_content, cove_results = run_cove_verification(
                    final_content,
                    "verify",
                    prior_contexts=prior_contexts_dict,
                )

                # Update final_content if regenerated
                base_name = os.path.splitext(file)[0]
                if cove_results["cove"]["regenerated"]:
                    final_content = cove_content
                    # Save regenerated document
                    regen_file = save_command_output(
                        f"{output}_regenerated" if output else "verify_regenerated",
                        final_content,
                        "" if output else os.path.basename(base_name),
                        metadata={
                            "Type": "CoVe Regenerated Document",
                            "File": file,
                            "Status": "[REGENERATED]",
                            "Issues Fixed": cove_results["cove"]["issues"],
                        },
                    )
                    extra_files["Regenerated document"] = regen_file

                # Save CoVe report with full dialogue
                cove_report = format_cove_report(cove_results)

                cove_file = save_command_output(
                    f"{output}_cove" if output else "verify_cove",
                    cove_report,
                    "" if output else os.path.basename(base_name),
                    metadata={
                        "Type": "Chain of Verification",
                        "File": file,
                        "Status": "[REGENERATED]"
                        if cove_results["cove"]["regenerated"]
                        else "[VERIFIED]",
                        "Issues": "Fixed"
                        if cove_results["cove"]["regenerated"]
                        else "None",
                    },
                )
                status = (
                    "[REGENERATED]"
                    if cove_results["cove"]["regenerated"]
                    else "[VERIFIED]"
                )
                click.echo(f"\n{status} Chain of Verification complete")
                click.echo(f"   - Analysis: {cove_file}")
                if cove_results["cove"]["regenerated"]:
                    click.echo(f"   - Regenerated: {regen_file}")
                else:
                    click.echo("   - No rewrite needed (document verified as accurate)")
                extra_files["CoVe report"] = cove_file
                reports_generated += 1

                try:
                    log_task_event(
                        "verify",
                        "cove",
                        "end",
                        f"Chain of Verification complete - {'regenerated' if cove_results['cove']['regenerated'] else 'verified'}"
                    )
                except Exception:
                    pass
            except Exception as e:
                handle_verification_error("Chain of Verification", e)

    click.echo(f"\nVerification complete. {reports_generated} reports generated.")

    # Command end log
    try:
        log_task_event(
            "verify",
            "init",
            "end",
            f"Verification command complete - {reports_generated} reports generated"
        )
    except Exception:
        pass

    # Save workflow log
    save_log(
        "verify",
        {
            "inputs": {
                "file": file,
                "options": {
                    "citations": citations,
                    "soundness": soundness,
                    "reasoning": reasoning,
                    "cove": cove,
                    "reference": reference,
                    "cove_reference": cove_reference,
                },
                "reference_files": reference_files,
                "cove_reference_files": cove_reference_files,
            },
            "outputs": extra_files,
            "reports_generated": reports_generated,
        },
    )

    return {
        "extra_files": extra_files,
        "reports_generated": reports_generated,
    }
