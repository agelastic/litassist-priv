# LitAssist Reference Manual

Last updated: 29/05/2026

---

## 1. Introduction

### 1.1 Purpose of This Manual

This reference manual provides comprehensive documentation for LitAssist, including
detailed command descriptions, worked examples, concept explanations, and workflow
guidance. It is the expanded companion to the concise
[LitAssist User Guide](LitAssist_User_Guide.md), which serves as a quick-reference
card for day-to-day use.

Use the **User Guide** when you need to quickly look up a command's options or
check a model assignment. Use this **Reference Manual** when you need to understand
how a feature works, see detailed examples, or plan a multi-step workflow.

### 1.2 What LitAssist Does

LitAssist is a command-line tool for Australian litigation support. It automates
legal research, document analysis, fact extraction, strategic brainstorming,
document drafting, and citation verification using a multi-model LLM pipeline
routed through OpenRouter.

**Core capabilities:**

- **Case-law research** via Jade.io and AustLII (Google Custom Search)
- **Document analysis** with neutral or strategic perspectives
- **Structured fact extraction** into a standard 10-heading format
- **Legal strategy generation** (orthodox, unorthodox, and analytical)
- **Citation-rich document drafting** with full-context input (PDFs and text alike sent in one LLM call)
- **Multi-stage citation verification** including Chain of Verification (CoVe)
- **Automated workflow planning** with executable command scripts

LitAssist provides 11 commands, each performing a specific role in the litigation
pipeline:

| Command | Purpose |
|---------|---------|
| `caseplan` | Generate a litigation workflow plan with executable scripts |
| `lookup` | Search Australian case law via Jade.io and AustLII |
| `digest` | Analyse documents with chronological summaries or issue identification |
| `extractfacts` | Extract structured facts into the 10-heading format |
| `brainstorm` | Generate orthodox, unorthodox, and analytically ranked strategies |
| `strategy` | Develop tactical plans for a specific legal outcome |
| `draft` | Create citation-rich legal documents using full-context input |
| `counselnotes` | Strategic analysis from an advocate's perspective |
| `barbrief` | Generate a structured barrister's brief |
| `verify` | Post-hoc citation, soundness, and reasoning verification |
| `verify-cove` | Standalone Chain of Verification pipeline |

### 1.3 Running Example: Smith v Jones (2026)

This manual uses a fictional family court case to demonstrate each command in a
practical context. All command examples, sample outputs, and workflow walkthroughs
reference this case.

**Case Overview:** Smith v Jones (Federal Circuit and Family Court of Australia,
Division 1)

**Key Parties:**

- Jennifer Smith (mother, 38): Formerly resided in Sydney, relocated to Brisbane
  for a senior hospital position
- Michael Jones (father, 42): Residing in Sydney
- Emily Jones (14): Currently living with her mother in Brisbane
- Thomas Jones (10): Currently living with his mother in Brisbane

**Core Issues:**

1. **Complex Parenting Arrangements**: The parents previously had a consent order
   with a week-about arrangement when both lived in Sydney.
2. **Interstate Relocation**: Ms Smith relocated with the children to Brisbane in
   January 2026, citing a career opportunity. Mr Jones filed a contravention
   application in February 2026.
3. **Allegations of Parental Alienation**: Mr Jones alleges Ms Smith is
   undermining his relationship with the children. Ms Smith claims Mr Jones
   exhibits controlling behaviour.

**Procedural Status:**

- Interim parenting orders issued April 2026
- Final hearing scheduled August 2026

**Why This Example Works:**

The case involves multiple areas of family law (relocation, parenting, allegations
of alienation), procedural complexity (interim and final proceedings), and competing
factual narratives. This makes it suitable for demonstrating the full range of
LitAssist's capabilities, from initial research through to verified court
submissions.

### 1.4 Pipeline Overview

LitAssist commands form a structured pipeline. While commands can be used
independently, they are most effective when used in sequence:

```
caseplan --> extractfacts --> lookup --> brainstorm --> strategy --> draft --> verify
                 |                ^                       ^
                 |                |                       |
                 +--- digest ----+--- counselnotes ------+
```

**Data flow between commands:**

- `caseplan` reads case facts and generates a phased workflow with executable
  commands
- `extractfacts` processes raw documents into the structured 10-heading format
  required by `brainstorm`, `strategy`, and `barbrief`
- `lookup` produces research reports that feed into `brainstorm` via `--research`
- `brainstorm` generates strategies that feed into `strategy` via `--strategies`
- `strategy` produces strategic options and draft documents for `verify`
- `draft` creates citation-rich legal documents for `verify`
- `verify` and `verify-cove` perform quality checks on any text output
- `digest` and `counselnotes` operate as standalone analysis tools at any stage
- `barbrief` consolidates facts, strategies, research, and documents into a brief

---

## 2. Installation and Configuration

### 2.1 Prerequisites

- Python 3.10 or later
- API keys for:
  - **OpenRouter** (required): Sole gateway for all LLM calls. Provider-level
    BYOK (e.g. for `openai/o3-pro`) is configured at OpenRouter, not in this
    project's config.
  - **Google Custom Search** (required): Citation verification and legal research
  - **Jina Reader** (optional): Fallback transport for JavaScript-rendered pages and Cloudflare-blocked content. The primary fetch transport is `curl_cffi` (no key required); a Jina API key enables the fallback path with higher rate limits.

### 2.2 Installation Methods

**Recommended: pipx**

```bash
pipx install litassist
```

**Alternative: Virtual environment**

```bash
python -m venv .venv
source .venv/bin/activate
pip install litassist
```

After installation, verify the command is available:

```bash
litassist --help
```

### 2.3 Configuration File

LitAssist uses a single configuration file at `~/.config/litassist/config.yaml`.
This is the only location checked. The `LITASSIST_CONFIG` environment variable
can override this path.

**Initial setup:**

```bash
mkdir -p ~/.config/litassist
cp config.yaml.template ~/.config/litassist/config.yaml
# Edit config.yaml with your API keys
```

**Complete annotated configuration:**

```yaml
# ~/.config/litassist/config.yaml

# --- OpenRouter (required) ---
# Routes all LLM calls. Get a key at https://openrouter.ai/keys
openrouter:
  api_key: "sk-or-v1-your-key-here"          # Required
  api_base: "https://openrouter.ai/api/v1"    # Default, rarely changed

# --- Google Custom Search (required) ---
# Used for citation verification and the lookup command
# See Google CSE setup.md for step-by-step CSE creation
google_cse:
  api_key: "AIzaSy-your-key-here"             # Required
  cse_id: "your-jade-cse-id"                  # Required: Jade.io search engine
  cse_id_austlii: "your-austlii-cse-id"       # Optional: AustLII search engine
  cse_id_comprehensive: "your-comp-cse-id"    # Optional: broader legal sources

# --- Jina Reader (optional) ---
# Provides higher rate limits for web content fetching
jina_reader:
  api_key: "jina_your-key-here"               # Optional

# --- General settings ---
general:
  heartbeat_interval: 20     # Seconds between "still working" progress messages
  max_chars: 200000          # Document chunk size for processing (~50K tokens)
  log_format: "json"         # Default audit log format: "json" or "markdown"

# --- Citation validation ---
citation_validation:
  offline_validation: false  # true = skip online checks (pattern-only validation)

# --- Web scraping ---
web_scraping:
  fetch_timeout: 10          # Per-request timeout in seconds
  max_fetch_time: 300        # Total fetch time limit in seconds
```

**Key points:**

- All keys under `openrouter` and `google_cse` are required (except the two
  optional CSE IDs). There is no `openai:` block: OpenRouter is the sole LLM
  gateway, and provider-level BYOK (e.g. for `openai/o3-pro`) is configured at
  OpenRouter's integrations dashboard, not in this project's config.
- The `jina_reader` section is entirely optional
- The `general`, `citation_validation`, and `web_scraping` sections use sensible
  defaults if omitted
- Never store config.yaml in a project directory or version control; the single
  global location prevents secret duplication

### 2.4 Google Custom Search Engine Setup

LitAssist uses up to three Google Custom Search Engines for legal research and
citation verification:

| CSE | Purpose | Required | Scope |
|-----|---------|----------|-------|
| Jade.io (`cse_id`) | Citation verification and primary lookup | Yes | `jade.io/*` |
| AustLII (`cse_id_austlii`) | Secondary lookup source | No | `austlii.edu.au/*` |
| Comprehensive (`cse_id_comprehensive`) | Broad legal research | No | Multiple `.gov.au`, `.edu.au/law` domains |

Google CSE provides 100 free requests per day. Paid usage costs $5 per 1,000
queries.

For step-by-step setup instructions, see
[Google CSE setup.md](Google%20CSE%20setup.md).

### 2.5 BYOK (Bring Your Own Key) for o3-pro

Several commands use the `openai/o3-pro` model routed through OpenRouter,
which requires Bring Your Own Key (BYOK) configured at OpenRouter. This
project has no separate OpenAI key in `config.yaml` -- LitAssist sends every
LLM request using only `openrouter.api_key`.

To enable o3-pro:

1. Put your OpenRouter API key in `openrouter.api_key`.
2. Open `https://openrouter.ai/settings/integrations`.
3. Add an OpenAI provider key in the OpenRouter integrations dashboard.

**Commands requiring BYOK:**

| Command | Stage |
|---------|-------|
| `brainstorm` | Analysis (ranking and "most likely to succeed") |
| `strategy` | Analysis stage |
| `draft` | Document generation |
| `counselnotes` | Full analysis |
| `barbrief` | Brief generation |

If the OpenAI provider key is missing from OpenRouter integrations, o3-pro
commands will fail with an authentication or model-access error. Commands that
use only non-BYOK models work without BYOK.

