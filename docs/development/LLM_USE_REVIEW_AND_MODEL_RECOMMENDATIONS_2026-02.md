# LitAssist LLM Use Review and Model Recommendations (2026-02)

Last updated: 25/02/2026

## Scope
This review covers how LitAssist currently uses LLMs in production code, compares that design to recent GenAI platform trends, and recommends practical upgrades—especially model-selection changes.

Primary files reviewed:
- `litassist/llm/model_configs.yaml`
- `litassist/llm/factory.py`
- `litassist/llm/client.py`
- `litassist/llm/parameter_handler.py`
- `litassist/llm/model_profiles.py`
- `README.md`

---

## 1) Current LLM Architecture (What LitAssist does today)

### 1.1 Configuration and routing
- Command-to-model mapping is centralized in `litassist/llm/model_configs.yaml` and loaded by `LLMClientFactory`.
- All commands are strict-keyed (no fallback config keys), which reduces silent misconfiguration risk.
- Model selection is controlled exclusively through `model_configs.yaml`; there are no runtime or environment variable overrides.
- All traffic is routed through OpenRouter with provider/model identifiers.

### 1.2 Current model strategy
LitAssist uses a **multi-model, multi-provider strategy** across 28 command configurations. The active source of truth is `litassist/llm/model_configs.yaml`; recommendations in later sections are historical unless revalidated.

| Model | Provider | Commands |
|---|---|---|
| Claude Sonnet 4.6 | Anthropic | extractfacts, brainstorm-orthodox, digest-summary, digest-issues, caseplan, caseplan-assessment, cove, cove-questions, cove-verify, cove-final, verification-light, verify-reasoning |
| Claude Opus 4.7 | Anthropic | strategy, verify-soundness |
| o3-pro | OpenAI | strategy-analysis, brainstorm-analysis, draft, counselnotes, barbrief |
| GPT-5.5 | OpenAI | verification, cove-answers, verification-heavy, verify-reasoning-heavy, verify-soundness-heavy, cove-answers-heavy |
| Gemini 3.5 Flash | Google | lookup |
| Grok 4.20 | xAI | brainstorm-unorthodox |

**Provider distribution**: Anthropic 14 configs, OpenAI 11, Google 1, xAI 1.

### 1.3 Strengths
- Good task specialization (research, generation, verification split).
- Parameter normalization (`thinking_effort` -> provider-specific `reasoning`).
- Practical handling for model capability differences (system-message support, tools/no-tools mode).
- Explicit verification stages for legal-safety workflows.

### 1.4 Observed limitations
1. **No explicit cost/latency quality router** at runtime.
   - Model choice is static by command; no policy-based dynamic escalation.
2. **No first-class fallback chain by command** (intentional “no fallback” config policy).
   - Good for correctness, but can reduce resiliency during outages/capacity events.
3. **Model docs appear partially stale in places** (historical references no longer matching YAML exactly).
4. **Heterogeneous model mix may increase operational overhead** (BYOK variance, pricing complexity, behavior drift).
5. **Limited visible eval automation for model refreshes** (no obvious benchmark harness dedicated to model-swap decisions).

---

## 2) Recent GenAI Developments Relevant to LitAssist

The most relevant ecosystem changes for legal AI products in 2025→2026 are:

1. **Reasoning-first APIs with budget controls**
   - Better controllability over deliberation depth (`reasoning.effort`/equivalent) and verbosity.
2. **Rapid model release cadence and quality drift**
   - Best model by task changes quarterly, sometimes monthly.
3. **Tool-calling reliability and structured outputs improved**
   - Deterministic schemas now practical for legal pipeline handoffs.
4. **Cost-performance frontier widened**
   - “Small/fast” models often handle preprocessing and extraction cheaply.
5. **Evaluation discipline is now core**
   - Production teams increasingly use regression test suites and offline evals before model swaps.

Implication for LitAssist: architecture is already strong, but should become **evaluation-driven + policy-routed** rather than primarily static.

---

## 3) Recommended AI Improvements (Prioritized)

## P0 (High impact, low risk)

