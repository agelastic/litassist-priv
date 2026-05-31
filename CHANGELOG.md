# Changelog

Last updated: 30/05/2026

All notable changes to LitAssist will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Historical dated sections preserve the model names that were current when those changes shipped. Current model assignments are defined in `litassist/llm/model_configs.yaml`.

## [Unreleased]

### Added
- `updatefacts` command: folds source documents (digest/extractfacts output or any text) into the 10-heading case_facts structure, updating an existing case-facts file (auto-resolved from the latest `case_facts*.txt`, or set with `--facts`) or creating one from scratch, with an extra Notes section for material that does not fit a heading. Writes a fresh, auto-discoverable `case_facts_<timestamp>.txt` into the working directory, removing the manual copy-to-`case_facts.txt` step. Uses a cheap merge model (`google/gemini-3.5-flash`).
- Comprehensive citation verification system with real-time Jade.io validation
- Reasoning trace capture across all commands for accountability
- Heartbeat progress indicators for long-running operations
- Advanced reasoning models support (o3-pro) for strategic analysis
- Barrister's brief generation command (barbrief)
- Counsel notes strategic analysis command
- Case plan generation for litigation planning
- `litassist refresh` subcommand: pulls per-model context-window, prices, and supported-parameters from OpenRouter `/api/v1/models` and writes `litassist/llm/model_capabilities.yaml`. Fails loudly when any model in `model_configs.yaml` is missing from the OpenRouter response.
- Direct OpenAI configuration removed. `config.yaml` no longer carries an `openai:` block; the project routes every LLM call through OpenRouter using `openrouter.api_key`. Provider-level BYOK for models like `openai/o3-pro` is configured at https://openrouter.ai/settings/integrations, not in this project's config.
- Stale model references cleaned up across docs and prompts. `litassist/prompts/system_feedback.yaml` dropped its dead `api:` subsection (`key_placeholder`, `byok_required_o1_pro`, `byok_required_o3` — none of which had any consumer in code). `litassist/README.md` example updated from `anthropic/claude-3-sonnet` to `anthropic/claude-sonnet-4.6`. `litassist/commands/digest/chunker.py` openai chunk-limit comment retargeted from `GPT-4/o3's 400k context` to the actual active models. `docs/development/LLM_MODEL_STRATEGY.md` ensemble example fixed from non-existent `x-ai/grok-4.20-turbo` to `x-ai/grok-4.20`. `docs/development/adversarial_modelling.md` Model Landscape section gained a design-time caveat clarifying that specific version pins (Claude Opus 4.6, Gemini 2.5, Grok 4.1 Fast) need re-validation against `model_configs.yaml` at implementation time.
- Parameter-translation infrastructure in `litassist/llm/model_profiles.py` is explicitly NOT narrowed. A header comment encodes the policy: the classifier tables must cover any OpenRouter model the user might swap into `model_configs.yaml`, not just the currently-active set.
- `LLMClientFactory.get_context_window_for_command()` lookup helper backed by the new capability file.
- `draft` preflight oversize handling: soft warn + hard fail derived from the model's actual context window plus a provider-error reframe pointing users at `litassist digest --mode summary <file>`.

### Changed

#### May 2026: dropped the no-op `--verify` flag from extractfacts and strategy
- `extractfacts` and `strategy` ran verification unconditionally (the call site hard-coded `verify_flag=True`), so their `--verify` flag did nothing but print a "verification already active" reminder. The flag is removed from both commands. Verification remains auto-enabled; use `--noverify` to skip it. `draft` already followed this pattern. The functional `--verify` on `brainstorm`, `counselnotes`, and `barbrief` (which genuinely toggles citation/content verification) is unchanged, as is the unsupported-flag guard on `lookup`, `digest`, and `caseplan`.

