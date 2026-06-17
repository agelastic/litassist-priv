# LitAssist User Guide

Last updated: 17/06/2026

## Overview

LitAssist is a command-line tool for Australian litigation support. It automates
legal research, document analysis, fact extraction, strategic brainstorming,
document drafting, and citation verification using a multi-model LLM pipeline
routed through OpenRouter.

### Key Capabilities

- **Case-law research** via Jade.io and AustLII (Google Custom Search)
- **Document analysis** with neutral or strategic perspectives
- **Structured fact extraction** into a standard 10-heading format
- **Matter-type posture** carried in case facts (civil, criminal, family, commercial, disciplinary, foi, administrative) so framing commands adapt forum, remedies, and document archetype
- **Legal strategy generation** (orthodox, unorthodox, and analytical)
- **Citation-rich document drafting** that feeds full source documents to the model in a single call
- **Multi-stage citation verification** including Chain of Verification (CoVe)
- **Automated workflow planning** with executable command scripts

### Prerequisites

- Python 3.10 or later
- API keys: OpenRouter (sole gateway for all LLM calls) and Google Custom Search. Provider-level BYOK for `openai/o3-pro` etc. is configured at OpenRouter's integrations dashboard, not in this project's config.

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

This tests OpenRouter, Google CSE, and web scraping capabilities.
Placeholder credentials are detected and skipped automatically.

---

## Quick Start

A typical workflow from raw documents to verified legal output:

```bash
# 1. Extract structured facts from case documents
litassist extractfacts brief.pdf affidavit.pdf

# 2. Research relevant case law
litassist lookup "duty of care in professional negligence" --mode irac

# 3. Generate strategic options
litassist brainstorm --facts case_facts.md --side plaintiff --area civil \
  --research outputs/lookup_*.md

# 4. Develop a targeted strategy with draft document
litassist strategy case_facts.md \
  --outcome "Summary judgement on liability" \
  --strategies outputs/brainstorm_*.md

# 5. Draft a citation-rich legal document
litassist draft case_facts.md strategies.txt "statement of claim"

# 6. Verify citations and legal soundness
litassist verify outputs/draft_*.md --cove

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
litassist caseplan [case_facts] [OPTIONS]
```

`case_facts` is optional: if omitted, the latest `case_facts*.md` in the current directory is auto-selected (and printed). This applies to `strategy`, `barbrief`, `brainstorm --facts`, and `draft` too.

| Option | Type | Description |
|--------|------|-------------|
| `--budget` | `minimal` / `standard` / `comprehensive` | Budget constraint. If omitted, LLM recommends one |
| `--context` | text | Additional context to guide planning |
| `--output` | text | Custom output filename prefix |

When `--budget` is omitted, performs a rapid assessment and recommends a budget
level. The plan also reads the `Matter type:` line in the case facts to set its
posture, so the recommended commands and forum suit e.g. a regulatory complaint or
FOI matter rather than defaulting to litigation. If the line is absent or
unrecognised, caseplan assumes `civil` and warns. When specified, generates a full plan with phased command sequences.
Each command in the plan includes a `# Switch rationale:` comment explaining
technical choices. `--context` guides both modes.

Generated commands are validated before the runnable script is saved: each is
parsed and re-rendered so shell control characters cannot run as live operators.
If no executable commands can be extracted, the plan is still saved and you are
warned to action the steps manually rather than handed an empty script.

```bash
# Get budget recommendation
litassist caseplan case_facts.md

# Generate full plan at standard budget
litassist caseplan case_facts.md --budget standard
```

**Model:** Claude Opus 4.7 (full plan); Claude Sonnet 4.6 (budget assessment)

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

**Model:** Gemini 3.5 Flash

---

### digest

Analyse one or more documents by splitting into chunks and producing either
a chronological summary or legal issues identification.

```bash
litassist digest <files>... [OPTIONS]
```

The `files` argument supports glob patterns.

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

**Model:** Claude Sonnet 4.6

---

### extractfacts