### 2.6 Verifying Connectivity

```bash
litassist test
```

This tests connectivity to all configured services:

- **OpenRouter**: API key validation and model routing
- **Google CSE**: Search API access
- **Web scraping**: HTTP fetching and PDF retrieval (Jina Reader is a fallback transport and is not probed here — its health surfaces on the first `lookup` that hits a Cloudflare challenge)

Placeholder credentials are detected and skipped automatically. The test command
reports which services are operational and which need attention.

---

## 3. Working Directory and Output Management

### 3.1 Project Directory Setup

LitAssist runs from any directory and creates outputs locally. The recommended
approach is one directory per matter:

```bash
# Create project directory for Smith v Jones
mkdir ~/legal-cases/smith-v-jones-2026
cd ~/legal-cases/smith-v-jones-2026

# LitAssist will create outputs/ and logs/ here automatically
# All commands use the global config but save results locally
```

This structure keeps each matter's documents, outputs, and logs isolated while
sharing a single configuration.

### 3.2 Output File Naming

All command outputs are saved to `outputs/` with a consistent naming convention:

```
{command}_{descriptor}_{YYYYMMDD}_{HHMMSS}.txt
```

Files are never overwritten. Each run creates a new timestamped file.

| Command | Example Filename |
|---------|-----------------|
| caseplan | `caseplan_standard_20260223_143022.txt` |
| lookup | `lookup_duty_of_care_20260223_143156.txt` |
| digest | `digest_summary_brief_20260223_143340.txt` |
| extractfacts | `extractfacts_brief_20260223_143502.txt` |
| brainstorm | `brainstorm_family_plaintiff_20260223_143622.txt` |
| strategy | `strategy_summary_judgement_20260223_143740.txt` |
| draft | `draft_statement_of_claim_20260223_143855.txt` |
| counselnotes | `counselnotes_brief_20260223_144010.txt` |
| barbrief | `barbrief_trial_20260223_144125.txt` |
| verify | `verify_citations_20260223_144240.txt` |
| verify-cove | `verify_cove_draft_20260223_144355.txt` |

Use the `--output` option on any command to set a custom filename prefix.

### 3.3 Working Files vs Archive Files

LitAssist distinguishes between two types of files:

**Working files** are maintained by the user and serve as stable inputs:

- `case_facts.txt` -- the structured 10-heading case facts, updated as the case
  develops
- `strategies.txt` -- curated strategies, typically copied from brainstorm output

**Archive files** are timestamped outputs that are never overwritten:

- Every command saves its output as a new timestamped file in `outputs/`
- This preserves a complete history of analysis as the case evolves
- Previous outputs remain available for comparison or reference

**Typical workflow:**

1. Run `extractfacts` to generate an initial `case_facts.txt`-style output
2. Copy the best output to `case_facts.txt` and refine manually
3. Run `brainstorm` to generate strategies
4. Copy the most relevant strategies to `strategies.txt`
5. Use these working files as stable inputs for `strategy`, `barbrief`, etc.

### 3.4 Audit Logs

Every LLM request and response is logged with full detail:

- **Location:** `logs/` directory in the current working directory
- **Naming:** `{tag}_{YYYYMMDD}-{HHMMSS}.{json|md}`
- **Format:** JSON (default) or Markdown, controlled by `log_format` in config.yaml
  or `--log-format` on the command line

**Each log entry includes:**

- Timestamp
- Model used
- Full messages sent to the LLM
- Complete response received
- Token counts (prompt, completion, total)
- Cost information (from OpenRouter)
- Error details and retry attempts (if any)

Logs are never truncated. This provides a complete audit trail for compliance and
review.

### 3.5 Clean CLI Output

LitAssist shows concise terminal summaries rather than dumping full content. Every
command follows a consistent output pattern:

```
[Y] [Command] complete!
[DOC] Output saved to: outputs/[filename]_YYYYMMDD_HHMMSS.txt
[STATS] [Processing statistics and summary]
[TIP] View full [content]: open outputs/[filename]_YYYYMMDD_HHMMSS.txt
```

Full content is always saved to the timestamped output file. To read the complete
output:

```bash
# Use the file path shown in the terminal output
open outputs/lookup_relocation_principles_20260223_143156.txt

# Or use any text editor
code outputs/lookup_relocation_principles_20260223_143156.txt
```

The terminal output uses ANSI-coloured ASCII text for status indicators. All
terminal and file output is ASCII-only (no emoji).

---

## 4. Global Options

These options apply to all commands and must be placed before the command name:

```bash
litassist [--log-format json|markdown] [--verbose] COMMAND [OPTIONS]
```

### 4.1 --log-format

Override the `log_format` setting from config.yaml for a single run.

```bash
# Use markdown logs for this run only
litassist --log-format markdown lookup "duty of care"
```

- `json` -- Structured JSON, suitable for programmatic analysis
- `markdown` -- Human-readable format with headers and formatting

If neither the CLI option nor config.yaml specifies a format, JSON is used.

### 4.2 --verbose

Enable debug-level logging with detailed output. Shows internal processing steps,
API call details, and timing information.

```bash
litassist --verbose extractfacts case_bundle.pdf
```

---

## 5. Command Reference

Each command section covers: purpose, syntax, all options, models used, a worked
Smith v Jones example, best practices, and integration with other commands.

---

### 5.1 caseplan -- Litigation Workflow Planning

**Pipeline position:** START HERE

**Purpose:** Generate a customised litigation workflow plan with phased commands,
cost estimates, and executable scripts. This is the recommended starting point for
any matter.

**Syntax:**

```bash
litassist caseplan <case_facts> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `case_facts` | Path to case facts file (can be a skeleton initially) |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--budget` | `minimal` / `standard` / `comprehensive` | Budget constraint level |
| `--context` | text | Additional context to guide planning |
| `--output` | text | Custom output filename prefix |

**Two-mode operation:**

- **Without `--budget`**: Performs a rapid assessment of case complexity and
  recommends a budget level with justification.
- **With `--budget`**: Generates a full phased workflow plan with executable
  commands. Each command includes a `# Switch rationale:` comment explaining
  technical choices (e.g., why `--comprehensive` was selected, why `--mode irac`
  was chosen over `--mode broad`).

**Model:** Claude Sonnet 4.6

**Smith v Jones example:**

```bash
# Step 1: Get a budget recommendation
litassist caseplan case_facts_skeleton.txt
```

Sample output:

```
COMPLEXITY SCORING:
- Legal Complexity: 7/10 (interstate relocation, parental alienation allegations)
- Factual Complexity: 6/10 (competing narratives, psychological factors)
- Procedural Complexity: 8/10 (urgent interim orders, tight timeframes)
- Strategic Complexity: 7/10 (high-conflict parties, risk of escalation)

BUDGET RECOMMENDATION: comprehensive

JUSTIFICATION: Interstate relocation with alienation allegations requires
extensive research on recent authorities. High-conflict nature demands multiple
strategic approaches. Tight timeframes necessitate parallel workflows.
```

```bash
# Step 2: Generate the full plan
litassist caseplan case_facts_skeleton.txt \
  --context "relocation and time arrangements" \
  --budget comprehensive
```

This generates two files:

1. A human-readable plan with phased commands, cost estimates, and rationale
2. An executable bash script with all commands ready to run:

```bash
#!/bin/bash
# Phase 1: Extract Initial Facts from Court Documents
litassist extractfacts interim_orders_april2026.pdf \
  contravention_application_feb2026.pdf \
  affidavit_smith_jan2026.pdf affidavit_jones_feb2026.pdf

# Phase 2: Research Interstate Relocation Law
litassist lookup "best interests paramount consideration when parent \
  relocates interstate with children family law act" \
  --mode irac --comprehensive
# Switch rationale: --comprehensive for evolving relocation law,
#   --mode irac for court submission format

# Phase 3: Research Parental Alienation Claims
litassist lookup "parental alienation evidence requirements and court \
  skepticism in Australian family law" --mode irac --comprehensive
# Switch rationale: --comprehensive for contentious psychological concepts
```

**Best practices:**

- Run caseplan early, even with minimal facts. Regenerate as the case develops.
- Use the executable script as a starting point; review and adjust commands before
  running.
- The `--context` option focuses the plan on specific aspects of the case.

---

### 5.2 lookup -- Case-Law Research

**Pipeline position:** Research stage

**Purpose:** Search Australian case law via Jade.io and AustLII using Google Custom
Search, then produce a structured legal answer using the search results as context.

**Syntax:**

```bash
litassist lookup <question> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `question` | The legal question to search for |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--mode` | `irac` / `broad` | Answer format (default: `irac`) |
| `--comprehensive` | flag | Search up to 10 results per source (vs 5) |
| `--context` | text | Contextual information to guide analysis |
| `--extract` | `citations` / `principles` / `checklist` | Extract specific elements as structured output |
| `--no-fetch` | flag | Skip content fetching, use URLs only |
| `--output` | text | Custom output filename prefix |

**Analysis modes:**

- **irac** (default): Produces a structured IRAC (Issue, Rule, Application,
  Conclusion) analysis suitable for court submissions and legal memoranda.
- **broad**: Produces a broader exploration of the legal landscape, identifying
  trends, competing approaches, and areas of uncertainty.

**Search scope:**

- Standard mode: 5 results from Jade.io + 5 results from AustLII (if configured)
- Comprehensive mode: 10 results from each source + secondary CSE (if configured)

**Extract modes:**

The `--extract` option produces structured output instead of a narrative analysis:

- `citations`: A list of all relevant citations found, with case names and
  neutral citations
- `principles`: Legal principles extracted from the search results, each with
  supporting authority
