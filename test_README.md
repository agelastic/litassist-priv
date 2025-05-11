# LitAssist Integration Tests

This test suite validates the key external service integrations used by LitAssist, particularly focusing on:

1. **OpenAI API** - Testing embedding generation and completion capabilities
2. **Pinecone Vector DB** - Testing vector storage and retrieval with MMR
3. **OpenRouter** - Testing model access and completion via the OpenRouter gateway

## Why Test OpenRouter?

While we primarily focus on OpenAI and Pinecone as core dependencies, the OpenRouter integration warrants testing because:

1. **Gateway Architecture**: LitAssist uses OpenRouter as a gateway to access various LLMs, making it a critical part of the execution path
2. **Completion Flow**: All model completions route through OpenRouter before reaching the application
3. **Model Availability**: OpenRouter provides access to models that may not be directly available via OpenAI
4. **Cost Control**: By creating minimal tests for OpenRouter, we can verify functionality without significant cost impact

## Test Coverage

| Service | Test Types | Purpose |
|---------|------------|---------|
| OpenAI | Model Listing, Embedding Generation, Completion | Verify that API key works and all required functionality is accessible |
| Pinecone | Connection, Vector Operations, MMR Search | Verify that vector storage, retrieval, and diversity-based search work properly |
| OpenRouter | Connection, Basic Completion | Lightweight verification that completions flow through this critical endpoint |

## Running the Tests

```bash
# Run all tests
python test_integrations.py

# Run just OpenAI tests
python test_integrations.py --openai

# Run Pinecone tests
python test_integrations.py --pinecone

# Run OpenRouter tests
python test_integrations.py --openrouter

# Run specific combinations
python test_integrations.py --openai --pinecone
```

## Test Results

Results are displayed in the terminal with color-coding for success/failure and detailed information about each test outcome.

Additionally, a JSON file with detailed results is saved as `test_results_YYYYMMDD-HHMMSS.json` for audit and debugging purposes.

## Important Considerations

1. **API Costs**: Running these tests will incur small API usage costs from OpenAI, OpenRouter, and potentially Pinecone
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

These tests are valuable in several scenarios:

1. **Initial Setup**: Verifying configuration during new environment setup
2. **Dependency Updates**: After updating OpenAI or Pinecone client libraries
3. **Troubleshooting**: When diagnosing issues with LitAssist functionality
4. **CI/CD Pipeline**: As part of automated testing before deployment
