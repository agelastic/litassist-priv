# Dead Code Analysis Report

This report details the findings from the `vulture` static analysis tool, which was run to identify unused code in the `litassist` repository. Each entry includes the identified code, its location, and an analysis of whether it is genuinely dead code or a false positive.

---

## `litassist/citation_patterns.py`

**Conclusion:** The offline, pattern-based validation functions in this file appear to be deprecated. The main entry point, `validate_citation_patterns`, now bypasses them in favor of online verification, rendering them unused.

### 1. `validate_generic_names` (Line 249)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This function is not called anywhere in the codebase. The main `validate_citation_patterns` function skips all local, pattern-based checks.
- **Recommendation:** Remove.

```python
def validate_generic_names(content: str, complete_citations: set) -> List[str]:
    """
    Check for generic/placeholder case names that might be hallucinated.
    ...
    """
    # ... function implementation
```

### 2. `validate_court_abbreviations` (Line 341)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Unused for the same reason as `validate_generic_names`.
- **Recommendation:** Remove.

```python
def validate_court_abbreviations(content: str) -> List[str]:
    """
    Validate court identifiers in medium-neutral citations.
    ...
    """
    # ... function implementation
```

### 3. `validate_report_series` (Line 396)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Unused.
- **Recommendation:** Remove.

```python
def validate_report_series(content: str) -> List[str]:
    """
    Validate traditional report series citations.
    ...
    """
    # ... function implementation
```

### 4. `validate_page_numbers` (Line 420)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Unused.
- **Recommendation:** Remove.

```python
def validate_page_numbers(content: str) -> List[str]:
    """
    Check for unrealistic page numbers in citations.
    ...
    """
    # ... function implementation
```

### 5. `validate_parallel_citations` (Line 443)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Unused.
- **Recommendation:** Remove.

```python
def validate_parallel_citations(content: str) -> List[str]:
    """
    Check consistency in parallel citations.
    ...
    """
    # ... function implementation
```

### 6. `detect_hallucination_patterns` (Line 469)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Unused.
- **Recommendation:** Remove.

```python
def detect_hallucination_patterns(content: str) -> List[str]:
    """
    Detect known AI hallucination patterns in case names.
    ...
    """
    # ... function implementation
```

### 7. `extract_complete_citations` (Line 490)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Unused.
- **Recommendation:** Remove.

```python
def extract_complete_citations(content: str) -> set:
    """
    Extract all complete citations to exclude from generic name checking.
    ...
    """
    # ... function implementation
```

### 8. `volume` variable (Line 410)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This variable is defined inside `validate_report_series`, which is itself dead code.
- **Recommendation:** Remove (will be removed with the function).

### 9. `verified_citations` variable (Line 550)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** In `validate_citation_patterns`, this variable is assigned but never used. The function's logic focuses on `unverified_citations`.
- **Recommendation:** Remove.

---

## `litassist/citation_verify.py`

**Conclusion:** This file contains several helper functions that are not part of the primary verification workflow. Some appear to be remnants of previous logic, while others may be used in tests or for debugging.

### 1. `TestVerificationError` class (Line 153)

- **Status:** False Positive
- **Confidence:** 100%
- **Analysis:** This exception class is used in the test suite to verify that specific errors are raised correctly. It should not be removed.
- **Recommendation:** Keep.

### 2. `in_test_mode` (Line 160)

- **Status:** False Positive
- **Confidence:** 100%
- **Analysis:** This function is used in the test suite to alter application behavior during tests.
- **Recommendation:** Keep.

### 3. `search_jade_via_google_cse` (Line 393)

- **Status:** False Positive
- **Confidence:** 100%
- **Analysis:** This function is used in the test suite (`tests/unit/test_citation_verification_simple.py`) to test citation verification functionality.
- **Recommendation:** Keep.

### 1. `TestVerificationError` class (Line 153)

- **Status:** Review Needed
- **Confidence:** 60%
- **Analysis:** This custom exception is likely used in the test suite to verify that specific errors are raised correctly. It should not be removed without first checking the project's tests.
- **Recommendation:** Investigate (search test files for usage).

```python
class TestVerificationError(CitationVerificationError):
    """Raised for expected verification errors in tests - no console output."""
    def __str__(self):
        return ""
```

### 2. `in_test_mode` (Line 160)

- **Status:** Review Needed
- **Confidence:** 60%
- **Analysis:** Like `TestVerificationError`, this function is almost certainly used within the test suite to alter application behavior during tests.
- **Recommendation:** Investigate (search test files for usage).

