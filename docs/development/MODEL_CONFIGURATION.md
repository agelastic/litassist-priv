# LitAssist Model Configuration Guide

Last updated: 28/05/2026
**Status**: Technical Reference - See `LLM_MODEL_STRATEGY.md` for strategy overview

## Overview

This document provides **detailed technical configuration** for LitAssist's LLM models. For strategy overview, see `LLM_MODEL_STRATEGY.md`.

LitAssist uses task-based model selection, matching each command to the model best suited for its job. Six model families serve distinct roles across 28 command configurations. The source of truth is `litassist/llm/model_configs.yaml`; this document explains that file.

All models are accessed through OpenRouter as the primary routing service.
o3-pro requires provider-key setup through OpenRouter integrations. GPT-5.5
currently runs as a standard OpenRouter model.

**Related Documentation:**
- **LLM_MODEL_STRATEGY.md** - Strategic overview, improvements, future opportunities
- **ARCHITECTURE_ANALYSIS_2025.md** - Overall architecture including LLM patterns
- **CLAUDE.md** - Development guidelines including model configuration policy

## Current Model Configuration

### Production Models

#### Active Models

**Claude Sonnet 4.6** (12 configurations)
- Legal reasoning, extraction, digest, caseplan, light verification, CoVe stages
- 1M context, $3/$15 per M tokens

**OpenAI o3-pro** (5 commands)
- draft, counselnotes, barbrief, strategy-analysis, brainstorm-analysis
- Extended thinking with structured reasoning traces

**Claude Opus 4.7** (2 configurations)
- strategy, verify-soundness
- Deep strategic and soundness analysis

**GPT-5.5** (6 configurations)
- verification, verification-heavy, verify-soundness-heavy, verify-reasoning-heavy, cove-answers, cove-answers-heavy
- Standard and heavy verification; heavy variants use higher reasoning effort

**Grok 4.20** (1 command)
- brainstorm-unorthodox
- High temperature with auto-verification

**Gemini 3.5 Flash** (1 command)
- lookup
- Fast synthesis over fetched legal research sources

#### Historical Notes
- November 2025 added `--heavy` variants for verify-soundness and verify-reasoning.
- November 2025 removed the global token limit system; models use API defaults.
- Current models have moved since the original November 2025 notes. Use `model_configs.yaml`, not historical changelog text, for active assignments.

