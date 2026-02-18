# Adversarial Modelling -- Design Reference

**Last Updated:** February 2026
**Status:** Design Reference (partially planned in ROADMAP P1-9, P3-22)
**Prerequisite:** P0A-1 (Matter Memory Module)
**Confidence:** 0.85

This document is the extended design reference for adversarial modelling in LitAssist. The ROADMAP entries P1-9 (Opponent Profiling System, 8-10h) and P3-22 (Simulated-Adversary Drafts, 8-10h) contain the scoped implementation plans derived from this design.

---

At a high level, an adversarial modelling feature in LitAssist would be a set of tools that build and maintain probabilistic profiles of each opponent (party, lawyer, firm) and then use those profiles to simulate their moves, generate their best arguments, and stress-test your drafts and strategies.

Below is a concrete breakdown of what it would consist of.

---

## Current State: Related Features in LitAssist

Before describing the full adversarial modelling vision, note what already exists:

**Orthodox/Unorthodox Strategy Generation (PRODUCTION)**
- `litassist brainstorm` generates 15 orthodox (conservative, precedent-based) + 15 unorthodox (creative) strategies
- These are YOUR strategies for YOUR side, not opponent simulation
- Uses Claude Sonnet 4.5 (orthodox) + Grok-4 (unorthodox) with different temperature settings
- Analysis/selection stage uses o3-pro with `thinking_effort: high`
- See: `litassist/commands/brainstorm/`

**Chain of Verification (CoVe) - PRODUCTION**
- `litassist verify-cove` implements 4-stage verification loop
- Questions --> Answers --> Critical verification --> Synthesis
- Uses a multi-model pipeline: Claude Sonnet 4.5 for question generation and verification stages, GPT-5.1 for answer generation (per `model_configs.yaml`)
- Soundness verification uses Claude Opus 4.1
- See: `litassist/commands/verify_cove/`

**Citation Verification - PRODUCTION**
- Real-time verification against AustLII, Jade.io
- Pattern validation + database lookup + plausibility assessment
- See: `litassist/citation/verify.py`

**What Doesn't Exist Yet:**
- Opponent/actor profiles
- "Write as [Opponent]" simulation
- Paragraph-by-paragraph adversarial review
- Move prediction
- Profile-based behavioural modelling

**Relevant Roadmap Items:**
- P1-9: Opponent Profiling System (Phase 3, 8-10h) -- covers Sections 1-2 of this document
- P3-22: Simulated-Adversary Drafts (Phase 5, 8-10h) -- covers Sections 3.1 and 3.3
- P0A-3: Letter Doctor -- overlaps with adversarial draft review (Section 3.3)
- P2-18: Cost-of-Obstruction Ledger -- feeds into strategy comparison (Section 4.1)
- P2-19: Bias Divergence Detector -- multi-model consensus for high-stakes adversarial outputs

**Design Principles (per CLAUDE.md and LLM Use Review):**
- Prefer single comprehensive calls over orchestrated multi-call pipelines
- Multi-model consensus reserved for filed-to-court quality gates only (P2-19)
- All model assignments should support Fast/Balanced/Max Accuracy routing tiers (LLM Use Review P0.2)
- Model assignments are recommendations pending validation via eval harness (LLM Use Review P0.1)

---

## Model Landscape (February 2026)

Models available for adversarial features, routed through OpenRouter (BYOK available for Anthropic, OpenAI, and xAI):

### Anthropic

| Model | Context | Key Benchmarks | Cost (input / output per M tokens) |
|---|---|---|---|
| Claude Opus 4.6 | 1M | GDPval-AA 1606 Elo, BigLaw Bench 90.2%, adaptive thinking | $5 / $25 ($10 / $37.50 >200K) |
| Claude Sonnet 4.5 | 200K (1M beta) | GDPval-AA 1259 Elo, strong instruction following | $3 / $15 |
| Claude Haiku 4.5 | 200K | Fast inference, extended thinking support | $1 / $5 |

### OpenAI

| Model | Context | Key Benchmarks | Cost (input / output per M tokens) |
|---|---|---|---|
| GPT-5.2 | 400K | GDPval-AA 1462 Elo, GPQA Diamond 92-93%, LongBench v2 54.5% | $1.75 / $14 |
| GPT-5.2 Pro | 400K | xhigh reasoning (5-10 min/decision), ARC-AGI-2 54.2%, newest deep-reasoning option | $21 / $168 |
| GPT-5-pro | 400K | Used in project for verification-heavy (BYOK) | ~$1.25 / $10 |
| o3-pro | 200K | Extended thinking, used in project for drafting/strategy (BYOK). Not deprecated but older (June 2025) | $20 / $80 |

