# P1-12 cross-check gate - results

Last updated: 14/06/2026
Run: 14/06/2026, branch `feat/verify-crosscheck`. Real-API, manual. Raw artefacts
in the gitignored `results/`; this is the committed summary.

## Verdict: SHIP on detection; cost criterion UNVERIFIED

Criteria 1-3 (detection) pass. Criterion 4 (cost) is NOT established: its figures
came from the local `estimate_call_cost` estimator, since removed (14/06/2026) for
undercounting the OpenRouter invoice 3-9x on reasoning-heavy o3 calls. Re-measure
the cost criterion with the new actual-cost capture (`usage.cost`) on a fresh
`verify --cross-check` run before treating it as met.

| # | Criterion | Threshold | Measured | Pass |
|---|-----------|-----------|----------|------|
| 1 | treatment-arm recall | >= 14/20 | 20/20 | yes |
| 2 | defects cross-check caught that baseline verify missed | >= 4 | 6 | yes |
| 3 | spurious HIGH disagreement on the 4 clean originals | <= 1 | 0 | yes |
| 4 | marginal cost vs baseline verify | <= 4x | est. 3.6x total / 2.6x marginal (estimator removed) | UNVERIFIED |

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

## Cost (from `[COST]` banners; gate-era figures were local estimates)

> Note: the figures below were produced by the since-removed local estimator
> (`estimate_call_cost`), which undercounted vs the OpenRouter invoice. Cost is now
> read from OpenRouter's actual `usage.cost`; treat these as rough lower bounds.


- baseline verify (reasoning + soundness LLM calls) ~ **$0.41 / document** (the
  citation stage is CSE, negligible LLM cost).
- cross-check marginal (3 panel + arbiter) ~ **$1.06 / document** (detection arm:
  draft $1.01, strategy $1.20, lookup $0.74, extractfacts $1.28).
- total treatment ~ $1.47/doc = **3.6x** baseline; marginal alone = **2.6x**. Within
  the ROADMAP 2-4x envelope. o3-pro is the dominant single cost (~$0.52/call).
- Total gate spend across the 8 runs: ~$11.

## Caveats (stated, not hidden)

- n=4, one fictional matter (Harper) - first-cut, same standard P-JUDGE shipped
  under. Defects were authored by the implementer (overfit risk); the ensemble
  prompts were frozen at commit `10646a4` before these runs.
- Disagreement level was LOW on all four seeded variants: the three models AGREED
  the documents were defective. Detection works through report content, not the
  disagreement level - the level is the uncertainty signal, orthogonal to recall.
- Scoring is deterministic (inspection against `manifest.yaml`); no LLM judge, so
  no self-grading against the gpt-5.5 panellist.
