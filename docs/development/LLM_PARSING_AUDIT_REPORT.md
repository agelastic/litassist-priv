# LLM Response Parsing Audit Report

**Date**: June 17, 2025  
**Last Updated**: July 7, 2025  
**Purpose**: Comprehensive audit of LLM response parsing throughout the litassist codebase  
**Goal**: Plan systematic elimination of local parsing through better prompt engineering

## Update (July 7, 2025)

**Progress on Parsing Removal**:
- **CasePlan prompt (July 2025):** New caseplan.yaml prompt enforces rationale, command coverage, and focus area in LLM output, minimizing local parsing for workflow planning.
- [DONE] **COMPLETED**: Removed ~25 lines of verification parsing in `brainstorm.py` (lines 481-500)
- [DONE] **PRINCIPLE APPLIED**: Trust well-prompted LLMs to return correct format
- [DONE] **TOKEN LIMITS**: Increased verification limits to 8192-16384 to avoid truncation
- [TODO] **ONGOING**: Continue removing parsing patterns identified in this audit  

## Executive Summary

This audit identified **extensive LLM response parsing** throughout the litassist codebase that can be eliminated through better prompt engineering. The current approach relies heavily on regex patterns, string manipulation, and complex parsing logic to extract structured data from LLM text responses.

**Key Findings:**
- 15+ major parsing patterns across 8 core files
- 200+ lines of regex-based parsing logic
- Complex multi-stage parsing workflows with fallback logic
- Extensive string manipulation of LLM outputs
- Multiple error handling layers around parsing failures

**Recommendation**: Replace all parsing logic with structured output requests in prompts (JSON/YAML format).

---

## 1. Regular Expression Parsing of LLM Outputs

### 1.1 Legal Reasoning Trace Extraction
**File**: `litassist/utils.py:778-838`  
**Impact**: HIGH - Core functionality across all commands  
**Description**: Complex regex parsing to extract IRAC-based legal reasoning traces  
**Current Approach**: Multiple regex patterns to extract Issue, Applicable Law, Application, Conclusion, Confidence, and Sources  
**Structured Output**: `LegalReasoningTrace` objects  

**Current Patterns**:
```python
trace_pattern = r"=== LEGAL REASONING TRACE ===\s*\n(.*?)(?=\n===|$)"
"issue": r"Issue:\s*(.*?)(?=\n\s*Applicable Law:|\n\s*Application to Facts:|\n\s*Conclusion:|\n\s*Confidence:|\n\s*Sources:|\Z)"
"applicable_law": r"Applicable Law:\s*(.*?)(?=\n\s*Application to Facts:|\n\s*Conclusion:|\n\s*Confidence:|\n\s*Sources:|\Z)"
"application": r"Application to Facts:\s*(.*?)(?=\n\s*Conclusion:|\n\s*Confidence:|\n\s*Sources:|\Z)"
"conclusion": r"Conclusion:\s*(.*?)(?=\n\s*Confidence:|\n\s*Sources:|\Z)"
"confidence": r"Confidence:\s*(\d+)%"
"sources": r"Sources:\s*(.*?)(?=\n\s*$|\Z)"
```

**Refactoring Approach**: Request JSON format for legal reasoning traces:
```json
{
  "legal_reasoning_trace": {
    "issue": "string",
    "applicable_law": "string", 
    "application": "string",
    "conclusion": "string",
    "confidence": 85,
    "sources": ["source1", "source2"]
  }
}
```

### 1.2 Soundness Issues Parsing
**File**: `litassist/commands/verify.py:272-291`  
**Impact**: MEDIUM - Document verification functionality  
**Description**: Extracts legal soundness issues from structured LLM response sections  
**Current Approach**: Regex to find "## Issues Found" section and extract numbered list items  

**Current Patterns**:
```python
match = re.search(r"## Issues Found\s*\n(.*?)(?:\n## |\Z)", soundness_result, re.DOTALL | re.IGNORECASE)
m = re.match(r"\s*\d+\.\s+(.*)", line)
```

