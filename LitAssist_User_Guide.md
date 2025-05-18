# LitAssist User Guide

## Introduction

LitAssist is a command-line tool designed for Australian legal professionals to automate litigation support workflows. It leverages large language models and vector search technology to enhance legal research, document analysis, and drafting processes.

## Installation

1. **Prerequisites**
   - Python 3.8 or higher
   - Git (for repository cloning)

2. **Setup**
   ```bash
   # Clone repository
   git clone https://github.com/your-org/litassist.git
   cd litassist
   
   # Create virtual environment
   python3 -m venv .venv
   source .venv/bin/activate
   
   # Install dependencies
   pip install click openai pinecone-client PyPDF2 google-api-python-client pyyaml
   
   # Make executable
   chmod +x litassist.py
   ```

3. **Configuration**
   Create a `config.yaml` file in the root directory with your API keys:
   ```yaml
   openrouter:
     api_key:    "YOUR_OPENROUTER_KEY"
     api_base:   "https://openrouter.ai/api/v1"   # optional
   
   openai:
     api_key:          "YOUR_OPENAI_KEY"
     embedding_model:  "text-embedding-ada-002"
   
   google_cse:
     api_key:  "YOUR_GOOGLE_API_KEY"
     cse_id:   "YOUR_GOOGLE_CSE_ID"
   
   pinecone:
     api_key:     "YOUR_PINECONE_KEY"
     environment: "YOUR_PINECONE_ENV"   # e.g. "us-east-1-aws"
     index_name:  "legal-rag"
   ```

## Core Commands

LitAssist operates through five primary commands, each addressing specific legal workflow needs:

### 1. lookup
Performs case law research using Google Custom Search and Google Gemini.

```bash
./litassist.py lookup "What defences exist to adverse costs orders?"
./litassist.py lookup "What defences exist to adverse costs orders?" --mode broad
```

**Options:**
- `--mode irac|broad` - Choose response format (default: irac)
- `--verify` - Run self-critique for accuracy

### 2. digest
Processes and summarizes large legal documents using Claude 3 Sonnet.

```bash
./litassist.py digest bundle.pdf --mode summary
./litassist.py digest hearing.txt --mode issues
```

**Options:**
- `--mode summary|issues` - Choose between chronological summary or issue spotting (default: summary)
- `--verify` - Run self-critique verification

### 3. ideate
Generates creative legal strategies using Grok's AI capabilities.

```bash
./litassist.py ideate case_facts.txt
```

**Options:**
- `--verify` - Run self-critique verification

### 4. extractfacts
Extracts structured case facts from documents using Claude 3 Sonnet.

```bash
./litassist.py extractfacts police_ebrief.pdf
```

**Options:**
- `--verify` - Run self-critique verification

### 5. draft
Creates citation-rich legal drafts using RAG methodology with GPT-4o.

```bash
./litassist.py draft bundle.pdf "skeleton argument on jurisdictional error"
```

**Options:**
- `--verify` - Run self-critique verification
- `--diversity FLOAT` - Control diversity in retrieved passages (0.0-1.0)

## Global Options

Options available for all commands:

```bash
./litassist.py [GLOBAL OPTIONS] <command> [ARGS] [OPTIONS]
```

- `--log-format [json|markdown]` - Set audit log format (default: markdown)
- `--verbose` - Enable detailed debug logging

## Audit Logging

All command executions are logged for audit purposes:
- Logs stored in `logs/` directory
- Format: `logs/<command>_YYYYMMDD-HHMMSS.{json|md}`
- Contents include metadata, inputs, prompts, responses, and token usage

## Troubleshooting

- Check configuration file for correct API keys
- Examine logs for error messages and API responses
- Ensure proper document formats for processing (PDF, TXT)
- Verify internet connectivity for all cloud API calls

## Legal Disclaimer

All outputs from LitAssist are draft documents only and must be reviewed by qualified legal counsel before use in formal proceedings.
