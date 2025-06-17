# System Patterns

## Architecture Overview

- **CLI Entry Point**: `litassist/cli.py` defines the top-level Click commands.
- **Command Modules**: Each workflow (lookup, digest, extractfacts, brainstorm, strategy, draft) lives under `litassist/commands/`.
- **Core Services**:
  - **LLM Integration** in `litassist/llm.py` with `LLMClientFactory`.
  - **Citation Validation** in `litassist/citation_patterns.py` and `litassist/citation_verify.py`.
  - **Prompt Templates** in `litassist/prompts/*.yaml`.
  - **Vector Retrieval** via Pinecone in `litassist/helpers/retriever.py` and `litassist/helpers/pinecone_config.py`.

## Pipeline Pattern

LitAssist commands form a linear pipeline:
```
Lookup → Digest → ExtractFacts → Brainstorm → Strategy → Draft
```
- **Research-Informed Brainstorm (June 2025):** The `brainstorm` command now supports a `--research` option, allowing one or more lookup report files to be provided. When used, the orthodox strategies prompt is dynamically injected with the research context, enabling research-grounded strategy generation. The unorthodox strategies remain purely creative. All prompt logic is managed via YAML templates; no LLM prompt text is hardcoded in Python.

Each stage:
1. Reads inputs (files/arguments)
2. Invokes LLM with structured prompts
3. Applies citation verification (zero‑tolerance enforcement or warnings)
4. Writes timestamped outputs in `outputs/`
5. Logs metadata and performance in `logs/`

## Verification Patterns

- **Two‑Phase Citation Control**:
  1. **Offline Validation**: Pattern‑based checks for generic names, future dates, malformed citations.
  2. **Online Verification**: HEAD requests to Jade.io/AustLII for real‑time existence checks.
- **Selective Regeneration (“Option B”)**:
  - Strategy commands regenerate or discard only the specific items with citation issues.
  - Preserves verified content and avoids manual filtering.

- **Comprehensive Post-Hoc Verification (verify command, June 2025)**:
  - `verify` command performs three checks: citation accuracy, legal soundness, and reasoning transparency.
  - Citation check reuses existing citation verification system.
  - Legal soundness check uses LLM with heavy verification prompt for Australian law compliance.
  - Reasoning transparency check extracts or generates an IRAC-structured reasoning trace (using LegalReasoningTrace if possible).
  - If no reasoning trace exists in the file, one is generated and output.
  - Each check writes a separate timestamped report to outputs/.
  - All steps use the existing logging infrastructure and minimal console output.

## Logging and Timing

- **Configuration Centralization**: `config.yaml` controls log format and verbosity.
- **@timed Decorator**: Applied to long‑running operations to record durations.
- **Audit Logs**: Stored in `logs/<command>_YYYYMMDD-HHMMSS.{json|md}` with prompts, responses, and timing.

## Design Patterns

- **Factory Pattern**: `LLMClientFactory` abstracts model configuration.
- **Decorator Pattern**: `@timed` for instrumentation.
- **Template Method**: Prompt-loading mechanism from YAML templates.
- **Strategy Pattern**: Separate reasoning‑trace modules for orthodox, unorthodox, and analysis stages.
- **Repository Pattern**: Pinecone wrapper for semantic search in a vector store.

## Prompt Management

- **YAML Prompts**: All system and user prompts stored in `litassist/prompts/`.
- **Runtime Loading**: Prompts injected into workflows based on command context.
- **Versioning**: Prompt templates updated centrally to apply improvements across commands.
