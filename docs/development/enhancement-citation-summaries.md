# Enhancement Plan: Citation Summaries for Verified Citations

**Date:** 2025-11-16
**Status:** Planning Phase — Not Implemented
**Last Verified:** February 2026
**Goal:** Add 2-3 sentence case summaries to verified citations for better strategy selection

## Executive Summary

This enhancement adds contextual case summaries to verified citations throughout the brainstorm pipeline, improving plausibility assessment quality and enabling better strategy selection in the analysis phase.

**Key Benefits:**
- More accurate plausibility risk assessments (grounded in verified case law vs guesswork)
- Better strategy selection based on strength of verified legal precedent
- Actionable citation alternatives for users when citations fail verification
- Minimal cost (+$0.04-$0.05 per brainstorm)

**Implementation:** Phase 2 (full document summaries) with Google CSE snippet fallback

## User Requirements

1. **Primary goal:** Better strategy selection in analysis phase
2. **Cost tolerance:** Additional costs acceptable
3. **Scope:** All verified citations
4. **Visibility:** Summaries in both final output annotations (user-facing) and analysis prompt
5. **Approach:** Jump to Phase 2 (full summaries) with snippet fallback

## Current State Analysis

### Citation Verification Flow

**Location:** [litassist/citation/verify.py:146-210](../litassist/citation/verify.py)

**Process:**
1. Extract citations from strategy text
2. Search Google CSE (Jade.io, then comprehensive, then AustLII)
3. Google CSE returns: `{title, snippet, link}` for each result
4. Only snippet used for matching verification
5. **Critical issue:** Snippets are discarded after verification

**Current cache structure:**
```python
{
    "exists": True/False,
    "url": "https://jade.io/article/12345",
    "reason": "Found via Google CSE" or "Citation not found"
}
```

**What is lost:**
- Google CSE snippets (150-200 char case previews)
- Case titles
- Any contextual information about the case

### Plausibility Checking Flow

**Location:** [litassist/commands/brainstorm/core.py:118-218](../litassist/commands/brainstorm/core.py)

**Current input to plausibility checker:**
```
ORTHODOX_3:
[Strategy preview: 500 chars]

Unverified Citations:
  - [1999] NSWCA 856 (Reason: Citation not found in online databases)
```

**What plausibility checker does NOT receive:**
- URLs from verified citations
- Snippets from Google CSE
- Case titles or descriptions
- Any legal context from verified precedents

**Current model:** openai/o3-pro (thinking_effort: high)
**Current cost:** ~$0.08 per brainstorm (~3,000 tokens)

### Data Flow: Verification → Plausibility → Analysis

```
1. STRATEGY GENERATION
   ↓ Orthodox (15) + Unorthodox (15) strategies with citations

2. CITATION VERIFICATION
   ↓ verify_all_citations(all_text)
   ↓ Google CSE returns: title, snippet, link
   ↓ Only snippet used for matching, then DISCARDED
   ↓ Returns: (verified: List[str], unverified: List[Tuple[str, str]])

3. BUILD VERIFICATION MAPS
   ↓ verified_set = set(verified_citations)
   ↓ unverified_dict = {citation: reason}

4. PLAUSIBILITY ASSESSMENT (for strategies with unverified citations)
   ↓ Input: Strategy preview + unverified citations + reasons
   ↓ Output: Risk assessment (LOW/MEDIUM/HIGH) + confidence + explanation
   ↓ Model: o3-pro with thinking_effort: high

5. ANNOTATION
   ↓ [VERIFIED]: {citation}
   ↓ [NOT VERIFIED]: {citation} - {risk} RISK ({conf}%) - {explanation}

6. ANALYSIS GENERATION
   ↓ Receives annotated strategies
   ↓ Selects 10 most promising
   ↓ Model: o3-pro with thinking_effort: high
```

**Information lost between stages:**
- Stage 2→3: Google CSE snippets, titles, full search results
- Stage 3→6: Any context about verified citations
- Analysis relies on LLM memory of law, not actual verified precedents

## Why This Enhancement Is Needed

### Problem 1: Plausibility Assessment Is Guesswork

**Current behavior:**
```
[NOT VERIFIED]: [1999] NSWCA 856
o3-pro assessment: "MEDIUM RISK - The strategy correctly relies on Motor Accident
Injuries Act provisions, so the substantive legal principle is sound..."
```