### Google

| Model | Context | Key Benchmarks | Cost (input / output per M tokens) |
|---|---|---|---|
| Gemini 3 Pro | 1M | GPQA Diamond 91.9%, BigLaw Bench 87.9%, GDPval-AA 1195 Elo | $2 / $12 ($4 / $18 >200K) |
| Gemini 3 Flash | 1M | Near-Pro reasoning, beats Gemini 2.5 Pro on 18/20 benchmarks | $0.50 / $3 |
| Gemini 2.5 Pro | 1M | Best long-context accuracy (LongBench v2 68.2%, MRCR 94.5% at 128K) | $1.25 / $5 ($2.50 / $15 >200K) |
| Gemini 2.5 Flash | 1M | Cost-effective extraction and preprocessing | $0.30 / $2.50 |

### xAI

| Model | Context | Key Benchmarks | Cost (input / output per M tokens) |
|---|---|---|---|
| Grok 4 | 256K | Creative/divergent reasoning, used in project for unorthodox brainstorming | $3 / $15 |
| Grok 4.1 Fast | 2M | 65% fewer hallucinations vs Grok 4, near-Grok-4 quality at 1/15th cost | $0.20 / $0.50 |

### Open-source (via OpenRouter)

| Model | Context | Key Benchmarks | Cost (input / output per M tokens) |
|---|---|---|---|
| DeepSeek R1 | 130K | Strong reasoning (GPQA 71.5%), open-weight | ~$1.35 / $4.20 (free tier available) |
| Kimi K2.5 | 256K | SOTA open-source (SWE-bench 76.8%, AIME 96%) | Varies by provider |

**Key platform developments since November 2025:**

1. **1M+ token context windows are standard.** Claude Opus 4.6, Gemini 2.5 Pro, Gemini 3 Pro, and Gemini 3 Flash all support 1M tokens; Grok 4.1 Fast supports 2M. A typical opponent's document corpus (20-50 documents, ~200K-500K tokens) fits in a single call. GPT-5.2's 400K context also covers most single-matter corpora. This fundamentally simplifies the ingestion pipeline described in Section 2.

2. **Structured output enforcement is reliable.** JSON schema constrained decoding now guarantees 100% schema adherence across all major providers (Anthropic, OpenAI, Google, xAI). Profile schemas, simulation outputs, and heat maps can be enforced at the API level, eliminating parsing logic (per CLAUDE.md: "Prefer prompt engineering over local parsing").

3. **Adaptive thinking controls.** Multiple providers now support effort parameters (Anthropic: low/medium/high/max; OpenAI: reasoning.effort; Google: thinking levels) allowing per-task reasoning depth. Profile building might use medium; steelman argument generation would use max.

4. **Eval harness prerequisite.** Per the LLM Use Review (February 2026), model assignments should be validated via a command-level eval harness before production use. The assignments in this document are recommendations pending that validation. Different models lead on different benchmarks (e.g., Opus 4.6 leads GDPval-AA, GPT-5.2 leads GPQA Diamond, Gemini 2.5 Pro leads LongBench v2), so task-specific evaluation is critical.

---

## 1. Core objects and data model

You would introduce explicit "adversary" entities:

* PartyProfile (eg "Party A")
* LawyerProfile (eg "Opposing Counsel B", "Opposing Counsel C")
* FirmProfile (eg "Firm X", "Firm Y")
* AgencyProfile (for government agencies, regulators)

Profiles are stored as YAML under Matter Memory: `~/.config/litassist/matters/profiles/{actor}.yaml` (per ROADMAP P1-9). Profile schemas should be enforced via JSON schema structured outputs at the API level when generating or updating profiles.

Each profile would maintain:

1. Identity and role

   * Name, role (applicant, respondent, agency), matter types they appear in.
   * Links to matters in your LitAssist store.

2. Evidence corpus

   * All documents authored by or attributed to that actor:

     * Letters, emails, pleadings, affidavits, submissions, press releases.
     * Internal notes where you paraphrase what they have said or done.
   * Metadata:

     * Dates, jurisdiction, forum, procedural posture.
     * Outcome (eg application refused, settlement terms, dismissal).

