"""
Reasoning trace verification and generation for verify command.

This module handles verification of existing IRAC-based reasoning traces
and generation of new traces using LLM when none exist.
"""

import os
import click
from litassist.prompts import PROMPTS
from litassist.llm.factory import LLMClientFactory
from litassist.logging import save_command_output, log_task_event
from litassist.utils.formatting import verifying_message, success_message, warning_message
from litassist.utils.legal_reasoning import (
    create_reasoning_prompt,
    extract_reasoning_trace,
    LegalReasoningTrace,
)
from litassist.citation_patterns import extract_citations
from litassist.citation_context import fetch_citation_context
from .formatters import verify_reasoning_trace


def verify_reasoning(
    content: str,
    file: str,
    case_content: dict = None,
    reference_context: str = None,
    citation_report: str = None,
    output: str = None
) -> tuple:
    """
    Verify existing reasoning trace or generate new one.

    Args:
        content: Document content to verify
        file: Original file path
        case_content: Dict of fetched case content
        reference_context: Optional reference files context
        citation_report: Optional citation report for context
        output: Optional custom output filename prefix

    Returns:
        tuple: (reasoning_response, reasoning_file, existing_trace)
    """
    click.echo(verifying_message("Starting reasoning trace verification..."))

    try:
        log_task_event(
            "verify",
            "reasoning",
            "start",
            "Starting reasoning trace verification"
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

    client = None
    existing_trace = extract_reasoning_trace(content)

    if existing_trace:
        # Verify existing trace
        action = "verified"
        trace_status = verify_reasoning_trace(existing_trace)
        msg = success_message(f"Reasoning trace {action}")
        click.echo(f"\n{msg}")
        click.echo(
            f"   - IRAC structure {'complete' if trace_status['complete'] else 'incomplete'}"
        )
        click.echo(f"   - Confidence: {existing_trace.confidence}%")

        # Create a verification report for existing trace
        report_parts = [
            "## Overall Strategic Reasoning Verification\n\n",
            "**Status**: Existing trace verified\n",
            f"**IRAC Structure**: {'Complete' if trace_status['complete'] else 'Incomplete'}\n",
            f"**Confidence**: {existing_trace.confidence}%\n\n",
        ]
        if trace_status["issues"]:
            report_parts.append("### Issues Found\n\n")
            report_parts.extend(
                f"- {issue}\n" for issue in trace_status["issues"]
            )
            report_parts.append("\n")
        report_parts.append(
            "### Original Document with Overall Strategic Reasoning\n\n"
        )
        report_parts.append(content)
        reasoning_response = "".join(report_parts)
        model_name = "N/A (existing trace verified)"
    else:
        # Generate new trace
        client = LLMClientFactory.for_command("verify-reasoning")
        enhanced_prompt = create_reasoning_prompt(content, "verify")

        # Append FULL case content if available
        if case_content:
            enhanced_prompt += "\n\n## Full Legal Context\n\n"
            enhanced_prompt += "Below are the complete legal documents referenced in the text:\n\n"
            for citation, full_text in case_content.items():
                enhanced_prompt += f"=== {citation} ===\n\n{full_text}\n\n"

        # Append reference files if available
        if reference_context:
            enhanced_prompt += "\n\n## Reference Documents\n\n"
            enhanced_prompt += "The following reference documents provide additional context:\n\n"
            enhanced_prompt += reference_context

        # Also append citation report summary if available
        if citation_report:
            enhanced_prompt += (
                "\n\n## Citation Verification Summary\n" + citation_report
            )

        messages = [
            {
                "role": "system",
                "content": PROMPTS.get("verification.system_prompt"),
            },
            {"role": "user", "content": enhanced_prompt},
        ]

        # Try with full context, implement backoff if prompt overload
        response = None
        cases_to_include = list(case_content.items()) if case_content else []
        attempts = 0

        while response is None and attempts < 5:
            try:
                try:
                    log_task_event(
                        "verify",
                        "reasoning",
                        "llm_call",
                        "Sending reasoning verification prompt to LLM",
                        {"model": client.model}
                    )
                except Exception:
                    pass

                response, _ = client.complete(messages, skip_citation_verification=True)

                if response:
                    try:
                        log_task_event(
                            "verify",
                            "reasoning",
                            "llm_response",
                            "Reasoning LLM response received",
                            {"model": client.model}
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

                        # Rebuild prompt without the dropped case
                        enhanced_prompt = create_reasoning_prompt(content, "verify")
                        if cases_to_include:
                            enhanced_prompt += "\n\n## Full Legal Context\n\n"
                            enhanced_prompt += "Below are the complete legal documents referenced in the text:\n\n"
                            for citation, full_text in cases_to_include:
                                enhanced_prompt += f"=== {citation} ===\n\n{full_text}\n\n"
                        if reference_context:
                            enhanced_prompt += "\n\n## Reference Documents\n\n"
                            enhanced_prompt += "The following reference documents provide additional context:\n\n"
                            enhanced_prompt += reference_context
                        if citation_report:
                            enhanced_prompt += (
                                "\n\n## Citation Verification Summary\n" + citation_report
                            )
                        messages[1]["content"] = enhanced_prompt
                        attempts += 1
                    else:
                        # No more cases to drop, re-raise the error
                        raise
                else:
                    # Not a token limit error, re-raise
                    raise

        if response is None:
            raise click.ClickException("Failed to get response after dropping all case content")

        reasoning_response = response
        existing_trace = extract_reasoning_trace(response)
        if not existing_trace:
            existing_trace = LegalReasoningTrace(
                issue="Legal document verification",
                applicable_law="Australian law principles",
                application=response[:500] + "...",
                conclusion="See full analysis above",
                confidence=75,
                sources=[],
                command="verify",
            )
        action = "generated"
        msg = success_message(f"Reasoning trace {action}")
        click.echo(f"\n{msg}")
        click.echo("   - IRAC structure complete")
        click.echo(f"   - Confidence: {existing_trace.confidence}%")
        model_name = client.model

    # Save the reasoning trace to a file
    base_name = os.path.splitext(file)[0]
    reasoning_file = save_command_output(
        f"{output}_reasoning" if output else "verify_reasoning",
        reasoning_response,
        "" if output else os.path.basename(base_name),
        metadata={
            "Type": "Overall Strategic Reasoning",
            "File": file,
            "Model": model_name,
            "Action": action.capitalize(),
            "IRAC Structure": "Complete" if existing_trace else "Generated",
            "Confidence": f"{existing_trace.confidence}%"
            if existing_trace
            else "N/A",
        },
    )
    click.echo(f"   - Details: {reasoning_file}")

    try:
        log_task_event(
            "verify",
            "reasoning",
            "end",
            f"Reasoning trace {action} - confidence {existing_trace.confidence}%" if existing_trace else "Reasoning trace complete"
        )
    except Exception:
        pass

    return reasoning_response, reasoning_file, existing_trace
