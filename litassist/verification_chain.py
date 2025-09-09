"""Minimal verification chain orchestrator - no overengineering."""

import time
import traceback
from typing import Dict, Optional, Tuple
from litassist.citation_patterns import validate_citation_patterns, extract_citations
from litassist.citation_verify import verify_all_citations
from litassist.citation_context import fetch_citation_context
from litassist.llm import LLMClientFactory
from litassist.llm.retry_handler import execute_with_document_dropping
from litassist.prompts import PROMPTS
from litassist.logging_utils import save_log


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
        client = LLMClientFactory.for_command("verification")
        citation_report = _format_simple_report(results.get("database", {}))
        corrected_content, model_name = client.verify(
            content, citation_context=citation_report if citation_report else None
        )

        results["llm"] = {
            "corrections_made": corrected_content != content,
            "passed": True,
        }

        if corrected_content != content:
            content = corrected_content

    # Note: CoVe is now handled directly by extractfacts and strategy commands
    # when --cove flag is passed, to avoid double verification

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

    Note: When running under pytest tests, mock responses may show document content
    instead of generated questions. This is expected test behavior and does not
    indicate a problem with the actual implementation.

    Args:
        content: Document to verify (ideally already processed by other verifications)
        command: Command name for context
        prior_contexts: Optional dict with citation/reasoning/soundness results

    Returns:
        Tuple of (content, cove_results dict)
    """
    # Create separate clients for each stage
    client_questions = LLMClientFactory.for_command("cove-questions")
    client_answers = LLMClientFactory.for_command("cove-answers")
    client_verify = LLMClientFactory.for_command("cove-verify")

    prior_contexts = prior_contexts or {}

    # Track all stages for summary logging
    cove_stages = {}

    # Build context summary for question generation with proper === separation
    context_summary = ""
    if prior_contexts.get("citations"):
        context_summary += "\n\n=== PRIOR VERIFICATION: CITATIONS ===\n"
        context_summary += (
            "Citation verification found issues that should be addressed.\n"
        )
        context_summary += "=== END PRIOR VERIFICATION: CITATIONS ===\n"
    if prior_contexts.get("reasoning"):
        context_summary += "\n\n=== PRIOR VERIFICATION: REASONING ===\n"
        context_summary += "Reasoning trace has been verified and validated.\n"
        context_summary += "=== END PRIOR VERIFICATION: REASONING ===\n"
    if prior_contexts.get("soundness"):
        num_issues = (
            len(prior_contexts["soundness"])
            if isinstance(prior_contexts["soundness"], list)
            else 0
        )
        if num_issues > 0:
            context_summary += "\n\n=== PRIOR VERIFICATION: SOUNDNESS ===\n"
            context_summary += f"Legal soundness check identified {num_issues} issues requiring attention.\n"
            context_summary += "=== END PRIOR VERIFICATION: SOUNDNESS ===\n"

    # Step 1: Generate questions (let LLM do the work)
    questions_prompt = PROMPTS.get("verification.cove.questions_generation").format(
        context=context_summary, content=content
    )

    # Set stage context for logging
    client_questions.command_context = f"cove_stage1_questions_{command}"
    questions, usage1 = client_questions.complete(
        [{"role": "user", "content": questions_prompt}]
    )

    # Store full information for debugging
    cove_stages["questions"] = {
        "prompt": questions_prompt,  # Full prompt for legal accountability
        "prompt_truncated": questions_prompt[:500],  # First 500 chars for quick review
        "prompt_full_length": len(questions_prompt),
        "response": questions,
        "response_length": len(questions),
        "usage": usage1,
        "model": client_questions.model,
    }

    # NEW Step 1.5: Extract and fetch FULL citation documents
    legal_context = {}
    total_context_size = 0

    try:
        # Extract citations from generated questions
        citations = extract_citations(questions)

        # Always log extraction result, even if empty
        save_log(
            "cove_citation_extraction",
            {
                "command": command,
                "citations_found": list(citations) if citations else [],
                "count": len(citations) if citations else 0,
                "questions_length": len(questions),
            },
        )

        if citations:
            # Fetch FULL documents for all citations found
            legal_context = fetch_citation_context(citations)

            if legal_context:
                total_context_size = sum(len(v) for v in legal_context.values())

                save_log(
                    "cove_citation_context",
                    {
                        "command": command,
                        "citations_fetched": list(legal_context.keys()),
                        "total_chars": total_context_size,
                        "estimated_tokens": total_context_size // 4,  # Rough estimate
                    },
                )

                # Warn if context is very large
                if total_context_size > 100000:  # ~25k tokens
                    save_log(
                        "cove_large_context_warning",
                        {
                            "command": command,
                            "size_chars": total_context_size,
                            "message": "Large legal context may impact token usage",
                        },
                    )
            else:
                save_log(
                    "cove_citation_fetch_empty",
                    {
                        "command": command,
                        "citations_requested": list(citations),
                        "message": "fetch_citation_context returned empty result",
                    },
                )
        else:
            save_log(
                "cove_no_citations_found",
                {
                    "command": command,
                    "questions_sample": questions[:500],
                    "message": "No citations extracted from questions",
                },
            )
    except Exception as e:
        # Log with full traceback for debugging
        save_log(
            "cove_citation_error",
            {
                "command": command,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": traceback.format_exc(),
            },
        )

    # Step 2: Answer questions with FULL legal documents and/or reference files
    reference_context = ""
    if prior_contexts and prior_contexts.get("cove_reference_files"):
        reference_context = prior_contexts["cove_reference_files"]
    
    if legal_context or reference_context:
        # Build context section with COMPLETE documents
        context_text = ""
        
        if legal_context:
            context_text += "\n=== LEGAL AUTHORITIES (FULL TEXT) ===\n"
            for citation, full_text in legal_context.items():
                context_text += f"\n=== {citation} ===\n"
                context_text += full_text
                context_text += f"\n=== END {citation} ===\n\n"
            context_text += "=== END LEGAL AUTHORITIES ===\n\n"
        
        if reference_context:
            context_text += "\n=== REFERENCE DOCUMENTS ===\n"
            context_text += reference_context
            context_text += "=== END REFERENCE DOCUMENTS ===\n\n"

        # Use enhanced prompt with context
        answers_prompt = PROMPTS.get("verification.cove.answers_with_context").format(
            questions=questions, legal_context=context_text
        )
    else:
        # Existing prompt without context
        answers_prompt = PROMPTS.get("verification.cove.answers_verification").format(
            content=questions
        )

    # Set stage context for logging
    client_answers.command_context = f"cove_stage2_answers_{command}"
    
    # Use document dropping for answer stage which may have large legal context
    if legal_context:
        # Build other context (questions + reference documents)
        other_context = f"QUESTIONS:\n{questions}\n\n"
        if reference_context:
            other_context += "\n=== REFERENCE DOCUMENTS ===\n"
            other_context += reference_context
            other_context += "=== END REFERENCE DOCUMENTS ===\n\n"
        
        # Rebuild function for answers with context
        def rebuild_answers_prompt(remaining_docs, other_ctx):
            context_text = ""
            if remaining_docs:
                context_text += "\n=== LEGAL AUTHORITIES (FULL TEXT) ===\n"
                for citation, full_text in remaining_docs.items():
                    context_text += f"\n=== {citation} ===\n"
                    context_text += full_text
                    context_text += f"\n=== END {citation} ===\n\n"
                context_text += "=== END LEGAL AUTHORITIES ===\n\n"
            
            if reference_context and context_text:
                # Both legal and reference context
                full_context = context_text + other_ctx
            elif context_text:
                # Just legal context
                full_context = context_text + f"QUESTIONS:\n{questions}\n\n"
            else:
                # Just reference context or nothing
                full_context = other_ctx
                
            return PROMPTS.get("verification.cove.answers_with_context").format(
                questions=questions, legal_context=full_context
            )
        
        answers, usage2 = execute_with_document_dropping(
            client=client_answers,
            messages=[{"role": "user", "content": answers_prompt}],
            documents=legal_context,
            other_context=other_context,
            rebuild_prompt_func=rebuild_answers_prompt,
            skip_citation_verification=False
        )
    else:
        # No large context, use regular complete
        answers, usage2 = client_answers.complete(
            [{"role": "user", "content": answers_prompt}]
        )

    cove_stages["answers"] = {
        "prompt": answers_prompt,  # Full prompt for legal accountability
        "prompt_truncated": answers_prompt[:500],
        "prompt_full_length": len(answers_prompt),
        "response": answers,
        "response_length": len(answers),
        "usage": usage2,
        "model": client_answers.model,
    }

    # Step 3: Detect inconsistencies (let LLM compare)
    verify_prompt = PROMPTS.get("verification.cove.inconsistency_detection").format(
        context=answers, content=content
    )

    # Set stage context for logging
    client_verify.command_context = f"cove_stage3_verify_{command}"
    issues, usage3 = client_verify.complete(
        [{"role": "user", "content": verify_prompt}]
    )

    cove_stages["verification"] = {
        "prompt": verify_prompt,  # Full prompt for legal accountability
        "prompt_truncated": verify_prompt[:500],
        "prompt_full_length": len(verify_prompt),
        "response": issues,
        "response_length": len(issues),
        "usage": usage3,
        "model": client_verify.model,
    }

    # Determine if verification passed
    passed = "no issues found" in issues.lower()

    # Step 4: Generate final verified response (Meta paper's critical step)
    final_content = content
    if not passed:
        # Create final client only when needed
        client_final = LLMClientFactory.for_command("cove-final")

        # This is the missing step from the Meta paper - regenerate to fix issues
        regenerate_prompt = PROMPTS.get("verification.cove.regeneration").format(
            context=issues, prompt=answers, content=content
        )

        # Set stage context for logging
        client_final.command_context = f"cove_stage4_regenerate_{command}"
        final_content, usage4 = client_final.complete(
            [{"role": "user", "content": regenerate_prompt}]
        )

        cove_stages["regeneration"] = {
            "prompt": regenerate_prompt,  # Full prompt for legal accountability
            "prompt_truncated": regenerate_prompt[:500],
            "prompt_full_length": len(regenerate_prompt),
            "response": final_content,  # Full regenerated content for audit trail
            "response_length": len(final_content),
            "usage": usage4,
            "model": client_final.model,
            "content_changed": final_content != content,
        }
    else:
        # No regeneration needed
        cove_stages["regeneration"] = {
            "skipped": True,
            "reason": "No issues found - regeneration not needed",
        }

    # Save aggregated CoVe summary log
    save_log(
        f"cove_{command}_summary",
        {
            "command": command,
            "stages": cove_stages,
            "prior_contexts": {
                "had_citations": bool(prior_contexts.get("citations")),
                "had_reasoning": bool(prior_contexts.get("reasoning")),
                "had_soundness": bool(prior_contexts.get("soundness")),
                "had_cove_reference": bool(prior_contexts.get("cove_reference_files")),
            },
            "result": {
                "passed": passed,
                "issues_found": issues if not passed else "None",
            },
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tokens": (
                usage1.get("total_tokens", 0)
                + usage2.get("total_tokens", 0)
                + usage3.get("total_tokens", 0)
                + (
                    usage4.get("total_tokens", 0)
                    if not passed and "usage4" in locals()
                    else 0
                )
            ),
        },
    )

    return final_content, {
        "cove": {
            "questions": questions,
            "answers": answers,
            "issues": issues,
            "passed": passed,
            "regenerated": not passed,
            "final_content_length": len(final_content),
            "original_content_length": len(content),
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