### P0.1 Add a model-eval harness for command-level model swaps
Build a repeatable benchmark over representative legal workloads:
- `extractfacts`: field-level precision/recall + citation integrity.
- `strategy`/`brainstorm-analysis`: legal-reasoning rubric + novelty/usefulness.
- `draft`/`barbrief`: structure correctness, citation consistency, hallucination incidence.
- `verification`: false negative/false positive rates on seeded errors.

**Why first:** Enables safe model upgrades and prevents regression from “new model hype” changes.

### P0.2 Introduce policy-based routing tiers (Fast / Balanced / Max Accuracy)
Add CLI/global config to choose budget profile:
- **Fast**: lower-cost model path where acceptable.
- **Balanced**: current default behavior.
- **Max Accuracy**: stronger verification and analysis models.

**Why:** users in legal practice have diverse deadlines/budgets; this unlocks explicit tradeoffs without branching code paths per command.

### P0.3 Consolidate command-level model decisions into a “primary + backup candidate” table
Keep strict config, but define one **approved alternate** per key command (for manual failover or feature flag rollout).

---

## 4) Model-change recommendations for LitAssist

### 4.1 Model landscape update (February 2026)

Since the original version of this document, several next-generation models have shipped. The recommendations below account for all current frontier models.

New models considered:

| Model | Released | GPQA Diamond | BigLaw Bench | SWE-bench | Context | Price (in/out $/M) |
|---|---|---|---|---|---|---|
| Claude Opus 4.6 | 05/02/2026 | 91.3% | **90.2%** | **80.8%** | 1M | $5 / $25 |
| Claude Sonnet 4.6 | 17/02/2026 | 89.9% | 87.6% | 79.6% | 1M | $3 / $15 |
| GPT-5.2 Thinking | 11/12/2025 | 92.4% | -- | ~80% | 400K | $1.75 / $14 |
| GPT-5.2 Pro | 11/12/2025 | **93.2%** | -- | -- | 400K | $21 / $168 |
| Gemini 3.1 Pro | 19/02/2026 | **94.3%** | -- | ~76% | 1M | $2 / $12 |
| Grok 4.1 Fast | 17/11/2025 | -- | -- | -- | 2M | $0.20 / $0.50 |

Sources: Anthropic model card (Opus 4.6, Sonnet 4.6); Harvey BigLaw Bench (Opus 4.6 90.2%, Sonnet 4.6 87.6%); OpenAI GPT-5.2 announcement; Google DeepMind Gemini 3.1 Pro model card; xAI Grok 4.1 announcement; OpenRouter pricing pages. All models confirmed available on OpenRouter.

Notes on benchmark coverage:
- **BigLaw Bench** (Harvey): the only legal-specific benchmark with published scores. Only Opus 4.6 and Sonnet 4.6 have been evaluated.
- **GPQA Diamond**: graduate-level science QA. Measures deep reasoning but is not legal-specific.
- **Gemini 3.1 Pro** on Case Law v2 (vals.ai): 65.6% accuracy, rank #11 -- a 12-point improvement over Gemini 3 Pro.
- **Grok 4.1 full model** is NOT available via API. Only the Fast variant is.
- **o3-pro** is superseded by GPT-5.2 family per OpenAI. GPT-5.2 Thinking exceeds o3-pro on GPQA, GDPval, and FrontierMath while costing significantly less.

### 4.2 Superseded drop-in upgrade notes

Earlier versions of this review recommended moving Sonnet 4.5 assignments to Sonnet 4.6 and updating verification models. Those changes are no longer pending recommendations; the active configuration already uses Sonnet 4.6 for the relevant stages, Opus 4.7 for strategy/soundness, GPT-5.5 for verification, Gemini 3.5 Flash for lookup, and Grok 4.20 for unorthodox brainstorming.

Any future model swap should go through the eval harness described in P0.1 rather than relying on this dated snapshot.

### 4.3 Eval-required upgrades

These involve changing model generation or provider. Evaluate via the P0 eval harness before adoption.

**o3-pro replacement -- drafting (draft, counselnotes, barbrief)**

