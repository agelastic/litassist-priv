# LitAssist Model Configuration Guide

Last updated: 18/02/2026
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
- verification-heavy, verify-soundness-heavy, verify-reasoning-heavy, cove-answers-heavy
- <1% hallucination rate for critical legal accuracy
- Premium cost justified by superior accuracy

**Tier 2: Fast Verification (GPT-5.1)**
- verification, cove-answers
- Upgraded from GPT-5 in November 2025
- Balanced speed and accuracy

**Tier 3: Legal Reasoning (Claude Sonnet 4.5 / Opus 4.1)**
- Most commands; verify-soundness uses Claude Opus 4.1 (cost-effective soundness)
- "State of the art on complex litigation tasks" per Anthropic
- 80% cost reduction vs Claude Opus 4.1 for standard tasks
- Extended thinking mode for multi-step analysis

#### November 2025 Updates
- `verification`: `gpt-5` → `gpt-5.1` (upgraded)
- `cove-answers`: `gpt-5` → `gpt-5.1` (upgraded)
- `verify-soundness`: `gpt-5-pro` → `claude-opus-4.1` (cost optimisation; heavy variant retains `gpt-5-pro`)
- `cove-final`: `gpt-5-pro` → `claude-sonnet-4.5` (cost optimisation)
- Added `--heavy` variants for verify-soundness and verify-reasoning
- Global token limit system removed; models use API defaults

| Command | Model | Purpose | Key Parameters |
|---------|-------|---------|----------------|
| **lookup** | `google/gemini-2.5-pro` | Rapid case law research | temperature: 0.2, top_p: 0.4, thinking_effort: low |
| **digest-summary** | `anthropic/claude-sonnet-4.5` | Document summarization | temperature: 0.2, top_p: 0.3, thinking_effort: medium |
| **digest-issues** | `anthropic/claude-sonnet-4.5` | Issue identification | temperature: 0.5, top_p: 0.8, thinking_effort: high |
| **caseplan** | `anthropic/claude-sonnet-4.5` | Workflow planning | temperature: 0.7, top_p: 0.95 |
| **caseplan-assessment** | `anthropic/claude-sonnet-4.5` | Budget assessment | temperature: 0.7, top_p: 0.95 |
| **extractfacts** | `anthropic/claude-sonnet-4.5` | Structured fact extraction | temperature: 0, top_p: 0.15, thinking_effort: high |
| **brainstorm-orthodox** | `anthropic/claude-sonnet-4.5` | Conservative legal strategies | temperature: 0.7, top_p: 0.95, thinking_effort: medium |
| **brainstorm-unorthodox** | `x-ai/grok-4` | Creative strategy generation | temperature: 0.8, top_p: 0.95, min_p: 0.05 |
| **brainstorm-analysis** | `openai/o3-pro` | Strategy analysis & ranking | temperature: 0.7, top_p: 0.9, thinking_effort: high* |
| **strategy** | `anthropic/claude-sonnet-4.5` | Legal strategy planning | temperature: 0.7, top_p: 0.95, thinking_effort: max |
| **strategy-analysis** | `openai/o3-pro` | Strategy assessment | temperature: 0.7, top_p: 0.95, thinking_effort: max* |
| **draft** | `openai/o3-pro` | Legal document drafting | temperature: 0.7, top_p: 0.95, thinking_effort: high, verbosity: high* |
| **counselnotes** | `openai/o3-pro` | Strategic advocate analysis | temperature: 0.7, top_p: 0.95, thinking_effort: high* |
| **barbrief** | `openai/o3-pro` | Comprehensive briefs | temperature: 0.7, top_p: 0.95, thinking_effort: high, verbosity: high* |
| **verification** | `openai/gpt-5.1` | Standard verification | temperature: 0.2, top_p: 0.3, thinking_effort: medium |
| **verification-heavy** | `openai/gpt-5-pro` | Critical verification | temperature: 0.2, top_p: 0.3, thinking_effort: max |
| **verification-light** | `anthropic/claude-sonnet-4.5` | Spelling/terminology | temperature: 0.2, top_p: 0.2, thinking_effort: medium |
| **verify-soundness** | `anthropic/claude-opus-4.1` | Soundness checking | temperature: 0.2, top_p: 0.3, thinking_effort: high |
| **verify-soundness-heavy** | `openai/gpt-5-pro` | Critical soundness checking | temperature: 0.2, top_p: 0.3, thinking_effort: max |
| **verify-reasoning** | `anthropic/claude-sonnet-4.5` | Reasoning extraction | temperature: 0.2, top_p: 0.3, thinking_effort: high |
| **verify-reasoning-heavy** | `openai/gpt-5-pro` | Critical reasoning check | temperature: 0.2, top_p: 0.3, thinking_effort: max |
| **cove** (stages) | `anthropic/claude-sonnet-4.5` | Chain of Verification | Various parameters per stage |
| **cove-questions** | `anthropic/claude-sonnet-4.5` | CoVe question generation | temperature: 0.6, top_p: 0.95, thinking_effort: low |
| **cove-answers** | `openai/gpt-5.1` | CoVe independent answers | temperature: 0.5, top_p: 0.8, thinking_effort: high |
| **cove-answers-heavy** | `openai/gpt-5-pro` | CoVe answers (heavy) | temperature: 0.5, top_p: 0.8, thinking_effort: max |
| **cove-verify** | `anthropic/claude-sonnet-4.5` | CoVe inconsistency check | temperature: 0.2, top_p: 0.3, thinking_effort: high |
| **cove-final** | `anthropic/claude-sonnet-4.5` | CoVe final validation | temperature: 0.2, top_p: 0.4, thinking_effort: medium |

