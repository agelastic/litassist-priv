# Unmerged Commits Analysis
Generated: 2025-08-19

## feature/prompts-cleanup branch

### Commit 1: 9cb669a - Prompt Documentation and Cleanup
**Author:** Vitaly Osipov  
**Date:** Sat Aug 2 19:42:46 2025 +1000

**Changes:**
- Added USED BY / LOCATION comments to track prompt usage
- Marked obsolete prompts as DEPRECATED (citation, accuracy, verification standards)
- Removed unused system prompts from extractfacts, lookup, brainstorm

**Impact:** Documentation improvement and code cleanup

### Commit 2: fedb297 - Australian Law Context Automation
**Author:** Vitaly Osipov  
**Date:** Fri Aug 1 18:07:34 2025 +1000

**Changes:**
- Modified `litassist/llm.py` to automatically inject Australian law context
- Removed redundant "Australian law only" phrases from individual prompts
- Updated tests to match new behavior

**Impact:** Code improvement - DRY principle applied to prompt system

## Recommendation
Both commits appear valuable:
- First improves documentation and removes unused code
- Second implements a systematic improvement to prompt handling

Consider merging to master after verification that tests pass.