```python
def in_test_mode():
    """Check if running in test mode."""
    return os.environ.get("LITASSIST_TEST_MODE") == "1"
```

### 3. `search_jade_via_google_cse` (Line 393)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This function is a simple wrapper around `search_legal_database_via_cse`. The main `verify_single_citation` function now calls the underlying function directly, making this wrapper redundant.
- **Recommendation:** Remove.

```python
def search_jade_via_google_cse(citation: str, timeout: int = 10) -> bool:
    """
    Backward compatibility wrapper for search_legal_database_via_cse.
    ...
    """
    success, url = search_legal_database_via_cse(citation, cse_id=None, cse_name="Jade.io", timeout=timeout)
    return success
```

### 4. `is_core_citation` (Line 806)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This function aims to determine the importance of a citation within a text block. However, it is not called from any part of the active codebase. It may have been part of a feature that was planned but not fully implemented.
**Update:** A search of the `tests/` directory revealed no usages of these items. They are confirmed as dead code.
- **Recommendation:** Remove.

```python
def is_core_citation(text_section: str, citation: str) -> bool:
    """
    Determine if a citation is core to a text section or just supporting.
    ...
    """
    # ... function implementation
```

### 5. `get_verification_stats` (Line 853)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Not called within the application. Likely a helper for debugging or a planned monitoring feature.
- **Recommendation:** Remove.

```python
def get_verification_stats() -> Dict:
    """
    Get statistics about citation verification cache.
    ...
    """
    # ... function implementation
```

### 6. `clear_verification_cache` (Line 873)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Not called within the application. Likely intended for use in test setup/teardown. A search in the test suite is required to confirm.
- **Recommendation:** Remove.

```python
def clear_verification_cache():
    """Clear the citation verification cache."""
    with _cache_lock:
        _citation_cache.clear()
---

## `litassist/cli.py`

### 1. `test` function (Line 279)
- **Status:** False Positive
- **Confidence:** 60%
- **Analysis:** This function is a `click` command, designed to be invoked from the command line (`litassist test`), not called directly from within the Python codebase. Static analysis tools like `vulture` often flag these as unused because they don't trace command-line entry points.
### 1. `selenium_enabled` attribute (Line 162)
- **Status:** False Positive
- **Confidence:** 100%
- **Analysis:** This configuration flag is used in the test suite (`tests/conftest.py`, `tests/unit/test_cli_command_loading.py`, `tests/unit/test_lookup_command.py`) to test Selenium-related functionality.
- **Recommendation:** Keep.

### 2. `selenium_timeout_multiplier` attribute (Line 163)
- **Status:** False Positive
- **Confidence:** 100%
- **Analysis:** This configuration flag is used in the test suite for testing Selenium timeout behavior.
- **Recommendation:** Keep.
- **Recommendation:** Keep.

```python
@cli.command()
def test():
### 1. `delete` method (Line 102)
- **Status:** False Positive
- **Confidence:** 100%
- **Analysis:** This method is used in test scripts (`test-scripts/test_quality.py`, `test-scripts/test_integrations.py`) to test Pinecone delete functionality.
- **Recommendation:** Keep.
    """
    Test API connectivity and web scraping capabilities.
    ...
    """
    validate_credentials(show_progress=True)
    test_scraping_capabilities()
```

---

## `litassist/config.py`

### 1. `selenium_enabled` attribute (Line 162)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This configuration flag was intended to control the use of Selenium for web scraping. A project-wide search confirms that Selenium is not implemented or used anywhere, making this flag redundant.
- **Recommendation:** Remove.

### 2. `selenium_timeout_multiplier` attribute (Line 163)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This is a supporting configuration for the unused Selenium feature. It is also dead code.
- **Recommendation:** Remove.

---

## `litassist/helpers/pinecone_config.py`

### 1. `delete` method (Line 102)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This method implements the `delete` functionality for the `PineconeWrapper`. However, no part of the application's current feature set requires deleting vectors from the Pinecone index.

### 1. `get_model_for_command` method (Line 729)

- **Status:** False Positive
- **Confidence:** 100%
- **Analysis:** This method is used in the test suite (`tests/unit/test_comprehensive_pipeline.py`) to test model configuration functionality.
- **Recommendation:** Keep.
- **Recommendation:** Remove.

```python
def delete(self, ids, namespace=None, **kwargs):
    """Delete vectors by ID"""
    data = {"ids": ids}
    if namespace:
        data["namespace"] = namespace
    response = requests.post(
        f"{self.host}/vectors/delete", headers=self.headers, json=data
    )
    return response.json()
