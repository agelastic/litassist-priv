# Lookup Command Enhancement Roadmap

Last updated: 18/02/2026

## Current State (Feb 2026)

The lookup command is a modular system at `litassist/commands/lookup/` that searches Jade and AustLII via Google CSE, fetches accessible content, and synthesises results with `google/gemini-2.5-pro`.

### Implemented features

- `--mode irac|broad` -- structured IRAC analysis or wider discursive answer
- `--extract citations|principles|checklist` -- extract a specific output type via prompt engineering
- `--comprehensive` -- exhaustive analysis using up to 40 sources across Jade, AustLII, and secondary CSE
- `--context` -- additional context string appended to the query
- `--output` -- custom output filename prefix
- `--no-fetch` -- skip content fetching, analyse URLs and search snippets only
- Drop-largest truncation when content exceeds model context
- Full audit logging of every LLM request and response
- Prompt templates in `litassist/prompts/lookup.yaml`
- LLMClientFactory for centralised model configuration

### Architecture

```
__init__.py   -- CLI entry point, orchestration
search.py     -- Google CSE queries (Jade, AustLII, secondary)
fetchers.py   -- URL content fetching (HTTP, Jina Reader, PDF extraction)
processors.py -- Prompt building, LLM interaction, output saving
error_handlers.py -- User-facing error guidance
```

Configuration in `litassist/llm/model_configs.yaml` under the `lookup` key.

---

## Roadmap

### 1. Add `--min-year` filter

**Value:** Practitioners often need only recent authorities. Currently they must read through the full output to filter by date.

**Approach:** Prompt engineering only. Add a click option and append a line to the user prompt:

```
Focus on authorities from {min_year} onwards. Older cases may be cited only if they remain leading authorities.
```

**Scope:** One click option in `__init__.py`, one line in `processors.py:build_prompt()`. No schema, no parsing.

### 2. Lookup-to-verify pipeline

**Value:** After `--extract citations`, the user often wants to verify those citations are real. Today this requires manually copying them into a file and running `litassist verify`.

**Approach:** The `--extract citations` prompt already produces a clean one-citation-per-line format. The output file from lookup can be passed directly to the verify command:

```bash
litassist lookup "bail exceptional circumstances NSW" --extract citations --output bail_cases
litassist verify outputs/bail_cases_citations_*.txt
```

**What needs to happen:**
- Confirm the extraction prompt produces a format the verify command can parse (one citation per line, no bullet prefixes that break parsing)
- If needed, tighten the extraction prompt to produce bare citations without bullet characters
- Document the pipeline in LOOKUP_USE_CASES.md

**Scope:** Prompt adjustment in `lookup.yaml` (extraction_instructions.citations), possibly minor parsing tolerance in the verify command. No schema, no new classes.

### 3. Lookup-to-draft integration

**Value:** The brainstorm-to-strategy pipeline (`--strategies <file>`) proves that cross-command file-based integration works. Lookup output could feed into the draft command the same way.

**Approach:** Follow the existing pattern:

1. Add `--research <file>` option to the draft command
2. The file is a plain-text lookup output (not JSON)
3. Draft reads the file and appends it to the prompt as research context
4. No schema, no JSON interchange -- same pattern as `--strategies`

**What needs to happen:**
- Add `--research` option to `litassist/commands/draft/core.py`
- Read the file content and include it in the draft prompt as a "Research context" section
- Update draft prompt templates if needed
- Add a workflow example to LOOKUP_USE_CASES.md

**Scope:** Changes to the draft command, not lookup. Lookup output format stays as-is.

---

## Ideas evaluated and rejected

The following ideas from the original design were evaluated against the project's minimal-changes philosophy and found to be over-engineering for the current stage:

| Idea | Reason for rejection |
|------|---------------------|
| LookupResult structured schema | Requires local parsing of LLM output -- contradicts "prefer prompt engineering over local parsing" |
| LookupPostProcessor class | NLP pipeline to extract case names, courts, hierarchy from text -- exactly the regex/parsing the project rejects |
| `--format` option (text/structured/JSON) | Redundant with `--extract`; JSON output has no consumer |
| `--legal-area` with area-specific templates | LLM already adapts based on question content; `--context` handles ambiguity |
| `--court-level` filtering | Marginal value; can be achieved with `--context "focus on High Court and Federal Court authorities"` |
| `--save-for draft/strategy` with JSON | Premature without consumer-side changes; plain text integration (item 3 above) is simpler |
| `--max-cases` | Already controlled by CSE result count and model context |
| Court hierarchy ranking | Would require reliable extraction of court identifiers -- parsing problem |
| Relevance scoring | LLM already ranks by relevance in its output; numeric scores add false precision |

These ideas are not inherently bad -- they are premature. If the three roadmap items above prove their value, some of these could be revisited.

---

## Design principles

Any enhancement to lookup must satisfy:

1. **Prompt engineering over local parsing** -- ask the LLM for the right format, do not parse its output into structures
2. **Fail fast** -- if the output format is wrong, surface it; do not add fallback parsing
3. **File-based integration** -- follow the brainstorm-to-strategy pattern (plain text via click.File)
4. **No new abstractions** -- no result schemas, no manager classes, no post-processing pipelines
5. **One change at a time** -- each item above is independently useful and independently shippable
