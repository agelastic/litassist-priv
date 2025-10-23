# LitAssist Model Configuration Guide

**Last Updated**: October 23, 2025
**Status**: Technical Reference - See `LLM_MODEL_STRATEGY.md` for strategy overview

## Overview

This document provides **detailed technical configuration** for LitAssist's LLM models. For strategy overview, see `LLM_MODEL_STRATEGY.md`.

LitAssist uses a three-tier model strategy optimized for legal work (October 2025 upgrade):

**Three-Tier Model Strategy:**
- **Tier 1: Critical Verification** - GPT-5 Pro (<1% hallucination rate) for soundness checking
- **Tier 2: Fast Verification** - GPT-5 (1.4% hallucination rate) for standard verification
- **Tier 3: Legal Reasoning** - Claude Sonnet 4.5 (state-of-the-art for complex litigation tasks)

All models are accessed through OpenRouter as the primary routing service, with BYOK (Bring Your Own Key) configurations for premium models (o3-pro, GPT-5, GPT-5 Pro).

**Related Documentation:**
- **LLM_MODEL_STRATEGY.md** - Strategic overview, improvements, future opportunities
- **ARCHITECTURE_ANALYSIS_2025.md** - Overall architecture including LLM patterns
- **CLAUDE.md** - Development guidelines including model configuration policy

## Current Model Configuration

### Production Models

#### October 2025: Three-Tier Model Upgrade
Major upgrade implementing three-tier strategy for optimal accuracy and cost-efficiency:

**Tier 1: Critical Verification (GPT-5 Pro)**
- verify-soundness, verification-heavy, cove-final
- <1% hallucination rate for critical legal accuracy
- Premium cost justified by superior accuracy

**Tier 2: Fast Verification (GPT-5)**
- verification, cove-answers
- 1.4-1.6% hallucination rate
- Balanced speed and accuracy

**Tier 3: Legal Reasoning (Claude Sonnet 4.5)**
- Most commands (14 total)
- "State of the art on complex litigation tasks" per Anthropic
- 80% cost reduction vs Claude Opus 4.1
- Extended thinking mode for multi-step analysis

| Command | Model | Purpose | Key Parameters |
|---------|-------|---------|----------------|
| **lookup** | `google/gemini-2.5-pro` | Rapid case law research | temperature: 0.2, top_p: 0.4, 1M context |
| **digest-summary** | `anthropic/claude-sonnet-4.5` | Document summarization | temperature: 0.2, top_p: 0.3, thinking_effort: medium |
| **digest-issues** | `anthropic/claude-sonnet-4.5` | Issue identification | temperature: 0.2, top_p: 0.5, thinking_effort: high |
| **caseplan** | `anthropic/claude-sonnet-4.5` | Workflow planning | temperature: 0.5, top_p: 0.7 |
| **caseplan-assessment** | `anthropic/claude-sonnet-4.5` | Budget assessment | temperature: 0.2, thinking_effort: medium |
| **extractfacts** | `anthropic/claude-sonnet-4.5` | Structured fact extraction | temperature: 0, top_p: 0.15, thinking_effort: high |
| **brainstorm-orthodox** | `anthropic/claude-sonnet-4.5` | Conservative legal strategies | temperature: 0.3, top_p: 0.7 |
| **brainstorm-unorthodox** | `x-ai/grok-4` | Creative strategy generation | temperature: 0.9, top_p: 0.95 |
| **brainstorm-analysis** | `openai/o3-pro` | Strategy analysis & ranking | max_completion_tokens: 8192, reasoning_effort: high |
| **strategy** | `anthropic/claude-sonnet-4.5` | Legal strategy planning | temperature: 0.2, top_p: 0.8, thinking_effort: max |
| **strategy-analysis** | `openai/o3-pro` | Strategy assessment | max_completion_tokens: 4096, reasoning_effort: high |
| **draft** | `openai/o3-pro` | Legal document drafting | max_completion_tokens: 4096, reasoning_effort: medium |
| **counselnotes** | `openai/o3-pro` | Strategic advocate analysis | max_completion_tokens: 8192, reasoning_effort: high |
| **barbrief** | `openai/o3-pro` | Comprehensive briefs | max_completion_tokens: 32768, reasoning_effort: high |
| **verification** | `openai/gpt-5` | Standard verification | temperature: 0.2, top_p: 0.3 |
| **verification-heavy** | `openai/gpt-5-pro` | Critical verification | temperature: 0.2, top_p: 0.3, thinking_effort: max |
| **verification-light** | `anthropic/claude-sonnet-4.5` | Spelling/terminology | temperature: 0, top_p: 0.2 |
| **verify-soundness** | `openai/gpt-5-pro` | Soundness checking | temperature: 0.2, top_p: 0.3, thinking_effort: max |
| **verify-reasoning** | `anthropic/claude-sonnet-4.5` | Reasoning extraction | temperature: 0.2, top_p: 0.3, thinking_effort: high |
| **cove** (stages) | `anthropic/claude-sonnet-4.5` | Chain of Verification | Various parameters per stage |
| **cove-final** | `openai/gpt-5-pro` | Final CoVe validation | temperature: 0.2, thinking_effort: high |

