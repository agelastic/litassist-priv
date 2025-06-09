# LitAssist

**LitAssist** is a command-line tool for automated litigation support workflows, tailored to Australian law. It leverages large language models (LLMs) and a managed vector store to provide an end-to-end pipeline:

```mermaid
graph TD
    A["Lookup - Research"] --> B["Digest - Analyse"]
    B --> C["ExtractFacts - Structure"]
    C --> D["Brainstorm - Generate Options"]
    D --> E["Strategy - Plan Approach"]
    E --> F["Draft - Create Documents"]
    
    G[Utilities] --> H["Test - API Connectivity"]
    G --> I["Audit Logging"]
    G --> J["Mock Mode"]
```

- **Lookup**: Rapid case-law research (Jade.io database via Google Custom Search + Google Gemini)  
- **Digest**: Mass-document processing (Chronological summaries or issue-spotting via Claude)  
- **ExtractFacts**: Automatic extraction of case facts into a structured file  
- **Brainstorm**: Creative legal strategy generation (Unorthodox strategies via Grok)  
- **Strategy**: Targeted legal options with probability assessments and draft documents (Enhanced reasoning via o1-pro)
- **Draft**: Citation-rich document creation (Superior technical writing via o3)  

For detailed usage guidance, see [LitAssist_User_Guide.md](/docs/user/LitAssist_User_Guide.md).

## 🆕 Recent Improvements (June 2025)

### June 2025: Lookup Command Overhaul
- **Simplified Search Engine**: Removed Google web search option due to anti-bot restrictions; now uses reliable Jade.io database exclusively
- **Comprehensive Mode**: Added `--comprehensive` flag for exhaustive analysis with up to 40 sources (vs 5 standard)
- **Enhanced Extraction**: Improved `--extract` options for citations, principles, and checklists with better parsing
- **Citation Integration**: Streamlined citation verification using Jade.io as primary source
- **Code Quality**: Fixed all ruff linting errors and removed unused dependencies

### Legal Reasoning & Transparency
- **Multi-Section Reasoning Traces**: Brainstorm command now saves separate reasoning files for orthodox, unorthodox, and "most likely to succeed" analysis
- **Comprehensive Legal Analysis**: See the logic behind every strategic recommendation with structured reasoning traces
- **Enhanced Strategy Integration**: Strategy command builds intelligently on brainstormed foundations

### Performance & Architecture  
- **Complete Timing Coverage**: All long-running operations now timed and logged for performance monitoring
- **Comprehensive Logging**: Every LLM call, HTTP request, and operation logged for full audit trails
- **Configuration Centralization**: Log format and other settings moved from CLI options to config.yaml for consistency

### Quality & User Experience
- **Clean CLI Output**: All commands show professional summaries instead of overwhelming text dumps
- **Citation Verification**: Enhanced real-time validation via Jade.io database search
- **File Organization**: Clear file locations with proper shell escaping for paths with spaces

## 🔧 Installation

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/your-org/litassist.git
cd litassist

# 2. Install globally with pipx (recommended)
brew install pipx
pipx install -e .
pipx ensurepath
source ~/.zshrc

# 3. Setup configuration
cp config.yaml.template config.yaml
# Edit config.yaml with your API keys

# 4. Copy config to global location
mkdir -p ~/.config/litassist
cp config.yaml ~/.config/litassist/

# 5. Use from anywhere
cd ~/any-directory/
litassist digest document.pdf
```

**📖 For detailed installation options, troubleshooting, and advanced setup, see [INSTALLATION.md](INSTALLATION.md)**

## ⚙️ Configuration

Required API keys in `config.yaml`:

```yaml
openrouter:
  api_key:    "YOUR_OPENROUTER_KEY"
  api_base:   "https://openrouter.ai/api/v1"   # optional

openai:
  api_key:          "YOUR_OPENAI_KEY"
  embedding_model:  "text-embedding-3-small"

google_cse:
  api_key:  "YOUR_GOOGLE_API_KEY"
  cse_id:   "YOUR_JADE_CSE_ID"    # Google CSE for Jade.io

pinecone:
  api_key:     "YOUR_PINECONE_KEY"
  environment: "YOUR_PINECONE_ENV"   # e.g. "us-east-1-aws"
  index_name:  "legal-rag"

llm:
  use_token_limits: false    # Enable conservative token limits for AI responses (default: false = use model defaults)

general:
  heartbeat_interval: 10  # Progress indicator interval in seconds (default: 10)
  max_chars: 20000        # Document chunking: characters per chunk for digest/extractfacts (default: 20000 ≈ 4000 words)
  rag_max_chars: 8000     # Document chunking: characters per chunk for draft command embeddings (default: 8000 ≈ 1600 words)
