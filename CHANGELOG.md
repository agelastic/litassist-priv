# Changelog

Last updated: 14/06/2026

All notable changes to LitAssist will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Historical dated sections preserve the model names that were current when those changes shipped. Current model assignments are defined in `litassist/llm/model_configs.yaml`.

## [Unreleased]

### Added
- `verify --cross-check` (ROADMAP P1-12): a read-only multi-model ensemble stage.
  A fixed three-model panel (Claude Sonnet 4.6 / GPT-5.5 / o3-pro) critiques the
  document independently, then a separate arbiter (Claude Opus 4.7, deliberately
  not a panel member) compares the critiques and emits a structured, fail-closed
  report with `=== AGREEMENT ===` / `=== DISAGREEMENTS ===` (carrying a
  machine-readable `DISAGREEMENT LEVEL: NONE|LOW|MEDIUM|HIGH` line) / `=== FLAGGED
  FOR HUMAN REVIEW ===` / `=== CONFIDENCE ===` sections. HIGH disagreement warns
  but does not fail the command; a malformed arbiter report is a stage error
  (non-zero exit). Each LLM call prints a `[COST]` banner. The stage never rewrites
  the document and always reviews the original as-read content. New
  `litassist/commands/verify/ensemble.py`, four `crosscheck-*` model roles,
  `verification.crosscheck.*` prompts. Composes additively with the three core
  checks and `--cove`; unaffected by `--heavy`. **Measurement gate PASSED
  (14/06/2026):** on 4 seeded-defect benchmark variants (20 defects) the
  cross-check caught 20/20, including 6 that baseline `verify` missed - all the
  fabricated-fact defects (0/4 baseline) and the contradictions baseline missed -
  with 0 spurious HIGH flags on clean documents at 2.6x marginal / 3.6x total cost
  (criterion is marginal <= 4x). Now surfaced to caseplan. Evidence:
  `test-scripts/judge_eval/crosscheck_gate/RESULTS.md`.
- Actual per-call cost from OpenRouter. Every LLM request now sets
  `usage: {include: true}`, so the response carries OpenRouter's real billed
  `cost` and a generation `id`; both are captured in `response_parser`, summed
  across all internal billed SDK calls (tool-fallback follow-up / retries, which
  were previously uncounted) via `litassist/llm/usage.py:merge_usage`, returned in
  the usage dict, and written to the audit log. The `[COST]` banner now prints
  OpenRouter's actual cost (`cost_message` helper). Replaces local price-table
  estimation: `litassist/llm/cost.py:estimate_call_cost` (which undercounted vs the
  OpenRouter invoice) is removed. Capability price fields stay for non-cost uses.
- P-JUDGE offline eval harness (`test-scripts/test_judge_eval.py`): repeatable,
  real-API quality scoring of litassist outputs against a rubric (citation
  grounding, structure, Australian English, faithfulness, AGLC format), with a
  fail-closed structured-output contract, baseline regression comparison
  (tolerance 8), and a retrieval-gap report that caps `citation_grounding` by
  the fraction of expected citations verifiable from sources. New `judge-eval`
  model role, `litassist/prompts/judge_eval.yaml` prompts, a 4-case benchmark
  generated from a fictional NSW negligence matter (extractfacts, lookup IRAC,
  strategy, draft), offline unit tests for the scoring core, and
  `docs/development/JUDGE_EVAL.md`. ROADMAP P-JUDGE; the ensemble items
  (P1-12, P2-19) stay gated on deltas measured with this harness.
- `LICENSE` file (MIT). The project licence is now stated consistently: `setup.py`
  classifier changed from `License :: Other/Proprietary License` to
  `License :: OSI Approved :: MIT License` (plus a `license="MIT"` kwarg), and README
  gained a Licence section. Resolves the licensing inconsistency deferred from v3.0.0.