#### May 2026: case facts file is optional - latest case_facts*.txt auto-selected
- The case facts input is now optional for `caseplan`, `strategy`, `barbrief` (positional), `brainstorm` (`--facts`), and `draft` (`documents`). When omitted, the new shared `resolve_case_facts_file()` (`litassist/utils/case_facts.py`) picks the most recent `case_facts*.txt` in the launch directory and prints which file it chose. Recency is the `YYYYMMDD_HHMMSS` timestamp embedded in the filename (e.g. `case_facts_20260530_101500.txt`) when present, otherwise the file's modification time - so the newest timestamped version wins, but a freshly-edited plain `case_facts.txt` is not shadowed by an older timestamped file. If no `case_facts*.txt` exists, the command fails with a clear message. `brainstorm`'s previous bespoke `case_facts.txt`-only default is replaced by this shared resolver. Commands that produce or do not consume case facts (`extractfacts`, `lookup`, `digest`, `counselnotes`, `verify`, `verify-cove`) are unchanged.

#### May 2026: barbrief 10-heading validation matches strategy (shared validator)
- The 10-heading case-facts check is now a single shared function, `validate_case_facts_format` in `litassist/utils/case_facts.py`, used by both `strategy` and `barbrief` (re-exported from `litassist/commands/strategy/validators.py` for existing importers). `barbrief` previously used a looser substring check (`barbrief/validator.py`, now removed) that accepted a heading appearing anywhere in the text; it now uses the shared validator and lists missing headings, matching `strategy`.
- The shared validator was also corrected: it now recognises a heading when it is the first alphabetic token on a line (after optional numbering / markdown bold / punctuation), so it accepts every form `extractfacts` produces -- `Parties:` on its own line, `## Parties`, and `1. **Parties**: ...` with the description inline. The previous per-line regex required the heading to end its line and so rejected the numbered/bold/inline style of the `extractfacts` format template (a latent `strategy` bug, surfaced when the check was shared with `barbrief`).
- `strategy.extract_legal_issues` was made format-tolerant to match: it now captures an issue written inline on the `Legal Issues` heading line and detects the next section heading by shape (header at line start, then a `:`/`*`/`#` or end-of-line boundary) instead of an exact-string match. Previously, once the looser validator let numbered/bold inline headings through, it missed the inline issue and over-ran into later sections.

#### May 2026: parameter translation aligned with recent GPT-5 / o3 / Grok / Gemini changes
- `litassist/llm/parameter_handler.py` and `model_profiles.py` now map generated requests to each model's current accepted parameters. GPT-5.5 gained the `xhigh` reasoning tier, so the universal `thinking_effort: max` maps to `xhigh` for `gpt5.5` (its ceiling); older GPT-5 variants and the o-series still cap at `high`. `verbosity` is now skipped for Grok 4.x (alongside the o-series) because those models do not accept it, and the `xai` profile was trimmed to grok-4.20's supported set -- `frequency_penalty`/`presence_penalty`/`verbosity`/`stop` dropped, while `min_p`/`top_a`/`repetition_penalty` continue to ride `extra_body` as best-effort. The o-series (o3-pro) already mapped correctly and is unchanged; Gemini now also skips `verbosity` (which `gemini-3.5-flash` does not accept and the `lookup` configs were setting). Both are pinned by tests.
- A directly-supplied `reasoning.effort` (a caller passing `reasoning={"effort": ...}` rather than `thinking_effort`) is now normalised through the same per-family mapping, so it cannot bypass the effort caps (e.g. `xhigh`/`max` reaching o3 or sonnet); an `effort` of `none` or `null` drops the reasoning object entirely (it is not coerced to medium).
- Added a maintenance reminder in `model_profiles.py` (and the effort/verbosity handlers): when a model is added to `model_configs.yaml`, verify its accepted parameters and reasoning-effort tiers before relying on the default profile. The command config files are intentionally kept uniform; per-model parameter differences are resolved only in the translation layer.

