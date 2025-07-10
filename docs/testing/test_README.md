# LitAssist Testing Documentation

This document covers both automated unit tests (pytest) and manual integration validation scripts.

## Important Testing Policy

[WARNING] **ALL pytest tests MUST run offline with mocked dependencies** [WARNING]
- No pytest test should EVER make real API calls
- All external services must be mocked in pytest tests
- Real API testing happens only through manual scripts in `test-scripts/`

## Automated Unit Tests (pytest)

The automated test suite uses pytest and runs completely offline:

### What We Test with Mocks

1. **OpenAI API** - Mocked embedding generation and completion capabilities
2. **Pinecone Vector DB** - Mocked vector storage and retrieval with MMR
3. **OpenRouter** - Mocked model access and completion via the OpenRouter gateway
4. **Google CSE & Jade** - Mocked case law lookup and retrieval

All these integrations are tested using mocks to ensure functionality without API costs.

### Unit Test Coverage

The project includes comprehensive offline unit tests for all major commands and utilities:

### Command Tests
- **test_verify_command.py**: Tests the verify command's citation verification, legal soundness checking, and reasoning trace functionality
- **test_strategy_command_comprehensive.py**: Validates strategy generation with case facts and brainstormed strategies
- **test_draft_command_comprehensive.py**: Tests document drafting with various input combinations
- **test_barbrief.py**: Tests barrister's brief generation with 10-heading validation and verification optimization
- **test_basic.py**: Basic smoke tests for all CLI commands

### Utility Tests
- **test_citation_verification_simple.py**: Tests citation pattern matching and validation
- **test_verification.py**: Tests content verification utilities
- **test_prompts.py**: Validates prompt management system
- **test_prompt_templates.py**: Ensures YAML template integrity
- **test_llm_client_factory.py**: Tests LLM client configuration and restrictions
- **test_utils_comprehensive.py**: Tests core utilities including LegalReasoningTrace and verification optimization

### Running Unit Tests
```bash
# Run all unit tests (always offline, no API calls)
pytest tests/unit/

# Run specific test file
pytest tests/unit/test_verify_command.py

# Run with coverage
pytest --cov=litassist tests/unit/

# Note: ALL these tests use mocks - no real API calls ever!
```

## Manual Integration Validation Scripts

[WARNING] **These scripts make REAL API calls and incur costs!** [WARNING]

Separate from pytest, we have manual validation scripts in `test-scripts/` for testing real API integrations:

| Service | Test Types | Purpose |
|---------|------------|---------|
| OpenAI | Model Listing, Embedding Generation, Completion | Verify that API key works and all required functionality is accessible |
| Pinecone | Connection, Basic Operations | Verify that vector storage and basic operations work |
| OpenRouter | Connection, Basic Completion | Lightweight verification that completions flow through this critical endpoint |
| Google CSE | Basic Connectivity | Verify that Google Custom Search API is accessible for case law lookup |
| Jade | Public Homepage Access, Specific Case Access | Verify that Jade's public endpoints are accessible for legal case retrieval |

### Running Manual Integration Scripts

**[WARNING] These commands make REAL API calls and cost money! [WARNING]**

```bash
# Navigate to test-scripts directory first
cd test-scripts/

# Run all integration tests (REAL API CALLS)
python test_integrations.py

# Run just OpenAI tests
python test_integrations.py --openai

# Run Pinecone tests
python test_integrations.py --pinecone

# Run OpenRouter tests
python test_integrations.py --openrouter

# Run Google CSE tests
python test_integrations.py --google

# Run Jade tests
python test_integrations.py --jade

# Run specific combinations
python test_integrations.py --openai --pinecone
```

## Test Results

Results are displayed in the terminal with color-coding for success/failure and detailed information about each test outcome.

Additionally, a JSON file with detailed results is saved as `test_results_YYYYMMDD-HHMMSS.json` for audit and debugging purposes.

## Important Considerations

### For Pytest (Automated Tests)
1. **No API Costs**: All pytest tests use mocks - zero API costs
2. **Fast Execution**: Mocked tests run quickly
3. **Safe to Run**: Can be run anytime without cost concerns
4. **CI/CD Ready**: Perfect for automated pipelines

### For Manual Integration Scripts
1. **API Costs**: Running these scripts WILL incur API usage costs from OpenAI, OpenRouter, and Pinecone
2. **Test Data**: The Pinecone tests create and delete temporary test vectors in a namespace called "test_namespace"
3. **API Keys**: Valid API keys must be configured in `config.yaml` before running tests
4. **Dependencies**: Requires the `openai`, `pinecone-client`, `numpy`, and `pyyaml` packages

## Test Design Philosophy

The tests are designed to be:

1. **Lightweight**: Minimizing resource usage, API calls, and costs
2. **Thorough**: Covering essential functionality rather than every edge case
3. **Non-destructive**: Cleaning up after themselves and not interfering with production data
4. **Informative**: Providing clear, detailed output about success/failure and performance
5. **Modular**: Supporting running specific test subsets when needed

## When to Run Tests

### Pytest Tests (Run Frequently)
1. **Every Code Change**: Before committing any changes
2. **CI/CD Pipeline**: Automatically on every push
3. **Pre-deployment**: As part of release process
4. **Development**: During active development

### Manual Integration Scripts (Run Sparingly)
1. **Initial Setup**: One-time verification of API credentials
2. **Major Updates**: After significant dependency changes
3. **Production Issues**: When debugging real API problems
4. **Quarterly Validation**: Periodic health checks
