# Architecture Review: Python Code and YAML

Last updated: 05/06/2026

## Scope and Method

This review examines **only** Python source and YAML files. No documentation, Markdown (other than this deliverable), or non-code artefacts were used as evidence.

Exploration used **code-review-graph MCP tools first** (`get_architecture_overview`, `list_communities`, `list_flows`, `list_graph_stats`, `find_large_functions`, `get_hub_nodes`, `get_bridge_nodes`, `get_knowledge_gaps`, `semantic_search_nodes`, `query_graph`, `get_flow`), with targeted reads of key modules only where the graph could not answer structural questions.

---

## 1. Architecture Review

### 1.1 System purpose (from code structure)

LitAssist is a **Click-based CLI** (`litassist/cli.py`) that registers **14 commands** (`litassist/commands/__init__.py`): lookup, digest, brainstorm, extractfacts, updatefacts, draft, strategy, verify, verify_cove, counselnotes, barbrief, caseplan, refresh.

Each command is a workflow that typically:

1. Reads legal documents (utils/file_ops, command-specific readers)
2. Builds prompts from YAML via `PromptManager` (`litassist/prompts.py`)
3. Calls an LLM through `LLMClient` / `LLMClientFactory` (OpenRouter gateway)
4. Optionally runs citation verification (`litassist/citation/`, `verification_chain.py`)
5. Logs full request/response audit trails (`litassist/logging/`)
6. Writes outputs under `outputs/` in the working directory

Australian legal focus is enforced in YAML (`litassist/prompts/base.yaml`) and injected in `LLMClient._prepare_messages_for_model`.

### 1.2 Layered structure

| Layer | Location | Role |
|-------|----------|------|
| CLI / config | `cli.py`, `config.py` | Entry, lazy config load, credential checks, global options |
| Commands | `litassist/commands/*/` | Per-workflow orchestration; many `core.py` entry functions |
| LLM spine | `llm/client.py`, `factory.py`, `api_handlers.py`, `parameter_handler.py`, `verification.py` | Single completion path, retries, model params, citation enforcement |
| Policy (YAML) | `litassist/prompts/*.yaml`, `llm/model_configs.yaml`, `llm/model_capabilities.yaml` | Prompts, per-command models, capabilities/budgets |
| Citation | `citation/`, `citation_context.py`, `citation_patterns.py` | Extraction, CSE/AustLII verification, context fetch for lookup |
| Cross-cutting | `logging/`, `utils/` | Audit logs, terminal messages, truncation, file I/O |
| Verification orchestration | `verification_chain.py`, `utils/legal_reasoning.py` | Multi-stage verify for extractfacts/strategy/draft |

Inheritance is minimal (13 `INHERITS` edges in the graph). Design is **function- and composition-heavy**: `LLMClient` uses `LLMVerificationMixin`; commands call factories and helpers rather than deep class trees.

### 1.3 Graph statistics (Python)

| Metric | Value |
|--------|-------|
| Files | 188 |
| Nodes | 1,416 (516 functions, 147 classes, 565 tests) |
| Edges | 13,113 (8,145 CALLS, 2,590 TESTED_BY) |
| Communities | 12 (directory-based Leiden grouping) |

### 1.4 Communities and cohesion

Production-relevant Python communities (bash `release-check` excluded):

| Community | Size | Cohesion | Dominant path |
|-----------|------|----------|----------------|
| unit-command | 652 | 0.13 | `tests/unit/` |
| lookup-extract | 134 | **0.05** | `litassist/commands/` (all commands in one bag) |
| llm-retry | 50 | 0.08 | `litassist/llm/` |
| utils-message | 46 | **0.06** | `litassist/utils/` |
| litassist-validate | 45 | 0.10 | `prompts.py`, `timing.py` |
| logging-write | 18 | **0.01** | `litassist/logging/` |
| citation-citation | 15 | 0.04 | `litassist/citation/` |

**Low cohesion** in `lookup-extract`, `logging-write`, and `utils-message` indicates commands do not form a tight internal module; they share the same spine (prompts, factory, client, logging, formatting).

