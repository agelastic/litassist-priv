# LitAssist LLM Improvements Analysis

## Status Update (June 2025)

**Implemented:**
- **CasePlan prompt engineering (July 2025):** New caseplan.yaml prompt enforces rationale for every phase, explicit command coverage analysis, focus area prioritization, and structured output. Minimizes local parsing in line with CLAUDE.md and memory bank principles.
- Comprehensive post-hoc verification (`verify` command): Performs citation accuracy, legal soundness, and reasoning transparency checks on generated documents. Each check writes a separate timestamped report to outputs/. All steps use the existing logging infrastructure and minimal console output.
- Research-informed brainstorming: `brainstorm` command supports `--research` option to inject lookup report(s) into the orthodox strategies prompt, enabling research-grounded strategy generation. All prompt logic is managed in YAML; no hardcoded LLM templates.
- Option B (selective regeneration/discard for citation issues in brainstorm/strategy)
- Multi-section reasoning traces (brainstorm)
- Strict two-phase citation verification (AustLII backend)
- Centralized config.yaml for all settings
- Model selection and BYOK requirements for advanced commands
- Clean CLI output, output timestamping, and professional summaries
- Comprehensive logging and timing for all operations
- LLM Response Parsing Audit: Comprehensive analysis documenting all parsing patterns for systematic elimination (see LLM_PARSING_AUDIT_REPORT.md)

**Planned:**
- IRAC/MIRAT enforcement
- Multi-model consensus and iterative improvement loops
- Confidence scoring and advanced QA loops
- Cost-tracking and workflow compound commands
- Systematic elimination of LLM response parsing through structured output requests (JSON/YAML)

## LLM Response Parsing Philosophy

**CRITICAL PRINCIPLE: Minimize Local Parsing Through Better Prompt Engineering**

The litassist codebase contains extensive parsing of LLM responses that should be eliminated. A comprehensive audit (see LLM_PARSING_AUDIT_REPORT.md) identified 15+ major parsing patterns across 8 core files.

**Core Guidelines:**
1. **Prompt Engineering First**: Request structured formats (JSON, YAML) instead of parsing text
2. **Longer Structured Output > Multiple Calls**: Prefer comprehensive structured responses
3. **No Fallback Parsing Logic**: Well-prompted LLMs return correctly formatted output
4. **Removal Over Addition**: Delete parsing code rather than adding more

**Current State**: 200+ lines of regex patterns, string manipulation, and complex parsing
**Target State**: Direct JSON/YAML responses with simple deserialization
**Benefits**: Reduced complexity, improved reliability, easier maintenance

This document analyzes all LLM prompts, settings, and processing in LitAssist with recommendations for improvements that prioritize quality over cost.

## Executive Summary

LitAssist currently uses 6 different LLM integrations across its commands. While functional, there are significant opportunities to enhance legal reasoning, accuracy, and output quality by implementing more sophisticated prompting techniques, multi-stage refinement, and validation systems.

## Current LLM Architecture

### Models and Their Roles
- **Google Gemini 2.5 Pro**: Case law research (fast, web-aware)
- **Claude 3 Sonnet**: Document processing (reliable extraction)
- **Grok 3 Beta**: Creative strategy generation (high creativity)
- **GPT-4o**: Strategic planning and drafting (balanced capabilities)
- **Verify Command**: Uses multiple models for post-hoc verification (citation, legal soundness, reasoning trace) on generated documents.

### Temperature Settings Philosophy
- **0.0**: Factual tasks (extraction, summaries)
- **0.2-0.5**: Analytical tasks (strategy, drafting)
- **0.9**: Creative tasks (brainstorming)

## Command-by-Command Analysis and Improvements

### 1. Lookup Command - Case Law Research

**Current State:**
- Model: `google/gemini-2.5-pro-preview`
- Temperature: 0 (IRAC) or 0.5 (broad)
- Basic prompt: Question + found links
- Simple citation guard retry