**Question:** How does o3-pro "know" the principle is sound?
**Answer:** It's guessing from training data (Australian law).

**Risk:** Hallucinated assessment of legal soundness

### Problem 2: Analysis Can't Verify Legal Reasoning

**Current prompt:** [strategies.yaml:79-93](../litassist/prompts/strategies.yaml)
```yaml
**Consider citation quality when selecting strategies:**
- For unverified citations, assess if legal reasoning is still sound
```

**Problem:** Analysis LLM can't actually verify if "legal reasoning is still sound" - it only sees citation strings without context.

### Problem 3: No Actionable Alternatives

**Current output:**
```
[NOT VERIFIED]: [1999] NSWCA 856 - Citation not found in online databases
```

**User question:** "What should I use instead?"
**Current answer:** Nothing - user must research manually

## Proposed Solution

### Overview

Add 2-3 sentence case summaries to verified citations throughout the pipeline:

1. **During verification:** Capture and store summaries
2. **During plausibility checking:** Include verified summaries for context
3. **In final output:** Display summaries under [VERIFIED] annotations
4. **In analysis:** Provide summaries to enable better strategy selection

### Data Sources

**Primary: Full Document Fetching**
- Use existing `fetch_citation_context()` function [citation_context.py:177-415](../litassist/citation/citation_context.py)
- Fetches complete legal documents from AustLII, Jade, etc.
- Extract 2-3 sentence summaries using heuristics

**Fallback: Google CSE Snippets**
- Already fetched during verification (zero additional cost)
- Use when full document fetch fails
- Quality: 150-200 char preview

### Enhanced Data Flow

```
1. STRATEGY GENERATION (unchanged)
   ↓

2. CITATION VERIFICATION (enhanced)
   ↓ verify_all_citations(all_text)
   ↓ Google CSE returns: title, snippet, link
   ↓ STORE snippets (not discard)
   ↓ Returns: [(citation, url, snippet), ...] for verified

3. FETCH SUMMARIES FOR VERIFIED CITATIONS (NEW)
   ↓ For each verified citation:
   ↓   try: fetch_citation_context(citation)
   ↓        summary = extract_summary(full_text)
   ↓   except: summary = google_cse_snippet (fallback)
   ↓ Store in cache: {exists, url, snippet, summary, source}

4. PLAUSIBILITY ASSESSMENT (enhanced)
   ↓ Input: Strategy preview
   ↓        + Verified citations WITH SUMMARIES
   ↓        + Unverified citations with reasons
   ↓ Model can assess if unverified citations have sound legal basis
   ↓ by comparing to verified precedents in same strategy

5. ANNOTATION (enhanced)
   ↓ [VERIFIED]: {citation}
   ↓   Summary: {2-3 sentence case summary}
   ↓ [NOT VERIFIED]: {citation} - {risk assessment with reference to verified alternatives}

6. ANALYSIS GENERATION (enhanced)
   ↓ Receives annotated strategies WITH summaries
   ↓ Can evaluate based on:
   ↓   - Strength of verified precedent (High Court vs lower courts)
   ↓   - Recency of authorities
   ↓   - Relevance of legal principles
   ↓   - Overlap between strategies
```

## Concrete Example Walkthrough

### Input Strategy

```
ORTHODOX_5: Challenge causation by arguing plaintiff's psychological injury
stems from pre-existing condition rather than defendant's negligence, citing
Watts v Rake (1960) 108 CLR 158 and [2005] NSWCA 295 regarding evidentiary
burden on pre-existing conditions.

Also cite [2006] NSWCA 142 on similar principle.
```

### Verification Phase (Enhanced)

**Citation 1:** Watts v Rake (1960) 108 CLR 158
**Result:** VERIFIED
**Google CSE snippet:** "High Court held that plaintiff bears burden of proving injury was caused by defendant's breach, not pre-existing condition."
**Action:** Fetch full document from AustLII
**Extracted summary:** "Watts v Rake (1960) 108 CLR 158. High Court held that in negligence claims, the plaintiff bears the burden of proving that their injury was caused by the defendant's breach of duty, not by a pre-existing condition. Defendants cannot escape liability merely by showing plaintiff had prior vulnerabilities."

**Citation 2:** [2005] NSWCA 295
**Result:** VERIFIED
**Google CSE snippet:** "Court of Appeal examined evidentiary requirements for distinguishing injury from pre-existing conditions."
**Action:** Fetch full document - FAILS (paywall/timeout)
**Fallback summary:** Use Google CSE snippet

