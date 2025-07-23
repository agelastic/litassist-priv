# Heartbeat Wrapping Implementation Plan

## Overview
Several LitAssist commands make LLM calls without heartbeat wrapping, causing them to appear stuck during long operations. This plan addresses the issue with minimal changes following CLAUDE.md principles.

## Current State Analysis

### Commands Using Heartbeat Wrapping ✅
1. **brainstorm.py** - All 3 LLM calls properly wrapped
2. **barbrief.py** - Fixed in recent update

### Commands Missing Heartbeat Wrapping ❌

#### 1. strategy.py
- **Total .complete() calls**: 4
- **With heartbeat**: 1 (line 286)
- **Missing heartbeat**: 3
  - Line 464: `analysis_client.complete()` - for strategy ranking
  - Line 813: `llm_client.complete()` - for next steps generation
  - Line 851: `llm_client.complete()` - for document generation

#### 2. digest.py
- **Total .complete() calls**: 3
- **With heartbeat**: 0
- **Missing heartbeat**: ALL
  - Line 200: `client.complete()` - single chunk processing
  - Line 252: `client.complete()` - chunk analysis in loop
  - Line 374: `client.complete()` - consolidation

#### 3. counselnotes.py
- **Total .complete() calls**: 5
- **With heartbeat**: 0
- **Missing heartbeat**: ALL
  - Line 125: `client.complete()` - extraction mode
  - Line 240: `client.complete()` - strategic analysis single chunk
  - Line 292: `client.complete()` - chunk analysis in loop
  - Line 338: `client.complete()` - consolidation
  - Line 298: `client.complete()` - sub-chunk processing

#### 4. extractfacts.py
- **Total .complete() calls**: 3
- **With heartbeat**: 0
- **Missing heartbeat**: ALL
  - Line 91: `client.complete()` - single chunk extraction
  - Line 118: `client.complete()` - chunk fact extraction in loop
  - Line 150: `client.complete()` - organizing facts

## Implementation Plan

### Minimal Change Approach (Following CLAUDE.md)

For each command, we need to:

1. **Check if CONFIG is imported** - Add `from litassist.config import CONFIG` if missing
2. **Create heartbeat wrapper** - Add before first LLM call:
   ```python
   call_with_hb = heartbeat(CONFIG.heartbeat_interval)(client.complete)
   ```
3. **Replace all .complete() calls** - Change from:
   ```python
   response, usage = client.complete(messages)
   ```
   To:
   ```python
   response, usage = call_with_hb(messages)
   ```

### Priority Order

1. **digest.py** - Most commonly used command, needs immediate fix
2. **extractfacts.py** - Foundation for other commands, important for demo
3. **strategy.py** - Fix remaining 3 calls (partial implementation exists)
4. **counselnotes.py** - Less frequently used but still important

### Implementation Notes

- Each command uses its own LLM client instance, so each needs its own wrapper
- For commands with multiple clients (like strategy.py with `llm_client` and `analysis_client`), create separate wrappers
- Maintain existing error handling - wrap only the `.complete()` method, not error handling
- Test each command after implementation to ensure heartbeat messages appear

### Expected Outcome

After implementation, all commands will show "…still working, please wait…" messages every 30 seconds during LLM operations, preventing the appearance of being stuck.

---

Created: 2025-01-23
Status: Ready for implementation