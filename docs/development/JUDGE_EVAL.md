# P-JUDGE offline eval harness

Last updated: 14/06/2026

Repeatable, real-API quality scoring of litassist outputs against a rubric,
so prompt/model changes are measured rather than guessed. This is ROADMAP
item P-JUDGE, the measurement keystone the ensemble items (P1-12, P2-19)
are gated on.

## What it is

`test-scripts/test_judge_eval.py` sends fixture outputs (real litassist
command outputs, frozen in the repo) to an LLM judge (model role
`judge-eval` in `litassist/llm/model_configs.yaml`, prompts in
`litassist/prompts/judge_eval.yaml`) and scores them 0-100 on up to five
dimensions:

- `citation_grounding` - propositions supported by citations whose substance
  is verifiable from the supplied SOURCES (never from the judge's own
  knowledge - see anti-laundering below).
- `structure` - conformance to the named structure contract the generating
  command promises (e.g. `formats.case_facts_10_heading` for extractfacts).
  Declared only for cases that have such a contract.
- `australian_english` - graduated penalties, never hard caps.
- `faithfulness` - no facts invented beyond SOURCES; explicit placeholders
  like `[DATE TO BE CONFIRMED]` are correct behaviour, not penalised.
- `aglc_format` - AGLC4 conventions as far as plain text allows.