#### May 2026: Claude 4.x parameter mapping corrected (Opus 4.7/4.8 sampling removed; new effort tiers)
- Claude parameter handling was split into precise families in `litassist/llm/model_profiles.py`: `claude_opus_4_7` and `claude_opus_4_8` (Opus reasoning models that removed `temperature`/`top_p`/`top_k` -- non-default values return a 400) and `claude4_sampling` (older opus + all sonnet-4.x, which keep sampling). Previously every Claude 4.x model fell back to the `default` profile, which forwarded `temperature`/`top_p`; OpenRouter silently absorbed the unsupported params. The Opus profiles now omit sampling entirely, so the `strategy`, `verify-soundness`, and `caseplan` (full-plan) configs no longer send parameters Opus 4.7 rejects.
- Anthropic rejects `temperature` and `top_p` specified together (since 4.1). `get_model_parameters` now drops `top_p` when both are present for `claude4_sampling` models (keeping `temperature`), fixing the latent "temperature and top_p cannot both be specified" 400 across the sonnet-4.6 commands (`extractfacts`, `digest`, `brainstorm-orthodox`, `verification-light`, `verify-reasoning`, `cove*`, `caseplan-assessment`).
- Opus 4.7/4.8 effort scale extended: `thinking_effort` now passes `xhigh` and `max` through for those models (default `xhigh` on 4.7, `high` on 4.8); other families cap `xhigh`/`max` to `high`. `xhigh` is now a recognised universal effort level.
- New guard test `tests/unit/test_model_config_sampling.py` cross-checks every command's effective sampling params against the model's OpenRouter `supported_parameters` from `model_capabilities.yaml`, so config/model drift that would send an unsupported sampling param fails CI.

#### May 2026: `caseplan` generated-command safety, fail-loud extraction, Opus full-plan
- Generated commands are now validated before the runnable script is written. `extract_cli_commands` (`litassist/commands/caseplan/command_extractor.py`) tokenises each candidate with `shlex.split` and re-renders it with `shlex.join`, so shell control characters in LLM output (`;`, `|`, `&&`, `$(...)`, redirections) cannot survive as live operators; only lines whose first parsed token is exactly `litassist` are accepted (a leading `Commands:` label is stripped first), and candidates that fail validation are reported as rejected. It now returns `(script, accepted_count, rejected)`.
- Full-plan mode fails loud instead of silently saving a header-only script: when no commands are accepted, `plan_generator` warns and skips both the command file and the `bash <file>` tip; rejected commands are listed.
- Budget-assessment mode now includes `--context` in the LLM prompt (previously the argument was accepted but never used) under the same `USER ANALYSIS GUIDANCE (NOT case facts)` framing as full-plan mode.
- Empty or whitespace-only case facts files are rejected up front with a `ClickException` before any LLM call.
- Full-plan generation routes to `anthropic/claude-opus-4.7` for heavier strategic reasoning; the `caseplan-assessment` sub-type stays on Sonnet 4.6. The command docstring and user docs are reconciled to match (`model_configs.yaml` is the source of truth).
- The plan system prompt gained a COMMAND OUTPUT FORMAT block (one complete `litassist` command per line, `[MANUAL TASK]` items as prose, no shell control characters) and a note that litassist expands globs itself so patterns need quoting only for paths with spaces. Nested `@timed` decorators on the plan/assessment worker functions were removed (the command-level timer already covers them).

#### May 2026: `caseplan` budget assessment body moved off console; banner kept on both surfaces
- `litassist caseplan` (without `--budget`) no longer echoes the assessment **body** to the console — only the `BUDGET RECOMMENDATION` banner remains there, plus the `Saved to` pointer and the next-step tip. The same banner is now prepended (and a closing divider appended) around the assessment body in the saved file so the on-disk recommendation has a self-describing header section above the LLM body. No other commands had the dump-after-save anti-pattern (verified by sweep). Banner divider width is 60 characters, matching the prior on-screen header.

