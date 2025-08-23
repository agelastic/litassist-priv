"""Minimal verification chain orchestrator - no overengineering."""

import time
from typing import Dict, Optional, Tuple
from litassist.citation_patterns import validate_citation_patterns
from litassist.citation_verify import verify_all_citations
from litassist.llm import LLMClientFactory
from litassist.utils import save_log


def run_verification_chain(
    content: str, command: str, skip_stages: Optional[set] = None
) -> Tuple[str, Dict]:
    """
    Minimal chain that orchestrates existing verification functions.
    Returns (content, verification_results).
    """
    skip_stages = skip_stages or set()
    results = {}

    # Stage 1: Pattern validation (offline, fast)
    if "patterns" not in skip_stages:
        pattern_issues = validate_citation_patterns(content, enable_online=False)
        results["patterns"] = {
            "issues": pattern_issues,
            "passed": len(pattern_issues) == 0,
        }

        # Early exit for high-risk commands
        if pattern_issues and command in ["extractfacts", "strategy", "draft"]:
            return content, results

    # Stage 2: Database verification (online, authoritative)
    if "database" not in skip_stages and results.get("patterns", {}).get(
        "passed", True
    ):
        verified, unverified = verify_all_citations(content)
        results["database"] = {
            "verified": verified,
            "unverified": unverified,
            "passed": len(unverified) == 0,
        }

        # Early exit for strict commands
        if unverified and command in ["extractfacts", "strategy"]:
            return content, results

    # Stage 3: LLM verification (expensive, comprehensive)
    if "llm" not in skip_stages and command in ["extractfacts", "strategy", "draft"]:
        client = LLMClientFactory.for_command("verify")
        citation_report = _format_simple_report(results.get("database", {}))
        corrected_content, _ = client.verify(
            content, citation_context=citation_report if citation_report else None
        )

        results["llm"] = {
            "corrections_made": corrected_content != content,
            "passed": True,
        }

        if corrected_content != content:
            content = corrected_content

    # Stage 4: CoVe verification for high-risk commands
    if 'cove' not in skip_stages and command in ['extractfacts', 'strategy']:
        cove_content, cove_results = run_cove_verification(content, command, prior_contexts=results)
        results.update(cove_results)
        if not cove_results['cove']['passed']:
            # Keep original content but mark issues found
            results['cove_issues_found'] = True

    return content, results


def _format_simple_report(database_results: Dict) -> Optional[str]:
    """Format database results for context - no parsing, just text."""
    verified = database_results.get("verified", [])
    unverified = database_results.get("unverified", [])

    if not verified and not unverified:
        return None

    report = f"Verified: {len(verified)}\n"
    if unverified:
        report += f"Unverified: {', '.join([u[0] for u in unverified])}"

    return report


def run_cove_verification(
    content: str, command: str, prior_contexts: Optional[Dict] = None
) -> Tuple[str, Dict]:
    """
    Chain of Verification - asks LLM to generate and answer questions.
    No local parsing - trust the LLM.

    Args:
        content: Document to verify (ideally already processed by other verifications)
        command: Command name for context
        prior_contexts: Optional dict with citation/reasoning/soundness results

    Returns:
        Tuple of (content, cove_results dict)
    """
    client = LLMClientFactory.for_command("verify")
    prior_contexts = prior_contexts or {}
    
    # Track all stages for summary logging
    cove_stages = {}

    # Build context summary for question generation
    context_summary = ""
    if prior_contexts.get("citations"):
        context_summary += "\nNote: Citation verification found some issues.\n"
    if prior_contexts.get("reasoning"):
        context_summary += "\nNote: Reasoning trace has been verified.\n"
    if prior_contexts.get("soundness"):
        num_issues = (
            len(prior_contexts["soundness"])
            if isinstance(prior_contexts["soundness"], list)
            else 0
        )
        if num_issues > 0:
            context_summary += f"\nNote: Soundness check found {num_issues} issues.\n"

    # Step 1: Generate questions (let LLM do the work)
    questions_prompt = f"""Generate 5-10 verification questions for this legal document.
Focus on citations, dates, party names, legal principles, and any potential inconsistencies.
{context_summary}

Document:
{content[:3000]}  # Limit for question generation

Output numbered questions only (1. Question one, 2. Question two, etc.)."""

    questions, usage1 = client.complete([{"role": "user", "content": questions_prompt}])
    cove_stages['questions'] = {
        'prompt': questions_prompt[:500],  # First 500 chars for summary
        'response': questions,
        'usage': usage1
    }

    # Step 2: Answer questions independently (factored approach)
    answers_prompt = f"""Answer these questions based ONLY on legal knowledge, NOT the document:

{questions}

For each question, answer: Yes/No/Uncertain with brief explanation.
Format: 1. Yes - [explanation], 2. No - [explanation], etc."""

    answers, usage2 = client.complete([{"role": "user", "content": answers_prompt}])
    cove_stages['answers'] = {
        'prompt': answers_prompt[:500],
        'response': answers,
        'usage': usage2
    }

    # Step 3: Detect inconsistencies (let LLM compare)
    verify_prompt = f"""Compare these Q&A pairs against the original document.
Identify any inconsistencies or errors.

Questions and Answers:
{answers}

Original Document:
{content}

Output: List specific issues found, or "No issues found" if document is consistent."""

    issues, usage3 = client.complete([{"role": "user", "content": verify_prompt}])
    cove_stages['verification'] = {
        'prompt': verify_prompt[:500],
        'response': issues,
        'usage': usage3
    }
    
    # Determine if verification passed
    passed = "no issues found" in issues.lower()
    
    # Save aggregated CoVe summary log
    save_log(f"cove_{command}_summary", {
        "command": command,
        "stages": cove_stages,
        "prior_contexts": {
            "had_citations": bool(prior_contexts.get('citations')),
            "had_reasoning": bool(prior_contexts.get('reasoning')),
            "had_soundness": bool(prior_contexts.get('soundness'))
        },
        "result": {
            "passed": passed,
            "issues_found": issues if not passed else "None"
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_tokens": (
            usage1.get('total_tokens', 0) + 
            usage2.get('total_tokens', 0) + 
            usage3.get('total_tokens', 0)
        )
    })

    return content, {
        "cove": {
            "questions": questions,
            "answers": answers,
            "issues": issues,
            "passed": passed,
        }
    }


def format_cove_report(cove_results: Dict) -> str:
    """Format CoVe results into a readable report."""
    cove_data = cove_results.get("cove", {})

    lines = [
        "## Chain of Verification Report\n",
        f"**Status**: {'PASSED' if cove_data.get('passed') else 'ISSUES FOUND'}",
        "",
        "### Verification Questions",
        cove_data.get("questions", "No questions generated"),
        "",
        "### Independent Answers",
        cove_data.get("answers", "No answers generated"),
        "",
        "### Verification Results",
        cove_data.get("issues", "No issues checked"),
    ]

    return "\n".join(lines)
