# Detailed Refactoring Plan for Duplicated and Repetitive Code

This document provides a detailed plan for refactoring the areas of the codebase with duplicated and repetitive code, as identified in the initial refactoring analysis.

## 1. Refactoring API Credential Validation in `cli.py`

**Problem:** The `validate_credentials` function in `litassist/cli.py` contains repetitive `try/except` blocks for each service (OpenAI, Pinecone, Google CSE, OpenRouter). This leads to significant code duplication and makes it cumbersome to add new validation checks.

**Solution:** Refactor to a data-driven approach by creating a generic validation orchestrator and a set of small, focused validation functions for each service.

### Detailed Steps:

1.  **Define a Data Structure for Services:**
    In `litassist/cli.py`, define a list of dictionaries that holds the configuration for each service to be validated. This will centralize the configuration and make it easy to add new services.

    ```python
    SERVICES_TO_VALIDATE = [
        {
            "name": "OpenAI",
            "placeholder_key": "openai",
            "validator": _validate_openai,
        },
        {
            "name": "Pinecone",
            "placeholder_key": "pinecone",
            "validator": _validate_pinecone,
        },
        {
            "name": "Google CSE",
            "placeholder_key": "google_cse",
            "validator": _validate_google_cse,
        },
        {
            "name": "OpenRouter",
            "placeholder_key": "openrouter",
            "validator": _validate_openrouter,
        },
    ]
    ```

2.  **Create Individual Validation Functions:**
    For each service, extract the validation logic into its own small, focused function. These functions will contain the `try/except` blocks and the specific API calls for validation.

    ```python
    def _validate_openai(config):
        # Validation logic for OpenAI
        openai.Model.list()

    def _validate_pinecone(config):
        # Validation logic for Pinecone
        pinecone.init(api_key=config.pc_key, environment=config.pc_env)
        pinecone.list_indexes()

    # ... and so on for Google CSE and OpenRouter
    ```

3.  **Create a Generic Validation Orchestrator:**
    Create a function `_validate_service` that takes a service configuration dictionary as input. This function will handle the placeholder check and call the appropriate validation function, printing the success or failure message.

    ```python
    def _validate_service(service_config, placeholder_checks):
        service_name = service_config["name"]
        placeholder_key = service_config["placeholder_key"]
        validator = service_config["validator"]

        if placeholder_checks.get(placeholder_key, False):
            print(f"  - Skipping {service_name} connectivity test (placeholder credentials)")
            return

        try:
            print(f"  - Testing {service_name} API... ", end="", flush=True)
            validator(load_config())
            print("OK")
        except Exception as e:
            print("FAILED")
            sys.exit(f"Error: {service_name} API test failed: {e}")
    ```

4.  **Simplify `validate_credentials`:**
    The main `validate_credentials` function will be simplified to iterate over the `SERVICES_TO_VALIDATE` list and call the `_validate_service` orchestrator for each one.

    ```python
    def validate_credentials(show_progress=True):
        config = load_config()
        placeholder_checks = config.using_placeholders()

        if show_progress:
            print("Verifying API connections")

        for service_config in SERVICES_TO_VALIDATE:
            _validate_service(service_config, placeholder_checks)

        if show_progress:
            print("All API connections verified.\n")
    ```

## 2. Unifying Chunk Processing in `digest.py`

**Problem:** The `digest` function in `litassist/commands/digest.py` has separate code paths for handling a single chunk versus multiple chunks. The single-chunk logic is a simplified version of the multiple-chunk logic, leading to code duplication and increased complexity.

**Solution:** Treat a single chunk as a special case of multiple chunks (i.e., a list with one item). This will unify the code paths and simplify the function.

### Detailed Steps:

1.  **Remove the Single-Chunk `if` Block:**
    The entire `if len(chunks) == 1:` block will be removed from the `digest` function. The logic within this block is redundant.

2.  **Always Use the Multiple-Chunk Logic:**
    The code path that handles multiple chunks (the `else` block) will now be used for all cases, regardless of the number of chunks. This logic already iterates through a list of chunks, processes them, and then consolidates the results. When there is only one chunk, it will simply process that single chunk and the consolidation step will effectively just return the analysis of that chunk.

3.  **Adjust the Consolidation Logic (if necessary):**
    The consolidation prompt and logic should be reviewed to ensure they handle the case of a single chunk gracefully. The LLM should be able to "consolidate" a single analysis without any issues, but the prompt can be tweaked to be more explicit if needed (e.g., "Consolidate the following analysis/analyses into a final report...").

4.  **Simplify the `digest` function:**
    By removing the conditional logic for single vs. multiple chunks, the `digest` function will become more linear and easier to follow. The main flow will be:
    *   Read the document.
    *   Chunk the text.
    *   Process each chunk (using the loop).
    *   Consolidate the results.
    *   Save the output.

This refactoring will make the `digest` command more robust and easier to maintain, as there will be a single, unified logic for processing documents of any length.

```