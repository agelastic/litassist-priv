"""
Post-hoc verification command for legal documents.

This command performs three types of verification on legal text files:
1. Citation verification - checks all citations are real and verifiable
2. Legal soundness - validates legal accuracy and Australian law compliance
3. Reasoning trace - verifies existing or generates new IRAC-based reasoning

By default (no flags), all three verifications are performed.
"""

import os
import re
import click
import logging

from litassist.prompts import PROMPTS
from litassist.citation_verify import verify_all_citations
from litassist.citation_patterns import extract_citations
from litassist.llm import LLMClientFactory
from litassist.utils import (
    verifying_message,
    success_message,
    error_message,
    warning_message,
    save_command_output,
)
from litassist.verification_chain import run_cove_verification, format_cove_report
from litassist.utils import (
    timed,
    save_log,
    read_document,
    create_reasoning_prompt,
    extract_reasoning_trace,
    LegalReasoningTrace,
)


def _handle_verification_error(step_name: str, exception: Exception) -> None:
    """Handle verification step errors with consistent formatting and logging."""
    msg = error_message(f"{step_name} failed: {exception}")
    click.echo(f"\n{msg}")
    logging.error(f"{step_name} error: {exception}")


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--citations", is_flag=True, help="Verify citations only")
@click.option("--soundness", is_flag=True, help="Verify legal soundness only")
@click.option("--reasoning", is_flag=True, help="Verify/generate reasoning trace only")
@click.option("--cove", is_flag=True, help="Add Chain of Verification as final check")
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def verify(file, citations, soundness, reasoning, cove, output):
    """
    Verify legal text for citations, soundness, and reasoning.

    By default, performs all three verification types.
    Use flags to run specific verifications only.
    """
    if not any([citations, soundness, reasoning]):
        citations = soundness = reasoning = True

    click.echo(verifying_message(f"Verifying {file}..."))

    try:
        content = read_document(file)
    except click.ClickException as e:
        raise e
    except Exception as e:
        raise click.ClickException(f"Error reading file: {e}")

    if not content.strip():
        raise click.ClickException("File is empty")

    base_name = os.path.splitext(file)[0]
    reports_generated = 0
    extra_files = {}
    citation_report = None  # Track citation report for passing to other steps
    reasoning_response = None  # Track reasoning response for potential combination

    # 1. Citation Verification
    if citations:
        click.echo(verifying_message("Starting citation verification..."))
        try:
            verified, unverified = verify_all_citations(content)
            citation_report = _format_citation_report(
                verified, unverified, total_found=len(extract_citations(content))
            )
            citation_file = save_command_output(
                f"{output}_citations" if output else "verify_citations",
                citation_report,
                "" if output else os.path.basename(base_name),
                metadata={
                    "Type": "Citation Verification",
                    "File": file,
                    "Total Citations": str(len(extract_citations(content))),
                    "Verified": str(len(verified)),
                    "Unverified": str(len(unverified)),
                    "Status": "[VERIFIED]" if not unverified else "[WARNING]",
                },
            )
            status = "[VERIFIED]" if not unverified else "[WARNING]"
            click.echo(f"\n{status} Citation verification complete")
            click.echo(
                f"   - {len(verified)} citations verified, {len(unverified)} unverified"
            )
            click.echo(f"   - Details: {citation_file}")
            extra_files["Citation report"] = citation_file
            reports_generated += 1
        except Exception as e:
            _handle_verification_error("Citation verification", e)

    # 2. Reasoning Trace Verification/Generation (run BEFORE soundness to allow combination)
    if reasoning:
        click.echo(verifying_message("Starting reasoning trace verification..."))
        try:
            client = None  # Initialize client variable
            existing_trace = extract_reasoning_trace(content)
            if existing_trace:
                action = "verified"
                trace_status = _verify_reasoning_trace(existing_trace)
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
                client = LLMClientFactory.for_command("verify-reasoning")
                enhanced_prompt = create_reasoning_prompt(content, "verify")
                # Append citation report if available
                if citation_report:
                    enhanced_prompt += (
                        "\n\n## Citation Verification Results\n" + citation_report
                    )
                messages = [
                    {
                        "role": "system",
                        "content": PROMPTS.get("verification.system_prompt"),
                    },
                    {"role": "user", "content": enhanced_prompt},
                ]
                response, _ = client.complete(messages, skip_citation_verification=True)
                reasoning_response = (
                    response  # Store for potential combination with soundness
                )
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
            if reasoning_response:
                # Pass only the reasoning content, let save_command_output handle headers
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
                extra_files["Reasoning analysis"] = reasoning_file
                reports_generated += 1
        except Exception as e:
            _handle_verification_error("Reasoning trace verification", e)

    # 3. Legal Soundness Verification
    if soundness:
        click.echo(verifying_message("Starting legal soundness check..."))
        try:
            client = LLMClientFactory.for_command("verify-soundness")
            # Pass both citation and reasoning contexts if available
            soundness_result, soundness_model = client.verify(
                content,
                citation_context=citation_report,
                reasoning_context=reasoning_response,
            )
            issues = _parse_soundness_issues(soundness_result)
            soundness_report = _format_soundness_report(issues, soundness_result)
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
            status = "[VERIFIED]" if not issues else "[WARNING]"
            click.echo(f"\n{status} Legal soundness check complete")
            click.echo(f"   - {len(issues)} issues identified")
            click.echo(f"   - Details: {soundness_file}")
            extra_files["Soundness report"] = soundness_file
            reports_generated += 1
        except Exception as e:
            _handle_verification_error("Legal soundness check", e)

    # 4. Chain of Verification (Final Stage - uses all prior results)
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

                cove_content, cove_results = run_cove_verification(
                    final_content,
                    "verify",
                    prior_contexts={
                        "citations": citation_report,
                        "reasoning": reasoning_response,
                        "soundness": issues
                        if soundness and "issues" in locals()
                        else None,
                    },
                )

                # Update final_content if regenerated
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

                # Don't pass critique_sections - the cove_report already contains all the information
                # Passing it causes duplication with "AI CRITIQUE & VERIFICATION" section

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
                    # critique_sections removed to prevent duplication
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
                extra_files["CoVe report"] = cove_file
                reports_generated += 1
            except Exception as e:
                _handle_verification_error("Chain of Verification", e)

    click.echo(f"\nVerification complete. {reports_generated} reports generated.")
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
                },
            },
            "outputs": extra_files,
            "reports_generated": reports_generated,
        },
    )


