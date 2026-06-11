# LitAssist Development TODO

Last updated: 11/06/2026

**Note:** Strategic feature planning (litigation support, advisory capabilities, new commands) is now in [ROADMAP.md](ROADMAP.md). This file focuses on bugs, technical debt, and code quality improvements.

**Active thrust (09/06/2026 - approved plan; goal: trustworthy output):** Phase 2
Model Quality & Research, **re-sequenced measurement-first**. **P-JUDGE SHIPPED
11/06/2026** on branch `feat/judge-eval-harness` (`test-scripts/test_judge_eval.py`,
`litassist/prompts/judge_eval.yaml`, `judge-eval` config, 4-case Harper benchmark +
baseline; see `docs/development/JUDGE_EVAL.md`). Next: P1-12 cross-checks shipped
**only if** P-JUDGE measures lift > cost, then P2-19 divergence (thin add).
De-risk track done: CSE->Vertex scoping validated 10/06/2026 (below) and licensing
resolved as MIT 10/06/2026. P-JUDGE's benchmark seeds the un-fetchable citation
classes (authorised-report CLR-only cites, a confabulated citation, overseas
reports) so the retrieval gap caps the grounding score instead of hiding - see
the C1/C2 items below. Full re-sequence rationale in ROADMAP Phase 2 + Next Steps.

**Prior (08/06/2026):** Matter-type-aware prompts Phase 1 (feature branch `feat/matter-type-prompts`) - the scoped fix from the complaints assessment. See ROADMAP **P-MTYPE**. Also fixes two assessment bugs: the `extractfacts`->`strategy`/`barbrief` heading-validation mismatch (parenthetical qualifiers) and lookup/digest definitional-section citation drift. Phase 2 (hard gate, Matter Memory wiring) deferred pending observation.

**Sources of truth:** command registration lives in `litassist/commands/__init__.py`; current model assignments live in `litassist/llm/model_configs.yaml`; strategic feature planning lives in `ROADMAP.md`.

---

