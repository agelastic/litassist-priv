# Claude Thinking Budget Implementation Plan

## Critical Overview
Implementation of Claude 3.7+ Sonnet's extended thinking mode parameters (`thinking_mode`, `thinking_budget`, `thinking_type`) for enhanced reasoning capabilities in LitAssist.

## Phase 1: Research & Validation (MUST DO FIRST)

### 1.1 Verify Model Support
- [ ] Confirm which Claude models support thinking parameters:
  - Claude 3.7 Sonnet (confirmed)
  - Claude 3.5 Sonnet (needs verification)
  - Claude Opus 4.1 (needs verification)
  - Claude Sonnet 4 (needs verification)

### 1.2 Test API Compatibility
```python
# Test script to verify parameter acceptance
test_params = {
    "model": "anthropic/claude-3-7-sonnet",
    "thinking_mode": "extended",
    "thinking_budget": 5000,
    "max_tokens": 2000,
    "messages": [{"role": "user", "content": "Test"}]
}
# Run through OpenRouter to verify support
```

### 1.3 Document Parameter Constraints
- `thinking_budget` must be < `max_tokens`
- Maximum thinking_budget: 128,000 tokens
- With tool use: can use full context window (200k)
- Cost implications: thinking tokens are billed

## Phase 2: Core Implementation

### 2.1 Update Parameter Profiles (`litassist/llm.py`)

```python
# Line ~79-89 - UPDATE CAREFULLY
"anthropic": {
    "allowed": [
        "temperature",
        "top_p", 
        "max_tokens",
        "stop",
        "top_k",
        "stream",
        "metadata",
        "stop_sequences",
        # NEW PARAMETERS - ADD THESE
        "thinking_mode",      # "extended", "quick", "disabled"
        "thinking_budget",    # Integer up to 128000
        "thinking_type",      # "enabled", "hidden"
    ],
},
```

### 2.2 Add Model Detection Pattern

```python
# Add new pattern for thinking-capable models
MODEL_PATTERNS = {
    # ... existing patterns ...
    "anthropic_thinking": r"anthropic/claude-3\.[7-9]|anthropic/claude-[4-9]",  # 3.7+ models
}

def supports_thinking_mode(model_name: str) -> bool:
    """Check if model supports extended thinking parameters."""
    import re
    pattern = MODEL_PATTERNS.get("anthropic_thinking", "")
    return bool(re.match(pattern, model_name))
```

### 2.3 Update Command Configurations

#### Strategic Commands (High Thinking Budget)
```python
# Strategy command - needs deep reasoning
"strategy": {
    "model": "anthropic/claude-3-7-sonnet",  # Upgrade from o3-pro if appropriate
    "thinking_mode": "extended",
    "thinking_budget": 32000,  # 32k tokens for complex strategy
    "thinking_type": "hidden",  # Don't expose internal reasoning
    "temperature": 0.2,
    "top_p": 0.7,
    "max_tokens": 8192,
    "force_verify": True,
},
```

#### Verification Commands (Medium Thinking Budget)
```python
# Verification - needs careful analysis
"verification": {
    "model": "anthropic/claude-3-7-sonnet",  
    "thinking_mode": "extended",
    "thinking_budget": 16000,  # 16k for thorough verification
    "thinking_type": "hidden",
    "temperature": 0,
    "top_p": 0.2,
    "max_tokens": 8192,
    "force_verify": False,
},
```

#### CoVe Stages (Variable Thinking Budgets)
```python
# CoVe question generation - moderate thinking
"cove-questions": {
    "model": "anthropic/claude-3-7-sonnet",
    "thinking_mode": "extended",
    "thinking_budget": 8000,  # 8k for question formulation
    "thinking_type": "hidden",
    "temperature": 0.2,
    "top_p": 0.8,
    "max_tokens": 4096,
},

# CoVe final regeneration - high thinking
"cove-final": {
    "model": "anthropic/claude-3-7-sonnet",
    "thinking_mode": "extended", 
    "thinking_budget": 24000,  # 24k for final synthesis
    "thinking_type": "hidden",
    "temperature": 0.1,
    "top_p": 0.8,
    "max_tokens": 8192,
},
```

## Phase 3: Smart Budget Allocation

### 3.1 Dynamic Budget Calculation
```python
def calculate_thinking_budget(command: str, content_length: int) -> int:
    """
    Calculate appropriate thinking budget based on command and content.
    
    CRITICAL: Must not exceed max_tokens or 128000.
    """
    base_budgets = {
        "strategy": 32000,
        "verification": 16000,
        "brainstorm-unorthodox": 24000,
        "extractfacts": 12000,
        "digest-issues": 16000,
        "cove-final": 24000,
    }
    
    base = base_budgets.get(command, 8000)
    
    # Scale based on content complexity
    if content_length > 50000:  # Large documents
        base = min(base * 1.5, 128000)
    elif content_length < 5000:  # Small documents
        base = base * 0.5
        
    return int(base)
```

### 3.2 Add CLI Options
```python
# Add --thinking-budget flag to commands
@click.option(
    "--thinking-budget",
    type=click.IntRange(0, 128000),
    help="Token budget for extended thinking (Claude 3.7+ only)"
)
@click.option(
    "--thinking-mode",
    type=click.Choice(["extended", "quick", "auto"]),
    default="auto",
    help="Thinking mode for Claude models"
)
```

## Phase 4: Fallback & Compatibility

### 4.1 Graceful Degradation
```python
def apply_thinking_params(model: str, params: dict) -> dict:
    """
    Apply thinking parameters only if supported.
    CRITICAL: Must not break existing functionality.
    """
    if not supports_thinking_mode(model):
        # Remove thinking parameters for incompatible models
        params.pop("thinking_mode", None)
        params.pop("thinking_budget", None)
        params.pop("thinking_type", None)
    else:
        # Ensure budget < max_tokens
        if "thinking_budget" in params and "max_tokens" in params:
            params["thinking_budget"] = min(
                params["thinking_budget"],
                params["max_tokens"] - 100  # Safety margin
            )
    return params
```

