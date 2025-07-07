# System Patterns

## Architecture Overview

- **CLI Entry Point**: `litassist/cli.py` defines the top-level Click commands.
- **Command Modules**: Each workflow (lookup, digest, extractfacts, brainstorm, strategy, draft, counselnotes, barbrief) lives under `litassist/commands/`.
- **Core Services**:
  - **LLM Integration** in `litassist/llm.py` with `LLMClientFactory`.
  - **Citation Validation** in `litassist/citation_patterns.py` and `litassist/citation_verify.py`.
  - **Prompt Templates** in `litassist/prompts/*.yaml`.
  - **Vector Retrieval** via Pinecone in `litassist/helpers/retriever.py` and `litassist/helpers/pinecone_config.py`.

## Pipeline Pattern

LitAssist commands form a linear pipeline:
```
Lookup → Digest → ExtractFacts → Brainstorm → Strategy → Draft → Barbrief
                                                          ↘
                                                        CounselNotes
```
- **Digest Command Hinting (June 2025):** The `digest` command now supports an optional `--hint` argument, allowing users to provide a text hint to focus LLM analysis on topics related to the hint. This enables targeted processing of non-legal and general documents.
- **Research-Informed Brainstorm (June 2025):** The `brainstorm` command now supports a `--research` option, allowing one or more lookup report files to be provided. When used, the orthodox strategies prompt is dynamically injected with the research context, enabling research-grounded strategy generation. The unorthodox strategies remain purely creative. All prompt logic is managed via YAML templates; no LLM prompt text is hardcoded in Python.
- **Multiple Input Files (July 2025):** The `extractfacts` command now accepts multiple input files via repeated FILE arguments. All files are combined with clear source attribution before processing, enabling comprehensive fact extraction from multiple documents in a single run.

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
- **Selective Regeneration ("Option B")**:
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

- **Verification System Improvements (July 2025)**:
  - **Token Limits**: Increased from 800-1536 to 8192-16384 tokens to handle full documents
  - **No Local Parsing**: Removed ~25 lines of content parsing in brainstorm.py - trust LLM output
  - **Prompt Clarity**: Updated prompts to preserve ALL sections and prevent system instruction bleeding
  - **API Simplification**: verify_with_level now only uses "heavy" for strategy/draft commands
  - **Full Document Preservation**: Fixed issue where "MOST LIKELY TO SUCCEED" section was being lost

## Structured Output Patterns

- **JSON-First Extraction (June 2025)**:
  - Lookup command implements "Prompt Engineering First" principle for --extract options
  - LLM instructed to return structured JSON: `{"extract_type": ["item1", "item2", ...]}`
  - Client-side parsing attempts `json.loads()` first, falls back to regex patterns if JSON parsing fails
  - Eliminates fragile regex parsing while maintaining backward compatibility
  - Pattern applicable to other commands requiring structured data extraction

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

## LLMClientFactory Configuration Pattern

Strategic analysis commands follow consistent configuration patterns:

- **CounselNotes**: `anthropic/claude-sonnet-4`, temp=0.3, top_p=0.7, force_verify=True
- **Brainstorm-Orthodox**: `anthropic/claude-sonnet-4`, temp=0.3, top_p=0.7, force_verify=True
- **Brainstorm-Unorthodox**: `x-ai/grok-3`, temp=0.9, top_p=0.95, force_verify=True
- **Brainstorm-Analysis**: `openai/o3-pro`, temp=0.2, top_p=0.8, reasoning_effort=high
- **Strategy-Analysis**: `anthropic/claude-sonnet-4`, temp=0.2, top_p=0.8
- **Barbrief**: `openai/o3-pro`, reasoning_effort=high, max_completion_tokens=32768

**Configuration Philosophy:**
- Strategic commands use Claude Sonnet 4 for balanced analysis capability
- Temperature 0.3 provides strategic thinking with controlled creativity
- Force verification enabled for professional legal accountability
- Consistent patterns across similar command types for predictable behavior
- Barbrief uses o3-pro for comprehensive document generation with extended token limits

**Brainstorm Verification Behavior (Updated January 2025):**
- Verification is ALWAYS performed on all brainstorm outputs automatically
- No --verify flag needed or available - verification is mandatory
- All three sub-types (orthodox, unorthodox, analysis) have force_verify=True
- Clean single message: "🔍 Verifying brainstorm strategies..."
- Maintains zero-tolerance citation policy across all strategies

**CounselNotes Specific Patterns:**
- Multi-document cross-synthesis capabilities
- Five-section strategic analysis framework (Overview, Opportunities, Risks, Recommendations, Management)
- Four JSON extraction modes (all, citations, principles, checklist)
- Multi-chunk consolidation for large document processing

**Barbrief Specific Patterns:**
- 10-section structured brief format (Cover Sheet through Annexures)
- Validates 10-heading case facts from extractfacts command output
- Supports multiple input types: strategies, research, supporting documents
- Hearing-type specific formatting (trial, directions, interlocutory, appeal)
- Uses o3-pro's reasoning capabilities with 32K token output limit (max_completion_tokens)
- Integrates citation verification when --verify flag is used
- Captures reasoning trace for transparency and accountability
- Implementation fixes: LLMClientFactory.for_command method, save_reasoning_trace with 2 args

## Prompt Management

- **YAML Prompts**: All system and user prompts stored in `litassist/prompts/`.
- **Runtime Loading**: Prompts injected into workflows based on command context.
- **Versioning**: Prompt templates updated centrally to apply improvements across commands.
