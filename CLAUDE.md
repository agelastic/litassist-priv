This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LitAssist is a command-line tool for automated litigation support workflows, tailored to Australian law. It leverages large language models (LLMs) and managed vector stores to provide:

- **Rapid case-law lookup** (Google Custom Search + Google Gemini)
- **Mass-document digestion** (Chronological summaries or issue-spotting via Claude)
- **Novel strategy ideation** (Creative legal arguments via Grok)
- **Automatic extraction of case facts** into a structured file
- **Citation-rich drafting** (Retrieval-Augmented Generation with GPT-4o)

## Commands

### Development Environment Setup

Set up the development environment:
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Make script executable
chmod +x litassist.py
```

### Running LitAssist

Run LitAssist commands:
```bash
# Basic usage
./litassist.py [GLOBAL OPTIONS] <command> [ARGS] [OPTIONS]

# Global options
# --log-format [json|markdown] - Choose audit-log format (default: markdown)
# --verbose - Enable debug-level logging

# Example: Rapid case-law lookup
./litassist.py lookup "What defences exist to adverse costs orders?"

# Example: Mass-document digestion
./litassist.py digest bundle.pdf --mode summary

# Example: Novel strategy ideation
./litassist.py ideate case_facts.txt

# Example: Auto-extract facts
./litassist.py extractfacts police_ebrief.pdf

# Example: Citation-rich drafting
./litassist.py draft bundle.pdf "skeleton argument on jurisdictional error"
```

### Running Tests

Run integration tests:
```bash
# Run all tests
./run_tests.sh --all

# Run specific tests
./run_tests.sh --openai
./run_tests.sh --pinecone
./run_tests.sh --openrouter

# Alternatively, use the Python script directly
python test_integrations.py --all
python test_integrations.py --openai --pinecone
```

## Architecture

### Core Components

1. **LLMClient** - Wrapper for LLM API calls with standardized interface for completions and verification
   ```python
   client = LLMClient("anthropic/claude-3-sonnet", temperature=0.2, top_p=0.8)
   content, usage = client.complete(messages)
   corrections = client.verify(content)  # Optional verification
   ```

2. **Retriever** - Handles Pinecone vector search with Maximal Marginal Relevance (MMR) re-ranking
   ```python
   retriever = Retriever(pc_index, use_mmr=True, diversity_level=0.3)
   passages = retriever.retrieve(query_embedding, top_k=5)
   ```

3. **Main Utilities**:
   - `read_document()` - Reads PDF and text files
   - `chunk_text()` - Splits text into manageable chunks
   - `create_embeddings()` - Creates embeddings for text inputs
   - `heartbeat()` decorator - Provides progress feedback for long-running operations
   - `timed()` decorator - Measures and logs execution time of functions
   - `save_log()` - Saves audit logs in JSON or Markdown format

### External Services

LitAssist integrates with three key external services:
1. **OpenAI API** - Provides embedding and completion capabilities
2. **Pinecone Vector Database** - Stores and retrieves embeddings with similarity search
3. **OpenRouter** - Acts as a gateway to multiple language models (Claude, Grok, Gemini, etc.)

### Command Flow

Each command follows a similar workflow:
1. Parse arguments and validate inputs
2. Configure service clients and connections
3. Process inputs (chunks, embeddings, etc.)
4. Call appropriate LLM services via LLMClient
5. Optionally perform self-verification if `--verify` flag is used
6. Save detailed audit logs
7. Display results to the user

### Testing Approach

Tests are designed to be:
1. **Lightweight** - Minimizing resource usage, API calls, and costs
2. **Thorough** - Covering essential functionality
3. **Non-destructive** - Cleaning up after themselves
4. **Informative** - Providing clear output about success/failure and performance
5. **Modular** - Supporting running specific test subsets when needed

## Important Files

- `litassist.py` - Main CLI application with all commands and business logic
- `config.yaml` - Configuration for API keys and services
- `run_tests.sh` - Helper script for running integration tests
- `test_integrations.py` - Integration tests for external services
- `test_README.md` - Documentation for the test suite
- `integration_testing_approach.md` - Detailed explanation of the testing approach
- `case_facts.txt` - Example or generated case facts for the ideate command