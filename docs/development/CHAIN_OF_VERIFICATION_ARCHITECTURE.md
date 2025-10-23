# Chain of Verification (CoVe) Architecture for LitAssist

**Status**: IMPLEMENTATION COMPLETE (2025-08-23)
**Last Verified**: October 2025
**Production Status**: Ready for testing

## Executive Summary

LitAssist implements Chain of Verification (CoVe) based on Meta AI research (arXiv:2309.11495) to address the critical legal hallucination problem where 69-88% of legal queries to LLMs contain factual errors. The implementation is complete, verified, and operational.

## The Legal Hallucination Crisis

Research from Stanford HAI and Oxford Journal of Legal Analysis reveals:
- Legal hallucinations occur in **69-88% of legal queries** to state-of-the-art LLMs
- In common law systems, *stare decisis* requires absolute fidelity to historical case law
- Any misstatement of binding law makes an LLM lose professional utility
- Legal sanctions and professional liability make accuracy paramount

## CoVe Four-Stage Process

Based on Meta AI research, CoVe implements a factored self-verification process:

1. **Generate baseline response** - Initial LLM output
2. **Plan verification questions** - Generate questions to fact-check the response
3. **Execute verifications independently** - Answer questions without bias from original (factored approach)
4. **Generate final verified response** - Incorporate verification results and regenerate if needed

The "factored" approach prevents the model from attending to prior answers, reducing repeated hallucinations.

## Current Implementation Architecture

### Core Components

**File**: `litassist/verification_chain.py` (556 lines)

#### 1. Standard Verification Chain

**Function**: `run_verification_chain(content, command, skip_stages)` (lines 14-70)

Three-stage verification process:
1. **Pattern Validation** (offline, fast) - Uses `citation_patterns.py`
2. **Database Verification** (online, authoritative) - Uses `citation_verify.py`
3. **LLM Verification** (expensive, comprehensive) - Uses `LLMClientFactory.for_command('verification')`

Returns: `(content, verification_results)` tuple

**Early Exit Logic**: High-risk commands (extractfacts, strategy, draft) exit early if pattern issues found.

#### 2. Chain of Verification (CoVe)

**Function**: `run_cove_verification(content, command, prior_contexts)` (lines 88-531)

Four-stage CoVe process:
1. **Generate Questions** (lines 140-183)
   - Uses `LLMClientFactory.for_command('cove-questions')`
   - Generates 5-10 verification questions focused on citations, dates, parties, legal principles
   - Extracts citations from questions (lines 185-260)
   - Fetches full legal documents for cited cases automatically

2. **Answer Questions** (lines 261-386)
   - Uses `LLMClientFactory.for_command('cove-answers')`
   - Factored approach: Answers based on legal knowledge + full cited documents
   - Scalable context inclusion: Drop-largest backoff on token errors (lines 278-360)
   - Supports reference files via `prior_contexts['cove_reference_files']`

3. **Detect Inconsistencies** (lines 388-429)
   - Uses `LLMClientFactory.for_command('cove-verify')`
   - Compares independent answers against original document
   - Returns issues found or "no issues found"

4. **Regenerate if Needed** (lines 431-490)
   - Uses `LLMClientFactory.for_command('cove-final')`
   - Only runs if inconsistencies detected
   - Incorporates verification findings into corrected document

Returns: `(final_content, cove_results)` tuple

#### 3. Report Formatting

**Function**: `format_cove_report(cove_results)` (lines 534-556)

Generates readable markdown report with:
- Verification status (PASSED/ISSUES FOUND)
- Questions generated
- Independent answers
- Verification results

### Command Integration

#### Primary: Standalone Command

**Command**: `litassist verify-cove`
**File**: `litassist/commands/verify_cove.py` (311 lines)
**Usage**: `litassist verify-cove document.txt [--reference "exhibits/*.pdf"]`

Features:
- Runs full CoVe pipeline on any document
- Supports `--reference` flag for additional context documents
- Saves CoVe report with full dialogue
- Saves regenerated document if issues found
- Comprehensive error handling and logging

**This is the primary way to use CoVe.**

#### Secondary: Optional `--cove` Flag

**Only two commands** have an optional `--cove` flag:

1. **`verify` command** - Adds CoVe as final verification step
   - Usage: `litassist verify document.txt --cove`
   - Also supports `--cove-reference` for reference documents

