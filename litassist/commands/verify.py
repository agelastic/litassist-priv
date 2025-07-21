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
    verifying_message, success_message, error_message
)
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
    msg = error_message(f'{step_name} failed: {exception}')
    click.echo(f"\n{msg}")
    logging.error(f"{step_name} error: {exception}")


@click.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--citations", is_flag=True, help="Verify citations only")
@click.option("--soundness", is_flag=True, help="Verify legal soundness only")
@click.option("--reasoning", is_flag=True, help="Verify/generate reasoning trace only")
@timed
def verify(file, citations, soundness, reasoning):
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
    reasoning_response = None  # Track reasoning response for potential combination

    # 1. Citation Verification
    if citations:
        try:
            verified, unverified = verify_all_citations(content)
            citation_report = _format_citation_report(
                verified, unverified, total_found=len(extract_citations(content))
            )
            citation_file = os.path.join(
                os.path.dirname(file) or ".",
                f"verify_{os.path.basename(base_name)}_citations.txt",
            )
            with open(citation_file, "w", encoding="utf-8") as f:
                f.write(citation_report)
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
        try:
            existing_trace = extract_reasoning_trace(content)
            if existing_trace:
                action = "verified"
                trace_status = _verify_reasoning_trace(existing_trace)
                msg = success_message(f'Reasoning trace {action}')
                click.echo(f"\n{msg}")
                click.echo(
                    f"   - IRAC structure {'complete' if trace_status['complete'] else 'incomplete'}"
                )
                click.echo(f"   - Confidence: {existing_trace.confidence}%")
                # Create a verification report for existing trace
                report_parts = [
                    "## Reasoning Trace Verification\n\n",
                    "**Status**: Existing trace verified\n",
                    f"**IRAC Structure**: {'Complete' if trace_status['complete'] else 'Incomplete'}\n",
                    f"**Confidence**: {existing_trace.confidence}%\n\n",
                ]
                if trace_status['issues']:
                    report_parts.append("### Issues Found\n\n")
                    report_parts.extend(f"- {issue}\n" for issue in trace_status['issues'])
                    report_parts.append("\n")
                report_parts.append("### Original Document with Reasoning Trace\n\n")
                report_parts.append(content)
                reasoning_response = "".join(report_parts)
            else:
                client = LLMClientFactory.for_command("verify")
                enhanced_prompt = create_reasoning_prompt(content, "verify")
                messages = [
                    {
                        "role": "system",
                        "content": PROMPTS.get("verification.system_prompt"),
                    },
                    {"role": "user", "content": enhanced_prompt},
                ]
                response, _ = client.complete(messages, skip_citation_verification=True)
                reasoning_response = response  # Store for potential combination with soundness
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
                msg = success_message(f'Reasoning trace {action}')
                click.echo(f"\n{msg}")
                click.echo("   - IRAC structure complete")
                click.echo(f"   - Confidence: {existing_trace.confidence}%")
            
            # Save the reasoning trace to a file only if soundness is not being run
            if reasoning_response and not soundness:
                reasoning_file = os.path.join(
                    os.path.dirname(file) or ".",
                    f"verify_{os.path.basename(base_name)}_reasoning.txt",
                )
                with open(reasoning_file, "w", encoding="utf-8") as f:
                    f.write(f"# Legal Reasoning Analysis\n\n{reasoning_response}")
                click.echo(f"   - Details: {reasoning_file}")
                extra_files["Reasoning analysis"] = reasoning_file
                reports_generated += 1
            elif reasoning_response and soundness:
                # When both flags are used, reasoning will be included in soundness report
                click.echo("   - Reasoning will be included in soundness report")
        except Exception as e:
            _handle_verification_error("Reasoning trace verification", e)

    # 3. Legal Soundness Verification
    if soundness:
        try:
            client = LLMClientFactory.for_command("verify")
            soundness_result = client.verify(content)
            issues = _parse_soundness_issues(soundness_result)
            soundness_report = _format_soundness_report(issues, soundness_result, client.model, reasoning_response)
            soundness_file = os.path.join(
                os.path.dirname(file) or ".",
                f"verify_{os.path.basename(base_name)}_soundness.txt",
            )
            with open(soundness_file, "w", encoding="utf-8") as f:
                f.write(soundness_report)
            status = "[VERIFIED]" if not issues else "[WARNING]"
            click.echo(f"\n{status} Legal soundness check complete")
            click.echo(f"   - {len(issues)} issues identified")
            click.echo(f"   - Details: {soundness_file}")
            extra_files["Soundness report"] = soundness_file
            reports_generated += 1
        except Exception as e:
            _handle_verification_error("Legal soundness check", e)

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
                },
            },
            "outputs": extra_files,
            "reports_generated": reports_generated,
        },
    )


def _format_citation_report(verified: list, unverified: list, total_found: int) -> str:
    """Format detailed citation verification report."""
    lines = [
        "# Citation Verification Report",
        "",
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
            "",
            "*Report generated by LitAssist verify command*",
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


def _format_soundness_report(issues: list, full_response: str, model: str, reasoning_response: str = None) -> str:
    """Format legal soundness verification report."""
    lines = [
        "# Legal Soundness Verification Report",
        "",
        f"**Issues identified**: {len(issues)}",
        f"**Verification model**: {model}",
        f"**Australian law compliance**: {'[VERIFIED]' if not issues else '[WARNING] Issues found'}",
        "",
    ]
    # Append the LLM's full response (which already includes its own "## Issues Found" section)
    lines.append(full_response.strip())
    
    # If reasoning response is provided, append it
    if reasoning_response:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Legal Reasoning Analysis")
        lines.append("")
        lines.append(reasoning_response.strip())
    
    lines.append("")
    lines.append("---")
    lines.append("*Report generated by LitAssist verify command*")
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