Each case declares its dimension subset; `overall` is the unweighted mean,
recomputed by the harness (the judge's own `overall` is only a cross-check).

This is a manual, paid script (real OpenRouter calls). It is NOT part of
pytest. Its pure parsing/scoring functions are covered offline by
`tests/unit/test_judge_eval_harness.py`.

## Running it

```bash
python test-scripts/test_judge_eval.py                 # full benchmark vs baseline
python test-scripts/test_judge_eval.py --only <case_id>
python test-scripts/test_judge_eval.py --update-baseline   # explicit only
python test-scripts/test_judge_eval.py --confirm-retrieval # re-check fetchable tags (CSE calls)
```

Exit is non-zero on any JUDGE_FORMAT_ERROR, baseline REGRESSION, or (with
`--confirm-retrieval`) fetchable-tag drift. Reports (.json + .md) go to
`test-scripts/judge_eval/results/` (gitignored); full request/response
audit logs land under `logs/` via the standard LLM client logging.

## Case schema

`test-scripts/judge_eval/cases/<id>.yaml`:

```yaml
case_id: extractfacts_harper
command: extractfacts
dimensions: [citation_grounding, structure, australian_english, faithfulness, aglc_format]
structure_template_key: formats.case_facts_10_heading   # required iff structure declared
output_file: extractfacts_harper.output.md              # relative to the case file
source_files:                                           # what the generating command saw
  - ../sources/claude_brief_harper_negligence.md
expected_citations:
  - cite: "Wyong Shire Council v Shirt (1980) 146 CLR 40"
    fetchable: false
    retrieval_class: authorised_report
  - cite: "Roads and Traffic Authority of NSW v Dederer [2007] HCA 42"
    fetchable: true
    retrieval_class: fetchable
```

`retrieval_class` values: `fetchable`, `authorised_report` (no
medium-neutral cite, so no AustLII URL is constructible - see TODO C1/C2),
`jade_spa` (Jade.io is SPA/auth-gated and skipped by the fetcher),
`austlii_pdf_blocked` (Cloudflare-blocked PDF paths), `not_found` (the
citation does not correspond to a retrievable real authority, e.g. a
confabulated cite or a case named without any citation), and
`fetch_failed` (a real authority for which the pipeline currently returns
no validated content - measured, not assumed). Tags are MEASURED with
`fetch_citation_context`, not reasoned about; `--confirm-retrieval`
re-derives the truth and reports drift.

## The retrieval-gap design (load-bearing)

The binding constraint on verification quality is retrieval, not the
verifier: whole citation classes return nothing today. The harness keeps
that visible instead of letting the judge launder it:

1. The judge is forbidden from using its own knowledge to confirm any
   citation absent from SOURCES (otherwise a frontier model silently
   "recognises" famous cites and the gap disappears from the scores).
2. The judge must list every expected citation it could not verify from
   SOURCES in `context_starved_citations`.
3. The harness computes `grounding_coverage = verifiable / total expected`
   and caps `citation_grounding` at `round(100 * coverage)`. A case
   leaning on an unfetchable cite cannot score 100 while the gap exists.
4. The report's `=== RETRIEVAL GAP ===` section counts unverifiable cites
   per retrieval class. When later retrieval work (e.g. the
   traditional-to-neutral cite primitive, Jade cookie fetch) lands, tags
   flip to `fetchable: true`, the ceiling lifts, and the eval registers
   the gain as a measured improvement.

## Baseline policy

`test-scripts/judge_eval/baseline/baseline_scores.yaml` holds per-case
per-dimension scores plus a single `tolerance` (default 8: covers the
single-digit run-to-run variance observed on deterministic-judge reruns
while catching real regressions; recalibrate from evidence).

- Drops below `baseline - tolerance` are REGRESSIONS (non-zero exit).
- Improvements beyond tolerance and new cases are notes, never failures.
- The baseline only moves via `--update-baseline` (explicit), after a human
  sanity-checks the numbers. A run never silently moves the goalposts.

## Benchmark fixtures

First-cut benchmark: one fictional NSW negligence matter (Harper v
Glenbrook Adventure Park) drives four cases - extractfacts, lookup
(IRAC), strategy, draft - generated with the real CLI from
`test-scripts/judge_eval/inputs/claude_brief_harper_negligence.md`. The
brief deliberately seeds authorised-report-only citations (Wyong, March v
Stramare) and a UK report (Donoghue) alongside a fetchable neutral cite
(Dederer [2007] HCA 42), so the retrieval gap is present from day one.
The `jade_spa` and `austlii_pdf_blocked` classes are defined in the schema
but not yet seeded in fixtures; tag them when a fixture's citations hit
those classes.

SOURCES fixtures are what the generating command actually saw: the input
brief for extractfacts, the case_facts input for strategy/draft, and the
retrieved search content (from the audit log of the generating run) for
lookup.

## First calibration (11/06/2026)

Zero format errors across the four cases; baseline captured at tolerance 8.
Overall scores: draft 82, extractfacts 77, strategy 73, lookup 57.
Grounding coverage: draft 0.89, extractfacts 0.56, strategy 0.33,
lookup 0.00 - the caps fired on lookup (25 -> 0) and strategy (35 -> 33).
The judge caught the seeded traps: the verification-stage Zaluzna
substitution flagged as not present in SOURCES, the confabulated Falvo v
Oztag citation flagged as absent, the "no verbal warnings" overstatement of
"does not recall any verbal warnings", and genuine American spellings in
the lookup output. The headline finding matches the thrust's premise: the
generation pipeline asserts far more authority than its retrieval provides
(lookup wrote its entire IRAC analysis with zero source-verifiable
citations), so retrieval work, not more verification, lifts the ceiling.

Tag verification (same day, via `fetch_citation_context` over the 22
distinct expected-citation strings across the four cases; the two March
v Stramare forms count separately because fetching keys on the exact
string): of the 13 strings tagged fetchable by assumption, only 3
actually fetched - Dederer [2007] HCA 42, Moore v Scenic Tours [2020]
HCA 17 (hcourt.gov.au judgment summary PDF) and the Competition and
Consumer Act 2010 (Cth). Every bare statute title and every NSWCA
neutral citation returned no validated content. A single-case rerun
scored within 1 point of baseline (lookup 56 vs 57), supporting the
+/-8 tolerance.

That measurement triggered three retrieval fixes (11/06/2026): the
anchored-regex bug in `construct_austlii_url` that disabled the direct
AustLII fallback for named neutral citations, jurisdiction-aware
legislation link filtering and validation, and a guard stopping Jina
dispatches to austlii.edu.au (always Cloudflare-challenged). A first
post-fix re-measurement showed 12 of 22 fetching, but three of those
(CLA NSW, Evidence Act NSW, UCPR NSW) had validated on arbitrary
SECTION pages of the right act - an overstatement the validation
strategy now refuses for whole-act citations (section-page guard,
same day). Final measured state: **9 of the 22** distinct citation
strings fetch - the four NSWCA cases via direct AustLII URL, the
Limitation Act 1969 (NSW) and Civil Procedure Act 2005 (NSW) via their
act-root pages, plus the original three (Dederer, Moore, CCA (Cth)).
The 13 that do not, by class: 7 authorised-report/overseas strings
(Wyong, both March v Stramare forms, Zaluzna, Darlington Futures,
Oceanic Sun Line, Calderbank - TODO C2 territory), 2 `not_found` (the
confabulated Falvo cite and the citation-less Action Paintball
reference), and 4 `fetch_failed` statutes whose act-root pages CSE does
not surface in its top results (DCA, CLA, Evidence Act, UCPR - a CSE
recall limitation, distinct from the fixed defects). The judge baseline
is unchanged: tags do not feed scoring, and the fixture SOURCES are
frozen.

## Gate for P1-12 / P2-19

The original idea was: run each benchmark case through the candidate pipeline,
judge both sides, ship only if the mean per-dimension delta is positive and worth
the added cost.

**This does not work for a read-only stage.** The P1-12 cross-check never rewrites
the document, so the before/after document is byte-identical and the judged delta
is zero by construction. Two further problems: the judge model (`judge-eval` ->
`openai/gpt-5.5`) is also a cross-check panel member, so judge-scoring the panel is
self-grading; and what a read-only checker delivers is *detection*, not a quality
lift the judge rubric measures.

### Substituted gate (used for P1-12, 14/06/2026): deterministic seeded-defect detection

Fixtures, protocol and pre-registered ship criteria live alongside the harness in
`test-scripts/judge_eval/crosscheck_gate/` (`README.md` = protocol, `manifest.yaml`
= frozen defect list, `RESULTS.md` = committed outcome, `variants/` = the 4 seeded
Harper outputs). In outline: seed 5 documented defects into each of the 4 benchmark
outputs (20 total) across five classes (confabulated cite, real-cite-wrong-
proposition, jurisdiction error, internal contradiction, fabricated fact); run
`verify --cross-check` on each; score detection deterministically against the
manifest by inspection (no LLM judge); compare cross-check detections against the
same run's baseline citation/soundness/reasoning reports; measure spurious HIGH
flags on the 4 clean originals and the cost ratio from the `[COST]` banners.

Ship iff: recall >= 14/20, >= 4 defects caught that baseline missed, <= 1 spurious
HIGH on clean docs, marginal cost <= 4x baseline. **P1-12 result: PASS (20/20, 6
treatment-only, 0 spurious HIGH, 2.6x marginal / 3.6x total cost).** The marginal value was entirely in
the fabricated-fact (0/4 -> 4/4) and internal-contradiction (2/4 -> 4/4) classes;
the existing citation/soundness stages already catch citation and jurisdiction
defects, so the retrieval gap did not bias the comparison.

P2-19 (divergence detector) reuses the same fixtures and the same deterministic
approach when it is built.