**Refactoring Approach**: Request structured list format:
```json
{
  "issues_found": [
    "Issue description 1",
    "Issue description 2"
  ]
}
```

### 1.3 Strategy Content Parsing
**File**: `litassist/commands/brainstorm.py:59-179`  
**Impact**: HIGH - Core brainstorming functionality  
**Description**: Splits strategies into individual numbered items for selective regeneration  
**Current Approach**: Regex split on numbered list patterns, then regex matching for validation  

**Current Patterns**:
```python
strategies = re.split(r"\n(?=\d+\.\s+)", original_content.strip())
strategies = [s.strip() for s in strategies if re.match(r"^\d+\.", s.strip())]
strategy_lines[0] = re.sub(r"^\d+\.", f"{i}.", strategy_lines[0])
```

**Refactoring Approach**: Request JSON array of strategies:
```json
{
  "strategies": [
    {
      "number": 1,
      "content": "Strategy description"
    }
  ]
}
```

### 1.4 Strategies File Metadata Parsing
**File**: `litassist/utils.py:1023-1084`  
**Impact**: MEDIUM - Strategy analysis functionality  
**Description**: Parses brainstormed strategies files to extract counts and metadata  
**Current Approach**: Multiple regex searches for different sections (orthodox, unorthodox, most likely)  

**Current Patterns**:
```python
metadata_match = re.search(r"# Side: (.+)\n# Area: (.+)", strategies_text)
orthodox_match = re.search(r"## ORTHODOX STRATEGIES\n(.*?)(?=## [A-Z]|===|\Z)", strategies_text, re.DOTALL)
parsed["orthodox_count"] = len(re.findall(r"^\d+\.", orthodox_text, re.MULTILINE))
```

**Refactoring Approach**: Include metadata in structured format:
```json
{
  "metadata": {
    "side": "string",
    "area": "string"
  },
  "sections": {
    "orthodox": {
      "count": 5,
      "strategies": ["...", "..."]
    },
    "unorthodox": {
      "count": 3,
      "strategies": ["...", "..."]
    }
  }
}
```

### 1.5 Legal Issues Extraction
**File**: `litassist/commands/strategy.py:75-104`  
**Impact**: MEDIUM - Strategy command functionality  
**Description**: Extracts legal issues from case facts text structure  
**Current Approach**: Regex to find "Legal Issues" section and split by delimiters  

**Current Patterns**:
```python
match = re.search(r"[^a-zA-Z]*Legal\s+Issues[^a-zA-Z]*\s*\n(.*?)(?:\n\s*[^a-zA-Z]*(?:Evidence\s+Available|Opposing\s+Arguments)[^a-zA-Z]*)", case_text, re.DOTALL | re.IGNORECASE)
issues = [issue.strip().strip("•-*") for issue in re.split(r"\n+|•|\*|-", issues_text) if issue.strip()]
```

**Refactoring Approach**: Request structured legal issues:
```json
{
  "legal_issues": [
    "Issue 1 description",
    "Issue 2 description"
  ]
}
```

### 1.6 Strategy Content Analysis
**File**: `litassist/commands/strategy.py:287-369`  
**Impact**: HIGH - Complex strategy processing  
**Description**: Complex parsing of different strategy sections to extract individual strategies  
**Current Approach**: Multiple regex searches for sections, then findall for numbered items  

**Current Patterns**:
```python
likely_match = re.search(r"## MOST LIKELY TO SUCCEED\n(.*?)(?====|\Z)", strategies_content, re.DOTALL)
strategy_patterns = re.findall(r"(^\d+\..*?)(?=^\d+\.|\Z)", likely_text, re.DOTALL | re.MULTILINE)
strategy_title = re.search(r"\d+\.\s*([^\n]+)", pattern)
```

**Refactoring Approach**: Request complete structured strategy analysis:
```json
{
  "strategy_analysis": {
    "most_likely": [
      {
        "number": 1,
        "title": "Strategy title",
        "content": "Full strategy description"
      }
    ],
    "orthodox": [...],
    "unorthodox": [...]
  }
}
```