### 4.2 Error Handling
```python
# In _execute_api_call_with_retry
try:
    response = client.chat.completions.create(**params)
except Exception as e:
    if "thinking_budget" in str(e) or "thinking_mode" in str(e):
        # Retry without thinking parameters
        logger.warning(f"Thinking parameters not supported, retrying without: {e}")
        filtered_params = {k: v for k, v in params.items() 
                          if k not in ["thinking_mode", "thinking_budget", "thinking_type"]}
        response = client.chat.completions.create(**filtered_params)
    else:
        raise
```

## Phase 5: Testing Plan

### 5.1 Unit Tests
```python
# test_thinking_parameters.py
def test_thinking_params_added_for_compatible_models():
    """Verify thinking params are added for Claude 3.7+."""
    
def test_thinking_params_removed_for_incompatible_models():
    """Verify thinking params are stripped for older models."""
    
def test_thinking_budget_never_exceeds_max_tokens():
    """CRITICAL: Ensure budget < max_tokens constraint."""
    
def test_fallback_on_thinking_param_error():
    """Verify graceful fallback if params rejected."""
```

### 5.2 Integration Tests
- [ ] Test with actual Claude 3.7 Sonnet via OpenRouter
- [ ] Test with Claude Opus 4.1 (should fallback gracefully)
- [ ] Test with non-Anthropic models (params should be stripped)
- [ ] Test cost tracking with thinking tokens

### 5.3 Command-Level Tests
- [ ] `strategy` with high thinking budget
- [ ] `verification` with medium thinking budget  
- [ ] `cove` stages with varying budgets
- [ ] User-specified `--thinking-budget` flag

## Phase 6: Documentation

### 6.1 Update CLAUDE.md
```markdown
### Thinking Budget Configuration

Claude 3.7+ models support extended thinking with configurable token budgets:

- **thinking_mode**: "extended" (deep reasoning) or "quick" (faster)
- **thinking_budget**: Up to 128,000 tokens for internal reasoning
- **thinking_type**: "hidden" (default) or "enabled" (show thinking)

Commands automatically allocate appropriate thinking budgets:
- Strategy: 32,000 tokens (complex multi-step reasoning)
- Verification: 16,000 tokens (thorough accuracy checks)
- Brainstorm: 24,000 tokens (creative exploration)
```

### 6.2 Update User Guide
- Explain thinking budget impact on quality/cost
- Document CLI flags for manual control
- Provide examples of when to adjust budgets

## Phase 7: Rollout Strategy

### 7.1 Staged Deployment
1. **Week 1**: Implement core parameter support (Phase 2)
2. **Week 2**: Add to verification commands only (low risk)
3. **Week 3**: Enable for strategy/brainstorm (higher value)
4. **Week 4**: Full rollout with CLI options

### 7.2 Monitoring
- Track API errors related to thinking parameters
- Monitor token usage increases
- Measure quality improvements in outputs

## Critical Success Criteria

1. **MUST NOT** break existing functionality for any model
2. **MUST** gracefully fallback if parameters rejected  
3. **MUST** enforce thinking_budget < max_tokens constraint
4. **MUST** strip parameters for non-compatible models
5. **MUST** handle API errors without crashes

## Risk Mitigation

### High-Risk Areas
1. **Parameter Validation**: Budget exceeding max_tokens → API rejection
2. **Model Detection**: Incorrectly identifying model capabilities
3. **Cost Explosion**: Thinking tokens can significantly increase costs
4. **Backwards Compatibility**: Breaking existing Claude integrations

### Mitigation Strategies
1. **Conservative Defaults**: Start with small thinking budgets
2. **Feature Flag**: Add `ENABLE_THINKING_MODE` config option
3. **Extensive Testing**: Test with all model variants
4. **Gradual Rollout**: Enable for one command at a time
5. **Cost Warnings**: Alert users when thinking budget > 10k tokens

## Implementation Checklist

- [ ] Research: Verify model support matrix
- [ ] Research: Test parameter acceptance via API
- [ ] Core: Update PARAMETER_PROFILES
- [ ] Core: Add supports_thinking_mode() function
- [ ] Core: Update command configurations
- [ ] Core: Implement dynamic budget calculation
- [ ] Core: Add parameter filtering logic
- [ ] UI: Add CLI flags for thinking control
- [ ] Safety: Add budget validation
- [ ] Safety: Implement fallback logic
- [ ] Testing: Write unit tests
- [ ] Testing: Perform integration tests
- [ ] Testing: Validate with production API
- [ ] Docs: Update CLAUDE.md
- [ ] Docs: Update User Guide
- [ ] Deploy: Feature flag implementation
- [ ] Deploy: Staged rollout
- [ ] Monitor: Track API errors
- [ ] Monitor: Analyze cost impact

## Final Notes

**CRITICAL VALIDATION BEFORE DEPLOYMENT:**
1. Test with $1 API credit limit to ensure no cost explosion
2. Verify fallback works with ALL existing model configurations
3. Ensure thinking_budget NEVER exceeds max_tokens - 100
4. Test with both OpenRouter and direct Anthropic API
5. Confirm no breaking changes to existing commands

**Remember**: Every parameter must be validated, every edge case must be handled, and every failure must degrade gracefully. The thinking budget feature should enhance capabilities without compromising stability.

---
*Last Updated: 2025-01-08*
*Status: PLANNING - DO NOT IMPLEMENT WITHOUT TESTING*