*\*o3-pro rows show YAML values; `temperature` and `top_p` are stripped by the dynamic parameter filter before the API call. Effective parameters passed to o3-pro are `max_completion_tokens` and `reasoning_effort` (derived from `thinking_effort` mapping). See "Dynamic Parameter System" below.*

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
- **o3-pro**:
  - **Purpose**: Extended comprehensive document generation
  - **Used by**: draft, barbrief, counselnotes, brainstorm-analysis, strategy-analysis
- **Effective API Parameters** (what the API actually receives):
  - `max_completion_tokens` (NOT `max_tokens`)
  - `reasoning_effort` (low, medium, high — derived from `thinking_effort` mapping)
- **API Restrictions**:
  - NO temperature, top_p, or penalty parameters accepted
  - Requires BYOK setup through OpenRouter
- **YAML vs API note**: The `model_configs.yaml` entries for o3-pro commands include `temperature` and `top_p` values. These are present in the YAML but are silently removed by the dynamic parameter filter (`litassist/llm/`) before the API call is made. Only `max_completion_tokens` and `reasoning_effort` reach the API. Do not remove them from the YAML — they serve as documentation of intent and have no runtime effect.

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

```yaml
# Canonical source: litassist/llm/model_configs.yaml
# Note: temperature/top_p in o3-pro entries are stripped by the dynamic parameter filter.

# Tier 3: Legal Reasoning - Claude Sonnet 4.5
extractfacts:
  model: "anthropic/claude-sonnet-4.5"
  temperature: 0
  top_p: 0.15
  thinking_effort: "high"
  enforce_citations: true

strategy:
  model: "anthropic/claude-sonnet-4.5"
  temperature: 0.7
  top_p: 0.95
  thinking_effort: "max"

brainstorm-orthodox:
  model: "anthropic/claude-sonnet-4.5"
  temperature: 0.7
  top_p: 0.95
  thinking_effort: "medium"

digest-summary:
  model: "anthropic/claude-sonnet-4.5"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "medium"

digest-issues:
  model: "anthropic/claude-sonnet-4.5"
  temperature: 0.5
  top_p: 0.8
  thinking_effort: "high"

# Tier 1: Critical Verification - GPT-5 Pro (<1% hallucination)
verification-heavy:
  model: "openai/gpt-5-pro"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "max"

verify-soundness:
  model: "anthropic/claude-opus-4.1"  # Nov 2025: was gpt-5-pro
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "high"

verify-soundness-heavy:
  model: "openai/gpt-5-pro"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "max"

verify-reasoning:
  model: "anthropic/claude-sonnet-4.5"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "high"

verify-reasoning-heavy:
  model: "openai/gpt-5-pro"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "max"

# Tier 2: Fast Verification - GPT-5.1
verification:
  model: "openai/gpt-5.1"  # Nov 2025: was gpt-5
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "medium"

# Advanced Reasoning - o3-pro (temperature/top_p stripped by param filter)
draft:
  model: "openai/o3-pro"
  temperature: 0.7
  top_p: 0.95
  thinking_effort: "high"
  verbosity: "high"

counselnotes:
  model: "openai/o3-pro"
  temperature: 0.7
  top_p: 0.95
  thinking_effort: "high"

barbrief:
  model: "openai/o3-pro"
  temperature: 0.7
  top_p: 0.95
  thinking_effort: "high"
  verbosity: "high"

brainstorm-analysis:
  model: "openai/o3-pro"
  temperature: 0.7
  top_p: 0.9
  thinking_effort: "high"

strategy-analysis:
  model: "openai/o3-pro"
  temperature: 0.7
  top_p: 0.95
  thinking_effort: "max"

# Research - Gemini 2.5 Pro (1M context window)
lookup:
  model: "google/gemini-2.5-pro"
  temperature: 0.2
  top_p: 0.4
  thinking_effort: "low"

# Creative Ideation - Grok 4
brainstorm-unorthodox:
  model: "x-ai/grok-4"
  temperature: 0.8
  top_p: 0.95
  min_p: 0.05

# CoVe stages
cove-questions:
  model: "anthropic/claude-sonnet-4.5"
  temperature: 0.6
  top_p: 0.95
  thinking_effort: "low"

cove-answers:
  model: "openai/gpt-5.1"  # Nov 2025: was gpt-5
  temperature: 0.5
  top_p: 0.8
  thinking_effort: "high"

cove-answers-heavy:
  model: "openai/gpt-5-pro"
  temperature: 0.5
  top_p: 0.8
  thinking_effort: "max"

cove-verify:
  model: "anthropic/claude-sonnet-4.5"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "high"

cove-final:
  model: "anthropic/claude-sonnet-4.5"  # Nov 2025: was gpt-5-pro
  temperature: 0.2
  top_p: 0.4
  thinking_effort: "medium"
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

The retry logic is implemented in `litassist/llm/` package using the `tenacity` library. Only transient network errors (connection, timeout) are retried. All retry attempts and failures are logged for audit and debugging.

## Model Selection Philosophy

### October 2025 Three-Tier Strategy

The October 2025 upgrade implements a three-tier model selection strategy optimizing for legal accuracy and cost-efficiency:

**Tier 1: Critical Verification (GPT-5 Pro)**
- **Purpose**: Maximum accuracy for critical legal soundness checking
- **Hallucination Rate**: <1% (industry-leading)
- **Cost**: Premium, justified by superior accuracy
- **Use Cases**: verification-heavy, verify-soundness-heavy, verify-reasoning-heavy, cove-answers-heavy
- **Rationale**: Legal work requires absolute accuracy; <1% hallucination rate worth premium cost

**Tier 2: Fast Verification (GPT-5.1)**
- **Purpose**: Balanced speed and accuracy for standard verification
- **Hallucination Rate**: 1.4-1.6%
- **Cost**: Moderate
- **Use Cases**: verification, cove-answers
- **Note**: Upgraded from GPT-5 in November 2025; verify-soundness (standard) moved to claude-opus-4.1 as cost optimisation

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

## Output Control Parameters

### Understanding thinking_effort vs max_tokens

**IMPORTANT**: LitAssist uses two SEPARATE parameter systems for controlling model behavior:

#### 1. thinking_effort (Reasoning Budget)
**Purpose**: Controls how much computational effort the model spends reasoning BEFORE generating output
**Applies to**: Claude models (Anthropic family)
**NOT an output limit**: Does not restrict response length
**Values**: `"low"`, `"medium"`, `"high"`, `"max"`

**Token Budget Mapping** (internal reasoning tokens, NOT output):
- `"minimal"` / `"low"`: 1,024 reasoning tokens
- `"medium"`: 8,192 reasoning tokens
- `"high"`: 16,384 reasoning tokens
- `"max"`: 32,000 reasoning tokens

**Example**:
```python
"strategy": {
    "model": "anthropic/claude-sonnet-4.5",
    "thinking_effort": "max",  # Uses 32K tokens for internal reasoning
    # NO output length restriction - can generate as much as needed
}
```

#### 2. reasoning_effort (o-series Models)
**Purpose**: Controls reasoning depth for OpenAI o1/o3 models
**Applies to**: OpenAI reasoning models (o1, o3, o1-pro, o3-pro)
**Values**: `"low"`, `"medium"`, `"high"`
**NOT related to output length**

#### 3. max_tokens / max_completion_tokens (Output Length)
**Purpose**: Explicitly limits OUTPUT response length (when needed for cost control)
**Applies to**: All models (parameter name varies by model family)
**Use cases**: Cost-sensitive commands that need brief responses

**Example**:
```python
# Brief response for cost control
"lookup": {
    "model": "google/gemini-2.5-pro",
    "max_tokens": 4096,  # Explicit output limit
}