```
---

## `litassist/helpers/retriever.py`

### 1. `delete` method in `MockPineconeIndex` (Line 34)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** The `delete` method in the main `PineconeWrapper` is already marked as dead code. Correspondingly, its mock equivalent in `MockPineconeIndex` is also unused, as no part of the application logic calls `delete` on the retriever or the underlying index.
- **Recommendation:** Remove.

```python
def delete(self, *args, **kwargs):
    """Mock delete (no-op)."""
    pass
```

---

## `litassist/llm/client.py`

### 1. `get_model_for_command` method (Line 729)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This class method was likely intended for debugging or logging, but a project-wide search confirms it is never called.
- **Recommendation:** Remove.

```python
@classmethod
def get_model_for_command(cls, command_name: str, sub_type: str = None) -> str:
    """
    Get the model name configured for a specific command.
    ...
    """
    # ... function implementation
```

### 2. `list_configurations` method (Line 749)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Another helper method on the factory that is never used.
- **Recommendation:** Remove.

```python
@classmethod
def list_configurations(cls) -> Dict[str, Dict[str, Any]]:
    """
    List all available command configurations.
    ...
    """
    return cls.COMMAND_CONFIGS.copy()
```

### 3. `_client` attribute (Line 819)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This attribute is initialized to `None` in the `LLMClient`'s `__init__` method but is never assigned a value or used anywhere else. The API client is now managed within the `execute_api_call_with_retry` function in `api_handlers.py`.
- **Recommendation:** Remove the line `self._client = None`.

---

## `litassist/llm/response_parser.py`

### 1. `parse_chat_response` function (Line 110)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This function combines several other functions from the same module (`check_response_errors`, `extract_content_and_usage`, `clean_response_content`). However, the `LLMClient.complete` method now calls these underlying functions directly, making this composite function redundant.
- **Recommendation:** Remove.

```python
def parse_chat_response(response: Any) -> Tuple[str, Dict[str, Any], Optional[str]]:
    """
    Parse a complete chat completion response.
    ...
    """
    # ... function implementation
```

---

## `litassist/llm/retry_handler.py`

### 1. `should_retry_for_citations` function (Line 15)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This function was designed to check if an error warrants a citation-based retry. The calling logic in `LLMClient.complete` now performs this check inline (`except CitationVerificationError as e:`), making this standalone function obsolete.
- **Recommendation:** Remove.

```python
def should_retry_for_citations(error: Exception) -> bool:
    """
    Determine if an error warrants a retry with enhanced citation instructions.
    ...
    """
    from litassist.citation_verify import CitationVerificationError

    # Only retry for citation verification errors
    return isinstance(error, CitationVerificationError)
```

---

## `litassist/llm/tools.py`

### 1. `arguments` variable (Line 30)

- **Status:** Dead Code
- **Confidence:** 100%
- **Analysis:** The `arguments` parameter in the `execute_tool` function is defined but never used. The only tool, `now()`, takes no arguments.
- **Recommendation:** Remove the unused parameter from the function signature.
---

## `litassist/llm/verification.py`

**Conclusion:** The `LLMVerificationClient` class appears to be a deprecated or incomplete feature. It creates a circular dependency by importing `LLMClient` within its methods. The core verification logic is already mixed into the main `LLMClient`, making this standalone client redundant. The methods within it are therefore also unused.

### 1. `verified_citations` variable (Line 129)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Within the `validate_and_verify_citations` method, this variable is assigned but never read. The logic focuses on `unverified_citations`.
- **Recommendation:** Remove.

### 2. `verify_content` method in `LLMVerificationClient` (Line 414)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This method is part of the unused `LLMVerificationClient` wrapper class.
- **Recommendation:** Remove the entire `LLMVerificationClient` class.

### 3. `verify_citations` method in `LLMVerificationClient` (Line 430)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Unused method in the `LLMVerificationClient` class.
- **Recommendation:** Remove the entire `LLMVerificationClient` class.

### 4. `assess_verification_need` method in `LLMVerificationClient` (Line 445)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Unused method in the `LLMVerificationClient` class.
- **Recommendation:** Remove the entire `LLMVerificationClient` class.

### 5. `verify_with_depth` method in `LLMVerificationClient` (Line 458)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** Unused method in the `LLMVerificationClient` class.
- **Recommendation:** Remove the entire `LLMVerificationClient` class.

---

## `litassist/prompts.py`

**Conclusion:** This file contains several convenience functions and methods that have been superseded by direct use of the `PROMPTS` instance and its `get` method.

### 1. `get_document_template` method (Line 154)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This is a simple wrapper around `self.get(f"documents.{document_type}", **kwargs)`. A project-wide search shows it is never called.
- **Recommendation:** Remove.

```python
def get_document_template(self, document_type: str, **kwargs) -> str:
    """
    Get a legal document template.
    ...
    """
    return self.get(f"documents.{document_type}", **kwargs)