### Model Capabilities & Restrictions

#### Claude Sonnet 4.5 (September 2025)
- **Model ID**: `anthropic/claude-sonnet-4.5`
- **Purpose**: State-of-the-art legal reasoning and analysis
- **Key Features**:
  - Explicitly "state of the art on complex litigation tasks"
  - Extended thinking mode via `thinking_effort` parameter
  - Superior legal domain knowledge per expert validation
  - 80% cost reduction vs Claude Opus 4.1 ($3/$15 vs $15/$75)
- **Strengths**: Multi-step legal reasoning, massive legal record parsing, coherent long-form analysis
- **Use Cases**: Strategy, fact extraction, issue identification, verification, workflow planning
- **Parameters**: Supports temperature, top_p, thinking_effort (low/medium/high/max)
- **BYOK**: Not required on OpenRouter

#### GPT-5 and GPT-5 Pro (August 2025)
- **Model IDs**: `openai/gpt-5`, `openai/gpt-5-pro`
- **Purpose**: Critical verification with industry-leading accuracy
- **Key Features**:
  - GPT-5: 1.4-1.6% hallucination rate
  - GPT-5 Pro: <1% hallucination rate, enhanced reasoning
  - 6x fewer factual errors than previous models
  - 80% fewer hallucinations than o3 with thinking mode
- **Strengths**: Factual accuracy, verification, soundness checking
- **Use Cases**: Critical verification (GPT-5 Pro), fast verification (GPT-5)
- **Parameters**: Standard OpenAI parameters (temperature, top_p, max_tokens)
- **BYOK**: Required on OpenRouter (Tier 4+ API key)

#### OpenAI o3 & o3-pro
- **o3**:
  - **Purpose**: Technical legal writing
  - **Used by**: draft command
  - **Default max_completion_tokens**: 4096
- **o3-pro**:
  - **Purpose**: Extended comprehensive document generation
  - **Used by**: barbrief, counselnotes, analysis commands
  - **Default max_completion_tokens**: 32768 (32K)
- **Supported Parameters (both models)**:
  - `max_completion_tokens` (NOT `max_tokens`)
  - `reasoning_effort` (low, medium, high)
- **Restrictions (both models)**:
  - NO temperature, top_p, or penalty parameters
  - Requires BYOK setup through OpenRouter
- **Key Difference**: o3-pro supports much longer outputs (32K vs 4K tokens)

#### Grok 4 (July 2025)
- **Model ID**: `x-ai/grok-4`
- **Purpose**: Creative legal strategy generation
- **Strengths**: Innovative thinking, unorthodox approaches, real-time search
- **Note**: Auto-verification enabled due to higher hallucination tendency
- **Parameters**: Supports temperature, top_p (use high values for creativity)

#### Gemini 2.5 Pro (2025)
- **Model ID**: `google/gemini-2.5-pro`
- **Purpose**: Fast, accurate case law research with massive context
- **Strengths**: 1M token context window, web-aware, comprehensive analysis
- **Use Cases**: Legal research with real-time verification, large document processing
- **Parameters**: Supports temperature, top_p, max_tokens

## Configuration Management

### LLMClientFactory Pattern

All model configurations are centralized in `litassist/llm/client.py` as `COMMAND_CONFIGS` dictionary:

