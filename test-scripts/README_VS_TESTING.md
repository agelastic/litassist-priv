# Verbalized Sampling Exploratory Testing

## Overview

This test compares three approaches for implementing Verbalized Sampling in litassist:

1. **VS-JSON**: Verbalized Sampling with JSON format (full paper implementation)
2. **VS-Markdown**: Verbalized Sampling with markdown + probability annotations (simpler)
3. **Baseline**: Current plain markdown (control)

## Running the Test

```bash
cd /Users/witt/Projects/litassist
python test-scripts/test_vs_exploration.py
```

**Duration:** ~24 minutes (18 LLM calls)

## What It Tests

### Strategy Types

Tests **BOTH orthodox and unorthodox strategies** (18 total calls):
- Orthodox: Conservative, precedent-based approaches
- Unorthodox: Creative, innovative approaches (where VS has highest expected impact)

### Automated Metrics

1. **Parse Success Rate**: Can we reliably extract strategies from LLM output?
   - Target: ≥95% (all 3 runs succeed)
   - Tested separately for orthodox and unorthodox

2. **Diversity Improvement**: How many unique strategy titles across 3 identical runs?
   - Target: ≥1.3x improvement vs baseline
   - Paper reported: 1.6-2.1x improvement
   - Tested separately for orthodox and unorthodox

3. **Probability Extraction**: Can we extract probability scores?
   - Important for VS-JSON (needed for ranking)
   - Optional for VS-Markdown

### Output Files

```
outputs/vs_exploration_YYYYMMDD_HHMMSS/
├── test_report.txt                          # Main report with recommendations
├── orthodox_baseline_run1_raw.txt           # Raw LLM responses
├── orthodox_baseline_run1_extracted.json    # Parsed strategies
├── orthodox_vs-json_run1_raw.txt
├── orthodox_vs-json_run1_extracted.json
├── orthodox_vs-markdown_run1_raw.txt
├── orthodox_vs-markdown_run1_extracted.json
├── unorthodox_baseline_run1_raw.txt
├── unorthodox_baseline_run1_extracted.json
├── unorthodox_vs-json_run1_raw.txt
├── unorthodox_vs-json_run1_extracted.json
├── unorthodox_vs-markdown_run1_raw.txt
└── unorthodox_vs-markdown_run1_extracted.json
```

## Manual Quality Review (After Test)

The automated test checks parsing and diversity. You must manually assess quality:

### Review 3 Strategies from Each Approach

```bash
# View first 3 orthodox strategies from each approach
cd outputs/vs_exploration_YYYYMMDD_HHMMSS/
cat orthodox_baseline_run1_extracted.json | jq '.[0:3]'
cat orthodox_vs-json_run1_extracted.json | jq '.[0:3]'
cat orthodox_vs-markdown_run1_extracted.json | jq '.[0:3]'

# View first 3 unorthodox strategies from each approach
cat unorthodox_baseline_run1_extracted.json | jq '.[0:3]'
cat unorthodox_vs-json_run1_extracted.json | jq '.[0:3]'
cat unorthodox_vs-markdown_run1_extracted.json | jq '.[0:3]'
```

### Quality Checklist (per strategy)

- [ ] Legally sound (correct legal principles)
- [ ] Relevant to case facts (residential tenancies dispute)
- [ ] Citations properly formatted (Australian format)
- [ ] Explanation has adequate depth (3-5 paragraphs)
- [ ] Likelihood assessment reasonable
- [ ] Risk considerations present

## Decision Criteria

### Proceed with VS if:
- ✓ Parse success rate ≥95%
- ✓ Diversity improvement ≥1.3x
- ✓ Quality review shows no degradation

### Choose approach:
- **VS-JSON** if you want probabilities for ranking/analysis
- **VS-Markdown** if simplicity is more important

### Abandon VS if:
- ✗ Parse success <95%
- ✗ Diversity improvement <1.3x
- ✗ Quality significantly degraded

## Interpreting Results

### Good Results Look Like:

```
SUMMARY COMPARISON
Approach             Parse Success   Total      Unique     Diversity
--------------------------------------------------------------------------------
Baseline (Current)   100%            50         35         70%
VS-JSON              100%            50         47         94%
VS-Markdown          100%            50         45         90%

DIVERSITY IMPROVEMENT vs BASELINE:
  VS-JSON:     1.34x  ← PASS (≥1.3x target)
  VS-Markdown: 1.29x  ← CLOSE (just below target)
```

### Bad Results Look Like:

```
SUMMARY COMPARISON
Approach             Parse Success   Total      Unique     Diversity
--------------------------------------------------------------------------------
Baseline (Current)   100%            50         35         70%
VS-JSON              60%             30         25         83%  ← FAIL (parse)
VS-Markdown          100%            50         37         74%  ← FAIL (diversity)

DIVERSITY IMPROVEMENT vs BASELINE:
  VS-JSON:     0.71x  ← FAIL (worse than baseline!)
  VS-Markdown: 1.06x  ← FAIL (below 1.3x target)
```

## Next Steps

### If VS-JSON passes:
1. Implement JSON parsing in orthodox_generator.py
2. Implement JSON parsing in unorthodox_generator.py
3. Update prompts in strategies.yaml
4. Keep regeneration as-is (uses markdown)

### If VS-Markdown passes:
1. Update prompts in strategies.yaml (add probability line)
2. No code changes needed (markdown passes through)
3. Probabilities displayed but not parsed

### If both fail:
1. Document findings in project notes
2. Consider alternative diversity approaches
3. Archive test results for future reference

## Test Case

The test uses a residential tenancies dispute (NSW):
- Tenant withheld rent due to water damage/mold
- Landlord issued eviction notice
- Tenant filed NCAT application
- Focus: Orthodox strategies for tenant (applicant)

This is representative of typical litassist use cases.

## Troubleshooting

### Import Errors
```bash
# Make sure you're in the project root
cd /Users/witt/Projects/litassist
# Run with python3 explicitly
python3 test-scripts/test_vs_exploration.py
```

### API Key Issues
```bash
# Check config
cat config.yaml | grep -i openrouter
# Or check environment
echo $OPENROUTER_API_KEY
```

### Model Not Available
Edit test script line 280 to use different model:
```python
client = LLMClient(
    model="anthropic/claude-sonnet-4.5",  # change to another model
    temperature=0.3,
    top_p=0.7
)
```

## Cost Estimate

- 18 LLM calls (2 strategy types × 3 approaches × 3 runs)
- ~1000 tokens input per call
- ~3000 tokens output per call (10 strategies)
- Total: ~72K tokens
- Cost: ~$0.60-1.20 (depends on model pricing)

## Questions?

Check the full analysis documents:
- claude_vs_analysis.md - Strategic analysis
- claude_vs_prompt_examples.md - Implementation examples