#### May 2026: lookup `--context` split; new `--guidance` flag for LLM-only case narrative
- `litassist lookup` now has two distinct flags where it previously had one. `--context` keeps its name but is narrowed to the short search-side hint: it is concatenated to the Google CSE query under `--comprehensive` (`question + " " + context` at `search.py:142`) and rendered as a `=== SEARCH CONTEXT ===` block in the LLM analysis prompt. The new `--guidance` flag carries the long LLM-only case narrative: it is wrapped in a `=== USER GUIDANCE (NOT facts from sources) ===` block above the analysis prompt and NEVER touches the CSE query. Two distinct prompt templates -- `analysis.lookup.context_prompt` (rewritten for the cold topic-label use case) and the new `analysis.lookup.guidance_prompt` (inherits the old USER GUIDANCE wording) -- give each input its own framing so the LLM sees the semantic distinction the two flags exist to express. The audit log records both as distinct inputs; the saved metadata distinguishes `Context:` and `Guidance:` on separate lines. Caseplan's plan-generator prompt updated to emit BOTH flags on every `lookup` call so generated bash scripts no longer cram case narratives into the CSE query. Backward compat: scripts that pass only `--context` still execute; they get the long string framed under SEARCH CONTEXT in the LLM prompt and concatenated to the CSE query (the recall they suffer today is unchanged by this branch -- only the wrapper wording around the LLM-side block differs). YAML placeholder whitelist updated to accept the new `{guidance}` template variable.

#### May 2026: caseplan plan-generator prompt aligned with the tightened lookup rule
- The capabilities-prompt rule "keep `lookup --context` short, no case narratives" was contradicted by the caseplan plan-generator's own system prompt (`litassist/prompts/caseplan.yaml`), which had a "CASE-SPECIFIC PARAMETERS" block (lines 222-229) telling the LLM "`--context` Must reference specific evidence, dates, parties, legal issues, claims and amounts" with GOOD examples like `--context "analyze the $40000 vehicle purchase by Victor Orlov on 3 June 2023"`. That guidance is correct for `digest`/`brainstorm`/`strategy`/`draft` (which use `--context`/instruction strings as LLM-only steering) but wrong for `lookup --context` (which is concatenated to the CSE search query under `--comprehensive`). Split the rule per-command: case-specific narrative is encouraged for the LLM-only commands; short topical phrase for `lookup --context` and the lookup question. Replaced the keyword-stuffed RESEARCH QUERY CONSTRUCTION examples (lines 241-243) and the Phase 4-8 worked examples (lines 145-151) with focused short queries (target ~60-80 chars) consistent with the new rule. Updated OPPOSING ARGUMENT ANALYSIS examples to make clear which phase uses `lookup` (short) vs `digest --context` (long, case-specific).

#### May 2026: `lookup` query/context guidance tightened in caseplan capabilities prompt
- `litassist/prompts/capabilities.yaml` previously described `lookup --context` as generic "contextual information to focus and guide the analysis" without naming the two paths it actually feeds: the `--comprehensive` CSE query (where context is concatenated verbatim to the search string -- a long context destroys Google match recall) and the LLM analysis prompt (where it is prepended via the `=== USER GUIDANCE ===` template). The caseplan LLM was generating commands with multi-sentence `--context` strings full of party names, invoice numbers, and dollar figures, producing unsearchable CSE queries. New guidance: target ~60 chars / hard ceiling ~150 chars for `--context`, target ~80 chars for the question itself, never embed case-specific facts (names/amounts/dates/IDs) in either, split one giant question into several focused ones. Includes a worked GOOD example and a worked anti-example.

#### May 2026: `caseplan` capabilities prompt reconciled against actual command flags
- `litassist/prompts/capabilities.yaml` (injected into the caseplan LLM as the universe of recommendable commands) was drifting from the actual Click decorators. Every command's option list audited against `@click.option(...)` declarations and corrected. Net changes: dropped stale `--cove` from `counselnotes`, `barbrief`, and `draft` (no such flag exists in code); dropped stale `--verify` from `draft` (auto-runs, not user-flag); added missing `--heavy` to `extractfacts`, `strategy`, and `verify`; added missing `--verify` to `brainstorm`; added missing `--noverify` to `strategy`; added `--reference`, `--cove-reference`, `--heavy` to `verify`; documented unsupported `--verify`/`--noverify` warnings on `lookup` and `digest` (matching the existing pattern for `caseplan`); corrected `test` to drop the stale "OpenAI" mention and clarify OpenRouter as sole gateway; added previously undocumented `verify-cove` and `refresh` commands. The header comment now points at the real consumer (`caseplan/plan_generator.py:57`, not the stale `caseplan.py:200`).
#### May 2026: `litassist test` cleanup
- Removed Jina Reader API probe from `litassist test`. Jina is a fallback transport used only on Cloudflare challenge bodies, SPA shells, or non-HTML payloads; failures on free-tier `r.jina.ai` were not diagnostic of LitAssist health and the 10-second timeout produced false negatives on healthy systems.
- Migrated OpenRouter auth probe in `validate_credentials` from `/auth/key` to `/key`. Both endpoints currently resolve; `/key` is the canonical name in current OpenRouter API docs and the legacy `/auth/key` alias is retained only for backward compatibility. The probe still only checks `status_code == 200` — its purpose is to confirm the bearer token authenticates, not to surface BYOK status (OpenRouter does not expose BYOK requirements via the API).
- Added BYOK reminder block to `litassist test`. After the OpenRouter auth + catalogue probes, the command now lists each configured model that requires a user-supplied provider key at OpenRouter (currently only `openai/o3-pro`) along with the commands routing to it and a pointer to https://openrouter.ai/settings/integrations. The reminder is silent when no configured model is BYOK-required. The BYOK-required set is hand-maintained in `litassist/cli.py` because OpenRouter does not expose BYOK status programmatically (it appears only on per-model documentation pages).

