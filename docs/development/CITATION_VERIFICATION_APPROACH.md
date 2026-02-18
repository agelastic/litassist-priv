# Citation Verification System

## Problem

AI models hallucinate legal citations. LitAssist implements a two-phase verification system to detect and handle fictitious citations across all commands.

## Two-Phase Architecture

### Phase 1: Pattern Validation (Offline)

**Module**: `litassist/citation_patterns.py`

`validate_citation_patterns(content, enable_online=True)` detects problematic citation patterns without network access:

- Generic case names (Smith v Jones, Brown v Wilson)
- Future dates and anachronistic references
- Non-existent courts and impossible citation numbers
- Placeholder names, single-letter parties
- Malformed parallel citations and unrealistic page numbers
- Court establishment date validation (e.g., FCA did not exist before 1977)
- Report series validation (CLR, ALR, FCR, etc.)

### Phase 2: Database Verification (Online)

**Package**: `litassist/citation/`

Modules: `verify.py`, `cache.py`, `google_cse.py`, `austlii.py`, `legislation.py`, `constants.py`, `exceptions.py`

`verify_all_citations(text)` returns `Tuple[List[Dict[str, str]], List[Tuple[str, str]]]` -- verified citation details and unverified citations with reasons. Makes HEAD requests to AustLII to confirm case existence. Results are cached with thread-safe locking.

Supporting functions:
- `verify_single_citation(citation)` -- single citation check
- `remove_citation_from_text(text, citation)` -- surgically removes bad citations
- `is_core_citation(text_section, citation)` -- distinguishes core from supporting citations

Court coverage: HCA, FCA, FCAFC, FamCA, all state supreme and appeal courts, specialist tribunals (VCAT, QCAT, SACAT, etc.). International citations (UK, US, NZ) accepted as valid but not checkable.

## LLM Client Integration

**Module**: `litassist/llm/verification.py` (via `LLMVerificationMixin`)

`validate_and_verify_citations(content, strict_mode=True)` provides automatic verification within the LLM client. When `enforce_citations` is true for a command (currently only `extractfacts`), failed citations trigger automatic retry with enhanced prompts instructing the model to use only verifiable citations.

**Module**: `litassist/llm/citation_handler.py`

`process_citation_verification(content, client_instance, skip_verification=False)` handles citation verification during `client.complete()` calls. Controlled by the `enforce_citations` flag in model config.

## Command Integration Patterns

Commands handle citation issues in two ways:

### Warning Approach (most commands)

Citation warnings are prepended or appended to output. Content is preserved and the user decides what to do about flagged citations.

| Command | Warning Placement |
|---------|------------------|
| lookup | Prepended to output |
| strategy | Prepended to output |
| draft | Appended to output |
| extractfacts | Appended to output |
| digest | Prepended per chunk |
| counselnotes | Displayed to CLI only (extraction mode) or prepended (analysis mode) |

### Selective Regeneration (brainstorm only)

`regenerate_bad_strategies()` in `litassist/commands/brainstorm/citation_regenerator.py` individually regenerates strategies that have citation issues. Strategies that pass validation are kept unchanged. Strategies that cannot be fixed after 2 retries are excluded entirely. Remaining strategies are renumbered.

## Verification Deduplication

**Function**: `verify_content_if_needed()` in `litassist/utils/legal_reasoning.py`

Commands with explicit `--verify` flags (e.g., `barbrief`) perform citation verification via Google CSE. The `citation_already_verified` parameter prevents redundant LLM-based citation validation when Google CSE has already verified the citations.

## File Structure

```
litassist/
  citation_patterns.py        # Phase 1: offline pattern validation
  citation_context.py          # Citation content fetching for CoVe
  citation/
    verify.py                  # Phase 2: orchestration and core functions
    cache.py                   # Thread-safe citation cache
    google_cse.py              # Google CSE verification strategy
    austlii.py                 # AustLII URL construction and verification
    legislation.py             # Legislation reference handling
    constants.py               # Court mappings, establishment dates
    exceptions.py              # CitationVerificationError
  llm/
    verification.py            # LLMVerificationMixin (validate_and_verify_citations)
    citation_handler.py        # process_citation_verification
  commands/
    lookup/                    # Warning approach
    brainstorm/                # Selective regeneration (citation_regenerator.py)
    strategy/                  # Warning approach
    draft/                     # Warning approach
    extractfacts/              # Warning approach (enforce_citations: true)
    digest/                    # Warning approach (per-chunk)
    counselnotes/              # Warning approach
    barbrief/                  # Warning approach + Google CSE deduplication
```

## Testing

Test suite in `tests/unit/test_citation_verification_simple.py`:
- Citation extraction and pattern matching
- Single and batch verification
- Citation removal and core citation detection
- Cache and statistics validation