```python
COMMAND_CONFIGS = {
    # Tier 3: Legal Reasoning - Claude Sonnet 4.5 (state-of-the-art litigation)
    "extractfacts": {
        "model": "anthropic/claude-sonnet-4.5",
        "temperature": 0,
        "top_p": 0.15,
        "thinking_effort": "high",
        "enforce_citations": True,
    },
    "strategy": {
        "model": "anthropic/claude-sonnet-4.5",
        "temperature": 0.2,
        "top_p": 0.8,
        "thinking_effort": "max",
    },
    "brainstorm-orthodox": {
        "model": "anthropic/claude-sonnet-4.5",
        "temperature": 0.3,
        "top_p": 0.7,
        "thinking_effort": "medium",
    },
    "digest-summary": {
        "model": "anthropic/claude-sonnet-4.5",
        "temperature": 0.2,
        "top_p": 0.3,
        "thinking_effort": "medium",
    },
    "digest-issues": {
        "model": "anthropic/claude-sonnet-4.5",
        "temperature": 0.2,
        "top_p": 0.5,
        "thinking_effort": "high",
    },

    # Tier 1: Critical Verification - GPT-5 Pro (<1% hallucination)
    "verification-heavy": {
        "model": "openai/gpt-5-pro",
        "temperature": 0.2,
        "top_p": 0.3,
        "thinking_effort": "max",
    },
    "verify-soundness": {
        "model": "openai/gpt-5-pro",
        "temperature": 0.2,
        "top_p": 0.3,
        "thinking_effort": "max",
    },

    # Tier 2: Fast Verification - GPT-5 (1.4% hallucination)
    "verification": {
        "model": "openai/gpt-5",
        "temperature": 0.2,
        "top_p": 0.3,
    },

    # Advanced Reasoning - o3-pro (drafting and comprehensive analysis)
    "draft": {
        "model": "openai/o3-pro",
        "max_completion_tokens": 4096,
        "reasoning_effort": "medium",
    },
    "counselnotes": {
        "model": "openai/o3-pro",
        "max_completion_tokens": 8192,
        "reasoning_effort": "high",
    },
    "barbrief": {
        "model": "openai/o3-pro",
        "max_completion_tokens": 32768,
        "reasoning_effort": "high",
    },

    # Research - Gemini 2.5 Pro (1M context window)
    "lookup": {
        "model": "google/gemini-2.5-pro",
        "temperature": 0.2,
        "top_p": 0.4,
    },

    # Creative Ideation - Grok 4
    "brainstorm-unorthodox": {
        "model": "x-ai/grok-4",
        "temperature": 0.9,
        "top_p": 0.95,
    },
    "brainstorm-analysis": {
        "model": "openai/o3-pro",
        "temperature": 0.2,
        "top_p": 0.8,
        "thinking_effort": "high",
        "disable_tools": True,
    },
    "strategy-analysis": {
        "model": "openai/o3-pro",
        "thinking_effort": "max",
        "disable_tools": True,
    },
}
```

### Environment Variable Overrides

Models can be overridden via environment variables:
```bash
export ANTHROPIC_MODEL="anthropic/claude-sonnet-4"
export OPENAI_MODEL="openai/o3-pro"
export GOOGLE_MODEL="google/gemini-2.5-pro"
export XGROK_MODEL="x-ai/grok-4"
```

### OpenRouter Configuration

**Primary Routing**: All models route through OpenRouter
- Centralized API management
- Multiple BYOK configurations attached
- Access to premium models
- Enhanced rate limits and capabilities

**API Key Setup**:
```yaml
# config.yaml
openrouter:
  api_key: "your-openrouter-api-key"
  
openai:
  api_key: "your-openai-api-key"  # Required for o3-pro BYOK
```

## Retry Logic Configuration

| Parameter         | Default | Description                                  |
|-------------------|---------|----------------------------------------------|
| retries           | 3       | Maximum connection attempts (1 + retries)    |
| min_retry_delay   | 0.5s    | Initial delay before first retry             |
| max_retry_delay   | 10s     | Maximum delay between attempts               |
| safety_cutoff     | 5       | Circuit breaker disables retries after N failures/hour |

**Safety Guarantees:**
- Original API configuration is always restored after failures
- No retries for authentication errors (4xx)
- Circuit breaker activates after 5 failures/hour

The retry logic is implemented in `litassist/llm.py` using the `tenacity` library. Only transient network errors (connection, timeout) are retried. All retry attempts and failures are logged for audit and debugging.

