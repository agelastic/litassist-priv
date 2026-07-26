# LitAssist LLM evaluation and update recommendations

Last updated: 26/07/2026

| Field | Value |
|---|---|
| Config evaluated | `litassist/llm/model_configs.yaml` (last updated 13/06/2026) |
| Capability snapshot | `litassist/llm/model_capabilities.yaml` (regenerated 10/06/2026) |
| Prior audits | `LitAssist_Model_Audit_OpenRouter_2026-04-21.md`, `LitAssist_Model_Replacement_Recommendations_2026-04-21.md` (snapshot 27/06/2026) |
| External sources | Vendor announcements and OpenRouter model pages fetched 26/07/2026 (links in Section G) |
| Scope | Evaluation and recommendations only. No code, config, or prompt changes are made by this document. |

This report answers three questions: (1) are the models currently pinned still fit for their stated purposes; (2) should any pins move to the July 2026 releases from Anthropic, OpenAI, xAI, Google, and Meta; (3) should prompts be reworked for current prompting and context-engineering guidance.

---

## A. Current inventory and fitness for stated purpose

Six distinct models serve 30 command configs. Stated purposes are taken from the comments in `model_configs.yaml`.

| Model | Roles | $/1M in/out | Fitness verdict |
|---|---|---|---|
| `anthropic/claude-sonnet-4.6` | Workhorse: extractfacts, brainstorm-orthodox, digest, verify-reasoning, caseplan-assessment, CoVe chain, faithfulness (14 configs) | $3 / $15 | **Sound.** Chosen because temperature/top_p are honoured (deterministic extraction) and 1M context. Still active and still the last Anthropic tier that honours sampling params. One generation behind Sonnet 5 (same list price). |
| `anthropic/claude-opus-4.7` | Heavy strategic reasoning: strategy, verify-soundness, caseplan | $5 / $25 | **Sound but two generations behind.** Opus 4.8 and now Claude Opus 5 exist at the same $5/$25. Nothing broken; capability left on the table at identical price. |
| `openai/o3-pro` | strategy-analysis, brainstorm-analysis, draft, counselnotes, barbrief | $20 / $80 | **No longer fit. Action required.** Priciest pin in the stack; 200K context (smallest in the stack, used by the largest-input commands); knowledge cutoff June 2024; BYOK-configured; and OpenAI has scheduled the `o3-pro-2025-06-10` snapshot for API retirement on 11/12/2026. This pin now has a hard deadline. |
| `openai/gpt-5.5` | Verification stack: verification(-heavy), verify-*-heavy, cove-answers(-heavy), faithfulness-align, judge-eval | $5 / $30 | **Sound but superseded.** GPT-5.6 (09/07/2026) offers the same price at the flagship tier (Sol) and half price at the mid tier (Terra, $2.50/$15) with the same 1.05M context. |
| `google/gemini-3.5-flash` | Cheap high-context: updatefacts, lookup, lookup-irac, lookup-broad | $1.50 / $9 | **Sound but superseded.** Gemini 3.6 Flash (21/07/2026) is the direct successor: $1.50/$7.50, emits ~17% fewer output tokens, knowledge cutoff advanced from Jan 2025 to Mar 2026 (materially useful for case-law lookup). |
| `x-ai/grok-4.3` | brainstorm-unorthodox | $1.25 / $2.50 | **Sound and empirically validated** (grok-4.20 refused ~2/3 of unorthodox trials; 4.3 passed 3/3 per `test_unorthodox_models.py`). Risk is xAI's retirement cadence, not quality: the entire Grok 3.x/4.x line was previously expired on a single day (15/05/2026), and Grok 4.6 is due late Aug-mid Sep. Expect an expiration date on 4.3. |

Overall: the model *selection logic* in this repo is in good shape — every pin has a documented reason, one was chosen by measurement, and the config/refresh/pytest loop guards swaps. The problem is drift: five of six pins have a successor released since the config was last touched (13/06/2026), and one pin has a retirement date.

---

## B. What changed since the 27/06/2026 audit

**Anthropic — Claude 5 family.** Claude Opus 5 (`$5/$25`, 1M context) is a drop-in successor to Opus 4.8 at unchanged pricing. Claude Sonnet 5 (`$3/$15`, introductory `$2/$10` through 31/08/2026, 1M context) succeeds Sonnet 4.6. Claude Fable 5 (`$10/$50`) is now confirmed as a real Anthropic release — the top "Mythos-class" tier above Opus — which resolves the "yellow flag" the June audit placed on it. Three API-surface changes matter for this repo:

- Opus 5 and Sonnet 5 remove/reject non-default sampling params (temperature/top_p/top_k), like Opus 4.7/4.8 already do. Sonnet 4.6 is the last Sonnet that honours them.
- Sonnet 5 uses a new tokenizer producing roughly 30% more tokens for the same text — token budgets and cost baselines shift even at flat per-token price.
- Fable 5 requires 30-day data retention (not available under zero-data-retention arrangements) and runs safety classifiers that can refuse — a consideration for a legal tool handling privileged material, and one to check against the practice's confidentiality posture before any use.

**OpenAI — GPT-5.6 and the o3-pro clock.** The GPT-5.6 family reached GA on 09/07/2026 in three tiers sharing a 1.05M context / 128K output: Sol ($5/$30), Terra ($2.50/$15), Luna ($1/$6). Two traps: the bare `gpt-5.6` alias routes and bills as Sol, so pins must name the tier explicitly (e.g. `openai/gpt-5.6-terra`); and requests over 272K input tokens bill at higher rates (Sol: $10/$45) — relevant to `draft`/`barbrief`, which consume large briefs. Separately, OpenAI announced on 11/06/2026 that the `o3-pro-2025-06-10` snapshot leaves the API on **11/12/2026**.

**Google — Gemini 3.6 Flash.** Released 21/07/2026: $1.50/$7.50, ~17% fewer output tokens for equivalent work, DeepSWE 49% (vs 37% for 3.5 Flash), knowledge cutoff Mar 2026. A lower-cost 3.5 Flash-Lite also shipped for high-volume mechanical work. No new Pro tier; Gemini 4 is in pre-training.

