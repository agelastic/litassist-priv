# LitAssist Centralized Prompt Management

**Status**: Phase 1 Complete [DONE]  
**Last Updated**: July 31, 2025

## Recent Updates (July 2025)

- **Prompt YAML Overhaul**: Major updates to barbrief.yaml, strategies.yaml, verification.yaml, caseplan.yaml, formats.yaml, glob_help_addon.yaml, lookup.yaml, system_feedback.yaml for clarity, compliance, and chunk-aware prompting.
- **Zero-Emoji Policy**: All prompts and system feedback now enforce ASCII/ANSI-only output (no emoji) for professional compliance.
- **Chunk-Aware Prompting**: Digest, strategy, and brainstorm prompts now include instructions for 50k token chunk processing and user warnings for large files.
- **Verification Model**: Verification prompts updated for Claude 4 Opus as the default verification model.
- **File Size Warnings**: New prompt templates for research file size analysis and user warnings when exceeding 128k tokens.
- **CasePlan**: New and expanded prompts for phased workflow planning and command coverage analysis.
- **Digest/ExtractFacts**: Prompts updated for multi-file and chunked input handling.
- **System Feedback**: Expanded error and warning messages for chunking, token limits, and policy compliance.

## Recent Updates (June 2025)

- **Verify Command**: Added comprehensive verification prompts for citation checking, legal soundness, and reasoning trace generation
- **Digest --context Option**: Added context instruction templates for focused document analysis
- **Brainstorm --research Option**: Added research context injection capability for orthodox strategies
- **System Feedback**: Consolidated error and warning messages into system_feedback.yaml
- **Improved Organization**: All verification-related prompts now centralized in verification.yaml

## Overview

This document describes the centralized prompt management system implemented in Phase 1 and expanded in July 2025, designed to improve consistency, maintainability, and quality control across all LitAssist commands.

**July 2025: All prompt templates now support chunk-based processing, token counting, and zero-emoji output. PromptManager and YAMLs have been updated for new verification models and file size handling.**

## Architecture

### Core Components

- **`litassist/prompts.py`** - Main prompt management module with `PromptManager` class
- **`litassist/prompts/`** - YAML template directory containing organized prompt templates
- **Template Categories**:
  - `base.yaml` - Australian law requirements and system prompts
  - `formats.yaml` - Output format templates (IRAC, 10-headings, etc.)
  - `documents.yaml` - Legal document templates (Statement of Claim, etc.)
  - `warnings.yaml` - Error messages and validation warnings
  - `lookup.yaml` - Lookup command specific prompts
  - `processing.yaml` - Document processing prompts for digest and draft
  - `strategies.yaml` - Strategic analysis and brainstorming prompts
  - `barbrief.yaml` - Barrister's brief generation templates with 10-section structure
  - `verification.yaml` - Verification and self-critique prompts
  - `system_feedback.yaml` - Unified system feedback messages for errors and warnings
  - `caseplan.yaml` - Workflow planning prompt with command coverage, focus, and rationale enforcement (NEW July 2025)

### PromptManager API

```python
from litassist.prompts import PROMPTS

# Basic template retrieval
australian_law = PROMPTS.get('base.australian_law')

# System prompt generation for commands
system_prompt = PROMPTS.get_system_prompt('extractfacts')

# Format template retrieval
case_facts_format = PROMPTS.get_format_template('case_facts_10_heading')

# Document template retrieval
claim_template = PROMPTS.get_document_template('statement_of_claim', 
                                                court_name="Supreme Court of NSW")

# Template composition
composed = PROMPTS.compose_prompt('base.australian_law', 'base.citation_standards')
```

## Implemented Templates

### CasePlan Prompts (`caseplan.yaml`)

- **Purpose**: Drives the `caseplan` command for phased workflow planning.
- **Key Features**:
  - Enforces rationale for every command/phase
  - **NEW: Switch Explanation Requirements (Section 2F)** - Every command includes `# Switch rationale:` explaining technical choices
  - **NEW: Improved Parameter Readability** - All examples use coherent phrases instead of keyword strings
  - Requires explicit command coverage analysis (lookup, brainstorm, strategy, counselnotes, draft, barbrief, verify)
  - Integrates focus area prioritization and relevance scoring
  - Mandates structured output: Name, Purpose, Commands, Rationale, Focus Relevance, Cost, Tag
  - Final section: "COMMAND COVERAGE ANALYSIS" with justification for any omitted commands
