# LitAssist CLI Switch Standardization Plan

## Overview
This plan proposes standardizing command-line switches across LitAssist commands to improve consistency, reduce user confusion, and maintain backwards compatibility where feasible.

## Proposed Standardizations

### 1. Guidance Switches → `--context`
**Current state**: Different commands use different switches for AI guidance:
- `--hint` (digest)
- `--focus` (caseplan)
- `--context` (lookup)
- `--instructions` (barbrief)
- `--outcome` (strategy) - special case, remains separate

**Proposed change**: Standardize to `--context` for all guidance switches except `--outcome`

**Implementation**:
```python
# All commands would use:
@click.option("--context", help="Additional context to guide the analysis")

# Maintain aliases for backwards compatibility:
@click.option("--hint", "--context", help="Additional context to guide the analysis")  # digest
@click.option("--focus", "--context", help="Additional context to guide the analysis")  # caseplan
@click.option("--instructions", "--context", help="Additional context to guide the analysis")  # barbrief
```

**Special case**: `--outcome` remains separate as it's a required parameter with specific semantic meaning for strategy command.

### 2. Verification Behavior Standardization
**Current state**: `--verify` behaves differently across commands:
- Self-critique: draft, extractfacts, strategy
- Citation verification: barbrief, counselnotes
- Auto-enabled: extractfacts, strategy

**Proposed change**: 
1. All `--verify` flags should explicitly state what they verify in help text
2. Commands that auto-enable should note this in help text
3. Consider splitting into `--verify-content` and `--verify-citations`

**Implementation**:
```python
# For self-critique commands:
@click.option("--verify", is_flag=True, help="Enable content verification and self-critique")

# For citation verification commands:
@click.option("--verify-citations", is_flag=True, help="Enable real-time citation verification")

# For auto-enabled commands:
@click.option("--verify", is_flag=True, help="Content verification (auto-enabled)")
```

### 3. Output Format Switches
**Current state**: 
- `--mode` (lookup, digest) - controls analysis style
- `--extract` (lookup, counselnotes) - controls extraction format

**Proposed change**: Keep as-is but ensure consistency in help text and choices

**Implementation**:
- Ensure all `--mode` options clearly describe output style
- Ensure all `--extract` options clearly describe extraction format
- Consider adding `--format` as a future unified option

### 4. File Input Switch Naming
**Current state**: Good consistency already exists
- Multiple files with glob: `--facts`, `--research`, `--strategies`, `--documents`
- Single file: `--strategies` (strategy command)

**Proposed change**: Document glob support clearly in help text

**Implementation**:
```python
# For multi-file inputs:
help="Input files (supports multiple files and glob patterns like 'outputs/*.txt')"

# For single-file inputs:
help="Single input file (no glob support)"
```

### 5. Punctuation and Formatting Standards

**Current problematic formats in prompts and examples**:
- `--hint "ownership gift presumption advancement contributions"`
- `lookup "gift valid elements delivery acceptance donative intent motor vehicle"`

**Proposed standards**:
1. All example hints/contexts should be complete sentences with punctuation
2. Lookup queries should be natural questions or clear search phrases
3. Instructions should be clear directives with proper grammar

**Examples of improved formatting**:
```bash
# Hints/Context (AI guidance):
--context "Analyze ownership claims, gift presumptions, advancement doctrine, and financial contributions."
--context "Focus on timeline conflicts and financial discrepancies in the evidence."

# Lookup queries (Google search):
lookup "What are the valid elements of a gift? Include delivery, acceptance, and donative intent for motor vehicles."
lookup "Define detinue for motor vehicle possession and wrongful detention under ACT law."

# Instructions (specific directives):
--context "Emphasize the respondent's claim of gift despite vehicle registration in applicant's name."
--context "Prepare for cross-examination on financial contribution evidence."

# Outcome (strategy):
--outcome "Establish a resulting trust over the vehicle valued at $40,364."
--outcome "Recover possession of vehicle through detinue or conversion claim."
```

## Migration Strategy

### Phase 1: Documentation Update (Immediate)
1. Update all YAML prompt files with properly punctuated examples
2. Update capabilities.yaml with new standardized examples
3. Create migration guide for users

### Phase 2: Add Aliases (Version 1.x)
1. Add alias support to maintain backwards compatibility
2. Update help text to show preferred option
3. Add deprecation warnings for old switches (optional)

### Phase 3: Full Migration (Version 2.0)
1. Remove deprecated aliases
2. Update all documentation to use only new switches
3. Provide clear migration script for users

## Backwards Compatibility

To ensure smooth transition:
1. Implement aliases for all renamed switches
2. Maintain old behavior where switches are standardized
3. Provide clear deprecation timeline
4. Include migration examples in documentation

## Implementation Priority

1. **High Priority**: Fix punctuation in all prompts and examples (no breaking changes)
2. **Medium Priority**: Standardize guidance switches to `--context` with aliases
3. **Low Priority**: Clarify verification behavior across commands
4. **Future**: Consider unified `--format` option for output control

## Benefits

1. **Consistency**: Users learn one set of switches that work across commands
2. **Clarity**: Properly punctuated examples are easier to understand
3. **Professionalism**: Well-formatted strings enhance the tool's credibility
4. **Maintainability**: Fewer switch variations to document and maintain
5. **User Experience**: Reduced cognitive load when switching between commands