- `checklist`: An actionable checklist of legal requirements or elements to prove

**Model:** Claude Sonnet 4.6

**Smith v Jones example:**

```bash
# IRAC analysis of relocation principles
litassist lookup "best interests paramount consideration when parent \
  relocates interstate with children" --mode irac \
  --context "Family law, mother relocated from Sydney to Brisbane \
  with children aged 14 and 10"
```

Sample output (saved to `outputs/lookup_best_interests_20260223_143156.txt`):

```
ISSUE:
Whether the best interests of the children are the paramount
consideration when a parent relocates interstate, and what factors
the court considers in determining parenting arrangements following
such a relocation.

RULE:
Section 60CA of the Family Law Act 1975 (Cth) establishes that in
deciding whether to make a particular parenting order, the court
must regard the best interests of the child as the paramount
consideration. The court must consider the primary and additional
considerations in s 60CC...

The leading authority on relocation cases is AHB v AHA [2023] FedCFamC1F 1038,
which confirmed that there is no presumption for or against relocation...

APPLICATION:
Applying these principles to the present facts, the mother's relocation
from Sydney to Brisbane with children aged 14 and 10 engages several
of the s 60CC factors...

CONCLUSION:
The court will assess the relocation by weighing all s 60CC factors
without any presumption. The children's ages (particularly Emily at 14)
will be significant as the court gives increasing weight to the expressed
views of mature children...
```

```bash
# Extract just the principles for later use
litassist lookup "parental alienation evidence Australian family law" \
  --extract principles --comprehensive
```

```bash
# Broad exploration when the legal landscape is uncertain
litassist lookup "whether allegations of parental alienation require \
  expert evidence" --mode broad --comprehensive
```

**Best practices:**

- Use `--mode irac` for questions with established legal principles; use
  `--mode broad` for emerging or contested areas.
- Add `--context` to focus results on your specific factual scenario.
- Use `--comprehensive` for critical research where coverage matters more than
  cost.
- Lookup output files can be passed to brainstorm via `--research` to ground
  strategies in real case law.

---

### 5.3 digest -- Document Analysis

**Pipeline position:** Analysis (can be used at any stage)

**Purpose:** Process one or more documents by splitting them into chunks and
producing either a chronological summary or legal issues identification. Digest
provides a neutral, factual perspective on the documents.

**Syntax:**

```bash
litassist digest <files>... [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `files` | One or more document files (PDF or text), glob supported |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--mode` | `summary` / `issues` | Type of analysis (default: `summary`) |
| `--context` | text | Additional context to guide analysis |
| `--output` | text | Custom output filename prefix |

**Analysis modes:**

- **summary**: Produces a chronological summary of the document contents. Events
  and facts are presented in time order with source references. Best for
  understanding what happened and when.
- **issues**: Identifies legal issues, potential problems, and areas requiring
  attention. Organises findings by issue type with supporting extracts. Best for
  spotting problems and planning responses.

**Large document handling:**

Documents exceeding the chunk size limit (default: 200,000 characters, configurable
via `max_chars` in config.yaml) are automatically split into chunks. Each chunk is
processed independently, and results are consolidated into a single output.

**Model:** Claude Sonnet 4.6

**Smith v Jones example:**

```bash
# Chronological summary of the mother's affidavit
litassist digest affidavit_smith_jan2026.pdf --mode summary

# Identify legal issues across multiple documents
litassist digest affidavit_smith_jan2026.pdf affidavit_jones_feb2026.pdf \
  --mode issues --context "Focus on parental alienation claims and evidence"
```

Sample terminal output:

```
[Y] Digest complete!
[DOC] Output saved to: outputs/digest_issues_2_files_20260223_143340.txt
[STATS] Processed 2 files (47 pages, 23,450 words)
[TIP] View full analysis: open outputs/digest_issues_2_files_20260223_143340.txt
```

**Best practices:**

- Use `--mode summary` for understanding chronology; use `--mode issues` for
  identifying legal problems.
- For multiple documents, digest produces a consolidated analysis with source
  attribution for each finding.
- Digest is the most flexible command for non-legal documents. See
  [non_legal_documents.md](non_legal_documents.md) for guidance.

**See also:** Section 6.1 (extractfacts vs digest) for guidance on choosing between
these commands.

---

### 5.4 extractfacts -- Structured Fact Extraction

**Pipeline position:** Structuring stage (feeds brainstorm, strategy, barbrief)

**Purpose:** Extract case facts from documents into the standard 10-heading
structure used by downstream commands. This is the foundational structuring step
in the pipeline.

**Syntax:**

```bash
litassist extractfacts <files>... [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `files` | One or more document files (PDF or text), glob supported |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--verify` | flag | Enable self-critique verification pass (auto-enabled) |
| `--heavy` | flag | Use GPT-5.5 with maximum reasoning effort for verification |
| `--noverify` | flag | Skip verification (not recommended for legal work) |
| `--output` | text | Custom output filename prefix |

**The 10-heading structure:**

Every extractfacts output is organised under these headings:

1. **Parties** -- All parties involved, their roles, and relationships
2. **Background** -- Context and history leading to the current dispute
3. **Key Events** -- Chronological timeline of significant events
4. **Legal Issues** -- The legal questions to be determined
5. **Evidence Available** -- Documents, witnesses, and other evidence
6. **Opposing Arguments** -- Known or anticipated positions of the other side
7. **Procedural History** -- Court filings, orders, and procedural steps to date
8. **Jurisdiction** -- Which court, which legislation, which rules apply
9. **Applicable Law** -- Key statutes, regulations, and leading cases
10. **Client Objectives** -- What the client wants to achieve

This structure is validated by `strategy` and consumed by `brainstorm`, `strategy`,
and `barbrief`. See Section 6.3 for the full explanation of each heading.

**Verification:**

Verification is auto-enabled by default. After extraction, a self-critique pass
reviews the output for accuracy, completeness, and citation quality.

- Standard verification uses GPT-5.5
- Heavy verification (`--heavy`) uses GPT-5.5 with maximum reasoning effort
- Skip verification with `--noverify` (acceptable for iteration, not for final
  outputs)

**Models:** Claude Sonnet 4.6 (extraction), GPT-5.5 (verification)

**Smith v Jones example:**

```bash
# Extract facts from court documents
litassist extractfacts interim_orders_april2026.pdf \
  contravention_application_feb2026.pdf \
  affidavit_smith_jan2026.pdf affidavit_jones_feb2026.pdf

# With heavy verification for critical work
litassist extractfacts affidavit_smith_jan2026.pdf \
  affidavit_jones_feb2026.pdf --heavy
```

Sample output structure:

```
## 1. Parties

- Jennifer Smith (mother, 38), applicant/respondent to contravention
  - Senior hospital administrator, relocated to Brisbane January 2026
- Michael Jones (father, 42), respondent/applicant for contravention
  - IT consultant, residing in Sydney
- Emily Jones (14), child of the relationship
- Thomas Jones (10), child of the relationship
- Independent Children's Lawyer: [TO BE APPOINTED]

## 2. Background

The parties were in a de facto relationship from 2010 to 2022. They
separated in March 2022 and entered into consent orders in June 2022
providing for a week-about arrangement...

## 3. Key Events

- June 2022: Consent orders made for week-about arrangement
- November 2025: Ms Smith offered senior position at Brisbane hospital
- January 2026: Ms Smith relocates to Brisbane with both children
- February 2026: Mr Jones files contravention application
- April 2026: Interim parenting orders issued
...

[continues through all 10 headings]
```

**Best practices:**

- Process all relevant documents in a single extractfacts call for consolidated
  output.
- Review and refine the output before using it as `case_facts.txt` for downstream
  commands.
- Use `--heavy` for matters heading to court; use standard verification for early
  drafts.

---

### 5.5 brainstorm -- Comprehensive Strategy Generation

**Pipeline position:** Strategy exploration

**Purpose:** Generate a comprehensive set of legal strategies: 15 orthodox
(conventional), 15 unorthodox (creative), analytical ranking of all 30, and a
final selection of the 5 most promising strategies.

**Syntax:**

```bash
litassist brainstorm [OPTIONS]
```

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--facts` | path(s) | Case facts file(s), glob supported. Defaults to `case_facts.txt` |
| `--side` | `plaintiff` / `defendant` / `accused` / `respondent` | Required: which side you represent |
| `--area` | `criminal` / `civil` / `family` / `commercial` / `administrative` | Required: area of law |
| `--research` | path(s) | Research files from lookup, glob supported |
| `--verify` | flag | Add LLM content verification |
| `--output` | text | Custom output filename prefix |

**Three-stage generation:**

1. **Orthodox strategies** (Claude Sonnet 4.6): 15 conventional legal approaches
   grounded in established case law and statutory provisions. When `--research`
   files are provided, these strategies are informed by actual authorities found
   via lookup.

2. **Unorthodox strategies** (Grok 4.20): 15 creative, lateral-thinking approaches
   that a conventional analysis might overlook. Uses higher temperature and
   repetition penalty to encourage novel ideas.

3. **Analysis** (o3-pro, BYOK required): Analytical ranking of all 30 strategies,
   followed by selection of the 5 most likely to succeed with detailed
   justification.

**Citation handling:**

All citations in the brainstorm output are automatically verified against Jade.io
via Google CSE. Strategies with problematic citations are flagged or regenerated.
Each citation is annotated with its verification status.

**Reasoning traces:**

Brainstorm saves separate reasoning files for the orthodox, unorthodox, and
analysis stages. These show the logic behind strategy selection and ranking.

**Models:** Claude Sonnet 4.6 (orthodox), Grok 4.20 (unorthodox), o3-pro (analysis)
**BYOK required:** Yes (analysis stage)

**Smith v Jones example:**

```bash
# Basic brainstorm for the mother's side
litassist brainstorm --side plaintiff --area family

