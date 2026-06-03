# LitAssist model audit against OpenRouter live catalogue

> **SUPERSEDED — 28/05/2026.** This audit is a snapshot of the model
> set as of 21/04/2026 and references models (`openai/gpt-5.1`,
> `openai/gpt-5-pro`, `text-embedding-3-small`) that are no longer in
> production. The live model set lives in
> `litassist/llm/model_configs.yaml`; capability data is regenerated
> by `litassist refresh` into `litassist/llm/model_capabilities.yaml`.
> Use those two files as the authoritative source.
>
> The RAG / Pinecone embedding pipeline this audit references was
> removed in the `remove-pinecone-rag` branch (May 2026). The
> `text-embedding-3-small` row is no longer applicable.

Last updated: 28/05/2026

| Field | Value |
|---|---|
| Audit as-at date (per request) | 21 April 2026 |
| OpenRouter catalogue snapshot | 2026-05-09T09:27:20Z (367 models returned) |
| Endpoint | `https://openrouter.ai/api/v1/models` (no auth required) |
| Repo HEAD examined | `agelastic/litassist-priv` master `63fc011` (17 April 2026) |
| Config source of truth | `litassist/llm/model_configs.yaml` |

> **Note on the snapshot date.** The user-facing audit date is 21 April 2026 per the request. The actual catalogue snapshot was taken on 09 May 2026 because that is when the audit was run. All findings below reflect the live OpenRouter state on the snapshot date. If the audit needs an as-at-21-April catalogue, that data is no longer recoverable from the live endpoint.

> **Headline finding.** Five of the six chat models configured for production are still served by OpenRouter with no expiration date. The sixth, `x-ai/grok-4`, has `expiration_date = 2026-05-15`, i.e. six days from the snapshot date. All Grok 3.x and 4.x models expire on the same day. The only two configured pieces of work that are not on OpenRouter are the embedding model (`text-embedding-3-small`, called directly via the OpenAI API by design) and the Jade/AustLII fetchers (not LLMs).

