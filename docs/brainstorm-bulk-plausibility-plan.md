# Brainstorm Bulk Plausibility Implementation Plan
Date: 2025-11-14
Status: Partially Implemented, Needs Completion

## Executive Summary
The bulk plausibility assessment for brainstorm command exists but isn't working due to strategy format issues. This document outlines the complete implementation plan based on the original design.

## Problem Statement
- Bulk plausibility function (`assess_legal_plausibility_bulk()`) exists in code
- Not working because strategies lack proper `### Strategy N: [Title]` format
- Extraction regex fails → No individual strategies → No risk assessments

## Original Design Philosophy
From the original plan:
- **Core Philosophy**: "Garbage in, garbage out" - Don't repair citations after selection
- **Approach**: Generate 15+15 → Verify & annotate ALL → Select 10 → Recommend exactly 5
- **Token Savings**: ~75% savings on flawed strategies (no repair + no wasted analysis)

## Current Implementation Status

### ✅ Completed
1. `verify_and_annotate_strategies()` function exists (core.py lines 195-306)
2. `assess_legal_plausibility_bulk()` function exists (core.py lines 110-192)
3. Citation verification logic in place
4. Annotation helper functions created
5. Prompt format fix applied (2025-11-14)

### ❌ Not Working
1. Strategy title format not being generated consistently by LLMs
2. Extraction regex not finding strategies when format is wrong
3. Risk levels not appearing in output
4. Wrong strategy counts (should be 15+15→10→5, currently undefined)

## Implementation Tasks

### Phase 1: Fix Strategy Format Generation ✅ Partially Complete
- [x] Fix prompt assembly in orthodox_generator.py
- [x] Fix prompt assembly in unorthodox_generator.py
- [ ] Verify LLMs follow format instructions
- [ ] Test extraction regex with proper format

### Phase 2: Update Strategy Counts
Per original plan: 15 orthodox + 15 unorthodox → 10 selected → 5 recommended

Files to update in `strategies.yaml`:
```yaml
# Line 11 - Orthodox count
orthodox_prompt: |
  Generate 15 ORTHODOX legal strategies...  # Currently says "Generate 15"

# Line 41 - Unorthodox count
unorthodox_prompt: |
  Generate 15 UNORTHODOX legal strategies... # Currently says "Generate 15"

# Line 71 - Analysis selection
analysis_prompt: |
  select EXACTLY 10 of the most promising... # Currently says "10"

# Line 125-141 - Final recommendations
## MOST LIKELY TO SUCCEED
[List EXACTLY 5 strategies...] # Currently says "EXACTLY 5"
```

### Phase 3: Fix Extraction Regex
Current pattern in `_extract_strategies()` (core.py line 49):
```python
pattern = r'(?:^|\n)(?:###\s+Strategy\s+\d+:|###\s+\d+\.|##\s*STRATEGY\s*\d+:|\d+\.)[^\n]*\n(.*?)(?=(?:\n(?:###\s+Strategy\s+\d+:|###\s+\d+\.|##\s*STRATEGY\s*\d+:|\d+\.))|$)'
```

This pattern is too complex and brittle. Simplify to:
```python
# Match "### Strategy N: [Title]" format specifically
pattern = r'###\s+Strategy\s+(\d+):\s*([^\n]+)\n(.*?)(?=###\s+Strategy\s+\d+:|$)'
```

### Phase 4: Ensure Bulk Plausibility Works
The function exists but needs verification:

1. **Add debug logging**:
```python
# In assess_legal_plausibility_bulk()
logging.info(f"Assessing {len(strategies_with_unverified)} strategies with unverified citations")
logging.debug(f"Plausibility response: {response[:500]}")
```

2. **Verify JSON parsing**:
```python
# Better error handling for JSON extraction
try:
    json_match = re.search(r'\{[\s\S]*\}', response)
    if json_match:
        assessments = json.loads(json_match.group(0))
        logging.info(f"Parsed {len(assessments)} risk assessments")
    else:
        logging.warning("No JSON found in plausibility response")
except json.JSONDecodeError as e:
    logging.error(f"JSON parsing failed: {e}")
```

3. **Ensure annotations are visible**:
- Verify `_annotate_strategies_with_verification()` is adding risk levels
- Check that annotated content is being returned to output

### Phase 5: Add Verification Summary
Add after line 304 in `verify_and_annotate_strategies()`:
```python
# Build detailed summary
summary_lines = [
    f"Total strategies: {len(orthodox_strategies) + len(unorthodox_strategies)}",
    f"Citations verified: {total_verified}",
    f"Citations unverified: {total_unverified}",
]

if plausibility_assessments:
    risk_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "UNKNOWN": 0}
    for assessment in plausibility_assessments.values():
        risk = assessment.get("risk", "UNKNOWN")
        risk_counts[risk] += 1

    summary_lines.append(f"Risk assessment: LOW={risk_counts['LOW']}, MEDIUM={risk_counts['MEDIUM']}, HIGH={risk_counts['HIGH']}")

summary = " | ".join(summary_lines)
```

## Testing Checklist
- [ ] Strategies have proper `### Strategy N: [Title]` format
- [ ] Extraction finds exactly 15 orthodox strategies
- [ ] Extraction finds exactly 15 unorthodox strategies
- [ ] Citations show [VERIFIED] or [NOT VERIFIED] status
- [ ] Unverified citations show risk levels (LOW/MEDIUM/HIGH)
- [ ] Analysis selects exactly 10 strategies
- [ ] Most Likely section lists exactly 5 strategies
- [ ] Bulk plausibility uses single LLM call for all unverified
- [ ] Performance: <10 seconds for plausibility assessment

## Token Cost Analysis

### Current (Broken)
- Generate (undefined count): ~16k tokens
- Repair attempts: ~4k tokens (wasteful)
- Analysis: ~12k tokens
- Total: ~32k tokens (but produces incorrect output)

### Target (Fixed)
- Generate 15+15: ~24k tokens (+50%)
- Citation verification: ~500 tokens (API calls)
- Bulk plausibility: ~5k tokens (single call)
- Analysis with annotations: ~15k tokens
- Total: ~44.5k tokens (38% increase but works correctly)

### Savings
- No repair cycles (saves 4k tokens)
- Single bulk assessment vs individual (saves 5k tokens)
- Net: Better quality at reasonable cost increase

## Risk Mitigation
1. **Graceful fallback**: If plausibility fails, continue without risk levels
2. **Format flexibility**: Support multiple strategy formats in extraction
3. **Comprehensive logging**: Track every step for debugging
4. **Backward compatibility**: Preserve existing output structure

## Success Metrics
1. **Extraction rate**: 100% of strategies extracted correctly
2. **Risk coverage**: All unverified citations get risk assessments
3. **Performance**: <10 second overhead for plausibility
4. **Reliability**: Zero failed brainstorm runs due to format issues
5. **Cost efficiency**: <50% token increase for >100% quality improvement

## Implementation Order
1. First: Save this plan ✅
2. Second: Fix extraction regex to be more robust
3. Third: Update strategy counts in prompts
4. Fourth: Add debug logging to trace issues
5. Fifth: Test with various citation patterns
6. Sixth: Add comprehensive verification summary

## Files Modified
- `orthodox_generator.py` - Prompt assembly fix ✅
- `unorthodox_generator.py` - Prompt assembly fix ✅
- `strategies.yaml` - Format instructions, counts
- `core.py` - Extraction regex, plausibility, summary
- This documentation file

## Notes
- The bulk plausibility implementation is architecturally sound
- Main issue is format consistency from LLMs
- Once format is reliable, entire pipeline should work
- Consider adding retry logic if format is wrong