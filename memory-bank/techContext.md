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
  - **Test Count (November 2025)**: 390 tests passing
- **Linting**: `ruff` for code style and static analysis
- **CI/CD**: GitHub Actions workflow running tests on Python 3.11 and 3.12
- **Pre-commit**: Automated pytest runs with fast-fail on every commit
- **Prompt Templates**: YAML files under `litassist/prompts/` for centralized prompt management  
- **Logging**: Configurable via `general.log_format` in config.yaml (`json` or `markdown`)
  - **Default Format (November 2025)**: Switched from JSON to markdown for better readability
  - **JSON Auto-Formatting**: LLM responses in JSON automatically formatted to rich markdown
  - **Output Location (November 2025)**: Saved to current working directory instead of package directory
- **Performance**: `@timed` decorator records durations for key operations  
- **Zero-Emoji Policy**: Enforced across all code and documentation (July 2025)
- **Documentation**: LaTeX articles, architectural diagrams, and comprehensive dev docs
- **Security (November 2025)**: Anti-injection prompt protection added for all LLM calls

## Dependencies & Constraints

- **LLM Models**:
  - **BYOK Required (October 2025)**: o3-pro, GPT-5, GPT-5 Pro (Tier 4+ OpenAI key via OpenRouter)
  - **No BYOK**: Claude Sonnet 4.5, Gemini 2.5 Pro (available directly through OpenRouter)
- **Reasoning Control (November 2025)**:
  - **thinking_effort** (Claude): Controls reasoning budget (1K-32K tokens), NOT output length
  - **reasoning_effort** (o-series): Controls reasoning depth (low/medium/high)
  - **No automatic output limits**: Models use API defaults for maximum quality
  - **Explicit limits**: Commands can set max_tokens if needed (rarely used)
  - **Token Limit System REMOVED**: use_token_limits flag eliminated (November 2025)
- **Input Processing**: Configurable in `general.max_chars` and `general.rag_max_chars`
  - **Chunk-Based Processing**: Large documents split into 50K character chunks for digest/strategy commands
  - **Raised Limits (November 2025)**: brainstorm/caseplan input limits increased from 50K to 600K characters
- **Citation Verification**: Jade.io primary with offline pattern fallback (`citation_validation.offline_validation`)
  - **Verification Flags (November 2025)**: --heavy (premium gpt-5-pro), --noverify (skip verification)
  - **Default Changed (November 2025)**: verify-soundness now uses claude-opus-4.1 instead of gpt-5-pro
- **Strict Structure**: `extractfacts` and `strategy` enforce fixed heading formats
- **Three-Tier Strategy (October 2025)**: Model selection optimizes accuracy vs cost based on task criticality

## Tool Usage Patterns

- **RAG**: Large documents (>50k chars) processed via Pinecone embeddings
- **Direct Processing**: Text `.txt` files under character limits passed directly to LLM
- **Chunk-Based Processing**: Digest and strategy commands split large documents into 50K character chunks for LLM processing
- **Token Counting**: All major commands use tiktoken for accurate token counting and user warnings for large inputs
- **Selective Regeneration**: Strategy commands only regenerate or discard items with citation issues  
- **Multi-Stage Refinement**: Prompts load from YAML templates and support iterative improvement loops
- **Zero-Emoji Policy**: All output and code must be ASCII/ANSI only, no emoji (enforced July 2025)