## Model Selection Philosophy

### October 2025 Three-Tier Strategy

The October 2025 upgrade implements a three-tier model selection strategy optimizing for legal accuracy and cost-efficiency:

**Tier 1: Critical Verification (GPT-5 Pro)**
- **Purpose**: Maximum accuracy for critical legal soundness checking
- **Hallucination Rate**: <1% (industry-leading)
- **Cost**: Premium, justified by superior accuracy
- **Use Cases**: verify-soundness, verification-heavy, cove-final
- **Rationale**: Legal work requires absolute accuracy; <1% hallucination rate worth premium cost

**Tier 2: Fast Verification (GPT-5)**
- **Purpose**: Balanced speed and accuracy for standard verification
- **Hallucination Rate**: 1.4-1.6%
- **Cost**: Moderate
- **Use Cases**: verification, cove-answers
- **Rationale**: 80% fewer errors than previous models at reasonable cost

**Tier 3: Legal Reasoning (Claude Sonnet 4.5)**
- **Purpose**: State-of-the-art legal domain knowledge and reasoning
- **Hallucination Rate**: ~2-3%
- **Cost**: 80% reduction vs Claude Opus 4.1 ($3/$15 vs $15/$75)
- **Use Cases**: 14 commands including strategy, extractfacts, digest, caseplan
- **Rationale**: Explicitly "state of the art on complex litigation tasks" per Anthropic

**Specialized Models:**
- **o3-pro**: Technical drafting and comprehensive briefs (extended 32K output capacity)
- **Gemini 2.5 Pro**: Legal research (1M context window)
- **Grok 4**: Creative ideation (unorthodox strategies)

### Task-Optimized Selection

1. **Factual Tasks** (temperature: 0)
   - Extraction, summaries, verification
   - Models: Claude Sonnet 4.5, GPT-5 Pro

2. **Analytical Tasks** (temperature: 0.2-0.5)
   - Strategy analysis, issue identification
   - Models: Claude Sonnet 4.5 (extended thinking mode)

3. **Creative Tasks** (temperature: 0.8-0.9)
   - Brainstorming, unorthodox strategies
   - Models: Grok 4

4. **Verification Tasks** (temperature: 0-0.2)
   - Critical: GPT-5 Pro (<1% hallucination)
   - Standard: GPT-5 (1.4% hallucination)
   - Light: Claude Sonnet 4.5 (spelling/terminology)

### Cost-Performance Balance

**October 2025 Improvements:**
- **80% cost reduction**: Opus 4.1 → Sonnet 4.5 for 14 commands
- **Better accuracy**: GPT-5 family for verification (6x fewer errors)
- **Maintained quality**: o3-pro for technical drafting
- **Net result**: 40-50% overall cost reduction while improving quality

**Model Cost Tiers:**
- **Premium**: GPT-5 Pro, o3-pro (critical tasks only)
- **Moderate**: GPT-5, Gemini 2.5 Pro (balanced performance)
- **Efficient**: Claude Sonnet 4.5 (best value for legal work)
- **Creative**: Grok 4 (specialized ideation)

## Token Limits & Configuration

### Generation Token Limits (July 2025 Update)

All models now use increased token limits for better output quality:

| Model | Generation Limit | Verification Limit |
|-------|-----------------|-------------------|
| `google/gemini-*` | 32768 | 8192 |
| `anthropic/claude-*` | 32768 | 16384 (heavy) / 8192 (standard) |
| `openai/gpt-4*` | 32768 | 8192 |
| `openai/o3-pro` | 32768 (max_completion_tokens) | 16384 |
| `x-ai/grok-*` | 32768 | 8192 |

### Verification Token Limits (July 2025)

Verification limits were increased significantly to handle full document verification:
- **Previous limits**: 800-1536 tokens (caused truncation)
- **New limits**: 8192-16384 tokens (preserves full documents)

### Configuration
```yaml
llm:
  use_token_limits: true  # Default since July 2025 - enforces 32K token limits for comprehensive outputs
```

## Dynamic Parameter System

LitAssist uses a dynamic, pattern-based parameter filtering system that automatically handles different model capabilities without hardcoding specific model names.

### How It Works

1. **Model Family Detection**: Models are matched against regex patterns to identify their family
2. **Parameter Filtering**: Each model family has an allowed parameter list
3. **Parameter Transformation**: Some parameters are automatically transformed (e.g., `max_tokens` -> `max_completion_tokens`)
4. **System Message Handling**: Automatic detection of system message support

