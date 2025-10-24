"""
Legal soundness verification for verify command.

This module handles verification of legal accuracy and Australian law compliance
using LLM-based analysis with automatic token limit backoff.
"""

import os
import click
from litassist.llm.factory import LLMClientFactory
from litassist.logging import save_command_output, log_task_event
from litassist.utils.formatting import verifying_message, success_message, warning_message
from litassist.citation_patterns import extract_citations
from litassist.citation_context import fetch_citation_context
from .formatters import parse_soundness_issues, format_soundness_report


def verify_soundness(
    content: str,
    file: str,
    case_content: dict = None,
    reference_context: str = None,
    citation_report: str = None,
    reasoning_response: str = None,
    output: str = None
) -> tuple:
    """
    Verify legal soundness and Australian law compliance.

    Args:
        content: Document content to verify
        file: Original file path
        case_content: Dict of fetched case content
        reference_context: Optional reference files context
        citation_report: Optional citation report for context
        reasoning_response: Optional reasoning trace for context
        output: Optional custom output filename prefix

    Returns:
        tuple: (soundness_result, issues, soundness_file)
    """
    click.echo(verifying_message("Starting legal soundness check..."))

    try:
        log_task_event(
            "verify",
            "soundness",
            "start",
            "Starting legal soundness verification"
        )
    except Exception:
        pass

    # If case content wasn't provided, fetch it now
    if not case_content:
        all_citations = extract_citations(content)
        if all_citations:
            click.echo(verifying_message(f"Fetching content for {len(all_citations)} citations..."))
            case_content = fetch_citation_context(all_citations)
            if case_content:
                click.echo(success_message(f"Fetched content for {len(case_content)} cases"))

    client = LLMClientFactory.for_command("verify-soundness")

    # Try with full context, implement backoff if prompt overload
    soundness_result = None
    soundness_model = None
    cases_to_include = list(case_content.items()) if case_content else []
    attempts = 0

    while soundness_result is None and attempts < 5:
        try:
            # Build citation context with case content for this attempt
            full_citation_context = ""
            if cases_to_include:
                full_citation_context = "## Full Legal Documents\n\n"
                for citation, full_text in cases_to_include:
                    full_citation_context += f"=== {citation} ===\n\n{full_text}\n\n"

            # Add reference files to citation context
            if reference_context:
                full_citation_context += "\n\n## Reference Documents\n\n"
                full_citation_context += reference_context

            if citation_report:
                full_citation_context += "\n\n## Citation Verification Summary\n" + citation_report

            # Pass both citation and reasoning contexts if available
            try:
                log_task_event(
                    "verify",
                    "soundness",
                    "llm_call",
                    "Sending soundness verification prompt to LLM",
                    {"model": client.model}
                )
            except Exception:
                pass

            soundness_result, soundness_model = client.verify(
                content,
                citation_context=full_citation_context if full_citation_context else None,
                reasoning_context=reasoning_response,
            )

            if soundness_result:
                try:
                    log_task_event(
                        "verify",
                        "soundness",
                        "llm_response",
                        "Soundness LLM response received",
                        {"model": soundness_model}
                    )
                except Exception:
                    pass
        except Exception as e:
            error_str = str(e).lower()
            # Check for token/context limit errors
            if any(x in error_str for x in ['token', 'context', 'length', 'too long', 'maximum']):
                if cases_to_include:
                    # Find and drop the largest case
                    largest_idx = max(range(len(cases_to_include)),
                                    key=lambda i: len(cases_to_include[i][1]))
                    dropped_case = cases_to_include.pop(largest_idx)
                    click.echo(warning_message(
                        f"Prompt exceeded token limit. Dropping largest case: {dropped_case[0]}"
                    ))
                    attempts += 1
                else:
                    # No more cases to drop, re-raise the error
                    raise
            else:
                # Not a token limit error, re-raise
                raise

    if soundness_result is None:
        raise click.ClickException("Failed to get soundness verification after dropping all case content")

    # Parse and format results
    issues = parse_soundness_issues(soundness_result)
    soundness_report = format_soundness_report(issues, soundness_result)

    # Save soundness report
    base_name = os.path.splitext(file)[0]
    soundness_file = save_command_output(
        f"{output}_soundness" if output else "verify_soundness",
        soundness_report,
        "" if output else os.path.basename(base_name),
        metadata={
            "Type": "Legal Soundness",
            "File": file,
            "Model": soundness_model,
            "Issues Found": str(len(issues)),
            "Compliance": "[VERIFIED]"
            if not issues
            else "[WARNING] Issues found",
            "Status": "[VERIFIED]" if not issues else "[WARNING]",
        },
    )

    # Display results
    status = "[VERIFIED]" if not issues else "[WARNING]"
    click.echo(f"\n{status} Legal soundness check complete")
    click.echo(f"   - {len(issues)} issues identified")
    click.echo(f"   - Details: {soundness_file}")

    try:
        log_task_event(
            "verify",
            "soundness",
            "end",
            f"Legal soundness check complete - {len(issues)} issues found"
        )
    except Exception:
        pass

    return soundness_result, issues, soundness_file
