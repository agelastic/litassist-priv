# LitAssist User Guide

## Overview

LitAssist is a command-line tool for Australian litigation support. It automates
legal research, document analysis, fact extraction, strategic brainstorming,
document drafting, and citation verification using a multi-model LLM pipeline
routed through OpenRouter.

### Key Capabilities

- **Case-law research** via Jade.io and AustLII (Google Custom Search)
- **Document analysis** with neutral or strategic perspectives
- **Structured fact extraction** into a standard 10-heading format
- **Legal strategy generation** (orthodox, unorthodox, and analytical)
- **Citation-rich document drafting** with RAG for large files
- **Multi-stage citation verification** including Chain of Verification (CoVe)
- **Automated workflow planning** with executable command scripts

### Prerequisites

- Python 3.10 or later
- API keys: OpenRouter, OpenAI, Google Custom Search, Pinecone
- Optional: OpenAI BYOK key for o3-pro commands (draft, counselnotes, barbrief)

---

## Installation

### Recommended: pipx

```bash
pipx install litassist
```

### Alternative: Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install litassist
```

### Configuration

LitAssist uses a single configuration file at `~/.config/litassist/config.yaml`.
The `LITASSIST_CONFIG` environment variable can override this path.

To set up:

```bash
mkdir -p ~/.config/litassist
cp config.yaml.template ~/.config/litassist/config.yaml
# Edit config.yaml with your API keys
```

See [Configuration Reference](#configuration-reference) below for the full
structure, and [Google CSE setup.md](Google%20CSE%20setup.md) for search engine
configuration.

### Verify Connectivity

```bash
litassist test
```

This tests OpenAI, OpenRouter, Pinecone, Google CSE, and web scraping
capabilities. Placeholder credentials are detected and skipped automatically.

---

## Quick Start

A typical workflow from raw documents to verified legal output:

```bash
# 1. Extract structured facts from case documents
litassist extractfacts brief.pdf affidavit.pdf

# 2. Research relevant case law
litassist lookup "duty of care in professional negligence" --mode irac

# 3. Generate strategic options
litassist brainstorm --facts case_facts.txt --side plaintiff --area civil \
  --research outputs/lookup_*.txt

# 4. Develop a targeted strategy with draft document
litassist strategy case_facts.txt \
  --outcome "Summary judgement on liability" \
  --strategies outputs/brainstorm_*.txt

# 5. Draft a citation-rich legal document
litassist draft case_facts.txt strategies.txt "statement of claim"

# 6. Verify citations and legal soundness
litassist verify outputs/draft_*.txt --cove