2. **`strategy` command** - Shows `--cove` in help text only
   - **WARNING**: Help text is outdated/misleading
   - `strategy` function signature has NO `cove` parameter (line 56)
   - Comment at line 384 says: "CoVe moved to standalone 'verify-cove' command"
   - The `--cove` flag does NOT actually exist in strategy command

#### No CoVe Integration in Other Commands

These commands do NOT have `--cove` flags:
- `extractfacts` - Uses standard verification only
- `draft` - No CoVe integration
- `barbrief` - No CoVe integration
- `counselnotes` - No CoVe integration

### Architecture Principles

Following CLAUDE.md guidelines:

1. **No Overengineering**: Simple functions instead of class hierarchies
2. **Minimal Abstraction**: Direct function calls, no pipeline infrastructure
3. **Trust the LLM**: No local parsing or regex for question extraction
4. **Comprehensive Logging**: Full audit trail for legal accountability
5. **Australian Legal Focus**: Designed for Australian legal proceedings

## Verification Flow Examples

### Standard Commands (extractfacts, strategy, draft, etc.)
```
Pattern Validation → Database Verification → LLM Self-Critique
```
**Note**: CoVe is NOT integrated into these commands. Use `verify-cove` separately.

### Verify Command with --cove Flag
```
Citations → Soundness → Reasoning → CoVe (if --cove flag passed)
```

### Standalone verify-cove Command
```
CoVe Questions → Fetch Citations → Answer with Context → Detect Issues → Regenerate
```
**This is the recommended way to use CoVe.**

## Implementation Details

### Citation Context Fetching

Lines 185-260 in `verification_chain.py`:
- Automatically extracts citations from generated questions
- Fetches full legal documents using `fetch_citation_context()`
- Includes full case text in answer stage for accurate verification
- Logs all citation extraction and fetching for audit trail

### Token Limit Handling

Lines 278-360 in `verification_chain.py`:
- Intelligent retry loop with drop-largest backoff
- Detects token/context limit errors
- Drops largest legal document and retries
- Logs each document drop for transparency
- Up to 5 retry attempts before failure

### Logging Infrastructure

Comprehensive logging at every stage:
- `log_task_event()` for stage start/end
- Full prompts stored for legal accountability
- Response lengths and token usage tracked
- Detailed metadata for debugging
- Separate logs for questions, answers, verification, regeneration

### Model Configuration

Uses LLMClientFactory pattern:
- `cove-questions` - Question generation client
- `cove-answers` - Independent answer client
- `cove-verify` - Inconsistency detection client
- `cove-final` - Final regeneration client (optional)

Allows different models for different CoVe stages.

## Code Quality

### Compliance with CLAUDE.md

- [Y] No emojis - ASCII output only (`[SUCCESS]`, `[VERIFYING]`)
- [Y] Minimal changes - Simple functions, no overengineering
- [Y] No hardcoded prompts - All via `PROMPTS.get()`
- [Y] Document separation - Standard `=== NAME ===` markers
- [Y] Full logging - Complete request/response audit trail
- [Y] Australian legal focus - Designed for Australian proceedings

### Implementation Quality

**Strengths**:
1. Comprehensive logging at every stage
2. Legal accountability through full audit trail
3. Scalable design with intelligent backoff
4. Error handling with specific exception types
5. Citation context fetching for accurate verification
6. Reference file support for additional context

**Notable Features**:
1. Three separate LLM clients for factored verification
2. Optional fourth client for regeneration only when needed
3. Proper context separation with `=== NAME ===` markers
4. Token limit retry logic with drop-largest strategy
5. Safe string handling prevents None crashes

## Testing Status

### Unit Tests
- [Y] All tests passing as of 2025-08-23
- [Y] Mocked LLM responses for offline testing
- [Y] Coverage of all core functions

### Production Testing (PENDING)
- [ ] Hallucination rate measurement
- [ ] High Court case validation
- [ ] Statutory reference validation
- [ ] Legal principle attribution assessment

## Implementation Statistics

| Component | Lines | Files | Status |
|-----------|-------|-------|--------|
| Verification Chain | 556 | 1 new | COMPLETE |
| CoVe Functions | (included above) | - | COMPLETE |
| Standalone Command | 311 | 1 new | COMPLETE |
| verify command --cove flag | ~30 | 1 modified | COMPLETE |
| **Total** | ~897 | 2 new, 1 modified | **COMPLETE** |

