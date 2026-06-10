#!/usr/bin/env python3
"""
P-JUDGE offline eval harness.

Scores litassist output fixtures against a rubric with an LLM judge
(model role `judge-eval` in litassist/llm/model_configs.yaml; prompts in
litassist/prompts/judge_eval.yaml). Repeatable, offline-input, real-API:
running this costs money and is never part of pytest. The pure
parsing/scoring functions below ARE covered offline by
tests/unit/test_judge_eval_harness.py, so they must stay stdlib-only and
importable without config.yaml (litassist imports are deferred into the
runtime path).

Usage:
    python test-scripts/test_judge_eval.py [--cases-dir DIR] [--only ID]
        [--baseline PATH] [--update-baseline] [--confirm-retrieval]

Exit status is non-zero on any JUDGE_FORMAT_ERROR, baseline REGRESSION,
or (with --confirm-retrieval) fetchable-tag drift.
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

# NOTE: only stdlib at module level. yaml and litassist imports are deferred
# into the runtime functions so tests/unit/test_judge_eval_harness.py can
# import the pure functions without config.yaml or project dependencies.

# Markers of the fail-closed judge output contract (must match
# judge_eval.system_prompt; mirrors the VERDICT: PASS|FAIL pattern in
# litassist/verification_chain.py).
JUDGE_START = "=== JUDGE SCORES (JSON) ==="
JUDGE_END = "=== END JUDGE SCORES (JSON) ==="

VALID_BANDS = {"excellent", "good", "adequate", "poor", "failing"}

# Score drift allowed before a dimension counts as a regression. +/-8 covers
# the single-digit run-to-run variance observed on deterministic-judge reruns
# while still catching real prompt/model regressions; recalibrate from
# evidence if reruns show otherwise.
DEFAULT_TOLERANCE = 8

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class JudgeFormatError(Exception):
    """Judge response violated the structured-output contract."""


# --------------------------------------------------------------------------
# Pure functions (unit-tested offline; no litassist imports)
# --------------------------------------------------------------------------


def extract_judge_json(response: str) -> dict:
    """Extract and parse the JSON block between the JUDGE SCORES markers.

    The response must END with the marker block (trailing whitespace
    tolerated). Any deviation raises JudgeFormatError - never silently
    scored.
    """
    match = re.search(
        re.escape(JUDGE_START) + r"(.*?)" + re.escape(JUDGE_END) + r"(.*)\Z",
        response,
        re.DOTALL,
    )
    if not match:
        raise JudgeFormatError(
            "JUDGE SCORES markers missing or malformed in judge response"
        )
    if match.group(2).strip():
        raise JudgeFormatError("content found after END marker; response must end with the marker block")
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError as e:
        raise JudgeFormatError(f"invalid JSON between JUDGE SCORES markers: {e}")


def validate_dimensions(parsed: dict, declared: list) -> None:
    """Check the parsed JSON scores exactly the declared dimensions."""
    if not isinstance(parsed, dict):
        raise JudgeFormatError("judge JSON is not an object")
    dims = parsed.get("dimensions")
    if not isinstance(dims, dict):
        raise JudgeFormatError("'dimensions' missing or not an object")
    missing = [d for d in declared if d not in dims]
    if missing:
        raise JudgeFormatError(f"declared dimensions missing from response: {missing}")
    extra = [d for d in dims if d not in declared]
    if extra:
        raise JudgeFormatError(f"undeclared dimensions in response: {extra}")
    for name, entry in dims.items():
        if not isinstance(entry, dict):
            raise JudgeFormatError(f"dimension '{name}' is not an object: {entry!r}")
        score = entry.get("score")
        if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
            raise JudgeFormatError(f"dimension '{name}' score is not an integer 0-100: {score!r}")
        if entry.get("band") not in VALID_BANDS:
            raise JudgeFormatError(f"dimension '{name}' band invalid: {entry.get('band')!r}")


def recompute_overall(dimensions: dict) -> int:
    """Unweighted mean of dimension scores; the model's own 'overall' is
    only a cross-check."""
    scores = [entry["score"] for entry in dimensions.values()]
    if not scores:
        raise JudgeFormatError("no dimensions to recompute overall from")
    return round(sum(scores) / len(scores))


def grounding_coverage(total_expected: int, starved_count: int) -> float:
    """Fraction of expected citations the judge could verify from SOURCES.

    No expected citations means nothing was unverifiable: coverage 1.0.
    """
    if total_expected == 0:
        return 1.0
    return (total_expected - starved_count) / total_expected


def apply_grounding_cap(score: int, coverage: float) -> int:
    """Cap citation_grounding by retrieval coverage so a case leaning on
    unfetchable citations cannot score above its evidence ceiling."""
    return min(score, round(100 * coverage))


def compare_to_baseline(results: dict, baseline: dict) -> tuple:
    """Compare {case_id: {dimension: score}} against the baseline file.

    Returns (regressions, notes). Only drops below tolerance regress;
    improvements and new/unmatched cases are notes.
    """
    tolerance = baseline.get("tolerance", DEFAULT_TOLERANCE)
    base_cases = baseline.get("cases", {})
    regressions = []
    notes = []
    for case_id, dims in results.items():
        if case_id not in base_cases:
            notes.append(f"NEW: {case_id} has no baseline entry")
            continue
        base_dims = base_cases[case_id]
        for dim, score in dims.items():
            if dim not in base_dims:
                notes.append(f"NEW: {case_id}.{dim} has no baseline entry")
                continue
            base = base_dims[dim]
            if score < base - tolerance:
                regressions.append(
                    f"REGRESSION: {case_id}.{dim} = {score}, baseline {base} (tolerance {tolerance})"
                )
            elif score > base + tolerance:
                notes.append(
                    f"IMPROVEMENT: {case_id}.{dim} = {score}, baseline {base}"
                )
    for case_id in base_cases:
        if case_id not in results:
            notes.append(f"SKIPPED: baseline case {case_id} not in this run")
    return regressions, notes


def build_citations_table(expected: list) -> str:
    """Render the EXPECTED CITATIONS block lines: 'cite | retrieval_class'."""
    if not expected:
        return "(none declared)"
    return "\n".join(f"{e['cite']} | {e['retrieval_class']}" for e in expected)


# --------------------------------------------------------------------------
# Runtime (real API; litassist imports deferred so unit tests can import
# this module without config.yaml)
# --------------------------------------------------------------------------


def load_case(case_path: str) -> dict:
    """Load one case YAML and its output/source files (paths relative to
    the case file's directory)."""
    import yaml

    with open(case_path, "r", encoding="utf-8") as f:
        case = yaml.safe_load(f)
    required = ["case_id", "command", "dimensions", "output_file", "source_files"]
    missing = [k for k in required if k not in case]
    if missing:
        sys.exit(f"Case {case_path} missing keys: {missing}")
    if "structure" in case["dimensions"] and not case.get("structure_template_key"):
        sys.exit(
            f"Case {case['case_id']} declares the structure dimension but no structure_template_key"
        )
    base = os.path.dirname(case_path)
    with open(os.path.join(base, case["output_file"]), "r", encoding="utf-8") as f:
        case["_output_text"] = f.read()
    sources = []
    for src in case["source_files"]:
        with open(os.path.join(base, src), "r", encoding="utf-8") as f:
            sources.append(f"=== SOURCE: {os.path.basename(src)} ===\n{f.read()}")
    case["_sources_text"] = "\n\n".join(sources)
    case.setdefault("expected_citations", [])
    return case


def build_messages(case: dict, prompts) -> list:
    """Assemble system + user messages for one case."""
    declared = case["dimensions"]
    rubrics = "\n".join(
        prompts.get(f"judge_eval.rubric_{dim}") for dim in declared
    )
    if case.get("structure_template_key"):
        structure_template = prompts.get(case["structure_template_key"])
    else:
        structure_template = "(no structure template declared for this case)"
    user = prompts.get("judge_eval.task_template").format(
        case_id=case["case_id"],
        command=case["command"],
        dimensions_list=", ".join(declared),
        rubrics=rubrics,
        structure_template=structure_template,
        expected_citations_table=build_citations_table(case["expected_citations"]),
        sources=case["_sources_text"],
        output=case["_output_text"],
        context_starved_instruction=prompts.get("judge_eval.context_starved_instruction"),
    )
    return [
        {"role": "system", "content": prompts.get("judge_eval.system_prompt")},
        {"role": "user", "content": user},
    ]


def score_case(case: dict, response: str) -> dict:
    """Parse, validate and score one judge response. Raises JudgeFormatError."""
    parsed = extract_judge_json(response)
    validate_dimensions(parsed, case["dimensions"])
    if parsed.get("case_id") != case["case_id"]:
        raise JudgeFormatError(
            f"case_id mismatch: expected {case['case_id']}, got {parsed.get('case_id')!r}"
        )

    expected_cites = {e["cite"] for e in case["expected_citations"]}
    starved_raw = parsed.get("context_starved_citations", [])
    starved = [s for s in starved_raw if s.get("cite") in expected_cites]
    unmatched = [s["cite"] for s in starved_raw if s.get("cite") not in expected_cites]

    coverage = grounding_coverage(len(expected_cites), len(starved))
    dims = {name: entry["score"] for name, entry in parsed["dimensions"].items()}
    capped_note = None
    if "citation_grounding" in dims:
        raw = dims["citation_grounding"]
        dims["citation_grounding"] = apply_grounding_cap(raw, coverage)
        if dims["citation_grounding"] < raw:
            capped_note = (
                f"citation_grounding capped {raw} -> {dims['citation_grounding']}"
                f" by grounding_coverage {coverage:.2f}"
            )

    overall = recompute_overall(
        {name: {"score": s} for name, s in dims.items()}
    )
    model_overall = parsed.get("overall")
    return {
        "case_id": case["case_id"],
        "dimensions": dims,
        "judge_detail": parsed["dimensions"],
        "overall": overall,
        "model_overall_crosscheck": model_overall,
        "overall_mismatch": isinstance(model_overall, int)
        and abs(model_overall - overall) > 1,
        "grounding_coverage": coverage,
        "context_starved": starved,
        "unmatched_starved_cites": unmatched,
        "capped_note": capped_note,
        "summary": parsed.get("summary", ""),
    }


def confirm_retrieval(cases: list) -> list:
    """Re-run fetch_citation_context over all expected citations and report
    fetchable-tag drift (costs CSE calls)."""
    from litassist.citation_context import fetch_citation_context

    drift = []
    all_cites = []
    tags = {}
    for case in cases:
        for e in case["expected_citations"]:
            all_cites.append(e["cite"])
            tags[e["cite"]] = e["fetchable"]
    if not all_cites:
        return drift
    successful, _failed = fetch_citation_context(all_cites)
    for cite, tagged_fetchable in tags.items():
        actually_fetched = cite in successful and bool(successful[cite].strip())
        if actually_fetched != tagged_fetchable:
            drift.append(
                f"DRIFT: {cite} tagged fetchable={tagged_fetchable} but fetch "
                f"{'succeeded' if actually_fetched else 'failed'}"
            )
    return drift


def write_reports(results_dir, run_results, format_errors, regressions, notes, gap_lines):
    """Write timestamped .json and .md reports; return the md path."""
    os.makedirs(results_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = os.path.join(results_dir, f"judge_eval_{ts}.json")
    md_path = os.path.join(results_dir, f"judge_eval_{ts}.md")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "results": run_results,
                "format_errors": format_errors,
                "regressions": regressions,
                "notes": notes,
            },
            f,
            indent=2,
        )
    lines = [f"# P-JUDGE eval report ({ts})", ""]
    for r in run_results:
        lines.append(f"## {r['case_id']}: overall {r['overall']}")
        for dim, score in r["dimensions"].items():
            detail = r["judge_detail"][dim]
            flags = f" flags: {detail['flags']}" if detail.get("flags") else ""
            lines.append(f"- {dim}: {score} ({detail['band']}){flags}")
        if r["capped_note"]:
            lines.append(f"- NOTE: {r['capped_note']}")
        if r["overall_mismatch"]:
            lines.append(
                f"- NOTE: model overall {r['model_overall_crosscheck']} differs from recomputed {r['overall']}"
            )
        if r["unmatched_starved_cites"]:
            lines.append(
                f"- NOTE: judge reported starved cites not in expected list: {r['unmatched_starved_cites']}"
            )
        lines.append("")
    lines.append("=== RETRIEVAL GAP ===")
    lines.extend(gap_lines or ["(no expected citations declared)"])
    lines.append("")
    if format_errors:
        lines.append("## Format errors")
        lines.extend(f"- {e}" for e in format_errors)
    if regressions:
        lines.append("## Regressions")
        lines.extend(f"- {r}" for r in regressions)
    if notes:
        lines.append("## Notes")
        lines.extend(f"- {n}" for n in notes)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return md_path