**Citation 3:** [2006] NSWCA 142
**Result:** NOT VERIFIED (citation not found)

### Plausibility Checking Phase (Enhanced)

**Input to o3-pro:**
```
ORTHODOX_5:
[Challenge causation by arguing plaintiff's psychological injury stems from
pre-existing condition rather than defendant's negligence...]

Verified Citations (legal context for this strategy):
  - Watts v Rake (1960) 108 CLR 158: High Court held that in negligence
    claims, the plaintiff bears the burden of proving that their injury was
    caused by the defendant's breach of duty, not by a pre-existing condition.
    Defendants cannot escape liability merely by showing plaintiff had prior
    vulnerabilities.

  - [2005] NSWCA 295: Court of Appeal examined evidentiary requirements for
    distinguishing injury caused by negligence from pre-existing medical
    conditions in motor vehicle accident cases.

Unverified Citations (assess these):
  - [2006] NSWCA 142 (Reason: Citation not found in online databases)

Task: Assess whether the unverified citation appears plausible given the
verified legal context above.
```

**o3-pro assessment:**
```
LOW RISK (confidence: 85%) - The legal principle regarding causation and
pre-existing conditions is well-established and confirmed by verified High
Court precedent Watts v Rake and NSW Court of Appeal authority [2005] NSWCA 295.
The unverified citation [2006] NSWCA 142 likely represents a citation error or
database gap rather than fabrication, as the substantive legal reasoning is
sound and corroborated by multiple verified authorities. Recommend verifying
manually or replacing with [2005] NSWCA 295.
```

**Comparison to current (without summaries):**
```
MEDIUM RISK (confidence: 75%) - Citation not found. Legal principle sounds
plausible but cannot verify.
```

**Improvement:** More confident assessment, grounded in verified precedents, provides actionable alternative

### Annotation Phase (Enhanced, User-Facing)

**Current:**
```
[VERIFIED]: Watts v Rake (1960) 108 CLR 158
[VERIFIED]: [2005] NSWCA 295
[NOT VERIFIED]: [2006] NSWCA 142 - Citation not found
```

**Enhanced:**
```
[VERIFIED]: Watts v Rake (1960) 108 CLR 158
  Summary: High Court held that in negligence claims, the plaintiff bears
  the burden of proving that their injury was caused by the defendant's
  breach of duty, not by a pre-existing condition. Defendants cannot escape
  liability merely by showing plaintiff had prior vulnerabilities.

[VERIFIED]: [2005] NSWCA 295
  Summary: Court of Appeal examined evidentiary requirements for distinguishing
  injury caused by negligence from pre-existing medical conditions in motor
  vehicle accident cases.

[NOT VERIFIED]: [2006] NSWCA 142 - LOW RISK (85% confidence)
  Assessment: Legal principle well-established via verified precedents above.
  Citation likely database gap. Suggest replacing with [2005] NSWCA 295.
```

**User value:**
- Understands what each verified case actually held
- Can evaluate strength of legal basis themselves
- Has concrete alternative citation to use
- Can quickly validate unverified citation manually with context

### Analysis Phase (Enhanced)

**Input to analysis LLM:**
- All 30 strategies with verified summaries
- Can evaluate legal strength based on actual precedents

**Example selection reasoning:**
```
Selected ORTHODOX_5 because:
- Strong High Court precedent (Watts v Rake) - highest authority
- Recent Court of Appeal confirmation ([2005] NSWCA 295)
- Well-established legal principle (causation burden)
- Low risk on unverified citation (principle confirmed via verified alternatives)
- Overlaps with ORTHODOX_8's approach (both cite Watts v Rake)
```

**Without summaries:**
```
Selected ORTHODOX_5 because:
- Addresses causation element
- Multiple citations suggest well-researched
[LLM guessing about legal strength]
```

## Technical Implementation Plan

### Files to Modify

#### 1. litassist/citation/google_cse.py

**Change:** Return snippets with search results

**Current:**
```python
def search_google_cse(query: str) -> List[str]:
    # Returns list of URLs only
```

**Enhanced:**
```python
def search_google_cse(query: str) -> List[Dict[str, str]]:
    # Returns: [{"url": "...", "snippet": "...", "title": "..."}, ...]
```

**Effort:** 30 minutes

#### 2. litassist/citation/cache.py

**Change:** Update cache schema