# With research context from prior lookup
litassist brainstorm --side plaintiff --area family \
  --facts case_facts.txt \
  --research 'outputs/lookup_*.txt'
```

Sample output excerpt (orthodox strategy):

```
## Orthodox Strategy 3: Best Interests -- Child's Wishes

APPROACH: Rely on s 60CC(3)(a) of the Family Law Act 1975 (Cth)
to argue that Emily (14) has expressed a clear and settled wish to
remain in Brisbane, and that her maturity warrants significant weight
being given to those views.

SUPPORTING AUTHORITY: CDJ v VAJ (1998) 197 CLR 172 [Verified]
established that the views of a mature child should be given
significant weight. See also Bondelmonte v Bondelmonte [2017]
HCA 8 [Verified] regarding relocation and children's connections.

RISK LEVEL: Low
PROBABILITY OF SUCCESS: Medium-High
```

**Best practices:**

- Always provide `--side` and `--area` to ensure strategies are properly
  contextualised.
- Use `--research` with lookup output files to ground orthodox strategies in real
  case law.
- Review all 30 strategies, not just the final 5. Unorthodox strategies sometimes
  reveal angles that inform better orthodox approaches.

**See also:** Section 6.2 (brainstorm vs strategy) for understanding how brainstorm
and strategy work together.

---

### 5.6 strategy -- Targeted Legal Strategy

**Pipeline position:** Strategy development

**Purpose:** Analyse case facts to produce strategic options for achieving a
specific legal outcome. Generates probability assessments, identifies hurdles,
and produces a draft legal document.

**Syntax:**

```bash
litassist strategy <case_facts> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `case_facts` | Path to case facts file (must follow 10-heading structure) |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--outcome` | text | Required: desired legal outcome (single sentence) |
| `--strategies` | path | Optional brainstorm strategies file |
| `--verify` | flag | Enable self-critique pass (auto-enabled) |
| `--heavy` | flag | Use GPT-5.5 for verification |
| `--noverify` | flag | Skip verification |
| `--output` | text | Custom output filename prefix |

**Input validation:**

The strategy command validates that the input file follows the 10-heading structure.
Files that do not contain the expected headings will produce an error with guidance
on using extractfacts first.

**Output components:**

1. **Strategic options** with probability assessments, hurdles, and missing facts
2. **Next steps document** with prioritised actions
3. **Draft legal document** tailored to the specified outcome
4. **Reasoning trace** showing the analytical process

**Strategy prioritisation with --strategies:**

When brainstorm output is provided via `--strategies`, the strategy command
intelligently uses it:

- Directly incorporates the "most likely to succeed" strategies from brainstorm
- Fills gaps not covered by brainstorm with independent analysis
- Provides a coherent tactical plan anchored in both creative and conventional
  thinking

**Models:** Claude Opus 4.7 (strategy), o3-pro (analysis)
**BYOK required:** Yes (analysis stage)

**Smith v Jones example:**

```bash
litassist strategy case_facts.txt \
  --outcome "Secure interim orders allowing children to remain in Brisbane" \
  --strategies outputs/brainstorm_family_plaintiff_20260223_143622.txt
```

Sample output excerpt:

```
## Strategic Option 1: Status Quo / Established Arrangements

PROBABILITY OF SUCCESS: 65-75%

APPROACH: Argue that the children have been in Brisbane since
January 2026 and have established meaningful connections there.
Disruption of these arrangements would be contrary to their best
interests under s 60CC.

HURDLES:
- Mr Jones's contravention application has procedural merit
- The original consent orders contemplated Sydney residence
- Court may view unilateral relocation unfavourably

MISSING FACTS NEEDED:
- School enrolment records and academic performance in Brisbane
- Medical/counselling records showing children's adjustment
- Evidence of Emily's expressed wishes (ideally from ICL)

NEXT STEPS:
1. Obtain school reports from Brisbane school (urgency: high)
2. Arrange family report writer appointment (urgency: high)
3. File responding affidavit addressing relocation decision
...
```

**Best practices:**

- Write the `--outcome` as a single clear sentence describing exactly what you
  want to achieve.
- Provide brainstorm output via `--strategies` when available; it produces better
  results than strategy alone.
- Use `--heavy` for strategies that will directly inform court documents.

**See also:** Section 6.2 (brainstorm vs strategy) for the distinction between
these commands.

---

### 5.7 draft -- Citation-Rich Document Drafting

**Pipeline position:** Document creation

**Purpose:** Generate well-supported legal documents with citation verification
and hallucination detection. All supplied documents are fed to the LLM in one
full-context call.

**Syntax:**

```bash
litassist draft <documents>... <query> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `documents` | One or more document files (PDF or text) as knowledge base, glob supported |
| `query` | The specific legal topic or argument to draft |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--heavy` | flag | Use verification-heavy mode (max thinking effort) |
| `--noverify` | flag | Skip verification (not recommended) |
| `--output` | text | Custom output filename prefix |

**Processing model:**

Every supplied document (text files and PDFs alike) is concatenated with section
markers and sent to the LLM in a single full-context call. There is no
retrieval, embedding, or vector store. For documents that exceed the configured
draft model's context window, draft fails with a clear error pointing at
`litassist digest --mode summary <file>`; feed the resulting summary back into
draft.

**Automatic document type detection:**

The draft command recognises `case_facts.txt`, `strategies.txt`, and files
containing structured headings. It adapts its prompting based on the document
types provided, building appropriate context with `=== MARKER ===` separators.
PDFs receive their own `=== PDF DOCUMENT: <path> ===` section.

**Citation handling:**

Draft includes automatic hallucination detection. Citations in the generated
document are verified against Jade.io via Google CSE. Unverified citations are
flagged with explicit placeholders.

**Model:** o3-pro
**BYOK required:** Yes

**Smith v Jones example:**

```bash
# Draft from text and PDF inputs (single full-context call)
litassist draft case_facts.txt strategies.txt \
  "outline of submissions regarding relocation"

litassist draft large_case_bundle.pdf \
  "response to contravention application"

# Multiple source documents
litassist draft case_facts.txt strategies.txt \
  outputs/lookup_relocation_principles_20260223_143156.txt \
  "submissions on parenting arrangements"