def build_gap_lines(run_results, cases) -> list:
    """Per-retrieval-class counts for the RETRIEVAL GAP section."""
    class_total = {}
    class_starved = {}
    starved_by_case = {r["case_id"]: {s["cite"] for s in r["context_starved"]} for r in run_results}
    for case in cases:
        starved = starved_by_case.get(case["case_id"], set())
        for e in case["expected_citations"]:
            cls = e["retrieval_class"]
            class_total[cls] = class_total.get(cls, 0) + 1
            if e["cite"] in starved:
                class_starved[cls] = class_starved.get(cls, 0) + 1
    lines = []
    for cls in sorted(class_total):
        starved_n = class_starved.get(cls, 0)
        lines.append(
            f"{cls}: {starved_n}/{class_total[cls]} expected citations unverifiable from sources"
        )
    for r in run_results:
        lines.append(f"{r['case_id']}: grounding_coverage = {r['grounding_coverage']:.2f}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description="P-JUDGE offline eval harness (real API; costs money)")
    default_cases = os.path.join(PROJECT_ROOT, "test-scripts", "judge_eval", "cases")
    parser.add_argument("--cases-dir", default=default_cases)
    parser.add_argument("--only", help="run a single case id")
    parser.add_argument(
        "--baseline",
        default=os.path.join(PROJECT_ROOT, "test-scripts", "judge_eval", "baseline", "baseline_scores.yaml"),
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="write this run's scores as the new baseline (explicit only; never automatic)",
    )
    parser.add_argument(
        "--confirm-retrieval",
        action="store_true",
        help="re-run fetch_citation_context to assert fetchable tags have not drifted (costs CSE calls)",
    )
    args = parser.parse_args()

    import yaml

    sys.path.insert(0, PROJECT_ROOT)
    from litassist.prompts import PROMPTS
    from litassist.llm.factory import LLMClientFactory

    case_files = sorted(
        os.path.join(args.cases_dir, f)
        for f in os.listdir(args.cases_dir)
        if f.endswith(".yaml")
    )
    cases = [load_case(p) for p in case_files]
    if args.only:
        cases = [c for c in cases if c["case_id"] == args.only]
        if not cases:
            sys.exit(f"No case with id {args.only}")

    drift = confirm_retrieval(cases) if args.confirm_retrieval else []
    for d in drift:
        print(d)

    client = LLMClientFactory.for_command("judge-eval")
    run_results = []
    format_errors = []
    for case in cases:
        print(f"[JUDGE] {case['case_id']} ({case['command']}) ...")
        messages = build_messages(case, PROMPTS)
        # skip_citation_verification: the judge's verdict text quotes fixture
        # citations (some deliberately unfetchable) and must not itself be
        # citation-verified.
        response, usage = client.complete(messages, skip_citation_verification=True)
        try:
            result = score_case(case, response)
            run_results.append(result)
            print(
                f"  overall {result['overall']}, coverage {result['grounding_coverage']:.2f}, "
                f"tokens {usage.get('total_tokens', '?')}"
            )
        except JudgeFormatError as e:
            format_errors.append(f"JUDGE_FORMAT_ERROR: {case['case_id']}: {e}")
            print(f"  JUDGE_FORMAT_ERROR: {e}")

    scores = {r["case_id"]: dict(r["dimensions"], overall=r["overall"]) for r in run_results}

    regressions = []
    notes = []
    if args.update_baseline:
        os.makedirs(os.path.dirname(args.baseline), exist_ok=True)
        existing_tolerance = DEFAULT_TOLERANCE
        if os.path.exists(args.baseline):
            with open(args.baseline, "r", encoding="utf-8") as f:
                existing_tolerance = (yaml.safe_load(f) or {}).get("tolerance", DEFAULT_TOLERANCE)
        with open(args.baseline, "w", encoding="utf-8") as f:
            yaml.safe_dump({"tolerance": existing_tolerance, "cases": scores}, f, sort_keys=True)
        print(f"Baseline updated: {args.baseline}")
    elif os.path.exists(args.baseline):
        with open(args.baseline, "r", encoding="utf-8") as f:
            baseline = yaml.safe_load(f) or {}
        regressions, notes = compare_to_baseline(scores, baseline)
    else:
        notes.append(f"No baseline at {args.baseline}; run with --update-baseline to create one")

    gap_lines = build_gap_lines(run_results, cases)
    results_dir = os.path.join(PROJECT_ROOT, "test-scripts", "judge_eval", "results")
    md_path = write_reports(results_dir, run_results, format_errors, regressions, notes, gap_lines)

    print()
    print("=== RETRIEVAL GAP ===")
    for line in gap_lines:
        print(line)
    for msg in format_errors + regressions + drift + notes:
        print(msg)
    print(f"Report: {md_path}")

    return 1 if (format_errors or regressions or drift) else 0


if __name__ == "__main__":
    sys.exit(main())