**Current:**
```python
{
    "exists": bool,
    "url": str,
    "reason": str
}
```

**Enhanced:**
```python
{
    "exists": bool,
    "url": str,
    "reason": str,
    "snippet": str,           # Google CSE snippet
    "summary": str,           # 2-3 sentence summary
    "source": str             # "full_document" or "snippet_fallback"
}
```

**Effort:** 30 minutes

#### 3. litassist/citation/verify.py

**Change:** Store snippets from Google CSE

**Current:**
```python
verified_citations = []  # List[str]
unverified_citations = []  # List[Tuple[str, str]]
```

**Enhanced:**
```python
verified_citations = []  # List[Tuple[str, str, str]] - (citation, url, snippet)
unverified_citations = []  # List[Tuple[str, str]] - (citation, reason)
```

**Effort:** 1 hour

#### 4. litassist/citation/summary_extractor.py (NEW FILE)

**Purpose:** Extract 2-3 sentence summaries from legal documents

**Functions:**
```python
def extract_summary_from_document(full_text: str, citation: str) -> str:
    """
    Extract 2-3 sentence summary using heuristics.
    Try in order:
    1. Catchwords section (Australian legal standard)
    2. Headnote/summary section
    3. First substantive paragraph (skip procedural)
    4. First 2-3 sentences as fallback
    """

def extract_catchwords(text: str) -> Optional[str]:
    """Extract catchwords section from legal document"""

def extract_headnote(text: str) -> Optional[str]:
    """Extract headnote or summary section"""

def find_first_substantive_paragraph(text: str) -> Optional[str]:
    """Find first paragraph with legal content (skip procedural)"""

def is_good_quality_summary(summary: str) -> bool:
    """Check if summary meets quality criteria"""

def format_summary(text: str, max_sentences: int = 3) -> str:
    """Format text as 2-3 sentence summary"""
```

**Effort:** 2-3 hours

#### 5. litassist/commands/brainstorm/core.py

**Changes:**
1. After verification, fetch documents for verified citations
2. Extract summaries (with snippet fallback)
3. Update `collect_strategies_for_plausibility()` to include verified summaries
4. Update `assess_legal_plausibility_bulk()` to receive and use summaries
5. Update `_annotate_strategies_with_verification()` to include summaries
6. Pass annotated strategies with summaries to analysis

**Key modifications:**

```python
# After line 242 (verification):
verified_citations, unverified_citations = verify_all_citations(all_text)

# NEW: Fetch summaries for verified citations
verified_with_summaries = fetch_summaries_for_verified_citations(
    verified_citations,
    strategies_for_plausibility  # Only fetch for strategies needing plausibility
)

# Update plausibility checking to include summaries:
assess_legal_plausibility_bulk(
    strategies_for_plausibility,
    verified_summaries_map  # NEW parameter
)

# Update annotation to include summaries:
_annotate_strategies_with_verification(
    strategies,
    verified_with_summaries,  # Enhanced with summaries
    risk_assessments
)
```

**Effort:** 2-3 hours

#### 6. litassist/prompts/strategies.yaml

**Changes:**
1. Update plausibility prompt template to include verified summaries
2. Ensure analysis prompt can utilize summaries

**Plausibility prompt enhancement:**

```yaml
# Current (lines 146-177):
strategies.brainstorm.plausibility_base: |
  For each strategy below, assess whether the unverified citations appear to be:
  [...]

# Enhanced:
strategies.brainstorm.plausibility_base: |
  For each strategy below, you are provided with:
  1. Strategy preview
  2. Verified citations in this strategy WITH case summaries (legal context)
  3. Unverified citations that need assessment

  Use the verified citations to evaluate whether the legal principles in
  unverified citations are plausible and sound.

  Format for each strategy:
  **{STRATEGY_ID}:**
  {strategy_preview}

  Verified Citations (legal context):
  {verified_summaries}

  Unverified Citations (assess these):
  {unverified_with_reasons}

  Assess whether unverified citations appear to be:
  - LOW RISK: Legal principle confirmed by verified citations above
  - MEDIUM RISK: Principle plausible but citation suspect
  - HIGH RISK: No verified support, likely hallucination
```

**Effort:** 1 hour

### New Helper Functions

#### Fetch Summaries for Verified Citations

