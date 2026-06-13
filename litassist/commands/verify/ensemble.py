"""
Multi-model cross-check stage for the verify command (ROADMAP P1-12).

A fixed three-model panel critiques a document independently, then a separate
arbiter model compares the critiques and emits a structured, fail-closed report.
This stage is READ-ONLY: it compares findings and flags disagreement, it never
rewrites the document (unlike the CoVe chain in verification_chain.py).
"""

import os
import re
from typing import Optional

import click

from litassist.llm.factory import LLMClientFactory
from litassist.llm.cost import estimate_call_cost
from litassist.logging import save_command_output, log_task_event
from litassist.prompts import PROMPTS
from litassist.utils.formatting import (
    verifying_message,
    warning_message,
    stats_message,
    cost_message,
)

# Fixed panel pinned by ROADMAP P1-12 for reasoning diversity. The arbiter is a
# separate, non-panel model so it never adjudicates its own critique.
PANEL_ROLES = ("crosscheck-claude", "crosscheck-gpt5", "crosscheck-o3")
ARBITER_ROLE = "crosscheck-arbiter"

# The arbiter's four contract sections, in the order the prompt requires.
_MARKERS = (
    "=== AGREEMENT ===",
    "=== DISAGREEMENTS ===",
    "=== FLAGGED FOR HUMAN REVIEW ===",
    "=== CONFIDENCE ===",
)
_SECTION_RE = re.compile(
    r"=== AGREEMENT ===(?P<agreement>.*?)"
    r"=== DISAGREEMENTS ===(?P<disagreements>.*?)"
    r"=== FLAGGED FOR HUMAN REVIEW ===(?P<flagged>.*?)"
    r"=== CONFIDENCE ===(?P<confidence>.*)\Z",
    re.DOTALL,
)

# Single machine-readable line inside DISAGREEMENTS that drives the warning,
# mirroring the CoVe VERDICT parse in verification_chain.py.
_LEVEL_RE = re.compile(
    r"^\s*DISAGREEMENT LEVEL:\s*(NONE|LOW|MEDIUM|HIGH)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def parse_arbiter_report(text: str) -> tuple[dict, str]:
    """
    Parse the arbiter report into its four sections plus the disagreement level.

    Fail-closed: a report missing any of the four section markers (in order), or
    missing/malformed the DISAGREEMENT LEVEL line, raises ValueError. There is no
    fallback parsing - a broken contract is a stage error, distinct from a
    well-formed HIGH finding (which only warns).

    Returns:
        (sections, level) where sections has keys agreement/disagreements/
        flagged/confidence (each stripped) and level is one of
        NONE/LOW/MEDIUM/HIGH (upper-cased).
    """
    # Require each section marker exactly once. Without this an ordered-subsequence
    # match could pick a later, lower DISAGREEMENT LEVEL and silently mask an
    # earlier HIGH one (the signal this stage exists to surface).
    for marker in _MARKERS:
        if text.count(marker) != 1:
            raise ValueError(
                f"Arbiter report must contain exactly one '{marker}'."
            )

    match = _SECTION_RE.search(text)
    if not match:
        raise ValueError(
            "Arbiter report missing one or more of the required sections "
            "(=== AGREEMENT ===, === DISAGREEMENTS ===, "
            "=== FLAGGED FOR HUMAN REVIEW ===, === CONFIDENCE ===) in order."
        )
    sections = {k: v.strip() for k, v in match.groupdict().items()}

    level_matches = _LEVEL_RE.findall(sections["disagreements"])
    if len(level_matches) != 1:
        raise ValueError(
            "Arbiter report must have exactly one 'DISAGREEMENT LEVEL: "
            "NONE|LOW|MEDIUM|HIGH' line in the DISAGREEMENTS section."
        )
    return sections, level_matches[0].upper()


def _echo_cost(label: str, model: str, usage: dict) -> None:
    """Print a [COST] banner for one LLM call."""
    cost = estimate_call_cost(model, usage)
    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)
    click.echo(
        cost_message(
            f"{label} ({model}): in {prompt_tokens:,} tok / "
            f"out {completion_tokens:,} tok ~= ${cost:.4f}"
        )
    )


def _log(stage_event: str, message: str, details: Optional[dict] = None) -> None:
    try:
        if details is None:
            log_task_event("verify", "crosscheck", stage_event, message)
        else:
            log_task_event("verify", "crosscheck", stage_event, message, details)
    except Exception:
        pass