**Improvement Recommendations:**

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

# Multi-pass refinement
refinement_passes = [
    "Initial research and analysis",
    "Review the above. What critical cases or statutes did I miss?",
    "Identify any conflicting authorities and reconcile them",
    "Provide practical application guidance for the practitioner"
]
```

**Benefits:**
- More thorough case analysis
- Better understanding of precedential value
- Conflict resolution between authorities
- Practical guidance for implementation

### 2. Digest Command - Document Analysis

**Current State:**
- Model: `anthropic/claude-3-sonnet`
- Temperature: 0 (summary) or 0.2 (issues)
- Basic chronological summary or issue spotting
- No verification

**Improvement Recommendations:**

```python
# Enhanced issue-spotting with structured analysis
issues_prompt = """Identify legal issues using the following framework:

1. **Causes of Action**: What claims could be brought?
   - Elements required for each cause
   - Evidence supporting/negating each element
   - Likely defences
   - Prospects of success (with reasoning)

2. **Procedural Issues**: 
   - Limitation periods (calculate specific dates)
   - Jurisdictional questions
   - Standing/capacity issues
   - Relevant court/tribunal

3. **Evidentiary Concerns**:
   - Hearsay issues (identify specific statements)
   - Privilege claims (legal professional, without prejudice)
   - Document authenticity questions
   - Burden of proof considerations

4. **Strategic Considerations**:
   - Strengths (rate 1-10 with justification)
   - Weaknesses (rate 1-10 with justification)
   - Missing evidence needed
   - Settlement prospects

5. **Risk Assessment**:
   - Costs exposure
   - Reputational considerations
   - Time/resource requirements
   - Alternative dispute resolution potential

For each issue, cite the specific page/paragraph from the source document."""

# Add extraction of key admissions/concessions
admissions_prompt = """
Extract any admissions or concessions that could be used against each party:
1. Direct admissions
2. Implied concessions
3. Inconsistent statements
4. Failure to deny allegations
"""
```

**Benefits:**
- Comprehensive legal analysis
- Better risk assessment
- Strategic insights
- Evidence-based ratings

### 3. ExtractFacts Command - Structured Extraction

**Current State:**
- Model: `anthropic/claude-3-sonnet`
- Temperature: 0, top_p: 0.15
- Fixed 10-heading structure
- Forced verification

**Improvement Recommendations:**

```python
# Add confidence scoring and source tracking
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

**Fact Verification Stage:**
After extraction, validate:
1. Internal consistency of timeline
2. Logical consistency of events
3. Missing critical facts marked "To be obtained"
4. Assumptions requiring validation
5. Gaps in evidence chain"""

# Add fact categorization
fact_categories = """
Categorize each fact as:
- AGREED: Both parties accept
- DISPUTED: Contested by one party
- UNKNOWN: Not addressed by either party
- DOCUMENTARY: Supported by documents
- TESTIMONIAL: Based on witness statements
"""
```

**Benefits:**
- Transparency in fact confidence
- Better evidence assessment
- Identification of weak points
- Clear action items for missing facts

### 4. Brainstorm Command - Strategy Generation

**Current State:**
- Model: `x-ai/grok-3`
- Temperature: 0.9, top_p: 0.95
- Orthodox/Unorthodox/Most Likely structure
- Auto-verification for Grok

**Improvement Recommendations:**

```python
# Enhanced creative reasoning with practical grounding
system_prompt = """You are a senior barrister brainstorming with junior counsel. Think creatively but ground all strategies in legal principle.

For each strategy, provide:
1. **Legal Foundation**: Specific statute/case supporting this approach
2. **Procedural Path**: Step-by-step implementation
3. **Success Factors**: What must be true for this to work
4. **Risk Assessment**: What could go wrong (rate 1-10)
5. **Cost Estimate**: Rough scale ($ to $$$$$)
6. **Timeline**: Realistic timeframe to resolution
7. **Precedent**: Has this worked before? Cite examples
8. **Resource Requirements**: Expertise/evidence needed