```python
def fetch_summaries_for_verified_citations(
    verified_citations: List[Tuple[str, str, str]],
    strategies_for_plausibility: List[Tuple]
) -> Dict[str, Dict[str, str]]:
    """
    Fetch full documents and extract summaries for verified citations.
    Only process citations in strategies needing plausibility checking.

    Args:
        verified_citations: List of (citation, url, snippet) tuples
        strategies_for_plausibility: Strategies with unverified citations

    Returns:
        {citation: {"summary": "...", "source": "full_document|snippet_fallback"}}
    """
    # 1. Identify which verified citations are in strategies needing plausibility
    citations_to_process = set()
    for strategy_id, strategy_text, unverified in strategies_for_plausibility:
        for citation, url, snippet in verified_citations:
            if citation in strategy_text:
                citations_to_process.add((citation, url, snippet))

    # 2. Fetch documents and extract summaries (parallelized, batched)
    summaries = {}
    for citation, url, snippet in citations_to_process:
        try:
            # Check cache first
            cached = cache.get(citation)
            if cached and "summary" in cached:
                summaries[citation] = cached
                continue

            # Fetch full document
            full_text = fetch_citation_context(citation)

            # Extract summary
            summary = extract_summary_from_document(full_text, citation)

            # Store in cache
            cache.set(citation, {
                "exists": True,
                "url": url,
                "snippet": snippet,
                "summary": summary,
                "source": "full_document"
            })

            summaries[citation] = {
                "summary": summary,
                "source": "full_document"
            }

        except Exception as e:
            # Fallback to snippet
            logger.warning(f"Failed to fetch {citation}, using snippet: {e}")
            summary = snippet

            cache.set(citation, {
                "exists": True,
                "url": url,
                "snippet": snippet,
                "summary": summary,
                "source": "snippet_fallback"
            })

            summaries[citation] = {
                "summary": summary,
                "source": "snippet_fallback"
            }

    return summaries
```

#### Parallel Batched Fetching (Performance Optimization)

```python
from concurrent.futures import ThreadPoolExecutor
import time

def fetch_summaries_batch(
    citations_to_process: Set[Tuple[str, str, str]],
    batch_size: int = 5,
    delay: float = 2.0
) -> Dict[str, Dict[str, str]]:
    """
    Fetch summaries in parallel batches to avoid rate limits.

    Args:
        citations_to_process: Set of (citation, url, snippet) tuples
        batch_size: Number of concurrent fetches per batch
        delay: Seconds to wait between batches

    Returns:
        {citation: {"summary": "...", "source": "..."}}
    """
    citations_list = list(citations_to_process)
    all_summaries = {}

    for i in range(0, len(citations_list), batch_size):
        batch = citations_list[i:i+batch_size]

        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = {
                executor.submit(fetch_and_summarize, cit, url, snip): cit
                for cit, url, snip in batch
            }

            for future in futures:
                citation = futures[future]
                try:
                    result = future.result(timeout=10)
                    all_summaries[citation] = result
                except Exception as e:
                    logger.error(f"Batch fetch failed for {citation}: {e}")

        # Rate limiting between batches
        if i + batch_size < len(citations_list):
            time.sleep(delay)

    return all_summaries

def fetch_and_summarize(
    citation: str,
    url: str,
    snippet: str
) -> Dict[str, str]:
    """Single citation fetch and summarize operation"""
    try:
        full_text = fetch_citation_context(citation)
        summary = extract_summary_from_document(full_text, citation)
        return {"summary": summary, "source": "full_document"}
    except Exception:
        return {"summary": snippet, "source": "snippet_fallback"}
```

## Edge Cases and Solutions

### Edge Case 1: Document Fetch Fails

**Scenario:** Citation verified via Google CSE but document fetch fails (paywall, rate limit, timeout)

**Solution:** Fallback to Google CSE snippet (already have it from verification)

**User sees:**
```
[VERIFIED]: [2005] NSWCA 295
  Summary: Court of Appeal examined evidentiary requirements for distinguishing
  injury caused by negligence from pre-existing medical conditions.
```

No indication to user that this is a snippet vs full summary (quality is usually adequate).

### Edge Case 2: Summary Extraction Produces Poor Quality

**Scenario:** Document fetched but first paragraph is procedural: "The appellant appeals from orders made by Justice Smith on 15 March..."

**Solution:** Multi-stage extraction with quality checks