def run_cross_check(
    content: str,
    file: str,
    reference_context: Optional[str] = None,
    output: Optional[str] = None,
) -> dict:
    """
    Run the multi-model cross-check stage on a document.

    Args:
        content: The document text (the original as-read content - the panel
            always reviews the user's document, never a regenerated version).
        file: Original file path (for output naming and metadata).
        reference_context: Optional reference-file context shown to every panel
            member identically.
        output: Optional custom output filename prefix.

    Returns:
        dict with crosscheck_file, disagreement_level, total_usage, total_cost_usd.
    """
    reference_context = reference_context or ""
    context = reference_context.strip() or "(no reference documents provided)"

    click.echo(verifying_message("Starting multi-model cross-check..."))
    _log("start", "Starting multi-model cross-check")

    # 1. Panel: three independent critiques of the same document.
    panel_results = []
    for role in PANEL_ROLES:
        client = LLMClientFactory.for_command(role)
        messages = [
            {"role": "system", "content": PROMPTS.get("verification.system_prompt")},
            {
                "role": "user",
                "content": PROMPTS.get(
                    "verification.crosscheck.panel_review",
                    context=context,
                    content=content,
                ),
            },
        ]
        _log("llm_call", f"Sending panel review to {role}", {"model": client.model})
        review, usage = client.complete(messages, skip_citation_verification=True)
        _log("llm_response", f"Panel review received from {role}", {"model": client.model})
        _echo_cost(role, client.model, usage)
        panel_results.append(
            {"role": role, "model": client.model, "review": review, "usage": usage}
        )

    # 2. Arbiter: compare the three critiques.
    panel_block = "\n\n".join(
        f"=== PANEL REVIEW: {r['model']} ===\n{r['review']}\n"
        f"=== END PANEL REVIEW: {r['model']} ==="
        for r in panel_results
    )
    arbiter_client = LLMClientFactory.for_command(ARBITER_ROLE)
    arbiter_messages = [
        {
            "role": "user",
            "content": PROMPTS.get(
                "verification.crosscheck.arbiter_report", panel_reviews=panel_block
            ),
        }
    ]
    _log("llm_call", "Sending arbiter comparison", {"model": arbiter_client.model})
    arbiter_report, arbiter_usage = arbiter_client.complete(
        arbiter_messages, skip_citation_verification=True
    )
    _log("llm_response", "Arbiter report received", {"model": arbiter_client.model})
    _echo_cost(ARBITER_ROLE, arbiter_client.model, arbiter_usage)

    sections, level = parse_arbiter_report(arbiter_report)

    # 3. Report: arbiter output verbatim plus the panel critiques as an audit appendix.
    appendix = "\n\n".join(
        f"### {r['role']} ({r['model']})\n\n{r['review']}" for r in panel_results
    )
    report = (
        f"{arbiter_report}\n\n"
        f"## Appendix: Panel Critiques\n\n{appendix}\n"
    )

    base_name = os.path.splitext(file)[0]
    crosscheck_file = save_command_output(
        f"{output}_crosscheck" if output else "verify_crosscheck",
        report,
        "" if output else os.path.basename(base_name),
        metadata={
            "Type": "Multi-Model Cross-Check",
            "File": file,
            "Panel": ", ".join(r["model"] for r in panel_results),
            "Arbiter": arbiter_client.model,
            "Disagreement Level": level,
            "Status": "[WARNING]" if level == "HIGH" else "[REVIEWED]",
        },
    )

    # 4. Totals, cost, and finding surfacing.
    all_calls = [(r["model"], r["usage"]) for r in panel_results] + [
        (arbiter_client.model, arbiter_usage)
    ]
    total_tokens = sum(u.get("total_tokens", 0) for _, u in all_calls)
    total_cost = sum(estimate_call_cost(m, u) for m, u in all_calls)

    click.echo("\n[REVIEWED] Multi-model cross-check complete")
    click.echo(f"   - Disagreement level: {level}")
    click.echo(f"   - Details: {crosscheck_file}")
    click.echo(f"   - Arbiter confidence: {sections['confidence']}")
    click.echo(stats_message(f"Cross-check total tokens used: {total_tokens:,}"))
    click.echo(cost_message(f"Cross-check total: ${total_cost:.4f} ({total_tokens:,} tokens)"))
    if level == "HIGH":
        click.echo(
            warning_message(
                "HIGH disagreement between models - human review recommended"
            )
        )

    _log("end", f"Multi-model cross-check complete - disagreement level {level}")

    return {
        "crosscheck_file": crosscheck_file,
        "disagreement_level": level,
        "total_usage": {"total_tokens": total_tokens},
        "total_cost_usd": total_cost,
    }
