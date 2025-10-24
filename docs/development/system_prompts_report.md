# LitAssist System Prompts Report

**Last Updated**: October 22, 2025 (Updated from January 2025 version)
**Status**: Reference Document

## Overview

This report documents all system prompts used across LitAssist commands and their submodes, including the exact prompt keys and code construction patterns.

**Purpose**: This document serves as a quick reference for developers to understand:
- How system prompts are constructed for each command
- Which YAML prompt keys are used where
- Patterns for combining base prompts with command-specific prompts

**Note**: All prompts are externalized to YAML files per CLAUDE.md policy. This document maps code → YAML keys.

## System Prompts by Command

### 1. lookup command

**Standard mode:**

```python
system_content = PROMPTS.get("base.australian_law") + "\n\n" + PROMPTS.get("lookup.standard_analysis.instructions")
```

**Extraction mode:**

```python
system_content = PROMPTS.get("base.australian_law") + "\n\n" + PROMPTS.get("lookup.extraction_system")
```

**Comprehensive mode:**

```python
system_content = f"""{PROMPTS.get("base.australian_law")} Provide exhaustive legal analysis.

{PROMPTS.get("lookup.comprehensive_analysis.requirements")}

{PROMPTS.get("lookup.comprehensive_analysis.citation_requirements")}

{PROMPTS.get("lookup.comprehensive_analysis.output_structure")}"""
```

### 2. brainstorm command

**Orthodox strategies:**

```python
{"role": "system", "content": PROMPTS.get("commands.brainstorm.orthodox_system")}
```

**Unorthodox strategies:**

```python
{"role": "system", "content": PROMPTS.get("commands.brainstorm.unorthodox_system")}
```

**Analysis mode:**

```python
{"role": "system", "content": PROMPTS.get("commands.brainstorm.analysis_system")}
```

### 3. strategy command

**Main generation:**

```python
system_prompt = PROMPTS.get("commands.strategy.system")
```

**Ranking submode (in ranker.py):**

```python
system_prompt = PROMPTS.get("commands.strategy.ranking_system")
```

### 4. caseplan command

**Standard mode:**

```python
system_prompt = PROMPTS.get("commands.caseplan.system").format(
    outcome_type=outcome_type,
    outcome_details=outcome_details
)
```

**Budget assessment mode:**

```python
system_prompt = PROMPTS.get("commands.caseplan.budget_assessment_system")
```

### 5. barbrief command

```python
{"role": "system", "content": PROMPTS.get("barbrief.system")}
```

### 6. draft command

```python
system_prompt = PROMPTS.get("processing.draft.system_prompt_base")
if template_content:
    system_prompt += "\n\n" + PROMPTS.get("processing.draft.system_prompt_template")
```

### 7. digest command

```python
{"role": "system", "content": PROMPTS.get("processing.digest.system_prompt")}
```

### 8. extractfacts command

```python
{"role": "system", "content": PROMPTS.get_system_prompt("extractfacts")}
# Which internally does:
# PROMPTS.get("base.australian_law") + " " + PROMPTS.get("commands.extractfacts.system")
```

### 9. verify command

**Standard verification:**

```python
{"role": "system", "content": PROMPTS.get("verification.system_prompt")}
```

**Heavy verification mode:**

```python
{"role": "system", "content": PROMPTS.get("verification.heavy_verification_system")}
```

### 10. counselnotes command

**Extraction stage:**

```python
{"role": "system", "content": PROMPTS.get("processing.counselnotes.extraction_system")}
```

**Strategic analysis stage:**

```python
{"role": "system", "content": PROMPTS.get("processing.counselnotes.strategic_system")}
```

**Consolidation stage:**

```python
{"role": "system", "content": PROMPTS.get("processing.counselnotes.consolidation_system")}
```

### 11. CoVe (Chain of Verification)

**Location**: `litassist/verification_chain.py`

Used by multiple commands (verify, draft, barbrief, counselnotes, extractfacts, strategy).

**Chain of Verification prompts** (from `verification.yaml`):
- `verification.cove.questions_system` - Generate verification questions
- `verification.cove.answers_system` - Answer questions with full context
- `verification.cove.inconsistency_system` - Detect inconsistencies
- `verification.cove.regeneration_system` - Regenerate corrected content

**Models Used** (October 2025):
- Questions: Claude Sonnet 4.5 (cove-questions client)
- Answers: GPT-5 (cove-answers client) - 1.4% hallucination rate
- Verify: Claude Sonnet 4.5 (cove-verify client)
- Final: GPT-5 Pro (cove-final client) - <1% hallucination rate

### 12. Base/Fallback System Prompt

```python
# Applied to all commands if no system message provided:
system_content = PROMPTS.get("base.australian_law")
```

## Special Cases

### LLMClient Auto-Injection