### 1.5 Cross-community coupling (warnings from graph)

| Source | Target | CALLS edges |
|--------|--------|-------------|
| lookup-extract (commands) | logging-write | **56** |
| lookup-extract | utils-message | **37** |
| llm-retry | utils-message | **14** |

Commands are wired as **consumers of pervasive aspect modules**, not as a domain core with stable inward APIs.

### 1.6 Execution flows (by criticality)

Highest-criticality flows are **verification and citation**, not document generation alone:

1. `verify_citations_if_requested` (0.82)
2. `validate_and_verify_citations` (0.81)
3. `run_verification_chain` (0.79)
4. `verify_citations` / `run_verification_workflow` (0.75–0.78, up to 32 nodes)
5. `execute_cove_pipeline`, `verify_reasoning`, `verify_soundness`
6. Content commands: `brainstorm`, `strategy`, `draft`, `extractfacts`, `digest`, `lookup`

Typical command flows (e.g. `brainstorm`, 21 nodes) immediately fan out to `log_task_event`, `save_log`, and multiple `utils/formatting.py` helpers.

### 1.7 Architectural hotspots (hubs)

| Symbol | File | Total degree | Notes |
|--------|------|--------------|-------|
| `log_task_event` | `logging/__init__.py` | **184** | Re-export of `task_events.log_task_event`; 183 inbound |
| `_fetch_url_content` | `lookup/fetchers.py` | 128 | Single function in **1,235-line** file |
| `strategy` | `commands/strategy/core.py` | 127 | 463-line entry function |
| `save_log` | `logging/__init__.py` | 124 | 86 inbound callers |
| `run_cove_verification` | `verification_chain.py` | 117 | Inside 619-line module |
| `get_model_parameters` | `llm/parameter_handler.py` | 108 | Bridge between YAML configs and API payload |
| `brainstorm` / `digest` | command `core.py` files | 106 / 101 | Large orchestrators |
| `LLMClient.complete` | `llm/client.py` | 89 | 50+ callers; 10 direct unit tests |

### 1.8 Bridges (betweenness)

`get_model_parameters`, `LLMClient`, `save_log`, and `fetch_citation_context` sit on many shortest paths between commands and infrastructure. Changes there affect most workflows.

### 1.9 YAML as policy layer

**Three explicit YAML load sites in Python:**

1. **`litassist/prompts.py`** — `PromptManager` merges all `litassist/prompts/*.yaml` (14 files: base, analysis, barbrief, caseplan, capabilities, documents, formats, lookup, processing, reasoning, strategies, system_feedback, verification, etc.). Access via `PROMPTS.get()` / `get_system_prompt()`.
2. **`litassist/config.py`** — user `config.yaml` (API keys, limits); not in repo; template only.
3. **`litassist/llm/factory.py`** — `model_configs.yaml` (~30 command/sub-command keys), `model_capabilities.yaml` (refreshed by `litassist refresh`).

**Enforcement in tests:** `test_prompt_validation.py`, `test_prompt_templates.py`, `test_yaml_prompt_validation.py`, `test_model_config_integrity.py`, `test_model_config_sampling.py`, `test_thinking_effort.py`.

`model_configs.yaml` documents that lookup sub-modes (`lookup-irac`, `lookup-broad`) must stay in YAML, not Python (`processors.py` resolves sub-type via factory).

### 1.10 Command module pattern

Most commands follow a repeated shape:

- `commands/<name>/core.py` — Click handler and orchestration (often 200–500+ lines)
- Supporting modules — generators, processors, readers, chunkers
- `LLMClientFactory.for_command(...)` for model selection
- `PROMPTS.get(...)` for templates
- `log_task_event` / `save_log` throughout

**Chunking** appears in digest, extractfacts, counselnotes (single vs multi extractors/processors).

**Lookup** is the outlier in size: `fetchers.py` (1,235 LOC), `processors.py` (575 LOC), with PDF/OCR/RTF/Jina/AustLII URL rewriting and trusted-host logic.

