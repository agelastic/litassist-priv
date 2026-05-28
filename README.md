# LitAssist

Last updated: 28/05/2026

**LitAssist** is a comprehensive legal workflow automation tool designed for Australian legal practice. It provides a structured end-to-end pipeline for litigation support:

```
plan → research → analyse → structure → brainstorm → strategy → draft
```

**Start with CasePlan:**  
ALWAYS begin with the `caseplan` command, even with a skeleton `case_facts.txt` file. It generates a complete litigation roadmap with executable commands, helping you systematically build your case. The plan includes cost estimates, time projections, and explains every technical choice.

```mermaid
graph TD
    CP["CasePlan<br/>Start Here!"] --> A["Lookup<br/>Research"]
    CP --> B["Digest<br/>Analyse"]
    CP --> C["ExtractFacts<br/>Structure"]
    
    A --> D["Brainstorm<br/>Generate Options"]
    B --> D
    C --> D
    
    D --> E["Strategy<br/>Plan Approach"]
    E --> F["Draft<br/>Create Documents"]
    
    B --> CN["CounselNotes<br/>Strategic Analysis"]
    C --> CN
    CN --> E
    
    C --> BB["Barbrief<br/>Barrister's Brief"]
    D --> BB
    E --> BB
    A --> BB
    
    G[Utilities] --> H["Test<br/>API Check"]
    G --> I["Audit<br/>Logging"]
    G --> J["Mock<br/>Mode"]
    
    style CP fill:#f9f,stroke:#333,stroke-width:4px
    style A fill:#e1f5fe
    style B fill:#e1f5fe
    style C fill:#e1f5fe
    style D fill:#fff3e0
    style E fill:#fff3e0
    style F fill:#e8f5e9
    style CN fill:#f3e5f5
    style BB fill:#f3e5f5
```

## Core Commands

**Sources of truth:** registered commands are defined in `litassist/commands/__init__.py`; current model assignments are defined in `litassist/llm/model_configs.yaml`; strategic feature planning lives in `ROADMAP.md`; active technical debt lives in `TODO.md`.

### Start Here: CasePlan
- **CasePlan**: START HERE! Automated phased workflow planning with executable scripts
  - Generates complete litigation roadmaps tailored to your case
  - Creates executable bash scripts with all commands ready to run
  - Explains every technical choice with "Switch rationale" comments
  - Adapts to case complexity: minimal, standard, or comprehensive workflows

### Primary Workflow Commands
- **Lookup**: Rapid case-law research (Jade.io/AustLII via Google Custom Search + Gemini 3.5 Flash)
- **Digest**: Mass document processing (chronological summaries or issue-spotting via Claude Sonnet 4.6)
- **ExtractFacts**: Automatic extraction of case facts into a structured file (Claude Sonnet 4.6)
- **Brainstorm**: Creative legal strategy generation (unorthodox strategies via Grok 4.20, analysis via o3-pro)
- **Strategy**: Targeted legal options with probability assessments (Claude Opus 4.7 with o3-pro analysis)
- **Draft**: Citation-rich document creation (superior technical writing via o3-pro)

### Specialized Commands
- **CounselNotes**: Strategic advocate analysis with structured extractions (o3-pro)
- **Barbrief**: Comprehensive barrister's briefs for litigation (extended output via o3-pro)

For detailed usage guidance, see the [LitAssist User Guide](docs/user/LitAssist_User_Guide.md).

## Installation

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/your-org/litassist.git
cd litassist

# 2. Install globally with pipx (recommended)
brew install pipx
pipx install -e .
pipx inject litassist tiktoken
pipx ensurepath
source ~/.zshrc

# For local development with pip instead of pipx:
# pip install -r requirements.txt

# 3. Setup configuration
cp config.yaml.template config.yaml
# Edit config.yaml with your API keys

# 4. Copy config to global location
mkdir -p ~/.config/litassist
cp config.yaml ~/.config/litassist/

# 5. Use from anywhere
cd ~/any-directory/
litassist caseplan case_facts.txt
```

**For detailed installation options, troubleshooting, and advanced setup, see the [Installation Guide](INSTALLATION.md)**

## Configuration

Required API keys in `config.yaml` (see [config.yaml.template](config.yaml.template) for reference):

```yaml
openrouter:
  api_key:    "YOUR_OPENROUTER_KEY"
  api_base:   "https://openrouter.ai/api/v1"   # optional

