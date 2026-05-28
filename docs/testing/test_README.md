# LitAssist Testing Documentation

Last updated: 18/02/2026

This document covers both automated unit tests (pytest) and manual integration validation scripts.

## Important Testing Policy

**ALL pytest tests MUST run offline with mocked dependencies.**

- No pytest test should ever make real API calls
- All external services must be mocked in pytest tests
- Real API testing happens only through manual scripts in `test-scripts/`

## Automated Unit Tests (pytest)

The automated test suite uses pytest and runs completely offline.

### What We Mock

1. **OpenRouter** -- mocked model access and completion via the OpenRouter gateway
2. **OpenAI** -- mocked completion (BYOK calls for o3-pro)
3. **Google CSE** -- mocked case law lookup and search results

All integrations are tested using mocks to ensure functionality without API costs.

### Running Unit Tests

```bash
# Run all unit tests (always offline, no API calls)
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_verify_command.py

# Run with coverage
pytest --cov=litassist tests/unit/
```

Test files live in `tests/unit/` and cover all major commands and utilities. Run `ls tests/unit/test_*.py` to see the current list.

## Manual Integration Validation Scripts

**These scripts make REAL API calls and incur costs.**

Separate from pytest, manual validation scripts in `test-scripts/` test real API connectivity:

| Service | Purpose |
|---------|---------|
| OpenRouter | Verify completions flow through the routing endpoint |
| OpenAI | Verify API key works and required functionality is accessible |
| Google CSE | Verify Custom Search API is accessible for case law lookup |

### Running Manual Integration Scripts

```bash
cd test-scripts/

# Run all integration tests (REAL API CALLS)
python test_integrations.py

# Run specific service tests
python test_integrations.py --openrouter
python test_integrations.py --openai
python test_integrations.py --google
python test_integrations.py --jade
```

Results are displayed in the terminal and saved as `test_results_YYYYMMDD-HHMMSS.json`.

## When to Run Tests

### Pytest Tests (Run Frequently)
1. Before committing any changes
2. Automatically in CI/CD pipelines
3. During active development

### Manual Integration Scripts (Run Sparingly)
1. Initial setup -- verify API credentials
2. After significant dependency changes
3. When debugging real API problems
