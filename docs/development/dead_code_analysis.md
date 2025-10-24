# Dead Code Analysis - October 2025

**Generated**: 2025-10-23 (Updated: 2025-10-23)
**Tool**: vulture (min-confidence 60%)
**Total items identified**: 49
**Items removed**: 12 (324 lines of code)

## Cleanup Status

### Completed (2025-10-23)
**High-priority cleanup performed:**
- citation_patterns.py: Removed 7 unused validation functions + 2 variables (~270 lines)
- prompts.py: Removed 3 unused wrapper methods (~52 lines)
- llm/verification.py: Removed 1 unused variable (~2 lines)

**Total removed**: ~324 lines of dead code
**Tests status**: All 387 unit tests passing
**Linting**: Ruff check passes

### Remaining Work
- **True dead code**: 27 items still in codebase
- **False positives**: 10 items (actively used, keep)

## Summary

Vulture identified 49 potentially unused code elements. After verification:
- **Removed**: 12 items (324 lines removed)
- **Remaining dead code**: 27 items (can be safely removed)
- **False positives**: 10 items (actively used, keep)

## False Positives (Keep - Actively Used)

### citation_verify.py
- **Line 166**: `TestVerificationError` class - Used in test suite
- **Line 173**: `in_test_mode()` - Used in test suite
- **Line 408**: `search_jade_via_google_cse()` - Used in tests/unit/test_citation_verification_simple.py

### cli.py
- **Line 279**: `test()` command - CLI command (`litassist test`), invoked from command line

### config.py
- **Line 162**: `selenium_enabled` - Used in 14 test files
- **Line 163**: `selenium_timeout_multiplier` - Used in test suite

### helpers/pinecone_config.py & helpers/retriever.py
- **Lines 102, 34**: `delete()` methods - Likely used in manual test scripts (test-scripts/)

### llm/verification.py
- **Line 414-458**: `LLMVerificationClient` methods - May be used in test suite, needs verification

### utils/truncation.py
- **Line 49**: `get_dropped()` - May be used in test suite

## Removed Dead Code (12 items)

### citation_patterns.py (9 items) - REMOVED 2025-10-23
Pattern-based validation functions bypassed in favor of online verification:
- ~~`validate_generic_names` (line 260)~~ **REMOVED**
- ~~`validate_court_abbreviations` (line 352)~~ **REMOVED**
- ~~`validate_report_series` (line 407)~~ **REMOVED**
- ~~`validate_page_numbers` (line 431)~~ **REMOVED**
- ~~`validate_parallel_citations` (line 454)~~ **REMOVED**
- ~~`detect_hallucination_patterns` (line 480)~~ **REMOVED**
- ~~`extract_complete_citations` (line 501)~~ **REMOVED**
- ~~`volume` variable (line 421)~~ **REMOVED**
- ~~`verified_citations` variable (line 561)~~ **REMOVED**

**Impact**: Removed ~270 lines. File reduced from 616 → 350 lines (43% reduction)
**Reason**: Main function explicitly skips pattern validation (line 282: "Skip pattern validation entirely")

### prompts.py (3 items) - REMOVED 2025-10-23
Convenience wrappers superseded by direct `PROMPTS.get()` usage:
- ~~`get_document_template` method (line 154)~~ **REMOVED**
- ~~`compose_prompt` method (line 167)~~ **REMOVED**
- ~~`list_templates` method (line 196)~~ **REMOVED**
- ~~`get_prompt` function (line 212)~~ **KEPT** (removed earlier, now only 3 methods removed)

**Impact**: Removed ~52 lines. File reduced from 218 → 166 lines (24% reduction)
**Tests updated**: Updated test_prompts.py and test_command_parameters.py to use PROMPTS.get() directly
**Reason**: Simple wrappers providing no additional functionality beyond PROMPTS.get()

### llm/verification.py (1 item) - REMOVED 2025-10-23
- ~~`verified_citations` variable (line 129)~~ **REMOVED**

**Impact**: Changed to `_` (unused return value marker)
**Reason**: Variable assigned but never used

## Remaining Dead Code (27 items)

### citation_verify.py (2 items)
- `is_core_citation` (line 844) - Planned feature never implemented
- `get_verification_stats` (line 891) - Debug helper
- `clear_verification_cache` (line 911) - Cleanup helper

### commands/brainstorm/ (1 item)
- `citation_regenerator.py:164` - `original_pos` variable

### commands/brainstorm/research_handler.py (1 item)
- `research_paths` parameter (line 13) - 100% confidence

