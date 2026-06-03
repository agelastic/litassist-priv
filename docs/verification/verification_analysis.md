# LitAssist Verification Mechanisms Analysis

Last updated: 19/02/2026

## Overview

This document describes how verification works across LitAssist commands. There are two independent layers: citation enforcement at the LLM client level, and command-level verification logic.

## 1. Citation Enforcement (`enforce_citations`)

### What It Does

Controls whether citation verification failures in an LLM response trigger automatic retries with enhanced prompts. It does not control whether verification happens -- `LLMClient.complete()` always calls `process_citation_verification()`.

- `enforce_citations: true` -- strict mode: `CitationVerificationError` raised, triggers retry with reinforced citation prompt
- `enforce_citations: false` -- lenient mode: warnings logged, no retry

### Current Settings

Only **extractfacts** has `enforce_citations: true`. All other commands use `false`:

| Command | enforce_citations | Reason |
|---------|:-:|--------|
| extractfacts | true | Foundational document -- citations must be accurate |
| strategy | false | No retry on citation errors |
| brainstorm-orthodox | false | No retry on citation errors |
| brainstorm-unorthodox | false | No retry on citation errors |
| counselnotes | false | No retry on citation errors |
| lookup | false | Lenient citation checking |
| verify-reasoning | false | Avoids double-enforcement |
| verify-soundness | false | Avoids double-enforcement |
| digest | false | Default |
| draft | false | Default |
| barbrief | false | Default |
| caseplan | false | Default |
| All CoVe commands | false | Default |

Settings are in `litassist/llm/model_configs.yaml`.

## 2. Command-Level Verification

Each command implements its own verification logic on top of the base `LLMClient.complete()` call. The patterns vary significantly.

### Always-On Verification

**extractfacts**
- Calls `verify_content_if_needed()` with `verify_flag=True` by default
- Citation enforcement enabled (retries on citation failures)
- Override: `--noverify` disables content verification

**strategy**
- Calls `llm_client.validate_citations()` on generated strategy content
- Calls `verify_content_if_needed()` with `verify_flag=True` by default
- Override: `--noverify` disables content verification

**brainstorm**
- Most aggressive verification in the codebase
- Calls `verify_all_citations()` (from `litassist/citation/verify`) on combined output
- Calls `verify_client.verify()` for content soundness
- Multiple independent verification layers that cannot be fully disabled

**draft**
- Calls `verify_content_if_needed()` with `verify_flag=True` by default
- Calls `detect_factual_hallucinations()` -- always runs, checks for invented specifics
- Override: `--noverify` disables content verification (hallucination detection still runs)

### Conditional Verification

**counselnotes**
- Calls `client.validate_citations()` only when `--verify` flag is passed
- No verification by default

**barbrief**
- Always validates case facts format via `validate_case_facts()` (10-heading structure)
- Calls `verify_all_citations()` only when `--verify` flag is passed
- Format validation cannot be disabled; citation verification is opt-in

**digest**
- Calls `validate_citations_if_needed()` only in "issues" mode
- Uses lenient validation (`strict_mode=False`)
- No citation verification in other modes

### No Verification

**lookup**
- No command-level verification
- Relies only on base `LLMClient.complete()` behaviour (lenient)

**caseplan**
- No verification support
- Explicitly rejects `--verify` and `--noverify` flags with warnings

## 3. Verification Functions

| Function | Location | Purpose |
|----------|----------|---------|
| `process_citation_verification()` | `litassist/llm/citation_handler.py` | Base-level citation check in every LLM call |
| `determine_strict_mode()` | `litassist/llm/citation_handler.py` | Reads `enforce_citations` setting to pick strict/lenient |
| `verify_content_if_needed()` | `litassist/llm/verification.py` | Semantic content verification via LLM |
| `validate_citations()` | `LLMClient` method | Pattern-based citation validation |
| `validate_and_verify_citations()` | `LLMVerificationMixin` | Combined format + database checking |
| `verify_all_citations()` | `litassist/citation/verify.py` | Full citation verification against AustLII/Google CSE |
| `detect_factual_hallucinations()` | `litassist/commands/draft/` | Flags invented specifics in drafted documents |
| `validate_case_facts()` | `litassist/commands/barbrief/` | Validates 10-heading brief structure |

## 4. Key Observations

1. **Two-level system**: `LLMClient.complete()` always runs base citation checking. Commands add their own verification on top. The `enforce_citations` flag only controls whether the base level retries on failure.

2. **Brainstorm is special**: Has the most aggressive verification with multiple independent layers. Uses `verify_all_citations()` (the real citation database checker) rather than the LLMClient's pattern-based `validate_citations()`.

3. **Inconsistent patterns**: Commands range from aggressive multi-layer verification (brainstorm) to none at all (caseplan). The flag conventions also vary: some use `--verify` to opt in, others use `--noverify` to opt out, and some support neither.

4. **enforce_citations is narrowly scoped**: Despite the name, it only controls retry behaviour on citation format errors during LLM completion. Most citation verification happens at the command level through separate function calls.
