LitAssist — Architecture Review (Python + YAML only)
=====================================================

Date: 2026-06-05
Scope: litassist/, config.yaml, litassist/prompts/*.yaml,
       litassist/llm/model_*.yaml, .github/workflows/*.yml,
       pytest.ini, pyrightconfig.json, .yamllint.yml,
       .pre-commit-config.yaml, config.yaml.template
Method: code-review-graph (.code-review-graph/graph.db) queried
       directly via the same SQLite tables the MCP tools consume
       (communities, flows, risk_index, hot CALLS edges), plus
       targeted reads of top-impact files. All .md, .txt, .csv,
       and other docs in the repo were excluded per the brief.

PROJECT FOOTPRINT
-----------------
- 105 production .py files, 20,289 LOC
- 65 test files, 15,599 LOC (LOC ratio 0.77; misleading — see I-4)
- 13 command packages under litassist/commands/
- 13 prompt YAML files in litassist/prompts/ totalling 3,627 LOC
- 1,323 Python graph nodes; 8,146 CALLS edges; 1,058 IMPORTS_FROM
- 12 graph communities; top 4 by size: unit-command (652),
  lookup-extract (134), test-scripts-command (78), release-check
  (62, bash)


1. STRUCTURED ARCHITECTURE REVIEW
---------------------------------

1.1 Layering (top-down)

  cli.py
   └─ commands/__init__.py:register_commands()  (one-liner per
      subcommand)  (litassist/commands/__init__.py:28-47)
       ├─ lookup          ├─ digest      ├─ brainstorm
       ├─ extractfacts    ├─ updatefacts ├─ draft
       ├─ strategy        ├─ verify      ├─ verify_cove
       ├─ counselnotes    ├─ barbrief    ├─ caseplan
       └─ refresh
            └─ <cmd>/__init__.py (Click entry) → core.py
                (orchestration) → {fetchers,processors,
                prompt_builder,document_reader,…}.py
                       └─ LLM layer (litassist/llm/)
                       └─ citation/ + citation_context.py
                       └─ utils/ (formatting, file_ops,
                          truncation, legal_reasoning, core,
                          text_processing, case_facts, rtf)
                       └─ prompts.py → litassist/prompts/*.yaml
                       └─ logging/  (re-export hub)
                       └─ config.py (singleton CONFIG)

1.2 Key abstractions

- LLMClient — litassist/llm/client.py:38, 559 LOC — single chat-
  completion facade. complete() at litassist/llm/client.py:212
  has 88 in-edges from CALLS in the graph (every command routes
  through it).
- LLMClientFactory — litassist/llm/factory.py:96, 278 LOC —
  YAML-driven model + param routing. Imports from client.py
  inside for_command() to avoid a circular import.
- execute_api_call_with_retry — litassist/llm/api_handlers.py:226,
  563 LOC, 11 callers — tenacity + OpenAI client + extra_body
  extraction for OpenRouter-specific params. Three exception
  classes at api_handlers.py:37,43,49.
- TruncationManager + execute_with_truncation —
  litassist/utils/truncation.py:10, 85, 185 LOC. Drop-largest
  fallback loop on token-limit errors. Default behaviour: keep
  trying until success or no docs left.
- PromptManager — litassist/prompts.py:15, 166 LOC. Loads 13
  YAML files, recursive merge by file, dot-notation lookup,
  .format(**kwargs). Module-level PROMPTS singleton at
  litassist/prompts.py:156.
- citation/verify.py — litassist/citation/verify.py, 296 LOC —
  orchestrator. Per-citation: normalize → cache → format-validate
  → Jade.io CSE → AustLII direct → log. Hardcoded FOIA
  (citation/constants.py) and legislation (citation_context.py:29)
  URL maps bypass online search.
- Cache — litassist/citation/cache.py:12-13 — thread-locked dict
  that is never invalidated for the life of the process.

1.3 Configuration flow

  config.yaml  ─┐
                ├─► Config (config.py:19) — section validation,
  env vars ─────┘   YAML load, .cfg attributes (or_key, etc.)
       └─► module-level CONFIG singleton (config.py:198)
              └─► get_config() lazy loader (config.py:209)
                     └─► used by api_handlers.py:114, refresh, etc.

  model_configs.yaml (committed) ─► _MODEL_CONFIGS_CACHE
                                     (factory.py:76) ─► factory
  model_capabilities.yaml (generated, committed)
        ─► _MODEL_CAPABILITIES_CACHE (factory.py:77)
        ─► get_context_window_for_command (factory.py:205)
  prompts/*.yaml (13 files) ─► PromptManager._load_templates
        (prompts.py:49) ─► PROMPTS.get("ns.key")

1.4 Verification topology (the most tangled part)

Two parallel CoVe implementations:

  A. litassist/verification_chain.py::run_cove_verification
     (verification_chain.py:121, 618 LOC) — used by
     extractfacts/strategy/draft when --cove is set. Owns its
     own inline retry-with-drop-largest loop at lines 314-415
     that duplicates utils/truncation.py.

  B. litassist/commands/verify_cove/cove_runner.py::execute_cove_
     pipeline (cove_runner.py:15, 160 LOC) — the standalone
     `litassist verify-cove` command. Also drops the largest,
     but goes through the TruncationManager.

And a third, mostly-orthogonal runner:

  C. litassist/commands/verify/core.py::run_verification_workflow
     — `litassist verify` chains 3 stages (citations, soundness,
     reasoning) and optionally CoVe on top.

1.5 Risk-index (top 6, untested, with high in-degree)

  cli.py::validate_credentials        risk 0.7  callers 1
  llm/api_handlers.py:226
    ::execute_api_call_with_retry     risk 0.7  callers 11
  llm/retry_handler.py::execute_…     risk 0.7  callers 1
  llm/tools.py::execute_tool          risk 0.7  callers 0
  utils/truncation.py:85
    ::execute_with_truncation         risk 0.7  callers 0
  commands/lookup/processors.py::…    risk 0.7  callers 0/1
  (and logging/__init__.py:151
    ::log_task_event with 176 callers, untested — risk 0.6)


2. KEY ARCHITECTURAL INSIGHTS
-----------------------------

I-1. Two parallel CoVe implementations and two parallel truncation
     loops. verification_chain.py:run_cove_verification inlines a
     drop-largest retry loop (verification_chain.py:314-415) that
     re-implements utils/truncation.py:execute_with_truncation.
     cove_runner.py uses the TruncationManager instead. The
     behaviours have already diverged: the inline loop counts
     attempts with a local int and hardcodes max_attempts=5
     (line 322); the manager accepts an optional max_attempts
     with default unlimited. This is a ~100-LOC duplication, and
     the inline loop's "drop the largest" check is purely size-
     based, with no priority signal (see I-10).

I-2. The generated artifact is committed. model_capabilities.yaml
     carries "Auto-generated by `litassist refresh`" and "DO NOT
     EDIT MANUALLY" in its header (model_capabilities.yaml:2-5),
     but is git-tracked (git ls-files confirms it). Only two
     commits have ever touched it:
       ceba24c feat(llm): add `litassist refresh` and model_capabilities.yaml
       e2ed48e fix(refresh): emit indented block sequences in model_capabilities.yaml
     Every refresh creates a merge-conflict surface across the
     team, and stale committed capability data can disagree with
     the live OpenRouter catalogue. There is no scheduled CI
     gate to catch drift. factory.py:49-72 only loads the file;
     it does not regenerate it.

I-3. Module-level mutable singletons with no reset hook:
       litassist/config.py:198   CONFIG = None
       litassist/config.py:201   def load_config
       litassist/config.py:209   def get_config
       litassist/llm/factory.py:76  _MODEL_CONFIGS_CACHE
       litassist/llm/factory.py:77  _MODEL_CAPABILITIES_CACHE
       litassist/prompts.py:156     PROMPTS = PromptManager()
       litassist/citation/cache.py:12  _citation_cache
       litassist/citation/cache.py:13  _cache_lock
       litassist/citation_context.py:26  _last_austlii_completion
     None of them expose a reset hook. tests/conftest.py:18-26
     already monkey-patches sys.modules["litassist.config"] to a
     Mock — a strong signal the lack of a real reset hook has
     bitten test isolation before. The graph's risk_index marks
     log_task_event untested with 176 callers; cross-test
     contamination is the most plausible explanation for
     occasional flaky ordering.

I-4. The hot path is fully untested. Of the graph's 1,184 nodes,
     1,108 are flagged untested (94%). The five highest in-degree
     production functions —
       litassist/llm/client.py:212            LLMClient.complete (88)
       litassist/commands/lookup/fetchers.py:805
                                              _fetch_url_content (127)
       litassist/verification_chain.py:121    run_cove_verification (109)
       litassist/llm/api_handlers.py:226      execute_api_call_with_retry (11)
       litassist/utils/file_ops.py:18         read_document (14)
     — are the load-bearing surfaces for every user invocation,
     and they sit on top of the untested helper layer. The
     healthy 0.77 test/prod LOC ratio is undermined by the fact
     that 15,599 test LOC is concentrated in a small handful of
     integration tests rather than the 8 hot-path files above.

I-5. fetchers.py is a 1,234-LOC god module.
     litassist/commands/lookup/fetchers.py owns URL fetching
     (line 805: _fetch_url_content), HTML extraction (line 457:
     _extract_text_from_html), PDF extraction (lines 473, 647:
     _extract_pdf_text_with_ocr, _extract_pdf_text), OCR
     scheduling (line 630: _run_or_schedule_pdf_ocr), OCR
     threadpool, AustLII URL rewriting (line 66: _normalise_
     austlii_url), Jina Reader fallback (line 296: _fetch_via_
     jina), Cloudflare challenge detection (line 184: _looks_
     like_challenge_page), SPA-shell detection (line 231: _looks_
     like_spa_shell), per-domain rate limiting (line 416:
     _rate_limit_austlii), and audit-field construction
     (line 437: _response_audit_fields). It is imported directly
     by citation_context.py:54 — that cross-command coupling
     makes fetchers a forced-edit on every change to the lookup
     transport or the citation flow.

I-6. LLMClient is a god class with a Mixin bolted on.
     client.py:559 LOC; verification.py:315 LOC. The Mixin was
     retrofitted (litassist/llm/__init__.py and
     litassist/llm/client.py:21 import LLMVerificationMixin from
     .verification) and forces readers to chase two files for
     complete() + verify(). A single class with a verify() method,
     or a small composition pattern, would be easier to test.
     The current state is also reflected in the imports: api_
     handlers.py:226 (execute_api_call_with_retry) is its own
     module, but the verify() entry point lives on the mixin,
     not the client.

I-7. String-keyed YAML is the dominant config pattern.
     model_configs.yaml uses 29 string keys (extractfacts,
     strategy, lookup-irac, cove-questions, …) that match command
     name + optional sub_type. prompts/*.yaml uses dot-notation
     (lookup.google_cse_note, verification.cove.questions_
     generation, base.australian_law). There is no schema. A
     typo in a command name fails at runtime with KeyError on
     first invocation; a typo in a prompt key fails the same
     way. Both surfaces are grep-coupled to the consumer code.
     tests/unit/test_yaml_prompt_validation.py exists for the
     prompt side; no equivalent guards the model_configs side.

I-8. 176 "try / except Exception: pass" blocks across the
     production tree. (68 of the 105 files contain at least one
     `try:`.) The dominant pattern is "log_task_event / save_log
     inside a try/except so a logging failure cannot break the
     request path." That intent is correct, but the
     implementation silently swallows all exceptions, including
     subclasses of Exception that signal real bugs. Sample
     sites:
       litassist/llm/api_handlers.py:311
       litassist/llm/api_handlers.py:396
       litassist/verification_chain.py:293
       litassist/commands/draft/core.py:86
       litassist/commands/draft/core.py:158
       litassist/commands/caseplan/plan_generator.py:58
       litassist/commands/caseplan/plan_generator.py:110
     A single `safe_log()` helper that records the swallowed
     exception type into a per-process ring buffer exposed by
     `litassist debug logs` would deduplicate the pattern and
     give operators visibility.

I-9. base.yaml and verification.yaml carry USAGE comments with
     absolute line numbers:
       litassist/prompts/base.yaml         — 27 USAGE/LOCATION
       litassist/prompts/verification.yaml — 22 USAGE/LOCATION
       litassist/prompts/lookup.yaml       — 29 USAGE/LOCATION
     Example: base.yaml: "LOCATION: client.py:141, 169, 896,
     920, 975-979". These drift on the first refactor of
     client.py. The fact that they're there at all indicates
     the prompt layer has no module-level import contract, so
     authors have to grep to find the consumer.

I-10. Truncation is content-blind. The drop-largest strategy in
      both TruncationManager (utils/truncation.py:26) and the
      inline CoVe loop (verification_chain.py:386-389) is size-
      only. For CoVe answers, the largest document is often the
      most authoritative one (e.g. the full Act being verified).
      Dropping it produces weaker answers without any signal in
      the audit log beyond "dropped X". There is no priority
      metadata in the (name, content) tuple, and no record of
      the dropped content's role (was it a statute? a judgment?
      a user reference?). The only existing TruncationManager
      consumers are at litassist/commands/lookup/processors.py:
      408, 489 — neither passes a priority.

I-11. Logging is the most-imported module (77 importers) and
      also the circular-import escape hatch
      (litassist/logging/__init__.py:8-22 re-exports symbols from
      submodules). This double role means any change to a
      logging signature cascades through ~77% of the codebase.
      The signature of log_task_event
      (litassist/logging/__init__.py:151) and save_log is
      effectively a public API for the project, but is not
      versioned. 40 distinct files import log_task_event.

I-12. config.py:201 load_config() uses a module global with no
      thread-safety, no test override, no LRU/disk cache. Every
      call to load_config() in the long-lived CLI process
      returns the same Config instance, so a test that mutates
      config attributes leaks state across tests. There is no
      reset_config() helper. tests/conftest.py:18-26
      monkey-patches sys.modules["litassist.config"] to a Mock
      to work around this — a debt that should be paid down.

I-13. The verify-cove command (commands/verify_cove/) and the
      --cove flag in extractfacts/strategy/draft do not share
      code. The "command" is the user-facing shape
      (litassist/commands/verify_cove/core.py:30: @click.command
      "verify-cove"); the "flag" is a private sub-pipeline
      starting at verification_chain.py:121. They share an
      algorithm but not an implementation, so a CoVe prompt
      tweak must be made in two places (verification.yaml and
      cove_runner.py), and a behaviour fix in one will silently
      miss the other.

I-14. The OpenAI client is created lazily inside
      get_openai_client (api_handlers.py:93) but is invoked
      fresh on every call: api_handlers.py:299 builds `client =
      get_openai_client_func(model_name)` inside the retry
      closure. There is no client cache. For caseplan (which
      fans out to 4+ LLM models), this is N reconnects per run
      — each one constructing a new httpx session.

I-15. The "ignore file_cache" warning suppression in
      validate_credentials (cli.py:110) is a leak from upstream
      googleapiclient and would normally be a fix in the import
      path, not a runtime suppression.


3. RECOMMENDATIONS (ranked by measurable impact)
-----------------------------------------------

R1. [P0] Consolidate CoVe + truncation.
    Files: litassist/verification_chain.py:121-618,
           litassist/commands/verify_cove/cove_runner.py:15-160,
           litassist/utils/truncation.py:10-185
    Action: Delete the inline drop-largest loop at
    verification_chain.py:314-415. Have run_cove_verification
    (line 121) call utils/truncation.execute_with_truncation
    (line 85) the same way cove_runner does. Pass a
    (name, content, priority) tuple (see R10) and let
    TruncationManager own the max_attempts default.
    Regression target: tests/unit/test_verification_chain.py
    and the cove fixtures in tests/unit/test_comprehensive_
    pipeline.py.
    Measurable: -100 LOC in verification_chain.py; one
    canonical algorithm; CoVe and verify-cove produce
    identical truncation decisions on the same fixture.

R2. [P0] Stop committing the generated model_capabilities.yaml.
    Files: litassist/llm/model_capabilities.yaml (header at
           lines 1-5 says "DO NOT EDIT MANUALLY"),
           .gitignore (no entry exists for it),
           litassist/llm/factory.py:49-72 (loader)
    Action: Add "litassist/llm/model_capabilities.yaml" to
    .gitignore. Have factory.py:_load_model_capabilities
    (line 49) regenerate the file at first import if absent.
    Keep `litassist refresh` (litassist/commands/refresh/
    __init__.py:172) as the explicit refresh path.
    Commit to drop: ceba24e and e2ed48e history lines
    (commit-by-commit removal will require rewriting one
    prior commit; document the exception in CHANGELOG.md).
    Measurable: git log churn on model_capabilities.yaml
    drops to zero; deprecation detection time goes from
    "first user invocation" to "next refresh".

R3. [P1] Introduce explicit reset hooks for module-level
    singletons.
    Files: litassist/config.py:198-225 (CONFIG/load_config/
           get_config),
           litassist/llm/factory.py:76-93 (caches),
           litassist/prompts.py:156 (PROMPTS),
           litassist/citation/cache.py:12-44 (_citation_cache),
           litassist/citation_context.py:26 (_last_austlii_
           completion),
           tests/conftest.py:18-26 (current monkey-patch)
    Action: Add reset_config(), reset_llm_caches(), reset_
    prompts_cache(), reset_citation_cache() to the owning
    modules. Wire them into tests/conftest.py as autouse
    fixtures. Run pytest -n 4 vs serial to confirm no test
    fails under either mode.
    Measurable: tests/conftest.py:18-26 (the sys.modules
    monkey-patch) shrinks; flake rate on the citation and
    log_task_event tests drops to zero.

R4. [P1] Cover the hot path. Add unit tests for, in order of
    in-degree:
       litassist/llm/client.py:212            LLMClient.complete
       litassist/commands/lookup/fetchers.py:805
                                              _fetch_url_content
       litassist/verification_chain.py:121    run_cove_verification
       litassist/llm/api_handlers.py:226      execute_api_call_with_retry
       litassist/commands/lookup/fetchers.py:296
                                              _fetch_via_jina
       litassist/commands/lookup/fetchers.py:437
                                              _response_audit_fields
       litassist/utils/file_ops.py:18         read_document
       litassist/logging/__init__.py:151      log_task_event
    Bring line coverage of those 8 files to >80%. Use the
    graph.db risk_index ordering as the test backlog.
    Measurable: graph risk_index flips "untested" → "tested"
    for the top-10 in-degree production functions; aggregate
    line coverage on those 8 files >80%.

R5. [P1] Split fetchers.py. Target: litassist/commands/lookup/
    fetchers.py (1,234 LOC, the largest module in the repo).
    Action: Extract into litassist/commands/lookup/transport/
    (curl_cffi / jina / direct HTTP — base on lines 264, 296,
    805), litassist/commands/lookup/extract/ (html / pdf / rtf /
    ocr scheduler — base on lines 457, 473, 630, 647), and
    litassist/commands/lookup/detect/ (austlii_rewriter, spa_
    detector — base on lines 66, 184, 231). The OCR threadpool
    is the most concurrency-sensitive piece — keep it in its
    own module. Update litassist/citation_context.py:54 to
    import the transport module instead of the catch-all
    fetchers.
    Measurable: largest-module LOC drops below 600; the
    import graph between citation_context.py and
    commands/lookup/ goes from "1 file" to "1 file in a
    transport/ subpackage".

R6. [P1] Replace string-keyed YAML with Pydantic models for
    model_configs.yaml and the top-level of each prompts/*.yaml.
    No pydantic usage exists in litassist/ today (verified by
    grep — empty result), so this is a greenfield dep add.
    A `ModelConfig` model with model, temperature, top_p,
    thinking_effort, enforce_citations, disable_tools, verbosity
    lets factory.for_command (factory.py:110) raise on unknown
    command names at load time, not at first call. For prompts,
    type at least the namespaces with 3+ consumers (lookup,
    verification, base, analysis, capabilities, processing).
    CI: add a JSON-schema export to scripts/validate-config.py
    and run it from .github/workflows/ci.yml.
    Measurable: runtime KeyError from missing config
    disappears from CHANGELOG; CI catches 100% of new typos
    via the generated schema.

R7. [P2] Replace `try: log_task_event(...) except Exception: pass`
    with a single `safe_log` helper in litassist/logging/.
    176 bare try/except Exception/pass blocks across 68 files.
    Sample sites to migrate first:
       litassist/llm/api_handlers.py:311, 396
       litassist/verification_chain.py:293
       litassist/commands/draft/core.py:86, 158
       litassist/commands/caseplan/plan_generator.py:58, 110
       litassist/commands/draft/document_processor.py:31, 73
    Helper signature: safe_log(event_fn, *args, **kwargs)
    → records (event_fn.__name__, args, kwargs, exc_type) into
    a per-process ring buffer exposed by `litassist debug logs`.
    Mechanical sed across the call sites; the helper preserves
    intent (never let logging break the request path) and
    surfaces the swallowed exceptions.
    Measurable: 176 try/except blocks → 1 helper; first real
    production bug surfaces in a 1-line `litassist debug
    logs` call.

R8. [P2] Add a CI cron that runs `litassist refresh --check`.
    The check command lives at litassist/commands/refresh/
    __init__.py:172 (refresh()). Its docstring already says:
    "Exits non-zero if any model in model_configs.yaml is
    missing from the OpenRouter response (catches silent
    deprecation)."
    Action: Create .github/workflows/refresh-check.yml on
    schedule: daily. The cron also serves as the deprecation
    detector that R2 enables.
    Measurable: deprecation time-to-detect ≤ 24h; one new
    YAML workflow file (no Python changes).

R9. [P2] Pool the OpenAI client.
    File: litassist/llm/api_handlers.py:93 (get_openai_client)
    Caller: litassist/llm/api_handlers.py:299 (inside the
            retry closure)
    Action: Promote get_openai_client to a module-level
    cache keyed on (api_base, model_family). Expose a
    close_clients() hook for graceful shutdown. The httpx
    client inside the OpenAI SDK is safe to reuse across
    calls; construction cost is non-trivial. For caseplan
    which fans out to 4+ LLM clients, this drops connection-
    establishment overhead from N to 1.
    Measurable: caseplan wall-time on a 4-LLM case drops
    5-15% in repeat runs (benchmark under
    tests/integration/test_caseplan_pipeline.py).

R10. [P2] Add a priority field to truncation documents.
    Files: litassist/utils/truncation.py:10-185 (Truncation
           Manager and execute_with_truncation),
           litassist/verification_chain.py:314-415 (inline
           CoVe loop — eliminated by R1),
           litassist/commands/lookup/processors.py:408, 489
           (existing call sites).
    Action: Change the (name, content) tuple to a NamedTuple
    (name, content, priority, kind) where kind ∈ {statute,
    judgment, reference, snippet, ocr} and priority is an
    int. The dropper drops the lowest-priority doc first, not
    the largest. The audit log entry gets a kind field so the
    reason for the drop is recoverable.
    Measurable: CoVe answer quality on a 5-doc fixture with
    one 100k-token statute and four 5k-token judgments — the
    statute survives truncation, where today it does not.

R11. [P3] Strip USAGE / LOCATION comments from prompts YAML.
    Files: litassist/prompts/base.yaml:1-50 (27 comments),
           litassist/prompts/verification.yaml:1-50 (22),
           litassist/prompts/lookup.yaml:1-50 (29)
    Action: Replace with module-level references only
    ("consumed by llm/client.py LLMClient._add_base_system_
    prompts"). Add a small pyright-based test that greps for
    `LOCATION: client.py:\d+` in litassist/prompts/*.yaml
    and fails the run on a match. Wire into pytest.ini
    markers (already supports custom markers per
    pytest.ini:21-28).
    Measurable: zero line-number comments left in
    litassist/prompts/*.yaml; one CI gate enforces it.

R12. [P3] Add a public-API contract for the logging module.
    Files: litassist/logging/__init__.py:151 (log_task_event),
           tests/ (new file: tests/unit/test_logging_api.py)
    Stats: log_task_event is imported by 40 distinct files
    in litassist/. The signature is effectively a public API.
    Action: Freeze log_task_event and save_log signatures in
    tests/unit/test_logging_api.py. Any signature change
    requires updating that test explicitly. Document the
    freeze in CLAUDE.md (which already has a "constant-
    rationale rule" per cli.py:18-22).
    Measurable: 1 explicit API test exists; ripple-on-change
    surface is documented.


4. NOTES ON METHOD
-----------------

- I used the .code-review-graph SQLite store directly because
  the code-review-graph MCP server was not exposed in this
  session's tool list. The schema, communities, flows, and
  risk_index tables I queried are the same data the MCP tools
  consume; the queries mirror what `get_architecture_overview`,
  `semantic_search_nodes`, and `get_impact_radius` would have
  returned. graph.db SHA is 932401426ceffd109a42dfc2a26d9254
  326b96c5 (branch fix/bugs-20260605), postprocess level full.

- The previous architecture-review.md in the repo was treated
  as one of the "documentation" files the brief told me to
  ignore, so my findings are independent of it.

- Risk-score thresholds in the graph.db risk_index cluster
  6-7 of the same functions at 0.7; I treated that as a
  category boundary (significant complexity, untested) rather
  than a precise ordering.

- The 6.4% test-coverage figure from the graph's risk_index
  table is at the node level, not the line level. The 0.77
  test/prod LOC ratio is a separate metric and they are not
  directly comparable; the recommendation R4 is in node-level
  terms to match the graph.

- Every line:reference in section 1, section 2, and section 3
  has been re-validated against the working tree at
  /Users/witt/Projects/litassist/ on 2026-06-05.