- **Switch Explanation Format**:
  ```bash
  litassist lookup "query text" --mode irac --comprehensive
  # Switch rationale: --comprehensive for novel legal area, --mode irac for structured court analysis
  ```
- **Prompt Engineering**: Designed to minimize local parsing and maximize LLM-structured output, in line with CLAUDE.md and memory bank principles.
- **Location**: `litassist/prompts/caseplan.yaml`

### Base System Prompts (`base.yaml`)

- **`base.australian_law`** - Core Australian law requirement used in ALL commands
- **`base.citation_standards`** - Citation format requirements
- **`base.accuracy_standards`** - Factual accuracy requirements
- **`base.verification_standards`** - Verification instructions
- **`commands.*`** - Command-specific system prompt components

### Format Templates (`formats.yaml`)

- **`case_facts_10_heading`** - 10-heading case facts structure (extractfacts, strategy)
- **`strategic_options`** - Strategic options format (brainstorm, strategy)
- **`irac_structure`** - IRAC analysis format (lookup)
- **`chronological_summary`** - Chronological summary format (digest)
- **`citation_extraction`** - Citation list format (lookup --extract citations)
- **`principles_extraction`** - Principles list format (lookup --extract principles)
- **`checklist_extraction`** - Checklist format (lookup --extract checklist)

### Document Templates (`documents.yaml`)

- **`statement_of_claim`** - Complete Statement of Claim template
- **`originating_application`** - Originating Application template
- **`affidavit`** - Affidavit template with oath/affirmation
- **`notice_of_motion`** - Notice of Motion template
- **`outline_submissions`** - Outline of Submissions template
- **`interlocutory_application`** - Interlocutory Application template

### Warning Templates (`warnings.yaml`)

- **`citation_validation_header`** - Citation warning headers
- **`file_size_exceeded`** - File size validation messages
- **`side_area_mismatch`** - Command validation warnings
- **`case_facts_missing_headings`** - Case facts structure validation
- **`api_key_placeholder`** - API connectivity warnings
- **`byok_required`** - BYOK setup instructions

### Lookup Prompts (`lookup.yaml`)

- **`research_assistant`** - Jade.io research assistant system prompt
- **`comprehensive_analysis`** - Exhaustive analysis requirements for --comprehensive mode
- **`extraction_instructions`** - Instructions for --extract mode
- **`standard_user_template`** - Standard user prompt format

### Processing Prompts (`processing.yaml`)

- **`digest.summary_mode`** - Chronological summary extraction
- **`digest.issues_mode`** - Legal issues identification
- **`digest.system_prompt`** - Digest command system prompt
- **`digest.summary_mode_context_instruction_with_context`** - Context instruction when --context provided
- **`digest.summary_mode_context_instruction_no_context`** - Default context instruction
- **`digest.issues_mode_context_instruction_with_context`** - Issues mode context with user guidance
- **`digest.issues_mode_context_instruction_no_context`** - Default issues mode context
- **`draft.system_prompt_base`** - Base system prompt for drafting
- **`draft.context_aware_prompt`** - Context-aware drafting with strategic alignment
- **`draft.user_prompt_template`** - User prompt structure
- **`extraction.*`** - Multi-chunk extraction prompts for extractfacts

### Strategy Prompts (`strategies.yaml`)

- **`brainstorm.orthodox_prompt`** - Conservative legal strategies generation (supports {research_context} placeholder)
- **`brainstorm.unorthodox_prompt`** - Creative legal strategies generation
- **`brainstorm.analysis_prompt`** - Strategy analysis and prioritization
- **`brainstorm.regeneration_prompt`** - Feedback-based regeneration
- **`strategy.strategic_options_instructions`** - Formal strategic options format
- **`strategy.next_steps_prompt`** - Immediate action items generation
- **`strategy.document_generation_context`** - Strategic document alignment

### Verification Prompts (`verification.yaml`)

- **`self_critique`** - Default legal accuracy verification
- **`citation_retry_instructions`** - Enhanced instructions for citation failures
- **`light_verification`** - Australian English compliance only
- **`heavy_verification`** - Comprehensive legal accuracy review
- **`system_prompt`** - Verification system prompt

## Commands Updated

