# LitAssist Unit Test Suite

Last updated: 08/06/2026

## Overview

The unit suite in `tests/unit/` exercises LitAssist's critical paths. As of the
date above it is **458 tests across 59 files**. Per the project testing policy,
every test runs **offline with mocked dependencies** - no real API calls. The
"integration" tests are still offline, mocked interactions. Real-API checks live in
`test-scripts/` and are run manually (they incur cost).

This document describes how the suite is organised by area. It intentionally does
NOT enumerate per-file test counts: those go stale on every change. For an exact
current count run `pytest tests/unit --collect-only -q`.

## Running

```bash
# Full unit suite
pytest tests/unit -q

# A single area / file
pytest tests/unit/test_model_parameters.py -q

# Slowest tests (find outliers)
pytest tests/unit --durations=10

# Coverage
pytest tests/unit --cov=litassist
```

## Coverage areas

### Commands (CLI end-to-end, mocked LLM)
`test_barbrief`, `test_brainstorm_internals`, `test_brainstorm_verification`,
`test_caseplan`, `test_caseplan_command_extractor`, `test_counselnotes_basic`,
`test_digest_command`, `test_draft_command_comprehensive`, `test_extractfacts_command`,
`test_refresh_command`, `test_strategy_command_comprehensive`, `test_updatefacts_command`,
`test_verify_command`, `test_verify_cove_command`, `test_cli_command`,
`test_cli_command_loading`.
These drive the Click commands via `CliRunner` and assert exit codes, output, and
call wiring with all external services mocked.

### LLM and model layer
`test_llm_client_factory`, `test_llm_complete`, `test_llm_retry_logic`,
`test_llm_integration_comprehensive`,
`test_model_parameters`, `test_model_config_integrity`, `test_model_config_sampling`,
`test_thinking_effort`, `test_provider_prefix`, `test_heavy_flag`. Per-model-family
parameter mapping (Claude / Gemini / OpenAI reasoning / Grok), retry/backoff on
transient errors, and command-to-model configuration.

### Lookup and content fetching
`test_lookup_command`, `test_lookup_context_split`, `test_lookup_gibberish_heuristic`,
`test_lookup_jina_challenge_detection`, `test_lookup_austlii_pdf_substitution`,
`test_lookup_rtf_extraction`, `test_lookup_processor_fetch_messages`,
`test_fetcher_review_fixes`. Google CSE search handling, fetch/OCR fallbacks,
Cloudflare-challenge detection, and document extraction.

### Citation and verification
`test_citation_trust`, `test_citation_verification_simple`,
`test_citation_context_failure_reason`, `test_verification`, `test_cove_regeneration`,
`test_format_cove_report_none_handling`, `test_noverify_flag`. Citation
trust/verification, auto-verify risk detection, and the Chain-of-Verification path.

### Case facts
`test_case_facts_validator`, `test_case_facts_autoselect`. The 10-heading
case-facts format validator and latest-file auto-selection.

### Prompts (YAML)
`test_prompts`, `test_prompt_templates`, `test_prompt_validation`,
`test_yaml_prompt_validation`. YAML parses, required keys exist, no empty values,
and the no-emoji policy across the prompt corpus.

### Logging, output and utilities
`test_logging_config`, `test_log_filename_collision`, `test_fetch_audit_log_fidelity`,
`test_output_saver`, `test_utils_comprehensive`, `test_utils_additional`,
`test_real_functionality`, `test_derived_size_caps`. Log-directory resolution and
filename collisions, output saving (`LITASSIST_OUTPUT_DIR` isolation), and core
text/chunking utilities.

### Config and file selection
`test_config_validation`, `test_glob_single`, `test_glob_newest_each`.
Configuration precedence/validation and glob-callback file selection.

## Conventions

- Shared fixtures and the global config mock live in `tests/conftest.py`; an autouse
  fixture redirects `LITASSIST_LOG_DIR` to a per-test temp dir so the suite never
  writes audit logs into the repo's `logs/`.
- Keep tests behavioural. Avoid framework-only assertions (mocking the function
  under test), tautologies, and duplicate coverage of the same path across files.
- ASCII only - no emoji anywhere in the repo, including this file.
