# LitAssist LLM Model Strategy

**Last Updated**: October 23, 2025
**Status**: Living Document
**Purpose**: Comprehensive guide to LLM usage, model selection, and improvement strategies

---

## Table of Contents

1. [Current Model Configuration (October 2025)](#current-model-configuration-october-2025)
2. [Three-Tier Quality Strategy](#three-tier-quality-strategy)
3. [Technical Configuration Reference](#technical-configuration-reference)
4. [LLM Response Philosophy](#llm-response-philosophy)
5. [Command-Specific Improvements](#command-specific-improvements)
6. [Future Model Opportunities](#future-model-opportunities)
7. [Global Improvements](#global-improvements)
8. [Implementation History](#implementation-history)
9. [Configuration Best Practices](#configuration-best-practices)

---

## Current Model Configuration (October 2025)

### Active Models by Purpose

| Model | Commands Using It | Purpose | Hallucination Rate | Cost |
|-------|------------------|---------|-------------------|------|
| **Claude Sonnet 4.5** | strategy, extractfacts, digest-*, caseplan, brainstorm-orthodox, verification-light, cove-* | Legal reasoning, foundational tasks | ~2-3% | $3/$15 |
| **OpenAI GPT-5 Pro** | verification-heavy | Critical verification (<1% hallucination) | <1% | Premium |
| **OpenAI GPT-5** | verification, cove-answers, cove-final | Standard verification | 1.4-1.6% | Higher |
| **OpenAI o3-pro** | draft, counselnotes, barbrief, strategy-analysis, brainstorm-analysis, verify-reasoning | Advanced reasoning, superior drafting | ~15-20%* | Higher |
| **Google Gemini 2.5 Pro** | lookup | Rapid processing (1M context) | ~2-3% | $1.25/$5 |
| **xAI Grok 4** | brainstorm-unorthodox | Creative ideation | ~5-8% | Medium |

*\*o3-pro has higher hallucination rate but excels at structured reasoning and drafting*

### Key Configuration Principles

1. **OpenRouter-First**: All LLM calls route through OpenRouter for unified management
2. **Dynamic Parameter Filtering**: Model family patterns determine allowed parameters
3. **Universal thinking_effort**: Single parameter translates to model-specific reasoning controls
4. **Citation Enforcement**: Selective enforcement based on task criticality
5. **Tool Calling Fallbacks**: Date injection fallback when tool calling fails

**Reference**: See `MODEL_CONFIGURATION.md` for complete parameter details

---

## Three-Tier Quality Strategy

**Implemented**: October 2025

### Tier 1: Critical Accuracy (GPT-5 Pro)
- **Hallucination Rate**: <1%
- **Use Case**: Final verification, critical legal analysis
- **Commands**: verification-heavy, cove-final
- **Cost**: Premium, justified by professional liability requirements

### Tier 2: Fast Verification (GPT-5)
- **Hallucination Rate**: 1.4-1.6%
- **Use Case**: Standard verification, fact-checking
- **Commands**: verification, cove-answers
- **Cost**: Higher, but 6x better than o3 on hallucinations

### Tier 3: Legal Reasoning (Claude Sonnet 4.5)
- **Hallucination Rate**: ~2-3%
- **Use Case**: Legal analysis, strategy, document processing
- **Commands**: strategy, extractfacts, digest-*, brainstorm-orthodox
- **Cost**: $3/$15 (80% cheaper than Opus 4.1)
- **Key Strength**: "State of the art on complex litigation tasks" per Anthropic

### Cost-Quality Optimization

**October 2025 Results**:
- 40-50% overall cost reduction
- Improved legal reasoning quality
- Maintained <2% hallucination rate on critical verification

**Key Insight**: Claude Sonnet 4.5's legal expertise eliminates need for Opus 4.1, achieving better quality at 80% lower cost

---

## Technical Configuration Reference

**See `MODEL_CONFIGURATION.md` for complete technical details.** Key information summarized below:

### Model Capabilities Summary

#### Claude Sonnet 4.5 (September 2025)
- **Model ID**: `anthropic/claude-sonnet-4.5`
- **Pricing**: $3/$15 per M tokens (80% cheaper than Opus 4.1)
- **Key Features**: Extended thinking mode, state-of-the-art litigation performance
- **Parameters**: temperature, top_p, thinking_effort (low/medium/high/max)
- **BYOK**: Not required on OpenRouter
- **Commands**: 14 total (strategy, extractfacts, digest, caseplan, verification-light, etc.)

#### GPT-5 and GPT-5 Pro (August 2025)
- **Model IDs**: `openai/gpt-5`, `openai/gpt-5-pro`
- **Hallucination Rates**: GPT-5 (1.4-1.6%), GPT-5 Pro (<1%)
- **Key Features**: 6x fewer factual errors, 80% fewer hallucinations than o3
- **Parameters**: Standard OpenAI (temperature, top_p, max_tokens)
- **BYOK**: Required on OpenRouter (Tier 4+ API key)
- **Commands**: verification (GPT-5), verification-heavy/cove-final (GPT-5 Pro)

#### OpenAI o3-pro
- **Model ID**: `openai/o3-pro`
- **Purpose**: Extended comprehensive document generation
- **Supported Parameters**: `max_completion_tokens` (NOT max_tokens), `reasoning_effort`
- **Restrictions**: NO temperature, top_p, or penalty parameters
- **BYOK**: Required through OpenRouter
- **Max Output**: 32768 tokens (32K)
- **Commands**: barbrief, counselnotes, draft, strategy-analysis, brainstorm-analysis

#### Gemini 2.5 Pro
- **Model ID**: `google/gemini-2.5-pro`
- **Context Window**: 1M tokens (900K used for content in lookup)
- **Pricing**: $1.25/$5 per M tokens
- **Parameters**: temperature, top_p, max_tokens
- **Commands**: lookup

#### Grok 4
- **Model ID**: `x-ai/grok-4`
- **Purpose**: Creative legal strategy generation
- **Auto-verification**: Enabled due to higher hallucination tendency
- **Parameters**: temperature (0.9), top_p (0.95) for creativity
- **Commands**: brainstorm-unorthodox

### Dynamic Parameter System

LitAssist uses pattern-based parameter filtering:

```python
MODEL_PATTERNS = {
    "openai_reasoning": r"openai/o\d+",      # o3, o3-pro, future o4, o5
    "gpt5": r"openai/gpt-5(-pro)?",          # GPT-5, GPT-5 Pro
    "claude4": r"anthropic/claude-(opus-4|sonnet-4)(\.\d+)?",  # Claude 4.x
    "anthropic": r"anthropic/claude",         # Other Claude models
    "google": r"google/(gemini|palm|bard)",
    "openai_standard": r"openai/(gpt|chatgpt)",
    "xai": r"x-ai/grok",
}
```

**Benefits**:
- Future model versions work without code changes
- No hardcoded model-specific logic
- Automatic parameter filtering per model family
- Maintainable centralized configuration

### Common Model Restrictions

**o3-pro Restrictions**:
- ✅ **Allowed**: `max_completion_tokens`, `reasoning_effort`
- ❌ **Forbidden**: `temperature`, `top_p`, `max_tokens`, `frequency_penalty`, `presence_penalty`
- ⚠️ **Note**: Use `max_completion_tokens` NOT `max_tokens`

**Claude Sonnet 4.5**:
- ✅ **Universal**: Works with `thinking_effort` parameter
- ⚠️ **Tool Calling**: May need `disable_tools: True` on OpenRouter (Sept 2025 issue)

**GPT-5 Family**:
- ✅ **Standard Parameters**: temperature, top_p, max_tokens
- ✅ **Thinking Mode**: Supports `thinking_effort` parameter
- ⚠️ **BYOK Required**: Must configure OpenAI API key in OpenRouter

### Environment Variable Overrides

```bash
export ANTHROPIC_MODEL="anthropic/claude-sonnet-4.5"
export OPENAI_MODEL="openai/o3-pro"
export GOOGLE_MODEL="google/gemini-2.5-pro"
export XGROK_MODEL="x-ai/grok-4"
```

### OpenRouter Configuration

**All models route through OpenRouter**:
```yaml
# config.yaml
openrouter:
  api_key: "your-openrouter-api-key"

openai:
  api_key: "your-openai-api-key"  # BYOK for o3-pro, GPT-5
```

**For detailed configuration**, see `MODEL_CONFIGURATION.md`:
- Complete COMMAND_CONFIGS dictionary
- Retry logic configuration
- Token limits and thresholds
- Parameter filtering details
- Troubleshooting guide

---

## LLM Response Philosophy

### CRITICAL PRINCIPLE: Minimize Local Parsing Through Better Prompt Engineering

**Core Guidelines** (from CLAUDE.md):

1. **Prompt Engineering First**: Request structured formats (JSON, YAML) instead of parsing text
2. **Longer Structured Output > Multiple Calls**: Prefer comprehensive structured responses
3. **No Fallback Parsing Logic**: Well-prompted LLMs return correctly formatted output
4. **Removal Over Addition**: Delete parsing code rather than adding more

**Current State**: ~200+ lines of regex/string manipulation (legacy)
**Target State**: Direct JSON/YAML responses with simple deserialization

**Policy**: Code must break instead of masking errors - no silent fallbacks

### YAML-Based Prompt Management

**All prompts externalized** to `litassist/prompts/*.yaml`:
- base.yaml - Australian law requirements
- processing.yaml - Draft, digest, counselnotes
- verification.yaml - Verification and CoVe
- strategies.yaml - Strategy command prompts
- lookup.yaml - Lookup and analysis
- And 9 more specialized files

**Access Pattern**: `PROMPTS.get("category.subcategory.key")`

**Benefits**:
- Version control for prompts
- Easy iteration without code changes
- Clear separation of logic and content
- Eliminates "prompt soup" anti-pattern

---

## Command-Specific Improvements

### 1. Lookup Command - Case Law Research

**Current Implementation** (October 2025):
- Model: `google/gemini-2.5-pro`
- Temperature: 0.2, top_p: 0.4
- Context: 1M tokens (using 900K for content)
- Single-stage pipeline

**Enhancement Opportunities**:

```python
# Enhanced system prompt with legal expertise
system_prompt = """You are an expert Australian legal researcher with deep knowledge of:
- Case law hierarchy (HC > FCA/FCAFC > State Supreme > District > Magistrates)
- Statutory interpretation principles (Acts Interpretation Act 1901 (Cth))
- Temporal relevance (prefer recent authorities unless foundational)
- Distinguishing ratio decidendi from obiter dicta

When analyzing cases:
1. Identify the legal principle established
2. Note any dissenting judgments
3. Check if subsequently overruled or distinguished
4. Extract relevant pinpoint paragraphs
5. Assess precedential value based on court hierarchy

Format citations as: Case Name [Year] Court Level Report (Judge Name at [para])
Example: Smith v Jones [2023] HCA 15; (2023) 412 ALR 1 (Gordon J at [45]-[47])"""
```

**Multi-pass refinement**:
- Initial research and analysis
- Review: What critical cases or statutes did I miss?
- Identify conflicting authorities and reconcile them
- Provide practical application guidance

**Status**: Partially implemented via prompts, could be enhanced

### 2. Digest Command - Document Analysis

**Current Implementation**:
- Model: `claude-sonnet-4.5`
- Modes: summary (temp 0.2) or issues (temp 0.2)
- No multi-stage refinement

**Enhancement Opportunities**:

**Issue-Spotting Framework**:
1. **Causes of Action**: Claims, elements, evidence, defences, prospects
2. **Procedural Issues**: Limitation periods, jurisdiction, standing
3. **Evidentiary Concerns**: Hearsay, privilege, authenticity
4. **Strategic Considerations**: Strengths/weaknesses (rated 1-10)
5. **Risk Assessment**: Costs, reputation, resources, ADR potential

**Admissions Extraction**:
- Direct admissions
- Implied concessions
- Inconsistent statements
- Failure to deny allegations

**Status**: Basic issue spotting implemented, could add structured framework

### 3. ExtractFacts Command - Structured Extraction

**Current Implementation**:
- Model: `claude-sonnet-4.5`
- Temperature: 0, top_p: 0.15
- Fixed 10-heading structure
- Mandatory verification

**Enhancement Opportunities**:

**Confidence Scoring**:
```python
enhanced_prompt = """Extract facts under these headings, with confidence scores:

For each fact extracted:
1. Quote the exact source text
2. Note page/paragraph reference
3. Assign confidence:
   - HIGH (explicitly stated)
   - MEDIUM (reasonably inferred)
   - LOW (possible but uncertain)
4. Flag any contradictions between sources
5. Note corroboration across multiple sources

Example:
**Key Events**:
- Contract signed on 1 March 2023 [HIGH confidence - page 3, para 2: "The parties executed the agreement on 1 March 2023"] [Corroborated: page 15, email confirmation]
- Breach occurred in April 2023 [MEDIUM confidence - page 8, para 5: "By April, deliveries had ceased"] [Contradiction: page 12 suggests May]
```

**Fact Categorization**:
- AGREED: Both parties accept
- DISPUTED: Contested by one party
- UNKNOWN: Not addressed by either party
- DOCUMENTARY: Supported by documents
- TESTIMONIAL: Based on witness statements

**Status**: Not implemented, HIGH VALUE opportunity

### 4. Brainstorm Command - Strategy Generation

**Current Implementation** (October 2025):
- Orthodox: Claude Sonnet 4.5 (temp 0.3)
- Unorthodox: Grok 4 (temp 0.9)
- Analysis: o3-pro (thinking_effort: high)
- Auto-verification for Grok

**Enhancement Opportunities**:

**Enhanced Structure for Each Strategy**:
1. **Legal Foundation**: Specific statute/case supporting approach
2. **Procedural Path**: Step-by-step implementation
3. **Success Factors**: What must be true for this to work
4. **Risk Assessment**: What could go wrong (rate 1-10)
5. **Cost Estimate**: Rough scale ($ to $$$$$)
6. **Timeline**: Realistic timeframe to resolution
7. **Precedent**: Has this worked before? Cite examples
8. **Resource Requirements**: Expertise/evidence needed

**Adversarial Testing**:
```python
adversarial_prompt = """
Now attack each strategy from the opponent's perspective:
1. What counter-strategies would neutralize this?
2. What evidence would defeat it?
3. What procedural blocks could they raise?
4. How would you defend against these attacks?
"""
```

**Contingency Planning**:
- Plan B if primary approach fails
- Early warning signs of failure
- Pivot points for changing strategy
- Preservation of alternative options

**Status**: Basic structure implemented, adversarial testing not automated

### 5. Strategy Command - Strategic Planning

**Current Implementation**:
- Model: `claude-sonnet-4.5`
- Temperature: 0.2, top_p: 0.8
- Multi-stage: options → steps → documents
- Simple probability percentages

**Enhancement Opportunities**:

**Structured Probability Methodology**:
```python
probability_prompt = """Calculate success probability using structured methodology:

**Base Rate Analysis** (Starting point):
- Historical success rate for this claim type: X%
- In this jurisdiction: Y%
- Before this judge/tribunal: Z%

**Adjustments:**
1. **Evidentiary Strength** (+/-20%):
   - Documentary evidence quality: +5-10%
   - Witness credibility issues: +/-10%
   - Expert opinion support: +5-10%
   - Gaps in evidence: -5-15%

2. **Legal Precedent** (+/-20%):
   - Direct binding authority: +15-20%
   - Persuasive analogous cases: +5-10%
   - Distinguishable contrary authority: -10-15%
   - Novel point of law: -5-10%

3. **Procedural Factors** (+/-15%):
   - Favorable jurisdiction: +5-10%
   - Experienced judge in area: +5%
   - Limitation period issues: -5-15%
   - Procedural complexity: -5-10%

4. **Resource Factors** (+/-15%):
   - Resource advantage: +5-10%
   - Quality of representation: +/-10%
   - Ability to run full trial: +/-5%

Show calculation transparently:
Base rate: 40%
+ Strong documentary evidence: +8%
+ Direct High Court authority: +15%
- Complex procedure: -5%
+ Senior counsel engaged: +7%
= Total: 65% probability of success

**Confidence interval**: 55-75% (accounting for unknowns)"""
```

**Decision Tree Analysis**:
```
1. Preliminary objections → 80% survive
   ↓
2. Discovery disputes → 70% favorable outcome
   ↓
3. Summary judgment → 60% survive
   ↓
4. Trial on merits → 55% success
   ↓
Overall path probability: 0.8 × 0.7 × 0.6 × 0.55 = 18.5%

Alternative paths:
- Early settlement: 40% chance at 70% of claim
- Mediation success: 30% chance at 60% of claim
```

**Status**: Basic probability implemented, structured methodology not implemented

### 6. Draft Command - Document Generation

**Current Implementation**:
- Model: `o3-pro`
- thinking_effort: high, verbosity: high
- Basic RAG with context
- Dynamic prompts

**Enhancement Opportunities**:

**Style Requirements**:
1. **Structure**: Relief sought in opening, numbered paragraphs, clear hierarchy
2. **Language**: Active voice, present tense, avoid nominalizations, max 25 words
3. **Citations**: Full case names first, short form thereafter, pinpoint paragraphs
4. **Precision**: Every assertion → evidence, every proposition → authority

**Multi-Stage Refinement**:
1. Pass 1: Legal accuracy and completeness
2. Pass 2: Persuasiveness and flow
3. Pass 3: Conciseness and clarity
4. Pass 4: Technical compliance

**Legal Reasoning Validation**:
- Major premise (legal principle) → stated with authority
- Minor premise (facts) → referenced to evidence
- Application → logical connection shown
- Conclusion → follows necessarily
- Alternative arguments → addressed

**Status**: Basic drafting implemented, multi-stage refinement not automated

### 7. Verification System

**Current Implementation** (October 2025):
- verification-light: Sonnet 4.5 (spelling/terminology)
- verification: GPT-5 (standard verification)
- verification-heavy: GPT-5 Pro (critical tasks <1% hallucination)
- Chain of Verification (CoVe): 4-stage pipeline

**Enhancement Opportunities**:

**Comprehensive Legal Review**:
1. **Legal Reasoning Audit**: Logical validity, hidden assumptions, alternative interpretations
2. **Authority Validation**: Citations verified, subsequent consideration, current sections
3. **Factual Accuracy**: Every assertion traced, contradictions reconciled
4. **Strategic Review**: Advances interests, no unintended admissions, preserves appeals
5. **Compliance Audit**: Court rules, page limits, certifications, deadlines
6. **Risk Assessment**: Rate each section 1-10 for soundness/support/strategy/clarity

**Multi-Perspective Review**:
- **Judge**: Is this clear and convincing?
- **Opponent**: Where would I attack?
- **Client**: Does this achieve my goals?

**Status**: CoVe partially implements this, could add multi-perspective explicitly

---

## Future Model Opportunities

### When Next-Generation Models Arrive

**Note**: The models below DO NOT EXIST as of October 2025. These are forward-looking recommendations for when they become available.

#### 1. OpenAI o4 Family (Future)

**Potential Applications**:
- `strategy-analysis`: Upgrade from o3-pro → o4-pro for transparent trace summaries
- `draft`: Consider o4-mini for faster latency while maintaining reasoning quality

**Prerequisites**:
- OpenRouter support confirmed
- Benchmarks show improvement over o3-pro
- Cost/quality tradeoff favorable

**Parameter Changes Needed**:
- Update pattern matching for `openai/o4` family
- Add support for trace summary channel
- Test `max_completion_tokens` requirements

#### 2. Claude 4.2 Family (Future)

**Potential Applications**:
- `strategy`: Upgrade from Sonnet 4.5 → Sonnet 4.2 (200K context, improved legal citation)
- `verification-heavy`: Consider Opus 4.2 for highest-stakes tasks

**Prerequisites**:
- Confirm tool calling works on OpenRouter
- Verify legal citation recall improvement
- Test extended thinking mode

**Parameter Changes Needed**:
- Pattern matcher already supports `claude-` family
- No code changes required, just config updates

#### 3. GPT-5.1 (Future)

**Potential Applications**:
- `verification-critical`: New tier with structured JSON schema output
- Hallucination reduction specifically for legal citations

**Prerequisites**:
- Confirm `response_format={"type": "json_schema"}` support on OpenRouter
- Benchmark hallucination rate vs GPT-5
- Test deterministic output quality

**Implementation**:
```python
"verification-critical": {
    "model": "openai/gpt-5.1",
    "temperature": 0.2,
    "top_p": 0.3,
    "response_format": {"type": "json_schema"},
    "thinking_effort": "max",
}
```

#### 4. Grok 4 Turbo (Future)

**Potential Applications**:
- Secondary verification cross-check
- Contradiction detection in verification pipeline

**Prerequisites**:
- OpenRouter support confirmed
- Benchmark verification accuracy
- Cost/benefit analysis

#### 5. Gemini 2.5 Flash Thinking (Available)

**Current Opportunity**:
- Cost-efficient alternative for `lookup` command
- Half the cost of Gemini 2.5 Pro
- Same retrieval-augmented reasoning

**Implementation Approach**:
```python
# Option 1: Add config toggle
"lookup.model_override": "google/gemini-2.5-flash-thinking"

# Option 2: Add separate command
"lookup-efficient": {
    "model": "google/gemini-2.5-flash-thinking",
    "temperature": 0.2,
    "top_p": 0.4,
    "thinking_effort": "low",
}
```

**Action Required**: A/B test vs Gemini 2.5 Pro for quality comparison

#### 6. Meta Llama 4.1 (Future - On-Prem Option)

**Potential Applications**:
- Self-hosted deployments for cost-sensitive firms
- `extractfacts`: `meta/llama-4.1-law` (legal summarization tuning)
- On-premises GPU cluster processing

**Prerequisites**:
- Llama 4.1-128k available
- Legal fine-tuning variant released
- Performance benchmarks acceptable

---

## Global Improvements

### 1. Legal Reasoning Framework

**Apply across all analytical commands**:

```python
legal_reasoning_framework = """
Apply structured legal reasoning:

1. **Issue Identification**
   - Primary legal question
   - Sub-issues requiring determination
   - Threshold questions

2. **Rule Statement**
   - Applicable legislation (with sections)
   - Binding precedents (with hierarchy)
   - Persuasive authorities
   - Legal principles/maxims

3. **Application to Facts**
   - Step-by-step application
   - Each element addressed
   - Counter-arguments considered
   - Factual distinctions noted

4. **Conclusion**
   - Clear statement of outcome
   - Confidence level
   - Assumptions/caveats
   - Next steps

Show your reasoning transparently at each step."""
```

**Status**: Partially implemented in prompts, not enforced systematically

### 2. Multi-Model Consensus (Future)

**For critical tasks** (final drafts, strategy recommendations):

```python
def multi_model_consensus(prompt, task_type):
    """Get consensus from multiple models for critical tasks."""

    models = {
        "analytical": "openai/gpt-5",
        "creative": "anthropic/claude-sonnet-4.5",
        "precise": "google/gemini-2.5-pro"
    }

    results = {}
    for perspective, model in models.items():
        results[perspective] = generate(model, prompt)

    synthesis_prompt = f"""
    Three senior counsel have provided {task_type}:

    Analytical perspective: {results['analytical']}
    Creative perspective: {results['creative']}
    Precise perspective: {results['precise']}

    Synthesize the best elements of each:
    1. Identify points of agreement
    2. Reconcile disagreements using best legal reasoning
    3. Combine unique valuable insights from each
    4. Create final version incorporating strengths of all
    """

    return generate("openai/gpt-5", synthesis_prompt)
```

**Status**: Not implemented, HIGH COST, use only for critical tasks

### 3. Iterative Improvement Loop (Future)

```python
def iterative_improvement(initial_output, task_type):
    """Iteratively improve output through targeted questioning."""

    improvement_rounds = [
        "What are the three weakest points in the above analysis?",
        "How would experienced opposing counsel attack this?",
        "What critical authorities or arguments are missing?",
        "Where could the reasoning be clearer or more persuasive?",
        "What practical implementation challenges exist?"
    ]

    current = initial_output
    for round_num, question in enumerate(improvement_rounds):
        prompt = f"""
        Current {task_type}:
        {current}

        {question}

        Provide specific improvements addressing these issues.
        """
        current = generate_improvement(prompt)

    return current
```

**Status**: Not implemented, EXPERIMENTAL, test before production use

### 4. Confidence Scoring System

```python
confidence_scoring = """
For each conclusion or recommendation, provide:

**Confidence Score** (0-100%):
- 90-100%: Settled law, clear facts, strong precedent
- 70-89%: Good authority, reasonable inference
- 50-69%: Arguable position, some uncertainty
- 30-49%: Novel argument, significant risks
- 0-29%: Speculative, against weight of authority

**Factors affecting confidence:**
- Quality of authorities cited
- Directness of factual support
- Consistency with established principle
- Jurisdictional variations
- Temporal relevance

**Uncertainty sources:**
- Missing facts (list specifically)
- Unsettled law (cite conflicting authorities)
- Discretionary factors
- Procedural variables
"""
```

**Status**: Could be added to prompts, not currently implemented

### 5. Australian Legal Context Enhancement

```python
australian_legal_context = """
Always consider Australian-specific factors:

1. **Uniform legislation variations** between states
2. **Federal/State jurisdictional complexity**
3. **Costs jurisdiction** and scale of costs
4. **Implied undertaking** in discovery
5. **Calderbank offers** and costs consequences
6. **Model litigant obligations** for government
7. **Proportionality** in civil procedure
8. **Overriding purpose** of just, quick, cheap resolution

Reference relevant practice directions and court guides.
"""
```

**Status**: Partially implemented in base.yaml, could be enhanced

---

## Implementation History

### October 2025 Model Upgrade ✅ FULLY IMPLEMENTED

**Date**: October 12, 2025
**Analysis Date**: October 11, 2025
**Status**: ✅ Complete

**Key Changes**:
1. ✅ **Claude Opus 4.1 → Claude Sonnet 4.5** (14 commands)
   - 80% cost reduction
   - Superior legal reasoning (state-of-the-art for litigation)
   - Commands: strategy, brainstorm-orthodox, digest-issues, verification

2. ✅ **Claude Sonnet 4 → Claude Sonnet 4.5** (6 commands)
   - Improved reasoning and domain knowledge
   - Commands: extractfacts, digest-summary, caseplan, cove stages

3. ✅ **New GPT-5 Pro** (3 commands)
   - <1% hallucination rate for critical verification
   - Commands: verification-heavy, cove-final

4. ✅ **New GPT-5** (2 commands)
   - 1.4-1.6% hallucination rate
   - Commands: verification, cove-answers

5. ✅ **Grok 3 → Grok 4** (1 command)
   - Unorthodox brainstorming upgrade

**Results**:
- 40-50% overall cost reduction
- Improved legal reasoning quality
- Maintained <2% hallucination rate on verification
- 380 unit tests passing

**Files Modified**:
- `litassist/llm/client.py` - Core configuration
- Test files updated for new models
- Documentation updated

**Reference**: See `claude_llm_model_recommendations_oct_2025.md` for full analysis

### June-July 2025 Enhancements ✅ IMPLEMENTED

**Implemented**:
- CasePlan prompt engineering (July 2025)
- Comprehensive post-hoc verification (`verify` command)
- Research-informed brainstorming (`--research` option)
- Selective regeneration for citation issues
- Multi-section reasoning traces
- Centralized config.yaml
- YAML-based prompt management
- LLM Response Parsing Audit

**Planned (Not Yet Implemented)**:
- IRAC/MIRAT enforcement
- Multi-model consensus
- Confidence scoring
- Cost-tracking
- Systematic elimination of parsing code

---

## Cost-Benefit Analysis

### Current State (October 2025)

**Average Cost Per Command**:
- Simple commands (lookup, extractfacts): $0.10-0.30
- Medium commands (digest, strategy): $0.30-0.80
- Complex commands (draft, barbrief): $0.80-2.00
- Verification: $0.20-1.50 depending on level

**Quality Score**: 8-9/10 (professional-grade outputs)

### With Full Improvements

**Estimated Cost Per Command**:
- Simple: $0.20-0.50 (2x increase for confidence scoring)
- Medium: $0.80-1.50 (2-3x for multi-stage refinement)
- Complex: $2.00-5.00 (3-4x for iterative improvement)
- Verification: Same (already comprehensive)

**Quality Score**: 9.5/10 (senior barrister quality)

### Value Proposition

**Benefits**:
- 30-50% improvement in output quality
- Reduced revision cycles (saves billable time)
- Better risk identification (reduces malpractice exposure)
- More defensible recommendations (client protection)
- Competitive advantage (superior AI legal assistance)

**When to Implement Full Improvements**:
- High-stakes litigation (>$500K value)
- Complex legal analysis (novel issues)
- Client willing to pay premium for quality
- Professional liability concerns paramount

**When to Use Current Implementation**:
- Standard matters
- Cost-sensitive clients
- Routine document processing
- Sufficient quality for purpose

---

## Configuration Best Practices

### 1. Runtime Model Selection (Future Enhancement)

**Not Yet Implemented - Recommended**:

```yaml
# config.yaml
models:
  commands:
    strategy: "anthropic/claude-sonnet-4.5"  # Override default
    verification-heavy: "openai/gpt-5.1"     # When available
    lookup: "google/gemini-2.5-flash-thinking"  # Cost optimization
```

**Benefits**:
- Experiment with new models without code changes
- Quick rollback to previous configurations
- Environment-specific model selection

### 2. Verification Ensembles

**Current**: Single model per verification level
**Future**: Mix-and-match verification models

```yaml
verification:
  light: ["anthropic/claude-sonnet-4.5"]
  standard: ["openai/gpt-5"]
  heavy: ["openai/gpt-5-pro", "x-ai/grok-4-turbo"]  # Ensemble
```

### 3. Benchmark and Guardrails

**Recommended Nightly Tests**:
- Run each model against legal benchmark set
- Store tokens used, verification results
- Track per-model hallucination statistics
- Automatic rollback on quality degradation

**Not Yet Implemented**

---

## Related Documentation

- **MODEL_CONFIGURATION.md** - Complete parameter details and current configuration
- **ARCHITECTURE_ANALYSIS_2025.md** - Overall architecture including LLM strategy
- **CLAUDE.md** - Development guidelines including prompt management policy
- **VERIFICATION_SYSTEM_COMPREHENSIVE.md** - Verification chain architecture
- **LLM_PARSING_AUDIT_REPORT.md** - Analysis of parsing patterns to eliminate

---

## Recommendations Summary

### Immediate Actions (October 2025)

✅ **COMPLETED**: October 2025 model upgrade fully implemented

### Short-Term (Next 3 Months)

1. **Test Gemini 2.5 Flash Thinking** for lookup cost optimization
2. **Add confidence scoring** to extractfacts command (HIGH VALUE)
3. **Implement structured probability** methodology for strategy
4. **Add fact categorization** (AGREED/DISPUTED/UNKNOWN) to extractfacts

### Medium-Term (3-6 Months)

1. **Runtime model configuration** via config.yaml
2. **Multi-perspective review** (judge/opponent/client) in verification
3. **Adversarial testing** automation for brainstorm
4. **Benchmark framework** for model performance tracking

### Long-Term (6-12 Months)

1. **Multi-model consensus** for critical tasks (when cost justified)
2. **Iterative improvement loops** for complex analysis
3. **Migrate to future models** (o4, Claude 4.2, GPT-5.1) when available
4. **Systematic parsing elimination** through structured outputs

---

## Conclusion

LitAssist has achieved **professional-grade legal AI assistance** through:

1. **Strategic Model Selection**: Three-tier quality strategy balances cost and accuracy
2. **Prompt Engineering Excellence**: YAML-based externalization enables rapid iteration
3. **No-Parsing Philosophy**: Trust LLMs to format correctly, eliminate brittle parsing
4. **Australian Legal Focus**: Deep domain knowledge in all prompts and configurations
5. **Professional Liability Awareness**: Sub-2% hallucination on critical tasks

**Key Architectural Wins**:
- Claude Sonnet 4.5 for legal reasoning (state-of-the-art litigation performance)
- GPT-5 family for verification (1.4-1.6% hallucination rate)
- OpenRouter routing (unified multi-provider management)
- Dynamic parameter filtering (model family awareness)

**Future Opportunities**:
- Runtime model configuration (flexibility without code changes)
- Confidence scoring (transparency in uncertainty)
- Multi-model consensus (quality ceiling for critical tasks)
- Structured outputs (eliminate remaining parsing code)

The October 2025 upgrade represents a **major architectural milestone**, achieving 40-50% cost reduction while improving quality through strategic use of next-generation models.

---

**Document Owners**: Claude (analysis), Project Team (implementation)
**Created**: Merged from three source documents (October 23, 2025)
**Sources**:
- LLM_IMPROVEMENTS.md (June 2025, updated Oct 22)
- claude_llm_model_recommendations_oct_2025.md (Oct 12 - IMPLEMENTED)
- llm_model_refresh.md (Oct 11 - forward-looking)