Extract structured case facts from documents into the standard 10-heading
format used by brainstorm, strategy, and barbrief commands.

```bash
litassist extractfacts <files>... [OPTIONS]
```

The `files` argument supports glob patterns.

| Option | Type | Description |
|--------|------|-------------|
| `--heavy` | flag | Use GPT-5.5 with maximum reasoning effort for verification |
| `--noverify` | flag | Skip verification (not recommended) |
| `--output` | text | Custom output filename prefix |

Verification is auto-enabled; use `--noverify` to skip it.

The 10-heading structure covers: Parties, Background, Key Events, Legal Issues,
Evidence Available, Opposing Arguments, Procedural History, Jurisdiction,
Applicable Law, and Client Objectives.

Under the Jurisdiction heading, extractfacts also proposes a `Matter type:` line
(one of: civil, criminal, family, commercial, disciplinary, foi, administrative),
classified from the source documents. Review and edit it if the classification is
wrong: the framing commands (brainstorm, strategy, barbrief, caseplan) read it to
set their posture. If it is missing or unrecognised, those commands assume `civil`
and print a warning.

```bash
# Extract facts with standard verification
litassist extractfacts case_bundle.pdf

# Extract from multiple documents with heavy verification
litassist extractfacts brief.pdf affidavit.pdf --heavy
```

**Model:** Claude Sonnet 4.6 (extraction), GPT-5.5 (verification)

---

### updatefacts

Fold source documents into the same 10-heading case facts structure, updating an
existing case-facts file or creating one from scratch. This removes the manual
copy-paste step after `extractfacts` or `digest`: it writes a fresh,
auto-discoverable `case_facts_<timestamp>.md` into the current directory that
brainstorm, strategy, draft, and barbrief pick up automatically.

```bash
litassist updatefacts <files>... [OPTIONS]
```

The `files` argument (the source material to fold in) supports glob patterns.

| Option | Type | Description |
|--------|------|-------------|
| `--facts` | path | Existing case facts file to update. Default: the latest `case_facts*.md` in the current directory; created from scratch if none. |

Anything that does not fit one of the ten headings (plus the merge model's own
observations and any source conflicts) is collected under a final **Notes**
section. The existing `Matter type:` line under Jurisdiction is preserved across
updates. Source files are never modified; each run emits a new timestamped file.

```bash
# Build/refresh case facts from extractfacts and digest output
litassist updatefacts 'outputs/extractfacts_*.md' 'outputs/digest_issues_*.md'

# Update a specific existing case-facts file with new material
litassist updatefacts new_affidavit.pdf --facts case_facts.md
```

**Model:** Gemini 3.5 Flash (cheap, fast merge)

---

### brainstorm

Generate comprehensive legal strategies: 15 orthodox, 15 unorthodox, analytical
ranking, and a final 5 most promising. Reads the `Matter type:` line in the case
facts to set its posture, so a disciplinary/regulatory complaint or an FOI matter is
framed for the relevant commissioner or agency rather than defaulting to court
litigation. Use `--side complainant` for regulatory and FOI matters. If the line is
absent or unrecognised, brainstorm assumes `civil` and warns.

```bash
litassist brainstorm [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--facts` | path(s) | Facts files (glob supported). Defaults to `case_facts.md` |
| `--side` | `plaintiff` / `defendant` / `accused` / `respondent` / `complainant` | Required: which side you represent (`complainant` = regulatory/FOI complaints) |
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
  --research 'outputs/lookup_*.md' --facts case_facts.md
