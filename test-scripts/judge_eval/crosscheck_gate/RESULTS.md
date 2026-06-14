# P1-12 cross-check gate - results

Last updated: 14/06/2026
Run: 14/06/2026, branch `feat/verify-crosscheck`. Real-API, manual. Raw artefacts
in the gitignored `results/`; this is the committed summary.

## Verdict: SHIP

All four criteria pass. Criterion 4 (cost) was re-measured with actual OpenRouter
`usage.cost` (14/06/2026) after the local `estimate_call_cost` estimator was
removed for undercounting the invoice. **N=5 real `verify --cross-check` runs
across different matters/sizes: marginal ratio mean 2.71x, range 1.41-3.93x, all
<= 4x** (full table below). The 3.93x worst case is the draft - driven by its
large cross-check cost (biggest document), not its baseline; the four fresh
fixtures sit 1.4-3.3x.

| # | Criterion | Threshold | Measured | Pass |
|---|-----------|-----------|----------|------|
| 1 | treatment-arm recall | >= 14/20 | 20/20 | yes |
| 2 | defects cross-check caught that baseline verify missed | >= 4 | 6 | yes |
| 3 | spurious HIGH disagreement on the 4 clean originals | <= 1 | 0 | yes |
| 4 | marginal cost vs baseline verify (actual `usage.cost`, N=5) | <= 4x | mean 2.71x, max 3.93x | yes |

## Detection (seeded-defect arm)

Each variant carries 5 seeded defects. "baseline" = the citation/soundness/
reasoning reports of the same `--cross-check` run (identical to a no-cross-check
run; the stage consumes no prior-stage output). "cross-check" = the arbiter report.

| Variant | seeded | baseline caught | cross-check caught | treatment-only |
|---------|--------|-----------------|--------------------|----------------|
| draft        | 5 | 3 (D1,D2,D3) | 5 | D4 (fabricated), D5 (contradiction) |
| strategy     | 5 | 4 (S1-S4)    | 5 | S5 (fabricated) |
| lookup       | 5 | 4 (L1-L4)    | 5 | L5 (fabricated) |
| extractfacts | 5 | 3 (E1,E2,E3) | 5 | E4 (contradiction), E5 (fabricated) |
| **Total**    | **20** | **14** | **20** | **6** |

### By defect class

| Class | seeded | baseline caught | cross-check caught |
|-------|--------|-----------------|--------------------|
| confabulated citation        | 4 | 4 | 4 |
| real-cite-wrong-proposition  | 4 | 4 | 4 |
| jurisdiction error           | 4 | 4 | 4 |
| internal contradiction       | 4 | 2 | 4 |
| fabricated fact              | 4 | 0 | 4 |

The cross-check's entire marginal value is in the **fabricated-fact** class (0/4 ->
4/4) and **internal contradiction** (2/4 -> 4/4). Citation/jurisdiction defects are
already caught by the existing citation-verification + soundness (Opus 4.7) stages,
so the retrieval gap does not bias the comparison - both arms catch those equally.
The honest read: the ensemble is not a better citation checker; it is a fabricated-
fact and contradiction detector that the single-pass soundness stage misses.

## False-positive arm (clean originals, `--citations --cross-check`)

| Original | disagreement level | spurious HIGH? |
|----------|--------------------|----------------|
| draft        | LOW    | no |
| strategy     | LOW    | no |
| lookup       | MEDIUM | no (reflects the pre-existing Falvo/Action Paintball cites in the fixture) |
| extractfacts | MEDIUM | no |

0 HIGH flags. The two MEDIUMs are defensible (residual issues in the post-
verification fixtures), not hallucinated alarm.

## Cost - actual OpenRouter `usage.cost`, N=5 (14/06/2026)

Measured with the actual-cost capture (the prior `estimate_call_cost` figures are
removed - they undercounted the invoice). Cross-check totals from the live
`[COST]` banners; baseline (reasoning + soundness) from the per-call audit-log
`usage.cost`. Five real `verify --cross-check` runs across different matters and
sizes:

| Document | size | baseline (reasoning+soundness) | cross-check stage | marginal |
|----------|------|--------------------------------|-------------------|----------|
| draft_harper (reasoning trace reused) | 14KB | $0.37 | $1.47 | 3.93x |
| contract supply dispute | 2.5KB | $0.39 | $0.55 | 1.41x |
| unfair dismissal | 2.2KB | $0.28 | $0.71 | 2.56x |
| tenancy bond | 1.6KB | $0.17 | $0.55 | 3.27x |
| defamation concerns notice | 2.4KB | $0.29 | $0.69 | 2.37x |

- **Marginal ratio mean 2.71x, range 1.41-3.93x; all five <= 4x.**
- The 3.93x case is the draft. The dominant driver is its large cross-check cost
  ($1.47 - it is the biggest document, 14KB, so the panel input/output is the
  largest), not its baseline (tenancy_bond has a lower baseline, $0.17 vs $0.37,
  yet only 3.27x). The draft's reused reasoning trace (no reasoning LLM call)
  additionally trims its baseline, compounding the ratio. The four fresh fixtures
  sit 1.4-3.3x.
- Cross-check absolute cost scales with document size ($0.55-$1.47); o3-pro is the
  largest single call. The earlier estimator's $1.06 "marginal" figure was both
  wrong in method and not comparable.
- Fixtures: `cost_fixtures/`. N=5 cost spend ~$4.5.

## Caveats (stated, not hidden)

- n=4, one fictional matter (Harper) - first-cut, same standard P-JUDGE shipped
  under. Defects were authored by the implementer (overfit risk); the ensemble
  prompts were frozen at commit `10646a4` before these runs.
- Disagreement level was LOW on all four seeded variants: the three models AGREED
  the documents were defective. Detection works through report content, not the
  disagreement level - the level is the uncertainty signal, orthogonal to recall.
- Scoring is deterministic (inspection against `manifest.yaml`); no LLM judge, so
  no self-grading against the gpt-5.5 panellist.
