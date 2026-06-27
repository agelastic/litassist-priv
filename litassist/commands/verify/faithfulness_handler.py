"""
Faithfulness verification for verify command (P-FAITH).

Checks whether the document's factual claims are grounded in the supplied source
documents (the --reference files). Saves a per-claim report and, when claims are
flagged, a separate corrective addendum. The original document is never modified.
"""

import os
from typing import Optional
import click
from litassist.logging import save_command_output, log_task_event
from litassist.utils.formatting import verifying_message
from litassist.verification_chain import (
    run_faithfulness_verification,
    format_faithfulness_report,
)


def verify_faithfulness(
    content: str,
    file: str,
    sources_context: str,
    output: Optional[str] = None,
) -> tuple:
    """
    Check whether the document's claims are grounded in the source documents.

    Args:
        content: Document content to verify
        file: Original file path
        sources_context: The --reference source documents the claims are checked against
        output: Optional custom output filename prefix

    Returns:
        tuple: (faithfulness_data, score, report_file, addendum_file)
    """
    click.echo(verifying_message("Starting faithfulness check..."))

    try:
        log_task_event(
            "verify", "faithfulness", "start", "Starting faithfulness verification"
        )
    except Exception:
        pass

    _, results = run_faithfulness_verification(content, sources_context, "verify")
    data = results["faithfulness"]
    report = format_faithfulness_report(results)

    base_name = os.path.splitext(file)[0]
    status = "[VERIFIED]" if data["flagged_count"] == 0 else "[WARNING]"

    report_file = save_command_output(
        f"{output}_faithfulness" if output else "verify_faithfulness",
        report,
        "" if output else os.path.basename(base_name),
        metadata={
            "Type": "Faithfulness",
            "File": file,
            "Score": f"{data['score']}/100",
            "Flagged": str(data["flagged_count"]),
            "Status": status,
        },
    )

    # Save the corrective addendum as a SEPARATE file when one was produced. The
    # original document is never rewritten.
    addendum_file = None
    if data.get("addendum"):
        addendum_file = save_command_output(
            f"{output}_faithfulness_addendum"
            if output
            else "verify_faithfulness_addendum",
            data["addendum"],
            "" if output else os.path.basename(base_name),
            metadata={
                "Type": "Faithfulness Addendum",
                "File": file,
                "Status": "[ADDENDUM]",
            },
        )

    click.echo(f"\n{status} Faithfulness check complete")
    click.echo(f"   - Score: {data['score']}/100")
    click.echo(f"   - {data['flagged_count']} claim(s) flagged")
    click.echo(f"   - Details: {report_file}")
    if addendum_file:
        click.echo(f"   - Addendum: {addendum_file}")

    try:
        log_task_event(
            "verify",
            "faithfulness",
            "end",
            f"Faithfulness check complete - score {data['score']}, {data['flagged_count']} flagged",
        )
    except Exception:
        pass

    return data, data["score"], report_file, addendum_file
