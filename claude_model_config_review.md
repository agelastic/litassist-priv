# LLM Model Configuration Review and Recommendations

## 1. Missing/Incorrect Parameters to Add

### Strategy Command (claude-opus-4.1)
**Current**: Missing thinking parameters for Opus 4.1
**Add**:
```python
"strategy": {
    "model": "anthropic/claude-opus-4.1",
    "temperature": 0.2,  # Add for control
    "top_p": 0.8,        # Add for focused output
    "thinking_effort": "max",  # Already present, good
    "max_completion_tokens": 16384,  # Add for longer strategies
}
```

### Extractfacts Command (claude-sonnet-4)
**Current**: Missing thinking capability
**Add**:
```python
"extractfacts": {
    "model": "anthropic/claude-sonnet-4",
    "temperature": 0,
    "top_p": 0.15,
    "thinking_effort": "medium",  # Add for accuracy
}
```

### Digest-issues (claude-opus-4.1)
**Current**: Missing thinking for complex issue spotting
**Add**:
```python
"digest-issues": {
    "model": "anthropic/claude-opus-4.1",
    "temperature": 0.2,
    "top_p": 0.5,
    "thinking_effort": "high",  # Add for deep analysis
}
```

### Lookup (gemini-2.5-pro)
**Current**: Has thinking_effort but Gemini support through OpenRouter is limited
**Consider**: Remove thinking_effort or keep for future compatibility

### Draft (o3-pro)
**Add**:
```python
"draft": {
    "model": "openai/o3-pro",
    "thinking_effort": "high",  # Present
    "verbosity": "high",  # Present
    "max_completion_tokens": 32768,  # Add for long drafts
}
```

### Barbrief (o3-pro)
**Current**: Has max_completion_tokens but missing seed for reproducibility
**Add**:
```python
"seed": 42,  # For consistent brief generation
```

## 2. Parameter Suitability Analysis

### ✅ Well-Configured Commands:
- **brainstorm-unorthodox**: Correctly uses high temp (0.8) + repetition_penalty for creativity
- **verification**: Zero temp for deterministic checking
- **cove stages**: Appropriate model/temp balance

### ⚠️ Needs Adjustment:
- **digest-summary**: `top_p: 0` is too restrictive, should be 0.1-0.2
- **strategy-analysis**: Using o3-pro with temp/top_p that will be ignored (o3 ignores these)
- **caseplan**: Using "openai/o4-mini-high" which doesn't exist yet (o4-mini launched but not "high" variant)

## 3. Alternative Model Recommendations

Based on August 2025 availability and benchmarks:

### High-Priority Changes:

**1. Strategy Command**
- **Current**: anthropic/claude-opus-4.1
- **Keep as is**: Opus 4.1 dominates for complex reasoning (78% AIME, 200k context)

**2. Draft Command**
- **Current**: openai/o3-pro
- **Alternative**: Consider `anthropic/claude-opus-4.1` for better prompt following and 200k context
- **Rationale**: Opus 4.1 excels at following instructions precisely, critical for legal drafting

**3. Brainstorm-unorthodox**
- **Current**: x-ai/grok-4
- **Keep**: Grok 4's 98% HumanEval coding + video generation capabilities offer unique creative potential

**4. Lookup Command**
- **Current**: google/gemini-2.5-pro
- **Keep**: 1M token context window is unmatched for large document search

**5. Caseplan Commands**
- **Current**: openai/o4-mini-high (doesn't exist)
- **Change to**: `openai/o4-mini` or `anthropic/claude-sonnet-4`
- **Rationale**: o4-mini exists, "high" variant not confirmed

### New Model Options (August 2025):

**GPT-5** (Released August 2025)
- Use for: strategy-analysis, counselnotes
- Benefits: 94.6% AIME, 400k context, Intelligence Index 69
- Replace o3-pro in analytical tasks

**Claude Sonnet 4** (vs 3.7)
- Use for: verification, cove stages
- Benefits: 72.7% SWE-bench, better reasoning than 3.7
- Cost-effective at $3/$15 per M tokens

## 4. Unified Parameter Translation Improvements

### Add to convert_thinking_effort():
```python
# Support o4-mini (new in 2025)
elif "openai/o4" in model_name:
    return {
        "reasoning": {
            "effort": effort_map.get(effort, "medium"),
            "summary": "auto"  # New o4 feature
        }
    }

# Support GPT-5 (August 2025)
elif "openai/gpt-5" in model_name:
    return {
        "reasoning": {
            "effort": effort_map.get(effort, "medium"),
            "verbosity": verbosity  # GPT-5 supports both
        }
    }
```

### Add new parameter profiles:
```python
"gpt5": {
    "allowed": [
        "temperature", "top_p", "max_tokens",
        "reasoning", "verbosity", "seed",
        "response_format", "structured_outputs"
    ],
    "system_message_support": True  # GPT-5 supports system messages
}

"claude4": {  # Opus 4.1 and Sonnet 4
    "allowed": [
        "temperature", "top_p", "max_tokens",
        "reasoning", "stop_sequences",
        "thinking_effort",  # Maps to reasoning.max_tokens
        "tool_use"  # New in Claude 4
    ]
}
```

## 5. Command-Specific Optimizations

### Legal Research (lookup, verify)
- Add `"response_format": {"type": "json_object"}` for structured citations
- Use `"seed"` parameter for reproducible legal research

### Creative Tasks (brainstorm)
- Add `"min_p": 0.05` for diversity
- Consider `"top_a": 0.1` for nuanced selection

### Technical Writing (draft, barbrief)
- Maximize `max_completion_tokens` (32768+)
- Use `"verbosity": "high"` consistently
- Add `"structured_outputs": true` when available

### Verification Tasks
- Always use `temperature: 0`
- Add `"seed"` for consistency
- Disable `force_verify` to prevent recursion

This configuration leverages the latest August 2025 models while maintaining backward compatibility through the unified translation system.