- Matter-type-aware prompts (Phase 1). `case_facts` now carries a `Matter type:` line
  under the Jurisdiction heading (proposed by `extractfacts`, preserved by `updatefacts`).
  The framing commands (`barbrief`, `strategy`, `brainstorm`, `caseplan`) read it and prepend
  a matter-type "posture" (forum / document archetype / process / remedies / what-to-avoid)
  to their system prompt, so a regulatory/disciplinary complaint, FOI matter, criminal,
  family, etc. is framed for the right forum instead of defaulting to court litigation.
  New `litassist/prompts/matter_types.yaml` holds one posture per type
  (civil/criminal/family/commercial/disciplinary/foi/administrative). `counselnotes` (which
  takes arbitrary files, not `case_facts`) gains an optional `--matter-type` flag;
  `brainstorm --side` gains `complainant`. When the line is absent/unknown the commands
  assume `civil` and warn - existing matters are unaffected (no hard gate). Motivated by the
  complaints tool-assessment.

### Fixed
- Jina Reader is no longer dispatched to austlii.edu.au URLs. AustLII serves
  Jina's datacentre IPs a Cloudflare challenge on every request (verified
  26/05/2026, reconfirmed 11/06/2026), so each dispatch was a guaranteed-
  failed paid call caught by the challenge detector. The fetcher now fails
  fast with an audit-log entry instead.
- Whole-act legislation citations (e.g. "Civil Liability Act 2002 (NSW)") are
  now retrievable by `fetch_citation_context` when CSE surfaces the act-root
  page. Two jurisdiction-blind spots fixed together: the AustLII CSE link
  filter accepted any /au/legis/ link (the WA Civil Liability Act and a
  Regulation were fetched for an NSW Act citation), and no validation
  strategy could pass on the correct page, whose header carries the bare
  title plus jurisdiction prose ("New South Wales Consolidated Acts") rather
  than the "(NSW)" literal. The link filter is now scoped to the citation's
  jurisdiction subtree and a legislation-aware validation strategy matches
  title-plus-jurisdiction in the header; a right-title/wrong-jurisdiction
  page still fails, and an arbitrary SECT/REG/RULE/SCHEDULE component page
  is refused for a whole-act citation rather than overstating retrieval.
  Found by the P-JUDGE retrieval-tag measurement.
- `construct_austlii_url` now accepts citations that carry their case name
  (e.g. "Fallas v Mourlas [2006] NSWCA 32" - the form every command output
  uses). The parser was anchored to the start of the string, so the direct
  AustLII fallback in `fetch_citation_context` silently never ran for named
  neutral citations; CSE then surfaced documents that merely cite the target
  and validation correctly rejected them. Found by the P-JUDGE retrieval-tag
  measurement (all four NSWCA fetch failures traced to this line).
- `strategy`/`barbrief` no longer reject `extractfacts` headings that carry parenthetical
  qualifiers (e.g. "Key Events (Chronological)"); the 10-heading validator tolerates them.
- `lookup` and `digest` prompts now instruct the model to verify statutory section numbers
  against the supplied sources (and flag unverified ones), reducing definitional-section drift.
- `brainstorm` no longer fabricates strategies when a model returns no `### Strategy N:`
  headers (e.g. a refusal). The blank-line fallback that silently split a refusal into up to
  15 "strategies" is removed; a lane that yields zero parseable strategies now prints a loud
  warning showing the model's response prefix and reports an honest count of 0, and the
  citation-verification stage logs the real strategy count instead of a hardcoded "30".
- `brainstorm` unorthodox prompt reworded toward creative-but-lawful framing (dropping the
  "fabricate 15 boundary-pushing / disruptive / forum-shopping" language) to reduce model
  refusals on regulatory/complaint matters.
