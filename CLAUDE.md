<!-- markdownlint-disable MD041 -->

Last updated: 18/02/2026

### CRITICAL: Minimal Changes Philosophy
- Make the smallest change that fixes the problem. No refactors unless explicitly asked. No opportunistic "improvements". No new abstractions. No silent fallbacks without explicit approval. Prefer inline fixes to architectural changes. One fix = one narrowly scoped change. Prefer deleting parsing logic to adding more. Use regex only as a last resort and confirm first.
- Over-engineering red flags: creating classes for single functions; factories with one product; decorators that could be plain calls; abstractions without multiple concrete implementations.
- Code duplication: refactor to remove repetition only with explicit approval.

### Code Analysis and Verification
- Read the code first. Map each function's purpose and dependencies. Propose only changes you can justify from the codebase. Verify behaviour after edits. Do not guess.

### Git Commit Standards
- Commit messages contain only a technical description.
- If a task seems to require a push to complete, stop and tell the user the branch is ready locally; let them decide.

### Code Quality Standards
- Code must pass `ruff check`.
- All pytest tests must pass before calling a fix complete.
- Update TODO.md and any relevant docs when changing behaviour.

### After every 5 iterations:
1. Summarize what changed and why
2. Run the test suite
3. Flag any naming drift from the original spec

### Refactoring Guidelines
- Goal: split 1000+ line files into focused modules under 500 lines when refactoring is explicitly requested.
- Strategy: identify functional groups and extract by responsibility.
- API changes: find all usages first, update atomically, and do not mix old and new.
  - Example:
    ```
    grep -r "pattern_to_change" . --include="*.py" > migration_list.txt
    # verify old pattern removed
    grep -r "old_pattern" . --include="*.py"
    ```
- Red flags: AttributeError from incomplete lazy-load migration; import errors from missed path updates; mixed old/new patterns.
- After refactor: update test import paths, remove dead code and unused deps, migrate deprecated calls, run tests.

### YAML File Integrity
- Validate all `.yaml` changes with a linter (e.g., `yamllint`) before completion, especially under `litassist/prompts/`.

### Prompt Template Management
- Do not hardcode prompts in Python except trivial one-liners. Keep all prompts in YAML. Access via `PROMPTS.get()` with stable keys.
- Avoid dynamic f-string keys unless necessary and approved. If you must, document why and add a brief comment.

### Emoji and Terminal Output
- No emojis anywhere in the repo. ASCII only.
- Use ANSI-coloured ASCII helpers in `utils.py`: `success_message`, `warning_message`, `error_message`, `info_message`, `stats_message`, `tip_message`, `saved_message`, `verifying_message`.

### Model Name Protection
- Never change model identifiers unless explicitly asked.

### OpenRouter Usage
- Route all LLM calls through OpenRouter by default.
- When adding models/providers, try OpenRouter first. If unsupported, ask how to proceed.

### Documentation Standards
- Do not add "Recent Changes" sections. Document current behaviour only.
- When creating or substantially updating text (txt md etc) files, add or update a "Last updated: DD/MM/YYYY" header. Adding housekeeping info like this, or improving formatting are not substantial updates.

### Code Simplicity
- Prefer plain Python functions to classes for stateless work. Avoid patterns unless solving a real problem. Abstract only when you have 3+ similar implementations. Do not optimise early. If complexity is justified, confirm first.

### Backward Compatibility
- Legacy support is not required. Clean breaks are fine. Remove deprecated code decisively.

### LLM Response Processing
- Prefer prompt engineering over local parsing. Ask for structured output (JSON/YAML or clear section markers) and one minimal example if needed.
- Prefer one comprehensive call over many orchestrated calls when practical.
- No fallback parsing logic. If format is wrong, fail fast rather than masking errors. Remove regex/string parsing where prompts can enforce structure.

### Document Separation Markers
- Use only `=== NAME ===` as the separator in prompts. Do not use dashes, underscores, or asterisks. Keep marker format consistent. Do not include these markers in model output.

### Anti-Hallucination
- Never invent facts. Use explicit placeholders for missing data: `[AGE TO BE PROVIDED]`, `[ADDRESS TO BE CONFIRMED]`, `[DATE TO BE CONFIRMED]`, `[ACCOUNT NUMBER - CLIENT TO PROVIDE]`, `[EXHIBIT A]`, `[EXHIBIT B]`.
- The draft pipeline detects likely hallucinations. Placeholders are preferred over guessed specifics.

