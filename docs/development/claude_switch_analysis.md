# Comprehensive Analysis of LitAssist Command-Line Switches

Based on my analysis of the codebase, here's a complete inventory of all command-line switches in LitAssist, organized by purpose and noting overlapping functionality.

## Global Options (apply to all commands)
- `--log-format` (json|markdown) - Format for audit logs
- `--verbose` - Enable debug-level logging

## Command-Specific Switches

### 1. AI Guidance Switches (provide context/instructions to LLM)
These switches serve similar purposes of guiding the AI's analysis:
- **`--context`** (digest) - Optional additional context to guide the analysis
- **`--context`** (caseplan) - Additional context to guide the analysis  
- **`--context`** (lookup) - Contextual information to guide the lookup analysis
- **`--context`** (barbrief) - Additional context to guide the analysis
- **`--outcome`** (strategy) - Desired outcome to achieve (required)

### 2. Verification Switches
Multiple commands have `--verify` but with different behaviors:
- **`--verify`** (draft) - Enable self-critique pass
- **`--verify`** (extractfacts) - Enable self-critique pass (auto-enabled by default)
- **`--verify`** (strategy) - Enable self-critique pass (auto-enabled by default)
- **`--verify`** (barbrief) - Enable citation verification
- **`--verify`** (counselnotes) - Enable citation verification for extracted content

Verify command has specialized flags:
- **`--citations`** (verify) - Verify citations only
- **`--soundness`** (verify) - Verify legal soundness only
- **`--reasoning`** (verify) - Verify/generate reasoning trace only

### 3. Mode/Type Selection Switches
- **`--mode`** (lookup) - Choose analysis mode: irac|broad (default: irac)
- **`--mode`** (digest) - Choose digest type: summary|issues (default: summary)
- **`--extract`** (lookup) - Extract specific info: citations|principles|checklist
- **`--extract`** (counselnotes) - Extract elements: all|citations|principles|checklist

### 4. Input File Switches
These accept multiple files and support glob patterns:
- **`--facts`** (brainstorm) - Multiple facts files with glob support
- **`--research`** (brainstorm, barbrief) - Multiple lookup reports with glob support
- **`--strategies`** (barbrief) - Multiple strategy files with glob support
- **`--strategies`** (strategy) - Single strategies file from brainstorm
- **`--documents`** (barbrief) - Supporting documents with glob support

### 5. Case Context Switches
- **`--side`** (brainstorm) - Which side: plaintiff|defendant|accused|respondent (required)
- **`--area`** (brainstorm) - Legal area: criminal|civil|family|commercial|administrative (required)
- **`--hearing-type`** (barbrief) - Type: trial|directions|interlocutory|appeal (required)

### 6. Other Switches
- **`--comprehensive`** (lookup) - Use exhaustive analysis (40 sources vs 5)
- **`--diversity`** (draft) - Control diversity of search results (0.0-1.0)
- **`--budget`** (caseplan) - Budget constraint: minimal|standard|comprehensive
- **`--output`** (counselnotes) - Custom output filename prefix

## Key Observations on Overlapping Switches

1. **Guidance switches** (hint/focus/context/instructions) all serve to provide additional context to guide the AI, but are command-specific. Consider standardizing to a single `--context` or `--guidance` switch across all commands.

2. **Verify switches** appear in 5 commands but behave differently:
   - Some enable self-critique (draft, extractfacts, strategy)
   - Others enable citation verification (barbrief, counselnotes)
   - Some auto-enable it regardless of flag (extractfacts, strategy)

3. **Mode and extract switches** both control output format but use different names. Could be standardized.

4. **File input switches** have good consistency - most support multiple files and glob patterns through a shared callback function.

5. **Required vs optional**: Some switches like `--outcome`, `--side`, `--area`, and `--hearing-type` are required, while most others are optional enhancements.

This analysis reveals opportunities for standardization while respecting command-specific needs. The most obvious candidates for consolidation are the guidance switches (hint/focus/context/instructions) and potentially the verify behavior across commands.