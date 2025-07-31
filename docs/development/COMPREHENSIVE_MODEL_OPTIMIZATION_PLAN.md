# Comprehensive Model Optimization Plan

**Last Updated**: July 31, 2025

**Date**: 26 July 2025  
**Status**: Planned - Ready for Implementation  
**Priority**: P1 - Performance & Accuracy Enhancement

## Executive Summary

This document outlines the complete implementation plan for optimizing all LitAssist commands using the hybrid model pipeline that balances speed, accuracy, citation correctness, and creative depth. The plan leverages cutting-edge models available via OpenRouter for maximum performance.

## Model Optimization Matrix

| Command | Current Model | New Model | Temperature | Top_p | Status | Rationale |
|---------|---------------|-----------|-------------|--------|--------|-----------|
| **lookup-retrieval** | google/gemini-2.5-pro | - | 0.1 | 0.2 | Implemented | Fastest broad retrieval |
| **lookup-verification** | Jade.io only | openai/o4-mini-high | 0 | 0 | Planned | Zero-hallucination verification |
| **extractfacts** | anthropic/claude-sonnet-4 | - | 0 | 0.15 | Implemented | Sub-second deterministic extraction |
| **digest-summary** | anthropic/claude-sonnet-4 | - | 0.1 | 0 | Implemented | Balanced coherence & brevity |
| **digest-issues** | anthropic/claude-opus-4 | - | 0.2 | 0.5 | Implemented | Focused issue-spotting |
| **brainstorm-orthodox** | anthropic/claude-opus-4 | - | 0.3 | 0.7 | Implemented | Fast creative breadth |
| **brainstorm-unorthodox** | x-ai/grok-4 | - | 0.8 | 0.95 | Implemented | Highly diverse creative angles |
| **brainstorm-analysis** | openai/o3-pro | - | - | - | Implemented | Reasoning analysis (unchanged) |
| **caseplan** | openai/o4-mini-high | - | 0.3 | 0.7 | Implemented | LLM-driven workflow planning |
| **strategy** | openai/o3-pro | - | - | - | Implemented | Deep legal reasoning (unchanged) |
| **strategy-analysis** | openai/o3-pro | - | - | - | Implemented | Detailed pros/cons (unchanged) |
| **draft** | openai/o3-pro | - | - | - | Implemented | Flawless drafting (unchanged) |
| **counselnotes** | openai/o3-pro | - | - | - | Implemented | Advocacy-style analysis |
| **barbrief** | openai/o3-pro | - | - | - | Implemented | Comprehensive briefs (unchanged) |
| **verify** | openai/o3-pro | - | - | - | Implemented | Enhanced verification |

## Implementation Phases

### Phase 1: Speed-Optimized Commands (Week 1)
**Commands**: extractfacts, digest-summary, digest-issues, caseplan

#### extractfacts Command
- **Current**: Claude Sonnet 4
- **New**: openai/o4-mini-high, temp=0, top_p=0
- **Benefit**: Sub-second deterministic fact extraction
- **Risk**: Minimal - o4-mini-high excels at structured extraction

#### digest Commands
- **Current**: Claude Sonnet 4
- **New**: openai/o4-mini-high variants
- **Benefit**: <1s summarization and issue-spotting
- **Implementation**: Separate prompt templates for summary vs issues

#### caseplan Command
- **Current**: Claude Sonnet 4
- **New**: openai/o4-mini-high, temp=0.4, top_p=0.8
- **Benefit**: Rapid creative phase planning with 200K context

### Phase 2: Creative Enhancement (Week 2)
**Commands**: brainstorm-unorthodox

#### brainstorm-unorthodox
- **Current**: Grok 3
- **New**: x-ai/grok-4, temp=0.8, top_p=0.95
- **Benefit**: Sparse MoE generates highly diverse, unexpected legal angles
- **Implementation**: Direct OpenRouter integration, no self-host needed

### Phase 3: Verification & Analysis (Week 3)
**Commands**: verify, counselnotes

#### verify Command
- **Current**: Claude Opus 4
- **New**: openai/o3-pro, reasoning_effort=high
- **Benefit**: Superior adversarial reasoning for verification tasks

#### counselnotes Command
 - **Current**: Claude Opus 4
 - **New**: openai/o3-pro, reasoning_effort=high
- **Benefit**: Enhanced advocacy-style analysis with tactical insights

### Phase 4: Lookup Pipeline (Week 4)
**Commands**: lookup (detailed in separate document)

## Configuration Updates

### New Model Registry
```python
# LLMClientFactory additions
MODEL_CONFIGURATIONS = {
    # Speed-optimized models
    "o4-mini-high-extract": {
        "model": "openai/o4-mini-high",
        "temperature": 0,
        "top_p": 0,
        "max_tokens": 4096
    },
    
    "gemini-retrieval": {
        "model": "google/gemini-2.5-pro-preview",
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": 8192
    },
    
    "kimi-creative": {
        "model": "moonshotai/kimi-k2",
        "temperature": 0.9,
        "top_p": 1,
        "max_tokens": 8192
    },
    
    # Enhanced reasoning models
    "o3-pro-analysis": {
        "model": "openai/o3-pro",
        "reasoning_effort": "high",
        "temperature": 0.2,
        "max_tokens": 16384
    }
}
```