### 1.7 Case Facts Format Validation
**File**: `litassist/commands/strategy.py:30-72`  
**Impact**: LOW - Input validation  
**Description**: Validates 10-heading structure in case facts files  
**Current Approach**: Regex patterns to check for required headings  

**Refactoring Approach**: Request LLM to validate format and return structured validation result:
```json
{
  "format_valid": true,
  "missing_headings": [],
  "validation_notes": "All required headings present"
}
```

---

## 2. String Manipulation of LLM Results

### 2.1 Citation Extraction and Processing
**File**: `litassist/commands/lookup.py:25-189`  
**Impact**: HIGH - Core lookup functionality  
**Description**: Complex string processing to extract citations, principles, and checklists from lookup responses  
**Current Approach**: Multiple split operations, regex cleaning, and filtering logic  

**Current String Operations**:
```python
# Citations extraction with multiple regex patterns
citations.update(re.findall(r"\[\d{4}\]\s+[A-Z]+[A-Za-z]*\s+\d+", content))

# Principles extraction with complex splitting
lines = content.split("\n")
sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", content)
sub_lines = re.split(r"(?:^|\s)(?:\d+\.|[•*-])\s*", line)
clean_line = re.sub(r"^\d+\.\s*", "", sub_line)  # Remove numbering
clean_line = re.sub(r"^[•*-]\s*", "", clean_line)  # Remove bullets

# Gemini formatting fixes
formatted = re.sub(r"(\*)\n(\*)", r"\1\2", formatted)
```

**Refactoring Approach**: Request structured lookup results:
```json
{
  "lookup_results": {
    "citations": [
      "[2024] HCA 15",
      "[2023] FCAFC 123"
    ],
    "legal_principles": [
      "Principle 1 description",
      "Principle 2 description"
    ],
    "practical_checklists": [
      "Checklist item 1",
      "Checklist item 2"
    ]
  }
}
```

### 2.2 Reasoning Trace Removal
**File**: `litassist/commands/brainstorm.py:518-524`  
**Impact**: LOW - Content cleaning  
**Description**: Removes reasoning trace blocks from main content  
**Current Approach**: Regex substitution to clean content  

**Refactoring Approach**: Request LLM to separate main content and reasoning trace:
```json
{
  "main_content": "Primary response content",
  "legal_reasoning_trace": { "issue": "...", "applicable_law": "..." }
}
```

### 2.3 Content Preview Generation
**File**: `litassist/commands/draft.py:291-292`  
**Impact**: LOW - UI/UX functionality  
**Description**: Creates content previews by splitting and filtering lines  

**Refactoring Approach**: Request LLM to generate preview directly:
```json
{
  "full_content": "Complete document content",
  "preview": "Brief summary for display"
}
```

### 2.4 LLM Verification Response Processing
**File**: `litassist/llm.py:990-996`  
**Impact**: MEDIUM - Verification system  
**Description**: Splits verification responses for different prompt components  

**Refactoring Approach**: Request structured verification response:
```json
{
  "verification_result": {
    "system_content": "System-level analysis",
    "user_content": "User-facing content"
  }
}
```

---

## 3. Citation and Reference Parsing

### 3.1 Citation Pattern Extraction
**File**: `litassist/citation_patterns.py:194-265`  
**Impact**: HIGH - Citation verification system  
**Description**: Comprehensive citation extraction using multiple regex patterns  
**Current Approach**: 6+ different regex patterns for various citation formats  

**Current Patterns**:
```python
# Medium neutral citations [YEAR] COURT NUMBER
pattern1 = r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(\d+)"

# Traditional citations (YEAR) VOLUME COURT PAGE
pattern2 = r"\((\d{4})\)\s+(\d+)\s+([A-Z]+[A-Za-z]*)\s+(\d+)"

# Medium neutral with case type suffix
pattern3 = r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(?:Civ|Crim|Admin|Fam|QB|Ch|Pat|Comm|TCC)\s+(\d+)"
```

**Refactoring Approach**: Request LLM to format citations consistently:
```json
{
  "content": "Main legal content",
  "citations": [
    {
      "citation": "[2024] HCA 15",
      "format": "medium_neutral",
      "year": 2024,
      "court": "HCA",
      "number": 15
    }
  ]
}
```

