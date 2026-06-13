# P1-12 cross-check measurement gate

Last updated: 14/06/2026

Decides whether `verify --cross-check` (ROADMAP P1-12) ships (status flip +
caseplan exposure) or shelves with evidence. Manual, real-API, NOT pytest.

## Why this gate, not the literal P-JUDGE one

ROADMAP P1-12 originally said "ship only if the P-JUDGE before/after per-dimension
delta is positive". The cross-check is read-only - it never rewrites the document
- so the before/after document is byte-identical and that delta is zero by
construction. This gate substitutes the honest question a read-only checker can
actually answer: **does it catch defects baseline `verify` misses, at acceptable
cost?**, scored deterministically (no LLM judge - the judge model, gpt-5.5, is also
a panel member, so judge-scoring would be self-grading).

## Method

- **Fixtures:** 4 Harper-benchmark outputs (draft, strategy, lookup, extractfacts)
  copied to `variants/`, each seeded with 5 documented defects (20 total) across
  five classes: confabulated citation, real-cite-wrong-proposition, jurisdiction
  error, internal contradiction, fabricated fact. The seeded edits are the only
  differences from `../cases/*.output.md` (see `/tmp/seed_defects.py` provenance in
  the commit). `manifest.yaml` (frozen before any run) lists each defect's
  detection criterion. The lookup original already contains two confabulations
  (`Falvo`, `Action Paintball`) recorded as `pre_existing_not_scored`.
- **Detection arm (4 runs):** `litassist verify variants/<v>.variant.md --cross-check`.
  A single `--cross-check` run yields BOTH the baseline reports (citations /
  soundness / reasoning, identical to a no-cross-check run because the stage
  consumes no prior-stage output) AND the cross-check report. So one run gives the
  baseline-vs-treatment comparison without a separate baseline run.
  - **baseline detection** = defects named in the citation/soundness/reasoning reports.
  - **treatment-only detection** = defects named in the cross-check report that the
    baseline reports did not catch.
- **False-positive arm (4 runs):** `litassist verify ../cases/<v>.output.md
  --citations --cross-check` (the cheap core path; cross-check sees the original
  text regardless). Count cross-check HIGH flags that do not correspond to a real
  issue in the clean original.
- **Scoring:** by inspection against `manifest.yaml`, recorded in `results/`.
- **Cost:** from the `[COST]` banners / audit logs.

## Pre-registered ship criteria (all four)

1. treatment-arm recall >= 14/20 seeded defects;
2. >= 4 defects detected by the cross-check that baseline verify missed;
3. <= 1 spurious HIGH disagreement across the 4 clean originals;
4. measured marginal cost <= 4x baseline verify cost per document.

Otherwise: **shelve with evidence** - the results table goes into ROADMAP P1-12
(status SHELVED), the cross-check stays unmerged/unflipped, and commit 1 (cost.py)
is kept regardless.

Citation-class defects (confab + wrongprop) are reported separately from the rest
so the retrieval-gap confound (un-fetchable cites starve both arms equally) stays
visible.

`results/` is gitignored (run artefacts); `variants/` and `manifest.yaml` are
committed fixtures.
