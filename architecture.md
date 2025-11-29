# LitAssist Architecture

## Overview
LitAssist is a Python-based CLI tool designed for AI-powered litigation support in Australian law. It leverages LLMs (OpenAI, Anthropic, Google) and vector databases (Pinecone) to assist with legal research, document analysis, and drafting.

## Project Structure
The project follows a standard Python package structure:
- `litassist/`: Main package directory containing source code.
- `setup.py`: Package installation and configuration.
- `requirements.txt`: Python dependencies.

## Core Components

### 1. CLI Entry Point
- Defined in `litassist/cli.py` using `click`.
- Handles global configuration (`config.yaml`), logging, and API credential validation.
- Dispatches commands to submodules in `litassist/commands/`.

### 2. Command Modules
Commands are organized as submodules in `litassist/commands/`. Each command typically has:
- `__init__.py`: Registers the command with the CLI.
- `core.py`: Contains the main logic for the command.
- Helper modules (e.g., `extractfacts` has `single_extractor.py`, `multi_extractor.py`).

Key commands include:
- `extractfacts`: Extracts facts from documents.
- `strategy`: Generates case strategy.
- `draft`: Drafts legal documents.
- `verify`: Verifies legal claims.
- `lookup`: Performs legal research.

### 3. LLM Integration
- **Factory Pattern**: `litassist/llm/factory.py` provides a `LLMClientFactory` to create configured LLM clients.
- **Configuration**: Model configurations are stored in `litassist/llm/model_configs.yaml`.
- **Client**: `litassist/llm/client.py` handles the actual API interactions via OpenRouter or direct providers.
- **Flexibility**: Supports environment variable overrides for model selection per command.

### 4. Citation Handling & Verification
- **Citation Context**: `litassist/citation_context.py` implements a robust strategy to fetch full text for citations:
    - **Cache**: Checks local cache first.
    - **Hardcoded**: Uses known URLs for specific legislation (e.g., FOI Act).
    - **CSE**: Uses Google Custom Search Engine with specific strategies for legislation (PDF preference) and case law (AustLII preference).
    - **Validation**: Validates fetched content against the citation using metadata headers, parallel citations, and case names.
- **Chain of Verification (CoVe)**: `litassist/verification_chain.py` implements a pipeline:
    1.  **Question Generation**: LLM generates questions to verify content.
    2.  **Citation Extraction**: Identifies citations in questions.
    3.  **Context Retrieval**: Fetches full text using `citation_context.py`.
    4.  **Answering**: LLM answers questions using the authoritative text.
    5.  **Inconsistency Detection**: LLM compares answers to original content.
    6.  **Regeneration**: LLM corrects the content if needed.

## External Integrations
- **OpenAI / OpenRouter**: Primary LLM providers.
- **Pinecone**: Vector database for semantic search (likely used in `lookup` or memory components).
- **Google Custom Search Engine (CSE)**: Used for retrieving legal documents from the web.
- **Jina Reader**: Used for scraping and parsing web content into markdown.

## Data Flow
1.  **User Input**: User runs a CLI command (e.g., `litassist extractfacts my_case.pdf`).
2.  **Processing**: The command module processes the input (e.g., reads PDF).
3.  **LLM Interaction**: The command requests an LLM client from the factory and sends prompts (from `litassist/prompts/`).
4.  **Verification (Optional)**: If verification is enabled, the CoVe pipeline is triggered to validate generated content against authoritative sources.
5.  **Output**: The result is printed to the console or saved to a file.