3. Behavioural features (computed or inline)

   With 1M token context windows, these features can be computed inline as part of a simulation call rather than requiring a separate pre-computation pipeline. The model produces behavioural analysis as part of profile generation when the full evidence corpus is in context. Pre-computation becomes an optional optimisation for repeat use or cost reduction (see Section 2).

   Examples:

   * Procedural style:

     * On-time vs late filings, tendency to seek adjournments, use of interim orders.
   * Substantive style:

     * Preferred case law, favourite arguments (eg abuse of process, jurisdictional error).
     * Reliance on affidavits vs aggressive cross-examination.
   * Tone and rhetoric:

     * Hedged vs absolutist language, personal attacks, moralising vs dry legalism.
   * Risk and cost behaviour:

     * Willingness to run economically irrational positions.
     * Thresholds where they tend to settle or back down.

4. Strategic priors

   * Manually set knobs that you can adjust:

     * "Litigation budget likely high/medium/low."
     * "Reputation sensitive: high/medium/low."
     * "Process weaponisation: rare / sometimes / default tool."
   * These priors shape how simulations behave when data is thin.

---

## 2. Ingestion and profile generation

This feature needs a way to convert raw material into profile features. The design choice is between two approaches, driven by the availability of 1M token context windows.

### 2.1 Document ingestion (required for both approaches)

When you add or OCR a document, LitAssist:

* Identifies authors and signatories.
* Links it to the relevant PartyProfile/LawyerProfile.
* Stores structured fields (dates, court, rule references, remedies sought).

This depends on the OCR/text extraction infrastructure from P4-23 (PDF Preflight Normalisation) and matter storage from P0A-1 (Matter Memory Module).

### 2.2 Profile generation approach

**Context-first (recommended for MVP):**

Load all opponent documents directly into a 1M context window call. Ask the model to produce the full profile in a single comprehensive call. The model performs argument structure extraction, procedural move classification, language style analysis, and compliance assessment in one pass, returning a structured profile conforming to the JSON schema.

This aligns with CLAUDE.md: "Prefer one comprehensive call over many orchestrated calls when practical."

A typical litigated matter involves 20-50 opponent documents totalling 200K-500K tokens -- well within a single call for Claude Opus 4.6 or Gemini 2.5 Pro.

* Model recommendation (governed by routing tier). Context window and long-context accuracy are the primary drivers for profile building:
  * Fast: `google/gemini-2.5-flash` ($0.30/$2.50 per M tokens, 1M context). Alternative: `x-ai/grok-4.1-fast` ($0.20/$0.50, 2M context) if eval harness validates extraction quality.
  * Balanced: `google/gemini-2.5-pro` ($1.25/$5 per M tokens, 1M context, LongBench v2 leader at 68.2%). Best long-context accuracy for document-heavy extraction.
  * Max Accuracy: `anthropic/claude-opus-4.6` with `thinking_effort: high` ($5/$25 per M tokens, 1M context, GDPval-AA 1606 Elo). Strongest legal reasoning for definitive profile generation. Alternative: `google/gemini-3-pro-preview` ($2/$12, 1M context, BigLaw Bench 87.9%) at lower cost.
* Structured output: Profile JSON schema passed as `response_format`, guaranteeing valid output. No parsing logic needed.
* Estimated cost for a 500K token corpus: approximately $2.50 input (Opus 4.6), $0.63 input (Gemini 2.5 Pro), $0.88 input (GPT-5.2), or $0.10 input (Grok 4.1 Fast) plus output tokens.

**Pipeline approach (for scale/cost optimisation later):**

Pre-compute features per document, store incrementally, merge into profile. Use when:
* Opponent corpus exceeds ~800K tokens (rare for a single matter, possible across multiple matters).
* Running repeated simulations against the same profile (amortise extraction cost).
* Operating under the Fast routing tier where avoiding large-context calls reduces cost.

For each document, the pipeline would compute:

* Argument structures (issues raised, authorities cited, relief requested).
* Procedural moves (strike-out, stay, extension, appeal, etc.; rules invoked).
* Language style (aggression vs conciliation, hedging vs certainty).
* Compliance behaviour (on-time vs late relative to timetable metadata).

### 2.3 Behavioural summary

Under the context-first approach, the behavioural summary is produced as part of the profile generation call (not as a separate computation step). The structured output schema includes fields for rolling stats:

* "In this matter, they missed X of Y deadlines."
* "In 70% of letters they threaten costs or procedural escalation."
* "Common pattern: raise vindictive/collateral motive allegations when cornered."

Under the pipeline approach, these stats are maintained incrementally as documents are ingested.

---

## 3. Simulation and generation capabilities

Once you have profiles, LitAssist can use them to generate and evaluate adversarial content.