Location: `litassist/llm/client.py:876-890`

```python
# If no system message in messages:
system_content = PROMPTS.get("base.australian_law")

# If o1-preview model and has system message:
system_content += "\n" + PROMPTS.get("base.australian_law")
```

### Tool-Based Prompts

When using tools, adds to existing system prompt:

```python
system_content += "\n\n" + PROMPTS.get("base.tool_instructions")
```

## Prompt Key Locations

| Command | File | Prompt Keys |
|---------|------|-------------|
| lookup | `litassist/commands/lookup/processors.py` | `base.australian_law`, `lookup.standard_analysis.instructions`, `lookup.extraction_system`, `lookup.comprehensive_analysis.*` |
| brainstorm | `litassist/commands/brainstorm/*.py` | `commands.brainstorm.orthodox_system`, `commands.brainstorm.unorthodox_system`, `commands.brainstorm.analysis_system` |
| strategy | `litassist/commands/strategy/core.py` | `commands.strategy.system`, `commands.strategy.ranking_system` |
| caseplan | `litassist/commands/caseplan.py` | `commands.caseplan.system`, `commands.caseplan.budget_assessment_system` |
| barbrief | `litassist/commands/barbrief.py` | `barbrief.system` |
| draft | `litassist/commands/draft.py` | `processing.draft.system_prompt_base`, `processing.draft.system_prompt_template` |
| digest | `litassist/commands/digest/core.py` | `processing.digest.system_prompt` |
| extractfacts | `litassist/commands/extractfacts.py` | `base.australian_law`, `commands.extractfacts.system` |
| verify | `litassist/commands/verify.py` | `verification.system_prompt`, `verification.heavy_verification_system` |
| counselnotes | `litassist/commands/counselnotes.py` | `processing.counselnotes.extraction_system`, `processing.counselnotes.strategic_system`, `processing.counselnotes.consolidation_system` |

## Prompt Files

All prompts are defined in YAML files under `litassist/prompts/`:

- `base.yaml` - Base Australian law requirements and common prompts
- `barbrief.yaml` - Barrister brief prompts
- `caseplan.yaml` - Case planning prompts
- `lookup.yaml` - Lookup and analysis prompts
- `processing.yaml` - Draft, digest, counselnotes prompts
- `verification.yaml` - Verification and CoVe prompts
- `strategies.yaml` - Strategy command prompts
- `reasoning.yaml` - Legal reasoning trace prompts
- `analysis.yaml` - Analysis and ranking prompts
- `documents.yaml` - Legal document templates
- `formats.yaml` - Output format specifications
- `capabilities.yaml` - Command capability descriptions
- `system_feedback.yaml` - User feedback and help prompts
- `glob_help_addon.yaml` - Glob pattern help

## Key Patterns

1. **Base + Command**: Most commands combine `base.australian_law` with command-specific prompts
2. **Mode-Specific**: Commands with modes (lookup, brainstorm, verify) use different prompts per mode
3. **Stage-Specific**: Multi-stage commands (counselnotes, CoVe) may use different prompts per stage
4. **Dynamic Construction**: Some prompts are built dynamically (e.g., lookup comprehensive mode)
5. **Format Parameters**: Some prompts accept format parameters (e.g., caseplan with outcome details)

## Key Changes Since January 2025

### October 2025 Model Upgrade
- **Three-Tier Strategy**: Critical verification (GPT-5 Pro), Fast verification (GPT-5), Legal reasoning (Claude Sonnet 4.5)
- **Verification Commands**: Split into verification, verification-heavy, verification-light
- **CoVe Models**: Now uses GPT-5 family for answers and final stages (accuracy improvement)

### Prompt Management Architecture
- **PromptManager**: Centralized singleton at `litassist/prompts.py`
- **Lazy Loading**: Templates loaded on first access
- **Dot Notation**: All prompts accessed via `PROMPTS.get("category.subcategory.key")`
- **No Hardcoded Prompts**: Enforced policy in CLAUDE.md

## Notes

- All commands enforce Australian law compliance through the base prompt
- System prompts define the AI's role (e.g., "senior solicitor", "senior barrister")
- Task-specific instructions are included in system prompts for consistent behavior
- CoVe verification uses dedicated system prompts for each stage (not inherited from calling command)
- **Policy**: Never hardcode prompts in Python; always use YAML externalization

## Related Documentation

- `ARCHITECTURE_ANALYSIS_2025.md` - Comprehensive architecture analysis
- `MODEL_CONFIGURATION.md` - Model selection and configuration details
- `VERIFICATION_SYSTEM_COMPREHENSIVE.md` - Verification chain architecture
- `CLAUDE.md` - Development guidelines including prompt management policy

---

**Generated**: January 6, 2025
**Updated**: October 22, 2025