```

**Models:** Claude Sonnet 4.6 (orthodox), Grok 4.20 (unorthodox), o3-pro (analysis)
**BYOK required:** o3-pro (analysis stage)

---

### strategy

Analyse case facts to produce strategic options for achieving a specific legal
outcome, including next steps and a draft legal document. The `Matter type:` line in
the case facts sets the posture (forum, available remedies, and document archetype),
so e.g. an FOI or disciplinary matter is targeted at the relevant agency or
commissioner instead of a court. If the line is absent or unrecognised, strategy
assumes `civil` and warns.

```bash
litassist strategy <case_facts> [OPTIONS]
```

| Option | Type | Description |
|--------|------|-------------|
| `--outcome` | text | Required: desired outcome (single sentence) |
| `--strategies` | path or glob | Optional brainstorm strategies file; a glob resolves to the most recent match |
| `--heavy` | flag | Use GPT-5.5 for verification |
| `--noverify` | flag | Skip verification |
| `--output` | text | Custom output filename prefix |

Generates: strategic options, next steps document, draft legal document, and
reasoning trace.

```bash
litassist strategy case_facts.md \
  --outcome "Summary judgement on liability" \
  --strategies outputs/brainstorm_civil_plaintiff_*.md
```

**Models:** Claude Opus 4.7 (strategy), o3-pro (analysis)
**BYOK required:** o3-pro (analysis stage)

---

### draft

Draft a citation-rich legal document. Every supplied document (text files and
PDFs alike) is concatenated and sent to the LLM in one full-context call.
For documents that exceed the draft model's context window, run
`litassist digest --mode summary <file>` first and feed the summary to draft.

```bash
litassist draft <documents>... <query> [OPTIONS]
```

The `documents` argument supports glob patterns.

| Option | Type | Description |
|--------|------|-------------|
| `--heavy` | flag | Use verification-heavy mode (max thinking effort) |
| `--noverify` | flag | Skip verification |
| `--output` | text | Custom output filename prefix |

Includes automatic hallucination detection. Citations are verified against
Jade.io via Google CSE.

```bash
# Draft from text and PDF inputs (single full-context call)
litassist draft case_facts.md strategies.txt "statement of claim"
litassist draft large_case_bundle.pdf "outline of submissions"
```

**Model:** o3-pro
**BYOK required:** Yes

---

### counselnotes

Generate strategic analysis from an advocate's perspective, complementing the
neutral analysis from digest. Supports structured JSON extraction modes. Because
counselnotes takes arbitrary files rather than a case-facts file, set the posture
with `--matter-type` (default `civil` with a warning).

```bash
litassist counselnotes <files>... [OPTIONS]
```

The `files` argument supports glob patterns.

| Option | Type | Description |
|--------|------|-------------|
| `--extract` | `all` / `citations` / `principles` / `checklist` | Extract structured JSON data |
| `--matter-type` | `civil` / `criminal` / `family` / `commercial` / `disciplinary` / `foi` / `administrative` | Posture framing (counselnotes has no `case_facts` to read it from); defaults to `civil` with a warning |
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
and supporting documents. Follows Australian legal conventions. The `Matter type:`
line in the case facts sets the brief's posture (forum, process, and remedies). If
the line is absent or unrecognised, barbrief assumes `civil` and warns.

```bash
litassist barbrief [case_facts] [OPTIONS]
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
litassist barbrief case_facts.md --hearing-type trial \
  --strategies 'outputs/brainstorm_*.md' \
  --research 'outputs/lookup_*.md' \
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
| `--reference` | glob | Reference files for context (required to detect fabricated facts - see below) |
| `--cove-reference` | glob | Reference files for CoVe answer stage (requires `--cove`) |
| `--heavy` | flag | Use GPT-5.5 for reasoning and soundness |
| `--output` | text | Custom output filename prefix |

With no flags, all three verifications run. Individual flags select specific
checks. `--cove` is additive: it runs on top of the selected checks, not instead of
them.

**Detecting fabricated facts requires a source (`--reference`).** A plausible,
internally-consistent fabricated fact - an invented expert report, email admission,
or finding - cannot be detected from the document alone, because the verifier has
nothing to check it against. In testing, a plain `litassist verify <doc>
--reference <source>` flagged every such fabricated fact (4/4); the same command
WITHOUT `--reference` caught none. So supply the document's factual basis via
`--reference` (the brief, exhibits, instructions, or the decision under review)
whenever the document asserts facts that depend on a source. `verify` reports the
unsupported assertion and the soundness stage can emit a corrected document.

