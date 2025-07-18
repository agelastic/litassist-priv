 # LitAssist Application Architecture

 ## Overview
 LitAssist is a modular command-line application designed to streamline Australian legal workflows through AI-powered assistance. It leverages large language models (LLMs) with retrieval-augmented generation (RAG) to provide citation-rich drafting, case law lookup, document digestion, strategic brainstorming, and more.

 ## High-Level Structure
 The application is organized in a layered architecture:
 
 ```
 User
   |
   v
 CLI (litassist.py, litassist/cli.py)
   |
   v
 Command Modules (litassist/commands/*.py)
   |
   v
 Core Components
   - config.py
   - prompts.py + prompts/ (YAML templates)
   - llm.py (LLM wrapper)
   - utils.py (utilities)
   - helpers/ (pinecone_config, retriever)
   - citation_verify.py, citation_patterns.py
   |
   v
 External Services
   - OpenAI / OpenRouter
   - Pinecone vector DB
   - Google Custom Search (CSE)
   - Requests
 ```

 ## Core Components

 ### 1. CLI Entry Point
 - `litassist.py` and `litassist/cli.py` define the `main` function and `cli` group using Click.
 - Global options (`--log-format`, `--verbose`) and environment configuration are handled at startup.
 - Commands are registered dynamically via `register_commands`.

 ### 2. Configuration Management
 - `litassist/config.py` loads `config.yaml` (or `LITASSIST_CONFIG`), validates required keys, and injects API credentials.
 - Provides a global `CONFIG` instance with attributes for all external services.

 ### 3. Prompt Management
 - `litassist/prompts.py` and the `prompts/` directory hold YAML templates for system and user prompts.
 - `PromptManager` loads and merges templates, supports dot-notation access, formatting parameters, and composing multi-part prompts.

 ### 4. LLM Client Layer
 - `litassist/llm.py` wraps different LLM providers (OpenAI, Anthropic, Google, etc.) into a unified interface.
 - Handles dynamic parameter filtering per model family, streaming and retry logic (`tenacity`), message formatting, and citation verification via `citation_verify.py`.

 ### 5. Command Modules
 - Located in `litassist/commands/*.py`, each file implements a specific workflow:
   - `lookup`: Case-law lookup via Google CSE or Jade.
   - `digest`: Document digestion and summarization.
   - `brainstorm`: Strategy generation.
   - `extractfacts`: Extract facts under headings.
   - `draft`: RAG-based citation-rich drafting with Pinecone.
   - `verify`: Self-critique and citation verification.
   - `counselnotes`, `caseplan`, `barbrief`, `strategy`: Domain-specific workflows.
 - Each command uses Click decorators, accepts arguments/options, orchestrates core modules, and reports user-friendly messages.

 ### 6. Utility Functions
 - `litassist/utils.py` provides:
   - Document I/O (`read_document`, PDF/text handling).
   - Text chunking for embedding or direct prompts.
   - Embedding creation (`create_embeddings`).
   - Logging utilities (`save_log`, `heartbeat`, `timed` decorators).
   - Output helpers (`info_message`, `warning_message`, `save_command_output`).
   - Factual hallucination detection and self-verification.

 ### 7. Helper Modules
 - `litassist/helpers/pinecone_config.py`: Pinecone index initialization parameters.
 - `litassist/helpers/retriever.py`: Vector retrieval with Maximal Marginal Relevance (MMR).

 ### 8. Citation Verification
 - `litassist/citation_verify.py` and `citation_patterns.py` implement offline/online citation verification, raising errors or stripping unverified citations.

 ## Data Flow
 1. **User Input**: Terminal command → Click parses args/options.
 2. **Configuration**: Load and validate API credentials.
 3. **Command Execution**: Selected command builds context:
    - Read documents, chunk if needed.
    - Retrieve relevant context from Pinecone (RAG).
    - Construct prompts via `PromptManager`.
 4. **LLM Invocation**: `LLMClient` sends chat completion requests, handles streaming and retries.
 5. **Post-Processing**: Optionally verify citations, detect hallucinations.
 6. **Output & Logging**: Results printed to console, audit logs saved in JSON or Markdown.

 ## Third-Party Integrations
 - **OpenAI / OpenRouter**: Chat completions and embeddings.
 - **Anthropic, Google Gemini, Grok**: Alternative LLM providers via unified interface.
 - **Pinecone**: Vector store for RAG workflows.
 - **Google Custom Search**: Case-law lookup.
 - **Requests**: HTTP requests for services like OpenRouter.

 ## Testing
 - Unit tests in `tests/unit/` using pytest.
 - Integration scripts in `test-scripts/`.
 - CI requirements in `requirements-ci.txt`.

 ## Documentation & Examples
 - User guides under `docs/user/`.
 - Development notes under `docs/development/`.
 - Prompt analyses under `docs/prompts/`.
 - Example inputs/outputs in `examples/`.

 ## Extensibility
 - To add commands: create a new module in `commands/`, define a Click command, register in `commands/__init__.py`.
 - Prompts: add YAML templates in `prompts/` and reference via `PromptManager`.
 - Configuration: extend `config.yaml.template` and use `CONFIG.<attribute>`.

 ## Deployment
 - Packaged via `setup.py` with `console_scripts` entry point `litassist`.
 - Installed packages include code and prompt templates.
 - Global install picks up `config.yaml` from standard locations (`~/.config/litassist/`).
