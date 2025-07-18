# Technical Context

## Technologies Used

- **Python** ≥ 3.11: Core implementation language (updated from 3.8 in July 2025)
- **Click**: CLI framework for command definitions  
- **OpenAI API**: LLM completions and embeddings via OpenRouter or direct  
- **Anthropic Claude**: Document summarization, fact extraction, analysis, and now verification (Claude 4 Opus as of July 2025)  
- **Grok**: Creative strategy generation  
- **Pinecone**: Managed vector store for retrieval-augmented generation (RAG)  
- **Google CSE (Jade.io)**: Citation verification and lookup integration  
- **PyPDF2**: PDF parsing and text extraction  
- **YAML**: Prompt templates and configuration (PyYAML)  
- **Requests**: HTTP interactions for citation verification  
- **ReportLab**: PDF report generation  
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

- **Testing**: `pytest` for unit and integration tests (see pytest.ini)  
- **Linting**: `ruff` for code style and static analysis  
- **CI/CD**: GitHub Actions workflow running tests on Python 3.11 and 3.12
- **Pre-commit**: Automated pytest runs with fast-fail on every commit
- **Prompt Templates**: YAML files under `litassist/prompts/` for centralized prompt management  
- **Logging**: Configurable via `general.log_format` in config.yaml (`json` or `markdown`)  
- **Performance**: `@timed` decorator records durations for key operations  
- **Zero-Emoji Policy**: Enforced across all code and documentation (July 2025)
- **Documentation**: LaTeX articles, architectural diagrams, and comprehensive dev docs  

## Dependencies & Constraints

- **LLM Models**: BYOK required for o3 and o1-pro models (OpenRouter integration)  
- **Token & Chunk Limits**: Configurable in `general.max_chars`, `general.rag_max_chars`, and `llm.use_token_limits`
  - **Verification Token Limits (July 2025)**: Increased to 8192-16384 tokens for full document verification
  - **Chunk-Based Processing (July 2025)**: Large documents split into 50k token chunks for digest/strategy commands
- **Citation Verification**: Jade.io primary with offline pattern fallback (`citation_validation.offline_validation`)  
- **Strict Structure**: `extractfacts` and `strategy` enforce fixed heading formats  

## Tool Usage Patterns

- **RAG**: Large documents (>50k chars) processed via Pinecone embeddings  
- **Direct Processing**: Text `.txt` files under token/chunk limits passed directly to LLM  
- **Chunk-Based Processing**: Digest and strategy commands split large documents into 50k token chunks for LLM processing (July 2025)
- **Token Counting**: All major commands use tiktoken for accurate token counting and user warnings for large inputs (July 2025)
- **Selective Regeneration**: Strategy commands only regenerate or discard items with citation issues  
- **Multi-Stage Refinement**: Prompts load from YAML templates and support iterative improvement loops
- **Zero-Emoji Policy**: All output and code must be ASCII/ANSI only, no emoji (enforced July 2025)
