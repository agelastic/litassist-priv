# Test Status

## Current Test Architecture

The test suite consists of several layers of tests:

## Unit Tests ✅
Located in `tests/unit/`:
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

## Integration Tests ✅
Located in test-scripts/:
- `test_connectivity.py` - Tests basic connectivity to external services
- `test_integrations.py` - Tests integration with external APIs (OpenAI, Pinecone, OpenRouter)
- `test_quality.py` - Tests response quality from various commands
- `test_barbrief_integration.py` - Barbrief command integration tests without API calls
- `test_cli_comprehensive.sh` - Complete CLI testing suite with mock files

## Running Tests

Integration tests can be run using:
```bash
./test-scripts/run_tests.sh --all
# Or for specific services
./test-scripts/run_tests.sh --openai --pinecone
```

Unit tests can be run using:
```bash
python -m pytest
```

## Test Design Philosophy

Tests are designed to be:
1. **Lightweight** - Minimizing resource usage, API calls, and costs
2. **Thorough** - Covering essential functionality
3. **Non-destructive** - Cleaning up after themselves
4. **Informative** - Providing clear output about success/failure
5. **Modular** - Supporting running specific test subsets when needed

## Test Template

See `test_real_functionality.py` for examples of:
- Proper file handling with `isolated_filesystem()`
- Correct mocking patterns
- Real functionality testing

For integration test approach details, see [integration_testing_approach.md](/docs/development/integration_testing_approach.md).