### 3.2 Citation Validation Logic
**File**: `litassist/citation_patterns.py:270-500+`  
**Impact**: HIGH - Citation accuracy  
**Description**: Complex validation logic for different citation types and formats  
**Current Approach**: Multiple specialized validation functions with regex matching  

**Refactoring Approach**: Request LLM to self-validate citations:
```json
{
  "content": "Legal content with validated citations",
  "citation_validation": {
    "all_valid": true,
    "validated_citations": [
      {
        "citation": "[2024] HCA 15",
        "valid": true,
        "verification_source": "AustLII"
      }
    ]
  }
}
```

### 3.3 Real-time Citation Verification
**File**: `litassist/citation_verify.py:150-600+`  
**Impact**: HIGH - Citation verification system  
**Description**: URL construction and response parsing for Jade.io verification  
**Current Approach**: Regex matching for citation format detection and URL building  

**Refactoring Approach**: Keep verification system but request pre-formatted citations from LLM to minimize parsing needs.

---

## 4. Complex Parsing Logic

### 4.1 Multi-Stage Strategy Processing
**File**: `litassist/commands/strategy.py:400-900+`  
**Impact**: HIGH - Core strategy functionality  
**Description**: Complex multi-step workflow for processing strategic options  
**Current Approach**: Multiple parsing stages with fallback logic and error handling  

**Components**:
- Strategy extraction from brainstormed content
- Option ranking and analysis  
- Reasoning trace consolidation
- Template-based document generation

**Refactoring Approach**: Consolidate into fewer, more comprehensive LLM calls with structured output:
```json
{
  "strategic_analysis": {
    "available_strategies": [...],
    "ranked_options": [
      {
        "rank": 1,
        "strategy": "Strategy description",
        "reasoning": "Why this strategy ranks highly",
        "legal_reasoning_trace": {...}
      }
    ],
    "final_recommendation": "Overall strategic recommendation"
  }
}
```

### 4.2 Citation Issue Processing
**File**: `litassist/commands/brainstorm.py:32-184`  
**Impact**: HIGH - Quality control system  
**Description**: Selective regeneration workflow for strategies with citation issues  
**Current Approach**: Multi-step parsing and regeneration with state tracking  

**Refactoring Approach**: Request LLM to self-correct citations within single calls:
```json
{
  "strategies": [
    {
      "strategy": "Strategy with verified citations",
      "citations_verified": true,
      "citation_sources": ["AustLII", "Jade.io"]
    }
  ]
}
```

### 4.3 Auto-Verification Detection
**File**: `litassist/llm.py:930-950`  
**Impact**: MEDIUM - Quality control  
**Description**: Content analysis to determine if auto-verification is needed  
**Current Approach**: Multiple regex patterns to detect high-risk content  

**Refactoring Approach**: Request LLM self-assessment:
```json
{
  "content": "Main response",
  "verification_needed": true,
  "risk_factors": ["contains_citations", "statutory_references"],
  "confidence": 85
}
```

---

## 5. Error Handling and Fallback Logic

### 5.1 Reasoning Trace Fallback
**File**: `litassist/commands/verify.py:178-189`  
**Impact**: MEDIUM - Quality assurance  
**Description**: Creates fallback reasoning trace when extraction fails  

**Refactoring Approach**: Eliminate need for fallbacks by ensuring LLM always provides structured reasoning trace.

### 5.2 Multiple Parsing Attempts
**File**: `litassist/commands/lookup.py:66-76, 125-131`  
**Impact**: MEDIUM - Robustness  
**Description**: Fallback parsing strategies when primary approach fails  

**Refactoring Approach**: Use consistent structured output format to eliminate parsing variability.

---

## Refactoring Priority Matrix

### Priority 1: High-Impact Core Functionality
1. **Legal Reasoning Trace Extraction** (`utils.py:778-838`)
   - **Impact**: Affects all commands
   - **Effort**: High - requires prompt template updates across multiple commands
   - **Approach**: JSON structured reasoning trace format