google_cse:
  api_key:                "YOUR_GOOGLE_API_KEY"         # API key for Google Custom Search
  cse_id:                 "YOUR_JADE_CSE_ID"           # Google CSE for Jade.io
  cse_id_comprehensive:   "YOUR_COMPREHENSIVE_CSE_ID"  # Optional: broader legal sources (gov.au etc.)
  cse_id_austlii:         "YOUR_AUSTLII_CSE_ID"        # Optional: AustLII CSE for Australian legal cases

llm:

general:
  heartbeat_interval: 10  # Progress indicator interval in seconds (default: 10)
  max_chars: 200000       # Document chunking: characters per chunk for digest/extractfacts (default: 200000 ≈ 50K tokens)
```

### OpenRouter Configuration

OpenRouter is the sole API gateway for all LLM calls. LitAssist sends every
LLM request with `openrouter.api_key`. There is no separate OpenAI key in
`config.yaml`; provider-specific BYOK (e.g. for `openai/o3-pro` access) is
configured in OpenRouter's integrations dashboard, not in this project's
config.

**BYOK status:**
- `openai/o3-pro` requires an OpenAI provider key in OpenRouter integrations (draft, barbrief, counselnotes, brainstorm-analysis, strategy-analysis)
- `openai/gpt-5.5` currently runs as a standard OpenRouter model
- Claude Sonnet 4.6 available without BYOK

**Quick BYOK Setup:**
1. Create or confirm your OpenRouter API key and put it in `openrouter.api_key`.
2. Go to [OpenRouter Settings](https://openrouter.ai/settings/integrations).
3. Add an OpenAI provider key under integrations for o3-pro access.
4. Save and verify model availability on your OpenRouter dashboard.

Anthropic models currently run without BYOK on OpenRouter.

### Model Configuration & BYOK Requirements

LitAssist uses task-based model selection, matching each command to the model best suited for its job:

- **Claude Sonnet 4.6** - extraction, digest, case planning, CoVe scaffolding, light/reasoning verification
- **Claude Opus 4.7** - primary strategy generation and legal soundness checking
- **OpenAI GPT-5.5** - standard and heavy verification, heavy reasoning, and CoVe answer stages
- **OpenAI o3-pro** - drafting, briefs, counsel notes, and analysis stages
- **Google Gemini 3.5 Flash** - lookup synthesis over fetched research sources
- **xAI Grok 4.20** - unorthodox brainstorm generation

| Command | Model | BYOK Required | Purpose |
|---------|-------|--------------|---------|
| **caseplan** | Claude Sonnet 4.6 | No | Workflow planning - START HERE! |
| **lookup** | Gemini 3.5 Flash | No | Case-law research synthesis |
| **digest** | Claude Sonnet 4.6 | No | Document analysis and issue identification |
| **extractfacts** | Claude Sonnet 4.6 | No | Structured fact extraction with citations |
| **brainstorm** | Claude Sonnet 4.6 / Grok 4.20 | No | Legal strategies + creative ideation |
| **strategy** | Claude Opus 4.7 / o3-pro | Yes for analysis stage | Strategic options and analysis |
| **draft** | OpenAI o3-pro | **Yes** | Superior technical legal writing |
| **counselnotes** | OpenAI o3-pro | **Yes** | Strategic advocate analysis |
| **barbrief** | OpenAI o3-pro | **Yes** | Comprehensive barrister's briefs |
| **verify** | GPT-5.5 / Claude Opus 4.7 / Claude Sonnet 4.6 | No | Citation, soundness, and reasoning verification |
| **verify-cove** | Claude Sonnet 4.6 / GPT-5.5 | No | Chain-of-Verification pipeline |

#### Why These Models?

**Claude Sonnet 4.6** (February 2026):
- Explicitly "state of the art on complex litigation tasks"
- Superior legal domain knowledge and reasoning
- 80% cost reduction vs previous models
- Extended thinking mode for multi-step analysis

**GPT-5.5**:
- Industry-leading accuracy: <1.6% hallucination rate
- 6x fewer factual errors than previous models
- Critical for legal verification where accuracy is paramount

**OpenAI o3-pro**:
- Advanced reasoning for technical drafting
- Extended output capacity (32K tokens) for briefs
- Specialized for structured legal documents

#### Required BYOK Setup

Commands using restricted models (`draft`, `barbrief`, `counselnotes`, and o3-pro analysis stages) require BYOK setup on OpenRouter. Without BYOK, these commands will fail with authentication errors.

**Note:** Check the [OpenRouter Models page](https://openrouter.ai/models) to verify which models are available with your API key vs. requiring BYOK.

For detailed API configuration, model availability, and troubleshooting, see the [LitAssist User Guide](docs/user/LitAssist_User_Guide.md#configuration).

## Command Reference

Basic usage:
```bash
litassist [GLOBAL OPTIONS] <command> [ARGS] [OPTIONS]
```

Global options:
- `--log-format [json|markdown]`: Choose audit-log format (default: from config.yaml)
- `--verbose`: Enable debug-level logging

### Core Pipeline Commands

### 1. caseplan - Your Starting Point

**ALWAYS START HERE!** This command is your litigation GPS, generating a complete roadmap tailored to your case.

```bash
# Step 1: Get budget recommendation based on case complexity
litassist caseplan case_facts.txt