### 3.1 "Write as [Opponent]" mode

**NOTE:** This is distinct from the existing `litassist brainstorm` orthodox/unorthodox split. That command generates YOUR strategies (conservative vs creative). This proposed feature would generate OPPONENT'S strategies based on their profile.

**ROADMAP:** Implemented via P3-22 (Simulated-Adversary Drafts, Phase 5, 8-10h).

Given a draft from you, the tool can:

* Generate:

  * A letter of demand or response as if written by the opponent.
  * Their likely defence, reply, or affidavit to your pleading.
  * Their likely submissions on a particular interlocutory application.

* With outputs such as:

  * Best possible version (steel-man) of their argument.
  * "Typical" version based on their historical style (eg sloppier, more emotional).
  * A specific mode based on their profile (eg "Aggressive Mode", "Conservative Mode").

* Model recommendations (by mode). Legal reasoning quality is the primary driver for steelman; style replication drives typical:
  * Steelman: Strongest legal reasoning required to construct the strongest possible opposing argument.
    * Fast: `openai/gpt-5.2` ($1.75/$14, GPQA Diamond 92-93%, GDPval-AA 1462 Elo, 400K context).
    * Balanced: `anthropic/claude-opus-4.6` with `thinking_effort: max` ($5/$25, GDPval-AA 1606 Elo, BigLaw Bench 90.2%). Leads legal reasoning benchmarks.
    * Max: `openai/gpt-5.2-pro` with xhigh reasoning ($21/$168, 400K context, ARC-AGI-2 54.2%, newest OpenAI deep-reasoning option). Alternative: `openai/o3-pro` ($20/$80, lower output cost but older model with 200K context). The project currently uses o3-pro for drafting; eval harness should compare both for adversarial steelman quality per dollar.
  * Typical/historical: Style replication rather than maximal reasoning depth.
    * Fast: `x-ai/grok-4.1-fast` ($0.20/$0.50, creative/style tasks, matches project's use of Grok for unorthodox generation).
    * Balanced: `openai/gpt-5.2` ($1.75/$14, strong general reasoning at moderate cost).
    * Max: `google/gemini-3-pro-preview` ($2/$12, 1M context, BigLaw Bench 87.9%).
  * For either mode, profile YAML + relevant documents are loaded into context alongside your draft.

* Structured output: Simulation results use a defined JSON schema enforced via `response_format`: `{simulation_type, simulated_document, reasoning_trace, confidence, key_arguments[], vulnerability_points[]}`.

* Prompts: `litassist/prompts/adversarial.yaml`, accessed via `PROMPTS.get("adversarial.simulate.steelman")` etc.

You would call something like:

* `litassist adversary simulate --actor="OpposingCounselB" --input draft.txt --mode="steelman" --matter LITIGATION-001`

### 3.2 Move prediction and timelines

For each matter, maintain a "next moves" panel:

* Predict:

  * Most likely applications they will bring next (eg stay, abuse of process, extension, strike-out).
  * Likely timing relative to known dates (close to deadline, last minute, early).
* Output:

  * A ranked list with likelihoods (most likely, likely, possible, unlikely) and brief rationale.
  * Links to prior matters or documents that justify each prediction.

* Model recommendations. Probabilistic reasoning and pattern analysis are the primary drivers:
  * Fast: `google/gemini-3-flash-preview` ($0.50/$3, near-Pro reasoning, 1M context).
  * Balanced: `openai/gpt-5.2` ($1.75/$14, GPQA Diamond 92-93%, strongest abstract reasoning among mid-cost models).
  * Max: `openai/gpt-5.2-pro` with xhigh reasoning ($21/$168, 400K context, deepest OpenAI reasoning). Alternative: `openai/o3-pro` ($20/$80, lower output cost, currently used in the project for strategy-analysis).

* **Calibration caveat:** LLM probability estimates are useful for relative ranking but should not be treated as calibrated forecasts. Output should present ranked likelihoods rather than precise percentages unless the Risk Assessment Framework (P1-11) provides calibrated base rates.

* **Dependencies:** P0A-1 (Matter Memory) for timeline data; P0A-2 (ACT Court Procedures Calculator) for deadline arithmetic.

This can plug straight into your timetable diagrams and decision trees.

### 3.3 Adversarial review of your drafts

**ROADMAP:** Implemented via P3-22 (Simulated-Adversary Drafts, Phase 5). Shares infrastructure with P0A-3 (Letter Doctor) -- Letter Doctor focuses on tone/bias/risk in your drafts; adversarial review focuses on how the opponent would attack. These are complementary and should share prompt architecture and paragraph-by-paragraph analysis infrastructure.

Given your draft (letter, submissions, affidavit), the tool can:

* Walk paragraph by paragraph and:

  * Generate "Opponent's reaction" and likely attack.
  * Suggest specific paragraphs most vulnerable to inversion, mischaracterisation, or costs arguments.
* Produce:

  * A "Heat map" of attack surface:

    * eg Paragraphs 4, 7, 12 are high-risk for misrepresentation or collateral purpose allegations.
  * Suggested rewrites to:

    * Preserve your content but remove the easiest attack vectors.
    * Minimise apparent aggression or manipulation.

* Model recommendations. Legal reasoning quality is critical -- these reviews inform documents before filing. Mirrors the project's existing use of GPT-5.x for verification tasks:
  * Fast: `openai/gpt-5.2` ($1.75/$14, GDPval-AA 1462 Elo, strong reasoning and structured output).
  * Balanced: `google/gemini-3-pro-preview` ($2/$12, 1M context holds full draft + profile + analysis, BigLaw Bench 87.9%).
  * Max: `anthropic/claude-opus-4.6` with `thinking_effort: high` ($5/$25, GDPval-AA 1606 Elo, BigLaw Bench 90.2%). For filed-to-court documents, dual verification via P2-19 (e.g., Opus 4.6 + `openai/gpt-5-pro`) is available.

* Structured output for the heat map: `{paragraphs: [{number, risk_level: "high"|"medium"|"low", attack_vector, opponent_reaction, suggested_rewrite}]}`. Enforced via `response_format`.

* **Red-team triad pattern:** Automated red-teaming research uses an "attacker-target-judge" triad (one model generates opponent arguments, another identifies weaknesses, a third judges quality). This maps naturally to adversarial review. However, per CLAUDE.md, implement as a single comprehensive call with structured prompt sections (simulate --> identify weaknesses --> assess quality) rather than three separate model calls. A single call at the appropriate tier model with maximum thinking effort covering all three roles is preferred.

---

## 4. Strategy and cost modules

### 4.1 Strategy comparison from both sides

Given a list of options you are considering (eg file default judgment, press discovery, amend pleadings):

* For each option:

  * Simulate what the adversary is likely to do in response (applications, objections, etc).
  * Estimate:

    * Delay they are likely to cause.
    * Cost exposure for both sides.
    * Probabilistic impact on outcomes.

* Output:

  * A table like:

    * Row = your move.
    * Columns = likely counter-moves, probabilities, expected time / cost.
    * Notes referencing adversary profile features that drive the predictions.

* Model recommendations. Game-theoretic reasoning and structured multi-step analysis are the primary drivers:
  * Fast: `openai/gpt-5.2` ($1.75/$14, strong reasoning). Alternative: `google/gemini-3-flash-preview` ($0.50/$3) for cost-constrained use.
  * Balanced: `openai/o3-pro` with `thinking_effort: high` ($20/$80, matches existing `strategy-analysis` and `brainstorm-analysis` configs). Alternative: `openai/gpt-5.2` ($1.75/$14) if eval harness shows comparable quality at fraction of cost.
  * Max: `openai/gpt-5.2-pro` with xhigh reasoning ($21/$168, 400K context, newest deep-reasoning option). Alternative: `openai/o3-pro` ($20/$80, lower output cost). The project currently uses o3-pro for strategy tasks; eval harness should compare both.

* Structured output: Define a JSON schema for the move/counter-move matrix to enforce consistent tabular output.

This aligns with a "cost of obstruction" framework. Cross-reference P2-18 (Cost-of-Obstruction Ledger) for cost estimation data and P1-11 (Risk Assessment Framework) for probability estimation methodology.

### 4.2 Narrative and credibility modelling

For each adversary, maintain:

* Narrative themes they rely on:

  * eg "victim narrative", "harassed litigant", "overburdened agency".
* Vulnerabilities:

  * Inconsistencies across their documents.
  * Places where a decision-maker would find them irrational, vindictive, or implausible.
* Use this to:

  * Stress-test whether your narrative actually exploits those weaknesses.
  * Avoid reinforcing their preferred narrative accidentally.

* Model recommendations. Narrative analysis requires deep understanding of rhetorical patterns and psychological consistency:
  * Fast: `google/gemini-3-flash-preview` ($0.50/$3, near-Pro reasoning, 1M context for full document corpus).
  * Balanced: `openai/gpt-5.2` ($1.75/$14, GPQA Diamond 92-93%, strong general reasoning at moderate cost).
  * Max: `anthropic/claude-opus-4.6` with `thinking_effort: high` ($5/$25, GDPval-AA leader, strongest professional knowledge work benchmarks).

* Structured output: `{themes[], vulnerabilities[], inconsistencies[], narrative_risks[]}`.

* Cross-references: P0A-3 (Letter Doctor `--bias-scan`) for bias detection in your own drafts; P2-19 (Bias Divergence Detector) for multi-model consensus on high-stakes narrative assessments.

---

## 5. Integration with existing LitAssist architecture

This feature should be a layer over things you already have or plan:

### 5.1 Profiles as first-class YAML/JSON objects

* Store PartyProfile/LawyerProfile definitions under Matter Memory (per ROADMAP P1-9):

  * `~/.config/litassist/matters/profiles/party_a.yaml`
  * `~/.config/litassist/matters/profiles/opposing_counsel_b.yaml`
* Each can be updated automatically by profile generation calls or manually edited.
* Profile schema enforced via structured output at generation time.

### 5.2 Hooks into existing features

* Case-facts extraction:

  * Current: Basic 10-heading structured extraction (`litassist/commands/extractfacts/`)
  * Would need enhancement: Automatic author/signatory identification and role linking
  * Profile ingestion would initially require manual document-to-profile tagging
* Citation verification and authority modules:

  * Existing system verifies citations in YOUR drafts (`litassist/citation/verify.py`)
  * Opponent simulation would reuse this: when generating opponent arguments, verify their cited authorities are real
  * Profile could track opponent's preferred authorities

### 5.3 Model selection for adversarial features

Model assignments use the Fast/Balanced/Max Accuracy routing tiers recommended by the LLM Use Review (P0.2). All models route through OpenRouter per project convention (BYOK available for Anthropic, OpenAI, xAI).

| Adversarial Task | Fast | Balanced | Max Accuracy |
|---|---|---|---|
| Profile building (ingestion) | Gemini 2.5 Flash | Gemini 2.5 Pro | Claude Opus 4.6 |
| Steelman simulation | GPT-5.2 | Claude Opus 4.6 | GPT-5.2 Pro (xhigh) |
| Typical simulation | Grok 4.1 Fast | GPT-5.2 | Gemini 3 Pro |
| Move prediction | Gemini 3 Flash | GPT-5.2 | GPT-5.2 Pro (xhigh) |
| Adversarial draft review | GPT-5.2 | Gemini 3 Pro | Claude Opus 4.6 |
| Strategy comparison | GPT-5.2 | o3-pro | GPT-5.2 Pro (xhigh) |
| Narrative analysis | Gemini 3 Flash | GPT-5.2 | Claude Opus 4.6 |

**Selection rationale by task:**

* **Profile building:** Long-context accuracy is the primary driver. Gemini 2.5 Pro leads on LongBench v2 (68.2%) and costs $1.25/$5 at 1M context. Gemini 2.5 Flash extends the same context at $0.30/$2.50 for Fast. Opus 4.6 for Max provides the strongest legal reasoning for definitive profiles.
* **Steelman simulation:** Legal reasoning quality is paramount. GPT-5.2 for Fast offers GPQA Diamond 92-93% at $1.75/$14. Opus 4.6 for Balanced leads GDPval-AA (1606 Elo) and BigLaw Bench (90.2%). GPT-5.2 Pro (xhigh) for Max provides 400K context and the newest deep-reasoning mode (ARC-AGI-2 54.2%); o3-pro ($20/$80, lower output cost) is the alternative if eval harness favours it.
* **Typical simulation:** Style replication over deep reasoning. Grok 4.1 Fast for Fast matches the project's use of Grok for creative/unorthodox generation at $0.20/$0.50. GPT-5.2 for Balanced provides strong general reasoning at moderate cost. Gemini 3 Pro for Max offers 1M context and BigLaw Bench 87.9%.
* **Move prediction:** Probabilistic reasoning and pattern analysis. Gemini 3 Flash for Fast offers near-Pro reasoning at $0.50/$3. GPT-5.2 for Balanced provides the strongest abstract reasoning (GPQA 92-93%). GPT-5.2 Pro (xhigh) for Max provides 400K context and deep reasoning; o3-pro is the alternative at lower output cost.
* **Adversarial draft review:** Critical quality task mirroring the project's use of GPT-5.x for verification. GPT-5.2 for Fast at $1.75/$14 with GDPval-AA 1462 Elo. Gemini 3 Pro for Balanced at $2/$12 with BigLaw Bench 87.9% and 1M context (holds full draft + profile + analysis). Opus 4.6 for Max at $5/$25 with GDPval-AA 1606 Elo for the highest-stakes reviews.
* **Strategy comparison:** Game-theoretic structured reasoning. GPT-5.2 for Fast at $1.75/$14. o3-pro for Balanced matches the project's existing `strategy-analysis` and `brainstorm-analysis` configs. GPT-5.2 Pro (xhigh) for Max is the newer deep-reasoning option with 400K context; o3-pro ($20/$80, lower output cost) remains a viable alternative pending eval harness comparison.
* **Narrative analysis:** Understanding rhetorical patterns and psychological consistency. Gemini 3 Flash for Fast at $0.50/$3 with near-Pro quality. GPT-5.2 for Balanced at $1.75/$14 with strong general reasoning. Opus 4.6 for Max as the overall professional knowledge work leader.

**Provider distribution across tiers:**

* Fast: Google 4 (Gemini 2.5 Flash, 3x Gemini 3 Flash), OpenAI 2 (GPT-5.2), xAI 1 (Grok 4.1 Fast)
* Balanced: Google 2 (Gemini 2.5 Pro, Gemini 3 Pro), OpenAI 4 (3x GPT-5.2, o3-pro), Anthropic 1 (Opus 4.6)
* Max: OpenAI 3 (3x GPT-5.2 Pro xhigh), Anthropic 3 (Opus 4.6), Google 1 (Gemini 3 Pro)

Multi-model consensus is available via P2-19 (Bias Divergence Detector) for high-stakes outputs such as adversarial reviews of documents being filed to court. This is not the default approach -- it is reserved for quality gates on critical filings.

All assignments are recommendations pending validation via the eval harness (LLM Use Review P0.1). Different models lead on different benchmarks, so task-specific evaluation is essential before finalising production model assignments.

### 5.4 Prompt architecture

All adversarial prompts go in `litassist/prompts/adversarial.yaml`, accessed via `PROMPTS.get()` with stable keys:

* `adversarial.simulate.steelman`
* `adversarial.simulate.typical`
* `adversarial.review.heatmap`
* `adversarial.predict.moves`
* `adversarial.profile.build`
* `adversarial.strategy.compare`
* `adversarial.narrative.analyse`

### 5.5 Structured output enforcement

All adversarial outputs use JSON schema enforcement via `response_format` parameter. This guarantees valid output and eliminates parsing logic (per CLAUDE.md: "Prefer prompt engineering over local parsing" and "No fallback parsing logic").

### 5.6 CLI / API surface

Example commands (with required `--matter` flag and optional `--tier` flag per LLM Use Review):

* `litassist adversary build-profile --actor="PartyA" --from-folder="matters/..." --matter LITIGATION-001`
* `litassist adversary simulate-letter --actor="OpposingCounselB" --reply-to="draft.txt" --matter LITIGATION-001 --tier max_accuracy`
* `litassist adversary stress-test --actor="OpposingCounselC" --draft="submissions.txt" --matter LITIGATION-001`

---

## 6. Minimal viable version vs later extensions

### 6.1 MVP (worth doing first)

**Mapped to ROADMAP items:**
* Actor profiles as YAML files -> **P1-9** (Opponent Profiling System, Phase 3, 8-10h)
* "Write as [Opponent]" mode + Basic adversarial review -> **P3-22** (Simulated-Adversary Drafts, Phase 5, 8-10h)
* Lightweight move prediction -> Part of **P1-9** scope

**Total estimated effort:** 16-20 hours (per ROADMAP estimates).
**Hard prerequisite:** P0A-1 (Matter Memory Module) must be implemented first.
**Eval dependency:** Model assignments should be validated via the eval harness (LLM Use Review P0.1) before production use.

MVP scope:

* Actor profiles as YAML files with:

  * Links to documents, rough behaviour notes, manual priors.
  * Context-first profile generation via 1M token context window (Section 2.2).
* "Write as [Opponent]" mode:

  * Generate steel-man letters and submissions from their side.
* Basic adversarial review:

  * Paragraph-by-paragraph "this is how they will attack this" commentary.
  * Shared infrastructure with Letter Doctor (P0A-3).
* Lightweight move prediction:

  * Ranked list of likely applications and timing with likelihoods (not precise percentages).

This already gives practical value in daily drafting and strategic planning.

### 6.2 Later / advanced features

* Quantitative behavioural statistics:

  * Charts of deadline compliance, adjournment patterns, etc.
  * Not yet in ROADMAP; would be a new item.
* Multi-matter learning:

  * Aggregate behaviour across several cases (if you end up facing them repeatedly).
  * Relates to P0A-1 (Matter Memory) cross-matter capabilities.
  * Feasibility improved by 1M context windows: multiple matters' documents for the same opponent can be loaded simultaneously.
* Judge-aware adversarial modelling:

  * Integrate what you know about particular decision-makers with how this opponent has behaved before that bench.
  * **Status: deprioritised.** Corresponds to DEP-28 (Judge Analytics) in ROADMAP, priority NONE (productisation feature).
* Cross-matter pattern detection:

  * eg "Whenever you raise X, they respond with Y and escalate costs threats."
  * Not yet in ROADMAP; would be a new item.
* Adversarial eval benchmarking:

  * Create a gold-standard set of known opponent arguments/moves for specific matter types.
  * Use to validate model performance on adversarial tasks and prevent regression during model swaps.
  * Aligns with the eval harness recommendation from the LLM Use Review (P0.1).

---

## 7. Caveats and alternative views

1. Risk of caricature and confirmation bias

   * Over-fitting a profile might tempt you to treat speculative predictions as facts, which could distort strategic choices.

2. Resource and complexity cost

   * Implementing this fully (stats, timelines, simulation) could be expensive and time-consuming compared with simpler features such as improved case-facts extraction or authority checking.

3. Model capability dependence

   * Adversarial modelling quality is directly dependent on the underlying model's legal reasoning capability. The eval harness (LLM Use Review P0.1) should include adversarial-specific test cases to validate that model changes do not degrade adversarial output quality. A model swap that improves drafting might simultaneously degrade opponent simulation -- these must be tested independently.

4. Alternative view A

   * Instead of highly personalised profiles, you might get 80 percent of the value from generic pattern modules: "how applicants in this matter type typically behave", "how defence firms commonly respond to this type of litigation", etc. However, 1M context windows reduce the cost argument for generic patterns: personalised profiles generated from a single context-first call are now cheap enough that the incremental cost over generic patterns is small.

5. Alternative view B

   * Some would argue that adversarial modelling should be used sparingly and only to generate best-case steel-man arguments, not to psychoanalyse behaviour. That keeps the tool focused on doctrinal quality rather than personalities.

6. Single-call vs multi-agent architecture

   * The "attacker-target-judge" triad from automated red-teaming research (where one model generates opponent arguments, another identifies weaknesses, a third judges quality) maps naturally to adversarial modelling. However, per CLAUDE.md, LitAssist should implement this as a single comprehensive call with structured prompt sections rather than orchestrating three separate model calls. The commercial legal AI trend (Thomson Reuters CoCounsel, LexisNexis Protege) leans toward multi-agent orchestration, but LitAssist's CLI-first, single-call philosophy is a deliberate design choice favouring simplicity and cost control.

---

**Confidence rationale:**
This design is now aligned with the actual codebase architecture (Matter Memory storage paths, PROMPTS.get() access pattern, OpenRouter routing), the ROADMAP (P1-9, P3-22), and the LLM Use Review (eval harness, routing tiers). The main remaining uncertainty is how well current models perform on adversarial legal tasks, which requires eval harness validation before production model assignments are finalised.

Answer: Adversarial modelling for LitAssist would consist of explicit opponent profiles (parties, lawyers, agencies) built from their historic documents and behaviour, plus tools that use those profiles to simulate their arguments and moves, stress-test your drafts, and estimate costs and timelines. The context-first approach enabled by 1M+ token context windows simplifies the ingestion pipeline to a single comprehensive call. MVP maps to ROADMAP P1-9 + P3-22 (16-20 hours total). Model assignments span all major providers: Google models (Gemini 2.5 Pro/Flash, Gemini 3 Pro/Flash) dominate the Fast tier on cost-efficiency and long-context performance; OpenAI models (GPT-5.2, GPT-5.2 Pro, o3-pro) feature across Balanced and Max tiers on reasoning benchmarks and deep analysis; Anthropic (Claude Opus 4.6) leads Max Accuracy for legal reasoning (GDPval-AA 1606, BigLaw Bench 90.2%); xAI (Grok 4.1 Fast) fills the ultra-low-cost creative niche. All assignments are pending eval harness validation. | Confidence 0.85 | Top uncertainty driver: Model performance on adversarial legal tasks pending eval harness validation.
