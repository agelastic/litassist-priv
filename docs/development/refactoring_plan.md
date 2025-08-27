# Refactoring Plan

Based on an analysis of the codebase, several opportunities for refactoring have been identified that could improve the code's readability, maintainability, and adherence to the project's own guidelines.

Here is a summary of the key areas for refactoring:

### 1. Long and Complex Functions

Several functions and methods in the codebase are very long and handle multiple responsibilities. Breaking them down into smaller, more focused functions would improve readability and make the code easier to test and maintain.

*   **`litassist.commands.lookup.lookup`**: This function is a prime candidate for refactoring. It currently handles searching, content fetching, prompt generation, LLM interaction, and output processing. This could be split into separate functions for each of these steps.
*   **`litassist.commands.digest.digest`**: Similar to `lookup`, this function manages file reading, chunking, processing individual chunks, consolidating results, and saving outputs. It also contains complex logic for handling failures and emergency saves. Breaking this down would significantly improve clarity.
*   **`litassist.llm.LLMClient.complete`**: This method is the core of the LLM interaction and has grown quite complex. It manages system message manipulation, parameter merging, API calls with retries, and citation verification. The citation verification and retry logic, in particular, could be extracted into their own methods.
*   **`litassist.cli.validate_credentials`**: This function has a repetitive structure for validating each API credential. This could be refactored into a more data-driven approach, where the validation logic is generalized and applied to a list of services and their configurations.

### 2. Duplicated and Repetitive Code

There are a few instances of duplicated code that could be consolidated to reduce redundancy and improve maintainability.

*   **API Credential Validation in `cli.py`**: The `validate_credentials` function contains very similar blocks of code for testing the connectivity to OpenAI, Pinecone, Google CSE, and OpenRouter. This could be refactored into a single function that takes the service name and a validation function as arguments.
*   **Chunk Processing in `digest.py`**: The logic for processing a single chunk is a simplified version of the logic for processing multiple chunks. These two paths could be unified to avoid code duplication.

### 3. Configuration Management

*   **`COMMAND_CONFIGS` in `llm.py`**: The `LLMClientFactory` class contains a large dictionary that maps commands to their LLM configurations. As the number of commands grows, this dictionary will become harder to manage. It would be beneficial to move this configuration to a separate YAML file, which would make it easier to update and maintain without changing the code.

### 4. Adherence to Project Guidelines (`GEMINI.md`)

The project has a strong guideline to "Minimize Local Parsing Through Better Prompt Engineering". However, there are a few places where the code relies on parsing the LLM's output instead of requesting a structured format.

*   **`extract_reasoning_trace` in `utils.py`**: This function uses regular expressions to extract the reasoning trace from the LLM's output. This is a brittle approach that could be improved by updating the prompts to request the reasoning trace in a structured JSON format. This would align with the project's philosophy and make the extraction process more reliable.
