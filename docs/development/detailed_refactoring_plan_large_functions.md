# Detailed Refactoring Plan for Large Functions

This document provides a detailed plan for refactoring the large functions identified in the initial refactoring analysis. The goal is to break down these functions into smaller, more manageable pieces, improving readability, testability, and maintainability.

## 1. Refactoring `litassist.commands.lookup.lookup`

**Current State:** The `lookup` function is a monolithic function responsible for searching, fetching, processing, and generating responses. This makes it difficult to understand, test, and modify.

**Proposed Refactoring:** Break down the function into a series of smaller, more focused functions, each responsible for a single part of the process. The main `lookup` function will become a coordinator that calls these new functions in sequence.

### Detailed Steps:

1.  **Create a `search` module/class:** This will encapsulate all the logic related to performing Google Custom Search Engine (CSE) lookups.
    *   **`search.perform_cse_search(service, query, cse_id, limit)`**: This function will take the CSE service, query, CSE ID, and limit as input and return a list of links and snippets. This will replace the existing `_perform_cse_search` function.
    *   **`search.search_all_sources(service, query, comprehensive)`**: This function will orchestrate the searches across all configured CSEs (Jade, AustLII, etc.), handle rate limiting, and return a consolidated list of links and snippets.

2.  **Create a `fetching` module/class:** This will handle all the logic related to fetching content from URLs.
    *   **`fetching.fetch_url_content(url, timeout)`**: This will be the main entry point for fetching content from a URL. It will delegate to the appropriate fetching strategy based on the URL.
    *   **`fetching._fetch_http(url, timeout)`**: A private function to handle plain HTTP requests.
    *   **`fetching._fetch_selenium(url, timeout)`**: A private function to handle fetching content from JavaScript-rendered pages using Selenium.
    *   **`fetching._extract_pdf(url, content)`**: A private function to extract text from PDF files.

3.  **Refactor the `lookup` function:** The main `lookup` function will be simplified to orchestrate the calls to the new modules.

    ```python
    def lookup(question, mode, extract, comprehensive, context, output, no_fetch):
        # 1. Perform searches
        links, snippets = search.search_all_sources(service, question, comprehensive)

        # 2. Fetch content
        if not no_fetch:
            contents = fetching.fetch_all_content(links)
        else:
            contents = []

        # 3. Build the prompt
        prompt = _build_lookup_prompt(question, links, contents, context, extract)

        # 4. Call the LLM
        client = LLMClientFactory.for_command("lookup", ...)
        content, usage = client.complete(prompt)

        # 5. Process the response
        formatted_content, json_data, json_file = _process_lookup_response(content, extract, ...)

        # 6. Save output and logs
        save_command_output(...)
        save_log(...)
    ```

4.  **Create helper functions for prompt building and response processing:**
    *   **`_build_lookup_prompt(...)`**: This function will be responsible for constructing the complex prompt sent to the LLM, including the question, links, fetched content, and any additional context or extraction instructions.
    *   **`_process_lookup_response(...)`**: This function will handle the processing of the LLM's response, including any extraction logic.

## 2. Refactoring `litassist.commands.digest.digest`

**Current State:** The `digest` function is another large function that handles file processing, chunking, LLM interaction, and output consolidation. It also has complex logic for handling failures and emergency saves.

**Proposed Refactoring:** Introduce a `ChunkProcessor` class to handle the processing of a single document, and simplify the main `digest` function to iterate over files and orchestrate the process.

### Detailed Steps:

1.  **Create a `ChunkProcessor` class:**
    *   **`__init__(self, client, mode, context)`**: Initialize the processor with the LLM client and other configuration.
    *   **`process_document(self, file_path)`**: This method will read a document, chunk it, and process each chunk using the LLM. It will handle the logic for both single and multiple chunk documents, as well as sub-chunking for very large chunks. It will return a list of chunk analyses.
    *   **`_process_chunk(self, chunk, chunk_num, total_chunks)`**: A private method to process a single chunk with the LLM.

2.  **Refactor the `digest` function:**
    *   The main `digest` function will be responsible for iterating over the input files, creating a `ChunkProcessor` instance, and calling `process_document` for each file.
    *   It will then collect the results from all files and call a new `_consolidate_digests` function to create the final output.

3.  **Create a `_consolidate_digests` function:** This function will take the analyses from all chunks and all files and use the LLM to create a final, consolidated summary or issue list.

4.  **Encapsulate emergency save logic:** The emergency save functionality can be extracted into a context manager or a decorator to make the main `digest` function cleaner.

## 3. Refactoring `litassist.llm.LLMClient.complete`

**Current State:** The `complete` method is the heart of the LLM interaction, but it has become overloaded with responsibilities, including message preparation, API calls, and complex citation verification logic.

**Proposed Refactoring:** Extract the citation verification and message preparation logic into separate methods to make the `complete` method more focused on the core task of making the LLM call.

### Detailed Steps:

1.  **Extract citation verification logic:**
    *   Create a new private method `_handle_citation_verification(self, content)` that takes the LLM's response and performs the citation verification and retry logic. This method will return the verified (and possibly corrected) content.

2.  **Extract message preparation logic:**
    *   Create a new private method `_prepare_messages(self, messages)` that handles the manipulation of system messages, such as prepending the Australian law prompt.

3.  **Simplify the `complete` method:** The `complete` method will then become a more straightforward sequence of calls:

    ```python
    def complete(self, messages, skip_citation_verification=False, **overrides):
        # 1. Prepare messages
        prepared_messages = self._prepare_messages(messages)

        # 2. Execute API call
        response = self._execute_api_call_with_retry(self.model, prepared_messages, ...)
        content = response.choices[0].message.content
        usage = response.usage

        # 3. Handle citation verification
        if not skip_citation_verification:
            content = self._handle_citation_verification(content)

        # 4. Log and return
        save_log(...)
        return content, usage
    ```

## 4. Refactoring `litassist.cli.validate_credentials`

**Current State:** The `validate_credentials` function contains repetitive blocks of code for validating each service (OpenAI, Pinecone, etc.).

**Proposed Refactoring:** Use a data-driven approach to generalize the validation logic.

### Detailed Steps:

1.  **Create a data structure for service configurations:**
    *   Define a list of dictionaries, where each dictionary represents a service to be validated. It will contain the service name, the placeholder check key, and a validation function.

    ```python
    SERVICES_TO_VALIDATE = [
        {"name": "OpenAI", "placeholder_key": "openai", "validator": _validate_openai},
        {"name": "Pinecone", "placeholder_key": "pinecone", "validator": _validate_pinecone},
        # ... and so on for other services
    ]
    ```

2.  **Create small, focused validation functions:**
    *   For each service, create a small function (e.g., `_validate_openai`, `_validate_pinecone`) that contains the specific logic for validating that service's credentials.

3.  **Create a generic `_validate_service` function:**
    *   This function will take a service configuration dictionary as input. It will check for placeholder credentials and then call the corresponding validator function, printing the success or failure message.

4.  **Simplify the `validate_credentials` function:**
    *   The main `validate_credentials` function will simply iterate over the `SERVICES_TO_VALIDATE` list and call `_validate_service` for each one.