o3-pro ($20/$80, 200K context) is superseded. Candidates ranked by legal reasoning accuracy:

1. **Claude Opus 4.6** ($5/$25, 1M context). BigLaw Bench 90.2% -- the only model with verified legal benchmark leadership. GPQA 91.3%. SWE-bench 80.8%. The strongest candidate for legal drafting given that BigLaw Bench directly measures the task domain.
2. **GPT-5.2 Pro** ($21/$168, 400K context). GPQA 93.2%. ARC-AGI-2 54.2%. Strongest general reasoning model. No legal-specific benchmarks but top-tier accuracy overall. High output cost is acceptable if accuracy justifies it.
3. **GPT-5.2 Thinking** ($1.75/$14, 400K context). GPQA 92.4%. GDPval SOTA (first model at/above human expert level on knowledge work). No legal-specific benchmarks.

Eval criteria: legal structure adherence, citation faithfulness, output coherence at long lengths, hallucination rate.

**o3-pro replacement -- analysis (strategy-analysis, brainstorm-analysis)**

Analysis tasks produce shorter output than drafting. Candidates ranked by general reasoning strength:

1. **GPT-5.2 Pro** ($21/$168, 400K context). GPQA 93.2%. Strongest general reasoning. Shorter output mitigates high per-token output cost.
2. **Gemini 3.1 Pro** ($2/$12, 1M context). GPQA 94.3% (highest). ARC-AGI-2 77.1% (highest). Very new (released 19/02/2026), limited legal-specific testing.
3. **Claude Opus 4.6** ($5/$25, 1M context). BigLaw Bench 90.2%. GPQA 91.3%. Legal reasoning leader.

Eval criteria: legal reasoning depth, novelty of analysis, citation accuracy.

**GPT-5.5 replacement (verification, cove-answers)**

1. **GPT-5.2 Thinking** ($1.75/$14, 400K context). GPQA 92.4% (vs GPT-5.5 ~88%). GDPval SOTA. 400K context (up from ~128K). Strictly better reasoning than GPT-5.5.
2. Also evaluate **GPT-5.2 Pro** if the eval harness shows meaningful accuracy gain on verification-specific tasks.

Eval criteria: false positive/negative rates on seeded verification errors.

**GPT-5.5 replacement (verification-heavy, verify-reasoning-heavy, verify-soundness-heavy, cove-answers-heavy)**

**GPT-5.2 Pro** ($21/$168, 400K context). GPQA 93.2%. ARC-AGI-2 54.2%. The strongest general reasoning model available. These heavy configs run infrequently on high-stakes work where accuracy is paramount.

Eval criteria: precision on critical legal errors, false negative rate.

**Grok 4.20 replacement (brainstorm-unorthodox)**

- **Grok 4.1 Fast** ($0.20/$0.50, 2M context). 65% hallucination reduction (xAI claim). Top LMArena ranking (1483 Elo, Thinking mode). 2M context (8x Grok 4.20).
- Risk: “Fast” variant may sacrifice creative divergence quality compared to full Grok 4.20 ($3/$15, 256K). The full Grok 4.1 model is not available via API.
- Evaluate whether hallucination reduction improves “novel but legally plausible” outcomes, or whether reduced creativity defeats the purpose of the unorthodox mode.

Eval criteria: novelty, legal plausibility, hallucination rate.

### 4.4 Updated command-area matrix

Every entry in `model_configs.yaml` is represented. “Recommended candidate” is the primary eval candidate per section 4.2/4.3.

