---
name: Refactor Safely
description: Plan and execute safe refactoring using dependency analysis
---

## Refactor Safely

Use the knowledge graph to plan and execute refactoring with confidence.

### Steps

1. Use `refactor_tool` with mode="suggest" for community-driven refactoring suggestions.
2. Use `refactor_tool` with mode="dead_code" to find unreferenced code.
3. For renames, use `refactor_tool` with mode="rename" to preview all affected locations.
4. Use `apply_refactor_tool` with the refactor_id to apply renames.
5. After changes, run `detect_changes` to verify the refactoring impact.

### Safety Checks

- Always preview before applying (rename mode gives you an edit list).
- Check `get_impact_radius` before major refactors.
- Use `get_affected_flows` to ensure no critical paths are broken.
- Run `find_large_functions` to identify decomposition targets.

## Large-file decomposition

CLAUDE.md sets a target of <500 lines per file after refactoring. Use this workflow when splitting a file that exceeds it.

### Steps

1. **Surface candidates.** Run `find_large_functions(min_lines=400)` to get the current oversized files. Do not work from a hard-coded list — counts shift with each refactor.

2. **Map internal call clusters.** For a candidate file, call `query_graph` with `pattern="callers_of"` and `pattern="callees_of"` for each top-level function and class. Look for clusters that call each other heavily but call out to the rest of the file rarely — those are natural module boundaries.

3. **Check blast radius before deciding the split.** `get_impact_radius` on each function in the candidate file. If a function has wide impact (many transitive callers across communities), keep it where consumers expect to find it.

4. **Propose splits.** Run `refactor_tool` with `mode="suggest"`; community detection often agrees with the call-cluster boundaries from step 2. If the suggestion conflicts with step 2, prefer the call-cluster boundary — community detection can be coarse.

5. **Atomic migration per CLAUDE.md:25.** Before moving any code: grep for every usage of the symbols you intend to move. Apply file moves + import-site updates in the same commit. Do NOT leave a backwards-compat re-export shim unless explicitly asked.

6. **Verify.** After the split: run `detect_changes` and `get_affected_flows` to confirm no flow regressed, then `pytest -q` and `ruff check`.

### Pitfalls observed in this codebase

- Functions decorated with `@timed` or `@heartbeat()` use `functools.wraps`. After moving, the `__wrapped__` chain (and `tests/unit/test_llm_complete.py::test_heartbeat_and_timed_decorators`) depend on the decorator-import order. Keep both decorators on the moved function in the same order.
- `log_task_event` has 170+ call sites. If a moved function logged, it MUST keep logging from its new home — see the log-coverage hook.
- Model-identifier strings in YAML and config are bridge data. Use `query_graph` to find every reference before changing one.

## Token Efficiency Rules
- ALWAYS start with `get_minimal_context(task="<your task>")` before any other graph tool.
- Use `detail_level="minimal"` on all calls. Only escalate to "standard" when minimal is insufficient.
- Target: complete any review/debug/refactor task in ≤5 tool calls and ≤800 total output tokens.