- `brainstorm-unorthodox` model changed from `x-ai/grok-4.20` to `x-ai/grok-4.3`. An eval
  (`test-scripts/test_unorthodox_models.py`) showed grok-4.20 still refused ~2/3 of trials on
  the disciplinary/complaint framing even with the reworded prompt, while grok-4.3 produced 15
  parseable strategies in 3/3 trials. Sampling parameters unchanged (same xAI family).
- `strategy` "Total tokens used" (and the audit log) now aggregate the options, next-steps and
  draft generation calls; previously only the options call was counted, under-reporting cost by
  roughly two-thirds. (The verification-stage call's usage is not yet returned by `verify()` and
  remains a documented residual.)

## [3.0.0] - 2026-06-04

Major release. Breaking changes (see end of this section). 298 commits since v2.0.0.

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
- Direct OpenAI configuration removed. `config.yaml` no longer carries an `openai:` block; the project routes every LLM call through OpenRouter using `openrouter.api_key`. Provider-level BYOK for models like `openai/o3-pro` is configured at <https://openrouter.ai/settings/integrations>, not in this project's config.
- Stale model references cleaned up across docs and prompts. `litassist/prompts/system_feedback.yaml` dropped its dead `api:` subsection (`key_placeholder`, `byok_required_o1_pro`, `byok_required_o3` — none of which had any consumer in code). `litassist/README.md` example updated from `anthropic/claude-3-sonnet` to `anthropic/claude-sonnet-4.6`. `litassist/commands/digest/chunker.py` openai chunk-limit comment retargeted from `GPT-4/o3's 400k context` to the actual active models. `docs/development/LLM_MODEL_STRATEGY.md` ensemble example fixed from non-existent `x-ai/grok-4.20-turbo` to `x-ai/grok-4.20`. `docs/development/adversarial_modelling.md` Model Landscape section gained a design-time caveat clarifying that specific version pins (Claude Opus 4.6, Gemini 2.5, Grok 4.1 Fast) need re-validation against `model_configs.yaml` at implementation time.
- Parameter-translation infrastructure in `litassist/llm/model_profiles.py` is explicitly NOT narrowed. A header comment encodes the policy: the classifier tables must cover any OpenRouter model the user might swap into `model_configs.yaml`, not just the currently-active set.
- `LLMClientFactory.get_context_window_for_command()` lookup helper backed by the new capability file.
- `draft` preflight oversize handling: soft warn + hard fail derived from the model's actual context window plus a provider-error reframe pointing users at `litassist digest --mode summary <file>`.

### Changed

#### June 2026: removed dead `verify_with_level` verification path
- Removed the unused `verify_with_level` method (no production callers). The boolean `--heavy` flag already provides two-tier (standard/heavy) verification via `run_verification_chain`. Also removed its now-orphaned prompts (`light_verification`, `heavy_verification`, `heavy_verification_system`) and the orphaned `verification-light` model config, and updated the verification docs accordingly.

#### June 2026: input budget is 80% of the routed model's window; counselnotes consolidates chunks
- `LLMClientFactory.get_input_budget_for_command` now offers 80% of each routed model's context window to input (was 30%). The budget already reads the per-model window from `model_capabilities.yaml`, so commands use far more of their window before chunking or rejecting input (e.g. `counselnotes` on a 200k-window model now runs typical multi-document inputs in a single unified pass instead of splitting into three). `1 - fraction` is the worst-case reserve for system prompt + reasoning + completion; 0.80 leaves comfortable headroom on every routed model.
- `brainstorm` now sizes its case-facts cap against its **analysis** stage (the smallest-window model in the pipeline, which receives facts + orthodox + unorthodox), not the orthodox-generation model. Previously the cap was computed against a larger-window model, so it could not protect the narrowest stage.
- `counselnotes --extract` now consolidates multi-chunk extractions with a single LLM reduce (preserving and merging the per-mode section headings) instead of concatenating the partials. The reduce runs only when the input was actually chunked; a single unified extraction is returned as-is.