# Step 2: Generate full plan with executable script
litassist caseplan case_facts.txt --budget standard

# Step 3: Execute the generated workflow
bash caseplan_commands_standard_*.txt
```

**Key Features:**
- **Complexity Analysis**: Evaluates legal, factual, procedural, and strategic complexity
- **Budget Levels**: 
  - `minimal`: Quick matters, 5-7 phases
  - `standard`: Typical litigation, 10-12 phases  
  - `comprehensive`: Complex cases, 15-25 phases
- **Context**: Use `--context "breach of contract"` to guide analysis and prioritize relevant workflow phases
- **Executable Output**: Creates bash script with all commands ready to run
- **Switch Explanations**: Every technical choice explained inline

**Example Output:**
```bash
# Phase 1: Extract Initial Facts
litassist extractfacts contract.pdf emails.pdf
# Switch rationale: Standard extraction, no special parameters needed

# Phase 2: Research Contract Breach Elements
litassist lookup "elements of contract breach and damages" --mode irac --comprehensive
# Switch rationale: --comprehensive for detailed analysis, --mode irac for structured output
```

### 2. lookup - Rapid case-law search with automatic citation
   ```bash
   litassist lookup "What defences exist to adverse costs orders?"
   litassist lookup "Question?" --mode broad --comprehensive
   litassist lookup "contract formation elements" --extract citations
   litassist lookup "negligence principles" --extract principles  
   litassist lookup "discovery requirements" --extract checklist
   ```
   
   Options:
   - `--mode [irac|broad]`: Analysis format (default: irac)
   - `--extract [citations|principles|checklist]`: Extract specific information in structured format
   - `--comprehensive`: Enable comprehensive mode: standard searches yield up to 5
     results each from Jade and AustLII; comprehensive mode yields up to 10 results
     each from Jade, AustLII, and a secondary CSE.

### 3. digest - Process large documents for summaries or issues

```bash
litassist digest bundle.pdf --mode [summary|issues]
```

### 4. extractfacts - Extract structured case facts from documents

```bash
# Single file
litassist extractfacts document.pdf

# Multiple files
litassist extractfacts file1.pdf file2.txt file3.pdf

# Creates: extractfacts_[combined_slugs]_YYYYMMDD_HHMMSS.txt
# Note: case_facts.txt must be created or edited manually
```

### 5. brainstorm - Generate comprehensive legal strategies with reasoning traces

```bash
# Default: uses case_facts.txt if present in current directory
litassist brainstorm --side [plaintiff|defendant|accused] --area [criminal|civil|family|commercial|administrative]

# Specify facts file(s) explicitly
litassist brainstorm --facts case_facts.txt --side plaintiff --area civil

# Use multiple facts files with glob patterns
litassist brainstorm --facts 'case_*.txt' --side plaintiff --area civil

# Add research context (supports glob patterns)
litassist brainstorm --side plaintiff --area civil --research 'outputs/lookup_*.txt'

# Multiple research files with selective patterns
litassist brainstorm --side plaintiff --area civil --research 'outputs/lookup_*gift*.txt' --research 'outputs/lookup_*trust*.txt'

