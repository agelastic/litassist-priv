# Hardcoded Prompts Audit Report

**Date:** 2025-01-21  
**Purpose:** Identify all hardcoded prompts in the LitAssist codebase that should be extracted to YAML files

## Executive Summary

This audit identifies hardcoded prompts in Python files that violate the centralized prompt management principle. The most significant finding is the reasoning trace prompt in `utils.py` which contains substantial multi-line prompt content that should be moved to YAML.

## Audit Findings

### 1. Critical Extractions Needed

#### utils.py - Legal Reasoning Trace Prompt
- **Location:** `create_reasoning_prompt()` function, lines ~861-879
- **Type:** Multi-line f-string with legal reasoning instructions
- **Content:** Full IRAC-format reasoning trace template
- **Priority:** HIGH - This is substantial prompt logic guiding LLM behavior
- **Action:** Extract to `base.yaml` as `reasoning.trace_instruction`

#### llm.py - Fallback Verification Prompts
- **Location:** `verify_with_level()` method, lines ~803-807
- **Type:** Hardcoded fallback strings for system_prompt and heavy_verification
- **Content:** Default prompts when YAML lookup fails
- **Priority:** MEDIUM - These should use YAML defaults instead
- **Action:** Move to `verification.yaml` as default entries

### 2. Acceptable Parametrized Strings (No Action Needed)

#### brainstorm.py
- Lines ~165-170: Citation retry instructions (simple f-string insertion)
- Lines ~285-304: Orthodox strategies format (template with variables)
- Lines ~312-331: Unorthodox strategies format (template with variables)
- Lines ~339-358: Analysis format (template with variables)
- Lines ~370-383: Content section combination (simple concatenation)

#### strategy.py
- Lines ~129-148: Base user prompt construction (inserts case facts)
- Lines ~226-242: Ranking prompt for remaining strategies
- Lines ~267-290: Ranking prompt for all strategies
- Lines ~315-329: Individual strategy development
- Lines ~405-410: Document generation context

#### lookup.py
- Lines ~142-151: System content with requirements (simple parameter insertion)

#### caseplan.py
- Lines ~172-177: Budget assessment prompt (inserts case facts)

### 3. Classification Criteria

**Should be extracted:**
- Multi-line prompt blocks with instructional content
- Prompts that define LLM behavior or output format
- Any prompt content > 3 lines
- Fallback/default prompts that duplicate YAML content

**OK to keep as code:**
- Simple f-strings that insert variables into YAML-loaded templates
- One-line parametrized messages
- Dynamic prompt construction based on runtime conditions
- Format strings that combine multiple YAML sections

## Recommended Extraction Plan

### Phase 1: Critical Extractions
1. **Extract reasoning trace prompt from utils.py**
   - Create new YAML entry: `base.reasoning.trace_instruction`
   - Update `create_reasoning_prompt()` to use `PROMPTS.get()`
   - Maintain `{command}` placeholder functionality

2. **Extract llm.py fallback prompts**
   - Add defaults to `verification.yaml`
   - Remove hardcoded fallbacks, rely on YAML defaults

### Phase 2: Documentation Updates
1. Update CLAUDE.md with explicit prompt centralization rules
2. Add linting rule or pre-commit hook to detect multi-line strings in Python files
3. Document the distinction between acceptable parametrized strings and prompts requiring extraction

## Progress Tracking

| File | Prompt | Status | Priority |
|------|---------|---------|-----------|
| utils.py | Reasoning trace instruction | ❌ Needs extraction | HIGH |
| llm.py | Fallback verification prompts | ❌ Needs extraction | MEDIUM |
| brainstorm.py | Various format strings | ✅ OK as parametrized | LOW |
| strategy.py | Various format strings | ✅ OK as parametrized | LOW |
| lookup.py | System content | ✅ OK as parametrized | LOW |
| caseplan.py | Budget prompt | ✅ OK as parametrized | LOW |

## Next Steps

1. Extract the reasoning trace prompt from utils.py (HIGH priority)
2. Update CLAUDE.md with prompt centralization principles
3. Consider automated detection of hardcoded prompts in CI/CD
4. Regular audits to ensure new code follows centralization principles

---

*This document should be updated as prompts are extracted or new hardcoded prompts are discovered.*