### Model Patterns

```python
MODEL_PATTERNS = {
    "openai_reasoning": r"openai/o\d+",     # o1, o3, o1-pro, o3-pro, future o5, etc.
    "anthropic": r"anthropic/claude",       # All Claude models
    "google": r"google/(gemini|palm|bard)", # Google models
    "openai_standard": r"openai/(gpt|chatgpt)", # Standard GPT models
    # ... more patterns
}
```

### Adding New Models

To add a new model, simply:

1. **Update the model name in COMMAND_CONFIGS**:
```python
"new_command": "provider/new-model-name"
```

2. **If it's a new provider**, add a pattern and profile:
```python
# Add to MODEL_PATTERNS
"new_provider": r"new-provider/",

# Add to PARAMETER_PROFILES
"new_provider": {
    "allowed": ["temperature", "max_tokens", ...],
    "transforms": {"old_param": "new_param"},
    "system_message_support": True,
}
```

3. **That's it!** The system automatically handles parameter filtering

### Examples

**Changing to a future model**:
```python
# Just change this:
"strategy": "openai/o3-pro"
# To this:
"strategy": "openai/o5-pro"  # Works automatically!
```

**Adding a new Claude model**:
```python
# Just use it:
"digest": "anthropic/claude-5-opus"  # Automatically gets Claude parameters
```

### Benefits

- **Zero hardcoding**: No `if model == "specific-model"` checks
- **Future-proof**: New model versions work without code changes
- **Pattern-based**: All `openai/o*` models are treated as reasoning models
- **Maintainable**: All parameter logic in one place

## Common Issues & Solutions

### Issue: Model Not Found
- Verify exact model identifier (case-sensitive)
- Check OpenRouter model availability
- Ensure API keys are configured

### Issue: Parameter Restrictions
- o3-pro: Use max_completion_tokens, not max_tokens
- o3-pro: No temperature/top_p/penalties allowed
- Check model-specific restrictions in llm.py

### Issue: BYOK Required
- Ensure both OpenRouter AND provider API keys configured
- Verify BYOK setup in OpenRouter dashboard
- Check provider-specific requirements

## Best Practices

1. **Never Change Model Identifiers**: They are exact API endpoints
2. **Use OpenRouter**: Primary routing for all models
3. **Respect Restrictions**: Model-specific parameter limitations
4. **Monitor Costs**: Premium models (o3-pro) for high-value tasks only
5. **Test Thoroughly**: Verify model behavior before production use

## Verification Optimization (2025 Enhancement)

### Problem: Redundant LLM Verification Calls

Commands with explicit verification (e.g., `barbrief --verify`) were making unnecessary duplicate verification calls:

1. **Explicit verification**: Google CSE API for accurate citation validation
2. **Auto-verification**: Additional LLM-based validation (redundant)

### Solution: Smart Verification Deduplication

```python
def verify_content_if_needed(
    client, content, command_name, verify_flag=False,
    citation_already_verified=False  # Added parameter
):
    # Skip redundant LLM citation validation when Google CSE already verified
```

### Benefits

- **50% reduction** in LLM calls for verified commands
- **Preserved accuracy**: Google CSE verification is more reliable
- **Cost savings**: Fewer premium model API calls
- **Backward compatible**: No breaking changes to existing workflows

### Implementation

Commands implementing verification optimization:
- `barbrief`: Passes `citation_already_verified=verify` to avoid double citation checking

## Future Considerations

See `LLM_MODEL_STRATEGY.md` → "Future Model Opportunities" for:
- OpenAI o4 family considerations
- Claude 4.2 family upgrade paths
- GPT-5.1 structured output opportunities
- Gemini 2.5 Flash Thinking cost optimization
- Runtime configuration recommendations

**Additional Technical Considerations:**
- Regular model version updates as providers release new versions
- Cost optimization through intelligent model selection
- Fallback strategies for model unavailability
- Performance monitoring and adaptive selection
- Extension of verification optimization to other commands with dual verification paths

---

**Document Purpose**: Technical reference for model configuration and parameters
**Strategic Guidance**: See `LLM_MODEL_STRATEGY.md`
**Last Updated**: October 23, 2025
