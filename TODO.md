# LitAssist Development TODO

Last updated: 04/06/2026

**Note:** Strategic feature planning (litigation support, advisory capabilities, new commands) is now in [ROADMAP.md](ROADMAP.md). This file focuses on bugs, technical debt, and code quality improvements.

**Sources of truth:** command registration lives in `litassist/commands/__init__.py`; current model assignments live in `litassist/llm/model_configs.yaml`; strategic feature planning lives in `ROADMAP.md`.

---

## Current State Summary

### Completed Features [DONE]
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

### Pending Tasks [IN PROGRESS]
- [ ] **Licensing reconciliation:** the repo is inconsistent/unstated - `setup.py` declares `License :: Other/Proprietary License` (commented "proprietary / closed-source") but there is NO LICENSE file and no licence prose in README or other top-level docs. Decide a single licence (proprietary vs an OSS licence), then make `setup.py`'s classifier, a `LICENSE` file, and any doc mention all agree. Deferred from the v3.0.0 release (04/06/2026), where adding an Apache-2.0 LICENSE was dropped because it contradicted the proprietary classifier.
- [ ] **GitHub Pages decision + stale URLs:** no GitHub Pages site exists (Pages API 404, no `gh-pages` branch, no `mkdocs.yml`/`_config.yml`/`CNAME`, no Pages workflow). Decide whether to publish the `docs/` tree as a Pages site. Regardless of that decision, the stale placeholder/branch URLs were corrected in the v3.0.0 release-tooling fix - `.github/workflows/release.yml` (`/blob/main/` -> `/blob/master/`), `scripts/release/finalize-release.sh` (`YOUR-ORG`/`main` -> `agelastic/litassist-priv`/`master`), and `RELEASE_PROCESS.md` (`main` -> `master`); confirm no other docs still link to a non-existent Pages site or the wrong branch.
- [x] ~~Fix lookup `--comprehensive` help/behavior mismatch~~ - Already correct (verified Oct 2025)
- [x] ~~Enable `openrouter.api_base` setting~~ - Not needed (OpenAI SDK v1.0+ architecture change)
- [ ] Implement circuit‑breaker (`safety_cutoff`) in retry logic [AG-124] - OPTIONAL enhancement (has 5-retry limit)
- [x] ~~Remove redundant top‑level `litassist.py` entry point~~ - COMPLETED (Oct 2025)
- [x] ~~Fail fast on config load errors~~ - Already implemented (verified Oct 2025)
- [x] ~~REMOVE temporary glob help addon after unification~~ - COMPLETED (deleted glob_help_addon.yaml, removed concatenation logic in caseplan/plan_generator.py)
- [x] ~~IMPLEMENT full glob unification~~ - COMPLETED (extractfacts, digest, draft, counselnotes routed through expand_glob_patterns_callback; brainstorm and barbrief already used it)
- [x] ~~extend strategy --strategies to MULTIPLE files~~ - COMPLETED (June 2026). `--strategies` is now `multiple=True` (repeatable, one brainstorm set per flag) via `expand_glob_newest_each_callback`; each flag resolves to its own newest match and `parse_strategies_files` merges the sets (summed counts, `=== filename ===`-separated content). The caseplan prompt emits creative + research flags. See ROADMAP.md P4-25.
- [ ] AUDIT: verification coverage (mapping done June 2026; two decisions remain). Confirmed against source: verifies BY DEFAULT (draft, strategy, extractfacts, with `--noverify` opt-out); OPT-IN via `--verify` (brainstorm, counselnotes, barbrief); NO verification (lookup, digest, updatefacts; caseplan and verify-cove are separate). Open items: (1) the caseplan prompt does NOT yet force `--verify` on opt-in commands that emit court documents, except barbrief (done May 2026) - extend it to the others; (2) decide whether strategy's auto-verified court doc (`outputs/strategy_draft_*.md`) also warrants a standalone post-hoc `verify`.
- [x] ~~Develop manual validation scripts for OpenRouter integration (in test-scripts/)~~ - COMPLETED (test_integrations.py, test_quality.py, test_cli_comprehensive.sh exist; RAG workflows removed in remove-pinecone-rag branch)
- [ ] Enhance QA loops: iterative improvement, contingency planning, multi-perspective reviews (partial: verify-cove + brainstorm regeneration exist; contingency/multi-perspective absent)
- [ ] Automate performance benchmarking and monitoring setup [MON]
- [ ] Implement OpenAI API fine-tuning per platform recommendations
- [ ] Add LLM response streaming functionality
- [ ] Expose model configuration parameters via CLI/env vars
- [ ] Develop "student mode" with newcomer-friendly explanations
- [x] ~~Add thinking trace logging system~~ - COMPLETED (LegalReasoningTrace class exists and used throughout)
- [x] ~~Integrate reasoning-model parameter standards~~ - COMPLETED (`o3-pro` and current GPT-5.5-style model handling are integrated with provider-specific parameter filtering)
- [ ] Adopt Jules framework for test instrumentation (evaluate if still desired)
- [x] ~~**Refactor verify_with_level (Option B)**~~ - COMPLETED (June 2026). Resolved as dead-code removal, not a refactor: `verify_with_level` had no production callers, and the boolean `--heavy` flag (Nov 2025) already provides two-tier (standard/heavy) verification via `run_verification_chain`. Deleted the method (`litassist/llm/verification.py`), its now-orphaned prompts (`light_verification`, `heavy_verification`, `heavy_verification_system` in `prompts/verification.yaml`), the orphaned `verification-light` entry in `model_configs.yaml`, and the four tests that referenced it. [DEBT]
- [ ] **Add optional reasoning trace file output**: CORRECTION (June 2026): strategy and verify already write reasoning traces to separate timestamped files by default (`commands/strategy/file_handler.py`, `commands/verify/reasoning_handler.py`); the premise "embedded in main output only" was stale. Residual scope is narrow - an opt-in `--save-reasoning` file for commands that do NOT already emit one (notably draft). Re-confirm need before building; may be useful for professional-liability audit trails.
- [ ] **Migrate off Google Custom Search JSON API by 01/01/2027**: Google has announced the JSON API is being retired in favour of Vertex AI Search (favourable alternative for <=50 domains) or the new full web search solution. LitAssist uses the JSON API in `litassist/citation/google_cse.py`, `litassist/commands/lookup/search.py`, `litassist/citation_context.py`, `litassist/cli.py` (startup ping), and two test-scripts. All three configured CSEs (Jade.io, AustLII, Comprehensive) are well under the 50-domain threshold and none use "Search the entire web", so the transition target is Vertex AI Search. Design sketch in `docs/development/GOOGLE_CSE_MIGRATION_PLAN.md`. No urgent action; deadline 01/01/2027.
- [ ] **[SOON] Implement jade.io cookie-reuse fetch via Jina**: Replace the jade.io skip in `litassist/commands/lookup/fetchers.py:548-572` with a cookie-authenticated Jina fetch. jade.io article pages are SPA-rendered behind passwordless email magic-link auth; direct/Jina fetches without auth currently return only login chrome (no judgment text). Approach: (1) user logs in manually in a browser once, (2) copies session cookies from DevTools (`JSESSIONID`, `IID`, any post-login auth cookies), (3) stores them in config (e.g. `JADE_COOKIES` env var or `config.yaml`), (4) lookup forwards the `Cookie:` header to Jina's `r.jina.ai` API so rendering happens as the authenticated user. Add a `_looks_like_jade_login_wall` detector matching strings like "Check your email", "sign-in link", "Use verification code", "Register for free" — fires when cookies have expired and logs a clear "refresh JADE_COOKIES" warning. Implementer note: verify that Jina's r.jina.ai API forwards arbitrary `Cookie:` headers to the target site (their docs cover header passthrough); if not, use curl_cffi + manual JS rendering or fall back to skipping. See conversation 26/05/2026 for empirical findings: curl_cffi defeats Cloudflare on jade.io (HTTP 200, 15KB shell) but content is auth-gated; Jina renders the page but only sees login chrome without cookies.
- [ ] **Evaluate removing Jina from the lookup fetcher chain**: After the 26/05/2026 fetcher work (captcha-marker fix, gibberish-heuristic loosening, AustLII PDF -> HTML substitution, fedcourt unblocked), Jina's production usage has shrunk to a narrow set: (1) `ndfv.jade.io` URLs (forced routing in `_fetch_url_content`), (2) HTTP 4xx/5xx fallback from curl_cffi (rare), (3) extraction < 100 chars (rare after the gibberish-check loosening). The jade.io cookie-reuse [SOON] entry above currently assumes Jina is the transport; if that work is reshaped to use curl_cffi directly with Cookie headers (avoiding Jina's IP class which is itself Cloudflare-challenged on many AU government sites), Jina would have no callers left. Decision criteria: after 1-2 weeks of production usage with the current chain, query the audit logs for `method=jina_reader` entries and count successes vs failures. If `successes / total < 5%` and no critical case relies on Jina alone, remove. Removal would: (a) drop the jina_api_key config field, (b) delete `_fetch_via_jina` and its tests, (c) replace the ndfv.jade.io routing with curl_cffi + skip (per the same logic as the jade.io main domain skip already in place), (d) collapse the gibberish fallback to "return empty content" instead of attempting Jina. Verified 26/05/2026: jina_api_key in config is valid and works (probe to fairwork.gov.au returned 64KB markdown); the question is not whether Jina works mechanically but whether it actually adds coverage that curl_cffi misses. See conversation 26/05/2026 for the empirical analysis (78% Jaccard similarity between curl_cffi and Jina renderings of triplezero.vic.gov.au showed Jina was adding navigation chrome, not legal content). Order this AFTER the jade.io cookie-reuse work since that may itself remove the last forced Jina path.
- [ ] **Known limitation: AustLII PDF paths are Cloudflare-blocked**: AustLII serves PDFs behind a strict Cloudflare policy that returns "Just a moment..." challenge body (HTTP 403, `cf-mitigated: challenge`) to every Python transport tested on 26/05/2026: requests with Chrome 91/136 UAs, curl_cffi with chrome116/120/131/136 profiles, curl_cffi with HTML-warmup cookies + Referer, Jina (datacentre IPs also challenged), Playwright vanilla, Playwright + playwright_stealth (16 attempts with fresh-context-per-fetch, multiple PDFs), patchright (CDP-leak-patched Chrome 148), nodriver (custom CDP transport), and Camoufox (custom Firefox with C++ stealth patches). The user's own real Chrome browser also shows the Cloudflare banner. The block is server-side and per-URL-extension: HTML siblings at the same paths pass curl_cffi cleanly. Mitigation already implemented (26/05/2026): the fetcher detects `austlii.edu.au` PDF URLs and rewrites to the `.html` sibling before the HTTP fetch (`litassist/commands/lookup/fetchers.py` `_fetch_url_content`). Recovery rates per empirical test: full article HTML (CanterLawRw, MelbULawRw patterns) returns 70-110KB of clean text; stub HTML (VUWLawRw 2016/2020, AukULawRw 1992 patterns) returns ~1KB containing the full Australian citation but no article body; bill_em PDFs have no HTML sibling and 404. If a paid Cloudflare-bypass service (ScrapingBee/ZenRows/Bright Data Web Unlocker) is later judged worth the cost, integrate as a new transport in the chain after curl_cffi but before Jina. Diagnostic scripts that produced this evidence: `/tmp/austlii_diag.py`, `/tmp/playwright_test*.py`, `/tmp/stealth_compare.py`, `/tmp/camoufox_test.py` (regenerate from the 26/05/2026 conversation if needed).
- [x] ~~Document July 2025 upgrades in all user/dev/system docs~~ - COMPLETED

