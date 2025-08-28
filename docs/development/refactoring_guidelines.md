# Refactoring Guidelines

This document outlines the key principles and guidelines for refactoring the codebase, based on the successful refactoring of the `refactor/large-funcs` branch.

## 1. Modularization and Single Responsibility Principle (SRP)

The primary goal of refactoring should be to break down large, monolithic files into smaller, more focused modules. Each module should have a single, well-defined responsibility.

*   **Guideline:** Identify distinct functionalities within a large file and extract them into separate modules.
*   **Example:** The `lookup.py` file was split into `search.py`, `fetchers.py`, `processors.py`, and `error_handlers.py`, each with a clear responsibility.

## 2. Separation of Concerns

Separate different aspects of the application into different packages and modules. This improves the organization of the codebase and makes it easier to find and modify code.

*   **Guideline:** Group related modules into packages. For example, all LLM-related functionality should be in the `llm` package, and all utility functions should be in the `utils` package.
*   **Example:** The `llm` package was refactored to separate API handling (`api_handlers.py`), client logic (`client.py`), and verification (`verification.py`).

## 3. Data-Driven Approach

Use data structures (like dictionaries or lists of objects) to drive logic instead of hardcoding it in long `if/elif/else` blocks. This makes the code more flexible and easier to extend.

*   **Guideline:** When you have a series of similar conditional blocks, consider refactoring them into a data-driven loop.
*   **Example:** The `validate_credentials` function in `cli.py` was refactored to use a list of service configurations to drive the validation process, eliminating repetitive code.

## 4. Configuration Management

Separate configuration from code by moving it to external files (e.g., YAML). This makes the application more flexible and easier to configure without changing the code.

*   **Guideline:** Identify hardcoded configurations (e.g., dictionaries of settings) and move them to a dedicated configuration file.
*   **Example:** The `COMMAND_CONFIGS` dictionary in `llm/client.py` was moved to a `command_configs.yaml` file.

## 5. Abstraction and Encapsulation

Use classes and functions to create clear interfaces and hide implementation details. This makes the code easier to use and reduces the risk of unintended side effects.

*   **Guideline:** Encapsulate complex logic within classes and provide a clean public interface.
*   **Example:** The `ChunkProcessor` class was created to encapsulate the logic for processing a document in chunks, hiding the complexity of the implementation from the `digest` command.

## 6. Adherence to Project-Specific Guidelines

Always follow the specific guidelines outlined in the project's documentation (e.g., `GEMINI.md` or `CLAUDE.md`). These guidelines are in place to ensure the quality, consistency, and maintainability of the codebase.

*   **Guideline:** Regularly review the project's guidelines and ensure that your code adheres to them.
*   **Example:** The refactoring of `extract_reasoning_trace` to use JSON instead of regex follows the guideline of minimizing local parsing of LLM output.

By following these guidelines, we can ensure that the codebase remains clean, well-organized, and easy to maintain as it continues to evolve.