```bash
# Full verification suite
litassist verify outputs/draft_statement_of_claim_*.md

# Citations only with Chain of Verification
litassist verify outputs/draft_*.md --citations --cove

# Heavy verification with reference documents
litassist verify outputs/draft_*.md --heavy --reference 'exhibits/*.pdf'
```

**Models:** GPT-5.5 (citation verification), Claude Opus 4.7 (soundness),
Claude Sonnet 4.6 (reasoning), GPT-5.5 (heavy mode)

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
| `--heavy` | flag | Use GPT-5.5 for the answers stage |
| `--output` | text | Custom output filename prefix |

```bash
# Standard CoVe
litassist verify-cove outputs/draft_*.md

# With reference documents and heavy mode
litassist verify-cove outputs/draft_*.md \
  --reference 'exhibits/*.pdf' --heavy
```

**Models:** Claude Sonnet 4.6 (questions, verify, final), GPT-5.5
(answers)

---

## Workflows

### Standard Litigation Workflow

The full pipeline from documents to verified output:

```
extractfacts --> updatefacts --> brainstorm --> strategy --> draft --> verify
     |               ^                            ^
     |               |                            |
     +--- digest ----+--- lookup --- counselnotes +
```

`updatefacts` is optional but convenient: it merges `extractfacts`/`digest`
output into an auto-discoverable `case_facts_<timestamp>.md` so the downstream
commands find it without a manual copy.

The case facts carry a `Matter type:` line (under Jurisdiction) that extractfacts
proposes and updatefacts preserves. The framing commands (brainstorm, strategy,
barbrief, caseplan) read it to adapt their posture, so a disciplinary, FOI, or
administrative matter is framed for the right forum instead of defaulting to
litigation. Check this line before brainstorming.

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
litassist caseplan case_facts.md

# Generate full plan with executable commands
litassist caseplan case_facts.md --budget standard
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

### Task-Based Model Selection

Current model assignments are defined in `litassist/llm/model_configs.yaml`. Registered commands are defined in `litassist/commands/__init__.py`.

| Role | Purpose | Model | Commands |
|------|---------|-------|----------|
| Legal Reasoning | Extraction, digest, case planning, light verification, CoVe scaffolding | Claude Sonnet 4.6 | 12 |
| Advanced Drafting | Documents, briefs, deep analysis | o3-pro | 5 |
| Critical Verification | Highest-stakes soundness checks | GPT-5.5 | 4 |
| Standard Verification | Self-critique, CoVe answers | GPT-5.5 | 2 |
| Strategy and Soundness | Strategic options and logical soundness analysis | Claude Opus 4.7 | 2 |
| Lookup Synthesis | Case-law research synthesis | Gemini 3.5 Flash | 1 |
| Creative Ideation | Unorthodox brainstorming | Grok 4.20 | 1 |

### Command-to-Model Assignments

| Command | Model | BYOK Required |
|---------|-------|---------------|
| caseplan | Claude Opus 4.7 (full plan) / Sonnet 4.6 (assessment) | No |
| lookup | Gemini 3.5 Flash | No |
| digest | Claude Sonnet 4.6 | No |
| extractfacts | Claude Sonnet 4.6 | No |
| updatefacts | Gemini 3.5 Flash | No |
| brainstorm (orthodox) | Claude Sonnet 4.6 | No |
| brainstorm (unorthodox) | Grok 4.20 | No |
| brainstorm (analysis) | o3-pro | Yes |
| strategy | Claude Opus 4.7 | No |
| strategy (analysis) | o3-pro | Yes |
| draft | o3-pro | Yes |
| counselnotes | o3-pro | Yes |
| barbrief | o3-pro | Yes |
| verification (standard) | GPT-5.5 | No |
| verification (heavy) | GPT-5.5 | No |
| verify-soundness | Claude Opus 4.7 | No |
| verify-soundness (heavy) | GPT-5.5 | No |
| verify-reasoning | Claude Sonnet 4.6 | No |
| CoVe questions/verify/final | Claude Sonnet 4.6 | No |
| CoVe answers | GPT-5.5 | No |
| CoVe answers (heavy) | GPT-5.5 | No |