### Phase 1 Implementation - COMPLETE [Y]

[Y] **`llm.py`** - Imports PROMPTS module  
[Y] **`extractfacts.py`** - Fully integrated with centralized prompts  
[Y] **`lookup.py`** - Fully integrated with centralized prompts  
[Y] **`brainstorm.py`** - Fully integrated with centralized prompts  
[Y] **`strategy.py`** - Fully integrated with centralized prompts  
[Y] **`draft.py`** - Fully integrated with centralized prompts  
[Y] **`digest.py`** - Fully integrated with centralized prompts  
[Y] **`barbrief.py`** - Fully integrated with centralized prompts (2025 addition)  

**Integration Status**: All commands now use centralized prompt templates from the YAML files, with comprehensive coverage of system prompts, format templates, and document templates.

## Benefits Achieved

### 1. Consistency
- [Y] Single source of truth for Australian law requirements
- [Y] Standardized citation format instructions across commands
- [Y] Uniform document structure templates

### 2. Maintainability
- [Y] Easy to update legal document formats in one place
- [Y] Clear separation of prompt logic from business logic
- [Y] Version control for prompt evolution

### 3. Quality Control
- [Y] Standardized error messages and warnings
- [Y] Centralized validation templates
- [Y] Consistent Australian legal compliance

### 4. Flexibility
- [Y] Template parameter substitution
- [Y] Prompt composition capabilities
- [Y] Error handling for missing templates

## Usage Patterns

### Command Integration Pattern

```python
# Standard pattern used in commands
from litassist.prompts import PROMPTS

# Get system prompt
system_prompt = PROMPTS.get_system_prompt('command_name')

# Get format template
format_template = PROMPTS.get_format_template('template_name')

# Get document template with parameters
document = PROMPTS.get_document_template('statement_of_claim',
                                        court_name="Federal Court of Australia",
                                        file_number="NSD123/2025")
```

### Template Customization

```python
# Template with parameter substitution
document = PROMPTS.get('documents.statement_of_claim',
                       court_name="Federal Court of Australia",
                       file_number="NSD123/2025",
                       plaintiff_name="John Smith")
```

## Testing

### Automated Tests

- **`test_prompts.py`** - Simple integration test script
- **`tests/unit/test_prompts.py`** - Comprehensive pytest suite
- Tests include:
  - Template loading and validation
  - API method functionality
  - Fallback behavior
  - Edge cases and error handling

### Manual Testing

```bash
# Run simple test script
python test_prompts.py

# Run comprehensive pytest suite
python -m pytest tests/unit/test_prompts.py -v
```

## Future Work

### Phase 2: Complete Command Migration
- Integrate centralized prompts into all commands
- Remove hardcoded prompts from command files
- Implement graceful fallbacks where appropriate

### Phase 3: Advanced Features
- Template inheritance and composition
- Jurisdiction-specific prompt sets
- Client-specific customizations
- Prompt performance analytics
- A/B testing support

## Migration Guide

To integrate centralized prompts into a command:

1. **Import prompt manager**: `from litassist.prompts import PROMPTS`
2. **Replace hardcoded prompts**: 
   ```python
   # Old
   system_prompt = "Australian law only..."
   
   # New
   system_prompt = PROMPTS.get_system_prompt('command_name')
   ```
3. **Use format templates**:
   ```python
   format_template = PROMPTS.get_format_template('template_name')
   ```
4. **Test thoroughly**: Ensure the command works with centralized prompts

## File Structure

```
litassist/
├── prompts.py                 # Core prompt management module
├── prompts/                   # Template directory
│   ├── base.yaml             # System prompts & Australian law requirements
│   ├── formats.yaml          # Output format templates
│   ├── documents.yaml        # Legal document templates
│   ├── warnings.yaml         # Warning and error messages
│   ├── lookup.yaml           # Lookup command prompts
│   ├── processing.yaml       # Digest/draft processing prompts
│   ├── strategies.yaml       # Brainstorm/strategy prompts
│   └── verification.yaml     # Verification prompts
test_prompts.py               # Simple test script
tests/unit/test_prompts.py    # Comprehensive pytest suite
```

## Notes

- All templates support parameter substitution using `{parameter_name}` syntax
- Missing templates raise `KeyError` with descriptive messages
- Templates are loaded once at startup for performance
- YAML files allow multiline strings with preserved formatting