```python
def extract_summary_from_document(full_text: str, citation: str) -> str:
    # Try 1: Catchwords
    if catchwords := extract_catchwords(full_text):
        return format_summary(catchwords)

    # Try 2: Headnote
    if headnote := extract_headnote(full_text):
        return format_summary(headnote)

    # Try 3: First substantive paragraph
    substantive = find_first_substantive_paragraph(full_text)
    if substantive and is_good_quality_summary(substantive):
        return format_summary(substantive)

    # Try 4: LLM-generated summary (expensive fallback)
    # Only use for documents < 10KB to control costs
    if len(full_text) < 10000:
        return generate_summary_with_llm(full_text, citation)

    # Final fallback: First 3 sentences
    return extract_first_n_sentences(full_text, 3)
```

### Edge Case 3: Too Many Verified Citations (Token Explosion)

**Scenario:** Strategy has 10 verified citations, summaries would add 750+ tokens to plausibility prompt

**Solution:** Only fetch summaries for verified citations in strategies that have unverified citations

**Optimization:**
```python
# Don't fetch summaries for fully-verified strategies
# Only fetch for strategies going to plausibility checker
strategies_for_plausibility = [
    (id, text, unverified_cits)
    for id, text in strategies
    if has_unverified_citations(text)
]

# Only fetch summaries for verified citations in these strategies
```

**Token savings:**
- Without optimization: 50 verified citations × 75 tokens = 3,750 tokens
- With optimization: ~20 verified citations × 75 tokens = 1,500 tokens

### Edge Case 4: Parallel Fetching Triggers Rate Limits

**Scenario:** Fetching 30 documents in parallel triggers AustLII rate limiting (429 errors)

**Solution:** Batched parallel fetching with delays

**Implementation:**
- Batch size: 5 concurrent requests
- Delay between batches: 2 seconds
- Timeout per request: 10 seconds

**Performance:**
- 30 citations in 6 batches = ~15-20 seconds (vs 60+ sequential)
- Rate limit compliant
- Handles failures gracefully

### Edge Case 5: Very Long Case Summaries

**Scenario:** Catchwords section is 10 sentences (500+ chars)

**Solution:** Enforce 2-3 sentence limit

```python
def format_summary(text: str, max_sentences: int = 3, max_chars: int = 400) -> str:
    """
    Format text as concise summary.

    Rules:
    - Maximum 3 sentences
    - Maximum 400 characters
    - Prefer complete sentences over truncation
    """
    sentences = split_into_sentences(text)

    # Take first max_sentences
    summary_sentences = sentences[:max_sentences]
    summary = " ".join(summary_sentences)

    # If still too long, truncate at sentence boundary
    if len(summary) > max_chars:
        summary_sentences = sentences[:max_sentences-1]
        summary = " ".join(summary_sentences)

    return summary
```

## Performance Analysis

### Time Impact

**Current brainstorm runtime:** 60-90 seconds
- Strategy generation: 30-45 seconds (two LLM calls)
- Verification: 10-20 seconds (Google CSE searches, cached after first run)
- Plausibility: 15-30 seconds (o3-pro thinking)

**Additional time with enhancement:**
- Document fetching: 15-30 seconds (batched parallel, cached after first run)
- Summary extraction: < 1 second (heuristic-based)

**New total:** 75-120 seconds (16-33% increase)

**Mitigation:**
- Aggressive caching (summaries cached permanently)
- Second run on same case: No additional time (all cached)
- Progress indicators for user ("Fetching case summaries... 15/30")

### Token Cost Impact

**Current plausibility check:** ~3,000 tokens
- Strategy previews: 500 chars × 15 strategies = 7,500 chars (~2,000 tokens)
- Unverified citations: ~50 chars × 20 = 1,000 chars (~250 tokens)
- Prompt template: ~400 chars (~100 tokens)
- Response: ~500-800 tokens

**Additional tokens with enhancement:**
- Verified summaries: 300 chars × 20 verified = 6,000 chars (~1,500 tokens)

**New total:** ~4,500 tokens (+50%)

**Cost impact:**
- Current: ~$0.08/brainstorm
- Enhanced: ~$0.12-$0.13/brainstorm
- **Increase: +$0.04-$0.05 per brainstorm**

**User confirmed acceptable**

### Storage Impact

**Cache growth:**
- Current: ~200 bytes per cached citation
- Enhanced: ~600 bytes per cached citation (+400 bytes for snippet + summary)
- Typical case: 100 unique citations = +40KB cache growth
- **Negligible**

## Outstanding Questions for User

### Question 1: Summary Extraction Method