#### May 2026: RAG / Pinecone pipeline removed; `draft` becomes full-context
- `draft` no longer routes PDFs or large text files into a Pinecone-backed retrieve-then-generate pipeline. Every supplied document is concatenated with section markers and sent to the configured draft model (`openai/o3-pro`) in a single full-context call.
- For documents that exceed the model's context window, `draft` fails with a clear error pointing at `litassist digest --mode summary <file>`. Use the resulting summary as input to draft.
- Removed: `--diversity` flag on `draft`; `litassist/commands/draft/rag_pipeline.py`; `litassist.helpers.pinecone_config` and `litassist.helpers.retriever`; the `helpers` package; `create_embeddings` helper in `litassist/utils/text_processing.py`.
- Removed configuration: `pinecone.*` block, `openai.embedding_model`, and `general.rag_max_chars`. (The full `openai:` block has since been dropped as well — see entry above; BYOK for `openai/o3-pro` is now configured at OpenRouter.)
- Removed dependency: `pinecone-client==2.2.4`.
- `litassist test` no longer checks Pinecone connectivity.
- Prompts updated: `--diversity` references and Pinecone-error templates removed from `capabilities.yaml`, `caseplan.yaml`, and `system_feedback.yaml`.



#### May 2026: Lookup fetcher chain rework (curl_cffi + Cloudflare resilience)
- New transport: `curl_cffi` with Chrome 136 TLS impersonation replaces direct `requests` calls for all content fetching. Defeats Cloudflare's TLS fingerprint detection that newly applied to AustLII; HTML resources now return real content (verified end-to-end). Added as a project dependency.
- AustLII PDF URLs are rewritten to their `.html` siblings before fetch. AustLII's Cloudflare policy on PDF paths is unreachable by any open-source Python client tested (curl_cffi multiple Chrome profiles, Playwright + playwright_stealth, patchright, nodriver, Camoufox — 16+ approaches all returned challenge body). HTML siblings remain reachable; substitution recovers full article text for most journal/case URLs, citation-only stub HTML for some, and 404 for the small set without HTML siblings (notably `legis/bill_em/`). URL parsing uses `urlsplit` to preserve query strings and fragments.
- RTF document support added (`litassist/utils/rtf.py`). Both URL fetches (RTF magic-byte detection) and local file reads (`read_document` extension dispatch) extract text via `striprtf`. AustLII serves some case files as RTF; users may hand in local RTF documents.
- Per-domain fetcher branching collapsed into a single generic chain: local file → jade.io skip / ndfv.jade.io Jina → AustLII PDF→HTML rewrite → AustLII rate limit → curl_cffi GET → PDF/RTF magic bytes → Content-Type guard → legislation.gov.au ToC follow → BS4 text extract → challenge/SPA-shell/gibberish detection → Jina fallback.
- SPA-shell detector (`_looks_like_spa_shell`) catches single-page-application envelopes via known framework markers (`<app-root>`, `id="root"`, `id="app"`, `id="__next"`, `id="__nuxt"`, `ng-version=`) or a text/HTML ratio threshold. Detected pages fall back to Jina for JS rendering.
- Captcha challenge marker narrowed from bare `"captcha"` substring (which false-positive-flagged fedcourt.gov.au practice-note pages embedding Google reCAPTCHA widgets) to canonical Cloudflare phrasings (`"please complete the captcha"`, `"captcha challenge"`). Real Cloudflare challenges still match via these and other markers.
- Gibberish heuristic loosened: dropped the newline-count condition (`text.count("\n") < 5`) which rejected Nuxt server-pre-rendered pages using Unicode word-joiner separators (e.g. triplezero.vic.gov.au — empirically 78% vocabulary overlap with Jina rendering and all substantive legal phrases present). Kept the length floor (`len(text) < 100`).
- Content-Type guard added after curl_cffi GET: payloads with non-text content types (e.g. `application/javascript`, `application/json`) route to Jina rather than passing through to BS4 as long-garbage text.
- legislation.gov.au ToC-link follow tightened: hostname check via `urlsplit().hostname` (was substring match) prevents attacker URLs containing `legislation.gov.au` in query strings from triggering the follow.
- Audit log fidelity restored: `write_fetch_log_markdown` now renders `http_status`, `content_size`, `rejection_reason`, `cf_mitigated`, `cf_ray`, `rewrite_target` fields that the previous formatter silently dropped. New `_response_audit_fields(response)` helper consolidates capture from curl_cffi response headers. Markdown audit logs can now distinguish real Cloudflare challenges (HTTP 403 + `cf-mitigated: challenge`) from detector false positives (HTTP 200 + no `cf-mitigated`).
- Log filename collision fixed: `save_log` filenames now use microsecond resolution (`%Y%m%d-%H%M%S-%f`) instead of second resolution. Two `save_log` calls within the same wall-clock second previously overwrote each other — specifically biting the curl_cffi-failure → immediate-Jina-fallback path.
- 50-page PDF extraction cap removed; PDFs of any size are now fully extracted, with oversized-prompt handling deferred to the truncation manager at the orchestration layer.
- PDF library consolidated onto `pdfplumber`; `pypdf` dependency removed.
- All 437 unit tests passing.