# Creates: brainstorm_[area]_[side]_YYYYMMDD_HHMMSS.txt (main strategies)
#          brainstorm_[area]_[side]_YYYYMMDD_HHMMSS_orthodox_reasoning.txt
#          brainstorm_[area]_[side]_YYYYMMDD_HHMMSS_unorthodox_reasoning.txt  
#          brainstorm_[area]_[side]_YYYYMMDD_HHMMSS_analysis_reasoning.txt
# Note: strategies.txt must be created or edited manually
```

### 6. strategy - Generate targeted legal options and draft documents

```bash
litassist strategy case_facts.txt --outcome "Obtain interim injunction against defendant"
# Or incorporate brainstormed strategies
litassist strategy case_facts.txt --outcome "..." --strategies strategies.txt
```

### 7. draft - Create citation-rich legal drafts with intelligent document recognition

```bash
# Single document
litassist draft case_facts.txt "skeleton argument on jurisdictional error"
# Multiple documents (automatically recognizes case_facts.txt and strategies.txt)
litassist draft case_facts.txt strategies.txt "argument based on strategy #3"
# Mix text files and PDFs
litassist draft case_facts.txt bundle.pdf "comprehensive submission"
```

### 8. counselnotes - Generate strategic advocate analysis

```bash
# Single document
litassist counselnotes document.pdf
# Multiple documents
litassist counselnotes doc1.pdf doc2.txt doc3.pdf
# Extract specific sections
litassist counselnotes case_bundle.pdf --extract all
```

### 9. barbrief - Generate comprehensive barrister's briefs for litigation

```bash
# Basic brief for trial
litassist barbrief case_facts.txt --hearing-type trial
# Appeal brief with strategies
litassist barbrief case_facts.txt --hearing-type appeal --strategies strategies.txt
# Full brief with all materials
litassist barbrief case_facts.txt --hearing-type interlocutory \
  --strategies strategies.txt \
  --research lookup_report1.txt --research lookup_report2.txt \
  --documents affidavit.pdf --documents exhibit_a.pdf \
  --context "Focus on jurisdictional issues" \
  --verify
```

Required:
- Case facts in 10-heading format (from extractfacts)
- `--hearing-type [trial|directions|interlocutory|appeal]`

Options:
- `--strategies FILE`: Brainstormed strategies
- `--research FILE`: Lookup/research reports (multiple allowed)
- `--documents FILE`: Supporting documents (multiple allowed)
- `--context TEXT`: Additional context to guide the analysis
- `--verify`: Enable citation verification

### Utility Commands

- **test** - Verify API connectivity
  ```bash
  litassist test
  ```

## Example Files

The [`examples/`](examples/) directory contains sample files for testing all commands, based on the fictional *Smith v Jones* family law case.

## Output Files & Logging

### Command Output Files
All commands now save their output to timestamped text files without overwriting existing files:

- **caseplan**: `caseplan_[budget]_YYYYMMDD_HHMMSS.txt` and `caseplan_commands_[budget]_YYYYMMDD_HHMMSS.txt`
- **lookup**: `lookup_[query_slug]_YYYYMMDD_HHMMSS.txt`
- **digest**: `digest_[mode]_[filename_slug]_YYYYMMDD_HHMMSS.txt`
- **brainstorm**: `brainstorm_[area]_[side]_YYYYMMDD_HHMMSS.txt`
- **extractfacts**: `extractfacts_[filename_slug]_YYYYMMDD_HHMMSS.txt`
- **strategy**: `strategy_[outcome_slug]_YYYYMMDD_HHMMSS.txt`
- **draft**: `draft_[query_slug]_YYYYMMDD_HHMMSS.txt`
- **counselnotes**: `counselnotes_[filename_slug]_YYYYMMDD_HHMMSS.txt`
- **barbrief**: `barbrief_[hearing_type]_YYYYMMDD_HHMMSS.txt`

Each output file includes metadata headers with command parameters and timestamps.

### Output Organization
- Command outputs are automatically stored in the `outputs/` directory
- Detailed logs are saved in `logs/<command>_YYYYMMDD-HHMMSS.{json|md}`
- Progress indicators keep you informed during long-running operations (configurable heartbeat interval)
- Network errors are caught and displayed with user-friendly messages

### Model Configuration
Each command uses optimized LLM models and parameters:
- **Factual tasks** (lookup, extractfacts): `temperature=0` for accuracy
- **Creative tasks** (brainstorm, draft): `temperature=0.5-0.9` for innovation
- **Verification**: Always uses `temperature=0` for consistency

**Note**:
- Document chunking (`max_chars`) controls input processing for large files.
- tiktoken is required for accurate token counting and large document handling.
- All output is now ASCII/ANSI only (no emoji).
- See the [LitAssist User Guide](docs/user/LitAssist_User_Guide.md#model-configuration) for details.

## Disclaimer

This tool provides drafts and summaries only. All outputs must be reviewed by qualified legal counsel before filing or submission.

---

For detailed instructions, workflows, and examples, see the [LitAssist User Guide](docs/user/LitAssist_User_Guide.md).
