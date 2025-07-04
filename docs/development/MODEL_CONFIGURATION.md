# LitAssist Model Configuration Guide

**Last Updated**: January 7, 2025

## Overview

LitAssist uses multiple specialized LLM models optimized for different legal tasks. All models are accessed through OpenRouter as the primary routing service, with extensive BYOK (Bring Your Own Key) configurations for premium models.

## Current Model Configuration

### Production Models

| Command | Model | Purpose | Key Parameters |
|---------|-------|---------|----------------|
| **lookup** | `google/gemini-2.5-pro-preview` | Rapid case law research | temperature: 0.1, top_p: 0.2 |
| **digest** | `anthropic/claude-sonnet-4` | Document processing & summarization | temperature: 0 (summary) or 0.2 (issues) |
| **extractfacts** | `anthropic/claude-sonnet-4` | Structured fact extraction | temperature: 0, top_p: 0.15 |
| **brainstorm** | `x-ai/grok-3-beta` | Creative strategy generation | temperature: 0.9, top_p: 0.95 |
| **brainstorm** (analysis) | `anthropic/claude-sonnet-4` | Strategy analysis & ranking | temperature: 0.2, top_p: 0.8 |
| **strategy** | `openai/o3-pro` | Strategic planning & analysis | max_completion_tokens: varies, reasoning_effort: varies |
| **draft** | `openai/o3-pro` | Legal document drafting | max_completion_tokens: 4096, reasoning_effort: medium |
| **counselnotes** | `anthropic/claude-sonnet-4` | Strategic advocate analysis | temperature: 0.3, top_p: 0.7 |
| **barbrief** | `openai/o3-pro` | Comprehensive barrister's briefs | max_completion_tokens: 32768, reasoning_effort: high |
| **verify** | `anthropic/claude-sonnet-4` | Document verification | temperature: 0, top_p: 0.2 |

### Model Capabilities & Restrictions

#### OpenAI o3 & o3-pro
- **o3**: 
  - **Purpose**: Superior technical legal writing
  - **Used by**: draft command
  - **Default max_completion_tokens**: 4096
- **o3-pro**: 
  - **Purpose**: Extended comprehensive document generation
  - **Used by**: barbrief command  
  - **Default max_completion_tokens**: 32768 (32K)
- **Supported Parameters (both models)**: 
  - `max_completion_tokens` (NOT `max_tokens`)
  - `reasoning_effort` (low, medium, high)
- **Restrictions (both models)**: 
  - NO temperature, top_p, or penalty parameters
  - Requires BYOK setup through OpenRouter
- **Key Difference**: o3-pro supports much longer outputs (32K vs 4K tokens)

#### Claude 4 Sonnet
- **Model ID**: `anthropic/claude-sonnet-4`
- **Purpose**: Reliable extraction, analysis, and verification
- **Strengths**: Structured output, consistency, following complex instructions
- **Use Cases**: Document processing, fact extraction, strategy analysis

#### Grok 3 Beta
- **Model ID**: `x-ai/grok-3-beta`
- **Purpose**: Creative legal strategy generation
- **Strengths**: Innovative thinking, unorthodox approaches
- **Note**: Auto-verification enabled due to hallucination tendencies

#### Gemini 2.5 Pro Preview
- **Model ID**: `google/gemini-2.5-pro-preview`
- **Purpose**: Fast, accurate case law research
- **Strengths**: Web-aware, comprehensive analysis
- **Use Cases**: Legal research with real-time verification

## Configuration Management

### LLMClientFactory Pattern

All model configurations are centralized in `litassist/llm.py`:

```python
MODEL_CONFIGS = {
    "lookup": "google/gemini-2.5-pro-preview",
    "digest": "anthropic/claude-sonnet-4",
    "extractfacts": "anthropic/claude-sonnet-4",
    "brainstorm": "x-ai/grok-3-beta",
    "brainstorm-analysis": "anthropic/claude-sonnet-4",
    "strategy": "openai/o3-pro",
    "draft": "openai/o3-pro",
    "verify": "anthropic/claude-sonnet-4"
}
```

### Environment Variable Overrides

Models can be overridden via environment variables:
```bash
export ANTHROPIC_MODEL="anthropic/claude-sonnet-4"
export OPENAI_MODEL="openai/o3-pro"
export GOOGLE_MODEL="google/gemini-2.5-pro-preview"
export XGROK_MODEL="x-ai/grok-3-beta"
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

## Model Selection Philosophy

### Task-Optimized Selection

1. **Factual Tasks** (temperature: 0)
   - Extraction, summaries, verification
   - Models: Claude Sonnet, Gemini

2. **Analytical Tasks** (temperature: 0.2-0.5)
   - Strategy analysis, drafting
   - Models: o3-pro, Claude Sonnet

3. **Creative Tasks** (temperature: 0.9)
   - Brainstorming, unorthodox strategies
   - Models: Grok 3 Beta

### Cost-Performance Balance

- **High-Value Tasks**: o3-pro for strategy/draft (justify premium cost)
- **Volume Tasks**: Claude Sonnet for reliable processing
- **Research Tasks**: Gemini for fast, accurate lookup
- **Creative Tasks**: Grok for innovation despite verification overhead

## Token Limits & Configuration

### Conservative Token Limits (when enabled)

| Model | Max Tokens | Conservative Limit |
|-------|------------|-------------------|
| `google/gemini-*` | 8192 | 2048 |
| `anthropic/claude-*` | 4096 | 1536 |
| `openai/gpt-4*` | 4096 | 3072 |
| `openai/o3-pro` | Uses max_completion_tokens | N/A |
| `x-ai/grok-*` | 4096 | 1536 |

### Configuration
```yaml
llm:
  use_token_limits: false  # Default: let models use natural limits
```

## Dynamic Parameter System

LitAssist uses a dynamic, pattern-based parameter filtering system that automatically handles different model capabilities without hardcoding specific model names.

### How It Works

1. **Model Family Detection**: Models are matched against regex patterns to identify their family
2. **Parameter Filtering**: Each model family has an allowed parameter list
3. **Parameter Transformation**: Some parameters are automatically transformed (e.g., `max_tokens` → `max_completion_tokens`)
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

## Future Considerations

- Regular model version updates as providers release new versions
- Cost optimization through intelligent model selection
- Fallback strategies for model unavailability
- Performance monitoring and adaptive selection