## Critical Bugs to Fix [HIGH PRIORITY]

### Code Quality Issues
- [x] ~~**Fix thread safety in progress indicator**: No error handling if progress thread fails. Add exception handling and timeout~~

### Performance & Reliability
_No critical bugs identified - all items below verified as already implemented or false alarms:_
- ~~Rate limiting~~ - Already exists (tenacity with exponential backoff)
- ~~Circuit breaker~~ - Has retry limits (5 attempts), full circuit breaker is nice-to-have but not critical
- ~~Bare exceptions~~ - All exceptions are properly typed and logged
- ~~o3-pro validation~~ - Validation exists via effort mapping
- ~~Large file handling~~ - MemoryError is caught and handled gracefully
- ~~Input validation~~ - Click validates file existence automatically at entry points

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

### Next Steps
1. Review and prioritize remaining TODO items for next sprint
2. Consider implementing circuit-breaker enhancement for API retries
3. Extend strategy --strategies to MULTIPLE files (glob-to-newest now done; multi-file interface still deferred; see Pending Tasks)
4. Review ongoing prompt optimization opportunities (October 2025 model strategy implemented)
5. **Pricing-aware features:** `litassist/llm/model_capabilities.yaml` already carries `input_price_per_mtok` and `output_price_per_mtok` per model (refreshable via `litassist refresh`). Consume them for per-call cost logging, a `--budget` flag, cost-aware model selection, and a cost field in the audit log. Capability data is already collected; consumers to be added.
6. See ROADMAP.md for strategic feature implementation planning

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
7. **Jules Framework**: Integrate with existing test infrastructure in `tests/unit/`, update `test-scripts/` directory structure
8. **Config Exposure**: Add CLI arguments in `litassist/cli.py`, extend configuration validation in `litassist/config.py`

### Technical Architecture Concerns
- **Jules Framework Integration**: Need to research Jules framework documentation and compatibility with existing test infrastructure
- **o3-pro Standards**: Requires clarification on specific coding standards and how they integrate with current Python/legal domain patterns
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
- Jules framework adoption may require team training
- Multiple concurrent LLM architecture changes increase testing complexity
- Student mode requires extensive legal domain expertise for accurate simplification

## Notes
- Prioritize minimal whitespace changes to maintain clean diffs
- Consider implementing features incrementally with feature flags to minimize integration risk
- Establish clear success criteria and rollback plans for each major change