#### November 2025: Token Limit System Removal
- Removed the global token limit system (use_token_limits flag and automatic 16K output limits)
- Increased input file size limits: brainstorm (50K to 600K), caseplan (50K to 600K), strategy (100K+100K to 600K combined)
- Clarified thinking_effort as a reasoning budget rather than an output limit
- Quality prioritised over cost: models use API defaults for comprehensive outputs
- Deprecation warnings added for old config files
- All 390 tests passing

#### November 2025: Verification System Enhancements & Tooling
- Added `--heavy` flag to the verify command for premium verification using gpt-5-pro
- Added `--noverify` flag to extractfacts, draft, and strategy commands for skipping verification
- Changed default verify-soundness model from gpt-5-pro to claude-opus-4.1 (cost optimisation)
- Fixed `verify_content_if_needed()` to properly respect the verify_flag parameter
- Citation validation improvements with header analysis for PDF content
- PDF search validation with automatic retry logic (up to 3 attempts)
- Anti-injection prompt protection added for all LLM calls
- Raw pre-verification output persistence for audit trail compliance
- All 392 tests passing

#### October 2025: Major Model Upgrade - Three-Tier Strategy Implementation
- **Implemented three-tier model strategy** for optimal accuracy and cost-efficiency:
  - Tier 1: GPT-5 Pro for critical verification (<1% hallucination rate)
  - Tier 2: GPT-5.1 for fast verification (1.4% hallucination rate)
  - Tier 3: Claude Sonnet 4.5 for legal reasoning (state-of-the-art for litigation)
- **Upgraded 20+ commands** to new models based on June-October 2025 releases:
  - Claude Opus 4.1 → Claude Sonnet 4.5 (14 commands, 80% cost reduction)
  - Claude Sonnet 4 → Claude Sonnet 4.5 (6 commands, improved reasoning)
  - New GPT-5 Pro implementation (3 critical verification commands)
  - New GPT-5.1 implementation (2 standard verification commands)
  - Grok 3 → Grok 4 (unorthodox brainstorming upgrade)
