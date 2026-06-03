# Counsel's Notes Command -- Technical Implementation

Last updated: 19/02/2026

## Overview

The `counselnotes` command generates strategic analysis and structured extractions from legal documents using an advocate's perspective. It complements the neutral analysis provided by the `digest` command.

Model: `openai/o3-pro` via OpenRouter with `thinking_effort: high`. Configuration in `litassist/llm/model_configs.yaml` under the `counselnotes` key.

## Command Signature

```
litassist counselnotes FILES [OPTIONS]
```

| Argument/Option | Type | Description |
|-----------------|------|-------------|
| `FILES` | paths (required, multiple) | One or more document files (PDF or text) |
| `--extract` | `all\|citations\|principles\|checklist` | Structured extraction mode. Omit for strategic analysis. |
| `--verify` | flag | Enable citation pattern validation after LLM response |
| `--output` | string | Custom output filename prefix |

No `--heavy` or `--noverify` flags.

## Module Architecture

```
litassist/commands/counselnotes/
  __init__.py              -- exports the click command
  core.py                  -- orchestration: reads files, routes to mode, saves output
  document_processor.py    -- read_and_consolidate_documents(), prepare_chunks()
  extraction_processor.py  -- process_extraction_mode(), consolidate_extraction_results()
  analysis_processor.py    -- analyze_single_chunk(), analyze_multiple_chunks(), process_strategic_analysis()
  consolidator.py          -- consolidate_analyses()
```

## Processing Workflow

### Document Phase

1. `read_and_consolidate_documents(files)` reads each file via `read_document()` and wraps each with `=== DOCUMENT: {filename} ===` markers. Returns combined content and file metadata.

2. `prepare_chunks(content)` checks content length against `config.max_chars`. If exceeded, chunks text via `chunk_text()` and sets mode to "chunked". Otherwise uses a single chunk with mode "unified".

### Routing

The command branches based on `--extract`:

- **With `--extract`**: routes to `process_extraction_mode()`
- **Without `--extract`**: routes to `process_strategic_analysis()`

### Extraction Mode

`process_extraction_mode()` iterates over chunks with a progress bar. For each chunk:

1. Gets the prompt via `PROMPTS.get(f"processing.counselnotes.extraction.{extract}", documents=chunk)`
2. Calls `client.complete()` with the system prompt and extraction prompt
3. If `--verify`: calls `client.validate_citations()` and displays warnings to CLI

Results are joined by `consolidate_extraction_results()`. Multiple chunks are separated with `---` dividers and a consolidation header.

Extraction output is plain text with section headers (e.g. `CITATIONS FOUND:`, `LEGAL PRINCIPLES:`, `PRACTICAL CHECKLIST:`), not JSON.

### Strategic Analysis Mode

`process_strategic_analysis()` dispatches based on chunk count:

**Single chunk (unified mode):**
- `analyze_single_chunk()` calls `client.complete()` with the `strategic_analysis` prompt
- If `--verify`: validates citations and prepends a `--- CITATION WARNINGS ---` block if issues found
- Returns content directly, no consolidation needed

**Multiple chunks:**
- `analyze_multiple_chunks()` processes each chunk with the `chunk_analysis` prompt (includes chunk number and total for context)
- Returns list of partial analyses, flagged for consolidation

**Consolidation:**
- `consolidate_analyses()` wraps each partial analysis with `=== ANALYSIS FROM DOCUMENT SECTION N ===` markers
- Calls `client.complete()` with the `consolidation` prompt to synthesise into unified counsel's notes
- If `--verify`: validates citations on the final consolidated output

## Prompt Templates

All prompts are in `litassist/prompts/processing.yaml` under `processing.counselnotes`:

| Key | Purpose | Parameters |
|-----|---------|------------|
| `system_prompt` | System prompt for all modes | None |
| `strategic_analysis` | Full document strategic analysis | `{documents}` |
| `chunk_analysis` | Partial analysis of a single chunk | `{documents}`, `{chunk_num}`, `{total_chunks}` |
| `consolidation` | Synthesise chunk analyses into final notes | `{chunk_analyses}`, `{total_chunks}` |
| `extraction.all` | Extract all counsel's notes elements | `{documents}` |
| `extraction.citations` | Extract citations only | `{documents}` |
| `extraction.principles` | Extract legal principles with authorities | `{documents}` |
| `extraction.checklist` | Extract tactical checklist items | `{documents}` |

## Verification Behaviour

- `--verify` calls `client.validate_citations()` -- pattern-based offline checking, not database lookup
- `enforce_citations: false` in model config -- no automatic LLM retry on citation format errors
- In strategic analysis mode: citation warnings are prepended to output as a `--- CITATION WARNINGS ---` block
- In extraction mode: citation warnings are displayed to CLI only (not included in output)

## Output

Uses `save_command_output()` from `litassist/logging`. Output files include a metadata header:

```
Mode: Strategic Analysis | Extraction (citations|principles|all|checklist)
Documents Analyzed: file1.pdf, file2.pdf
Processing Mode: unified | chunked
Extraction Type: all | citations | principles | checklist | None
Citation Verification: Enabled | Disabled
```

Filename pattern: `{prefix}_{slug}_{timestamp}.txt` saved to the `outputs/` directory.

Audit logging via `save_log()` captures file paths, extraction mode, verification status, processing mode, chunk count, and token usage.