| Command | Model | Purpose | Key Parameters |
|---------|-------|---------|----------------|
| **lookup** | `google/gemini-3.5-flash` | Rapid case law research synthesis | temperature: 0.2, top_p: 0.4, thinking_effort: low |
| **digest-summary** | `anthropic/claude-sonnet-4.6` | Document summarization | temperature: 0.2, top_p: 0.3, thinking_effort: medium |
| **digest-issues** | `anthropic/claude-sonnet-4.6` | Issue identification | temperature: 0.5, top_p: 0.8, thinking_effort: high |
| **caseplan** | `anthropic/claude-opus-4.7` | Workflow planning | temperature: 0.7, top_p: 0.95† |
| **caseplan-assessment** | `anthropic/claude-sonnet-4.6` | Budget assessment | temperature: 0.7, top_p: 0.95 |
| **extractfacts** | `anthropic/claude-sonnet-4.6` | Structured fact extraction | temperature: 0, top_p: 0.15, thinking_effort: high |
| **brainstorm-orthodox** | `anthropic/claude-sonnet-4.6` | Conservative legal strategies | temperature: 0.7, top_p: 0.95, thinking_effort: medium |
| **brainstorm-unorthodox** | `x-ai/grok-4.20` | Creative strategy generation | temperature: 0.8, top_p: 0.95, min_p: 0.05 |
| **brainstorm-analysis** | `openai/o3-pro` | Strategy analysis & ranking | temperature: 0.7, top_p: 0.9, thinking_effort: high* |
| **strategy** | `anthropic/claude-opus-4.7` | Legal strategy planning | temperature: 0.7, top_p: 0.95, thinking_effort: max† |
| **strategy-analysis** | `openai/o3-pro` | Strategy assessment | temperature: 0.7, top_p: 0.95, thinking_effort: max* |
| **draft** | `openai/o3-pro` | Legal document drafting | temperature: 0.7, top_p: 0.95, thinking_effort: high, verbosity: high* |
| **counselnotes** | `openai/o3-pro` | Strategic advocate analysis | temperature: 0.7, top_p: 0.95, thinking_effort: high* |
| **barbrief** | `openai/o3-pro` | Comprehensive briefs | temperature: 0.7, top_p: 0.95, thinking_effort: high, verbosity: high* |
| **verification** | `openai/gpt-5.5` | Standard verification | temperature: 0.2, top_p: 0.3, thinking_effort: medium |
| **verification-heavy** | `openai/gpt-5.5` | Critical verification | temperature: 0.2, top_p: 0.3, thinking_effort: max |
| **verification-light** | `anthropic/claude-sonnet-4.6` | Spelling/terminology | temperature: 0.2, top_p: 0.2, thinking_effort: medium |
| **verify-soundness** | `anthropic/claude-opus-4.7` | Soundness checking | temperature: 0.2, top_p: 0.3, thinking_effort: high† |
| **verify-soundness-heavy** | `openai/gpt-5.5` | Critical soundness checking | temperature: 0.2, top_p: 0.3, thinking_effort: max |
| **verify-reasoning** | `anthropic/claude-sonnet-4.6` | Reasoning extraction | temperature: 0.2, top_p: 0.3, thinking_effort: high |
| **verify-reasoning-heavy** | `openai/gpt-5.5` | Critical reasoning check | temperature: 0.2, top_p: 0.3, thinking_effort: max |
| **cove** (stages) | `anthropic/claude-sonnet-4.6` | Chain of Verification | Various parameters per stage |
| **cove-questions** | `anthropic/claude-sonnet-4.6` | CoVe question generation | temperature: 0.6, top_p: 0.95, thinking_effort: low |
| **cove-answers** | `openai/gpt-5.5` | CoVe independent answers | temperature: 0.5, top_p: 0.8, thinking_effort: high |
| **cove-answers-heavy** | `openai/gpt-5.5` | CoVe answers (heavy) | temperature: 0.5, top_p: 0.8, thinking_effort: max |
| **cove-verify** | `anthropic/claude-sonnet-4.6` | CoVe inconsistency check | temperature: 0.2, top_p: 0.3, thinking_effort: high |
| **cove-final** | `anthropic/claude-sonnet-4.6` | CoVe final validation | temperature: 0.2, top_p: 0.4, thinking_effort: medium |

*\*o3-pro rows show YAML values; `temperature` and `top_p` are stripped by the dynamic parameter filter before the API call. Effective parameters passed to o3-pro are `max_completion_tokens` and `reasoning_effort` (derived from `thinking_effort` mapping). See "Dynamic Parameter System" below.*

*†Opus 4.7/4.8 rows show YAML values; `temperature`/`top_p`/`top_k` are removed before the API call (Opus 4.7+ returns 400 on non-default sampling). `thinking_effort` uses the extended effort scale -- `xhigh`/`max` pass through (default `xhigh` on 4.7, `high` on 4.8). For other Claude 4.x (sonnet-4.x, older opus), `temperature` and `top_p` are never sent together (Anthropic since 4.1; `top_p` is dropped when both are set).*

### Model Capabilities & Restrictions

#### Claude Sonnet 4.6 (September 2025)
- **Model ID**: `anthropic/claude-sonnet-4.6`
- **Purpose**: State-of-the-art legal reasoning and analysis
- **Key Features**:
  - Explicitly "state of the art on complex litigation tasks"
  - Extended thinking mode via `thinking_effort` parameter
  - Superior legal domain knowledge per expert validation
  - 80% cost reduction vs Claude Opus 4.7 ($3/$15 vs $15/$75)