# Comprehensive analysis - NO limit
"barbrief": {
    "model": "openai/o3-pro",
    "max_completion_tokens": 32768,  # Large limit for comprehensive briefs
    "reasoning_effort": "high",  # Deep reasoning
}
```

### November 2025 Update: Output Limits Removed

**Previous behavior** (July-October 2025):
- Global `use_token_limits` flag automatically applied 16K-32K output limits
- All commands received automatic output restrictions

**Current behavior** (November 2025+):
- NO automatic output limits applied
- Models use API defaults (typically unlimited or very high limits)
- Commands that need output limits specify them explicitly in model_configs.yaml
- Quality prioritized over cost savings

**Rationale**:
- Modern models (Claude Sonnet 4.5, GPT-5, o3-pro) handle large outputs efficiently
- Legal work requires comprehensive responses - artificial truncation reduces quality
- thinking_effort provides reasoning control without limiting output length

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
    "gpt5.1": r"openai/gpt-5\.1",           # GPT-5.1 (must precede gpt5-pro)
    "gpt5-pro": r"openai/gpt-5-pro$",       # GPT-5 Pro specifically
    "gpt5": r"openai/gpt-5$",               # GPT-5 base model
    "anthropic": r"anthropic/claude",       # All Claude models
    "google": r"google/(gemini|palm|bard)", # Google models
    "xai": r"x-ai/grok",                    # xAI Grok models
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
Last updated: 18/02/2026
