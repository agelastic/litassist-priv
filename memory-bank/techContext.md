# Technical Context

## Technologies Used

- **Python** ≥ 3.11: Core implementation language (updated from 3.8 in July 2025)
- **Click**: CLI framework for command definitions
- **OpenAI API**: LLM completions and embeddings via OpenRouter
  - **GPT-5 Pro**: Critical verification (<1% hallucination rate, October 2025)
  - **GPT-5**: Fast verification (1.4% hallucination rate, October 2025)
  - **o3-pro**: Technical drafting and comprehensive analysis
- **Anthropic Claude**: Primary legal reasoning and analysis
  - **Claude Sonnet 4.5**: State-of-the-art for complex litigation tasks (October 2025)
  - **Previous**: Claude 4 Opus verification (July 2025), now replaced by GPT-5 family
- **Grok 4**: Creative strategy generation (October 2025, upgraded from Grok 3)
- **Pinecone**: Managed vector store for retrieval-augmented generation (RAG)
- **Google CSE (Jade.io)**: Citation verification and lookup integration
- **Google Gemini 2.5 Pro**: Case law research with 1M context window
- **PyPDF2 & pdfplumber**: PDF parsing and text extraction
- **YAML**: Prompt templates and configuration (PyYAML)
- **Requests**: HTTP interactions for citation verification
- **ReportLab**: PDF report generation
- **Selenium**: Browser automation for JavaScript-rendered content (e.g., Jade.io)
- **tiktoken**: Token counting for GPT models (cl100k_base encoding, added July 2025)
- **pytest**: Unit testing framework with tmp_path fixtures
- **GitHub Actions**: CI/CD pipeline for automated testing
- **pre-commit**: Git hooks for code quality checks

## Development Setup

- **Package Management**: `pip install -r requirements.txt` / `pipx install -e .`  
- **Configuration**: `cp config.yaml.template config.yaml` → populate API keys  
- **Global Config**: `~/.config/litassist/config.yaml` for CLI use anywhere  
- **Environment**: macOS (zsh), Linux, Windows (WSL) supported  

## Tooling & Conventions

- **Testing**: A two-tiered testing strategy is in place, as documented in `test-scripts/TESTS_STATUS.md`. This includes a suite of fully-mocked, offline `pytest` unit tests (`tests/unit/`) and a collection of manual integration scripts (`test-scripts/`) that perform real API calls for validation.
- **Linting**: `ruff` for code style and static analysis
- **CI/CD**: GitHub Actions workflow running tests on Python 3.11 and 3.12
- **Pre-commit**: Automated pytest runs with fast-fail on every commit
- **Prompt Templates**: YAML files under `litassist/prompts/` for centralized prompt management  
- **Logging**: Configurable via `general.log_format` in config.yaml (`json` or `markdown`)  
- **Performance**: `@timed` decorator records durations for key operations  
- **Zero-Emoji Policy**: Enforced across all code and documentation (July 2025)
- **Documentation**: LaTeX articles, architectural diagrams, and comprehensive dev docs  

## Dependencies & Constraints

- **LLM Models**:
  - **BYOK Required (October 2025)**: o3-pro, GPT-5, GPT-5 Pro (Tier 4+ OpenAI key via OpenRouter)
  - **No BYOK**: Claude Sonnet 4.5, Gemini 2.5 Pro (available directly through OpenRouter)
- **Token & Chunk Limits**: Configurable in `general.max_chars`, `general.rag_max_chars`, and `llm.use_token_limits`
  - **Verification Token Limits (July 2025)**: Increased to 8192-16384 tokens for full document verification
  - **Chunk-Based Processing (July 2025)**: Large documents split into 50k token chunks for digest/strategy commands
- **Citation Verification**: Jade.io primary with offline pattern fallback (`citation_validation.offline_validation`)
- **Strict Structure**: `extractfacts` and `strategy` enforce fixed heading formats
- **Three-Tier Strategy (October 2025)**: Model selection optimizes accuracy vs cost based on task criticality  

## Tool Usage Patterns

- **RAG**: Large documents (>50k chars) processed via Pinecone embeddings  
- **Direct Processing**: Text `.txt` files under token/chunk limits passed directly to LLM  
- **Chunk-Based Processing**: Digest and strategy commands split large documents into 50k token chunks for LLM processing (July 2025)
- **Token Counting**: All major commands use tiktoken for accurate token counting and user warnings for large inputs (July 2025)
- **Selective Regeneration**: Strategy commands only regenerate or discard items with citation issues  
- **Multi-Stage Refinement**: Prompts load from YAML templates and support iterative improvement loops
- **Zero-Emoji Policy**: All output and code must be ASCII/ANSI only, no emoji (enforced July 2025)
