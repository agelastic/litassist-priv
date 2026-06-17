# LitAssist Architecture

Last updated: 17/06/2026

## Overview
LitAssist is a Python-based CLI tool for AI-powered litigation support in Australian law. It uses LLMs (via OpenRouter) and external search (Google CSE) to assist with legal research, document analysis, strategy generation, and drafting.

## Sources of Truth
- Command registration: `litassist/commands/__init__.py`
- Model assignments: `litassist/llm/model_configs.yaml`
- Strategic feature roadmap: `ROADMAP.md`
- Active bugs, technical debt, and reliability work: `TODO.md`

## Project Structure
```
litassist/
  cli.py                  # Click-based CLI entry point
  config.py               # Configuration loading (~/.config/litassist/config.yaml)
  citation_context.py     # Citation full-text retrieval (cache, CSE, scraping)
  citation_patterns.py    # Offline citation format validation
  verification_chain.py   # Chain of Verification (CoVe) pipeline
  commands/               # 12 user-facing command packages (each has __init__.py + core.py)
    barbrief/
    brainstorm/
    caseplan/
    counselnotes/
    digest/
    draft/
    extractfacts/
    updatefacts/
    lookup/
    strategy/
    verify/
    verify_cove/
  citation/               # Citation verification package (verify, cache, google_cse, austlii, legislation)
  llm/                    # LLM client package (factory, client, model_configs.yaml, api_handlers)
  logging/                # Logging package (task_events, config, json_utils, markdown_writers)
  prompts/                # YAML prompt templates (base, strategies, verification, barbrief, etc.)
  utils/                  # Shared utilities (file_ops, legal_reasoning, message formatting)
setup.py                  # Package installation (v1.0.0)
requirements.txt          # Python dependencies
```

## Core Components

### 1. CLI Entry Point
- Defined in `litassist/cli.py` using `click`.
- Handles global configuration, logging, and API credential validation.
- Dispatches commands to submodules in `litassist/commands/`.

### 2. Command Modules
Commands are organised as packages in `litassist/commands/`. Each command has:
- `__init__.py`: Registers the command with the CLI.
- `core.py`: Main logic.
- Helper modules as needed (e.g., `brainstorm/` has `orthodox_generator.py`, `unorthodox_generator.py`, `analysis_generator.py`, `citation_regenerator.py`).

The 12 registered user-facing commands are: `lookup`, `digest`, `extractfacts`, `updatefacts`, `brainstorm`, `strategy`, `draft`, `verify`, `verify-cove`, `counselnotes`, `barbrief`, and `caseplan`.

### 3. LLM Integration
- **Factory Pattern**: `litassist/llm/factory.py` provides `LLMClientFactory.for_command("commandname")` to create configured clients.
- **Configuration**: Model assignments in `litassist/llm/model_configs.yaml` (temperature, top_p, max_tokens per command).
- **Client**: `litassist/llm/client.py` handles API interactions via OpenRouter. Base system prompts (Australian law, anti-injection, anti-hallucination) are automatically prepended.
- **Current model families**: The active model configuration includes `anthropic/claude-sonnet-4.6`, `anthropic/claude-opus-4.7`, `openai/gpt-5.5`, `openai/o3-pro`, `google/gemini-3.5-flash`, and `x-ai/grok-4.20`. Older model references in historical changelog sections are not current-state configuration.

### 4. Citation Handling & Verification
- **Offline Validation**: `litassist/citation_patterns.py` validates citation format (pattern matching, no network).
- **Online Verification**: `litassist/citation/` package verifies citations against AustLII and Jade.io via Google CSE.
- **Citation Context**: `litassist/citation_context.py` fetches full text for citations (cache first, then CSE, then scraping).
- **Chain of Verification (CoVe)**: `litassist/verification_chain.py` implements a four-stage factored verification:
    1. **Generate Questions**: LLM generates verification questions from content.
    2. **Answer Questions**: LLM answers using fetched authoritative text.
    3. **Detect Inconsistencies**: LLM compares answers to original content.
    4. **Regenerate**: LLM corrects content if inconsistencies found.