- **Strengths**: Multi-step legal reasoning, massive legal record parsing, coherent long-form analysis
- **Use Cases**: Fact extraction, issue identification, light verification, CoVe scaffolding, workflow planning
- **Parameters**: Supports temperature, top_p, thinking_effort (low/medium/high/max)
- **BYOK**: Not required on OpenRouter

#### GPT-5.5 (August 2025)
- **Model ID**: `openai/gpt-5.5`
- **Purpose**: Critical verification with industry-leading accuracy
- **Key Features**:
  - GPT-5.5: <1% hallucination rate, enhanced reasoning
  - 6x fewer factual errors than previous models
  - 80% fewer hallucinations than o3 with thinking mode
- **Strengths**: Factual accuracy, verification, soundness checking
- **Use Cases**: Standard and heavy verification, CoVe answers, heavy soundness and reasoning stages
- **Parameters**: Standard OpenAI parameters (temperature, top_p, max_tokens)
- **BYOK**: Not required on OpenRouter

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

#### Grok 4.20 (July 2025)
- **Model ID**: `x-ai/grok-4.20`
- **Purpose**: Creative legal strategy generation
- **Strengths**: Innovative thinking, unorthodox approaches, real-time search
- **Note**: Auto-verification enabled due to higher hallucination tendency
- **Parameters**: Supports temperature, top_p (use high values for creativity)

#### Gemini 3.5 Flash (2025)
- **Model ID**: `google/gemini-3.5-flash`
- **Purpose**: Fast, accurate case law research with massive context
- **Strengths**: 1M token context window, web-aware, comprehensive analysis
- **Use Cases**: Legal research with real-time verification, large document processing
- **Parameters**: Supports temperature, top_p, max_tokens

## Configuration Management

### LLMClientFactory Pattern

All model configurations are centralized in `litassist/llm/model_configs.yaml` and loaded through `litassist/llm/factory.py`.

```yaml
# Canonical source: litassist/llm/model_configs.yaml
# Note: temperature/top_p in o3-pro entries are stripped by the dynamic parameter filter.

# Tier 3: Legal Reasoning - Claude Sonnet 4.6
extractfacts:
  model: "anthropic/claude-sonnet-4.6"
  temperature: 0
  top_p: 0.15
  thinking_effort: "high"
  enforce_citations: true

strategy:
  model: "anthropic/claude-opus-4.7"
  temperature: 0.7
  top_p: 0.95
  thinking_effort: "max"

brainstorm-orthodox:
  model: "anthropic/claude-sonnet-4.6"
  temperature: 0.7
  top_p: 0.95
  thinking_effort: "medium"

digest-summary:
  model: "anthropic/claude-sonnet-4.6"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "medium"

digest-issues:
  model: "anthropic/claude-sonnet-4.6"
  temperature: 0.5
  top_p: 0.8
  thinking_effort: "high"

# Tier 1: Critical Verification - GPT-5.5 (<1% hallucination)
verification-heavy:
  model: "openai/gpt-5.5"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "max"

verify-soundness:
  model: "anthropic/claude-opus-4.7"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "high"

verify-soundness-heavy:
  model: "openai/gpt-5.5"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "max"

verify-reasoning:
  model: "anthropic/claude-sonnet-4.6"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "high"

verify-reasoning-heavy:
  model: "openai/gpt-5.5"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "max"

# Tier 2: Fast Verification - GPT-5.5
verification:
  model: "openai/gpt-5.5"
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

# Research synthesis - Gemini 3.5 Flash
lookup:
  model: "google/gemini-3.5-flash"
  temperature: 0.2
  top_p: 0.4
  thinking_effort: "low"

# Creative Ideation - Grok 4.20
brainstorm-unorthodox:
  model: "x-ai/grok-4.20"
  temperature: 0.8
  top_p: 0.95
  min_p: 0.05

# CoVe stages
cove-questions:
  model: "anthropic/claude-sonnet-4.6"
  temperature: 0.6
  top_p: 0.95
  thinking_effort: "low"

cove-answers:
  model: "openai/gpt-5.5"
  temperature: 0.5
  top_p: 0.8
  thinking_effort: "high"

cove-answers-heavy:
  model: "openai/gpt-5.5"
  temperature: 0.5
  top_p: 0.8
  thinking_effort: "max"

cove-verify:
  model: "anthropic/claude-sonnet-4.6"
  temperature: 0.2
  top_p: 0.3
  thinking_effort: "high"

cove-final:
  model: "anthropic/claude-sonnet-4.6"
  temperature: 0.2
  top_p: 0.4
  thinking_effort: "medium"
```

