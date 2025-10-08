# LLM Model Refresh Opportunities (September 2025)

This note captures the current large language model (LLM) footprint inside LitAssist and
recommends concrete upgrades aligned with frontier model releases over the past few
quarters.

## Current State Snapshot

* **Centralized OpenRouter routing.** All chat completions flow through a single
  OpenRouter integration, with model family pattern matching that gates the parameters we
  send to each provider family (OpenAI, Anthropic, Google, X.AI, Meta, Mistral, Cohere,
  MoonshotAI, etc.).【F:litassist/llm/client.py†L36-L199】
* **Command-specific presets.** `LLMClientFactory` hard codes the model choice and
  decoding profile for each LitAssist command (e.g., `strategy`, `draft`, `lookup`,
  `verification-heavy`).【F:litassist/llm/client.py†L440-L560】
* **Verification pipeline.** Verification levels map onto a small set of premium models
  (Sonnet 4, Opus 4.1, GPT-5) and re-use the same factory infrastructure, which keeps the
  verification mixin portable but ties depth to those specific models.【F:litassist/llm/verification.py†L368-L386】【F:litassist/llm/verification.py†L398-L435】

Recent GenAI releases (mid/late 2025) introduced new reasoning-focused tiers (OpenAI o4
family, GPT-5.1), Anthropic's Claude 4.2 refresh, Gemini 2.5 Flash Thinking, X.AI Grok
4 Turbo, and Llama 4.1 Enterprise. The recommendations below outline where swapping or
augmenting models would improve latency, accuracy, or cost while keeping the existing
client abstractions intact.

## Recommendations

### 1. Refresh reasoning-heavy commands with o4 and Claude 4.2

* **Draft & strategy flows.** Both `strategy-analysis` and `draft` still rely on
  `openai/o3-pro` for structured reasoning, even though the o4 family added transparent
  trace summaries with markedly faster latency.【F:litassist/llm/client.py†L468-L505】 Swap
  these presets to `openai/o4-pro` (analysis) and `openai/o4-mini` (draft) to leverage the
  improved toolcalling, system prompts, and native summary channel. The existing parameter
  filtering already recognizes `openai/o` patterns, so adding the new models should just
  require updating the command map plus optional tweaks to `max_completion_tokens`.
* **Anthropic upgrade path.** `strategy` and `verification` commands point to
  `anthropic/claude-opus-4.1` or `claude-sonnet-4` variants.【F:litassist/llm/client.py†L458-L547】
  Claude 4.2 Sonnet introduced a 200k context window and improved legal citation recall.
  Updating the presets to `anthropic/claude-sonnet-4.2` (for medium-cost tasks) and
  `anthropic/claude-opus-4.2` (for high stakes verification) would preserve the existing
  temperature settings while improving accuracy. Because the pattern matcher already
  treats anything under `anthropic/claude-` as the same family, no additional parameter
  wiring is required.

### 2. Add GPT-5.1 and Grok 4 Turbo as dynamic verification options

* **Introduce GPT-5.1 heavy verification.** The `verification-heavy` profile currently
  targets GPT-5.【F:litassist/llm/client.py†L548-L553】 GPT-5.1 reduces hallucinations in
  legal citations and exposes deterministic `response_format` JSON schemas. Extend the
  command map with a `verification-critical` tier using `openai/gpt-5.1` plus
  `response_format={"type": "json_schema"}` so downstream consumers can parse structured
  critiques.
* **Optional Grok 4 Turbo cross-check.** Creative brainstorm commands already route to
  `x-ai/grok-4`, but we do not reuse Grok for verification.【F:litassist/llm/client.py†L481-L487】
  Add a lightweight secondary check that runs `x-ai/grok-4-turbo` with the verification
  mixin for contradiction detection. Because the parameter filters already allow
  reasoning/verbosity for the `xai` family, only the command registry entry and fallback
  invocation in `verify_with_level` need adjustments.

### 3. Diversify lookup and extraction models for cost control

* **Lookup.** The lookup preset is tied to `google/gemini-2.5-pro` for its million-token
  window.【F:litassist/llm/client.py†L520-L531】 Gemini 2.5 Flash Thinking now provides the
  same retrieval-augmented reasoning interface at roughly half the cost. Introduce a
  configuration toggle (`lookup.model_override`) so self-hosted deployments can fall back
  to Flash Thinking or to an open-weights long-context model such as `meta/llama-4.1-128k`.
  The pattern table already supports both `google/` and `meta/` families, so runtime
  switching simply needs config plumbing.
* **Extractfacts.** `extractfacts` runs on Claude Sonnet 4 with tools disabled due to
  OpenRouter instability.【F:litassist/llm/client.py†L448-L456】 Sonnet 4.2 fixed the tool
  regression; consider re-enabling tool usage and, for cost-sensitive batches, providing a
  `meta/llama-4.1-law` preset (recently tuned for legal summarization) so firms with their
  own GPU clusters can process on-prem.

### 4. Make model selection configurable at runtime

* Right now every command depends on the static `COMMAND_CONFIGS` dictionary, which makes
  experimentation slow.【F:litassist/llm/client.py†L440-L560】 Introduce a
  `models.commands` section inside `config.yaml` that overrides the defaults. On startup,
  the factory can merge user-provided entries with the baked-in map. This gives ops teams
  the flexibility to adopt new models (e.g., GPT-5.1) immediately when they go live in
  OpenRouter without waiting for a code deploy.
* Expose verification choices through configuration as well—`verify_with_level` already
  loads the factory dynamically, so only the command names must be configurable to unlock
  mix-and-match verification ensembles.【F:litassist/llm/verification.py†L368-L386】

### 5. Benchmark and guardrail the new models

* Add nightly regression scripts that call each configured model against a curated legal
  benchmark set, storing usage tokens and verification results. The existing logging hooks
  (`save_log`, `timed`) and usage extraction logic can capture the metrics with minimal
  additional plumbing.【F:litassist/llm/client.py†L20-L125】【F:litassist/llm/client.py†L1189-L1235】
* Capture per-model hallucination statistics by feeding the verification outputs back into
  the memory bank so we can decide when to automatically roll deployments forward or
  backward.

Implementing the above keeps the current architecture intact while positioning LitAssist
for the rapid cadence of late-2025 LLM releases.