All calls route through OpenRouter. Model assignments are defined in
`litassist/llm/model_configs.yaml`.

### BYOK Setup

Commands using `openai/o3-pro` route through OpenRouter and require a provider
key (BYOK) configured at OpenRouter, NOT in this project's config. LitAssist
sends every LLM request to OpenRouter using `openrouter.api_key`; there is no
separate OpenAI key in `config.yaml`.

To enable o3-pro:

1. Put your OpenRouter API key in `openrouter.api_key`.
2. Open `https://openrouter.ai/settings/integrations`.
3. Add an OpenAI provider key in the OpenRouter integrations dashboard.

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

Files follow the pattern `{command}_{descriptor}_{YYYYMMDD}_{HHMMSS}.md`:

| Command | Example Filename |
|---------|-----------------|
| caseplan | `caseplan_standard_20260218_143022.md` |
| lookup | `lookup_duty_of_care_20260218_143156.md` |
| digest | `digest_summary_brief_20260218_143340.md` |
| extractfacts | `extractfacts_brief_20260218_143502.md` |
| updatefacts | `case_facts_20260218_143515.md` (written to the current directory) |
| brainstorm | `brainstorm_civil_plaintiff_20260218_143622.md` |
| strategy | `strategy_summary_judgement_20260218_143740.md` |
| draft | `draft_statement_of_claim_20260218_143855.md` |
| counselnotes | `counselnotes_brief_20260218_144010.md` |
| barbrief | `barbrief_trial_20260218_144125.md` |
| verify | `verify_citations_20260218_144240.md` |

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

google_cse:
  api_key: "your-google-api-key"          # Required
  cse_id: "your-jade-cse-id"             # Required (Jade.io)
  cse_id_austlii: "your-austlii-cse-id"  # Optional (AustLII)
  cse_id_comprehensive: "your-comp-cse-id"  # Optional (broader sources)

jina_reader:
  api_key: "your-jina-key"               # Optional - fallback transport for
                                         # JavaScript-rendered pages and
                                         # Cloudflare-blocked content (never
                                         # used for austlii.edu.au, which
                                         # blocks Jina's IPs). Primary
                                         # transport is curl_cffi (no key
                                         # required); Jina key enables higher
                                         # rate limits on the fallback path.

general:
  heartbeat_interval: 20     # Seconds between "still working" messages
  max_chars: 200000          # Document chunk size (~50K tokens)
  log_format: "json"         # Default log format (json or markdown)

citation_validation:
  offline_validation: false  # Skip online citation checks

web_scraping:
  fetch_timeout: 10          # Per-request timeout (seconds)
  max_fetch_time: 300        # Total fetch time limit (seconds)
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
strategy-analysis) require an OpenAI provider key in OpenRouter integrations.
Open `https://openrouter.ai/settings/integrations`, add the OpenAI key there,
and confirm `openrouter.api_key` is valid locally.

### Supported Input File Formats

Commands that accept file paths (`extractfacts`, `counselnotes`, `digest`,
`draft`, `brainstorm`, `barbrief`, `verify`) read these formats:

- `.pdf` — extracted via `pdfplumber` (no OCR, so scanned PDFs without
  underlying text are reported as skipped)
- `.rtf` — extracted via `striprtf` (May 2026 addition; works for AustLII
  RTF case files and any local RTF document)
- `.txt`, `.md` — read as UTF-8 text directly

### Large File Processing

Files exceeding the routed model's input budget (about 80% of that model's
context window, read from `model_capabilities.yaml`) are automatically chunked by
digest / extractfacts / counselnotes; each command then merges the per-chunk
results with a consolidation step rather than concatenating them. Because the
budget scales with the model's window, most multi-document inputs now process in
a single pass. The draft command sends every input in one full-context call; if
the combined payload exceeds the configured draft model's window, draft fails
with a clear error pointing at `litassist digest --mode summary`.

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