#### June 2026: command outputs are Markdown (.md); caseplan runner is .py
- All command outputs now save with a `.md` extension instead of `.txt` (they have always been Markdown-formatted prose). `save_command_output` gained an `extension` parameter (default `.md`); the caseplan executable runner passes `extension=".py"` so it is saved as a real Python file (`caseplan_commands_*.py`, run with `python <file>`). The canonical case-facts file is now `case_facts.md`: `updatefacts` writes the stable `case_facts.md` and the caseplan runner seeds/copies the baseline as `case_facts.md`. `resolve_case_facts_file()` globs BOTH `case_facts*.md` and legacy `case_facts*.txt`, so existing `.txt` case-facts folders keep auto-resolving (newest still wins by the same recency rule). The caseplan and capabilities prompts, all command help text, and the user/developer docs now reference `outputs/*.md` and `case_facts.md`. Source-document inputs are unchanged - litassist still reads `.pdf`, `.rtf`, `.txt`, and `.md`. Supersedes the `.txt` output/case-facts filenames shown in the earlier Unreleased entries below.

#### June 2026: caseplan sends the real source-file inventory to the planner
- The caseplan prompt previously sent case facts + budget + context but NO list of the documents actually present, so the model invented source-document filenames (e.g. `bank_statements.pdf`) and the generated runner then failed at `extractfacts`/`digest` on files that do not exist. caseplan now discovers the source documents in the working directory (top-level `pdf/rtf/txt` - the formats litassist can read; Word `.doc/.docx` are not listed - excluding `case_facts*.txt`), lists them for the user, and injects an `AVAILABLE SOURCE FILES` block into the prompt instructing the model to use those EXACT names, target the specific files each step needs by role (not blanket-glob unrelated documents), and mark `[MANUAL TASK]` for any needed-but-absent document. When run interactively, caseplan shows the inventory and asks to confirm before the paid full-plan call (`--yes`/`-y` skips the prompt; non-interactive runs proceed). Fully local - no file contents are read and no extra LLM call. The chosen file list is recorded in the caseplan audit log.

#### June 2026: caseplan emits a Python runner that isolates each execution
- A caseplan-generated script accumulates outputs into the shared, never-cleaned `outputs/` folder, so a glob like `outputs/brainstorm_creative_*.txt` could match files from a PREVIOUS run (and a re-run silently mixed with the prior attempt). caseplan now generates a **Python** runner instead of a bash script (`command_extractor.py`). When executed, the runner creates a fresh `outputs/run_<YYYYMMDD_HHMMSS_microseconds>/` directory, sets `LITASSIST_OUTPUT_DIR` (inherited by every `subprocess.run(args, shell=False)` step), and rewrites every `outputs/...` and `case_facts` argument to `os.path.join(run_dir, ...)`. So each EXECUTION is fully isolated - outputs AND case_facts live in the run dir, retries never mix, and there is no shell-injection surface. `save_command_output` honours `LITASSIST_OUTPUT_DIR` when no explicit dir is given (the single output sink), `updatefacts` and `resolve_case_facts_file` honour it for case_facts, and a supplied cwd `case_facts*.txt` is copied in as a seed (the cwd original is never mutated). All hooks are env-gated, so normal single-command use is unchanged. This replaces the earlier per-generation `RUNID` sentinel approach. A new `include_header=False` on `save_command_output` writes the runner verbatim so it stays executable Python.

