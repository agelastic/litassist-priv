# LitAssist Package Architecture

Last updated: 03/06/2026

This directory contains the modular implementation of LitAssist, providing a structured approach to handling Australian legal workflows through various specialized commands.

## Package Structure

```
litassist/
├── __init__.py             # Package initialization
├── cli.py                  # CLI entry point and command registration
├── config.py               # Configuration management (get_config)
├── prompts.py              # PROMPTS template manager (loads prompts/*.yaml)
├── timing.py               # @timed execution-timing decorator
├── citation_context.py     # Citation context retrieval
├── citation_patterns.py    # Offline citation pattern validation
├── verification_chain.py   # Standard + Chain-of-Verification orchestration
├── llm/                    # LLM client package
│   ├── client.py           #   LLMClient (standard complete()/verify() interface)
│   ├── factory.py          #   LLMClientFactory.for_command(name)
│   ├── model_configs.yaml  #   command -> model assignments
│   └── ...                 #   api_handlers, parameter_handler, model_profiles, ...
├── utils/                  # Utilities package
│   ├── file_ops.py         #   read_document, glob expansion
│   ├── text_processing.py  #   chunk_text
│   ├── core.py             #   heartbeat, command-completion helpers
│   ├── formatting.py       #   ANSI message helpers (success_message, ...)
│   └── ...                 #   legal_reasoning, case_facts, rtf, truncation
├── logging/                # Logging/output package
│   ├── output_saver.py     #   save_command_output
│   └── __init__.py         #   save_log, log_task_event
├── citation/               # Citation verification package (Jade.io/AustLII)
├── prompts/                # YAML prompt templates (base, lookup, processing, ...)
└── commands/               # One package per command
    ├── __init__.py         #   register_commands()
    ├── lookup/  digest/  brainstorm/  extractfacts/  updatefacts/
    ├── draft/  strategy/  verify/  verify_cove/
    └── counselnotes/  barbrief/  caseplan/  refresh/
```

## Core Components

### LLMClient (llm/client.py)

Centralized client that provides a standardized interface to various LLM providers. In practice clients are usually built from the per-command model config via `LLMClientFactory.for_command("draft")`; direct construction also works:

```python
from litassist.llm.client import LLMClient

# Initialize with model ID and parameters
client = LLMClient("anthropic/claude-sonnet-4.6", temperature=0.2)

# Standard message format for all models
content, usage = client.complete([
    {"role": "system", "content": "Australian law only."},
    {"role": "user", "content": prompt}
])

# Optional self-verification (returns the corrections text and the model used)
corrections, model_used = client.verify(content)
```

### Utilities (utils/ package)

Provides document handling and monitoring capabilities:

```python
from litassist.utils.file_ops import read_document
from litassist.utils.text_processing import chunk_text
from litassist.utils.core import heartbeat
from litassist.timing import timed
from litassist.logging import save_log

# Document processing
text = read_document(file_path)  # Handles PDF, RTF, and text
chunks = chunk_text(text)        # Intelligent chunking

# Monitoring and logging
@heartbeat(30)  # Show progress every 30 seconds
def long_running_function():
    pass

@timed  # Measure and log execution time
def performance_critical_function():
    pass

# Audit logging
save_log("command_name", data_dict)  # JSON or Markdown
```

## Adding New Commands

To add a new command:

1. Create a new package in the `commands/` directory (e.g. `commands/newcmd/` with a `core.py` defining the command function)
2. Define a command function using Click decorators:
   ```python
   @click.command()
   @click.argument("input_argument", type=click.Path(exists=True))
   @click.option("--option", help="Help text")
   def new_command(input_argument, option):
       """Command description for help text."""
       # Implementation
   ```
3. Import the command and register it in `commands/__init__.py` via `register_commands()`

## Developer Notes

- **Error Handling**: Use `click.ClickException` for user-friendly error messages
- **Progress Feedback**: Use `click.progressbar` for multi-step processes
- **Resource Cleanup**: Ensure proper cleanup in finally blocks
- **Configuration**: Access via `from litassist.config import get_config`
- **Token Usage**: Track and log all API usage for cost monitoring

## Testing

Test fixtures and utilities are available in the `tests/` directory. Key test files:

- `conftest.py`: Shared fixtures and mocks
- `unit/`: Offline unit and (mocked) integration tests - no real API calls
- `../test-scripts/`: Manual real-API checks (incur cost; run manually)

Run tests with pytest:
```bash
python -m pytest
```

For detailed developer documentation, please refer to the main project README.md in the root directory.