2. **Strategy Content Processing** (`brainstorm.py`, `strategy.py`)
   - **Impact**: Core brainstorming and strategy functionality
   - **Effort**: High - complex multi-stage workflows
   - **Approach**: Comprehensive structured strategy output

3. **Citation Extraction and Processing** (`lookup.py`, `citation_patterns.py`)
   - **Impact**: Citation accuracy and lookup functionality
   - **Effort**: Medium - affects citation verification system
   - **Approach**: Structured citation format with metadata

### Priority 2: Medium-Impact Quality Control
1. **Verification and Validation Logic** (`verify.py`, `llm.py`)
   - **Impact**: Document quality and accuracy
   - **Effort**: Medium - affects verification workflows
   - **Approach**: LLM self-validation and structured assessment

2. **Content Analysis and Parsing** (`strategy.py:287-369`)
   - **Impact**: Strategic analysis functionality
   - **Effort**: Medium - complex section parsing
   - **Approach**: Structured strategy analysis output

### Priority 3: Low-Impact Utilities
1. **Content Preview and Formatting** (`draft.py:291-292`)
   - **Impact**: UI/UX improvements
   - **Effort**: Low - simple string operations
   - **Approach**: Direct LLM preview generation

2. **Format Validation** (`strategy.py:30-72`)
   - **Impact**: Input validation
   - **Effort**: Low - simple validation logic
   - **Approach**: LLM-based format validation

---

## Implementation Strategy

### Phase 1: Foundation (Priority 1 Items)
1. **Update Core Prompt Templates**
   - Modify YAML templates in `litassist/prompts/` to request JSON output
   - Add structured format examples
   - Include self-validation instructions

2. **Refactor Legal Reasoning Trace**
   - Update `utils.py` to expect JSON reasoning traces
   - Remove regex parsing logic
   - Update all command files to use new format

3. **Restructure Strategy Processing**
   - Consolidate multi-stage parsing into comprehensive LLM calls
   - Remove regex-based strategy extraction
   - Implement structured strategy analysis format

### Phase 2: Quality Control (Priority 2 Items)
1. **Citation System Overhaul**
   - Request structured citation format from LLMs
   - Maintain verification system but simplify input processing
   - Remove complex citation extraction patterns

2. **Verification System Simplification**
   - Replace pattern-based risk detection with LLM self-assessment
   - Implement structured verification output
   - Remove fallback logic dependencies

### Phase 3: Polish (Priority 3 Items)
1. **Utility Function Cleanup**
   - Replace remaining string manipulation with direct LLM requests
   - Remove unnecessary parsing helper functions
   - Consolidate format validation into LLM calls

### Testing Strategy
1. **Unit Test Updates**
   - Modify tests to expect JSON structured output
   - Remove parsing logic tests
   - Add JSON schema validation tests

2. **Integration Testing**
   - Verify structured output works with all LLM providers
   - Test backwards compatibility during transition
   - Validate citation verification still works

3. **Manual Testing**
   - Legal reasoning quality validation
   - Citation accuracy verification
   - Australian law compliance checking

### Expected Outcomes
- **Code Reduction**: 200+ lines of parsing logic eliminated
- **Maintainability**: Simpler, more reliable code
- **Performance**: Fewer parsing operations, faster execution
- **API Costs**: Better structured output, potentially reduced token usage
- **Reliability**: Elimination of parsing failures and edge cases

---

## Conclusion

This comprehensive audit reveals that the litassist codebase contains extensive opportunities for simplification through better prompt engineering. By systematically replacing local parsing logic with structured LLM output requests, the codebase can be significantly simplified while improving reliability and maintainability.

The key insight is that **LLMs will always return properly formatted output when correctly prompted**, eliminating the need for complex parsing, error handling, and fallback logic. This refactoring should be approached systematically, starting with the highest-impact parsing patterns and working toward complete elimination of local LLM response processing.

**Next Steps**: Begin Phase 1 implementation with Legal Reasoning Trace refactoring, as this affects all commands and provides the foundation for subsequent improvements.
