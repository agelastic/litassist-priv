"""Minimal verification chain orchestrator - no overengineering."""

import re
import time
import traceback
from typing import Dict, Optional, Tuple

import click

from litassist.citation_patterns import validate_citation_patterns, extract_citations
from litassist.citation.verify import verify_all_citations
from litassist.citation_context import fetch_citation_context
from litassist.llm.factory import LLMClientFactory
from litassist.prompts import PROMPTS
from litassist.logging import save_log, log_task_event
from litassist.utils.formatting import warning_message


def run_verification_chain(
    content: str, command: str, skip_stages: Optional[set] = None, heavy: bool = False
) -> Tuple[str, Dict]:
    """
    Minimal chain that orchestrates existing verification functions.
    Returns (content, verification_results).

    On an early exit (offline pattern issues, or unverified citations) the
    chain records ``results["short_circuit"]`` and emits a click.echo warning.
    Callers are the CLI commands (extractfacts, strategy, draft) via
    verify_content_if_needed; a non-CLI caller would get the warning on stdout.

    Args:
        content: Content to verify
        command: Command name
        skip_stages: Set of stages to skip
        heavy: Use verification-heavy mode (max thinking effort)
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

        # Early exit for high-risk commands. Announce it: callers otherwise
        # report "verification applied" for content that never reached the LLM
        # verification stage (it was only offline pattern-checked).
        if pattern_issues and command in ["extractfacts", "strategy", "draft"]:
            results["short_circuit"] = "citation pattern issues"
            click.echo(
                warning_message(
                    "Verification short-circuited (citation pattern issues): "
                    "LLM verification was skipped; content was NOT fully verified."
                )
            )
            return content, results

    # Stage 2: Database verification (online, authoritative)
    if "database" not in skip_stages and results.get("patterns", {}).get(
        "passed", True
    ):
        verified_details, unverified = verify_all_citations(content)
        results["database"] = {
            "verified": [v["citation"] for v in verified_details],
            "unverified": unverified,
            "passed": len(unverified) == 0,
        }

        # Early exit for strict commands (same visibility rationale as above).
        if unverified and command in ["extractfacts", "strategy"]:
            results["short_circuit"] = "unverified citations"
            click.echo(
                warning_message(
                    "Verification short-circuited (unverified citations): "
                    "LLM verification was skipped; content was NOT fully verified."
                )
            )
            return content, results

    # Stage 3: LLM verification (expensive, comprehensive)
    if "llm" not in skip_stages and command in ["extractfacts", "strategy", "draft"]:
        config_name = "verification-heavy" if heavy else "verification"
        client = LLMClientFactory.for_command(config_name)
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
    content: str, command: str, prior_contexts: Optional[Dict] = None, heavy: bool = False
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
        heavy: Use heavy mode (max thinking effort) for answers stage

    Returns:
        Tuple of (content, cove_results dict)
    """
    # Create separate clients for each stage
    client_questions = LLMClientFactory.for_command("cove-questions")
    answers_config = "cove-answers-heavy" if heavy else "cove-answers"
    client_answers = LLMClientFactory.for_command(answers_config)
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

    # Announce stage start and LLM call
    log_task_event(
        command, "cove-questions", "start", "Generating verification questions"
    )
    log_task_event(
        command,
        "cove-questions",
        "llm_call",
        "Sending questions prompt to LLM",
        {"model": client_questions.model, "prompt_length": len(questions_prompt)},
    )

    # Set stage context for logging
    client_questions.command_context = f"cove_stage1_questions_{command}"
    questions, usage1 = client_questions.complete(
        [{"role": "user", "content": questions_prompt}]
    )
    log_task_event(
        command,
        "cove-questions",
        "llm_response",
        "Received questions from LLM",
        {
            "model": client_questions.model,
            "response_length": len(questions),
            "usage": usage1,
        },
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
    failed_citations = []
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
            # Fetch FULL documents for all citations found. Pass the original
            # document `content` (NOT `questions`, which is LLM-generated and may not
            # print the parallel neutral cite) so C2 parallel-cite resolution works.
            legal_context, failed_citations = fetch_citation_context(citations, content)

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

                # No size warning emitted here. The earlier `save_log` write
                # was never surfaced to the user (file-only log entry), and
                # the verification model's actual capacity is enforced by
                # the underlying API -- if the call exceeds the model
                # window the provider returns a clear error. A soft warn
                # between "comfortable" and "hard cap" adds no signal.

            # Log failed citations
            if failed_citations:
                save_log(
                    "cove_citation_fetch_failures",
                    {
                        "command": command,
                        "failed_citations": [(cit, reason) for cit, reason in failed_citations],
                        "count": len(failed_citations),
                    },
                )

            if not legal_context and not failed_citations:
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

    # Announce stage start
    log_task_event(command, "cove-answers", "start", "Answering verification questions")

    # Prepare scalable inclusion of legal documents (drop-largest backoff on token errors)
    cases_to_include = list(legal_context.items()) if legal_context else []
    attempts = 0
    answers = None
    usage2 = {}

    # Set stage context for logging
    client_answers.command_context = f"cove_stage2_answers_{command}"

    while answers is None and attempts < 5:
        # Build context section based on current cases_to_include and any reference files
        has_any_context = bool(cases_to_include) or bool(reference_context)
        context_text = ""

        if cases_to_include:
            context_text += "\n=== LEGAL AUTHORITIES (FULL TEXT) ===\n"
            for citation, full_text in cases_to_include:
                context_text += f"\n=== {citation} ===\n"
                context_text += full_text
                context_text += f"\n=== END {citation} ===\n\n"
            context_text += "=== END LEGAL AUTHORITIES ===\n\n"

        if reference_context:
            context_text += "\n=== REFERENCE DOCUMENTS ===\n"
            context_text += reference_context
            context_text += "=== END REFERENCE DOCUMENTS ===\n\n"

        # Add retrieval failures section if any citations failed to fetch
        if failed_citations:
            context_text += "\n=== RETRIEVAL FAILURES ===\n"
            context_text += "The following citations could not be retrieved:\n\n"
            for citation, reason in failed_citations:
                context_text += f"- {citation}: {reason}\n"
            context_text += "\n=== END RETRIEVAL FAILURES ===\n\n"

        # Choose appropriate prompt template
        if has_any_context:
            answers_prompt = PROMPTS.get(
                "verification.cove.answers_with_context"
            ).format(questions=questions, legal_context=context_text)
        else:
            answers_prompt = PROMPTS.get(
                "verification.cove.answers_verification"
            ).format(content=questions)

        # Log the outgoing call for this attempt
        log_task_event(
            command,
            "cove-answers",
            "llm_call",
            "Sending answers prompt to LLM",
            {
                "model": client_answers.model,
                "prompt_length": len(answers_prompt),
                "attempt": attempts + 1,
            },
        )

        try:
            # Make the LLM call
            answers, usage2 = client_answers.complete(
                [{"role": "user", "content": answers_prompt}]
            )
        except Exception as e:
            error_str = str(e).lower()
            # Detect token/context limit errors and drop the largest document if available
            if any(
                x in error_str
                for x in ["token", "context", "length", "too long", "maximum"]
            ):
                if cases_to_include:
                    # Identify and drop the largest included case/document
                    largest_idx = max(
                        range(len(cases_to_include)),
                        key=lambda i: len(cases_to_include[i][1]),
                    )
                    dropped_case = cases_to_include.pop(largest_idx)

                    # Log the drop event for auditability
                    save_log(
                        "cove_answers_scaling_drop",
                        {
                            "command": command,
                            "dropped_case": dropped_case[0],
                            "dropped_length": len(dropped_case[1]),
                            "remaining_cases": [c for c, _ in cases_to_include],
                            "attempt": attempts + 1,
                            "error": str(e),
                        },
                    )

                    attempts += 1
                    continue  # retry with reduced context
                else:
                    # Nothing left to drop - re-raise
                    raise
            else:
                # Not a token/context limit error - re-raise
                raise

    if answers is None:
        # Exhausted retries without success
        raise Exception("Failed to get CoVe answers after dropping all legal context")

    # Log the successful response
    log_task_event(
        command,
        "cove-answers",
        "llm_response",
        "Received independent answers from LLM",
        {
            "model": client_answers.model,
            "response_length": len(answers),
            "usage": usage2,
        },
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

    # Announce stage start and LLM call
    log_task_event(
        command,
        "cove-verify",
        "start",
        "Detecting inconsistencies against the original",
    )
    log_task_event(
        command,
        "cove-verify",
        "llm_call",
        "Sending verification (inconsistency detection) prompt to LLM",
        {"model": client_verify.model, "prompt_length": len(verify_prompt)},
    )

    # Set stage context for logging
    client_verify.command_context = f"cove_stage3_verify_{command}"
    issues, usage3 = client_verify.complete(
        [{"role": "user", "content": verify_prompt}]
    )
    log_task_event(
        command,
        "cove-verify",
        "llm_response",
        "Received inconsistency report from LLM",
        {"model": client_verify.model, "response_length": len(issues), "usage": usage3},
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

    # Determine if verification passed using the structured VERDICT line.
    # Substring matching against "no issues found" used to leak through quoted
    # and negated text (e.g. 'not "no issues found"'). The verifier prompt now
    # requires an explicit VERDICT: PASS|FAIL line and a missing line fails
    # closed (treated as FAIL).
    verdict_match = re.search(
        r"^\s*VERDICT:\s*(PASS|FAIL)\s*$",
        issues,
        re.MULTILINE | re.IGNORECASE,
    )
    passed = bool(verdict_match) and verdict_match.group(1).upper() == "PASS"

    # Step 4: Generate final verified response (Meta paper's critical step)
    final_content = content
    if not passed:
        # Create final client only when needed
        client_final = LLMClientFactory.for_command("cove-final")

        # This is the missing step from the Meta paper - regenerate to fix issues
        regenerate_prompt = PROMPTS.get("verification.cove.regeneration").format(
            context=issues, prompt=answers, content=content
        )

        # Announce stage start and LLM call
        log_task_event(
            command, "cove-regenerate", "start", "Regenerating corrected document"
        )
        log_task_event(
            command,
            "cove-regenerate",
            "llm_call",
            "Sending regeneration prompt to LLM",
            {"model": client_final.model, "prompt_length": len(regenerate_prompt)},
        )

        # Set stage context for logging
        client_final.command_context = f"cove_stage4_regenerate_{command}"
        final_content, usage4 = client_final.complete(
            [{"role": "user", "content": regenerate_prompt}]
        )
        log_task_event(
            command,
            "cove-regenerate",
            "llm_response",
            "Received regenerated document from LLM",
            {
                "model": client_final.model,
                "response_length": len(final_content),
                "usage": usage4,
            },
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

    # Helper to ensure string values (handles None gracefully)
    def safe_str(value: str | None, default: str) -> str:
        """Return value if not None, otherwise return default."""
        return value if value is not None else default

    lines = [
        "## Chain of Verification Report\n",
        f"**Status**: {'PASSED' if cove_data.get('passed') else 'ISSUES FOUND'}",
        "",
        "### Verification Questions",
        safe_str(cove_data.get("questions"), "No questions generated"),
        "",
        "### Independent Answers",
        safe_str(cove_data.get("answers"), "No answers generated"),
        "",
        "### Verification Results",
        safe_str(cove_data.get("issues"), "No issues checked"),
    ]

    return "\n".join(lines)


# --- P-FAITH: faithfulness scoring -----------------------------------------

# The four labels the alignment stage may assign to a claim. Kept as a set so the
# pure scorer can validate its input and fail loud on anything else.
_FAITHFULNESS_LABELS = ("SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "PLACEHOLDER")

# Matches the alignment stage's per-claim classification line. One match per claim is
# the authoritative count for scoring; a malformed response yields zero matches and is
# failed closed by the orchestrator (no silent score-100).
_CLASSIFICATION_RE = re.compile(
    r"^CLASSIFICATION:\s*(SUPPORTED|UNSUPPORTED|CONTRADICTED|PLACEHOLDER)\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def score_faithfulness(classifications) -> Dict:
    """Aggregate per-claim faithfulness labels into a deterministic score.

    Each entry in ``classifications`` is one of SUPPORTED / UNSUPPORTED /
    CONTRADICTED / PLACEHOLDER (case-insensitive). Pure -- no I/O -- so it is directly
    unit-testable offline.

    PLACEHOLDER claims use the project's sanctioned ``[... TO BE PROVIDED]`` convention
    for missing data, so they are NEUTRAL and excluded from the denominator. The score
    is the fraction of *substantive* claims (supported + unsupported + contradicted)
    that are grounded in the sources; with no substantive claims the score is 100.
    """
    counts = {label: 0 for label in _FAITHFULNESS_LABELS}
    for label in classifications:
        key = label.strip().upper()
        if key not in counts:
            raise ValueError(f"Unknown faithfulness label: {label!r}")
        counts[key] += 1

    supported = counts["SUPPORTED"]
    unsupported = counts["UNSUPPORTED"]
    contradicted = counts["CONTRADICTED"]
    placeholder = counts["PLACEHOLDER"]

    # Denominator excludes placeholders (correctly-marked missing data, not a grounding
    # failure); 100 when nothing substantive needs grounding.
    substantive = supported + unsupported + contradicted
    score = round(100 * supported / substantive) if substantive else 100

    return {
        "score": score,
        "supported": supported,
        "unsupported": unsupported,
        "contradicted": contradicted,
        "placeholder": placeholder,
        "flagged_count": unsupported + contradicted,
        "total": len(classifications),
    }


def _flagged_blocks(alignment: str) -> str:
    """Return the alignment blocks classified UNSUPPORTED or CONTRADICTED, joined.

    Splits on each ``CLAIM:`` line so blocks stay intact; used only to feed the addendum
    prompt. The authoritative score comes from ``_CLASSIFICATION_RE`` counts, not this.
    """
    flagged = []
    for block in re.split(r"(?im)^(?=CLAIM:)", alignment):
        match = _CLASSIFICATION_RE.search(block)
        if match and match.group(1).upper() in ("UNSUPPORTED", "CONTRADICTED"):
            flagged.append(block.strip())
    return "\n\n".join(flagged)


def run_faithfulness_verification(
    content: str, sources_context: str, command: str
) -> Tuple[str, Dict]:
    """Check whether the document's factual claims are grounded in the source documents.

    Three stages mirroring run_cove_verification: extract atomic claims, classify each
    against the sources, and -- only when claims are flagged -- draft a standalone
    corrective addendum. The original ``content`` is NEVER modified; it is returned
    unchanged. Returns (content, results) where ``results["faithfulness"]`` carries the
    score, per-claim classifications, the flagged blocks, and the addendum (or None).
    """
    client_claims = LLMClientFactory.for_command("faithfulness-claims")
    client_align = LLMClientFactory.for_command("faithfulness-align")
    stages = {}

    # Stage 1: extract atomic claims from the document under test.
    claims_prompt = PROMPTS.get("verification.faithfulness.claim_extraction").format(
        content=content
    )
    log_task_event(command, "faithfulness-claims", "start", "Extracting atomic claims")
    client_claims.command_context = f"faithfulness_stage1_claims_{command}"
    claims, usage1 = client_claims.complete(
        [{"role": "user", "content": claims_prompt}]
    )
    log_task_event(
        command,
        "faithfulness-claims",
        "llm_response",
        "Received atomic claims",
        {"model": client_claims.model, "response_length": len(claims), "usage": usage1},
    )
    stages["claims"] = {
        "prompt": claims_prompt,
        "response": claims,
        "usage": usage1,
        "model": client_claims.model,
    }

    # No substantive claims -> nothing to ground; faithful by definition.
    if not claims.strip():
        score_data = score_faithfulness([])
        results = {
            "faithfulness": {
                **score_data,
                "claims": claims,
                "alignment": "",
                "flagged_text": "",
                "addendum": None,
            }
        }
        save_log(
            f"faithfulness_{command}_summary",
            {
                "command": command,
                "stages": stages,
                "result": score_data,
                "addendum_generated": False,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
        return content, results

    # Stage 2: classify each claim against the sources.
    align_prompt = PROMPTS.get("verification.faithfulness.alignment").format(
        sources=sources_context, claims=claims
    )
    log_task_event(
        command, "faithfulness-align", "start", "Classifying claims against sources"
    )
    client_align.command_context = f"faithfulness_stage2_align_{command}"
    alignment, usage2 = client_align.complete(
        [{"role": "user", "content": align_prompt}]
    )
    log_task_event(
        command,
        "faithfulness-align",
        "llm_response",
        "Received claim classifications",
        {"model": client_align.model, "response_length": len(alignment), "usage": usage2},
    )
    stages["alignment"] = {
        "prompt": align_prompt,
        "response": alignment,
        "usage": usage2,
        "model": client_align.model,
    }

    # Count the claims stage 1 extracted (the prompt numbers them "1. ", "2. ", ...).
    claim_count = len(re.findall(r"(?m)^\s*\d+\.", claims))
    labels = [m.group(1).upper() for m in _CLASSIFICATION_RE.finditer(alignment)]
    # Fail closed unless the classifications match the extracted claims one-to-one.
    # Fewer labels means an ungraded claim (which could be unsupported or contradicted);
    # more labels means the grader classified something that was never extracted. Either
    # way the counts cannot be trusted, so a mismatch is an error, not a score.
    if not labels or len(labels) != claim_count:
        raise ValueError(
            f"Faithfulness alignment classified {len(labels)} of {claim_count} claims; "
            "expected one classification per extracted claim"
        )

    score_data = score_faithfulness(labels)
    flagged_text = _flagged_blocks(alignment)

    # Stage 3: corrective addendum, only when claims are flagged. The original document
    # is left untouched -- the addendum is a separate artifact.
    addendum = None
    if score_data["flagged_count"] > 0:
        client_addendum = LLMClientFactory.for_command("faithfulness-addendum")
        addendum_prompt = PROMPTS.get("verification.faithfulness.addendum").format(
            flagged=flagged_text, sources=sources_context, content=content
        )
        log_task_event(
            command, "faithfulness-addendum", "start", "Drafting corrective addendum"
        )
        client_addendum.command_context = f"faithfulness_stage3_addendum_{command}"
        addendum, usage3 = client_addendum.complete(
            [{"role": "user", "content": addendum_prompt}]
        )
        log_task_event(
            command,
            "faithfulness-addendum",
            "llm_response",
            "Received corrective addendum",
            {
                "model": client_addendum.model,
                "response_length": len(addendum),
                "usage": usage3,
            },
        )
        stages["addendum"] = {
            "prompt": addendum_prompt,
            "response": addendum,
            "usage": usage3,
            "model": client_addendum.model,
        }

    results = {
        "faithfulness": {
            **score_data,
            "claims": claims,
            "alignment": alignment,
            "flagged_text": flagged_text,
            "addendum": addendum,
        }
    }

    save_log(
        f"faithfulness_{command}_summary",
        {
            "command": command,
            "stages": stages,
            "result": score_data,
            "addendum_generated": addendum is not None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    )

    return content, results


def format_faithfulness_report(results: Dict) -> str:
    """Format faithfulness results into a readable report."""
    data = results.get("faithfulness", {})
    lines = [
        "## Faithfulness Report\n",
        f"**Score**: {data.get('score', 0)}/100",
        "",
        f"- Supported: {data.get('supported', 0)}",
        f"- Unsupported: {data.get('unsupported', 0)}",
        f"- Contradicted: {data.get('contradicted', 0)}",
        f"- Placeholder (neutral): {data.get('placeholder', 0)}",
        "",
        "### Per-claim classification",
        data.get("alignment") or "No claims extracted.",
        "",
        "### Flagged claims (unsupported or contradicted)",
        data.get("flagged_text") or "None",
    ]
    return "\n".join(lines)