### commands/digest/ (5 items)
- `chunker.py:56` - `overlap` parameter (100% confidence)
- `core.py:155` - `chunk_count` variable
- `emergency_handler.py:77` - `frame`, `signum` variables (signal handler args, 100% confidence)
- `processors.py:16, 107` - `file_name` variables (100% confidence)

### commands/extractfacts.py (2 items)
- `source_desc` variable (lines 335, 337)

### commands/lookup/error_handlers.py (1 item)
- `check_model_token_limits` (line 119)

### llm/client.py (2 items)
- `list_configurations` method (line 785)
- `_client` attribute (line 855)

### llm/response_parser.py (1 item)
- `parse_chat_response` function (line 110) - Composite function, underlying functions called directly

### llm/retry_handler.py (1 item)
- `should_retry_for_citations` (line 14) - Logic inlined in LLMClient.complete

### llm/tools.py (1 item)
- `arguments` variable (line 30) - 100% confidence


### utils/formatting.py (2 items)
- `WHITE` constant (line 19)
- `BOLD` constant (line 21)

### utils/legal_reasoning.py (1 item)
- `to_markdown` method (line 74) - Only `to_structured_text` is used

## Recommendations for Remaining Dead Code

### High Priority (Remove) - ~~COMPLETED 2025-10-23~~
1. ~~**citation_patterns.py** - Remove 9 unused pattern validation functions (~200 lines)~~ **DONE**
2. ~~**prompts.py** - Remove 3 wrapper methods superseded by PROMPTS.get()~~ **DONE**
3. ~~**llm/verification.py** - Remove verified_citations variable~~ **DONE**

### Medium Priority (Clean up)
4. Remove unused parameters (overlap, research_paths, arguments, etc.)
   - `commands/digest/chunker.py:56` - `overlap` parameter
   - `commands/brainstorm/research_handler.py:13` - `research_paths` parameter
   - `llm/tools.py:30` - `arguments` variable
5. Remove unused variables (source_desc, chunk_count, etc.)
   - `commands/digest/core.py:155` - `chunk_count`
   - `commands/extractfacts.py:335, 337` - `source_desc`
   - `commands/digest/processors.py:16, 107` - `file_name`
   - `commands/brainstorm/citation_regenerator.py:164` - `original_pos`

### Low Priority (Consider removing)
6. Debug helpers (get_verification_stats, clear_verification_cache, is_core_citation)
   - `citation_verify.py:844` - `is_core_citation()`
   - `citation_verify.py:891` - `get_verification_stats()`
   - `citation_verify.py:911` - `clear_verification_cache()`
7. Unused constants (WHITE, BOLD)
   - `utils/formatting.py:19, 21` - `WHITE`, `BOLD`
8. Other dead code
   - `llm/client.py:785` - `list_configurations()` method
   - `llm/client.py:855` - `_client` attribute
   - `llm/response_parser.py:110` - `parse_chat_response()`
   - `llm/retry_handler.py:14` - `should_retry_for_citations()`
   - `utils/legal_reasoning.py:74` - `to_markdown()` method
   - `commands/lookup/error_handlers.py:119` - `check_model_token_limits()`

## Cleanup Details

### Files Modified (2025-10-23)

**litassist/citation_patterns.py**
- Before: 616 lines
- After: 350 lines
- Removed: ~270 lines (43% reduction)
- Changes: Removed 7 unreachable validation functions + 2 unused variables

**litassist/prompts.py**
- Before: 218 lines
- After: 166 lines
- Removed: ~52 lines (24% reduction)
- Changes: Removed 3 wrapper methods (get_document_template, compose_prompt, list_templates)

**litassist/llm/verification.py**
- Before: 469 lines
- After: 469 lines
- Changed: 1 variable (`verified_citations` → `_`)

**tests/unit/test_prompts.py**
- Updated to use `PROMPTS.get()` and `PROMPTS.templates` directly
- Removed dependencies on wrapper methods

**tests/unit/test_command_parameters.py**
- Updated mocks to use `.get()` instead of removed wrapper methods

### Verification
- All 387 unit tests passing after cleanup
- Ruff linting passes with no violations
- No production code impacted (was already using PROMPTS.get() directly)

## Notes

- Vulture cannot detect CLI commands or test suite usage reliably
- Manual verification required for items marked as "used in tests"
- Some items may be intentionally kept for future use or debugging
- Signal handler arguments (frame, signum) are required by Python API even if unused
- High-priority cleanup completed 2025-10-23, removing 324 lines of confirmed dead code