For unorthodox strategies:
- Acknowledge which boundaries you're pushing
- Cite any analogous successful cases
- Rate ethics risk (1-10)
- Suggest safeguards
- Consider reputational impact

End each strategy with a "Devil's Advocate" critique."""

# Add adversarial testing
adversarial_prompt = """
Now attack each strategy from the opponent's perspective:
1. What counter-strategies would neutralize this?
2. What evidence would defeat it?
3. What procedural blocks could they raise?
4. How would you defend against these attacks?
"""

# Add contingency planning
contingency_prompt = """
For each strategy, provide:
- Plan B if the primary approach fails
- Early warning signs of failure
- Pivot points for changing strategy
- Preservation of alternative options
"""
```

**Benefits:**
- More practical, implementable strategies
- Better risk awareness
- Adversarial testing built-in
- Contingency planning included

### 5. Strategy Command - Strategic Planning

**Current State:**
- Model: `openai/gpt-4o`
- Temperature: 0.2
- Simple probability percentages
- Multi-stage: options → steps → documents

**Improvement Recommendations:**

```python
# Enhanced probability assessment with methodology
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

# Add decision tree analysis
decision_tree_prompt = """
Map critical decision points:

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
"""

# Enhanced document generation
document_enhancement = """
For each document type, include:
1. Jurisdiction-specific requirements
2. Recent practice directions compliance
3. Page/paragraph limits
4. Required schedules/annexures
5. Certification requirements
6. Filing deadlines calculated from today
"""
```

**Benefits:**
- Transparent probability methodology
- Better client advice
- Risk-adjusted strategy selection
- Compliance with court requirements

### 6. Draft Command - Document Generation

**Current State:**
- Model: `openai/gpt-4o`
- Temperature: 0.5, presence/frequency penalties
- Basic RAG with context
- Dynamic prompts based on input

**Improvement Recommendations:**

```python
# Enhanced drafting with style guide and legal reasoning
system_prompt = """You are a senior barrister drafting for Australian courts.

**Style Requirements:**
1. **Structure**: 
   - Relief sought in opening paragraph
   - Numbered paragraphs throughout
   - Clear heading hierarchy
   - Logical flow between sections

2. **Language**:
   - Active voice preferred
   - Present tense for continuing states
   - "The applicant submits" not "It is submitted"
   - Avoid nominalizations
   - Short sentences (max 25 words ideal)

3. **Citations**:
   - Full case names on first reference
   - Short form thereafter with [year] identifier
   - Pinpoint to specific paragraphs
   - Legislative references with full title first time

4. **Precision Requirements**:
   □ Every factual assertion → evidence reference
   □ Every legal proposition → authority
   □ Every conclusion → reasoning shown
   □ Consistent defined terms
   □ No ambiguous pronouns
   □ No assumptions beyond pleaded facts

**Include footnotes for:**
- Case citations with pinpoints
- Legislative sections
- Evidence references (affidavit para/exhibit)
- Cross-references to pleadings"""

# Multi-stage refinement process
refinement_stages = [
    {
        "pass": 1,
        "focus": "Legal accuracy and completeness",
        "prompt": "Draft focusing on getting all legal points correct"
    },
    {
        "pass": 2,
        "focus": "Persuasiveness and flow",
        "prompt": "Enhance persuasiveness, improve transitions, strengthen key arguments"
    },
    {
        "pass": 3,
        "focus": "Conciseness and clarity",
        "prompt": "Remove redundancy, tighten language, clarify ambiguities"
    },
    {
        "pass": 4,
        "focus": "Technical compliance",
        "prompt": "Verify all citations, check formatting, ensure rule compliance"
    }
]

# Add legal reasoning validation
reasoning_validation = """
For each submission, verify:
1. Major premise (legal principle) → stated with authority
2. Minor premise (facts) → referenced to evidence  
3. Application → logical connection shown
4. Conclusion → follows necessarily
5. Alternative arguments → addressed
"""
```

**Benefits:**
- Professional drafting quality
- Better persuasiveness
- Reduced revision cycles
- Court-compliant output

### 7. Verification System Enhancements

**Current State:**
- Three levels: light/medium/heavy
- Basic citation checking
- Auto-verification for some commands

**Improvement Recommendations:**

```python
# Comprehensive legal review system
heavy_verification_prompt = """
Conduct senior counsel review:

**1. Legal Reasoning Audit**:
- Logical validity of each argument
- Hidden assumptions identified
- Alternative interpretations considered
- Syllogistic structure verified
- Fallacies identified

**2. Authority Validation**:
- Case citations verified against AustLII
- Check for subsequent judicial consideration
- Statutory sections current as of date
- No superseded authorities relied upon
- Hierarchy of authority respected

**3. Factual Accuracy**:
- Every assertion traced to evidence
- No facts outside the record
- Inferences clearly marked
- Contradictions reconciled
- Chronology verified

**4. Strategic Review**:
- Advances client's best interests
- No unintended admissions
- Preserves appeal points
- Consistent with case theory
- No doors unnecessarily closed

**5. Compliance Audit**:
- Court rules compliance verified
- Page/word limits checked
- Required certifications present
- Filing deadlines calculated
- Service requirements noted

**6. Risk Assessment**:
Rate each section 1-10 for:
- Legal soundness
- Factual support
- Strategic wisdom
- Clarity of expression

Explain any rating below 8 and suggest improvements."""

# Add multi-perspective review
perspective_review = """
Review from three perspectives:
1. **Judge**: Is this clear and convincing?
2. **Opponent**: Where would I attack?
3. **Client**: Does this achieve my goals?
"""
```

**Benefits:**
- Comprehensive quality assurance
- Multiple perspective validation
- Risk identification
- Actionable improvement suggestions

## Global Improvements

### 1. Legal Reasoning Framework

Implement across all analytical commands:

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

### 2. Multi-Model Consensus

For critical tasks (final drafts, strategy recommendations):

```python
def multi_model_consensus(prompt, task_type):
    """Get consensus from multiple models for critical tasks."""
    
    models = {
        "analytical": "openai/gpt-4o",
        "creative": "anthropic/claude-3-opus", 
        "precise": "google/gemini-ultra"
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
    
    return generate("openai/gpt-4o", synthesis_prompt)
```

### 3. Iterative Improvement Loop

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

## Implementation Recommendations

### Phase 1: High-Impact, Low-Complexity (1-2 weeks)
1. Enhanced prompts for each command
2. Legal reasoning framework
3. Confidence scoring
4. Australian legal context

### Phase 2: Medium-Complexity (2-4 weeks)
1. Multi-stage refinement
2. Adversarial testing
3. Decision tree analysis
4. Enhanced verification

### Phase 3: High-Complexity (4-8 weeks)
1. Multi-model consensus
2. Iterative improvement loops
3. Full legal reasoning traces
4. Comprehensive review system

## Cost-Benefit Analysis

### Current State
- Average tokens per command: 2,000-4,000
- Cost per command: $0.10-0.40
- Quality score: 7/10

### With Improvements
- Average tokens per command: 8,000-15,000
- Cost per command: $0.40-1.50
- Quality score: 9/10
- Time increase: 2-3x

### Value Proposition
- 30-50% improvement in output quality
- Reduced revision cycles
- Better risk identification
- More defensible recommendations
- Professional-grade outputs

## Conclusion

These improvements would transform LitAssist from a good legal AI assistant into an exceptional one that reasons and writes like a senior barrister. The key is implementing improvements progressively, starting with high-impact prompt enhancements and building toward more sophisticated multi-model and iterative systems.

The investment in better prompting and processing would pay dividends in:
- Reduced malpractice risk
- Better client outcomes
- Time saved on revisions
- Competitive advantage
- Professional credibility