```

### 🤖 Model Configuration & BYOK Requirements

LitAssist uses cutting-edge AI models optimized for legal work:

| Command | Model | BYOK Required | Purpose |
|---------|-------|--------------|---------|
| **strategy** | OpenAI o1-pro | No | Enhanced multi-step legal reasoning |
| **draft** | OpenAI o3 | **Yes** | Superior technical legal writing |
| **brainstorm** | Claude 4 Sonnet / Grok 3 | No | Conservative vs creative strategies |
| **digest** | Claude 4 Sonnet | No | Document analysis and summarization |
| **extractfacts** | Claude 4 Sonnet | No | Structured fact extraction |

#### Setting up BYOK for o3 (Draft Command)

The `draft` command uses OpenAI's o3 model, which requires **BYOK (Bring Your Own Key)**:

1. Go to [OpenRouter Settings](https://openrouter.ai/settings/integrations)
2. Add your OpenAI API key under "OpenAI Integration"
3. Save the integration
4. o3 will now be available through your OpenRouter API key

Without BYOK setup, the draft command will fail with an authentication error.

## 🚀 Command Reference

Basic usage:
```bash
./litassist.py [GLOBAL OPTIONS] <command> [ARGS] [OPTIONS]
```

Global options:
- `--log-format [json|markdown]`: Choose audit-log format (default: json)
- `--verbose`: Enable debug-level logging

### Core Pipeline Commands

1. **lookup** - Rapid case-law search with automatic citation
   ```bash
   ./litassist.py lookup "What defences exist to adverse costs orders?"
   ./litassist.py lookup "Question?" --mode broad --engine jade
   ```

2. **digest** - Process large documents for summaries or issues
   ```bash
   ./litassist.py digest bundle.pdf --mode [summary|issues]
   ```

3. **extractfacts** - Extract structured case facts from documents
   ```bash
   ./litassist.py extractfacts document.pdf
   # Creates: extractfacts_document_YYYYMMDD_HHMMSS.txt
   # Note: case_facts.txt must be created/edited manually
   ```

4. **brainstorm** - Generate comprehensive legal strategies with reasoning traces
   ```bash
   ./litassist.py brainstorm case_facts.txt --side [plaintiff|defendant|accused] --area [criminal|civil|family|commercial|administrative]
   # Creates: brainstorm_[area]_[side]_YYYYMMDD_HHMMSS.txt (main strategies)
   #          brainstorm_[area]_[side]_YYYYMMDD_HHMMSS_orthodox_reasoning.txt
   #          brainstorm_[area]_[side]_YYYYMMDD_HHMMSS_unorthodox_reasoning.txt  
   #          brainstorm_[area]_[side]_YYYYMMDD_HHMMSS_analysis_reasoning.txt
   # Note: strategies.txt must be created/edited manually
   ```

5. **strategy** - Generate targeted legal options and draft documents
   ```bash
   ./litassist.py strategy case_facts.txt --outcome "Obtain interim injunction against defendant"
   # Or incorporate brainstormed strategies
   ./litassist.py strategy case_facts.txt --outcome "..." --strategies strategies.txt
   ```

6. **draft** - Create citation-rich legal drafts with intelligent document recognition
   ```bash
   # Single document
   ./litassist.py draft case_facts.txt "skeleton argument on jurisdictional error"
   # Multiple documents (automatically recognizes case_facts.txt and strategies.txt)
   ./litassist.py draft case_facts.txt strategies.txt "argument based on strategy #3"
   # Mix text files and PDFs
   ./litassist.py draft case_facts.txt bundle.pdf "comprehensive submission"
   ```

### Utility Commands

- **test** - Verify API connectivity
  ```bash
  ./litassist.py test
  ```

## 📁 Example Files

The `examples/` directory contains sample files for testing all commands, based on the fictional *Smith v Jones* family law case.

## 📂 Output Files & Logging

### Command Output Files
All commands now save their output to timestamped text files without overwriting existing files:

- **lookup**: `lookup_[query_slug]_YYYYMMDD_HHMMSS.txt`
- **digest**: `digest_[mode]_[filename_slug]_YYYYMMDD_HHMMSS.txt`
- **brainstorm**: `brainstorm_[area]_[side]_YYYYMMDD_HHMMSS.txt`
- **extractfacts**: `extractfacts_[filename_slug]_YYYYMMDD_HHMMSS.txt`
- **strategy**: `strategy_[outcome_slug]_YYYYMMDD_HHMMSS.txt`
- **draft**: `draft_[query_slug]_YYYYMMDD_HHMMSS.txt`

Each output file includes metadata headers with command parameters and timestamps.

### Output Organization
- Command outputs stored in `outputs/` directory
- Detailed logs stored in `logs/<command>_YYYYMMDD-HHMMSS.{json|md}`
- Progress indicators for long-running operations (configurable heartbeat interval)
- Network errors are caught with user-friendly messages

### Model Configuration
Each command uses optimized LLM models and parameters:
- **Factual tasks** (lookup, extractfacts): `temperature=0` for accuracy
- **Creative tasks** (brainstorm, draft): `temperature=0.5-0.9` for innovation
- **Verification**: Always uses `temperature=0` for consistency

**Note**: Document chunking (`max_chars`) and AI output limits (`use_token_limits`) are separate systems. See [LitAssist_User_Guide.md](/docs/user/LitAssist_User_Guide.md#llm-models-and-parameter-configuration) for details.

## ⚖️ Disclaimer

This tool provides drafts and summaries only. All outputs should be reviewed by qualified counsel before filing or submission.

---

For detailed instructions, workflows, and examples, see [LitAssist_User_Guide.md](/docs/user/LitAssist_User_Guide.md).
