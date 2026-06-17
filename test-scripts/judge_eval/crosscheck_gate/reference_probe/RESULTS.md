# Reference-grounding probe: do sources make fabricated facts detectable?

Last updated: 15/06/2026

## Question

The N=15 detection benchmark ran every arm with NO `--reference`. Under that
condition both baseline `verify` and `verify --cross-check` reliably caught 4
defect classes (confab cite, real-cite-wrong-prop, jurisdiction, contradiction)
but BOTH missed plausible, internally-consistent **fabricated facts** - there was
no ground truth to check them against. This probe tests whether supplying the
source document via `--reference` (real `litassist verify` usage) flips those
misses.

## Method

4 probes, each a document carrying one plausible fabricated fact the N=15 run
missed. One paid run per probe per round:

    litassist verify <variant> --cross-check --reference <source>

A default `verify` (no stage flag) runs citations + soundness + reasoning, so one
run yields BOTH arms:
- baseline-with-reference = soundness + reasoning reports (these receive
  `reference_context` in normal usage)
- cross-check-with-reference = the multi-model panel + arbiter report

Two rounds, differing only in how the source treats the fabricated fact:
- **Round B (explicit-negative):** source affirmatively states the opposite
  ("No expert reports have been commissioned"). Easy case.
- **Round C (absence-only):** the explicit denials were stripped; the fact is
  merely ABSENT from the source. Harder, more realistic case.

Each report scored by an INDEPENDENT subagent requiring a verbatim quote naming
the specific fabricated fact as unsupported-by-reference before crediting a CATCH
(guards against lenient self-scoring).

## Result

| Probe | Fabricated fact | A: no-ref (N=15) | B: explicit-neg | C: absence-only |
|---|---|---|---|---|
| criminal_sentencing | Dr Markovic psych report | MISS | CAUGHT | CAUGHT (MEDIUM) |
| affidavit | Venkataraman 2 May email | MISS | CAUGHT | CAUGHT |
| olsc_complaint | 9 Jul concession email | MISS | CAUGHT | CAUGHT |
| migration_review | delegate "false evidence" finding | MISS | CAUGHT | CAUGHT |

In BOTH rounds, all 4 flipped from MISS to CATCH at the **baseline soundness +
reasoning stages** - the stages that receive the reference in normal `verify`
usage. Cross-check also caught 4/4 in both rounds.

## What the absence-only round (C) showed beyond round B

1. Source-grounding works even with NO contradicting sentence: the stages flag
   the asserted fact as "not listed among the brief materials" / "not corroborated
   by reference materials" / "does not appear anywhere in the delegate's decision".
2. Severity is honestly calibrated: explicit-negative -> HIGH/"fabricated";
   absence-only -> MEDIUM/"confirm with instructions" (correct: a report could
   legitimately have been obtained after the brief).
3. Detection in 3/4 absence cases leaned on the source's ENUMERATED INVENTORY
   (materials/documents lists). The one purely-narrative source with no inventory
   (migration) was still caught - but there the cross-check + reasoning carried it;
   soundness was weaker and less explicit about source-silence.
4. The cross-check earns its keep specifically in the hard absence case: it was
   the most consistent and explicit at tying the assertion to the reference's
   silence (all three panellists compared assertion vs source), where soundness
   sometimes hedged. This is the cross-check's clearest distinct value found so far
   on fabricated facts - redundancy + convergent severity, not unique catching.

## Cost

| Round | Cost | Calls |
|---|---|---|
| B explicit-negative | $5.08 | 24 (6/run x 4) |
| C absence-only | $4.50 | 24 |
| **Total** | **$9.58** | 48 |

Per-run mean ~$1.20-1.27. Worst-case-HIGH quoted before each round ($16, then $8)
was not approached. Per-model (round B): opus-4.7 $1.76, sonnet-4.6 $1.45,
o3-pro $1.00, gpt-5.5 $0.88.

## Decision this drives

Confirms the plan's leading branch: **fabrication detection is a function of
HAVING THE SOURCE, not of the ensemble.** Real `verify --reference` already
handles it, even on pure absence. The N=15 "miss" was a no-reference artifact.

Two consequences:

1. **Cross-check SHELVED (15/06/2026).** The cross-check adds no unique detection
   value over a plain `verify --reference`: plain three-stage verify with a source
   caught 4/4, and the ensemble's only margin is redundancy and convergent severity
   on contradictions - not justified at its 3-4x cost. The `--cross-check` flag and
   `ensemble.py` are retained but not recommended; P2-19 (which reused the plumbing)
   is parked. No code change.

2. **Documentation.** State plainly that fabricated-fact detection requires
   `--reference` (or case_facts as the document's factual basis); without a source
   the verifier has nothing to check a plausible fabrication against, and `verify`
   flags rather than fixes. Corrected in ROADMAP P1-12, CHANGELOG, the user guide,
   the reference manual, and the verification dev doc.

Parked follow-up (separate session): test whether CoVe (`--cove --cove-reference`)
is a stronger per-assertion fabrication detector (plan:
`~/.claude/plans/test-cove-fabrication-detection.md`). A second parked idea: the
arbiter receives only the panel reviews, never the reference (ensemble.py:179-186),
so the panel does the source comparison and the final DISAGREEMENT LEVEL is one
layer removed - but this is moot while the cross-check is shelved.

## Artefacts

- Sources: `reference_probe/sources/` (round B), `reference_probe/sources_absence/`
  (round C).
- Variants reused from `detection_set2/` and `detection_set3/variants/`.
- Run consoles: `reference_probe/results/probeB_*.console.log`,
  `probeC_*.console.log`. Reports in `outputs/claude_probeB_*`, `claude_probeC_*`.