### 5. Logging
- `litassist/logging/` package with `log_task_event()` as the primary API.
- Every LLM call logged with timestamp, model, parameters, token counts, and costs.
- Command outputs saved to `outputs/`; audit logs saved to `logs/`.

## External Integrations
- **OpenRouter**: Primary API gateway for all LLM calls (Claude, GPT, Gemini, Grok, o3-pro).
- **Google Custom Search Engine (CSE)**: Retrieves legal documents from Jade.io and AustLII.
- **curl_cffi**: Primary content-fetch transport with Chrome 136 TLS impersonation. Defeats Cloudflare TLS fingerprint detection for HTML responses on AustLII and similar protected hosts. Direct `requests` is not used for content fetching.
- **Jina Reader**: Fallback transport used by `litassist/commands/lookup/fetchers.py` when curl_cffi returns a Cloudflare challenge body, a JavaScript SPA shell, or non-HTML content. Also serves `ndfv.jade.io` URLs directly. Never dispatched to austlii.edu.au hosts (AustLII always Cloudflare-challenges Jina's datacentre IPs; guarded since 11/06/2026). Narrower role since the May 2026 fetcher rework (see CHANGELOG).

### Lookup fetcher chain
The fetcher in `litassist/commands/lookup/fetchers.py` runs every URL through a single generic pipeline:

1. Local file path → `read_document` (handles PDF via pdfplumber, RTF via `litassist/utils/rtf.py`, text directly).
2. `jade.io` main domain → skipped; `ndfv.jade.io` subdomain → Jina with `/download` URL rewrite.
3. AustLII `*.pdf` URL → rewritten to `.html` sibling before HTTP (AustLII Cloudflare policy blocks PDF paths for all tested Python clients).
4. AustLII rate limit → 2–3 s random delay between requests.
5. `curl_cffi` GET with Chrome 136 TLS impersonation.
6. Magic-byte routing: PDF → `_extract_pdf_text` (pdfplumber); RTF → `_extract_rtf_text` (striprtf).
7. Content-Type guard: non-text payloads route to Jina rather than passing through to BS4.
8. legislation.gov.au `/latest/text` → follow the OEBPS document link via curl_cffi.
9. BS4 text extraction (strip scripts/styles/meta/link/noscript).
10. Detection: Cloudflare challenge markers (`_looks_like_challenge_page`), SPA shell (`_looks_like_spa_shell`), or gibberish (text < 100 chars) → Jina fallback (not for austlii.edu.au hosts, which are guarded out of the Jina path).
11. Otherwise return cleaned text.

## Data Flow
1. **User Input**: User runs a CLI command (e.g., `litassist extractfacts my_case.pdf`).
2. **Processing**: The command module processes the input (reads PDF, chunks if needed).
3. **LLM Interaction**: The command gets a configured client via `LLMClientFactory` and sends prompts from `litassist/prompts/`.
4. **Verification (Optional)**: If enabled, the CoVe pipeline validates generated content against authoritative sources.
5. **Output**: Results saved to `outputs/` with timestamped filenames; audit logs saved to `logs/`.

`caseplan` emits a **Python runner** (not a bash script) so that each EXECUTION is fully isolated. `caseplan/command_extractor.py` builds a runner that, when run, creates a fresh `outputs/run_<timestamp>/` directory, sets `LITASSIST_OUTPUT_DIR` (inherited by each `subprocess.run(args, shell=False)` step), and rewrites every `outputs/...` and `case_facts` argument to `os.path.join(run_dir, ...)`. `save_command_output` (the single output write sink), `updatefacts`, and `resolve_case_facts_file` all honour `LITASSIST_OUTPUT_DIR`, so a run's outputs and case_facts are written and read inside its own directory; a supplied cwd `case_facts*.md` is copied in as a seed and the cwd original is never mutated. These hooks are env-gated, so normal single-command use is unaffected, and retries (re-running the same runner) get a brand-new directory rather than mixing with the prior attempt.