- **Expected impact**: 40-50% overall cost reduction while improving quality
- **Key improvements**:
  - Superior legal reasoning: "state of the art on complex litigation tasks"
  - Enhanced accuracy: <1.6% hallucination rate on all verification
  - Extended thinking mode for complex multi-step analysis
  - Preserved old configurations as comments for rollback capability
- All 407 unit tests passing with updated model configurations
- Comprehensive documentation updates across README, user guide, and dev docs

#### Previous Changes
- Removed pattern-based citation validation in favor of online verification only
- Improved verification system with increased token limits
- Standardized CLI flags to use --context across all commands
- Enhanced prompt template system with centralized YAML management

### Fixed

#### May 2026: Packaging and cross-cutting trust/cache/format fixes
- `setup.py` `package_data` now includes `litassist/prompts/*.yaml` and `litassist/llm/*.yaml`; matching `recursive-include` lines added to `MANIFEST.in`. Installed wheels previously omitted these runtime assets and commands failed with missing prompt-key errors.
- `MANIFEST.in` now ships `requirements.txt` in the sdist. The fallback list in `setup.py::read_requirements` is removed (raises with a clear error if the file is missing) so installed packages cannot silently drift from the in-repo dependency manifest.
- `find_packages(exclude=[...])` now excludes `tests`, `tests.*`, `test-scripts`, `test-scripts.*` from distribution builds.
- `requirements-dev.txt` added declaring `numpy` for the manual `test-scripts/test_quality.py` checks (the only consumer; test-scripts are not shipped).
- `lookup/processors.py` source prioritisation now uses the shared `is_trusted_legal_host` helper (parsed hostname) instead of substring matching against link URLs, so attacker URLs containing trusted-host substrings cannot jump the queue.
- `verify_single_citation` no longer caches a negative result when verification raises (network error, CSE quota, parser crash). The previous broad `except Exception: pass` poisoned the cache for the rest of the process; transient failures now return False with a descriptive reason and skip the cache write so the next call retries.
- `lookup/search.py` and `lookup/processors.py` log filenames now include a monotonic sub-second suffix to avoid same-second collisions between snippet/fetch saves.
- Removed eight literal `0x14` (DC4) control characters from `litassist/logging/markdown_writers.py` heading f-strings that corrupted rendered audit log titles.

#### May 2026: Logging, config, and CLI robustness
- `litassist --help` and command discovery now work even when `config.yaml` is missing or broken. The CLI module no longer eagerly calls `load_config()` at import time; config is loaded lazily inside command handlers.
- Tools-fallback LLM call now emits a second audit-log entry recording the actual `fallback_messages` and the fallback marker. The original log only recorded the pre-fallback (tools-bearing) request, so audit trails missed what the model actually received.
- Null or wrong-typed YAML sections (`openrouter:` with no body, scalar where a mapping is expected) now raise `ConfigError` with a clear message naming the offending section, instead of opaque `TypeError`/`AttributeError`.
- `save_command_output` filenames now include a monotonic sub-second component (`time.monotonic_ns() % 1_000_000_000`) appended after the existing second-resolution timestamp. Two saves within the same wall-clock second no longer overwrite each other.
- OpenRouter validation in `validate_credentials` now honours `config.or_base` when probing `/models`, so users pointing at a proxy or mirror don't silently validate against the public endpoint.
- `expand_glob_patterns` callback now rejects literal directory arguments and filters directories out of glob matches. Downstream code reads file contents, so directory paths used to produce confusing errors deep inside the pipeline.
- Citation-validation markdown writer now reads both `enable_online` (the source-of-truth key) and the legacy `online_enabled` so the flag is rendered correctly in audit logs.

