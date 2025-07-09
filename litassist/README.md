# LitAssist Package Architecture

This directory contains the modular implementation of LitAssist, providing a structured approach to handling Australian legal workflows through various specialized commands.

## Package Structure

```
litassist/
├── __init__.py             # Package initialization
├── config.py               # Configuration management (API keys, service endpoints)
├── utils.py                # Core utilities (document reading, chunking, logging)
├── llm.py                  # LLM client wrapper with standard interface
├── retriever.py            # Vector search with MMR re-ranking
├── pinecone_config.py      # Pinecone index configuration
├── cli.py                  # CLI entry point and command registration
└── commands/               # Individual command implementations
    ├── __init__.py         # Command registration mechanism
    ├── lookup.py           # Case-law lookup via Google CSE/Jade
    ├── digest.py           # Document digestion with Claude
    ├── brainstorm.py       # Legal strategy generation with Grok
    ├── extractfacts.py     # Case facts extraction under 10 headings
    ├── draft.py            # RAG-based legal drafting with o3
    ├── strategy.py         # Strategic options and document generation
    ├── verify.py           # Citation verification with Claude
    ├── counselnotes.py     # Strategic advocate analysis with Claude
    ├── caseplan.py         # Phased workflow planning with command coverage, focus, and rationale (Sonnet/Opus)
    └── barbrief.py         # Comprehensive barrister's briefs with o3-pro
```

## Core Components

### LLMClient (llm.py)

Centralized client that provides a standardized interface to various LLM providers:

```python
# Initialize with model ID and parameters
client = LLMClient("anthropic/claude-3-sonnet", temperature=0.2)

# Standard message format for all models
content, usage = client.complete([
    {"role": "system", "content": "Australian law only."},
    {"role": "user", "content": prompt}
])

# Optional self-verification
corrections = client.verify(content)
```

### Retriever (retriever.py)

Handles vector search with Maximal Marginal Relevance (MMR) for diversity:

```python
# Initialize with Pinecone index
retriever = Retriever(pc_index, use_mmr=True, diversity_level=0.3)

# Retrieve relevant passages with optional diversity
passages = retriever.retrieve(query_embedding, top_k=5)
```

### Utilities (utils.py)

Provides document handling and monitoring capabilities:

```python
# Document processing
text = read_document(file_path)  # Handles PDF and text
chunks = chunk_text(text)        # Intelligent chunking

# Monitoring and logging
@heartbeat(30)  # Show progress every 30 seconds
def long_running_function():
    pass

@timed()  # Measure and log execution time
def performance_critical_function():
    pass

# Audit logging
save_log("command_name", data_dict)  # JSON or Markdown
```

## Adding New Commands

To add a new command:

1. Create a new file in the `commands/` directory
2. Define a command function using Click decorators:
   ```python
   @click.command()
   @click.argument("input_argument", type=click.Path(exists=True))
   @click.option("--option", help="Help text")
   def new_command(input_argument, option):
       """Command description for help text."""
       # Implementation
   ```
3. Import and register in `commands/__init__.py`

## Developer Notes

- **Error Handling**: Use `click.ClickException` for user-friendly error messages
- **Progress Feedback**: Use `click.progressbar` for multi-step processes
- **Resource Cleanup**: Ensure proper cleanup in finally blocks
- **Configuration**: Access via `config.get_config()` utility
- **Token Usage**: Track and log all API usage for cost monitoring

## Testing

Test fixtures and utilities are available in the `tests/` directory. Key test files:

- `conftest.py`: Shared fixtures and mocks
- `unit/`: Unit tests for individual components
- `integration/`: End-to-end workflow tests

Run tests with pytest:
```bash
python -m pytest
```

For detailed developer documentation, please refer to the main project README.md in the root directory.
