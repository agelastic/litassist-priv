"""
File handling functions for strategy command.

This module handles saving strategy outputs and related files.
"""

from typing import Dict, List, Tuple, Optional
from litassist.logging import save_command_output, save_log


def save_strategy_outputs(
    strategy_content: str,
    next_steps_content: str,
    document_content: str,
    reasoning_trace: str,
    outcome: str,
    case_facts_name: str,
    doc_type: str,
    output_prefix: Optional[str] = None,
    strategies_name: Optional[str] = None,
    citation_issues: Optional[List[str]] = None,
    llm_model: str = None,
) -> Tuple[str, str, str, str]:
    """
    Save all strategy command outputs to separate files.

    Args:
        strategy_content: Main strategic options content
        next_steps_content: Recommended next steps
        document_content: Draft legal document
        reasoning_trace: Consolidated reasoning trace
        outcome: Desired legal outcome
        case_facts_name: Name of case facts file
        doc_type: Type of document generated
        output_prefix: Optional custom output prefix
        strategies_name: Optional strategies file name
        citation_issues: Optional list of citation validation issues
        llm_model: LLM model used

    Returns:
        Tuple of (strategy_file, steps_file, draft_file, trace_file) paths

    Note:
        CoVe was removed from strategy command in Sep 2025. Use `litassist verify-cove`
        on output files for Chain of Verification.
    """
    # Collect all critiques
    critiques = []

    # Add citation issues if any
    if citation_issues:
        critiques.append(("Citation Validation Issues", "\n".join(citation_issues)))

    # Build metadata
    metadata = {"Desired Outcome": outcome, "Case Facts File": case_facts_name}
    if strategies_name:
        metadata["Strategies File"] = strategies_name

    # Add verification metadata
    metadata["Verification"] = "Standard verification"
    if llm_model:
        metadata["Model"] = llm_model

    # 1. Save main strategic options with critiques
    strategy_file = save_command_output(
        f"{output_prefix}_options" if output_prefix else "strategy",
        strategy_content,
        "" if output_prefix else outcome,
        metadata=metadata,
        critique_sections=critiques if critiques else None,
    )

    # 2. Save next steps separately
    steps_metadata = {"Desired Outcome": outcome, "Type": "Recommended Next Steps"}
    steps_file = save_command_output(
        f"{output_prefix}_nextsteps" if output_prefix else "strategy_nextsteps",
        next_steps_content,
        "" if output_prefix else outcome,
        metadata=steps_metadata,
    )

    # 3. Save draft document separately
    draft_metadata = {"Desired Outcome": outcome, "Document Type": doc_type.title()}
    draft_file = save_command_output(
        f"{output_prefix}_draft" if output_prefix else "strategy_draft",
        document_content,
        "" if output_prefix else outcome,
        metadata=draft_metadata,
    )

    # 4. Save reasoning trace separately
    trace_metadata = {
        "Desired Outcome": outcome,
        "Type": "Strategic Reasoning Analysis",
    }
    trace_file = save_command_output(
        f"{output_prefix}_reasoning" if output_prefix else "strategy_reasoning",
        reasoning_trace,
        "" if output_prefix else outcome,
        metadata=trace_metadata,
    )

    return strategy_file, steps_file, draft_file, trace_file


def save_strategy_log(
    outcome: str,
    strategy_content: str,
    usage: Dict,
    cove_results: Optional[Dict] = None,
):
    """
    Save strategy generation log.

    Args:
        outcome: Desired legal outcome
        strategy_content: Generated strategy content
        usage: Token usage statistics
        cove_results: Optional CoVe verification results
    """
    log_data = {
        "outcome": outcome,
        "usage": usage,
        "content_length": len(strategy_content),
    }

    if cove_results:
        log_data["cove_regeneration"] = {
            "issues_fixed": cove_results["cove"]["issues"],
            "passed": cove_results["cove"]["passed"],
        }

    save_log("strategy", log_data)
