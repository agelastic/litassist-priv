# LitAssist Testing Approach

## Overview

LitAssist maintains two distinct categories of tests:

1. **Automated Unit Tests (pytest)** - Run offline with mocked dependencies
2. **Manual Integration Validation Scripts** - Make real API calls for service validation

## Testing Policy

⚠️ **CRITICAL: ALL pytest tests MUST run offline with mocked dependencies** ⚠️

- **No pytest test should EVER make real API calls**
- All external services (OpenAI, Pinecone, OpenRouter, Google CSE, Jade) must be mocked in pytest
- Real API testing happens only through manual scripts in `test-scripts/`
- This separation ensures fast, cost-free automated testing while preserving integration validation capabilities

## Automated Unit Testing (pytest)

### What We Test with Mocks

All unit tests in `tests/unit/` use mocked versions of:

1. **OpenAI API**: Mocked embedding generation and completion capabilities
2. **Pinecone Vector Database**: Mocked vector storage and retrieval with MMR
3. **OpenRouter**: Mocked model routing and multi-provider access
4. **Google CSE & Jade**: Mocked case law lookup and citation verification

### Benefits of Mocked Testing

1. **Zero API Costs**: No real API calls means no usage charges
2. **Fast Execution**: Tests run in seconds, not minutes
3. **Reliable CI/CD**: No flaky tests due to network issues
4. **Unlimited Runs**: Developers can run tests frequently without cost concerns
5. **Predictable Results**: Mocked responses ensure consistent test behavior

### Integration Tests Within pytest

Files with "integration" in their names (e.g., `test_llm_integration_comprehensive.py`) test how components work together but still use mocks exclusively. These are NOT real integration tests but rather comprehensive unit tests that verify component interactions.

## Manual Integration Validation Scripts

### Purpose

The `test-scripts/` directory contains scripts for manual validation of real API integrations:

- `test_integrations.py` - Validates connectivity to OpenAI, Pinecone, OpenRouter
- `test_quality.py` - Tests output quality with real LLM responses
- `test_cli_comprehensive.sh` - Full CLI testing with real API calls

### When to Use Manual Scripts

1. **Initial Setup**: One-time verification of API credentials
2. **Major Updates**: After significant dependency or API changes
3. **Production Debugging**: When investigating real API issues
4. **Periodic Health Checks**: Quarterly validation of service integrations

### Cost Considerations

Manual integration scripts incur real API costs:
- OpenAI embedding and completion tokens
- OpenRouter model usage
- Pinecone operations
- Google CSE queries

Run these scripts sparingly and only when necessary.

## Services Under Test

### OpenAI API
- **Unit Tests**: Mock all embedding and completion calls
- **Manual Tests**: Verify real API connectivity and model availability

### Pinecone Vector Database
- **Unit Tests**: Mock all vector operations (upsert, query, delete)
- **Manual Tests**: Test real vector storage and MMR search

### OpenRouter Gateway
- **Unit Tests**: Mock model routing and responses
- **Manual Tests**: Verify gateway connectivity and model access

### Google CSE & Jade
- **Unit Tests**: Mock search results and case law responses
- **Manual Tests**: Validate real citation lookups

## Testing Best Practices

### For Developers

1. **Always run pytest before committing** - It's fast and free
2. **Never add real API calls to pytest tests** - Use mocks exclusively
3. **Keep manual scripts updated** - But run them sparingly
4. **Document mock behaviors** - Help future developers understand test assumptions

### For CI/CD

1. **Run full pytest suite on every push** - Safe and cost-free
2. **Never run manual integration scripts in CI** - Too expensive
3. **Monitor test coverage** - Ensure new features have tests
4. **Fail fast on test failures** - Don't deploy broken code

## Migration from Old Approach

Previously, some documentation suggested integration tests within pytest. This has been clarified:

1. All pytest tests are now explicitly offline-only
2. Real API testing moved to separate manual scripts
3. Documentation updated to reflect this separation
4. No more confusion about test costs or API usage

## Conclusion

This dual approach provides the best of both worlds:
- Fast, free, reliable automated testing for development
- Thorough manual validation scripts for when real API testing is needed

By maintaining this clear separation, we ensure efficient development workflows while preserving the ability to validate real service integrations when necessary.