```

**Best practices:**

- Provide case facts and strategies as separate files for the best context
  building.
- For very large bundles, summarise first with
  `litassist digest --mode summary <file>` and feed the summary to draft.
- Always verify draft output with `litassist verify` before relying on it for
  court filings.

---

### 5.8 counselnotes -- Strategic Advocate Analysis

**Pipeline position:** Analysis (can be used at any stage)

**Purpose:** Generate strategic analysis from an advocate's perspective, identifying
tactical opportunities, risks, and actionable recommendations. This complements
the neutral analysis provided by digest.

**Syntax:**

```bash
litassist counselnotes <files>... [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `files` | One or more document files (PDF or text), glob supported |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--extract` | `all` / `citations` / `principles` / `checklist` | Extract structured JSON data |
| `--verify` | flag | Enable citation verification |
| `--output` | text | Custom output filename prefix |

**Strategic analysis framework:**

Without `--extract`, counselnotes produces a narrative strategic analysis covering:

1. **Case Overview** -- Summary of the matter from an advocate's perspective
2. **Tactical Opportunities** -- Specific advantages and openings to exploit
3. **Risk Assessment** -- Vulnerabilities and threats to address
4. **Strategic Recommendations** -- Prioritised actions with reasoning
5. **Case Management Notes** -- Procedural and practical considerations

**Structured extraction modes:**

With `--extract`, counselnotes produces structured JSON output:

- `all` -- All structured elements (citations, principles, and checklist combined)
- `citations` -- A list of all citations found in the documents with context
- `principles` -- Legal principles identified, each with supporting authority
- `checklist` -- An actionable checklist of steps to take

**Multi-document synthesis:**

When multiple files are provided, counselnotes synthesises findings across all
documents rather than analysing each in isolation. This is useful for building a
complete picture from multiple affidavits, reports, and correspondence.

**Model:** o3-pro
**BYOK required:** Yes

**Smith v Jones example:**

```bash
# Strategic analysis of case materials
litassist counselnotes affidavit_smith_jan2026.pdf \
  affidavit_jones_feb2026.pdf interim_orders_april2026.pdf

# Extract actionable checklist
litassist counselnotes --extract checklist case_materials.pdf

# Extract all structured elements with citation verification
litassist counselnotes --extract all --verify \
  affidavit_jones_feb2026.pdf
```

**Best practices:**

- Use digest for neutral factual analysis; use counselnotes for strategic
  perspective. They complement each other.
- Use `--extract checklist` to generate immediate action items from any document.
- When processing opposing party documents, counselnotes identifies weaknesses
  and opportunities that digest's neutral stance would not highlight.

For detailed counselnotes usage, extraction modes, and workflow integration, see
[COUNSELNOTES_GUIDE.md](COUNSELNOTES_GUIDE.md).

---

### 5.9 barbrief -- Barrister's Brief Generation

**Pipeline position:** Consolidation stage

**Purpose:** Create a structured barrister's brief combining case facts,
strategies, research, and supporting documents into a single comprehensive
document following Australian legal conventions.

**Syntax:**

```bash
litassist barbrief <case_facts> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `case_facts` | Path to structured case facts (10-heading format) |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--hearing-type` | `trial` / `directions` / `interlocutory` / `appeal` | Required: type of hearing |
| `--strategies` | path(s) | Brainstorm strategies files (glob supported) |
| `--research` | path(s) | Lookup/research reports (glob supported) |
| `--documents` | path(s) | Supporting documents (glob supported) |
| `--context` | text | Additional context to guide analysis |
| `--verify` | flag | Enable citation verification |
| `--output` | text | Custom output filename prefix |

**Hearing types:**

- `trial` -- Full trial brief with comprehensive legal analysis
- `directions` -- Focused brief for directions hearings
- `interlocutory` -- Brief for interlocutory applications
- `appeal` -- Appeal brief with grounds and error analysis

**Model:** o3-pro (extended output capacity: 32K tokens)
**BYOK required:** Yes

**Smith v Jones example:**

```bash
litassist barbrief case_facts.txt --hearing-type interlocutory \
  --strategies 'outputs/brainstorm_family_plaintiff_*.txt' \
  --research 'outputs/lookup_*.txt' \
  --documents 'affidavit_smith_jan2026.pdf' \
  --context "Application for interim orders allowing children \
  to remain in Brisbane pending final hearing" \
  --verify
```

**Best practices:**

- Provide as much supporting material as possible via `--strategies`, `--research`,
  and `--documents` for a comprehensive brief.
- Use glob patterns to include all relevant files from previous command outputs.
- Always use `--verify` for briefs intended for court.
- Match `--hearing-type` to the specific hearing; the output structure and depth
  adjust accordingly.

---

### 5.10 verify -- Post-Hoc Document Verification

**Pipeline position:** Quality assurance

**Purpose:** Perform comprehensive quality checks on legal documents. Supports
three types of verification: citation checking, legal soundness review, and
reasoning trace analysis. Optionally adds Chain of Verification (CoVe) as a
final check.

**Syntax:**

```bash
litassist verify <file> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `file` | Path to text file to verify |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--citations` | flag | Verify citations only |
| `--soundness` | flag | Verify legal soundness only |
| `--reasoning` | flag | Verify/generate reasoning trace only |
| `--cove` | flag | Add Chain of Verification as final check |
| `--reference` | glob | Reference files for context |
| `--cove-reference` | glob | Reference files for CoVe answer stage (requires `--cove`) |
| `--heavy` | flag | Use GPT-5.5 for reasoning and soundness |
| `--output` | text | Custom output filename prefix |

**Default behaviour:**

With no flags, all three verifications run: citations, soundness, and reasoning.
Individual flags select specific checks. The `--cove` flag adds CoVe as an
additional stage after the selected checks.

**Three verification types:**

1. **Citation verification** (GPT-5.5): Validates all citations against Jade.io
   via Google CSE. Reports each citation as verified, unverified, legislation
   (assumed valid), or international (recognised but not verifiable in Australian
   databases).

2. **Legal soundness** (Claude Opus 4.7): Reviews the document for legal accuracy,
   correct application of Australian law, appropriate jurisdiction references, and
   logical consistency.

3. **Reasoning trace** (Claude Sonnet 4.6): Analyses the document's reasoning
   structure, checking for logical gaps, unsupported conclusions, and assumptions
   that need explicit support.

**Heavy mode:**

The `--heavy` flag substitutes GPT-5.5 (with maximum reasoning effort) for the
reasoning and soundness stages. This provides the highest quality verification at
higher cost.

**Reference files:**

The `--reference` option provides additional documents as context during
verification. This is useful when the document being verified references exhibits,
affidavits, or other materials that the verifier needs to see.

**Models:** GPT-5.5 (citations), Claude Opus 4.7 (soundness), Claude Sonnet 4.6
(reasoning), GPT-5.5 (heavy mode)

**Smith v Jones example:**

```bash
# Full verification suite
litassist verify outputs/draft_outline_submissions_20260223_143855.txt

# Citations only with Chain of Verification
litassist verify outputs/draft_outline_submissions_20260223_143855.txt \
  --citations --cove

# Heavy verification with reference documents
litassist verify outputs/draft_outline_submissions_20260223_143855.txt \
  --heavy --reference 'exhibits/*.pdf'

# Maximum confidence: heavy mode with CoVe and all references
litassist verify outputs/draft_outline_submissions_20260223_143855.txt \
  --heavy --cove --cove-reference 'exhibits/*.pdf'
```

Sample verification output excerpt:

```
## Citation Verification Report

Citations Found: 12
Verified: 9
Unverified: 2
Legislation: 1

VERIFIED:
- AHB v AHA [2023] FedCFamC1F 1038 -- Verified via Jade.io
- CDJ v VAJ (1998) 197 CLR 172 -- Verified via Jade.io
- Bondelmonte v Bondelmonte [2017] HCA 8 -- Verified via Jade.io
...

UNVERIFIED:
- Taylor v Henderson [2024] FamCAFC 89 -- Not found in Jade.io
  ACTION: Manual verification required

LEGISLATION:
- Family Law Act 1975 (Cth) ss 60CA, 60CC -- Legislation (assumed valid)

## Soundness Assessment

Overall: Sound with minor observations
...
```

**Best practices:**

- Always run full verification on documents intended for court.
- Use `--cove` for high-stakes documents; it catches errors that standard
  verification misses.
- Use `--heavy` when maximum rigour is needed (e.g., final submissions).
- Provide reference documents via `--reference` when the document being verified
  cites specific exhibits.

---

### 5.11 verify-cove -- Standalone Chain of Verification

**Pipeline position:** Quality assurance (advanced)

**Purpose:** Run the full 4-stage Chain of Verification pipeline independently
on any document. This is a standalone version of the `--cove` flag on the verify
command, producing a detailed CoVe report.

**Syntax:**

```bash
litassist verify-cove <file> [OPTIONS]
```

**Arguments:**

| Argument | Description |
|----------|-------------|
| `file` | Path to legal document to verify |

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--reference` | glob | Reference files for the answer stage |
| `--heavy` | flag | Use GPT-5.5 for the answers stage |
| `--output` | text | Custom output filename prefix |

**The four CoVe stages:**

1. **Generate verification questions** (Claude Sonnet 4.6): The model reads the
   document and generates specific factual and legal questions that, if answered
   correctly, would confirm the document's accuracy.

2. **Answer questions** (GPT-5.5): A different model answers each
   question independently, without seeing the original document. If `--reference`
   files are provided, they are used as the sole factual source for answers.

3. **Detect inconsistencies** (Claude Sonnet 4.6): The original document is
   compared against the independent answers. Any discrepancies are flagged with
   specific details.

4. **Regenerate** (Claude Sonnet 4.6): If inconsistencies are found, a corrected
   version of the document is produced. If no issues are detected, the original
   is confirmed as accurate.

**Models:** Claude Sonnet 4.6 (questions, verify, final), GPT-5.5
(answers)

**Smith v Jones example:**

```bash
# Standard CoVe
litassist verify-cove outputs/draft_outline_submissions_20260223_143855.txt

# With reference documents and heavy mode
litassist verify-cove outputs/draft_outline_submissions_20260223_143855.txt \
  --reference 'exhibits/*.pdf' --heavy
```

**Best practices:**

- Use verify-cove for critical documents that will be filed with the court.
- Provide reference documents via `--reference` whenever possible; this gives the
  answer stage a factual grounding independent of the LLM's training data.
- Use `--heavy` (GPT-5.5) for the highest quality answers at the cost of higher
  API usage.

**See also:** Section 6.5 (Chain of Verification) for a detailed explanation of
the CoVe methodology.

---

### 5.12 test -- API Connectivity Verification

**Purpose:** Validate all API connections and web scraping capabilities.

**Syntax:**

```bash
litassist test
```

**What it tests:**

| Service | Check |
|---------|-------|
| OpenRouter | API key validation, model routing |
| Google CSE | Search API access, Jade.io CSE query |
| HTTP scraping | Direct HTTP fetching |
| PDF fetching | PDF download and extraction |

Placeholder credentials (containing `YOUR_`) are detected and skipped
automatically. The test reports which services are operational and which need
attention.

---

## 6. Key Concepts

### 6.1 extractfacts vs digest

Users frequently ask whether to use `extractfacts` or `digest` when processing
documents. The two commands serve different purposes:

| Aspect | extractfacts | digest |
|--------|-------------|--------|
| **Output format** | Rigid 10-heading structure | Flexible narrative |
| **Perspective** | Structured legal analysis | Neutral factual analysis |
| **Modes** | Single mode (extraction) | `summary` or `issues` |
| **Verification** | Auto-enabled self-critique | No verification stage |
| **Downstream use** | Required by brainstorm, strategy, barbrief | Standalone analysis |
| **Non-legal docs** | Rigid structure is a poor fit | Flexible; works well |
| **Primary purpose** | Create structured input for pipeline | Understand document content |

**When to use extractfacts:**

- You need structured input for brainstorm, strategy, or barbrief
- You are building the foundational `case_facts.txt` for a matter
- The documents contain information that maps to the 10-heading structure

**When to use digest:**

- You want to understand what a document says (chronological summary)
- You want to identify legal issues and problems (issues mode)
- The document is non-legal or does not fit the 10-heading structure
- You want a quick overview before deciding how to proceed

**Typical combined usage:**

1. Run `digest --mode summary` to understand the document
2. Run `digest --mode issues` to identify legal problems
3. Run `extractfacts` to create the structured input for the pipeline

### 6.2 brainstorm vs strategy

These commands are often confused because both produce "strategies." The key
distinction is scope:

| Aspect | brainstorm | strategy |
|--------|-----------|----------|
| **Scope** | Broad exploration of all possible approaches | Targeted plan for a specific outcome |
| **Input** | Case facts, optional research | Case facts, specific outcome, optional brainstorm output |
| **Output** | 30 strategies (15 orthodox + 15 unorthodox) + top 5 | Strategic options with probabilities, next steps, draft document |
| **Mindset** | "What could we do?" | "How do we achieve this specific result?" |
| **Creative scope** | Maximum (especially unorthodox) | Focused on feasibility |
| **Risk assessment** | Risk level per strategy | Probability percentages, hurdles, missing facts |
| **Draft document** | No | Yes, tailored to the outcome |
| **Citation depth** | Supporting authorities per strategy | Comprehensive citation in draft |

**How they work together:**

1. Run `brainstorm` first to explore all possible approaches
2. Review the output and identify promising directions
3. Run `strategy` with a specific `--outcome` and pass the brainstorm output via
   `--strategies`
4. The strategy command intelligently incorporates the brainstorm analysis into
   its tactical plan

**Example from Smith v Jones:**

- **Brainstorm** might generate strategies including: "Argue relocation was in
  children's best interests," "Challenge father's standing to claim alienation
  without expert evidence," "Seek appointment of ICL to independently assess
  children's wishes," etc.
- **Strategy** with `--outcome "Secure interim orders allowing children to remain
  in Brisbane"` would take the most relevant brainstorm strategies and develop a
  detailed tactical plan with probability assessments, evidence needed, procedural
  steps, and a draft application.

### 6.3 The 10-Heading Structure

The 10-heading structure is the standard format for case facts throughout
LitAssist. It is produced by `extractfacts`, validated by `strategy`, and consumed
by `brainstorm`, `strategy`, and `barbrief`.

**Full explanation of each heading:**

1. **Parties**
   - All parties involved, their roles (plaintiff, defendant, applicant,
     respondent), relationships to each other, and key characteristics relevant
     to the case.
   - Include legal representatives if known.

2. **Background**
   - Context and history leading to the current dispute. The narrative should
     explain how the situation arose and why it has become a legal matter.
   - Focus on facts, not legal argument.

3. **Key Events**
   - A chronological timeline of significant events. Each event should be dated
     (or approximately dated) and described factually.
   - Include both disputed and undisputed events, noting which are contested.

4. **Legal Issues**
   - The legal questions to be determined by the court. These should be framed
     as questions, not arguments.
   - Example: "Whether the relocation was in the best interests of the children
     under s 60CC of the Family Law Act 1975 (Cth)."

5. **Evidence Available**
   - Documents, witnesses, expert reports, and other evidence that is available
     or could be obtained.
   - Note the strength and relevance of each piece of evidence.

6. **Opposing Arguments**
   - Known or anticipated positions of the other side. Based on filed documents,
     correspondence, or reasonable inference.
   - Understanding the opposition's case is critical for strategy development.

7. **Procedural History**
   - Court filings, orders, directions, and procedural steps to date. Include
     dates and outcomes of each step.
   - Note upcoming dates and deadlines.

8. **Jurisdiction**
   - Which court has jurisdiction, which legislation applies, which procedural
     rules govern the proceedings.

9. **Applicable Law**
   - Key statutes, regulations, and leading cases relevant to the legal issues.
   - This is a summary, not a full legal analysis.

10. **Client Objectives**
    - What the client wants to achieve, both in the immediate proceedings and
      overall. Include both primary and fallback objectives.

**Template for manual creation:**

```text
## 1. Parties

[List all parties with roles and key details]

## 2. Background

[Narrative of how the dispute arose]

## 3. Key Events

[Chronological timeline with dates]

## 4. Legal Issues

[Questions to be determined]

## 5. Evidence Available

[Documents, witnesses, other evidence]

## 6. Opposing Arguments

[Known or anticipated positions of the other side]

## 7. Procedural History

[Court filings, orders, dates]

## 8. Jurisdiction

[Court, legislation, rules]

## 9. Applicable Law

[Key statutes and cases]

## 10. Client Objectives

[Primary and fallback objectives]
```

### 6.4 Citation Verification System

LitAssist uses a two-phase citation checking system to ensure all legal references
are accurate and verifiable.

#### Phase 1: Offline Pattern Validation

**Purpose:** Detect problematic citation patterns without internet access.

**What it catches:**

- **AI hallucinations**: Generic case names like "Smith v Jones" that are commonly
  fabricated by language models
- **Impossible citations**: Future dates, non-existent courts, anachronistic
  references (e.g., a Full Federal Court citation before 1977 when the court was
  established)
- **Suspicious patterns**: Placeholder names, single-letter parties,
  "Corporation v Corporation"
- **Format issues**: Malformed parallel citations, unrealistic page numbers

**How it works:**

- Runs instantly using pattern matching against Australian legal citation formats
- No internet connection required
- Provides immediate feedback

**Example detections:**

```
GENERIC CASE NAME: Smith v Jones
  FAILURE: Both parties use common surnames (possible AI hallucination)
  ACTION: Flagging for manual verification

ANACHRONISTIC CITATION: [1970] FCAFC 123
  FAILURE: Full Federal Court not established until 1977
  ACTION: Excluding impossible historical reference
```

#### Phase 2: Online Database Verification

**Purpose:** Confirm that citations actually exist in legal databases.

**What it verifies:**

- **Australian cases**: Checks against Jade.io via Google Custom Search Engine
- **International citations**: Recognises UK, US, NZ, and other international
  citations as valid but not verifiable in Australian databases
- **Legislation**: Recognises statutory references (Acts, Regulations) as valid
  without database lookup
- **Medium-neutral citations**: Validates format like `[2020] HCA 41` and
  retrieves URLs when found
- **Traditional citations**: Validates format like `(1980) 146 CLR 40`

**How it works:**

- Performs real-time Google CSE queries against Jade.io
- Retrieves URLs for verified Australian cases
- Handles international citations by classification rather than verification
- Results are cached to avoid duplicate lookups within a session

**Example verifications:**

```
[2020] HCA 41
  Verified: True
  URL: https://jade.io/article/...

[1932] AC 562
  Verified: True
  Reason: UK/International citation (Appeal Cases) - not in Australian databases

Family Law Act 1975 (Cth) s 60CC
  Verified: True
  Reason: Legislation (assumed valid)

[2024] FamCAFC 999
  Verified: False
  Reason: Not found in Jade.io
  ACTION: Manual verification required
```

#### How the Phases Work Together

1. **Validation** runs first to catch obvious problems through pattern analysis
2. **Verification** then confirms that remaining citations exist in databases
3. Together they provide comprehensive quality control

#### Command-Specific Citation Handling

Different commands respond to citation issues in different ways:

| Command | Validates | Verifies | Response to Issues |
|---------|-----------|----------|-------------------|
| lookup | Yes | Yes | Warnings in output |
| digest | Yes | Yes | Warnings per chunk |
| extractfacts | Yes | Yes | Enhanced error messages |
| brainstorm | Yes | Yes | Regenerates problematic strategies |
| strategy | Yes | Yes | Discards options with bad citations |
| draft | Yes | Yes | Appends warnings to draft |
| counselnotes | Yes | With `--verify` | Warnings in analysis |
| barbrief | Yes | With `--verify` | Verification report generated |

### 6.5 Chain of Verification (CoVe)

Chain of Verification is a self-verification technique that addresses the problem
of LLM hallucination in legal documents. Research has shown that LLMs produce
incorrect legal citations at high rates; CoVe provides a structured way to catch
and correct these errors.

**The four-stage factored process:**

1. **Generate verification questions**: A model reads the document and creates
   specific factual and legal questions that, if answered correctly, would confirm
   the document's accuracy. For example: "Is CDJ v VAJ (1998) 197 CLR 172 a real
   case?", "Does s 60CC of the Family Law Act 1975 (Cth) deal with best interests
   considerations?"

2. **Answer questions independently** (factored approach): A *different* model
   answers each question without seeing the original document. This prevents the
   answering model from simply repeating the same errors. When `--reference` files
   are provided, the answering model uses only those files as its factual source.

3. **Detect inconsistencies**: The original document is compared against the
   independent answers. Any discrepancy is flagged with specific details about what
   the original claims and what the independent answer found.

4. **Regenerate**: If inconsistencies are found, a corrected version of the
   document is produced, incorporating the corrections while preserving the
   document's structure and argumentation. If no issues are found, the original
   is confirmed.

**Why the "factored" approach matters:**

The key insight is that a model asked to "check its own work" tends to repeat its
original errors. By using a different model to answer verification questions, and
by withholding the original document during the answering stage, CoVe breaks this
self-reinforcing loop.

**Two access points:**

- `litassist verify --cove` -- adds CoVe as a final stage after standard
  verification
- `litassist verify-cove` -- runs the full CoVe pipeline as a standalone command

**When to use CoVe:**

- Court-filing quality documents where citation accuracy is critical
- Documents containing numerous case references
- High-stakes matters where errors could have serious consequences
- When standard verification flags concerns that need deeper investigation

### 6.6 Oversize Document Handling for draft

The draft command sends every supplied document (text and PDF alike) to the
configured draft model in a single full-context call. There is no retrieval,
embedding, or vector store.

Before the LLM call, draft computes the assembled payload size and compares it
against the model's context window (looked up from
`litassist/llm/model_capabilities.yaml`, refreshable via `litassist refresh`):