> **BYOK summary.** Per the OpenRouter BYOK documentation (https://openrouter.ai/docs/use-cases/byok), BYOK is **optional** on every model in the public catalogue. Bringing your own provider key replaces OpenRouter's normal markup with a flat 5% surcharge on the underlying provider price (waived for the first 1M BYOK requests/month). Every model the repo currently configures works on OpenRouter credits alone, including `openai/o3-pro`. The `CLAUDE.md` line "OpenAI (for o3-pro BYOK)" therefore reflects a project-level cost choice, not an OpenRouter access requirement.

## 1. OpenAI models

| Model id | Used in (file:line) | Status | Pricing in/out per 1M | Context | BYOK | Notes |
|---|---|---|---|---|---|---|
| `openai/o3-pro` | `litassist/llm/model_configs.yaml:24, 48, 55, 144, 152` | STILL SERVED | $20.00 / $80.00 | 200,000 | optional (5% surcharge if BYOK) | Used for `strategy-analysis`, `brainstorm-analysis`, `draft`, `counselnotes`, `barbrief`. No `expiration_date`. Knowledge cutoff 2024-06-30. Supports `response_format`, `structured_outputs`, `tools`. Note: catalogue now also lists `openai/o3-deep-research` ($10/$40) and `openai/o3` ($2/$8) which may be cheaper alternatives for some commands; benchmark before swapping. |
| `openai/gpt-5.1` | `litassist/llm/model_configs.yaml:86, 190` | STILL SERVED | $1.25 / $10.00 | 400,000 | optional | Used for `verification`, `cove-answers`. Best price/performance reasoning model in the configured set. Supports `response_format` and `structured_outputs`. Catalogue also lists `openai/gpt-5.2` and `openai/gpt-5.3-chat` newer than this. |
| `openai/gpt-5-pro` | `litassist/llm/model_configs.yaml:102, 118, 135, 206` | STILL SERVED | $15.00 / $120.00 | 400,000 | optional | Used for `verification-heavy`, `verify-reasoning-heavy`, `verify-soundness-heavy`, `cove-answers-heavy`. Knowledge cutoff 2024-09-30. The most expensive completion price in the configured set; verify it is still pulling its weight versus `gpt-5.2-pro` (newer, also in catalogue). |
| `text-embedding-3-small` | `config.yaml.template:11`, `litassist/config.py:120` | NOT VIA OPENROUTER (by design) | n/a | n/a | n/a | OpenAI embeddings are called directly through the OpenAI SDK using the configured `openai.api_key`. OpenRouter does not list embedding models in its chat-completions catalogue. No action required; this is the supported pattern. |

## 2. Anthropic models

| Model id | Used in (file:line) | Status | Pricing in/out per 1M | Context | BYOK | Notes |
|---|---|---|---|---|---|---|
| `anthropic/claude-sonnet-4.6` | `litassist/llm/model_configs.yaml:7, 15, 31, 63, 70, 77, 94, 110, 160, 167, 174, 182, 198, 214` | STILL SERVED | $3.00 / $15.00 | 1,000,000 | optional | Workhorse model, used by 14 of 26 command profiles. No `expiration_date`. 1M context. Supports the full modern parameter set: `response_format`, `structured_outputs`, `tools`, `tool_choice`, `reasoning`, `verbosity`. Catalogue also lists `claude-opus-4.6`, `claude-opus-4.7`, `claude-haiku-4.5` if you want to widen the dispatch. |
| `anthropic/claude-opus-4.1` | `litassist/llm/model_configs.yaml:126` | STILL SERVED | $15.00 / $75.00 | 200,000 | optional | Used only by `verify-soundness`. Knowledge cutoff 2025-01-31. No `expiration_date`. Worth noting the catalogue has `claude-opus-4.6` and `claude-opus-4.7` available; consider benchmarking before keeping 4.1 on this one role. |

## 3. Google models

No Google/Gemini models are referenced in the production model_configs.yaml. Google appears in tests (`test-scripts/test_dynamic_parameters.py`, `tests/unit/test_verification.py` referencing `google/gemini-2.5-pro`, `google/gemini-pro`, `google/palm-2`) but only as test fixtures for the parameter dispatch logic in `model_profiles.py`. None of those identifiers are exercised against the live API in the unit tests. No action required.

## 4. Meta / Llama models

No Meta/Llama models configured. Test fixture only: `meta/llama-2-70b` in `test-scripts/test_dynamic_parameters.py:26`. No action required.

## 5. Other vendors (xAI, Mistral, DeepSeek, Qwen, Cohere)

### xAI

| Model id | Used in (file:line) | Status | Pricing in/out per 1M | Context | BYOK | Notes |
|---|---|---|---|---|---|---|
| `x-ai/grok-4` | `litassist/llm/model_configs.yaml:39` | **EXPIRES 2026-05-15** | $3.00 / $15.00 | 256,000 | optional | Used by `brainstorm-unorthodox`. `expiration_date: "2026-05-15"` returned by the catalogue. Six days from snapshot date. All Grok 3.x and 4.x line items in the catalogue carry the same expiration. **Action required before 15 May 2026** — see Section 6. |

### Mistral, DeepSeek, Qwen, Cohere

No production references. Cohere and Mistral appear only as keys in `litassist/llm/model_profiles.py` (regex patterns and parameter profiles for dispatch logic), not as configured models. Qwen and DeepSeek are not referenced anywhere. No action required.

## 6. Deprecated / not found

Only one item requires action.

| Configured id | Issue | Recommended replacement(s) | Rationale |
|---|---|---|---|
| `x-ai/grok-4` | OpenRouter `expiration_date: 2026-05-15`. Will start returning 404 / removed-from-list errors after that date. | `x-ai/grok-4.20` (preferred) or `x-ai/grok-4.3` | `grok-4.20`: 2M context (was 256K), same intent (xAI flagship), pricing $1.25/$2.50 per 1M (cheaper than grok-4 at $3/$15), no expiration set. `grok-4.3`: 1M context, $1.25/$2.50, also no expiration. Either is a drop-in upgrade for the `brainstorm-unorthodox` command. The minimal-change PR is a one-line edit to `model_configs.yaml`. |

No other configured production models are deprecated, missing, or scheduled for removal at the snapshot time.

## 7. BYOK summary

| Model | Works on OR credits alone? | BYOK required? | BYOK optional? | Notes |
|---|---|---|---|---|
| `anthropic/claude-sonnet-4.6` | Yes | No | Yes (5% surcharge instead of OR markup) | |
| `anthropic/claude-opus-4.1` | Yes | No | Yes | |
| `openai/o3-pro` | Yes | No | Yes | Project currently uses BYOK by choice per `CLAUDE.md`; this is a cost decision, not a hard requirement. |
| `openai/gpt-5.1` | Yes | No | Yes | |
| `openai/gpt-5-pro` | Yes | No | Yes | |
| `x-ai/grok-4` | Yes (until 2026-05-15) | No | Yes | After 15 May 2026, neither OR credits nor BYOK will work — model is being retired by xAI. |
| `text-embedding-3-small` | n/a (not on OR) | n/a — direct OpenAI key | n/a | Stays as-is. |

> **Confirmation method.** OpenRouter docs at https://openrouter.ai/docs/use-cases/byok state: *"OpenRouter supports both OpenRouter credits and the option to bring your own provider keys (BYOK)... The cost of using custom provider keys on OpenRouter is 5% of what the same model/provider would cost normally on OpenRouter."* No BYOK-only restriction is documented for any model in the litassist configuration. Azure OpenAI, AWS Bedrock, and Google Vertex deployments require BYOK, but litassist does not target any of those provider IDs.

## 8. Methodology

**Endpoint hit.**
- `GET https://openrouter.ai/api/v1/models` at 2026-05-09T09:27:20Z. HTTP 200, 435 KB response, 367 model entries. Saved locally at `/sessions/upbeat-optimistic-edison/openrouter_models.json` for the duration of the audit (not committed to the repo).

**Documentation pages consulted.**
- BYOK: https://openrouter.ai/docs/use-cases/byok (fetched 2026-05-09).

**Inventory method.**
1. `grep` over `litassist/llm/model_configs.yaml` for all `model:` keys (the canonical config).
2. `grep` over the rest of `litassist/`, `tests/`, `test-scripts/` for the regex `(anthropic|openai|google|x-ai|meta-llama|mistral|deepseek|qwen|cohere)/` to catch any code-side overrides.
3. Read `config.yaml.template` for embedding-model and other non-OR identifiers.
4. Cross-reference each distinct model id against the OR catalogue using `jq`.

**De-duplication.** All distinct OR-routed model ids found in the production config (excluding test fixtures and parameter-profile regex keys): six. Plus one OpenAI direct-API embedding model. Test fixtures (`google/gemini-pro`, `meta/llama-2-70b`, `mistral/mixtral-8x7b`, `cohere/command`, `openai/o5`, etc.) were excluded from the audit because they are synthetic identifiers exercising parameter dispatch logic, not real calls.

**What was not audited.**
- Pinecone (vector DB, separate service).
- Google CSE (custom search, separate service).
- Jade/AustLII fetchers (HTTP, not LLM).
- Jina Reader (web fetcher, separate service).

**Confidence caveats.**
- BYOK conclusions are based on the public OR docs page, which describes BYOK as an optional cost-optimisation feature applied to all listed models. There is no machine-readable per-model BYOK flag in the catalogue JSON, so the conclusion is inferred from the doc, not measured from a per-model field. If a specific model later becomes BYOK-only (which has happened in the past for some Anthropic enterprise tiers), a separate confirmation against the OR `/integrations` UI would be needed to detect that.
- The 21 April 2026 audit date is honoured in the file name; the actual catalogue snapshot reflects 9 May 2026 state. The substantive findings would not differ on 21 April for the configured models, but `expiration_date` semantics for Grok 4 would have read as "scheduled for removal in 24 days" rather than "in 6 days".
