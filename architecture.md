# LitAssist Architecture

## Overview
LitAssist is a Python-based CLI tool for AI-powered litigation support in Australian law. It uses LLMs (via OpenRouter) and external search (Google CSE) to assist with legal research, document analysis, strategy generation, and drafting.

## Project Structure
```
litassist/
  cli.py                  # Click-based CLI entry point
  config.py               # Configuration loading (~/.config/litassist/config.yaml)
  citation_context.py     # Citation full-text retrieval (cache, CSE, scraping)
  citation_patterns.py    # Offline citation format validation
  verification_chain.py   # Chain of Verification (CoVe) pipeline
  commands/               # 12 command packages (each has __init__.py + core.py)
    barbrief/
    brainstorm/
    caseplan/
    counselnotes/
    digest/
    draft/
    extractfacts/
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

### 3. LLM Integration
- **Factory Pattern**: `litassist/llm/factory.py` provides `LLMClientFactory.for_command("commandname")` to create configured clients.
- **Configuration**: Model assignments in `litassist/llm/model_configs.yaml` (temperature, top_p, max_tokens per command).
- **Client**: `litassist/llm/client.py` handles API interactions via OpenRouter. Base system prompts (Australian law, anti-injection, anti-hallucination) are automatically prepended.
- **Flexibility**: Supports environment variable overrides for model selection per command.

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
- **Jina Reader**: Scraping and parsing web content into markdown (fallback for complex pages).
- **Pinecone**: Vector database (configuration present; not actively used by current commands).

## Data Flow
1. **User Input**: User runs a CLI command (e.g., `litassist extractfacts my_case.pdf`).
2. **Processing**: The command module processes the input (reads PDF, chunks if needed).
3. **LLM Interaction**: The command gets a configured client via `LLMClientFactory` and sends prompts from `litassist/prompts/`.
4. **Verification (Optional)**: If enabled, the CoVe pipeline validates generated content against authoritative sources.
5. **Output**: Results saved to `outputs/` with timestamped filenames; audit logs saved to `logs/`.