- **Below the soft threshold** (~49% of the input budget): proceeds silently.
- **Between soft and hard thresholds** (~49% to ~70%): prints a warning
  suggesting `litassist digest --mode summary <file>`, then proceeds.
- **At or above the hard threshold** (~70% of the input budget): raises a
  `ClickException` with the same `digest` guidance. No API call is made.

The provider call is also wrapped in a safety net: if the upstream model
rejects on context length despite our estimate, the error is reframed with
the same `digest` guidance instead of leaking a raw provider message.

Use `litassist digest --mode summary <file>` to produce a compressed version
of any oversize input, then feed the summary back into draft.

### 6.7 Large Document Handling and Chunking

LitAssist handles documents of any size through automatic chunking.

**How chunking works:**

- Documents exceeding `max_chars` (default: 200,000 characters, configurable in
  config.yaml) are split into chunks
- Each chunk is processed independently by the LLM
- Results are consolidated into a single output
- Chunk boundaries respect paragraph breaks where possible

**Which commands chunk:**

| Command | Chunking Behaviour |
|---------|-------------------|
| digest | Per-file chunking, results consolidated |
| extractfacts | Multi-file consolidation into structured output |
| draft | Single full-context call; oversize inputs require `digest --mode summary` first (see 6.6) |
| brainstorm | Research files passed as context (truncated if very large) |
| strategy | Case facts validated; strategies passed as context |