### LLM Request and Response Logging
- Log every LLM request and response in full with timestamp, model and parameters, token counts/costs, context identifiers, and errors/retries. Never truncate. Use `logging_utils.py`. Do not bypass logging in any environment.

### Australian Legal Focus
- Use Australian English spelling (e.g., "judgement"). Follow Australian precedent. Ensure citations are verifiable via Google CSE. Use DD/MM/YYYY dates.

## Testing Approach
- Pytest tests in `tests/unit/` run offline with mocked dependencies. No real API calls in pytest.
- "Integration" tests are still offline mocked interactions.
- Manual real-API checks live in `test-scripts/` and incur costs. Run manually only.
- Remove tests that no longer test meaningful behaviour.

## Configuration Management
- Required keys: OpenRouter (sole gateway for all LLM calls; provider-level BYOK for e.g. `openai/o3-pro` is configured at OpenRouter, not in this project's config) and Google CSE (Jade verification).
- Configuration precedence: environment variables, then `config.yaml`, then code defaults.
- Never edit any file named `config.yaml` via automation.

## Git Workflow
- Forbidden: `git filter-branch`, interactive rebases that rewrite history, `git reset --hard` without checking local work, and `push --force`.
- Allowed: `status`, `diff`, `log`, `branch`, `add`, `commit`. Use `gh` CLI.
- Never modify history.
- Before creating a pull request, ensure all relevant user and developer documentation has been updated to reflect the branch's behavioural changes. If any other docs are stale, propose the updates and complete them before opening the PR. Relevant docs typically include `CHANGELOG.md`, `architecture.md`, `docs/user/*.md`, `docs/development/*.md`, and `TODO.md`. Trivial fixes (typos, single-file refactors with no user-visible change) are exempt.

## Safety Compliance Check
Before any action confirm:
1) Compliance with this file. 2) Minimal changes. 3) No emojis. 4) Australian legal requirements satisfied where relevant. 5) No over-engineering.

## Performance and Cost
- Time long-running tasks, log metrics, and keep debug logs.
- Optimise API use: use HEAD for citation checks where possible, deduplicate work, and regenerate selectively.

## File Naming
- Prefix files generated by Claude with `claude_` to separate AI outputs from human-authored files.

## Development Philosophy
- Broken tests are your responsibility. Your goal is to ensure they are green. Always assume that recent codebase changes caused failures. 
- Use a common user agent for web access. Do not use odd agents blocked by sites.
- Never truncate API responses in logs.
- Do not scrape jade.io or its subdomains.
- If something fails, check code or configuration first. 

<!-- code-review-graph MCP tools -->
## MCP Tools: code-review-graph

**IMPORTANT: This project has a knowledge graph. ALWAYS use the
code-review-graph MCP tools BEFORE using Grep/Glob/Read to explore
the codebase.** The graph is faster, cheaper (fewer tokens), and gives
you structural context (callers, dependents, test coverage) that file
scanning cannot.

### When to use graph tools FIRST

- **Exploring code**: `semantic_search_nodes` or `query_graph` instead of Grep
- **Understanding impact**: `get_impact_radius` instead of manually tracing imports
- **Code review**: `detect_changes` + `get_review_context` instead of reading entire files
- **Finding relationships**: `query_graph` with callers_of/callees_of/imports_of/tests_for
- **Architecture questions**: `get_architecture_overview` + `list_communities`

Fall back to Grep/Glob/Read **only** when the graph doesn't cover what you need.

### Key Tools

| Tool | Use when |
|------|----------|
| `detect_changes` | Reviewing code changes - gives risk-scored analysis |
| `get_review_context` | Need source snippets for review - token-efficient |
| `get_impact_radius` | Understanding blast radius of a change |
| `get_affected_flows` | Finding which execution paths are impacted |
| `query_graph` | Tracing callers, callees, imports, tests, dependencies |
| `semantic_search_nodes` | Finding functions/classes by name or keyword |
| `get_architecture_overview` | Understanding high-level codebase structure |
| `refactor_tool` | Planning renames, finding dead code |

### Workflow

1. The graph auto-updates on file changes (via hooks).
2. Use `detect_changes` for code review.
3. Use `get_affected_flows` to understand impact.
4. Use `query_graph` pattern="tests_for" to check coverage.
