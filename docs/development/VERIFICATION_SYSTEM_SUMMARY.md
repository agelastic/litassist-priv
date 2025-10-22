# LitAssist Verification System - Executive Summary
*Last Updated: 2025-10-14 - October 2025 Model Upgrade*

## Quick Reference

### Two Verification Pathways

1. **Standard Verification** (Default)
   - 3 stages: Pattern → Database → LLM
   - Single model for verification
   - Inline corrections
   - ~5-10 seconds, ~5-10K tokens

2. **Chain of Verification (CoVe)** (--cove flag)
   - 4 stages: Questions → Answers → Verify → Regenerate
   - 4 different models (one per stage)
   - Complete regeneration when issues found
   - ~15-30 seconds, ~20-40K tokens

### Command Usage Matrix

| Command | Standard Verify | CoVe Available | Default Behavior |
|---------|----------------|----------------|------------------|
| **extractfacts** | ✓ Always | ✓ via --cove | Standard (auto) |
| **strategy** | ✓ Always | ✓ via --cove | Standard (auto) |
| **draft** | ✓ Always | ✓ via --cove | Standard (auto) |
| **brainstorm** | ✓ Unorthodox only | ✗ | Auto for unorthodox |
| **verify** | ✓ Modular | ✓ via --cove | All types |
| **barbrief** | ✗ | ✓ via --cove | None |
| **counselnotes** | ✗ | ✓ via --cove | None |
| **lookup** | ✗ | ✗ | None |
| **digest** | ✗ | ✗ | None |

### Key Implementation Details

#### Standard Verification Pipeline
```python
# Automatic for high-risk commands
1. validate_citation_patterns()     # Offline, <100ms
2. verify_all_citations()           # Jade.io check, 1-2s/citation  
3. client.verify()                  # LLM correction, 3-5s
```

#### CoVe Implementation
```python
# Explicit via --cove flag
1. Generate questions about document
2. Answer questions (without seeing document)
3. Compare answers to document
4. Regenerate if inconsistencies found
```

### Citation Verification Layers

1. **Pattern Check**: Regex validation of format
2. **Database Check**: Real-time Jade.io verification
3. **Selective Regeneration**: Remove bad, regenerate affected sections

### Model Configuration (October 2025)

```yaml
# Three-tier strategy for optimal accuracy
verification: openai/gpt-5, temp=0.2 (1.4% hallucination rate)
verification-heavy: openai/gpt-5-pro, temp=0.2, thinking_effort=max (<1% hallucination)
verification-light: anthropic/claude-sonnet-4.5, temp=0.0 (spelling/terminology)
cove-questions: anthropic/claude-sonnet-4.5, temp=0.3
cove-answers: openai/gpt-5, temp=0.2
cove-verify: anthropic/claude-sonnet-4.5, temp=0.0
cove-final: openai/gpt-5-pro, temp=0.2, thinking_effort=max (premium regeneration)
```

### Important Architecture Decisions

1. **No Double Verification**: Commands use EITHER standard OR CoVe, never both
2. **Trust LLM Output**: No local parsing of LLM responses in CoVe
3. **Separate Models**: Each CoVe stage uses independent model to avoid bias
4. **Full Logging**: Complete prompts and responses logged for legal accountability
5. **No Fallbacks**: System fails if prompts missing (no hidden defaults)

### When to Use What

**Use Standard Verification:**
- Default for all high-risk commands
- Quick iterations during drafting
- Time-sensitive matters
- Good enough for most cases

**Use CoVe (--cove flag):**
- Final review before court filing
- Complex or novel legal arguments
- When standard verification finds issues
- High-stakes documents
- When you need maximum confidence

### Performance Trade-offs

| Metric | Standard | CoVe |
|--------|----------|------|
| **Time** | 5-10 sec | 15-30 sec |
| **Tokens** | 5-10K | 20-40K |
| **Cost** | ~$0.10 | ~$0.40 |
| **Accuracy** | High | Highest |
| **Models Used** | 1 | 4 |

### File Outputs

All verified content includes metadata:
```
Verification: Standard verification | Chain of Verification (CoVe)
CoVe Status: PASSED | REGENERATED
Model: [model used]
Issues Fixed: [if regenerated]
```

**NEW (2025)**: All AI critiques and verification feedback are now appended to output files:
```
================================================================================
AI CRITIQUE & VERIFICATION
================================================================================

## Citation Validation Issues
[Raw LLM feedback on citations]

## CoVe Stage 1: Questions Generated
[Verification questions]

## CoVe Stage 2: Independent Answers
[Answers to questions]

## CoVe Stage 3: Verification Analysis
[Analysis of inconsistencies]
```

### Key Files

- `verification_chain.py` - Orchestrates both verification types
- `llm.py` - LLM client with verify() method
- `citation_verify.py` - Real-time Jade.io checking
- `citation_patterns.py` - Offline pattern validation

### Logging

- Standard: `logs/verification_summary.json`
- CoVe: `logs/cove_[command]_summary.json`
- Full accountability with prompts, responses, models, tokens

## Critical Points

1. **CoVe replaces standard verification** - not additional
2. **High-risk commands always verify** - unless explicitly disabled
3. **Citation checking is multi-layered** - pattern, database, regeneration
4. **Each CoVe stage is independent** - different models, no shared context
5. **Regeneration is complete** - not patching, full document rewrite
6. **Australian law focused** - Jade.io primary, AustLII fallback
7. **All critiques now visible** - AI reasoning appended to output files (2025)

## Quick Decision Tree

```
Is this a high-risk command? (extractfacts/strategy/draft)
  ├─ Yes → Want maximum accuracy?
  │         ├─ Yes → Use --cove flag
  │         └─ No → Use default (standard verification)
  └─ No → Is it verify command?
           ├─ Yes → Choose what to verify (citations/soundness/reasoning/cove)
           └─ No → No verification needed
```