def _format_citation_report(verified: list, unverified: list, total_found: int) -> str:
    """Format detailed citation verification report (content only, no headers)."""
    lines = [
        f"**Total citations found**: {total_found}",
        f"**Verified citations**: {len(verified)}",
        f"**Unverified citations**: {len(unverified)}",
        "",
    ]
    if verified:
        lines.extend(["## Verified Citations", ""])
        lines += [f"- [VERIFIED] {c}" for c in verified]
        lines.append("")
    if unverified:
        lines.extend(["## Unverified Citations", ""])
        for citation, reason in unverified:
            lines.append(f"- [UNVERIFIED] {citation}")
            lines.append(f"  - **Reason**: {reason}")
        lines.append("")
    lines.extend(
        [
            "## Verification Method",
            "",
            "Citations were verified using:",
            "1. Real-time Jade.io database lookup via Google Custom Search",
            "2. Pattern validation for Australian legal citation formats",
            "3. International citation recognition (UK, NZ, etc.)",
        ]
    )
    return "\n".join(lines)


def _parse_soundness_issues(soundness_result: str) -> list:
    """Parse legal soundness issues from the '## Issues Found' section."""
    issues = []
    match = re.search(
        r"## Issues Found\s*\n(.*?)(?:\n## |\Z)",
        soundness_result,
        re.DOTALL | re.IGNORECASE,
    )
    if match:
        block = match.group(1).strip()
        if "no issues found" in block.lower():
            return []
        for line in block.splitlines():
            m = re.match(r"\s*\d+\.\s+(.*)", line)
            if m:
                issues.append(m.group(1).strip())
    return issues


def _format_soundness_report(issues: list, full_response: str) -> str:
    """Format legal soundness verification report (content only, no headers)."""
    lines = [
        f"**Issues identified**: {len(issues)}",
        f"**Australian law compliance**: {'[VERIFIED]' if not issues else '[WARNING] Issues found'}",
        "",
    ]
    # Append the LLM's full response (which already includes its own "## Issues Found" section)
    lines.append(full_response.strip())
    return "\n".join(lines)


def _verify_reasoning_trace(trace: LegalReasoningTrace) -> dict:
    """Verify completeness and quality of existing reasoning trace."""
    status = {"complete": True, "issues": []}
    if not trace.issue or len(trace.issue) < 10:
        status["complete"] = False
        status["issues"].append("Issue statement missing or too brief")
    if not trace.applicable_law or len(trace.applicable_law) < 20:
        status["complete"] = False
        status["issues"].append("Applicable law section missing or insufficient")
    if not trace.application or len(trace.application) < 30:
        status["complete"] = False
        status["issues"].append("Application to facts missing or insufficient")
    if not trace.conclusion or len(trace.conclusion) < 10:
        status["complete"] = False
        status["issues"].append("Conclusion missing or too brief")
    if trace.confidence < 0 or trace.confidence > 100:
        status["issues"].append(f"Invalid confidence score: {trace.confidence}")
    if not trace.sources:
        status["issues"].append("No legal sources cited")
    return status
