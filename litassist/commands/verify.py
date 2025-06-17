"""
Verify command for LitAssist: post-hoc quality checks for legal documents.

Performs citation accuracy, legal soundness, and reasoning transparency checks
on any legal text file. Outputs detailed reports for each check and logs all
operations using the existing logging infrastructure.

Usage:
    litassist verify FILE_PATH [--citations] [--soundness] [--reasoning]

If no flags are provided, all checks are performed.
"""

import os
import click
import logging
from datetime import datetime

from litassist.config import CONFIG
from litassist.citation_verify import verify_all_citations
from litassist.llm import LLMClientFactory
from litassist.utils import LegalReasoningTrace, extract_reasoning_trace

# Helper: get logger
logger = CONFIG.get_logger(__name__)


@click.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False))
@click.option("--citations", is_flag=True, help="Check citation accuracy only.")
@click.option("--soundness", is_flag=True, help="Check legal soundness only.")
@click.option("--reasoning", is_flag=True, help="Check reasoning transparency only.")
@click.pass_context
def verify(ctx, file_path, citations, soundness, reasoning):
    """
    Quality-check a legal document for citations, legal soundness, and reasoning trace.
    """
    # Determine which checks to run
    run_citations = citations or not (citations or soundness or reasoning)
    run_soundness = soundness or not (citations or soundness or reasoning)
    run_reasoning = reasoning or not (citations or soundness or reasoning)

    # Read file
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Prepare output paths
    base = os.path.splitext(os.path.basename(file_path))[0]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir = CONFIG.outputs_dir if hasattr(CONFIG, "outputs_dir") else "outputs"
    os.makedirs(outdir, exist_ok=True)

    # Minimal console output
    click.echo(f"Verifying {file_path}...")

    # 1. Citation check
    if run_citations:
        logger.info("Starting citation verification")
        verified, unverified = verify_all_citations(text)
        # Format report
        report_lines = []
        report_lines.append("Citation Verification Report\n")
        report_lines.append(f"Total citations found: {len(verified) + len(unverified)}")
        report_lines.append(f"Verified citations: {len(verified)}")
        report_lines.append(f"Unverified citations: {len(unverified)}\n")
        if verified:
            report_lines.append("Verified citations:")
            for c in verified:
                report_lines.append(f"  - {c}")
        if unverified:
            report_lines.append("\nUnverified citations:")
            for c, reason in unverified:
                report_lines.append(f"  - {c}  [Reason: {reason}]")
        citations_report = "\n".join(report_lines)
        citations_path = os.path.join(outdir, f"{base}_{timestamp}_citations.txt")
        with open(citations_path, "w", encoding="utf-8") as f:
            f.write(citations_report)
        logger.info(f"Citation verification complete: {citations_path}")
        click.echo(f"  Citations: done ({citations_path})")

    # 2. Legal soundness check
    if run_soundness:
        logger.info("Starting legal soundness verification")
        llm = LLMClientFactory.create()
        prompt = CONFIG.get_prompt("verification.heavy_verification")
        soundness_report = llm.verify_with_level(text, level="heavy", prompt=prompt)
        soundness_path = os.path.join(outdir, f"{base}_{timestamp}_soundness.txt")
        with open(soundness_path, "w", encoding="utf-8") as f:
            f.write(soundness_report)
        logger.info(f"Legal soundness verification complete: {soundness_path}")
        click.echo(f"  Soundness: done ({soundness_path})")

    # 3. Reasoning trace check/generation
    if run_reasoning:
        logger.info("Starting reasoning trace verification")
        # Try to extract existing reasoning trace
        trace = extract_reasoning_trace(text)
        if not trace:
            logger.info("No reasoning trace found, generating new trace")
            llm = LLMClientFactory.create()
            prompt = CONFIG.get_prompt("verification.heavy_verification")
            trace = llm.verify_with_level(text, level="heavy", prompt=prompt)
            # Optionally, parse/structure as LegalReasoningTrace
        else:
            logger.info("Existing reasoning trace found")
        reasoning_path = os.path.join(outdir, f"{base}_{timestamp}_reasoning.txt")
        with open(reasoning_path, "w", encoding="utf-8") as f:
            f.write(str(trace))
        logger.info(f"Reasoning trace verification complete: {reasoning_path}")
        click.echo(f"  Reasoning: done ({reasoning_path})")

    logger.info("Verification complete for %s", file_path)
    click.echo("Verification complete.")
