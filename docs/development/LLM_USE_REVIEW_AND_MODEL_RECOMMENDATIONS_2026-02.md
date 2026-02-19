# LitAssist LLM Use Review and Model Recommendations (2026-02)

Last updated: 16/02/2026

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
- Model overrides are supported through environment variables per command/sub-command.
- Most traffic is routed through OpenRouter with provider/model identifiers.

### 1.2 Current model strategy
LitAssist already uses a **multi-model strategy**:
- **Anthropic Claude Sonnet 4.5** for many legal reasoning/generation steps.
- **OpenAI o3-pro** for analysis-heavy drafting and structured long-form output.
- **GPT-5.1 / GPT-5-pro** for verification-heavy work.
- **Gemini 2.5 Pro** for lookup/research.
- **Grok 4** for unorthodox brainstorming.

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

Below is a pragmatic target matrix to evaluate (not blindly adopt) via the P0 eval harness.

| Command area | Current | Recommended direction |
|---|---|---|
| `lookup` | Gemini 2.5 Pro | Keep as primary; add an evaluated alternate with stronger legal citation-grounding for failover. |
| `extractfacts` | Claude Sonnet 4.5 | Keep primary; test a cheaper/faster extraction-capable model for Fast profile. |
| `digest-*` | Claude Sonnet 4.5 | Keep Balanced profile on Sonnet; add Fast profile candidate to reduce costs on bulk runs. |
| `strategy` | Claude Sonnet 4.5 | Keep primary; consider “Max Accuracy” variant using a top reasoning model for high-stakes matters. |
| `draft` / `counselnotes` / `barbrief` | o3-pro | Re-evaluate against latest top-tier reasoning+writing model(s); keep o3-pro if still best on legal-structure + long output. |
| `verification` | GPT-5.1 | Keep for standard verification if evals confirm precision remains high. |
| `verification-heavy`, `verify-soundness-heavy` | GPT-5-pro | Keep for highest-risk checks; consider optional dual-model consensus only for critical filings. |
| `brainstorm-unorthodox` | Grok 4 | Keep only if novelty benefit survives evals; otherwise swap to a lower-hallucination creative model and prompt for divergence explicitly. |

### Specific proposed swaps to evaluate first
1. **Drafting stack (`draft`, `counselnotes`, `barbrief`)**
   - Evaluate whether latest GPT-5.x family variant(s) outperform `o3-pro` on:
     - legal structure adherence,
     - citation faithfulness,
     - output coherence at long lengths,
     - cost per finished document.
2. **Brainstorm unorthodox model**
   - Benchmark Grok 4 vs one alternate for “novel but legally plausible” outcomes.
3. **Digest/ExtractFacts fast lane**
   - Add one lower-cost candidate model for batch preprocessing profile.

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

## 7) Recommended immediate decision

If only one near-term change can be made, prioritize:
1. **Eval harness + scorecard**, then
2. **Drafting stack re-evaluation** (highest token spend, high user-visible impact), then
3. **Fast profile for digest/extractfacts** (biggest cost lever).

This sequence yields the best balance of legal safety, output quality, and operating cost.