**Options:**

**a) Heuristic-based (FAST, FREE, variable quality)**
- Try catchwords → headnote → first substantive paragraph → first 3 sentences → snippet
- No API costs, fast execution
- Quality varies by document structure

**b) LLM-generated (SLOW, EXPENSIVE, consistent quality)**
- Ask LLM to summarize each case: "Summarize this case in 2-3 sentences"
- Consistent high-quality summaries
- Cost: ~$11/brainstorm just for summarization (30 citations × 25KB × 2)

**c) Hybrid (RECOMMENDED)**
- Try heuristic extraction first
- Check quality (length, legal terms, coherence)
- If poor quality AND document < 10KB: use LLM
- Otherwise: use heuristic or fallback to snippet
- Balance of cost and quality

**Recommendation:** Option C (Hybrid)
**Rationale:** Minimizes cost while ensuring quality fallback

### Question 2: Summary Inclusion Scope for Analysis Prompt

For plausibility checking: Include summaries for verified citations in strategies with unverified citations (clear use case)

For analysis prompt: Which option?

**Option A:** All verified citations in all 30 strategies
- Most context for analysis LLM
- Can compare strength across all strategies
- Cost: +3,000 tokens (~+$0.07)

**Option B:** Only verified citations in strategies that had unverified citations
- Saves tokens (only ~10-15 strategies)
- Less context for comparing strategies
- Cost: +1,000 tokens (~+$0.02)

**Question:** Which scope for analysis prompt?

### Question 3: Summary Display Format in Final Output

**Option A (Concise):**
```
[VERIFIED]: Watts v Rake (1960) 108 CLR 158
  Plaintiff bears burden proving causation, not defendant to disprove pre-existing condition.
```

**Option B (Detailed, RECOMMENDED):**
```
[VERIFIED]: Watts v Rake (1960) 108 CLR 158
  Summary: High Court held that in negligence claims, the plaintiff bears the
  burden of proving that their injury was caused by the defendant's breach of
  duty, not by a pre-existing condition. Defendants cannot escape liability
  merely by showing plaintiff had prior vulnerabilities.
```

**Option C (With metadata):**
```
[VERIFIED]: Watts v Rake (1960) 108 CLR 158 (High Court of Australia)
  Principle: Plaintiff bears burden of proving causation in negligence claims.
  Defendants cannot escape liability by showing prior vulnerabilities.
  [Source: Full document | AustLII]
```

**Recommendation:** Option B (Detailed)
**Rationale:** Clear, informative, not cluttered with metadata

**Question:** Which format?

### Question 4: Summary Length Enforcement

**Options:**

**a) Strict:** Exactly 2-3 sentences, truncate if longer
- Consistent format
- May cut important context

**b) Flexible:** 2-5 sentences if needed for completeness
- More complete summaries
- Variable length

**c) Character limit:** 250-400 characters regardless of sentence count
- Consistent token usage
- May break sentences unnaturally

**Recommendation:** Option B (Flexible 2-5 sentences, max 400 chars)
**Rationale:** Balances completeness with token efficiency

**Question:** Which length enforcement?

## Implementation Timeline

### Phase 1: Core Infrastructure (4-5 hours)
1. Modify google_cse.py to return snippets ✓
2. Update cache.py schema ✓
3. Store snippets in verify.py ✓
4. Create summary_extractor.py ✓

### Phase 2: Integration (3-4 hours)
1. Add summary fetching to brainstorm/core.py ✓
2. Update plausibility checking to include summaries ✓
3. Update annotation logic ✓
4. Update prompt templates ✓

### Phase 3: Testing and Refinement (2-3 hours)
1. Test on known cases ✓
2. Verify summaries in all locations ✓
3. Test fallback mechanisms ✓
4. Validate token costs ✓
5. Performance testing ✓

**Total estimated effort:** 10-12 hours

## Testing Strategy

### Test Case 1: Mixed Verification with Known Cases

**Input:** Case with:
- 3 verified High Court cases (should fetch full documents)
- 2 verified NSWCA cases (test variety)
- 2 unverified citations (similar to verified ones)

**Expected:**
- Summaries fetched for verified citations
- Plausibility prompt includes summaries
- Plausibility assessment references verified precedents
- Final output shows summaries under [VERIFIED]
- Analysis receives summaries

### Test Case 2: Document Fetch Failures

