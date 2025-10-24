"""
CoVe verification pipeline execution for verify-cove command.

Handles running the Chain of Verification process, saving reports, and
managing regenerated documents.
"""

import click
from typing import Dict, Tuple, Optional

from litassist.logging import save_command_output, log_task_event
from litassist.verification_chain import run_cove_verification, format_cove_report


def execute_cove_pipeline(
    content: str,
    reference_context: Optional[str]
) -> Tuple[str, Dict, str]:
    """
    Execute the Chain of Verification pipeline.

    Args:
        content: Document content to verify
        reference_context: Optional reference file context for CoVe answers stage

    Returns:
        Tuple of (cove_content, cove_results, cove_report)
        - cove_content: Regenerated content (if issues found) or original
        - cove_results: CoVe results dictionary
        - cove_report: Formatted CoVe report text

    Raises:
        Exception: If CoVe pipeline fails
    """
    prior_contexts = {}
    if reference_context:
        # CoVe answers stage reads this key
        prior_contexts["cove_reference_files"] = reference_context

    try:
        log_task_event(
            "verify-cove",
            "cove",
            "start",
            "Starting Chain of Verification pipeline"
        )
    except Exception:
        pass

    cove_content, cove_results = run_cove_verification(
        content,
        "verify-cove",
        prior_contexts=prior_contexts if prior_contexts else None,
    )

    cove_report = format_cove_report(cove_results)

    return cove_content, cove_results, cove_report


def save_cove_outputs(
    cove_content: str,
    cove_results: Dict,
    cove_report: str,
    file: str,
    output: Optional[str],
    base_name: str
) -> Dict[str, str]:
    """
    Save CoVe outputs including regenerated document and report.

    Args:
        cove_content: Regenerated content (if issues found)
        cove_results: CoVe results dictionary
        cove_report: Formatted CoVe report text
        file: Original file path
        output: Custom output filename prefix (optional)
        base_name: Base name for output files

    Returns:
        Dictionary of extra files saved (report, regenerated doc if applicable)

    Raises:
        Exception: If saving fails
    """
    extra_files = {}

    # Save regenerated document if CoVe fixed issues
    if cove_results["cove"]["regenerated"]:
        regen_file = save_command_output(
            f"{output}_regenerated" if output else "verify_cove_regenerated",
            cove_content,
            "" if output else base_name,
            metadata={
                "Type": "CoVe Regenerated Document",
                "File": file,
                "Status": "[REGENERATED]",
                "Issues Fixed": cove_results["cove"]["issues"],
            },
        )
        extra_files["Regenerated document"] = regen_file

    # Save CoVe report with full dialogue
    cove_file = save_command_output(
        output if output else "verify_cove",
        cove_report,
        "" if output else base_name,
        metadata={
            "Type": "Chain of Verification",
            "File": file,
            "Status": (
                "[REGENERATED]"
                if cove_results["cove"]["regenerated"]
                else "[VERIFIED]"
            ),
            "Issues": "Fixed" if cove_results["cove"]["regenerated"] else "None",
        },
    )

    extra_files["CoVe report"] = cove_file

    return extra_files


def display_cove_results(cove_results: Dict, extra_files: Dict) -> None:
    """
    Display CoVe verification results to user.

    Args:
        cove_results: CoVe results dictionary
        extra_files: Dictionary of saved files
    """
    status = (
        "[REGENERATED]" if cove_results["cove"]["regenerated"] else "[VERIFIED]"
    )
    click.echo(f"\n{status} Chain of Verification complete")
    click.echo(f"   - Analysis: {extra_files['CoVe report']}")
    if cove_results["cove"]["regenerated"]:
        click.echo(f"   - Regenerated: {extra_files['Regenerated document']}")
    else:
        click.echo("   - No rewrite needed (document verified as accurate)")

    # Stage completion event
    try:
        log_task_event(
            "verify-cove",
            "cove",
            "end",
            f"CoVe complete: status={'regenerated' if cove_results['cove']['regenerated'] else 'verified'}",
            {
                "regenerated": cove_results["cove"]["regenerated"],
                "analysis_file": extra_files.get("CoVe report"),
                "regenerated_file": extra_files.get("Regenerated document"),
            },
        )
    except Exception:
        pass