#### June 2026: strategy `--strategies` accepts MULTIPLE brainstorm sets
- The caseplan dual-brainstorm design produces two files - a creative set (`brainstorm_creative_*`) and a research set (`brainstorm_research_*`) - but `strategy --strategies` was single-valued (`expand_glob_single_callback`), so it silently ingested only the newest match and dropped the other set. `--strategies` is now `multiple=True` (repeatable: one brainstorm set per flag) backed by a new `expand_glob_newest_each_callback` (`litassist/utils/file_ops.py`): each flag resolves INDEPENDENTLY to its own most-recent match (so older same-prefix files from prior runs are ignored), every glob resolution is announced on the console, and the resolved files are de-duplicated. A new `parse_strategies_files` merge helper (`litassist/utils/core.py`) parses each file, SUMS the orthodox/unorthodox/most-likely counts for the on-screen summary, and joins the bodies under the standard `=== filename ===` separator before the combined text goes to the model. The caseplan prompt now emits two `--strategies` flags (creative + research) for each `strategy` step. The scalar `expand_glob_single_callback` is unchanged - `verify`'s single `FILE` arg still uses it.

#### May 2026: strategy `--strategies` and verify `FILE` accept globs (most recent match)
- Caseplan-generated scripts chain step outputs by glob (e.g. `strategy --strategies 'outputs/brainstorm_*.txt'`, `verify 'outputs/draft_*.txt'`), and the user docs already showed those forms, but the two single-input path args crashed on a glob: `--strategies` was a `click.File` and `verify`'s `FILE` was `click.Path(exists=True)`, both resolved at Click's parse stage before any callback could expand the pattern. Both now use a new `expand_glob_single_callback` (`litassist/utils/file_ops.py`): a literal path passes through, a glob resolves to the most recent matching file (by mtime, mirroring `resolve_case_facts_file`), and a zero-match / directory / missing literal fails loudly. When a glob matches more than one file (e.g. `draft` writes a raw and a final file under one prefix) it warns and uses the newest. Multi-input commands (`counselnotes`, `draft`, `barbrief`, `digest`, `brainstorm --research`) are unchanged - they still take all matches.

#### May 2026: caseplan emits unique `--output` prefixes and one verify per deliverable
- The caseplan prompt (`caseplan.yaml` plus the injected `capabilities.yaml`) now tells the model to give same-type producers distinct, command-name-prefixed `--output` names (`brainstorm_creative` / `brainstorm_research`, `draft_memo` / `draft_summary`) and to reference the specific prefix downstream, and to run `verify` once per finished deliverable rather than a single `verify 'outputs/draft_*.txt'` (which resolves to only the most recent draft). The false blanket "litassist expands all globs" line and the impossible concrete-timestamp `--strategies` example were corrected to the actual per-arg glob behaviour. This makes generated scripts chain correctly given the accumulating, never-cleaned `outputs/` folder.

#### May 2026: dropped the no-op `--verify` flag from extractfacts and strategy
- `extractfacts` and `strategy` ran verification unconditionally (the call site hard-coded `verify_flag=True`), so their `--verify` flag did nothing but print a "verification already active" reminder. The flag is removed from both commands. Verification remains auto-enabled; use `--noverify` to skip it. `draft` already followed this pattern. The functional `--verify` on `brainstorm`, `counselnotes`, and `barbrief` (which genuinely toggles citation/content verification) is unchanged, as is the unsupported-flag guard on `lookup`, `digest`, and `caseplan`.

#### May 2026: extractfacts points to updatefacts instead of manual copy
- `extractfacts` no longer ends with "manually copy to case_facts.txt". Its completion message now names the next step explicitly: `litassist updatefacts <the saved file>`, which folds the extraction into an auto-discoverable `case_facts` file. No behaviour change beyond the message.

#### May 2026: verification short-circuits are now announced
- `run_verification_chain` (`litassist/verification_chain.py`) bails before the expensive LLM verification stage when the offline citation-pattern check, or the citation-database check, finds problems (for `extractfacts`/`strategy`; pattern issues also short-circuit `draft`). Previously this was silent and the command still reported "verification applied". The chain now records a `short_circuit` reason in its results and prints a warning, so the user knows the content was only pattern/citation-checked, not fully verified. `extractfacts` additionally reports whether verification actually made corrections ("corrections applied" vs "no corrections") in its output metadata.

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
- Added BYOK reminder block to `litassist test`. After the OpenRouter auth + catalogue probes, the command now lists each configured model that requires a user-supplied provider key at OpenRouter (currently only `openai/o3-pro`) along with the commands routing to it and a pointer to <https://openrouter.ai/settings/integrations>. The reminder is silent when no configured model is BYOK-required. The BYOK-required set is hand-maintained in `litassist/cli.py` because OpenRouter does not expose BYOK status programmatically (it appears only on per-model documentation pages).

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