#### May 2026: Command-orchestration exit-code and isolation fixes
- Draft RAG pipeline now isolates each run with a per-run Pinecone namespace (`draft-<uuid>`) and namespaced vector IDs. Deterministic IDs (`d1`, `d2`, ...) used to collide across runs and stale vectors from one matter could surface in a different matter's draft. The namespace is deleted in a `finally` block after retrieval (or on retrieval failure) to avoid leaks. `Retriever.retrieve()` accepts an optional `namespace` parameter.
- `verify` command now accumulates per-stage failures and exits non-zero when any user-selected stage raises. Previously each stage was wrapped in a try/except, the error was logged, then the command printed "Verification complete. 0 reports generated." and exited zero — masking failures in CI and downstream scripts.
- `verify-cove` command now exits non-zero when the CoVe pipeline raises. Fallback diagnostic saves still run so audit trails are preserved; the completion message is suppressed on failure.
- `brainstorm --verify` now preserves the original brainstorm content when the verifier response is missing the `## Verified and Corrected Document` header. Previously the original was overwritten with the verifier's freeform text while the user-facing message claimed "using original output". Parse-and-fallback logic is extracted to `_extract_verified_document()`.
- `digest` now exits non-zero and skips the output save when every input file fails to read or chunk. Previously digest still wrote an empty output file and reported "Files processed: 0" with exit zero, masking total failure.

#### May 2026: LLM retry and truncation handling
- `_call_with_streaming_wrap` now copies `filtered_params` per attempt before popping OpenRouter-specific keys into `extra_body`. Retries previously re-entered with the drained outer dict and silently dropped `reasoning`, `verbosity`, and other OpenRouter parameters from the second attempt onward. The retry/final-failure audit logs also now record the unmutated request.
- Responses with `finish_reason == "length"` now raise an explicit truncation error naming the model and completion-token count. They were previously returned as if successful, letting callers act on partial legal drafts/answers without warning.

#### May 2026: Accuracy-critical verification fixes
- User-only LLM calls no longer bypass base Australian-law and anti-injection prompts. Both `_add_base_system_prompts` (system-capable models) and `_merge_system_into_user` (o1/o3 models) now inject base prompts when callers supply no system message. The Chain-of-Verification question step (`verification_chain.py`) previously slipped through this gap.
- Legislation and UK/International citations now require positive source evidence. The `verify_single_citation()` function used to short-circuit to `exists=True` on pattern match alone, letting fabricated references (e.g. "Imaginary Aliens Act 2099 (Cth)", "[2099] UKSC 999") pass as verified. Category tagging is preserved in audit logs via a `_tag()` helper that prefixes the verification reason.
- CoVe verification now uses a structured `VERDICT: PASS|FAIL` line instead of substring-matching "no issues found". Quoted or negated occurrences (e.g. `the answer is not "no issues found"`) used to register as PASS. Missing or malformed VERDICT lines fail closed. Prompt at `verification.yaml::verification.cove.inconsistency_detection` updated to require the structured output.
- Google CSE verification now requires the result link to resolve to a trusted legal host (austlii.edu.au, jade.io, legislation.gov.au, hcourt.gov.au, fedcourt.gov.au, ag.gov.au) AND the citation tokens to appear in title or snippet (not the link, which is attacker-controllable). New `litassist/citation/trust.py` centralises the parsed-hostname check.
- `citation_context.py` URL trust filters switched from substring matching (`.gov.au` in link, `austlii.edu.au` in link) to the shared parsed-hostname helper. Hostnames like `austlii.edu.au.attacker.invalid` are now rejected.
- Note: downstream `verify`/`brainstorm` runs will surface more "unverified" citations under the new existence checks. This is the intended outcome; placeholders should replace any unverifiable references.

#### Previous fixes
- Citation verification no longer flags valid NSW tribunal citations
- Brainstorm command streaming API errors resolved
- Barbrief command progress indicator issues fixed
- Verification system now preserves full document content

### Security
- No security vulnerabilities reported

## [1.0.0] - 2025-01-23

### Added
- Initial release of LitAssist
- Core commands: lookup, digest, brainstorm, extractfacts, strategy, draft, verify
- Australian legal citation support
- Integration with multiple LLM providers (OpenAI, Anthropic, Google, xAI)
- Comprehensive prompt template system
- Document chunking and processing capabilities
- Strategic litigation planning features

### Notes
This is the first stable release of LitAssist, providing AI-powered litigation support specifically designed for Australian legal practitioners.
