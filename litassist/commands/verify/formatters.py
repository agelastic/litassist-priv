"""
Report formatting and validation helpers for verification command.

This module provides helper functions for formatting verification reports
and validating reasoning traces.
"""

import re
from litassist.utils.legal_reasoning import LegalReasoningTrace


def format_citation_report(verified: list, unverified: list, total_found: int) -> str:
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


def parse_soundness_issues(soundness_result: str) -> list:
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


def format_soundness_report(issues: list, full_response: str) -> str:
    """Format legal soundness verification report (content only, no headers)."""
    lines = [
        f"**Issues identified**: {len(issues)}",
        f"**Australian law compliance**: {'[VERIFIED]' if not issues else '[WARNING] Issues found'}",
        "",
    ]
    # Append the LLM's full response (which already includes its own "## Issues Found" section)
    lines.append(full_response.strip())
    return "\n".join(lines)


def verify_reasoning_trace(trace: LegalReasoningTrace) -> dict:
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
