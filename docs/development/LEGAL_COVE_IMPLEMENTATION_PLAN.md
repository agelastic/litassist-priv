# Legal Chain of Verification (CoVe) Implementation Plan

**UPDATED: 2025-08-21 - Revised to follow CLAUDE.md principles and actual codebase reality**

## Executive Summary

Implementing Chain of Verification (CoVe) for legal documents to address the critical hallucination problem in legal AI, where research shows 69-88% hallucination rates in legal queries. This plan has been completely revised to:
1. Follow CLAUDE.md minimal changes principle
2. Build on actual codebase (not planned architectures that don't exist)
3. Create minimal chain first (130 lines total)
4. Avoid overengineering and unnecessary abstractions

## Background: The Legal Hallucination Crisis

Research from Stanford HAI and Oxford Journal of Legal Analysis reveals:
- Legal hallucinations occur in **69-88% of legal queries** to state-of-the-art LLMs
- In common law systems, *stare decisis* requires absolute fidelity to historical case law
- Any misstatement of binding law makes an LLM lose professional utility
- Legal sanctions and professional liability make accuracy paramount

## What is Chain of Verification (CoVe)?

Based on Meta AI research (arXiv:2309.11495), CoVe is a four-step self-verification process:

1. **Generate baseline response** - Initial LLM output
2. **Plan verification questions** - Generate questions to fact-check the response
3. **Execute verifications independently** - Answer questions without bias from original
4. **Generate final verified response** - Incorporate verification results

The "factored" approach (preventing the model from attending to prior answers) reduces repeated hallucinations.

## Current Codebase Reality (Verified)

After examining the actual code (not documentation), here's what exists:

### What EXISTS:
- `citation_patterns.py`: `validate_citation_patterns()` → List[str] of issues
- `citation_verify.py`: `verify_all_citations()` → (verified, unverified) tuples
- `llm.py`: `client.verify()` with context passing (our recent work)
- `utils.py`: `verify_content_if_needed()` for command-level verification
- Automatic citation verification in `LLMClient.complete()`

### What DOESN'T EXIST:
- ❌ No `litassist/verification/` directory
- ❌ No VerificationChain class
- ❌ No stages.py or config with stages
- ❌ No pipeline infrastructure

**Critical Finding**: The Chain of Verification Architecture document describes a system that was never built.

## Revised Implementation (Following CLAUDE.md Principles)

### PHASE 1: Minimal Chain First (80 lines)

**Single file: `litassist/verification_chain.py`**

```python
"""Minimal verification chain orchestrator - no overengineering."""

from typing import Dict, Optional, Tuple
from litassist.citation_patterns import validate_citation_patterns
from litassist.citation_verify import verify_all_citations
from litassist.llm import LLMClientFactory


def run_verification_chain(
    content: str, 
    command: str,
    skip_stages: Optional[set] = None
) -> Tuple[str, Dict]:
    """
    Minimal chain that orchestrates existing verification functions.
    Returns (content, verification_results).
    """
    skip_stages = skip_stages or set()
    results = {}
    
    # Stage 1: Pattern validation (offline, fast)
    if 'patterns' not in skip_stages:
        pattern_issues = validate_citation_patterns(content, enable_online=False)
        results['patterns'] = {
            'issues': pattern_issues,
            'passed': len(pattern_issues) == 0
        }
        
        # Early exit for high-risk commands
        if pattern_issues and command in ['extractfacts', 'strategy', 'draft']:
            return content, results
    
    # Stage 2: Database verification (online, authoritative)
    if 'database' not in skip_stages and results.get('patterns', {}).get('passed', True):
        verified, unverified = verify_all_citations(content)
        results['database'] = {
            'verified': verified,
            'unverified': unverified,
            'passed': len(unverified) == 0
        }
        
        # Early exit for strict commands
        if unverified and command in ['extractfacts', 'strategy']:
            return content, results
    
    # Stage 3: LLM verification (expensive, comprehensive)
    if 'llm' not in skip_stages and command in ['extractfacts', 'strategy', 'draft']:
        client = LLMClientFactory.for_command('verify')
        citation_report = _format_simple_report(results.get('database', {}))
        corrected_content, _ = client.verify(
            content,
            citation_context=citation_report if citation_report else None
        )
        
        if isinstance(corrected_content, tuple):
            corrected_content = corrected_content[0]
            
        results['llm'] = {
            'corrections_made': corrected_content != content,
            'passed': True
        }
        
        if corrected_content != content:
            content = corrected_content
    
    return content, results


def _format_simple_report(database_results: Dict) -> Optional[str]:
    """Format database results for context - no parsing, just text."""
    if not database_results:
        return None
        
    verified = database_results.get('verified', [])
    unverified = database_results.get('unverified', [])
    
    if not verified and not unverified:
        return None
        
    report = f"Verified: {len(verified)}\n"
    if unverified:
        report += f"Unverified: {', '.join([u[0] for u in unverified])}"
    
    return report
```

### Integration with Existing Code (10 lines)

In `litassist/utils.py`, modify `verify_content_if_needed()` at line ~1150:

```python
# Add before: if needs_verification:
if command_name in ['extractfacts', 'strategy', 'draft']:
    from litassist.verification_chain import run_verification_chain
    verified_content, results = run_verification_chain(content, command_name)
    if results.get('llm', {}).get('corrections_made'):
        return verified_content, True
    # Fall through to existing verification if chain didn't handle it
```

### PHASE 2: CoVe Implementation (50 additional lines)

Add to the same `litassist/verification_chain.py` file:

```python
def run_cove_verification(content: str, command: str) -> Tuple[str, Dict]:
    """
    Chain of Verification - asks LLM to generate and answer questions.
    No local parsing - trust the LLM.
    """
    client = LLMClientFactory.for_command('verify')
    
    # Step 1: Generate questions (let LLM do the work)
    questions_prompt = f"""
    Generate 5-10 verification questions for this legal document.
    Focus on citations, dates, party names, and legal principles.
    
    Document:
    {content[:3000]}  # Limit for question generation
    
    Output numbered questions only.
    """
    
    questions, _ = client.complete([{"role": "user", "content": questions_prompt}])
    
    # Step 2: Answer questions independently (factored approach)
    answers_prompt = f"""
    Answer these questions based ONLY on legal knowledge, NOT the document:
    
    {questions}
    
    For each question, answer: Yes/No/Uncertain with brief explanation.
    """
    
    answers, _ = client.complete([{"role": "user", "content": answers_prompt}])
    
    # Step 3: Detect inconsistencies (let LLM compare)
    verify_prompt = f"""
    Compare these Q&A pairs against the original document.
    Identify any inconsistencies or errors.
    
    Questions and Answers:
    {answers}
    
    Original Document:
    {content}
    
    Output: List issues found, or "No issues found"
    """
    
    issues, _ = client.complete([{"role": "user", "content": verify_prompt}])
    
    return content, {
        'cove': {
            'questions': questions,
            'answers': answers,
            'issues': issues,
            'passed': 'No issues found' in issues
        }
    }
```

### Integration of CoVe with Chain

Modify `run_verification_chain()` to add CoVe as Stage 4:

```python
# Add after Stage 3 (LLM verification), before final return
if 'cove' not in skip_stages and command in ['extractfacts', 'strategy']:
    content, cove_results = run_cove_verification(content, command)
    results.update(cove_results)
```

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

## Revised Implementation Timeline

### Phase 1: Minimal Chain (2 hours)
- [ ] Create `litassist/verification_chain.py` (80 lines)
- [ ] Add integration to `utils.py` (10 lines)
- [ ] Test with extractfacts command
- [ ] No classes, no abstractions, just functions

### Phase 2: CoVe Addition (1 hour)
- [ ] Add `run_cove_verification()` to same file (50 lines)
- [ ] Integrate as Stage 4 in chain
- [ ] Test factored approach
- [ ] Let LLM do all parsing - no regex

## Why This Approach Is Better

1. **Follows CLAUDE.md Principles**:
   - Minimal changes (130 lines total)
   - No classes when functions work
   - No local parsing - trust the LLM
   - No premature abstractions

2. **Based on Actual Code**:
   - Uses existing `validate_citation_patterns()`
   - Uses existing `verify_all_citations()`
   - Uses existing `client.verify()` with context
   - Doesn't assume non-existent infrastructure

3. **Safe and Incremental**:
   - Chain works without CoVe
   - CoVe builds on chain
   - Each phase is independently useful
   - No breaking changes

## What Was Removed from Original Plan

The following were removed as violations of CLAUDE.md principles:

1. **Class hierarchies** (850 lines across 7 files):
   - `LegalCoVe`, `QuestionRouter`, `FactoredCoVe`, `LegalQuestionTemplates` classes
   - Replaced with: 2 simple functions (130 lines total)

2. **Local parsing and regex** - Let LLM extract questions instead

3. **Question routing/classification** - Trust LLM to answer appropriately

4. **Configuration files with stages** - Infrastructure that doesn't exist

5. **Template abstractions** - Premature optimization

All 850+ lines of overengineered code have been replaced with 130 lines of simple functions.

## Final Implementation Summary

| Component | Lines | Files | Time |
|-----------|-------|-------|------|
| Minimal Chain | 80 | 1 new | 2 hrs |
| CoVe Addition | 50 | 0 new | 1 hr |
| Integration | 10 | 1 mod | 10 min |
| **Total** | **140** | **1 new file** | **3 hrs** |

## Success Criteria

- [ ] Hallucination rate reduced to <10% for citations
- [ ] All High Court cases correctly verified
- [ ] Statutory references validated against current law
- [ ] Legal principles accurately attributed
- [ ] Full audit trail for every verification

## Expected Outcomes

### Metrics
- **Baseline**: 69-88% hallucination rate (research data)
- **Standard CoVe**: ~30-40% reduction (Meta's results)
- **Legal CoVe Target**: <10% hallucination rate through minimal implementation

### Quality Improvements
1. **Every citation verified** against legal databases
2. **Every statute checked** for current validity
3. **Every principle validated** through factored verification
4. **Every fact cross-referenced** for consistency
5. **Full audit trail** for professional liability

## Risk Mitigation

1. **Performance**: Limit CoVe questions to 5-10 per document
2. **Cost**: Only run CoVe for high-risk commands
3. **Accuracy**: Use factored approach to prevent bias
4. **Reliability**: Chain continues even if one stage fails

## References

- Meta AI CoVe Paper: arXiv:2309.11495 (Dhuliawala et al., 2023)
- Legal Hallucinations Study: Oxford Journal of Legal Analysis (2024)
- Stanford HAI Report: "Hallucinating Law" (2023)
- Implementation Examples: github.com/ritun16/chain-of-verification

---

*Last Updated: 2025-08-21*
*Status: Ready for Implementation*
*Priority: HIGH - Addresses critical legal accuracy requirements*