### Fixed

#### June 2026: brainstorm/strategy pipeline fixes
- `strategy` no longer fails with HTTP 400 `reasoning.effort: Invalid option`. Its
  `thinking_effort: "max"` on `anthropic/claude-opus-4.7` was mapped to
  `reasoning.effort: "max"`, but OpenRouter's effort enum has no `max` tier (ceiling
  is `xhigh`); `convert_thinking_effort` now maps `max -> xhigh` for the Opus 4.7/4.8
  family, matching the GPT-5.5 branch.
- `brainstorm`/`strategy` "most likely to succeed" count is no longer always 0. The
  analysis prompt formats each entry as `**N. Title**` (bold) but
  `parse_strategies_file` counted `^\d+\.`; the most-likely regex now also matches
  the bold-numbered form.
- `brainstorm --verify` and `verify` now tolerate light formatting of the
  `## Verified and Corrected Document` header (bold, `&`, case, `###`, trailing
  colon) instead of discarding the verifier's corrections. The parse-and-fallback
  logic is now a single shared `extract_verified_document()` in `utils/core.py` used
  by both commands (it was duplicated, which let the two copies drift).

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

### Security
- No security vulnerabilities reported

### Breaking Changes
- RAG/Pinecone pipeline removed: `draft` is now a single full-context call (no retrieve-then-generate); oversize inputs fail with a `digest --mode summary <file>` pointer instead of being retrieved.
- `draft --diversity` flag removed.
- Config keys removed (existing `config.yaml` must be updated): the entire `pinecone.*` block, the `openai:` block (`openai.api_key`, `openai.embedding_model`), `general.rag_max_chars`, and `llm.use_token_limits` / `llm.token_limit`.
- Dependency `pinecone-client==2.2.4` removed; `litassist test` no longer probes Pinecone.
- No-op `--verify` flag removed from `extractfacts` and `strategy` (verification stays auto-enabled; use `--noverify` to skip).
- Default command output extension changed from `.txt` to `.md`; canonical case-facts file is now `case_facts.md` (legacy `case_facts*.txt` still auto-resolves on read).
- Direct OpenAI configuration removed; all LLM calls route through OpenRouter (provider BYOK for models like `openai/o3-pro` is configured at OpenRouter).

### Upgrading from v2.0.0
- Edit `config.yaml`: delete the `pinecone.*` and `openai:` blocks, `general.rag_max_chars`, and `llm.use_token_limits`/`llm.token_limit`.
- Remove any use of `draft --diversity` and the no-op `--verify` on `extractfacts`/`strategy` (use `--noverify` to skip verification).
- For oversize `draft` inputs, pre-summarise with `litassist digest --mode summary <file>`.
- Configure provider BYOK (e.g. `openai/o3-pro`) at OpenRouter, not in this project's config.
- Scripts that hardcode `.txt` output names: outputs are now `.md` (reading legacy `.txt` case-facts still works).

## [2.0.0] - 2025-10-26

> Backfilled 2026-06-04: v2.0.0 was originally a lightweight git tag (placed on an unrelated commit) and never received a CHANGELOG entry. The items below are reconstructed from the changes that shipped between v1.0.0 and the v2.0.0 tag.

### Changed

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

#### Previous fixes
- Citation verification no longer flags valid NSW tribunal citations
- Brainstorm command streaming API errors resolved
- Barbrief command progress indicator issues fixed
- Verification system now preserves full document content

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