## Pending Tasks [IN PROGRESS]
- [x] **[RESOLVED 07/06/2026] Assess how current tools handle complaints (overhaul vs usable-interim):** **Verdict: keep complaints on current commands** - see [docs/development/claude_complaints_tool_assessment.md](docs/development/claude_complaints_tool_assessment.md). Ran a real combined fee+conduct OLSC matter (Osipov v Dowson Turco, CAS022856) end-to-end through the pipeline and scored each output against the Commissioner's actual determination (complaint closed, no finding). 9 of 11 outputs landed at a/b; the two c's (counselnotes, barbrief) share one court-default framing gap fixed by a scoped enum/prompt tweak, NOT the P2-15 subsystem. Surfaced two real bugs: extractfacts->strategy/barbrief heading-validation mismatch, and recurring LPUL definitional-section citation drift. ROADMAP Phase 4 / P2-15 stays dormant. Original brief: Run this FIRST - in parallel with the Phase 1 foundation work, not after it (it has no build dependency; it only exercises existing commands). It is ROADMAP Build Sequence step 0, and Phase 4 stays dormant/gated on its finding. Before any dedicated complaint tooling is built, evaluate whether the existing commands (extractfacts, brainstorm, strategy, draft, counselnotes, barbrief, verify) already produce usable output for professional-oversight complaints (QLSC/OLSC/ACT Bar). Method: run a representative real complaint scenario end-to-end through the current pipeline and judge against three outcomes - (a) usable as-is for now, (b) usable with prompt/template tweaks only (cheap, scope them), or (c) needs a major overhaul / a dedicated `complaint` command. Deliverable: a short go/no-go that either keeps complaints handled by current commands or unblocks ROADMAP P2-15 with a concrete scope. Until this reports, complaints are handled with the current commands.
- [x] **[RESOLVED 10/06/2026] Licensing reconciliation [DE-RISK TRACK - Inc 0b]:** user chose **MIT**. Added `LICENSE` (MIT, copyright 2026 Vitaly Osipov), switched `setup.py` classifier to `License :: OSI Approved :: MIT License` + `license="MIT"` kwarg, added a Licence section to README. Original brief: the repo was inconsistent/unstated - `setup.py` declared proprietary but there was no LICENSE file and no licence prose in README; deferred from the v3.0.0 release (04/06/2026).
- [ ] **GitHub Pages decision + stale URLs:** no GitHub Pages site exists (Pages API 404, no `gh-pages` branch, no `mkdocs.yml`/`_config.yml`/`CNAME`, no Pages workflow). Decide whether to publish the `docs/` tree as a Pages site. Regardless of that decision, the stale placeholder/branch URLs were corrected in the v3.0.0 release-tooling fix - `.github/workflows/release.yml` (`/blob/main/` -> `/blob/master/`), `scripts/release/finalize-release.sh` (`YOUR-ORG`/`main` -> `agelastic/litassist-priv`/`master`), and `RELEASE_PROCESS.md` (`main` -> `master`); confirm no other docs still link to a non-existent Pages site or the wrong branch.
- [ ] Implement circuit‑breaker (`safety_cutoff`) in retry logic [AG-124] - OPTIONAL enhancement (has 5-retry limit)
- [ ] AUDIT: verification coverage (mapping done June 2026; two decisions remain). Confirmed against source: verifies BY DEFAULT (draft, strategy, extractfacts, with `--noverify` opt-out); OPT-IN via `--verify` (brainstorm, counselnotes, barbrief); NO verification (lookup, digest, updatefacts; caseplan and verify-cove are separate). Open items: (1) the caseplan prompt does NOT yet force `--verify` on opt-in commands that emit court documents, except barbrief (done May 2026) - extend it to the others; (2) decide whether strategy's auto-verified court doc (`outputs/strategy_draft_*.md`) also warrants a standalone post-hoc `verify`.
- [ ] Enhance QA loops: iterative improvement, contingency planning, multi-perspective reviews (partial: verify-cove + brainstorm regeneration exist; contingency/multi-perspective absent)
- [ ] Automate performance benchmarking and monitoring setup [MON]
- [ ] Implement OpenAI API fine-tuning per platform recommendations
- [ ] Add LLM response streaming functionality
- [ ] **Complete token & cost accounting + in/out surfacing [PLANNED - see ROADMAP P-TOK]:** per-call usage IS logged by `LLMClient.complete()` (audit trail complete, including output/completion tokens), but command-level totals are inconsistent. Only `strategy`/`barbrief`/`counselnotes`/`digest` print a user-facing total; `lookup`/`draft`/`extractfacts`/`updatefacts`/`caseplan`/`verify`/`verify-cove` print none; output tokens are never surfaced separately anywhere; and several rollups drop secondary-call usage - `brainstorm` plausibility (`core.py:200`) + regeneration (`citation_regenerator.py:115`) + `--verify`, `verify` reasoning stage (`reasoning_handler.py:158`), `updatefacts` (`core.py:159`) - while `verify()` (`llm/verification.py:95`) drops usage on return so every verification call's tokens are uncounted at command level. Plan: shared `litassist/llm/usage.py` (`merge_usage` + `format_token_usage` -> "N (in: X, out: Y)"); change `verify()` to also return usage (4 real callers: `verification_chain.py:88`, `brainstorm/core.py:697`, `verify/soundness_checker.py:108`, `legal_reasoning.py:308`); capture the dropped usages; add a consistent "Total tokens used: N (in: X, out: Y)" line to every command. Ties into Pricing-aware features (Next Steps #4); closes the strategy verification-stage residual.
- [ ] Expose model configuration parameters via CLI/env vars
- [ ] Develop "student mode" with newcomer-friendly explanations
- [ ] **Add optional reasoning trace file output**: CORRECTION (June 2026): strategy and verify already write reasoning traces to separate timestamped files by default (`litassist/commands/strategy/file_handler.py`, `litassist/commands/verify/reasoning_handler.py`); the premise "embedded in main output only" was stale. Residual scope is narrow - an opt-in `--save-reasoning` file for commands that do NOT already emit one (notably draft). Re-confirm need before building; may be useful for professional-liability audit trails.
- [ ] **Migrate off Google Custom Search JSON API by 01/01/2027 [DE-RISK TRACK - Inc 0a scoping DONE 10/06/2026]**: scoping pass complete - `docs/development/GOOGLE_CSE_MIGRATION_PLAN.md` is now a validated design with concrete, test-gated cutover steps (two spike-time risks remain open: the `*.gov.au/*` public-suffix pattern and Jade snippet parity). Key findings: website search needs Vertex **Enterprise edition** (USD 4/1,000 queries, 10k/month free vs CSE's 100/day); the **`searchLite`** method accepts a plain API key (built for CSE migrants - keeps the current config.yaml API-key model, no service-account plumbing); basic website data stores are global-only, need no domain verification, 50-pattern limit (our CSEs use 1/1/6); whether `*.gov.au/*` works over a public suffix is undocumented and must be spike-tested. **Next action is on the user (billable GCP setup):** enable `discoveryengine.googleapis.com`, accept Enterprise billing, create the Jade data store + app, mint an API key - then the one-query spike + citation-regression parity check is <1h. Remaining work tracked in the doc's Cutover steps; build by Q3-Q4 2026.
- [ ] **[SOON] Implement jade.io cookie-reuse fetch via Jina**: Replace the jade.io skip in `litassist/commands/lookup/fetchers.py:548-572` with a cookie-authenticated Jina fetch. jade.io article pages are SPA-rendered behind passwordless email magic-link auth; direct/Jina fetches without auth currently return only login chrome (no judgment text). Approach: (1) user logs in manually in a browser once, (2) copies session cookies from DevTools (`JSESSIONID`, `IID`, any post-login auth cookies), (3) stores them in config (e.g. `JADE_COOKIES` env var or `config.yaml`), (4) lookup forwards the `Cookie:` header to Jina's `r.jina.ai` API so rendering happens as the authenticated user. Add a `_looks_like_jade_login_wall` detector matching strings like "Check your email", "sign-in link", "Use verification code", "Register for free" — fires when cookies have expired and logs a clear "refresh JADE_COOKIES" warning. Implementer note: verify that Jina's r.jina.ai API forwards arbitrary `Cookie:` headers to the target site (their docs cover header passthrough); if not, use curl_cffi + manual JS rendering or fall back to skipping. See conversation 26/05/2026 for empirical findings: curl_cffi defeats Cloudflare on jade.io (HTTP 200, 15KB shell) but content is auth-gated; Jina renders the page but only sees login chrome without cookies.
- [ ] **Evaluate removing Jina from the lookup fetcher chain** *(update 11/06/2026: `_fetch_via_jina` now short-circuits for austlii.edu.au hosts - always Cloudflare-challenged - shrinking Jina's effective call surface further; factor this into the success-rate query below)*: After the 26/05/2026 fetcher work (captcha-marker fix, gibberish-heuristic loosening, AustLII PDF -> HTML substitution, fedcourt unblocked), Jina's production usage has shrunk to a narrow set: (1) `ndfv.jade.io` URLs (forced routing in `_fetch_url_content`), (2) HTTP 4xx/5xx fallback from curl_cffi (rare), (3) extraction < 100 chars (rare after the gibberish-check loosening). The jade.io cookie-reuse [SOON] entry above currently assumes Jina is the transport; if that work is reshaped to use curl_cffi directly with Cookie headers (avoiding Jina's IP class which is itself Cloudflare-challenged on many AU government sites), Jina would have no callers left. Decision criteria: after 1-2 weeks of production usage with the current chain, query the audit logs for `method=jina_reader` entries and count successes vs failures. If `successes / total < 5%` and no critical case relies on Jina alone, remove. Removal would: (a) drop the jina_api_key config field, (b) delete `_fetch_via_jina` and its tests, (c) replace the ndfv.jade.io routing with curl_cffi + skip (per the same logic as the jade.io main domain skip already in place), (d) collapse the gibberish fallback to "return empty content" instead of attempting Jina. Verified 26/05/2026: jina_api_key in config is valid and works (probe to fairwork.gov.au returned 64KB markdown); the question is not whether Jina works mechanically but whether it actually adds coverage that curl_cffi misses. See conversation 26/05/2026 for the empirical analysis (78% Jaccard similarity between curl_cffi and Jina renderings of triplezero.vic.gov.au showed Jina was adding navigation chrome, not legal content). Order this AFTER the jade.io cookie-reuse work since that may itself remove the last forced Jina path.
- [ ] **Known limitation: AustLII PDF paths are Cloudflare-blocked**: AustLII serves PDFs behind a strict Cloudflare policy that returns "Just a moment..." challenge body (HTTP 403, `cf-mitigated: challenge`) to every Python transport tested on 26/05/2026: requests with Chrome 91/136 UAs, curl_cffi with chrome116/120/131/136 profiles, curl_cffi with HTML-warmup cookies + Referer, Jina (datacentre IPs also challenged), Playwright vanilla, Playwright + playwright_stealth (16 attempts with fresh-context-per-fetch, multiple PDFs), patchright (CDP-leak-patched Chrome 148), nodriver (custom CDP transport), and Camoufox (custom Firefox with C++ stealth patches). The user's own real Chrome browser also shows the Cloudflare banner. The block is server-side and per-URL-extension: HTML siblings at the same paths pass curl_cffi cleanly. Mitigation already implemented (26/05/2026): the fetcher detects `austlii.edu.au` PDF URLs and rewrites to the `.html` sibling before the HTTP fetch (`litassist/commands/lookup/fetchers.py` `_fetch_url_content`). Recovery rates per empirical test: full article HTML (CanterLawRw, MelbULawRw patterns) returns 70-110KB of clean text; stub HTML (VUWLawRw 2016/2020, AukULawRw 1992 patterns) returns ~1KB containing the full Australian citation but no article body; bill_em PDFs have no HTML sibling and 404. If a paid Cloudflare-bypass service (ScrapingBee/ZenRows/Bright Data Web Unlocker) is later judged worth the cost, integrate as a new transport in the chain after curl_cffi but before Jina. Diagnostic scripts that produced this evidence: `/tmp/austlii_diag.py`, `/tmp/playwright_test*.py`, `/tmp/stealth_compare.py`, `/tmp/camoufox_test.py` (regenerate from the 26/05/2026 conversation if needed).

## Critical Bugs to Fix [HIGH PRIORITY]

### Citation content retrieval: authorised-report citations [FOLLOW-UP]
Verified-real authorised-report citations (e.g. `(1999) 201 CLR 1`) fail the
post-fetch content retrieval in `fetch_citation_context` (`litassist/citation_context.py`),
so `verify --soundness`/`--reasoning` run with no document context for them
(soundness effectively runs blind on those citations). The misleading failure
reason was fixed (`_search_and_validate` now preserves the fetched URL so the
reason reads "Document fetch or content validation failed" instead of "URL not
found - CSE returned no results"). Making these citations actually retrievable is
deferred:
- **C1 (retrieval) - downgraded, not a standalone fix.** Landing on the AustLII
  case page (whose header carries parallel cites for `_check_header_parallel_citations`
  to validate) is impossible from a CLR-only cite: `construct_austlii_url`
  (`litassist/citation/austlii.py:28`) requires medium-neutral `[YYYY] COURT N`,
  and `normalize_citation` leaves the CLR string unchanged, so the CSE query has
  no name/neutral cite to hit.
- **C2 (the real lever) - add a `traditional cite -> medium-neutral cite`
  primitive.** Source the neutral cite from, cheapest first: (1) draft
  co-occurrence (drafts usually print both forms together, e.g.
  `... (1999) 201 CLR 1; [1999] HCA 66`) - free, no fetch, prefer this; or
  (2) AustLII LawCite citator via a constructible query URL
  (`https://www.austlii.edu.au/cgi-bin/LawCite?cit=...`) - one extra fetch plus a
  new HTML parser (AustLII is permitted; only jade.io is off-limits). Once the
  neutral cite is known, the existing AustLII fetch + parallel-citation validation
  already work. Decide C2 option 1 vs 2 deliberately before building.

**Now measured (09/06/2026):** this gap - plus the jade.io cookie-reuse [SOON]
item and the AustLII PDF block above - is the **binding constraint** for the
trustworthy-output thrust: better verification cannot help citations the pipeline
cannot fetch. The P-JUDGE eval benchmark deliberately tags these classes
`fetchable:false` and **caps `citation_grounding`** on un-fetchable cites, so the
gap is a quantified line item (`=== RETRIEVAL GAP ===` in the report) rather than
an invisible assumption. Closing C2 (and Jade cookie-reuse) flips the tags to
`fetchable:true` and lifts the eval's score ceiling - which is how the win becomes
visible. See ROADMAP P-JUDGE.

## Next Steps
1. Review and prioritize remaining TODO items for next sprint
2. Consider implementing circuit-breaker enhancement for API retries
3. Review ongoing prompt optimization opportunities (October 2025 model strategy implemented)
4. **Pricing-aware features:** `litassist/llm/model_capabilities.yaml` already carries `input_price_per_mtok` and `output_price_per_mtok` per model (refreshable via `litassist refresh`). Consume them for per-call cost logging, a `--budget` flag, cost-aware model selection, and a cost field in the audit log. Capability data is already collected; consumers to be added. **First consumer arrives with P1-12 (Inc 2):** a small `litassist/llm/cost.py:estimate_call_cost()` powering the `[COST]` banner on the ensemble cross-check (which makes its 2-4x spend explicit) - generalise it to the `--budget`/audit-log uses above once it exists.
5. See ROADMAP.md for strategic feature implementation planning
6. **Roadmap restructure (04/06/2026 - no active litigation):** ROADMAP.md is research-led, with professional complaints demoted to the dormant backlog pending the [URGENT] tool-assessment above. Phase order: (1) Matter Foundation, (2) Model Quality & Research [LEAD], (3) Citation & Compliance, (4) Professional Complaints (DEFERRED/dormant), (5) Litigation Tooling (DORMANT), (6) FOI (deprioritised) + Infrastructure. P-IDs are now stable handles (not phase indicators). Code-touching items relevant to this file: P1-12 Multi-Model Cross-Checks, P2-19 Bias Divergence Detector, and the new **P-FAITH** Long-Context Faithfulness Checker all extend `litassist/verification_chain.py` (reusing `run_cove_verification()` + `citation_context.py:fetch_citation_context()`); the new **P-JUDGE** LLM-as-Judge eval harness lands as a real-API `test-scripts/test_judge_eval.py` building on `test_quality.py`. Deprioritised: P0A-2 (-> P3, dormant), P2-16 FOI (-> LOW). Dropped: P1-14 Evidence Chain Tracker. Full detail and dependency notes in ROADMAP.md.
7. **Phase 2 re-sequence (09/06/2026 - approved plan, measurement-first):** within the Model Quality & Research thrust, **P-JUDGE is built first** as the measurement keystone; P1-12 cross-checks ship **only if** P-JUDGE shows lift > cost; P2-19 divergence is a thin add reusing P1-12's `litassist/commands/verify/ensemble.py`. Corrects the prior ordering (which committed the ensemble spend before the eval that justifies it). The two new `verify` flags (`--cross-check`, `--divergence-check`/`--models`) attach to the **positional FILE** arg (not `--input`) and must be added to `test-scripts/test_cli_comprehensive.sh`. See ROADMAP Phase 2 + Next Steps.

## Future Plans

**Strategic Features:** See [ROADMAP.md](ROADMAP.md) for comprehensive feature planning (litigation support, advisory capabilities, matter management, FOI tools, etc.)

**Technical Documentation:**
- Historical LLM analysis in `docs/prompts/llm_enhancement_recommendations.md` (pre-October 2025, superseded by three-tier model strategy)
- Current model strategy in `docs/development/LLM_MODEL_STRATEGY.md`
- Testing approach in `docs/testing/test_README.md`

**Technical Enhancements:**
- Advanced QA loops: adversarial testing, iterative improvement loops, contingency planning
- Performance benchmarking and monitoring setup
- LLM response streaming functionality
- OpenAI API fine-tuning integration  

## Implementation Concerns & Considerations

### Key Architectural Implementation Points
1. **OpenAI Fine-tuning Integration**: Review `litassist/llm/` integration points (`factory.py`, `client.py`), extend LLMClient factory pattern to support fine-tuned model endpoints
2. **Streaming Implementation**: Update CLI output handlers in `litassist/cli.py`, modify response processing in command modules (`litassist/commands/`), add progress indicators
3. **Student Mode**: Leverage existing prompt templates in `litassist/prompts/`, extend base.yaml and system_feedback.yaml with beginner-friendly variants
4. **Model Configuration**: Extend `litassist/config.py` with new environment variable mappings, update `config.yaml.template` with streaming/model options
5. **Thinking Traces**: Add new logging handlers in `litassist/utils.py`, extend output directory structure for trace files
6. **o3-pro Standards**: Review existing code patterns in `litassist/commands/` modules, update linting rules in `setup.py` and `requirements-ci.txt`
8. **Config Exposure**: Add CLI arguments in `litassist/cli.py`, extend configuration validation in `litassist/config.py`

### Technical Architecture Concerns
- **Model Config Exposure**: Risk of breaking existing config.yaml structure; need backward compatibility strategy
- **Fine-tuning Implementation**: Requires OpenAI API credits, training data preparation, and evaluation metrics - significant cost implications
- **Streaming Architecture**: Major refactor needed for CLI output handling, progress indicators, and error handling during streaming
- **Student Mode Design**: Risk of prompt bloat; need clear separation between expert and beginner explanations
- **Thinking Traces**: Potential performance impact on response times; need configurable verbosity levels

### Integration Risks  
- New features may conflict with existing zero-tolerance citation enforcement
- Streaming could interfere with current output timestamping and file organization
- Model config changes might break OpenRouter integration
- Student mode explanations could dilute legal accuracy requirements

### Resource & Timeline Concerns
- Fine-tuning requires significant API budget and data preparation time
- Multiple concurrent LLM architecture changes increase testing complexity
- Student mode requires extensive legal domain expertise for accurate simplification

## Notes
- Prioritize minimal whitespace changes to maintain clean diffs
- Consider implementing features incrementally with feature flags to minimize integration risk
- Establish clear success criteria and rollback plans for each major change

---

## Completed [DONE]

### Shipped Features
- 12 registered user-facing commands (lookup, digest, extractfacts, updatefacts, brainstorm, strategy, draft, verify, verify-cove, counselnotes, barbrief, caseplan)
- Global installation via pipx
- Single configuration approach
- Outputs organized in `outputs/` directory
- Comprehensive documentation suite
- Australian legal focus throughout
- Timestamped outputs preventing data loss
- Multi-level verification system
- Zero-tolerance citation enforcement
- Clean CLI summaries instead of content dumps
- Comprehensive logging and timing instrumentation
- Fixed all ruff linting errors and removed unused dependencies
- CounselNotes command for strategic advocate analysis (January 2025)
- Barbrief command for comprehensive barrister's briefs (January 2025)

### Dated Upgrade Log
- **October 2025: Historical LLM model upgrade** - Implemented the first three-tier strategy
  - This section records the historical upgrade. Current model assignments are now in `litassist/llm/model_configs.yaml`.
  - Upgraded 20+ commands with 40-50% cost reduction while improving quality
  - All 407 unit tests passing
  - Comprehensive documentation updates across all user/dev docs
- **November 2025: Verification System Enhancements & Tooling**
  - Added --heavy flag to verify command for premium verification
  - Added --noverify flag to extractfacts, draft, and strategy commands for skipping verification
  - Changed default verify-soundness model for cost optimization
  - Fixed verify_content_if_needed() to properly respect verify_flag parameter
  - Citation validation improvements with header analysis for PDF content
  - PDF search validation with automatic retry logic (up to 3 attempts)
  - Anti-injection prompt protection added for all LLM calls
  - Raw pre-verification output persistence for audit trail compliance
  - All 392 tests passing
- **November 2025: Token Limit System Removal**
  - Removed global token limit system (use_token_limits flag and automatic 16K output limits)
  - Increased input file size limits: brainstorm (50K→600K), caseplan (50K→600K), strategy (100K+100K→600K combined)
  - Clarified thinking_effort as reasoning budget (not output limit)
  - Quality prioritized over cost - models use API defaults for comprehensive outputs
  - Deprecation warnings added for old config files
  - All 390 tests passing
- **May 2026: Caseplan hardening + parameter-translation correctness** (caseplan-upgrade branch)
  - caseplan: generated commands validated via a `shlex` round-trip (shell control characters in LLM output cannot become live operators in the saved script) with fail-loud on zero extracted commands; assessment mode now honours `--context`; empty case facts rejected before any LLM call; full-plan routed to Opus 4.7; nested `@timed` removed; plan prompt gained a canonical command-output rule and a fence/continuation fix.
  - LLM parameter translation corrected per model in `model_profiles.py`/`parameter_handler.py`: Opus 4.7/4.8 strip sampling (`temperature`/`top_p`/`top_k`) and use the extended effort scale (`xhigh`/`max`); other Claude 4.x never send `temperature` and `top_p` together; GPT-5.5 `xhigh` tier; o3 / Grok 4.20 / Gemini verbosity handling; a directly-supplied `reasoning.effort` is normalised. Added `test_model_config_sampling.py` (config-vs-capabilities guard) and a `supports_system_messages` test.
  - test-scripts: online CLI harness (`test_cli_comprehensive.sh`) stuffed with every command's switches + a `refresh` case + an output-saved assertion per command; superseded print-only scripts removed (`test_dynamic_parameters.py`, `test_prompts.py`, `test_barbrief_integration.py`); citation fetching wired into `run_tests.sh`.
  - Full offline suite green (537 tests).
- **June 2026: Glob, verification, and tooling cleanups**
  - Full glob unification: `extractfacts`, `digest`, `draft`, `counselnotes` routed through `expand_glob_patterns_callback` (matching `brainstorm`/`barbrief`); temporary `prompts/glob_help_addon.yaml` and its concatenation logic removed. See ROADMAP.md P4-25.
  - `strategy --strategies` made a multiple-files interface (`multiple=True` via `expand_glob_newest_each_callback`); each flag resolves to its own newest match and `parse_strategies_files` merges the sets.
  - Removed dead `verify_with_level` (no production callers; the `--heavy` flag already provides two-tier verification via `run_verification_chain`), plus its orphaned prompts (`light_verification`, `heavy_verification`, `heavy_verification_system`), the `verification-light` entry in `model_configs.yaml`, and four referencing tests.
  - Removed redundant top-level `litassist.py` entry point (Oct 2025).
  - Thinking-trace logging (`LegalReasoningTrace`) and reasoning-model parameter standards (o3-pro / GPT-5.5 provider-specific filtering) integrated.
  - Manual OpenRouter validation scripts present in `test-scripts/` (`test_integrations.py`, `test_quality.py`, `test_cli_comprehensive.sh`).
  - Thread-safety handling added to the progress indicator.
  - July 2025 upgrades documented across user/dev/system docs.