**Input:** Case with citations where:
- 2 verified but behind paywalls (should fallback to snippets)
- 3 verified with fetchable documents

**Expected:**
- Snippet fallback works correctly
- No errors or crashes
- User sees summaries (mix of full and snippet-based)

### Test Case 3: Token Cost Validation

**Input:** Case generating typical verification (20 verified, 10 unverified)

**Expected:**
- Token count matches projections (~4,500 tokens)
- Cost increase ~$0.04-$0.05
- Logged in LLM request/response logs

### Test Case 4: Performance Testing

**Input:** Case with 30 verified citations

**Expected:**
- Completes in < 2 minutes
- Progress indicators displayed
- Parallel fetching works without rate limits
- Second run uses cache (minimal additional time)

### Test Case 5: Summary Quality

**Input:** Mix of case types:
- High Court decision with catchwords
- NSWCA decision with headnote
- Older case without structured summary

**Expected:**
- Catchwords extracted correctly
- Headnotes formatted properly
- Older cases fallback to first paragraph or snippet
- All summaries 2-5 sentences, < 400 chars
- Legal principles clearly stated

## Success Criteria

### Functional Requirements
- ✓ Summaries fetched for all verified citations (with snippet fallback)
- ✓ Summaries appear in plausibility prompt
- ✓ Summaries appear in final output under [VERIFIED]
- ✓ Summaries passed to analysis prompt
- ✓ Fallback to snippets when document fetch fails
- ✓ No crashes or errors on edge cases

### Quality Requirements
- ✓ Summaries are 2-5 sentences, < 400 chars
- ✓ Summaries contain legal principles (not just procedural)
- ✓ Plausibility assessments reference verified precedents
- ✓ Analysis selections justify based on verified strength

### Performance Requirements
- ✓ Brainstorm completes in < 2 minutes
- ✓ Second run (cached) has minimal overhead
- ✓ No rate limiting errors from parallel fetching

### Cost Requirements
- ✓ Token increase < 60% (+1,500 tokens max)
- ✓ Cost increase < $0.06 per brainstorm
- ✓ No expensive LLM summarization (unless hybrid fallback)

## Future Enhancements

### Enhancement 1: Smart Citation Suggestions

When unverified citation detected, automatically suggest most similar verified citation:

```
[NOT VERIFIED]: [1999] NSWCA 856 - LOW RISK
  Suggested replacement: [1998] NSWCA 314 (verified, same court/year/topic)
  Summary: [case summary]
```

### Enhancement 2: Cross-Strategy Citation Analysis

Identify when multiple strategies cite same verified precedent:

```
Analysis insight: 5 strategies rely on Watts v Rake principle (causation burden).
Suggests strong legal basis for causation challenge approach.
```

### Enhancement 3: Precedent Strength Scoring

Rate verified citations by authority level:

- High Court: 5 stars
- Full Federal Court / Full Court of Appeal: 4 stars
- Single judge Court of Appeal: 3 stars
- First instance: 2 stars

Display in summaries:

```
[VERIFIED]: Watts v Rake (1960) 108 CLR 158 ⭐⭐⭐⭐⭐
  Summary: [High Court precedent]
```

### Enhancement 4: Summary Caching Across Cases

Build a permanent library of case summaries:

- Cache summaries separately from verification cache
- Reuse summaries across different brainstorm runs
- Eventually build comprehensive Australian case law summary database

## Conclusion

This enhancement addresses the core limitation of current plausibility checking and analysis: lack of verified legal context. By adding 2-3 sentence case summaries to verified citations throughout the pipeline, we enable:

1. **Grounded plausibility assessment** - o3-pro can verify legal principles against actual verified cases
2. **Better strategy selection** - Analysis can evaluate strength based on verified precedent
3. **User value** - Concrete case context and actionable citation alternatives

**Implementation is technically feasible:**
- All required components exist (document fetching, verification, prompts)
- Fallback mechanisms handle edge cases (snippet when fetch fails)
- Performance acceptable (15-30 seconds additional, cached after first run)
- Cost acceptable (+$0.04-$0.05 per brainstorm, approved by user)

**Recommended approach:**
- Phase 2 (full document summaries) with snippet fallback
- Hybrid extraction method (heuristic with LLM fallback for poor quality)
- Include summaries in plausibility, output annotations, and analysis
- Flexible 2-5 sentence summaries (max 400 chars)

**Next step:** Answer 4 outstanding questions, then proceed with implementation.