### OpenRouter Configuration

**Primary Routing**: All models route through OpenRouter
- Centralized API management
- OpenAI BYOK integration required in OpenRouter for o3-pro
- Access to premium models
- Enhanced rate limits and capabilities

**API Key Setup**:
```yaml
# config.yaml
openrouter:
  api_key: "your-openrouter-api-key"
```

For BYOK access to specific provider models such as `openai/o3-pro`, add the
provider key in the OpenRouter integrations dashboard:
https://openrouter.ai/settings/integrations. This project carries no direct
OpenAI key.

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

### Task-Based Model Selection

Each command is assigned the model best suited to its task. Selection criteria are
accuracy requirements, reasoning depth, cost, and context window needs.

See `LLM_MODEL_STRATEGY.md` for the full strategy description and model groupings.

### Task-Optimized Selection

1. **Factual Tasks** (temperature: 0)
   - Extraction, summaries, verification
   - Models: Claude Sonnet 4.6, GPT-5.5

2. **Analytical Tasks** (temperature: 0.2-0.5)
   - Strategy analysis, issue identification
   - Models: Claude Sonnet 4.6 (extended thinking mode)

3. **Creative Tasks** (temperature: 0.8-0.9)
   - Brainstorming, unorthodox strategies
   - Models: Grok 4.20

4. **Verification Tasks** (temperature: 0-0.2)
   - Critical: GPT-5.5 (<1% hallucination)
   - Standard: GPT-5.5 (<1% hallucination)
   - Light: Claude Sonnet 4.6 (spelling/terminology)

### Cost-Performance Balance

- Sonnet 4.6 handles 12 configurations at $3/$15 (80% cheaper than GPT-5.5)
- GPT-5 family for verification only where low hallucination rates justify premium cost
- o3-pro for technical drafting where extended reasoning matters
- Net result: 40-50% overall cost reduction vs single-model approach

**Model Cost Tiers:**
- **Premium**: GPT-5.5, o3-pro (critical tasks only)
- **Moderate**: Claude Opus 4.7, Gemini 3.5 Flash (specialized performance)
- **Efficient**: Claude Sonnet 4.6 (best value for legal work)
- **Creative**: Grok 4.20 (specialized ideation)

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
    "model": "anthropic/claude-sonnet-4.6",
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
    "model": "anthropic/claude-sonnet-4.6",
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
- Modern models (Claude Sonnet 4.6, GPT-5, o3-pro) handle large outputs efficiently
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
    "gpt5.5": r"openai/gpt-5\.5",          # active GPT-5.5 family
    "gpt5.1": r"openai/gpt-5\.1",          # legacy GPT-5.1 family
    "gpt5-pro": r"openai/gpt-5-pro$",      # legacy GPT-5 Pro family
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

**Adding a model from a new provider**:
```python
# Just use it:
"digest": "zai/glm-4.7"  # Falls to the "default" profile (safe sampling params)
                         # until a zai/ pattern is added to MODEL_PATTERNS in
                         # litassist/llm/model_profiles.py for richer routing.
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
- Ensure `openrouter.api_key` is configured locally
- Add the OpenAI provider key in OpenRouter integrations for o3-pro
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
- GPT-5.5 structured output opportunities
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
Last updated: 26/02/2026