# All outputs are timestamped in outputs/ and audit logs in logs/
```

---

## Global Options

These options apply to all commands and must be placed before the command name:

```bash
litassist [--log-format json|markdown] [--verbose] COMMAND [OPTIONS]
```

| Option | Default | Description |
|--------|---------|-------------|
| `--log-format` | from config.yaml | Format for audit logs (`json` or `markdown`) |
| `--verbose` | off | Enable debug-level logging |

---

## Command Reference

### caseplan

Generate a customised litigation workflow plan with executable command scripts.

```bash
litassist caseplan <case_facts> [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--budget` | `minimal` / `standard` / `comprehensive` | Budget constraint. If omitted, LLM recommends one |
| `--context` | text | Additional context to guide planning |
| `--output` | text | Custom output filename prefix |

When `--budget` is omitted, performs a rapid assessment and recommends a budget
level. When specified, generates a full plan with phased command sequences.
Each command in the plan includes a `# Switch rationale:` comment explaining
technical choices.

```bash
# Get budget recommendation
litassist caseplan case_facts.txt

# Generate full plan at standard budget
litassist caseplan case_facts.txt --budget standard
```

**Model:** Claude Sonnet 4.5

---

### lookup

Search Australian case law via Jade.io and AustLII using Google Custom Search,
then produce a structured legal answer.

```bash
litassist lookup <question> [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--mode` | `irac` / `broad` | Answer format: structured IRAC analysis or broad exploration |
| `--comprehensive` | flag | Search up to 10 results from multiple sources (vs 5) |
| `--context` | text | Contextual information to guide analysis |
| `--extract` | `citations` / `principles` / `checklist` | Extract specific elements as structured output |
| `--no-fetch` | flag | Skip content fetching, use URLs only |
| `--output` | text | Custom output filename prefix |

```bash
# Standard IRAC analysis
litassist lookup "Is frustration a defence to costs in contract law?"

# Comprehensive search with context
litassist lookup "negligence principles" --comprehensive \
  --context "medical malpractice involving surgical errors"

# Extract just the citations
litassist lookup "duty of care" --extract citations
```

**Model:** Gemini 2.5 Pro

---

### digest

Analyse one or more documents by splitting into chunks and producing either
a chronological summary or legal issues identification.

```bash
litassist digest <files>... [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--mode` | `summary` / `issues` | Chronological summary or legal issue identification |
| `--context` | text | Additional context to guide analysis |
| `--output` | text | Custom output filename prefix |

```bash
# Summarise a contract
litassist digest purchase_agreement.pdf --mode summary

# Identify legal issues across multiple documents
litassist digest brief.pdf affidavit.pdf --mode issues

# Focused analysis with context
litassist digest correspondence.pdf --mode summary \
  --context "Focus on payment obligations"
```

**Model:** Claude Sonnet 4.5

---

### extractfacts

Extract structured case facts from documents into the standard 10-heading
format used by brainstorm, strategy, and barbrief commands.

```bash
litassist extractfacts <files>... [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--verify` | flag | Enable self-critique verification pass (auto-enabled) |
| `--heavy` | flag | Use GPT-5 Pro for verification instead of GPT-5.1 |
| `--noverify` | flag | Skip verification (not recommended) |
| `--output` | text | Custom output filename prefix |

The 10-heading structure covers: Parties, Background, Key Events, Legal Issues,
Evidence Available, Opposing Arguments, Procedural History, Jurisdiction,
Applicable Law, and Client Objectives.

```bash
# Extract facts with standard verification
litassist extractfacts case_bundle.pdf

# Extract from multiple documents with heavy verification
litassist extractfacts brief.pdf affidavit.pdf --heavy
```

**Model:** Claude Sonnet 4.5 (extraction), GPT-5.1 or GPT-5 Pro (verification)

---

### brainstorm

Generate comprehensive legal strategies: 15 orthodox, 15 unorthodox, analytical
ranking, and a final 5 most promising.

```bash
litassist brainstorm [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--facts` | path(s) | Facts files (glob supported). Defaults to `case_facts.txt` |
| `--side` | `plaintiff` / `defendant` / `accused` / `respondent` | Required: which side you represent |
| `--area` | `criminal` / `civil` / `family` / `commercial` / `administrative` | Required: legal area |
| `--research` | path(s) | Optional lookup reports to inform orthodox strategies (glob supported) |
| `--verify` | flag | Add LLM content verification |
| `--output` | text | Custom output filename prefix |

All citations are automatically verified and annotated with risk levels.

```bash
# Basic brainstorm
litassist brainstorm --side plaintiff --area civil

# With research context from lookup outputs
litassist brainstorm --side defendant --area family \
  --research 'outputs/lookup_*.txt' --facts case_facts.txt
```

**Models:** Claude Sonnet 4.5 (orthodox), Grok-4 (unorthodox), o3-pro (analysis)
**BYOK required:** o3-pro (analysis stage)

---

### strategy

Analyse case facts to produce strategic options for achieving a specific legal
outcome, including next steps and a draft legal document.

```bash
litassist strategy <case_facts> [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--outcome` | text | Required: desired outcome (single sentence) |
| `--strategies` | path | Optional brainstorm strategies file |
| `--verify` | flag | Enable self-critique pass (auto-enabled) |
| `--heavy` | flag | Use GPT-5 Pro for verification |
| `--noverify` | flag | Skip verification |
| `--output` | text | Custom output filename prefix |

Generates: strategic options, next steps document, draft legal document, and
reasoning trace.

```bash
litassist strategy case_facts.txt \
  --outcome "Summary judgement on liability" \
  --strategies outputs/brainstorm_civil_plaintiff_*.txt
```

**Models:** Claude Sonnet 4.5 (strategy), o3-pro (analysis)
**BYOK required:** o3-pro (analysis stage)

---

### draft

Draft a citation-rich legal document. Small text files are passed directly to
the LLM. PDFs and large files use Retrieval-Augmented Generation (RAG) via
Pinecone embeddings with MMR re-ranking.

```bash
litassist draft <documents>... <query> [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--heavy` | flag | Use GPT-5 Pro for verification |
| `--noverify` | flag | Skip verification |
| `--diversity` | float | RAG search diversity (0.0-1.0). Higher = more diverse results |
| `--output` | text | Custom output filename prefix |

Includes automatic hallucination detection. Citations are verified against
Jade.io via Google CSE.

```bash
# Draft from text files (direct LLM)
litassist draft case_facts.txt strategies.txt "statement of claim"

# Draft from PDF with RAG
litassist draft large_case_bundle.pdf "outline of submissions" --diversity 0.3
```

**Model:** o3-pro
**BYOK required:** Yes

---

### counselnotes

Generate strategic analysis from an advocate's perspective, complementing the
neutral analysis from digest. Supports structured JSON extraction modes.

```bash
litassist counselnotes <files>... [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--extract` | `all` / `citations` / `principles` / `checklist` | Extract structured JSON data |
| `--verify` | flag | Enable citation verification |
| `--output` | text | Custom output filename prefix |

See [COUNSELNOTES_GUIDE.md](COUNSELNOTES_GUIDE.md) for detailed usage.

```bash
# Strategic analysis
litassist counselnotes brief.pdf affidavit.pdf

# Extract actionable checklist
litassist counselnotes --extract checklist case_materials.pdf

# Extract all structured elements with verification
litassist counselnotes --extract all --verify judgment.pdf
```

**Model:** o3-pro
**BYOK required:** Yes

---

### barbrief

Create a structured barrister's brief combining case facts, strategies, research,
and supporting documents. Follows Australian legal conventions.

```bash
litassist barbrief <case_facts> [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--hearing-type` | `trial` / `directions` / `interlocutory` / `appeal` | Required: type of hearing |
| `--strategies` | path(s) | Brainstorm strategies files (glob supported) |
| `--research` | path(s) | Lookup/research reports (glob supported) |
| `--documents` | path(s) | Supporting documents (glob supported) |
| `--context` | text | Additional context |
| `--verify` | flag | Enable citation verification |
| `--output` | text | Custom output filename prefix |

```bash
litassist barbrief case_facts.txt --hearing-type trial \
  --strategies 'outputs/brainstorm_*.txt' \
  --research 'outputs/lookup_*.txt' \
  --documents '*.pdf'
```

**Model:** o3-pro
**BYOK required:** Yes

---

### verify

Post-hoc verification of legal documents. By default runs all three checks:
citation verification, legal soundness, and reasoning trace.

```bash
litassist verify <file> [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--citations` | flag | Verify citations only |
| `--soundness` | flag | Verify legal soundness only |
| `--reasoning` | flag | Verify/generate reasoning trace only |
| `--cove` | flag | Add Chain of Verification as final check |
| `--reference` | glob | Reference files for context |
| `--cove-reference` | glob | Reference files for CoVe answer stage (requires `--cove`) |
| `--heavy` | flag | Use GPT-5 Pro for reasoning and soundness |
| `--output` | text | Custom output filename prefix |

With no flags, all three verifications run. Individual flags select specific
checks.

```bash
# Full verification suite
litassist verify outputs/draft_statement_of_claim_*.txt

# Citations only with Chain of Verification
litassist verify outputs/draft_*.txt --citations --cove

# Heavy verification with reference documents
litassist verify outputs/draft_*.txt --heavy --reference 'exhibits/*.pdf'
```

**Models:** GPT-5.1 (citation verification), Claude Opus 4.1 (soundness),
Claude Sonnet 4.5 (reasoning), GPT-5 Pro (heavy mode)

---

### verify-cove

Standalone Chain of Verification. Runs the full 4-stage CoVe pipeline on a
document: generate questions, answer questions, detect inconsistencies,
regenerate corrected output.

```bash
litassist verify-cove <file> [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--reference` | glob | Reference files for the answer stage |
| `--heavy` | flag | Use GPT-5 Pro for the answers stage |
| `--output` | text | Custom output filename prefix |

```bash
# Standard CoVe
litassist verify-cove outputs/draft_*.txt

# With reference documents and heavy mode
litassist verify-cove outputs/draft_*.txt \
  --reference 'exhibits/*.pdf' --heavy
```

**Models:** Claude Sonnet 4.5 (questions, verify, final), GPT-5.1 or GPT-5 Pro
(answers)

---

## Workflows

### Standard Litigation Workflow

The full pipeline from documents to verified output:

```
extractfacts --> brainstorm --> strategy --> draft --> verify
     |               ^                       ^
     |               |                       |
     +--- lookup ----+--- counselnotes ------+
```

1. **Extract facts** from case documents into 10-heading structure
2. **Research** relevant case law via lookup
3. **Brainstorm** strategies using facts and research
4. **Develop strategy** with specific outcome and draft document
5. **Draft** citation-rich legal documents
6. **Verify** citations, soundness, and reasoning

### Document Review Workflow

For reviewing incoming documents (opposing briefs, judgements):

```bash
# 1. Neutral factual analysis
litassist digest opposing_brief.pdf --mode issues

# 2. Strategic perspective
litassist counselnotes --verify opposing_brief.pdf

# 3. Extract actionable items
litassist counselnotes --extract checklist opposing_brief.pdf
```

### CasePlan Automated Workflow

Let LitAssist plan the workflow for you:

```bash
# Get budget recommendation first
litassist caseplan case_facts.txt

# Generate full plan with executable commands
litassist caseplan case_facts.txt --budget standard
```

The plan output includes complete bash commands with switch rationale comments,
budget allocation, and a command coverage analysis explaining why each command
was included or omitted.

### Verification Pipeline

For maximum confidence in outputs:

```bash
# Standard: citations + soundness + reasoning
litassist verify draft.txt

# Add Chain of Verification
litassist verify draft.txt --cove

# Standalone CoVe with reference documents
litassist verify-cove draft.txt --reference 'exhibits/*.pdf'

# Heavy mode for filed-to-court quality
litassist verify draft.txt --heavy --cove --cove-reference 'exhibits/*.pdf'
```

---

## Model Configuration

### Three-Tier Strategy

| Tier | Purpose | Models | Cost |
|------|---------|--------|------|
| Critical | Verification, soundness checks | GPT-5 Pro, Claude Opus 4.1 | Highest |
| Fast | Standard verification, CoVe answers | GPT-5.1 | Medium |
| Legal Reasoning | Most commands (analysis, drafting, extraction) | Claude Sonnet 4.5, o3-pro, Grok-4, Gemini 2.5 Pro | Varies |

### Command-to-Model Assignments

| Command | Model | BYOK Required |
|---------|-------|---------------|
| caseplan | Claude Sonnet 4.5 | No |
| lookup | Gemini 2.5 Pro | No |
| digest | Claude Sonnet 4.5 | No |
| extractfacts | Claude Sonnet 4.5 | No |
| brainstorm (orthodox) | Claude Sonnet 4.5 | No |
| brainstorm (unorthodox) | Grok-4 | No |
| brainstorm (analysis) | o3-pro | Yes |
| strategy | Claude Sonnet 4.5 | No |
| strategy (analysis) | o3-pro | Yes |
| draft | o3-pro | Yes |
| counselnotes | o3-pro | Yes |
| barbrief | o3-pro | Yes |
| verification (standard) | GPT-5.1 | No |
| verification (heavy) | GPT-5 Pro | No |
| verify-soundness | Claude Opus 4.1 | No |
| verify-soundness (heavy) | GPT-5 Pro | No |
| verify-reasoning | Claude Sonnet 4.5 | No |
| CoVe questions/verify/final | Claude Sonnet 4.5 | No |
| CoVe answers | GPT-5.1 | No |
| CoVe answers (heavy) | GPT-5 Pro | No |

All calls route through OpenRouter. Model assignments are defined in
`litassist/llm/model_configs.yaml`.

### BYOK Setup

Commands using o3-pro require an OpenAI API key configured for Bring Your Own
Key (BYOK) through OpenRouter. Set `openai.api_key` in config.yaml to your
OpenAI API key. OpenRouter passes o3-pro requests directly to OpenAI using
your key.

---

## Output Files

### Directory Structure

LitAssist creates two directories in the current working directory:

```
./outputs/    Command output files (timestamped, never overwrites)
./logs/       Audit logs (JSON or Markdown format)
```

Both directories are created automatically on first run.

### Output Naming

Files follow the pattern `{command}_{descriptor}_{YYYYMMDD}_{HHMMSS}.txt`:

| Command | Example Filename |
|---------|-----------------|
| caseplan | `caseplan_standard_20260218_143022.txt` |
| lookup | `lookup_duty_of_care_20260218_143156.txt` |
| digest | `digest_summary_brief_20260218_143340.txt` |
| extractfacts | `extractfacts_brief_20260218_143502.txt` |
| brainstorm | `brainstorm_civil_plaintiff_20260218_143622.txt` |
| strategy | `strategy_summary_judgement_20260218_143740.txt` |
| draft | `draft_statement_of_claim_20260218_143855.txt` |
| counselnotes | `counselnotes_brief_20260218_144010.txt` |
| barbrief | `barbrief_trial_20260218_144125.txt` |
| verify | `verify_citations_20260218_144240.txt` |

### Audit Logs

Every LLM request and response is logged with timestamp, model, token counts,
and costs. Format is controlled by `--log-format` (CLI) or `log_format`
(config.yaml). Log files are named `{tag}_{YYYYMMDD}-{HHMMSS}.{json|md}`.

---

## Configuration Reference

```yaml
# ~/.config/litassist/config.yaml

openrouter:
  api_key: "your-openrouter-key"          # Required
  api_base: "https://openrouter.ai/api/v1"  # Default

openai:
  api_key: "your-openai-key"              # Required (embeddings + BYOK)
  embedding_model: "text-embedding-3-small"  # Default

google_cse:
  api_key: "your-google-api-key"          # Required
  cse_id: "your-jade-cse-id"             # Required (Jade.io)
  cse_id_austlii: "your-austlii-cse-id"  # Optional (AustLII)
  cse_id_comprehensive: "your-comp-cse-id"  # Optional (broader sources)

pinecone:
  api_key: "your-pinecone-key"            # Required
  environment: "your-environment"          # Required
  index_name: "your-index-name"           # Required

jina_reader:
  api_key: "your-jina-key"               # Optional (higher rate limits)

general:
  heartbeat_interval: 20     # Seconds between "still working" messages
  max_chars: 200000          # Document chunk size (~50K tokens)
  rag_max_chars: 8000        # RAG chunk size (~1600 words)
  log_format: "json"         # Default log format (json or markdown)

citation_validation:
  offline_validation: false  # Skip online citation checks

web_scraping:
  fetch_timeout: 10          # Per-request timeout (seconds)
  max_fetch_time: 300        # Total fetch time limit (seconds)
  selenium_enabled: true     # Use Selenium for complex pages
  selenium_timeout_multiplier: 2
```

---

## Troubleshooting

### API Key Errors

```
Error: config.yaml missing key 'openrouter'
```

Ensure all required sections exist in `~/.config/litassist/config.yaml`.
Run `litassist test` to verify each service.

### BYOK Not Configured

```
BYOK required for o3-pro
```

Commands using o3-pro (draft, counselnotes, barbrief, brainstorm-analysis,
strategy-analysis) require a valid OpenAI API key. Set `openai.api_key` in
config.yaml to your actual OpenAI key (not a placeholder).

### Large File Processing

Files exceeding `max_chars` (default 200,000 characters) are automatically
chunked. For very large PDFs, the RAG pipeline (draft command) embeds chunks
into Pinecone for retrieval. Use `--diversity` to control result variety.

If processing is slow, the heartbeat indicator ("...still working...") confirms
the command is active. Adjust `heartbeat_interval` in config.yaml.

### Citation Verification Failures

Citations are verified against Jade.io via Google Custom Search. Common causes
of failure:

- Google CSE daily quota exceeded (free tier: 100 requests/day)
- Citation format not matching Australian standards
- Case not indexed in Jade.io

Use `--noverify` to skip verification when testing, but always verify before
relying on citations for court filings.

### No Config File Found

```
Error: No config.yaml found.
```

Configuration must be at `~/.config/litassist/config.yaml`. This is the only
location checked (unless `LITASSIST_CONFIG` environment variable is set).

---

## Related Guides

- [Counsel's Notes Guide](COUNSELNOTES_GUIDE.md) -- detailed counselnotes
  command usage, extraction modes, and workflow integration
- [Google CSE Setup](Google%20CSE%20setup.md) -- setting up Jade.io, AustLII,
  and comprehensive search engines
- [Prompt Management](PROMPTS_README.md) -- prompt template system
  architecture and customisation
- [Non-Legal Documents](non_legal_documents.md) -- adapting LitAssist for
  documents outside standard legal workflows