| Command area | Commands | Current model | Recommended candidate |
|---|---|---|---|
| Extraction | extractfacts | Sonnet 4.6 | Keep unless eval shows improvement |
| Digest | digest-summary, digest-issues | Sonnet 4.6 | Keep unless eval shows improvement |
| Strategy | strategy | Opus 4.7 | Keep unless eval shows improvement |
| Strategy analysis | strategy-analysis | o3-pro | **GPT-5.2 Pro** (eval) |
| Brainstorm orthodox | brainstorm-orthodox | Sonnet 4.6 | Keep unless eval shows improvement |
| Brainstorm unorthodox | brainstorm-unorthodox | Grok 4.20 | **Grok 4.1 Fast** (eval) |
| Brainstorm analysis | brainstorm-analysis | o3-pro | **GPT-5.2 Pro** (eval) |
| Drafting | draft, counselnotes, barbrief | o3-pro | **Opus 4.6** (eval) |
| Lookup | lookup | Gemini 3.5 Flash | Eval before changing |
| Case planning | caseplan, caseplan-assessment | Sonnet 4.6 | Keep unless eval shows improvement |
| Verification standard | verification | GPT-5.5 | **GPT-5.2 Thinking** (eval) |
| Verification light | verification-light | Sonnet 4.6 | Keep unless eval shows improvement |
| Verification heavy | verification-heavy | GPT-5.5 | **GPT-5.2 Pro** (eval) |
| Reasoning check | verify-reasoning | Sonnet 4.6 | Keep unless eval shows improvement |
| Reasoning check heavy | verify-reasoning-heavy | GPT-5.5 | **GPT-5.2 Pro** (eval) |
| Soundness check | verify-soundness | Opus 4.7 | Keep unless eval shows improvement |
| Soundness check heavy | verify-soundness-heavy | GPT-5.5 | **GPT-5.2 Pro** (eval) |
| CoVe pipeline | cove, cove-questions, cove-verify, cove-final | Sonnet 4.6 | Keep unless eval shows improvement |
| CoVe answers | cove-answers | GPT-5.5 | **GPT-5.2 Thinking** (eval) |
| CoVe answers heavy | cove-answers-heavy | GPT-5.5 | **GPT-5.2 Pro** (eval) |

### 4.5 Eval priority order

1. **Eval harness first** -- no further model swaps should be defaulted without command-level regression data.
2. **Drafting stack** -- evaluate Opus 4.6 vs GPT-5.2 Pro vs GPT-5.2 Thinking against o3-pro.
3. **Heavy verification** -- evaluate GPT-5.2 Pro against the active GPT-5.5 heavy-verification baseline.
4. **Standard verification** -- evaluate GPT-5.2 Thinking against GPT-5.5.
5. **Analysis sub-commands** -- evaluate GPT-5.2 Pro and Gemini 3.1 Pro against o3-pro.
6. **Brainstorm unorthodox** -- evaluate Grok 4.1 Fast against Grok 4.20.

---

## 5) Engineering improvements beyond model swaps

1. **Structured-output contracts by stage**
   - Prefer schema-validated JSON between pipeline stages where possible.
2. **Automatic canarying for model changes**
   - Route a small percentage to candidate model; compare quality/latency/cost.
3. **Prompt+model version pinning in logs**
   - Include exact model revision and prompt hash in audit logs for reproducibility.
4. **Consensus verification mode (optional)**
   - For “filed-to-court” quality gates, run two independent verifiers and require agreement on high-severity issues.

---

## 6) Suggested implementation plan

### Phase 1 (1–2 weeks)
- Build eval dataset and scoring scripts.
- Add profile-level routing (`fast`, `balanced`, `max_accuracy`) with current mapping as `balanced`.

### Phase 2 (1 week)
- Run model bake-off for drafting stack and brainstorm-unorthodox.
- Publish scorecard and recommended swaps.

### Phase 3 (1 week)
- Ship selected model swaps behind feature flags.
- Canary rollout + monitor quality, latency, and cost.

### Phase 4 (ongoing)
- Monthly model review cadence.
- Regression gates required before any default model change.

---

## 7) Recommended immediate actions

In priority order:
1. **Build eval harness** (P0.1) -- required before any generation-change upgrade.
2. **Evaluate drafting stack** -- Opus 4.6 and GPT-5.2 Pro/Thinking against o3-pro. Highest user-visible impact.
3. **Evaluate heavy verification** -- GPT-5.2 Pro against the active GPT-5.5 heavy-verification baseline. Highest accuracy-sensitivity.
4. **Review lookup model candidates** -- benchmark any Gemini replacement against the active Gemini 3.5 Flash baseline.