### Configuration Schema Updates
```yaml
# config.yaml additions
commands:
  extractfacts:
    model: "openai/o4-mini-high"
    temperature: 0
    top_p: 0
    
  digest:
    summary_model: "openai/o4-mini-high"
    summary_temp: 0.3
    issues_model: "openai/o4-mini-high"
    issues_temp: 0.1
    
  brainstorm:
    orthodox_model: "openai/o4-mini-high"
    orthodox_temp: 0.7
    unorthodox_model: "moonshotai/kimi-k2"
    unorthodox_temp: 0.9
    
  caseplan:
    model: "openai/o4-mini-high"
    temperature: 0.4
    
  verify:
    model: "openai/o3-pro"
    reasoning_effort: "high"
    
  counselnotes:
    model: "openai/o3-pro"
    reasoning_effort: "high"
    temperature: 0.5
```

## Prompt Template Updates

### extractfacts.yaml
```yaml
system: |
  You are a precise legal fact extraction system. Extract ONLY verifiable facts from the provided documents.
  Use zero-temperature reasoning for deterministic output.
  
user: |
  Extract all verifiable facts from the following legal documents...
```

### digest.yaml
```yaml
summary_system: |
  Provide concise, accurate summaries of legal documents using controlled creativity (temp=0.3).
  
issues_system: |
  Identify specific legal issues with zero-temperature precision to avoid spurious findings.
```

### brainstorm.yaml
```yaml
orthodox_system: |
  Generate creative but legally sound strategies using moderate temperature for breadth.
  
unorthodox_system: |
  Generate highly diverse, unexpected legal angles using maximum creativity (Kimi K2 sparse MoE).
```

## Testing Strategy

### Performance Benchmarks
| Command | Current Speed | Target Speed | Improvement |
|---------|---------------|--------------|-------------|
| extractfacts | 2-3s | <1s | 60-70% faster |
| digest-summary | 3-4s | <1s | 70-75% faster |
| digest-issues | 2-3s | <1s | 60-70% faster |
| caseplan | 4-5s | 1-2s | 60-80% faster |
| brainstorm | 3-4s | 1-2s | 50-67% faster |

### Accuracy Validation
- **Citation correctness**: >99% (up from ~95%)
- **Legal soundness**: Enhanced through o3-pro reasoning
- **Creative diversity**: Significantly improved via Kimi K2

### A/B Testing Framework
```python
# Test configuration
TEST_SCENARIOS = {
    "speed_test": {
        "commands": ["extractfacts", "digest", "caseplan"],
        "metrics": ["response_time", "token_usage", "accuracy"]
    },
    "creativity_test": {
        "commands": ["brainstorm-unorthodox"],
        "metrics": ["diversity_score", "novelty_rating", "legal_soundness"]
    },
    "verification_test": {
        "commands": ["verify", "counselnotes"],
        "metrics": ["reasoning_depth", "citation_accuracy", "completeness"]
    }
}
```

## Rollout Strategy

### Week 1: Speed Commands
- extractfacts, digest-summary, digest-issues, caseplan
- Low-risk, immediate performance gains

### Week 2: Creative Enhancement
- brainstorm-unorthodox with Kimi K2
- A/B testing against current Grok implementation

### Week 3: Verification & Analysis
- verify, counselnotes with o3-pro
- Enhanced reasoning capabilities

### Week 4: Lookup Pipeline
- Two-stage lookup (separate document)

## Risk Mitigation

### Technical Risks
- **API Availability**: All models available via OpenRouter
- **Rate Limits**: Implement exponential backoff
- **Cost Monitoring**: Usage tracking per command

### Legal Risks
- **Model Knowledge**: Validate Australian legal expertise
- **Citation Accuracy**: Enhanced verification pipeline
- **Professional Standards**: Compliance testing

### Fallback Strategy
```python
# Automatic fallback configurations
FALLBACK_MODELS = {
    "openai/o4-mini-high": "anthropic/claude-sonnet-4",
    "google/gemini-2.5-pro-preview": "anthropic/claude-sonnet-4", 
    "moonshotai/kimi-k2": "x-ai/grok-3",
    "openai/o3-pro": "anthropic/claude-opus-4"
}
```

## Success Metrics

### Performance Targets
- **Speed**: 50-80% improvement across commands
- **Accuracy**: >99% citation correctness
- **Reliability**: <0.1% error rate
- **Creativity**: 3x increase in strategy diversity

### User Experience
- **Perceived speed**: Sub-second for most commands
- **Quality**: Zero hallucination reports
- **Satisfaction**: Positive user feedback

## Monitoring & Alerting

### Usage Tracking
```python
# Metrics collection
METRICS = {
    "response_time": "per_command",
    "token_usage": "per_model",
    "error_rate": "per_command",
    "user_satisfaction": "per_survey"
}
```

### Cost Monitoring
- **Budget alerts**: Per command and total
- **Usage dashboards**: Real-time visibility
- **Efficiency reports**: Weekly analysis

## Next Steps

1. **Review and approve** this comprehensive plan
2. **Toggle to Act mode** for implementation
3. **Begin Phase 1** (speed-optimized commands)
4. **Update Memory Bank** after each phase
5. **Monitor metrics** throughout rollout

## Related Documents
- [LOOKUP_PIPELINE_OPTIMIZATION_PLAN.md](LOOKUP_PIPELINE_OPTIMIZATION_PLAN.md) - Detailed lookup pipeline changes
- [MODEL_CONFIGURATION.md](MODEL_CONFIGURATION.md) - Current model configurations
- [LLM_IMPROVEMENTS.md](LLM_IMPROVEMENTS.md) - General LLM optimization strategies

---

**Document Owner**: Cline  
**Last Updated**: July 31, 2025  
**Review Date**: Post-implementation analysis
