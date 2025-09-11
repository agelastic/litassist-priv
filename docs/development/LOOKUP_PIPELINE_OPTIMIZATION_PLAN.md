# Lookup Pipeline Optimization Plan

**Date**: 26 July 2025  
**Status**: Planned - Ready for Implementation  
**Priority**: P1 - Performance Enhancement

## Executive Summary

This document outlines the implementation plan for optimizing LitAssist's lookup command using a hybrid two-stage pipeline that balances speed, accuracy, and citation correctness. The plan leverages Google's Gemini 2.5 Pro for rapid retrieval and OpenAI's o4-mini-high for precision verification.

## Current vs Proposed Architecture

### Current Implementation
- **Single-stage**: Direct LLM call with Jade.io verification
- **Model**: Claude Sonnet 4 or equivalent
- **Speed**: Moderate (2-5 seconds typical)
- **Accuracy**: Good, but single-pass verification

### Proposed Implementation
- **Two-stage**: Gemini retrieval → o4-mini-high verification
- **Stage 1**: `google/gemini-2.5-pro-preview` (retrieval)
- **Stage 2**: `openai/o4-mini-high` (verification)
- **Speed**: Sub-second retrieval + <1s verification
- **Accuracy**: Dual-verification pipeline

## Detailed Implementation Plan

### Phase 1: Model Configuration Updates

#### New Model Configurations
```python
# LLMClientFactory additions
LOOKUP_RETRIEVAL_CONFIG = {
    "model": "google/gemini-2.5-pro-preview",
    "temperature": 0.1,
    "max_tokens": 8192,
    "top_p": 0.9
}

LOOKUP_VERIFICATION_CONFIG = {
    "model": "openai/o4-mini-high",
    "temperature": 0,
    "top_p": 0,
    "max_tokens": 4096
}
```

#### Configuration Strategy
- **New config option**: `lookup.pipeline_mode` (single|dual)
- **Default**: "dual" for new installations
- **Backward compatibility**: Existing configs maintain "single"
- **Environment override**: `LITASSIST_LOOKUP_MODE`

### Phase 2: Pipeline Flow Changes

#### Current Flow
```
User Query → Single LLM → Jade.io Verification → Output
```

#### New Flow
```
User Query → Gemini Retrieval → o4-mini-high Verification → Jade.io Final Check → Output
```

### Phase 3: Prompt Template Updates

#### Retrieval Prompt (Stage 1)
- **Purpose**: Comprehensive case law discovery
- **Focus**: Broad retrieval, preliminary citations
- **Model**: google/gemini-2.5-pro-preview

#### Verification Prompt (Stage 2)
- **Purpose**: Zero-hallucination citation rewriting
- **Focus**: Precision verification, accuracy
- **Model**: openai/o4-mini-high

### Phase 4: Implementation Details

#### Core Changes Required
1. **LLMClientFactory**: Add new model configurations
2. **lookup.py**: Implement two-stage pipeline
3. **lookup.yaml**: Update prompt templates for dual-stage
4. **config.py**: Add pipeline_mode configuration
5. **tests**: Add comprehensive test coverage

#### Error Handling
- **Fallback**: Single-stage if dual-stage fails
- **Retry logic**: Exponential backoff for API failures
- **Validation**: Enhanced citation verification pipeline

### Phase 5: Performance Optimizations

#### Speed Improvements
- **Parallel processing**: Overlap Gemini retrieval with o4-mini-high preparation
- **Caching**: Intermediate results for repeated queries
- **Streaming**: Real-time progress updates

#### Accuracy Enhancements
- **Dual verification**: o4-mini-high + Jade.io
- **Zero-temperature**: o4-mini-high for deterministic output
- **Citation validation**: Enhanced verification pipeline

## Testing Strategy

### Unit Tests
- Model configuration validation
- Pipeline flow correctness
- Error handling scenarios

### Integration Tests
- End-to-end lookup pipeline
- Performance benchmarks
- Citation accuracy validation

### A/B Testing
- Compare current vs new pipeline
- Measure speed/accuracy trade-offs
- User feedback collection

## Rollout Timeline

| Week | Activity | Status |
|------|----------|--------|
| 1 | Implement dual-stage pipeline | Planned |
| 2 | Internal testing | Planned |
| 3 | Beta user rollout | Planned |
| 4 | Full deployment | Planned |

## Risk Mitigation

### Technical Risks
- **API Rate Limits**: Implement exponential backoff
- **Model Availability**: Fallback configurations
- **Cost Monitoring**: Usage tracking and alerts

### Legal Risks
- **Citation Accuracy**: Enhanced verification pipeline
- **Australian Law**: Model validation
- **Professional Standards**: Compliance testing

## Success Metrics

### Performance Metrics
- **Speed**: <2 seconds total response time
- **Accuracy**: >99% citation correctness
- **Reliability**: <0.1% error rate

### User Experience
- **Perceived speed**: Sub-second initial response
- **Quality**: Zero hallucination reports
- **Satisfaction**: Positive user feedback

## Configuration Examples

### config.yaml Updates
```yaml
lookup:
  pipeline_mode: "dual"  # or "single"
  retrieval_model: "google/gemini-2.5-pro-preview"
  verification_model: "openai/o4-mini-high"
  enable_caching: true
  max_retries: 3
```

### Environment Variables
```bash
export LITASSIST_LOOKUP_MODE="dual"
export LITASSIST_LOOKUP_RETRIEVAL_MODEL="google/gemini-2.5-pro-preview"
export LITASSIST_LOOKUP_VERIFICATION_MODEL="openai/o4-mini-high"
```

## Dependencies

### Required Models
- `google/gemini-2.5-pro-preview` (via OpenRouter)
- `openai/o4-mini-high` (via OpenRouter)

### Required Updates
- LLMClientFactory model registry
- lookup.py pipeline implementation
- lookup.yaml prompt templates
- Configuration schema updates
- Test suite expansion

## Next Steps

1. **Review and approve** this plan
2. **Toggle to Act mode** for implementation
3. **Begin Phase 1** implementation
4. **Update Memory Bank** after completion

## Related Documents
- [LLM_IMPROVEMENTS.md](LLM_IMPROVEMENTS.md) - General LLM optimization strategies
- [CITATION_VERIFICATION_APPROACH.md](CITATION_VERIFICATION_APPROACH.md) - Citation verification methodology
- [MODEL_CONFIGURATION.md](MODEL_CONFIGURATION.md) - Model configuration patterns

---

**Document Owner**: Cline  
**Last Updated**: 26 July 2025  
**Review Date**: Implementation completion