**Token counting:**

LitAssist uses tiktoken for accurate token counting. Large processing jobs
(exceeding approximately 1.5 million characters) trigger a warning with estimated
processing time.

**Configuration:**

```yaml
general:
  max_chars: 200000     # Chunk size for digest / extractfacts / counselnotes
                        # multi-chunk processing (~50K tokens). Per-command
                        # chunk size for digest is now derived from the
                        # model's context window via
                        # LLMClientFactory.get_input_budget_for_command(),
                        # so this fallback only applies when no model
                        # capability data is available.
```

### 6.8 Verification Modes and the --verify / --heavy / --noverify Switches

Several commands include built-in verification stages. The behaviour is controlled
by three switches:

**--verify (auto-enabled on some commands):**

- On `extractfacts` and `strategy`, verification is auto-enabled. The `--verify`
  flag is accepted but produces a reminder that verification is already active.
- On `brainstorm`, `counselnotes`, and `barbrief`, `--verify` explicitly enables
  citation verification.

**--heavy:**

Substitutes GPT-5.5 (with maximum reasoning effort) for the standard
verification model. This provides the highest quality verification at higher cost.
Available on: `extractfacts`, `brainstorm`, `strategy`, `draft`, `verify`,
`verify-cove`.

**--noverify:**

Skips the verification stage entirely. Use this during iteration and testing, but
never for documents intended for court or client review.

**Auto-verification triggers in draft:**

The draft command includes automatic hallucination detection that triggers
verification when the output contains:

- Citations (case references, legislation)
- Percentage claims or statistical assertions
- Strong legal conclusions
- Statutory section references

---

## 7. Model Configuration

### 7.1 Task-Based Model Selection

LitAssist matches each command to the model best suited for its job:

Current model assignments are defined in `litassist/llm/model_configs.yaml`. Registered commands are defined in `litassist/commands/__init__.py`.

| Role | Purpose | Model | Commands |
|------|---------|-------|----------|
| **Legal Reasoning** | Extraction, digest, case planning, light verification, CoVe scaffolding | Claude Sonnet 4.6 | 12 |
| **Advanced Drafting** | Documents, briefs, deep analysis | o3-pro | 5 |
| **Critical Verification** | Highest-stakes soundness checks | GPT-5.5 | 4 |
| **Standard Verification** | Self-critique, CoVe answers | GPT-5.5 | 2 |
| **Strategy and Soundness** | Strategic options and logical soundness analysis | Claude Opus 4.7 | 2 |
| **Lookup Synthesis** | Case-law research synthesis | Gemini 3.5 Flash | 1 |
| **Creative Ideation** | Unorthodox brainstorming | Grok 4.20 | 1 |

**Rationale for task specialisation:**

- **Verification** stages use GPT-5.5 for both standard and heavy paths, with
  reasoning effort increased for heavy modes.
- **Legal reasoning** (Sonnet 4.6) handles the bulk of work at $3/$15 per M
  tokens with 1M context window and strong legal benchmarks.
- **Drafting** (o3-pro) provides extended reasoning traces for structured
  document generation.
- **Creative** (Grok 4.20) uses high temperature with auto-verification.

### 7.2 Complete Command-to-Model Assignment Table

| Config Key | Model | Command / Stage | BYOK |
|-----------|-------|-----------------|------|
| `extractfacts` | Claude Sonnet 4.6 | Fact extraction | No |
| `lookup` | Gemini 3.5 Flash | Case law research synthesis | No |
| `digest-summary` | Claude Sonnet 4.6 | Document summary | No |
| `digest-issues` | Claude Sonnet 4.6 | Issue identification | No |
| `brainstorm-orthodox` | Claude Sonnet 4.6 | Orthodox strategies | No |
| `brainstorm-unorthodox` | Grok 4.20 | Unorthodox strategies | No |
| `brainstorm-analysis` | o3-pro | Strategy ranking and top 5 | Yes |
| `strategy` | Claude Opus 4.7 | Strategic options | No |
| `strategy-analysis` | o3-pro | Strategy analysis | Yes |
| `draft` | o3-pro | Document generation | Yes |
| `counselnotes` | o3-pro | Advocate analysis | Yes |
| `barbrief` | o3-pro | Barrister's brief | Yes |
| `caseplan` | Claude Sonnet 4.6 | Full plan generation | No |
| `caseplan-assessment` | Claude Sonnet 4.6 | Budget assessment | No |
| `verification` | GPT-5.5 | Standard citation verification | No |
| `verification-light` | Claude Sonnet 4.6 | Quick verification checks | No |
| `verification-heavy` | GPT-5.5 | Heavy citation verification | No |
| `verify-reasoning` | Claude Sonnet 4.6 | Reasoning trace analysis | No |
| `verify-reasoning-heavy` | GPT-5.5 | Heavy reasoning analysis | No |
| `verify-soundness` | Claude Opus 4.7 | Legal soundness review | No |
| `verify-soundness-heavy` | GPT-5.5 | Heavy soundness review | No |
| `cove-questions` | Claude Sonnet 4.6 | CoVe question generation | No |
| `cove-answers` | GPT-5.5 | CoVe independent answers | No |
| `cove-answers-heavy` | GPT-5.5 | CoVe heavy answers | No |
| `cove-verify` | Claude Sonnet 4.6 | CoVe inconsistency detection | No |
| `cove-final` | Claude Sonnet 4.6 | CoVe final output | No |

All model assignments are defined in `litassist/llm/model_configs.yaml`.

### 7.3 Model Parameters

Each model configuration includes parameters that control its behaviour:

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| `temperature` | Controls randomness. Lower = more deterministic, higher = more creative | 0.0 - 0.8 |
| `top_p` | Nucleus sampling threshold. Lower = more focused, higher = more diverse | 0.15 - 0.95 |
| `thinking_effort` | Reasoning depth for models that support it | `low`, `medium`, `high`, `max` |
| `disable_tools` | Prevents the model from attempting tool calls | Always `true` |
| `enforce_citations` | Requires the model to include citations in output | `true` for extractfacts |
| `verbosity` | Controls output detail level | `low`, `medium`, `high` |
| `min_p` | Minimum probability threshold (Grok 4.20) | 0.05 |
| `repetition_penalty` | Discourages repetitive output (Grok 4.20) | 1.2 |

**Why parameters vary by command:**

- `extractfacts` uses temperature=0 and top_p=0.15 for maximum determinism in
  fact extraction
- `brainstorm-unorthodox` uses temperature=0.8 with repetition_penalty=1.2 to
  encourage creative, non-repetitive strategies
- Verification models use temperature=0.2 for consistent, reproducible checks
- `draft` and `barbrief` use verbosity="high" for comprehensive output

### 7.4 OpenRouter Routing

All LLM calls route through OpenRouter's API. Model names follow the
`provider/model` convention with a `/` separator:

- `openai/o3-pro`
- `openai/gpt-5.5`
- `anthropic/claude-sonnet-4.6`
- `x-ai/grok-4.20`
- `anthropic/claude-opus-4.7`

OpenRouter handles authentication, rate limiting, and provider routing. BYOK
commands (those using `openai/o3-pro`) require an OpenAI provider key added in
the OpenRouter integrations dashboard. This project does not carry a separate
OpenAI key in `config.yaml`; only `openrouter.api_key` is the bearer token for
LLM requests.

The `disable_tools: true` parameter is set on all model configurations to prevent
models from attempting tool calls, which is not supported in LitAssist's pipeline.

---

## 8. Workflows

### 8.1 Standard Litigation Workflow

The full pipeline from raw documents to verified legal output:

```
1. caseplan      Plan the workflow (or skip if you know what you need)
2. extractfacts  Structure raw documents into 10-heading format
3. lookup        Research relevant case law
4. brainstorm    Explore all possible strategies
5. strategy      Develop a targeted plan for a specific outcome
6. draft         Create citation-rich legal documents
7. verify        Check citations, soundness, and reasoning
```

**Smith v Jones complete walkthrough:**

```bash
# Set up project directory
mkdir ~/legal-cases/smith-v-jones-2026
cd ~/legal-cases/smith-v-jones-2026

# 1. Plan the workflow
litassist caseplan case_facts_skeleton.txt --budget comprehensive

# 2. Extract structured facts from court documents
litassist extractfacts interim_orders_april2026.pdf \
  contravention_application_feb2026.pdf \
  affidavit_smith_jan2026.pdf affidavit_jones_feb2026.pdf
# Copy output to case_facts.txt and review/refine

# 3. Research key legal issues
litassist lookup "best interests paramount consideration interstate \
  relocation children" --mode irac --comprehensive
litassist lookup "parental alienation evidence requirements Australian \
  family law" --mode irac --comprehensive

# 4. Brainstorm strategies
litassist brainstorm --side plaintiff --area family \
  --facts case_facts.txt \
  --research 'outputs/lookup_*.txt'

# 5. Develop targeted strategy
litassist strategy case_facts.txt \
  --outcome "Secure interim orders allowing children to remain in Brisbane" \
  --strategies outputs/brainstorm_family_plaintiff_*.txt

# 6. Draft submissions
litassist draft case_facts.txt \
  outputs/strategy_secure_interim_orders_*.txt \
  "outline of submissions regarding relocation"

# 7. Verify the draft
litassist verify outputs/draft_outline_submissions_*.txt \
  --heavy --cove --reference 'exhibits/*.pdf'
```

