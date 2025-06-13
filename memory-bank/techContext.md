# Technical Context

## Technologies Used

- **Python** ≥ 3.8: Core implementation language  
- **Click**: CLI framework for command definitions  
- **OpenAI API**: LLM completions and embeddings via OpenRouter or direct  
- **Anthropic Claude**: Document summarization, fact extraction, analysis  
- **Grok**: Creative strategy generation  
- **Pinecone**: Managed vector store for retrieval-augmented generation (RAG)  
- **Google CSE (Jade.io)**: Citation verification and lookup integration  
- **PyPDF2**: PDF parsing and text extraction  
- **YAML**: Prompt templates and configuration (PyYAML)  
- **Requests**: HTTP interactions for citation verification  
- **ReportLab**: PDF report generation  

## Development Setup

- **Package Management**: `pip install -r requirements.txt` / `pipx install -e .`  
- **Configuration**: `cp config.yaml.template config.yaml` → populate API keys  
- **Global Config**: `~/.config/litassist/config.yaml` for CLI use anywhere  
- **Environment**: macOS (zsh), Linux, Windows (WSL) supported  

## Tooling & Conventions

- **Testing**: `pytest` for unit and integration tests (see pytest.ini)  
- **Linting**: `ruff` for code style and static analysis  
- **Prompt Templates**: YAML files under `litassist/prompts/` for centralized prompt management  
- **Logging**: Configurable via `general.log_format` in config.yaml (`json` or `markdown`)  
- **Performance**: `@timed` decorator records durations for key operations  

## Dependencies & Constraints

- **LLM Models**: BYOK required for o3 and o1-pro models (OpenRouter integration)  
- **Token & Chunk Limits**: Configurable in `general.max_chars`, `general.rag_max_chars`, and `llm.use_token_limits`  
- **Citation Verification**: Jade.io primary with offline pattern fallback (`citation_validation.offline_validation`)  
- **Strict Structure**: `extractfacts` and `strategy` enforce fixed heading formats  

## Tool Usage Patterns

- **RAG**: Large documents (>50k chars) processed via Pinecone embeddings  
- **Direct Processing**: Text `.txt` files under token/chunk limits passed directly to LLM  
- **Selective Regeneration**: Strategy commands only regenerate or discard items with citation issues  
- **Multi-Stage Refinement**: Prompts load from YAML templates and support iterative improvement loops