**Note**: Original plan estimated 251 lines. Actual implementation is larger due to:
- Citation fetching infrastructure
- Scalable context inclusion with backoff
- Enhanced logging and error handling
- Reference document support
- Full standalone command implementation

**Command Integration Reality**:
- Only `verify` command has working `--cove` flag
- `strategy` command has outdated help text mentioning CoVe but no actual flag
- All other commands (extractfacts, draft, barbrief, counselnotes) have NO CoVe integration
- **Primary usage**: Standalone `verify-cove` command for all CoVe needs

## Example Verification Questions

### Citation Verification
- "Is 'Donoghue v Stevenson [1932] AC 562' correctly cited?"
- "Was Mabo v Queensland (No 2) decided in 1992 by the High Court?"
- "Does Carlill v Carbolic Smoke Ball Company establish unilateral contracts?"

### Statutory Verification
- "Is section 18 of the Australian Consumer Law about misleading conduct?"
- "Has the Trade Practices Act 1974 been replaced by Competition and Consumer Act 2010?"
- "Is section 52 still in force or has it been repealed?"

### Principle Verification
- "Is the 'neighbor principle' correctly attributed to Lord Atkin?"
- "Does the 'reasonable person test' apply in negligence cases?"
- "Is strict liability applicable to the facts described?"

### Consistency Verification
- "Is the accident date consistently stated as March 15, 2023?"
- "Is the plaintiff's name spelled 'Smith' throughout?"
- "Do the claimed damages align with the injury description?"

## Expected Outcomes

### Metrics
- **Baseline**: 69-88% hallucination rate (research data)
- **Standard CoVe**: ~30-40% reduction (Meta's results)
- **Legal CoVe Target**: <10% hallucination rate

### Quality Improvements
1. Every citation verified against legal databases
2. Every statute checked for current validity
3. Every principle validated through factored verification
4. Every fact cross-referenced for consistency
5. Full audit trail for professional liability

## Usage Examples

### Standalone CoVe Command
```bash
# Basic CoVe verification
litassist verify-cove witness_statement.txt

# With reference documents
litassist verify-cove affidavit.txt --reference "exhibits/*.pdf"

# Custom output prefix
litassist verify-cove document.txt --output final_review
```

### Verify Command with CoVe
```bash
# Add CoVe as final verification step
litassist verify document.txt --cove

# With reference documents for CoVe
litassist verify document.txt --cove --cove-reference "exhibits/*.pdf"
```

### Post-Processing with verify-cove
```bash
# Run CoVe on any command output
litassist strategy case_facts.txt --outcome "summary judgment"
litassist verify-cove outputs/strategy_*.md

# Or on draft documents
litassist draft bundle.pdf "motion to dismiss"
litassist verify-cove outputs/draft_*.md --reference "exhibits/*.pdf"
```

## Risk Mitigation

1. **Performance**: Limit CoVe questions to 5-10 per document
2. **Cost**: CoVe only for high-risk commands or when explicitly requested
3. **Accuracy**: Factored approach prevents confirmation bias
4. **Reliability**: Chain continues even if one stage fails
5. **Token Limits**: Drop-largest backoff handles context overflow

## Future Enhancements (Optional)

1. **Performance Optimization**: Consider caching CoVe results for repeated documents
2. **Question Template Refinement**: Develop specialized templates for document types
3. **Configurable CoVe Depth**: Allow users to specify number of verification questions
4. **CoVe Report Export**: Add option to save detailed analysis separately
5. **Multi-Model Consensus**: Use multiple models for critical verifications

## References

- Meta AI CoVe Paper: arXiv:2309.11495 (Dhuliawala et al., 2023)
- Legal Hallucinations Study: Oxford Journal of Legal Analysis (2024)
- Stanford HAI Report: "Hallucinating Law" (2023)
- Implementation Examples: github.com/ritun16/chain-of-verification

## Related Documentation

- Implementation code: `litassist/verification_chain.py`
- Standalone command: `litassist/commands/verify_cove.py`
- User guide: `docs/user/LitAssist_User_Guide.md`
- Testing: `tests/unit/test_verification.py`

---

**Last Updated**: October 2025
**Status**: IMPLEMENTATION COMPLETE - Production testing pending
**Priority**: HIGH - Addresses critical legal accuracy requirements