### 1.11 Citation subsystem

`litassist/citation/` modules:

- `verify.py` — orchestration (`verify_single_citation`, `verify_all_citations`)
- `google_cse.py`, `austlii.py`, `legislation.py`, `trust.py`, `cache.py`, `exceptions.py`

Top-level `citation_context.py` (717 LOC) and `citation_patterns.py` support lookup and offline pattern checks. `verification_chain.py` chains pattern check → database verify → context fetch → LLM verification stages.

### 1.12 LLM client pipeline

```
LLMClientFactory.for_command(name)
  → LLMClient.complete(messages)
      → _prepare_messages_for_model (base YAML prompts, date/tool rules)
      → execute_api_call_with_retry (api_handlers.py)
      → extract_content_and_usage
      → optional process_citation_verification / handle_citation_retry
```

`parameter_handler.py` maps universal knobs (`thinking_effort`, `verbosity`) to OpenRouter payloads using `model_profiles.MODEL_PATTERNS` and `PARAMETER_PROFILES`.

### 1.13 Testing architecture (from graph)

- **565 test nodes**; `tests/unit/` is the largest community (652 nodes including nested helpers).
- **2,590 TESTED_BY edges** — good coverage density on many modules.
- **Gaps:** `log_task_event`, `get_model_parameters`, `run_cove_verification`, and several command entry functions are flagged as **untested hotspots** (degree high, few or no direct `tests_for` — command cores are often tested via integration-style tests that mock at factory/client level).
- `verification_chain.py` has **0** `tests_for` edges on the file node; behaviour is covered indirectly via `verify_content_if_needed` mocks in `test_utils_comprehensive.py`.
- **test-scripts/** — manual/real-API scripts (e.g. `test_quality.py` 1,079 LOC); separate from offline pytest.

### 1.14 Static analysis blind spot

Command entry functions (`strategy`, `brainstorm`, `digest`, etc.) show **0 `callers_of`** in the graph because registration is dynamic:

```python
# commands/__init__.py
cli.add_command(strategy.strategy)
```

Only `register_commands(cli)` → `cli.main` links the CLI group. Impact/dead-code tools under-count command surface area unless registration is made explicitly referential in code.

### 1.15 Large files (production, ≥500 LOC)

| File | LOC | Concern |
|------|-----|---------|
| `commands/lookup/fetchers.py` | 1,235 | Fetch pipeline monolith |
| `commands/brainstorm/core.py` | 819 | Command orchestration |
| `citation_context.py` | 717 | Citation context fetch |
| `verification_chain.py` | 619 | CoVe + chain |
| `commands/lookup/processors.py` | 575 | Lookup orchestration |
| `llm/api_handlers.py` | 564 | Retry/streaming |
| `llm/client.py` | 560 | Completion + verification hooks |

---

## 2. Key Architectural Insights

1. **YAML + six Python modules form the real “platform”.** Prompt text, model choice, thinking effort, and API keys flow from YAML into `PromptManager`, `LLMClientFactory`, and `Config`. Almost every command imports these; the graph shows commands as a thin, low-cohesion shell around a shared spine.

2. **Logging is the highest fan-in hub, not the LLM.** `log_task_event` (degree 184) and `save_log` (124) absorb more structural dependency than any single legal-domain function. Auditability is a first-class architectural constraint, but it scatters across 77+ importers of `logging/__init__.py`.

3. **Verification paths dominate criticality.** The top execution flows are citation/CoVe/soundness/reasoning checks. Product risk concentrates in `verification_chain.py` and `commands/verify/*`, not only in draft generation.

4. **Lookup fetch is a separate “subsystem” inside one file.** `_fetch_url_content` and helpers in `fetchers.py` encode AustLII, legislation.gov.au, PDF/OCR, Jina, content-type guards, and challenge detection — with **128** internal call graph degree in one function. This is the primary maintainability hotspot in production code.

5. **Model parameter routing is the main bridge.** `get_model_parameters` / `get_model_family` / `convert_thinking_effort` centralise provider-specific behaviour. Typos in `model_configs.yaml` are guarded by `test_model_config_integrity.py`; runtime behaviour still depends on long branching in `parameter_handler.py`.

6. **Dual verification entry points.** Commands use `verify_content_if_needed` (`utils/legal_reasoning.py`) for extractfacts/strategy/draft; standalone `verify` and `verify_cove` commands have their own pipelines. Shared concepts (citations, prompts) but separate orchestration paths — worth knowing when changing verify behaviour.

7. **Prompt/command coupling is partially machine-checked.** Regex-based `test_prompt_validation.py` lists command files and asserts `PROMPTS.get("...")` keys exist. Adding a new command requires updating that list manually — a measurable gap when commands grow.

8. **Test mass mirrors production layout but obscures hub risk.** Huge `test_*_comprehensive.py` files test behaviour end-to-end while graph marks spine functions as “untested” because tests mock at factory boundaries. Coverage exists; **structural** test linkage to hubs is weak.

9. **Isolated/low-link symbols are real but small.** Graph reports 31 isolated nodes (e.g. `citation/cache.add_to_cache` only called from verify path, `TruncationManager.get_dropped`). Some are test-only or emergency-handler APIs — not all are dead code.

10. **Stale graph communities.** `helpers-pinecone` (17 nodes, cohesion 0.24) has no matching `litassist/helpers/` directory in the tree — likely obsolete graph grouping; do not treat as active architecture.

---

## 3. Recommendations (measurable impact)

Recommendations are ordered by **graph-measurable** leverage: degree, coupling edge counts, LOC, and test gaps. Avoid generic “best practices.”

### R1. Split `lookup/fetchers.py` by responsibility

**Target:** 1,235 LOC file; `_fetch_url_content` 430 LOC, degree 128.

**Action:** Extract modules by mechanism (e.g. `fetch_http.py`, `fetch_pdf_ocr.py`, `fetch_jina.py`, `austlii_urls.py`) with `_fetch_url_content` as a thin coordinator.

**Measurable impact:**

- Reduces largest production file below 500 LOC (project refactor guideline).
- Lowers per-function degree concentration; improves `find_large_functions` and hub rankings for `_fetch_url_content`.
- Enables focused unit tests per fetch strategy (today most coverage is via `test_lookup_*` integration tests).

**Success metric:** No production file in `litassist/` above 600 LOC; `_fetch_url_content` under 150 LOC.

---

### R2. Add direct unit tests for top untested hubs

**Targets (from `get_knowledge_gaps` / hub list, 0 or weak `tests_for`):**

| Function | Degree | Current tests_for |
|----------|--------|-------------------|
| `log_task_event` | 184 | 0 direct |
| `get_model_parameters` | 108 | 0 direct |
| `run_cove_verification` | 117 | 0 direct |
| `run_verification_workflow` | 59 | indirect only |

**Action:** Small tests asserting payload shape, file write paths, short-circuit flags, and parameter mapping for one model per family — no live API.

**Measurable impact:**

- Increases TESTED_BY edges on nodes with highest in-degree.
- Reduces `untested_hotspots` count (currently 20).
- Lowers regression risk on the 56 + 37 cross-community logging/utils edges.

**Success metric:** `query_graph tests_for` returns ≥3 tests each for `log_task_event`, `get_model_parameters`, and `run_cove_verification`; `untested_hotspots` &lt; 12.

---

### R3. Introduce a narrow `CommandReporter` facade for logging + terminal output

**Target:** 56 CALLS (commands → logging) + 37 CALLS (commands → utils formatting).

**Action:** One module (e.g. `litassist/command_output.py`) exposing `event()`, `saved()`, `verify_status()` that delegates to `log_task_event` and formatting helpers. Migrate commands incrementally (start with verify + digest).

**Measurable impact:**

- Drops raw cross-community CALLS edge counts in a re-run of `get_architecture_overview`.
- Raises `logging-write` community cohesion above 0.05.
- Single place to change audit vs user-visible output behaviour.

**Success metric:** lookup-extract → logging-write edges reduced by ≥30%; command files import one facade instead of 5+ formatting functions.

---

### R4. Make command registration graph-visible

**Target:** All command cores show 0 `callers_of`; dead-code detection false positives.

**Action:** In `commands/__init__.py`, define `COMMAND_REGISTRY: list[tuple[str, click.Command]]` with explicit references to each `*.strategy`, `*.brainstorm`, etc., and loop in `register_commands`.

**Measurable impact:**

- Adds stable IMPORTS/CALLS edges from `register_commands` to each command entry.
- Improves `detect_changes` / `get_impact_radius` when editing a command signature.
- Removes command entries from `refactor_tool` dead_code suggestions.

**Success metric:** `callers_of` for `strategy` shows `register_commands`; dead_code list no longer flags active command entrypoints.

---

### R5. Extend prompt validation coverage to match factory commands

**Target:** `test_prompt_validation.py` lists 17 command files; `model_configs.yaml` has ~30 keys including sub-commands (`lookup-irac`, `cove-answers-heavy`, etc.).

**Action:**

1. Generate command file list from `commands/__init__.py` registry (R4).
2. Add test that every `LLMClientFactory.for_command` string has a `model_configs.yaml` key (mirror `test_model_config_integrity.py`).

**Measurable impact:**

- Catches missing YAML keys at CI time (KeyError currently at runtime).
- Reduces manual list drift in `COMMAND_FILES`.

**Success metric:** Zero factory command strings without YAML entry; prompt validation file list auto-derived (no hand-maintained paths).

---

### R6. Decompose `verification_chain.run_cove_verification` without changing CLI contract

**Target:** 472 LOC function inside 619 LOC file; criticality 0.75+ flows.

**Action:** Extract stage functions (`_stage_patterns`, `_stage_database`, `_stage_context`, `_stage_llm_verify`) with shared `results` dict; keep `run_cove_verification` signature.

**Measurable impact:**

- Enables R2 tests per stage.
- Reduces largest-function LOC in verification path.
- Clearer mapping from flow steps to code units in `get_flow` output.

**Success metric:** No function in `verification_chain.py` above 120 LOC; ≥4 new stage-level tests.

---

### R7. Confirm and remove true dead symbols (graph-isolated, no tests, no callers)

**Candidates from `get_knowledge_gaps` (verify before delete):** `Colors` class if unused, duplicate prompt builders, `add_to_cache` only if cache never written in practice, `get_tool_definitions` if tools disabled for all configured commands.

**Action:** Run `refactor_tool` dead_code mode + `callers_of` per symbol; delete only with pytest green.

**Measurable impact:**

- Reduces isolated node count (31 → target &lt; 15).
- Shrinks noise in hub/dead-code reports.

**Success metric:** `list_graph_stats` node count decreases; `ruff check` and full pytest pass.

---

## 4. Re-analysis checklist

After implementing recommendations, re-run:

- `get_architecture_overview_tool` — coupling warnings and community cohesion
- `get_knowledge_gaps_tool` — untested_hotspots and isolated_nodes counts
- `find_large_functions_tool` — files/functions over thresholds
- `get_hub_nodes_tool` — degree redistribution off monoliths

Document deltas in the same metrics tables above to prove impact.

---

## Appendix: Command registry (from code)

| Command | Primary module |
|---------|----------------|
| lookup | `commands/lookup/__init__.py` |
| digest | `commands/digest/core.py` |
| brainstorm | `commands/brainstorm/core.py` |
| extractfacts | `commands/extractfacts/core.py` |
| updatefacts | `commands/updatefacts/core.py` |
| draft | `commands/draft/core.py` |
| strategy | `commands/strategy/core.py` |
| verify | `commands/verify/core.py` |
| verify_cove | `commands/verify_cove/core.py` |
| counselnotes | `commands/counselnotes/core.py` |
| barbrief | `commands/barbrief/core.py` |
| caseplan | `commands/caseplan/core.py` |
| refresh | `commands/refresh/__init__.py` |