### 8.2 Document Review Workflow

For reviewing incoming documents (opposing briefs, judgements, affidavits):

```bash
# Step 1: Neutral factual analysis
litassist digest opposing_response_affidavit.pdf --mode issues \
  --context "Review for weaknesses and inconsistencies"

# Step 2: Strategic perspective
litassist counselnotes opposing_response_affidavit.pdf

# Step 3: Extract actionable items
litassist counselnotes --extract checklist opposing_response_affidavit.pdf
```

This three-step approach gives you:

1. A neutral identification of the issues and facts in the document
2. A strategic assessment of opportunities and risks
3. A concrete checklist of actions to take in response

### 8.3 CasePlan Automated Workflow

Let LitAssist plan the entire workflow for you:

```bash
# Step 1: Get budget recommendation
litassist caseplan case_facts.txt

# Step 2: Generate full plan with executable commands
litassist caseplan case_facts.txt --budget standard

# Step 3: Review the plan, then execute the generated script
bash outputs/caseplan_commands_standard_*.txt
```

The generated script includes all commands in the correct order with appropriate
switches and rationale comments. Review and adjust before running.

**Iterating the plan:**

As the case develops and new documents arrive, regenerate the plan:

```bash
# Update case_facts.txt with new information
# Then regenerate the plan
litassist caseplan case_facts.txt --budget comprehensive \
  --context "New expert report received, settlement conference scheduled"
```

### 8.4 Verification Pipeline

Choose the verification level appropriate to the document's purpose:

**Level 1 -- Standard (everyday work):**

```bash
litassist verify draft.txt
```

Runs all three checks: citations, soundness, reasoning.

**Level 2 -- Enhanced (important documents):**

```bash
litassist verify draft.txt --cove
```

Adds Chain of Verification for deeper fact-checking.

**Level 3 -- Maximum (court filings):**

```bash
litassist verify draft.txt --heavy --cove \
  --cove-reference 'exhibits/*.pdf' \
  --reference 'exhibits/*.pdf'
```

Uses GPT-5.5 for all verification stages and provides reference documents for
both standard verification and CoVe.

**Standalone CoVe for specific documents:**

```bash
litassist verify-cove draft.txt --reference 'exhibits/*.pdf' --heavy
```

### 8.5 Research-to-Draft Pipeline

A focused workflow for producing a single well-researched document:

```bash
# 1. Research the specific legal question
litassist lookup "duty of care medical negligence surgical errors" \
  --mode irac --comprehensive \
  --context "Hospital setting, postoperative complications"

# 2. Extract facts from case materials
litassist extractfacts medical_records.pdf expert_report.pdf \
  complaint_letter.pdf

# 3. Brainstorm with research context
litassist brainstorm --side plaintiff --area civil \
  --facts case_facts.txt \
  --research 'outputs/lookup_*.txt'

# 4. Develop strategy for specific outcome
litassist strategy case_facts.txt \
  --outcome "Establish breach of duty of care" \
  --strategies outputs/brainstorm_civil_plaintiff_*.txt

# 5. Draft the document
litassist draft case_facts.txt \
  outputs/strategy_establish_breach_*.txt \
  outputs/lookup_duty_of_care_*.txt \
  "statement of claim"

# 6. Verify
litassist verify outputs/draft_statement_of_claim_*.txt --heavy --cove
```

Each stage builds on the previous one, with file outputs flowing naturally between
commands via glob patterns.

---

## 9. Prompt Template System

LitAssist uses a centralised prompt management system. All prompts are stored in
YAML files under `litassist/prompts/` and accessed via the `PromptManager` class.
This ensures consistency across commands and simplifies maintenance.

**Template categories:**

| File | Contents |
|------|----------|
| `base.yaml` | Australian law context, anti-injection, anti-hallucination, date handling |
| `formats.yaml` | Output format templates (10-heading, IRAC, chronological, etc.) |
| `documents.yaml` | Legal document type templates |
| `warnings.yaml` | Validation and warning messages |
| `lookup.yaml` | Case law research prompts |
| `processing.yaml` | Document processing prompts |
| `strategies.yaml` | Strategy generation prompts |
| `barbrief.yaml` | Barrister's brief prompts |
| `verification.yaml` | Verification and self-critique prompts |
| `system_feedback.yaml` | Error messages and user feedback |
| `caseplan.yaml` | Workflow planning prompts |

Templates are loaded lazily on first access and cached for the session.

For full prompt system documentation including architecture, customisation, and
testing, see [PROMPTS_README.md](PROMPTS_README.md).

---

## 10. Troubleshooting

### 10.1 Configuration Issues

**No config file found:**

```
Error: No config.yaml found.
```

Configuration must be at `~/.config/litassist/config.yaml`. This is the only
location checked (unless `LITASSIST_CONFIG` is set).

```bash
mkdir -p ~/.config/litassist
cp config.yaml.template ~/.config/litassist/config.yaml
# Edit with your API keys
```

**Missing required keys:**

```
Error: config.yaml missing key 'openrouter'
```

Ensure all required sections exist in config.yaml. Run `litassist test` to verify
each service.

**Invalid YAML syntax:**

```
Error: Invalid YAML in config.yaml: ...
```

Check for indentation errors, missing colons, or unquoted special characters.
YAML is sensitive to formatting.

### 10.2 API Connectivity

**BYOK not configured:**

```
BYOK required for o3-pro
```

Commands using `openai/o3-pro` (draft, counselnotes, barbrief,
brainstorm-analysis, strategy-analysis) require an OpenAI provider key added
to OpenRouter integrations. Open `https://openrouter.ai/settings/integrations`,
add the OpenAI key there, and confirm `openrouter.api_key` is valid locally.
This project does not carry a separate OpenAI key in `config.yaml`.

**OpenRouter connection failures:**

Check that `openrouter.api_key` is valid and that the `api_base` URL is correct.
Run `litassist test` to diagnose.

**Google CSE quota exceeded:**

The free tier provides 100 CSE requests per day. If exceeded, citation
verification and lookup commands will fail. Either wait until the quota resets or
enable paid usage in the Google Cloud console.

### 10.3 Large File Processing

**Slow processing:**

Files exceeding `max_chars` (default: 200,000 characters) are chunked. Processing
time scales with the number of chunks. The heartbeat indicator
("...still working...") confirms the command is active. Adjust
`heartbeat_interval` in config.yaml if needed.

**Out of memory:**

For very large documents (many hundreds of pages), process in stages. For example,
split a large PDF into sections and run extractfacts or digest on each section
separately.

### 10.4 Citation Verification Failures

**Common causes:**

- **CSE quota exhausted**: 100 free requests/day. Check Google Cloud console.
- **Citation format**: Non-standard formats may not be recognised. Australian
  medium-neutral (`[YYYY] COURT NUM`) and traditional (`(YYYY) VOL REP PAGE`)
  formats are supported.
- **Case not in Jade.io**: Not all Australian cases are indexed. Older or
  unreported decisions may not be found.
- **International citations**: UK, US, NZ citations are recognised but cannot be
  verified against Australian databases. They are flagged as "international."

**Workaround for testing:**

Use `--noverify` to skip verification during iteration. Always verify before
relying on citations for court filings.

### 10.5 Draft Quality Issues

**Sparse or unfocused output:**

- Ensure input files use `.txt` extension. Files with `.md` extension may not be
  processed as expected.
- Provide more context files (case facts, strategies, research) to give the model
  better grounding.
- For very large bundles, summarise with `litassist digest --mode summary` first
  and feed the summary to draft (see section 6.6 for the oversize-input policy).

### 10.6 Command Validation Errors

**Missing 10-heading structure:**

```
Error: Input file does not appear to follow the 10-heading structure
```

The `strategy` command validates that the input contains the expected headings.
Use `extractfacts` to generate properly structured case facts, or create them
manually following the template in Section 6.3.

**Missing required options:**

```
Error: Missing option '--side'
```

Some options are required for specific commands. Check the command reference
(Section 5) for required options.

### 10.7 Common Error Messages

| Error | Cause | Resolution |
|-------|-------|------------|
| `config.yaml missing key 'X'` | Required config section missing | Add the section to config.yaml |
| `BYOK required for o3-pro` | OpenAI provider key not configured at OpenRouter | Add it at https://openrouter.ai/settings/integrations |
| `Google CSE quota exceeded` | 100 daily free requests used | Wait or enable paid usage |
| `Invalid YAML in config.yaml` | Syntax error in config file | Fix YAML formatting |
| `No config.yaml found` | Config not at expected path | Create at `~/.config/litassist/config.yaml` |
| `Input file does not appear to follow the 10-heading structure` | strategy input missing headings | Use extractfacts or create manually |

---

## 11. Related Guides

- [LitAssist User Guide](LitAssist_User_Guide.md) -- concise command reference
  for day-to-day use
- [Counsel's Notes Guide](COUNSELNOTES_GUIDE.md) -- detailed counselnotes command
  usage, extraction modes, and workflow integration
- [Google CSE Setup](Google%20CSE%20setup.md) -- step-by-step guide for setting up
  Jade.io, AustLII, and comprehensive search engines
- [Prompt Management](PROMPTS_README.md) -- prompt template system architecture
  and customisation
- [Non-Legal Documents](non_legal_documents.md) -- adapting LitAssist for
  documents outside standard legal workflows
