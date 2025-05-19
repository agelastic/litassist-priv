# LitAssist Refactored

This directory contains the refactored version of the LitAssist tool, which provides automated litigation support workflows for Australian legal practice.

## Structure

The codebase has been refactored from a monolithic script into a modular package:

```
litassist/
├── __init__.py             # Package initialization
├── config.py               # Configuration management
├── utils.py                # Utility functions
├── llm.py                  # LLM client wrapper
├── retriever.py            # Vector search implementation
├── cli.py                  # Main CLI interface
└── commands/               # Command implementations
    ├── __init__.py         # Command registration
    ├── lookup.py           # Case-law lookup
    ├── digest.py           # Document digestion
    ├── brainstorm.py       # Creative legal strategy generation
    ├── extractfacts.py     # Case facts extraction
    └── draft.py            # Citation-rich drafting
```

## Running the Application

The application can be run using the `litassist_cli.py` script in the parent directory:

```bash
./litassist_cli.py [OPTIONS] COMMAND [ARGS]...
```

## Commands

The following commands are available:

- `lookup`: Rapid case-law lookup via Google CSE + Gemini
- `digest`: Mass-document digestion via Claude
- `brainstorm`: Generate comprehensive legal strategies via Grok (orthodox/unorthodox, tailored to party side and legal area)
- `extractfacts`: Auto-generate case_facts.txt under structured headings
- `draft`: Citation-rich drafting via RAG & GPT-4o

## Refactoring Benefits

This refactored structure offers several advantages:

1. **Separation of Concerns**: Each module has a single responsibility
2. **Maintainability**: Easier to update individual components
3. **Readability**: Clearer organization makes the code easier to understand
4. **Testability**: Components can be tested in isolation
5. **Extensibility**: New commands can be added without modifying existing code
