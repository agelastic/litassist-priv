# Test Status

Last updated: 29/05/2026

## Important Testing Policy

[WARNING] **ALL pytest tests MUST run offline with mocked dependencies**
- Pytest tests (in `tests/unit/`) NEVER make real API calls
- Manual test scripts (in `test-scripts/`) make REAL API calls for validation

## Current Test Architecture

The test suite consists of two distinct categories:

## Automated Unit Tests (pytest) [VERIFIED]
Located in `tests/unit/` - ALL run offline with mocks:
- `test_basic.py` - Basic infrastructure tests
- `test_real_functionality.py` - Real function tests with proper examples 
- `test_simple.py` - Simple functionality tests
- `test_barbrief.py` - Barbrief command unit tests
- `test_counselnotes.py` - CounselNotes command unit tests
- `test_llm_client_factory.py` - LLMClientFactory pattern verification
- `test_prompts.py` - Centralized prompt management system testing
- `test_prompt_templates.py` - YAML template validation and structure verification
- `test_citation_verification_simple.py` - Citation validation testing
- `test_verification.py` - Content verification testing

## Manual Integration Validation Scripts [WARNING]
Located in `test-scripts/` - these make REAL API calls and incur cost:
- `run_tests.sh` - wrapper that runs `test_integrations.py`
- `test_integrations.py` - **REAL API** connectivity: OpenRouter, Google CSE, Jade
- `test_quality.py` / `test_quality.sh` - **REAL API** response-quality validation
- `test_citation_fetching.py` - **REAL API** citation fetching via Google CSE / Jade (not covered by the mocked unit citation tests)
- `test_cli_comprehensive.sh` - **REAL API** CLI smoke for every registered command, each invocation stuffed with as many switches as the command accepts (`./test_cli_comprehensive.sh all`)
- `test_utils.py` - shared `ErrorHandler` helper imported by the scripts above (not a test itself)

**WARNING**: These scripts incur API costs! Run manually and sparingly.

**MAINTENANCE**: when a command is added to litassist, add it to
`test_cli_comprehensive.sh` (test function + `run_test_group` dispatch + the
`all` runner + the help menu), stuffed with switches. Offline, print-only
diagnostics do not belong here -- the offline pytest suite under `tests/unit/`
is the assert-based source of truth (it absorbed the former
`test_prompts.py`/`test_dynamic_parameters.py`/`test_barbrief_integration.py`
scripts).

## Running Tests

### Automated Unit Tests (Safe, Free, Fast)
```bash
# Run all unit tests - no API calls, no costs
python -m pytest tests/unit/

# Run with coverage
python -m pytest --cov=litassist tests/unit/
```

### Manual Integration Scripts (Real APIs, Costs Money!)
```bash
# [WARNING] These make REAL API calls and cost money!
cd test-scripts/
python test_integrations.py --all
# Or for specific services
python test_integrations.py --openrouter
```

## Test Design Philosophy

### For Pytest (Automated Tests)
1. **Offline Only** - ALL tests use mocks, zero API calls
2. **Fast** - Run in seconds, not minutes
3. **Free** - No API costs ever
4. **Reliable** - No network dependencies
5. **CI/CD Ready** - Safe for automated pipelines

### For Manual Scripts
1. **Real Validation** - Test actual API connectivity
2. **Cost Conscious** - Minimize token usage
3. **Diagnostic** - Provide detailed service status
4. **Selective** - Run only when needed
5. **Documented** - Clear warnings about costs

## Test Template

See `test_real_functionality.py` for examples of:
- Proper file handling with `isolated_filesystem()`
- Correct mocking patterns
- Real functionality testing

For testing approach details, see `docs/testing/test_README.md`.