```

### 2. `compose_prompt` method (Line 167)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This helper for combining multiple templates is never used. Prompts are now constructed manually where needed.
- **Recommendation:** Remove.

```python
def compose_prompt(
    self, *template_keys: str, include_glob_help: bool = False
) -> str:
    """
    Compose multiple templates into a single prompt.
    ...
    """
    # ... function implementation
```

### 3. `list_templates` method (Line 196)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** A helper for debugging that is never used in the application code.
- **Recommendation:** Remove.

```python
def list_templates(self) -> Dict[str, Any]:
    """
    List all available templates.
    ...
    """
    self._ensure_loaded()
    return self.templates.copy() if self.templates else {}
```

### 4. `get_prompt` function (Line 212)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This is a backward-compatibility wrapper for `PROMPTS.get()`. It is no longer used.
- **Recommendation:** Remove.

```python
def get_prompt(key: str, **kwargs) -> str:
    """Get a prompt template by key."""
    return PROMPTS.get(key, **kwargs)
```
---

## `litassist/utils/formatting.py`

### 1. `WHITE` and `BOLD` constants (Lines 19, 21)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** These ANSI escape code constants are defined in the `Colors` class but are never used by any of the message formatting functions.
- **Recommendation:** Remove.

---

## `litassist/utils/legal_reasoning.py`

### 1. `to_markdown` method (Line 74)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** The `LegalReasoningTrace` class has two serialization methods: `to_markdown` and `to_structured_text`. Only `to_structured_text` is used (in `save_reasoning_trace`) to write the reasoning file. The markdown version is never called.
- **Recommendation:** Remove.

```python
def to_markdown(self) -> str:
    """Format reasoning trace as markdown."""
    # ... function implementation
```

---

## `litassist/commands/brainstorm/citation_regenerator.py`

### 1. `original_pos` variable (Line 164)

- **Status:** Dead Code
- **Confidence:** 60%
- **Analysis:** This variable is an artifact of a `for` loop iterating over `sorted(strategy_results.items())`. While the key of the dictionary item (the original position) is unpacked, only the value (`strategy`) is used in the loop body.
- **Recommendation:** Change `for i, (original_pos, strategy) in enumerate(...)` to `for i, strategy in enumerate(sorted(strategy_results.values()), 1)` to be more direct. Since this requires a logic change, I will simply mark the variable for removal and address the code simplification when acting on this report.

---

## `litassist/commands/brainstorm/research_handler.py`

### 1. `research_paths` parameter (Line 13)

- **Status:** Dead Code
- **Confidence:** 100%
- **Analysis:** The function `analyze_research_size` accepts `research_paths` as a parameter but never uses it. The reporting relies on `len(research_contents)`.
- **Recommendation:** Remove the unused parameter from the function signature and any calling locations.

---

## `litassist/commands/digest/chunker.py`

### 1. `overlap` parameter (Line 56)

- **Status:** Dead Code
- **Confidence:** 100%
- **Analysis:** The function `read_and_chunk_document` accepts an `overlap` parameter but does not use it. It calls `chunk_text`, but does not pass the overlap value to it.
- **Recommendation:** Remove the unused parameter.

---

## Final Unanalyzed Items from Report

The following items from the `vulture_report.txt` have not been analyzed in detail, but a brief review suggests they are also unused variables or function parameters.

- **`litassist/commands/digest/core.py:133`**: unused variable `chunk_count`
- **`litassist/commands/digest/emergency_handler.py:77`**: unused variables `frame`, `signum` (signal handler arguments)
- **`litassist/commands/digest/processors.py:15,82`**: unused variable `file_name`
- **`litassist/commands/extractfacts.py:267,269`**: unused variable `source_desc`

**Recommendation:** These are all minor, single-variable issues that can be safely removed.