**xAI — Grok 4.5, with 4.6/4.7 imminent.** Grok 4.5 (08/07/2026): $2/$6, 500K context (down from 4.3's 1M), positioned as an Opus-class coding/agentic model. Grok 4.6 (~2T params) is confirmed and expected late August-mid September, with 4.7 behind it. Refusal posture of 4.5 on adversarial legal framings — the property that actually drove the 4.3 selection — is unpublished and must be measured.

**Meta — Muse Spark 1.1.** Released 09/07/2026 by Meta Superintelligence Labs, with the Meta Model API in public preview. Two corrections to how it was framed in the request:

1. **It is not a creativity model.** Despite the "Muse" name, Meta positions it as a multimodal *agentic/reasoning* model — tool and computer use, coding, multi-agent orchestration, 1M context — competing with GPT-5.5/Opus 4.8/Gemini. No creative-writing positioning appears in Meta's announcement or independent coverage.
2. **It is on OpenRouter (`meta/muse-spark-1.1`) but restricted to US developers.** For an Australian-focused tool operated from Australia, that is a hard availability blocker today.

Pricing is aggressive ($1.25/$4.25, +5.5% OpenRouter fee), which will make it an interesting cost-tier candidate *if* the regional restriction lifts and it demonstrates any AU-legal competence. Neither condition holds now.

---

## C. Per-role recommendations

Same notation as the June audit: **SWAP** (do it, subject to the standing A/B protocol), **TRIAL** (run the Section E protocol from `LitAssist_Model_Replacement_Recommendations_2026-04-21.md` first), **EVAL** (verify a material claim before trialling), **KEEP**.

| Priority | Roles | Current | Recommendation |
|---|---|---|---|
| **P0** | strategy-analysis, brainstorm-analysis, draft, counselnotes, barbrief | `openai/o3-pro` | **SWAP-by-deadline to `openai/gpt-5.6-terra`** (fallback: `-sol` if quality drops). Migration is forced by the 11/12/2026 retirement; doing it now also cuts output cost 81% (Terra) and lifts context 200K to 1.05M — removing the tightest window in the stack from the largest-input commands — and moves the knowledge cutoff forward ~2 years. Name the tier explicitly (bare `gpt-5.6` bills as Sol) and verify Terra's >272K-input surcharge on its OpenRouter page for `draft`/`barbrief` workloads. Also lets BYOK config be retired (`cli.py` special-case). |
| **P1** | brainstorm-unorthodox | `x-ai/grok-4.3` | **KEEP, but pre-qualify the successor now.** Re-run `test-scripts/test_unorthodox_models.py` against `x-ai/grok-4.5` (and 4.6 when it lands) so a validated fallback exists before xAI stamps an expiration date on 4.3, as it did to the whole 3.x/4.x line in May. Watch `litassist refresh` output for `expiration_date`. Note 4.5 costs more ($2/$6 vs $1.25/$2.50) and halves context to 500K — fine for brainstorming, but not an upgrade unless 4.3 is retired or 4.5 measures better on refusal rate. |
| **P2** | strategy, verify-soundness, caseplan | `anthropic/claude-opus-4.7` | **TRIAL `anthropic/claude-opus-5`** (skip 4.8). Same $5/$25, same 1M context, a two-generation capability step for heavy strategic reasoning — the stated purpose of these roles. Requires the code-side prep in Section D first. The June audit's "TRIAL Opus 4.8" rows are superseded by this. |
| **P2** | Sonnet 4.6 roles *except* extractfacts | `anthropic/claude-sonnet-4.6` | **TRIAL `anthropic/claude-sonnet-5`, ideally before 31/08/2026** while the $2/$10 introductory pricing makes the eval itself cheap. Near-Opus quality at Sonnet price is exactly what the workhorse tier wants. Two watch-outs: the ~30% tokenizer inflation partially offsets the price cut, and sampling params are rejected — determinism must come from `thinking_effort` + prompt wording. Move the CoVe chain as one unit (the June audit's "don't fragment the chain" reasoning stands). |
| **P2** | extractfacts | `anthropic/claude-sonnet-4.6` | **KEEP for now.** The pin's documented rationale — temperature 0 / top_p 0.15 honoured for deterministic structured extraction — does not survive a move to Sonnet 5, which rejects sampling params. Trial Sonnet 5 here only after the P2 trials above show effort-plus-prompt determinism holds on the 10-heading structure (parse-success and citation metrics per the standing protocol). |
| **P3** | updatefacts, lookup, lookup-irac, lookup-broad | `google/gemini-3.5-flash` | **TRIAL `google/gemini-3.6-flash`.** Direct successor: ~31% effective output-cost cut (17% lower price x 17% fewer tokens), fresher case-law knowledge (Mar 2026 cutoff). Lookup remains the most citation-sensitive command family, so the AU-citation eval gate from the June audit still applies — but this is a same-vendor generational step, the lowest-risk swap class available. For updatefacts (mechanical merge, cheapest-model-by-design), also price `google/gemini-3.5-flash-lite` as a further step down. |
| **P3** | verification stack (verification, *-heavy, cove-answers, faithfulness-align) | `openai/gpt-5.5` | **TRIAL `openai/gpt-5.6-terra`** for the non-heavy roles (-50% cost) and **`-sol`** for the `-heavy` roles (flat cost, newer model). Supersedes the June audit's "gpt-5.5 to opus-4.8" TRIAL rows — same-vendor continuity now comes with a price cut, which that option lacked. |
| **P4** | judge-eval | `openai/gpt-5.5` | **KEEP.** Switching the judge silently re-calibrates every eval that gates the other swaps. Migrate the judge *last*, deliberately, re-baselining incumbent scores — and before 5.5's own eventual retirement (watch OpenAI's deprecations page; no date announced). |
| **P4** | strategy (stretch) | — | **EVAL `anthropic/claude-fable-5`** only if the Opus 5 trial shows quality still limits `strategy`/`caseplan` outcomes. Now confirmed real, but 2x Opus price, refusal classifiers, and the 30-day retention requirement all need explicit sign-off for privileged material. Not a default path. |
| — | any role | — | **Muse Spark 1.1: WATCH, do not adopt.** US-only on OpenRouter (blocker from Australia), two weeks old, no AU-legal or refusal track record, and positioned as an agentic model rather than the creative one the name suggests. Re-assess if the regional restriction lifts; the natural first trial slot would be a cost-tier role (updatefacts/digest-summary), not a creative one. |

**Cost effect if P0-P3 all pass their evals:** the five o3-pro roles — the dominant per-case cost drivers — drop ~81-87%; the verification stack drops up to 50%; lookup/updatefacts drop ~31% on output; Anthropic roles are flat to slightly cheaper (intro window) with capability gains. Aggregate saving on a typical case plausibly 40-60%, larger than the June audit's 30-50% estimate because GPT-5.6 Terra did not exist then.

---

## D. Code-side prerequisites for any pin update (no changes made now)

The repo's own machinery dictates the sequence; these are the gaps that will bite:

1. **`model_profiles.py` has no patterns for the new families.** `claude_opus_4_7`/`_4_8` are end-anchored and will not match `claude-opus-5`; `claude4_sampling` matches only `claude-(opus-4|sonnet-4)`. A `claude-opus-5`/`claude-sonnet-5`/`claude-fable-5` id would fall through to the generic `anthropic` profile, which *allows* temperature/top_p — exactly the params these models reject. New entries (mirroring the 4.7/4.8 no-sampling profiles) plus `convert_thinking_effort` maps are required *before* any Claude 5 swap. Same check for `gpt-5.6` (the `gpt5.5` regex will not match; confirm which effort tiers 5.6 exposes — whether `xhigh` survives — against its OpenRouter page) and for `meta/muse-spark` if ever adopted (current `meta` pattern only matches `llama|codellama`).
2. **Per the config header:** parameters are never trimmed on a model swap, only added; the dispatch layer drops what the new model rejects. So the temperature/top_p lines stay even on sampling-less targets — they document intent.
3. **After every `model:` edit:** `litassist refresh` (regenerates `model_capabilities.yaml`) and `pytest` (the integrity tests assert config-capabilities consistency). Note the ordering constraint: `refresh` derives its query set from the models already configured in `model_configs.yaml` (`litassist/commands/refresh/__init__.py:188-189`), so it cannot pre-validate a candidate id that is not yet configured. To confirm a candidate exists and pull its real pricing, add it first as a temporary `-trial` config (the June audit's Section E.4 pattern) and then run `refresh`, or check the id directly on its OpenRouter model page.
4. **Eval gate:** every TRIAL row runs the Section E protocol in `LitAssist_Model_Replacement_Recommendations_2026-04-21.md` (citation precision >= incumbent is the hard constraint; incumbent wins ties). That protocol remains fit for purpose and is not restated here.

---

## E. Prompts: should they be edited for current prompting guidance?

Short answer: **not pre-emptively, and not wholesale — but yes, targeted edits should ride along with each model swap.** The library's structure is already aligned with current best practice in the ways that matter most: prompts live in YAML with stable keys, anti-injection framing wraps untrusted document content, anti-hallucination rules mandate placeholders over invention, and `=== NAME ===` section markers give the models unambiguous structure. None of that needs rework.

What has shifted is the *style* current frontier models want:

1. **Emphasis-heavy imperatives are now over-steering.** The library contains ~73 `CRITICAL`/`MUST`/`NEVER`/`IMPORTANT` markers. Vendor migration guidance for the 2026 model generations (Anthropic Opus 4.6+ / Sonnet 5; OpenAI GPT-5.x) is consistent: these models follow instructions literally, and language written to overcome older models' waywardness now causes overtriggering and rigidity. The right response is *not* a mass soften — several of these blocks encode genuine domain constraints (the anti-hallucination and complete-document rules exist because the failure modes are real and expensive in legal work; keep them). The right response is: when a role's model is swapped, A/B the role's prompt with dialled-back emphasis via `judge-eval` in the same trial. One prompt change per swap, measured, never standalone.
2. **Formatting-police blocks should become structured output — but note lookup's output path first.** The clearest wins are the markdown-spacing battles in `lookup.yaml` ("FINAL CRITICAL REMINDER: EVERY header MUST have TWO blank lines before it..."). Every pinned model now supports `response_format`/`structured_outputs` via OpenRouter (see `model_capabilities.yaml`), and requesting a schema instead of policing spacing is the "prefer prompt engineering over local parsing / fail fast" direction CLAUDE.md already mandates. Prerequisite the capability flag does not cover: lookup saves the completion string verbatim as the user-facing markdown file (`client.complete()` at `litassist/commands/lookup/processors.py:435-438`, passed straight to `save_command_output` at `:532-536`) — there is no renderer, so a JSON-schema response would ship raw JSON to the user. Either add a structured-response-to-markdown render step to that path as part of the change, or take the cheaper variant consistent with the minimal-changes rule: keep markdown as the response format and only trim the redundant emphasis/spacing prose. Do this per-command as those commands' models are trialled — the swap is when output shape is being re-validated anyway.
3. **Determinism intent must move from sampling to words.** As pins migrate to reasoning families that strip temperature/top_p (GPT-5.6, Claude 5), `temperature: 0` stops doing anything. For extraction/merge roles the prompts should carry the intent explicitly ("extract literally; do not paraphrase; preserve source wording") — currently that intent lives partly in sampling params that the newest targets ignore.
4. **Expect more verbosity by default, and say so only if observed.** The newer Opus/GPT generations write longer responses and longer documents. `draft`/`barbrief` run `verbosity: high` deliberately, so this mostly affects the verification/analysis roles. Add conciseness instructions only where trial outputs actually bloat — positive length guidance, per role, not a global rule.
5. **Do not add self-check scaffolding to new-model prompts.** Current guidance for the strongest 2026 models is that "double-check your answer" instructions cause over-verification. The library is already clean here (the verification *commands* are a separate pipeline, which is the correct architecture — external verification beats prompted self-checks). Preserve that property; resist importing self-check phrasing during any prompt rework.
6. **Context engineering is broadly fine.** The 1M-context pins comfortably hold concatenated full-text judgements for lookup; the o3-pro migration removes the one tight window (200K) from the biggest-input commands. Prompt caching is low-value for a single-shot CLI workload and is not worth engineering for now.

---

## F. Suggested sequence

1. **Now:** add Claude 5 / GPT-5.6 entries to `model_profiles.py` + effort maps (prereq for everything Anthropic/OpenAI); then add the candidates as temporary `-trial` configs and run `litassist refresh` to confirm the live ids and pull real OpenRouter pricing into `model_capabilities.yaml` (refresh only queries models present in `model_configs.yaml`, so profile entries alone are not enough).
2. **Now:** re-run the unorthodox eval against `x-ai/grok-4.5` to bank a validated fallback for `brainstorm-unorthodox`.
3. **Before 31/08/2026:** Sonnet 5 trials on the workhorse roles while introductory pricing halves eval cost.
4. **Next 4-6 weeks:** GPT-5.6 Terra trials on the five o3-pro roles; this is the P0 item with the 11/12/2026 deadline — do not let it queue behind the cheaper experiments.
5. **Alongside each swap:** the corresponding prompt A/B (emphasis dial-back, structured output for lookup, determinism wording for extraction).
6. **Last:** judge-eval migration, deliberately re-baselined.
7. **Standing:** watch OpenRouter for Grok 4.6, Gemini 4, Muse Spark regional availability, and expiration dates via `litassist refresh`.

---

## G. Sources

Anthropic model/pricing data is from Anthropic's current model documentation (Claude 5 family: Fable 5 $10/$50, Opus 5 $5/$25, Sonnet 5 $3/$15 with introductory $2/$10 through 31/08/2026; sampling-parameter removal and Sonnet 5 tokenizer change per the official migration guidance). External items verified 26/07/2026:

- Meta Muse Spark 1.1: [Meta announcement](https://ai.meta.com/blog/introducing-muse-spark-meta-model-api/), [TechCrunch](https://techcrunch.com/2026/07/09/meta-enters-the-crowded-ai-coding-battle-with-muse-spark-1-1/), [MarkTechPost](https://www.marktechpost.com/2026/07/09/meta-superintelligence-labs-releases-muse-spark-1-1/), [OpenRouter model page](https://openrouter.ai/meta/muse-spark-1.1), [US-only availability](https://www.kucoin.com/news/flash/meta-s-muse-spark-1-1-available-on-openrouter-limited-to-u-s-developers)
- OpenAI GPT-5.6 tiers/pricing: [CloudZero](https://www.cloudzero.com/blog/gpt-5-6-pricing/), [Finout](https://www.finout.io/blog/gpt-5.6-pricing-2026-sol-terra-and-luna-tiers-explained), [OpenRouter gpt-5.6-terra](https://openrouter.ai/openai/gpt-5.6-terra)
- o3-pro retirement 11/12/2026: [OpenAI deprecations](https://developers.openai.com/api/docs/deprecations), [byteiota summary](https://byteiota.com/openai-model-retirements-2026-what-dies-next-and-what-to-use-instead/)
- Gemini 3.6 Flash: [Google announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/gemini-3-6-flash-3-5-flash-lite-3-5-flash-cyber/), [TechCrunch](https://techcrunch.com/2026/07/21/google-releases-three-new-gemini-models-but-no-3-5-pro/)
- Grok 4.5 / 4.6: [OpenRouter grok-4.5](https://openrouter.ai/x-ai/grok-4.5), [release-cadence reporting](https://startupfortune.com/xai-is-shipping-grok-46-and-47-back-to-back-in-a-release-cadence-no-frontier-lab-has-matched/)

Note: the container's egress proxy blocked a direct `openrouter.ai/api/v1/models` fetch this session (403), so OpenRouter ids/prices above come from OpenRouter's public model pages via search rather than the catalogue JSON. Confirm exact ids and live pricing before relying on them: add the candidate as a temporary `-trial` config and run `litassist refresh` (which only queries configured models), or check the candidate's OpenRouter model page directly.
