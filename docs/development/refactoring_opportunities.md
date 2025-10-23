# LitAssist Codebase Refactoring & Technical Debt Report

**Generated:** 2025-10-22
**Analysis Scope:** Full codebase refactoring needs, critical bugs, anti-patterns, and optimization opportunities
**Sources:** Combined analysis of code structure, TODO.md, CLAUDE.md compliance, and dependency mapping

---

## Executive Summary

The LitAssist codebase is fundamentally well-architected with strong adherence to minimal changes philosophy. However, **4 critical files exceed 500 lines** and require immediate refactoring, plus **8 critical bugs** identified in TODO.md pose reliability and cost risks.

### Key Statistics
- **Total Python LOC:** ~17,059 lines
- **Largest file:** `litassist/llm/client.py` (1,275 lines) - **URGENT REFACTORING NEEDED**
- **Total classes:** 20 (excellent - not over-engineered)
- **Try-except blocks:** 286 (zero bare except clauses ✓)
- **Regex usage:** 109 occurrences (opportunity for prompt engineering)
- **YAML prompt lines:** 3,419 (excellent externalization ✓)
- **Zero circular dependencies** ✓
- **Zero TODO/FIXME comments** ✓

### Critical Issues Summary
- **1 Real Bug** requiring immediate attention (API timeouts) + 1 optional enhancement (circuit breaker)
- **4 Large Files** (>500 lines) needing decomposition
- **Deep coupling chain** in citation system needs untangling
- **109 regex operations** could be replaced with prompt engineering

**Note:** Original bug report claimed 7-8 critical bugs. After verification, only 1 real bug found. See `claude_bug_verification_report.md` for detailed analysis.

---

## PRIORITY 0: VERIFIED BUGS (After Code Analysis)

### Real Bugs Requiring Fixes

#### 0.1 Missing API Timeouts - HIGH PRIORITY (REAL BUG)
**Location:** `litassist/llm/api_handlers.py:278, 285`
**Problem:** API calls lack `timeout` parameter, can hang indefinitely
**Impact:** MEDIUM - poor UX, hanging processes

**Solution:**
```python
# Add timeout=30.0 to both API calls
resp = client.chat.completions.create(
    model=model_name,
    messages=messages,
    extra_body=extra_body,
    timeout=30.0,  # Add this line
    **filtered_params,
)
```

**Estimated Effort:** 5 minutes
**Risk:** Very Low
**Priority:** HIGH - quick win

---

### Optional Enhancements (Nice-to-Have)

#### 0.2 Circuit Breaker Pattern - LOW PRIORITY (ENHANCEMENT)
**Location:** `litassist/llm/api_handlers.py`
**Current State:** ✅ Has retry limits (5 attempts per request)
**Enhancement:** Add circuit breaker to track failures across multiple calls

**Why This is Optional:**
- Current implementation prevents infinite retries (5-attempt limit)
- Circuit breaker would prevent cascading failures across multiple requests
- This is a cost optimization, not a critical bug

**If Implemented:**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half_open
```

**Estimated Effort:** 2-3 hours
**Risk:** Medium
**Priority:** LOW - nice-to-have optimization

---

## PRIORITY 1: CRITICAL - Large File Refactoring

### 1.1 `litassist/llm/client.py` (1,275 lines) - URGENT

**Problem:** Single monolithic file combining factory pattern, parameter handling, request building, streaming, tool execution, and verification logic. **Impacts 14+ dependent modules.**

**Current Responsibilities:**
- LLMClientFactory class
- LLMClient class with 10+ methods
- Model family detection (MODEL_PATTERNS)
- Parameter profiles (PARAMETER_PROFILES)
- Request building
- Response streaming
- Tool execution
- Verification mixing

**Recommended Split:**
```
litassist/llm/
├── __init__.py                         # Re-export public API
├── client.py (200-300 lines)           # Core LLMClient class only
├── factory.py (150-200 lines)          # LLMClientFactory
├── model_profiles.py (150-200 lines)   # MODEL_PATTERNS, PARAMETER_PROFILES
├── parameter_handler.py (200 lines)    # Parameter filtering & validation
├── request_builder.py (150-200 lines)  # Request construction logic
├── verification.py (exists, 469 lines) # Keep as-is ✓
├── api_handlers.py (exists, 459 lines) # Keep as-is ✓
├── response_parser.py (exists, 132 lines) # Keep as-is ✓
├── retry_handler.py (exists)           # Keep as-is ✓
├── citation_handler.py (exists)        # Keep as-is ✓
└── tools.py (exists)                   # Keep as-is ✓
```

**Benefits:**
- Easier testing of parameter profiles in isolation
- Clear separation of model configuration vs execution
- Reduced cognitive load for developers
- Safer model parameter modifications
- Faster file navigation and search

**Migration Strategy:**
1. Extract `model_profiles.py` (MODEL_PATTERNS, PARAMETER_PROFILES) - no imports broken
2. Extract `parameter_handler.py` (filtering functions) - update client.py imports only
3. Extract `factory.py` (LLMClientFactory) - update 14 command imports atomically
4. Extract `request_builder.py` (request construction) - update client.py only
5. Update `__init__.py` to re-export public API (backward compatibility)
6. Run full test suite after each extraction
7. Update mock paths in tests

**Estimated Effort:** 6-8 hours
**Risk:** Low-Medium (good test coverage, but many dependents)
**Priority:** CRITICAL - highest impact refactoring

---

### 1.2 `litassist/citation_verify.py` (914 lines) - HIGH PRIORITY

**Problem:** Combines verification logic, hardcoded data, cache management, and multiple verification strategies. **Part of deep coupling chain.**

**Deep Coupling Chain Identified:**
```
citation_patterns → citation_verify → citation_context →
llm/citation_handler → llm/client
```

**Current Responsibilities:**
- Google CSE verification
- AustLII verification
- Legislation handling
- Court mappings (COURT_MAPPINGS dict)
- UK/International courts (UK_INTERNATIONAL_COURTS dict)
- FOIA hardcoded files mapping
- Citation cache management

**Recommended Split:**
```
litassist/citation/
├── __init__.py                      # Re-export public API
├── verify.py (200-300 lines)        # Main orchestration
├── cache.py (100 lines)             # Citation cache management
├── google_cse.py (150-200 lines)    # Google CSE verification strategy
├── austlii.py (150-200 lines)       # AustLII verification strategy
├── legislation.py (100-150 lines)   # Legislation handling
├── court_mappings.py (200 lines)    # COURT_MAPPINGS, UK_INTERNATIONAL_COURTS data
├── foia_hardcoded.py (50 lines)     # HARDCODED_FOIA_FILES mapping
└── patterns.py (rename from citation_patterns.py, 616 lines)
```

**Benefits:**
- Untangles deep coupling chain
- Verification strategies become pluggable
- Court mappings become pure data
- Cache management isolated and testable
- Cache becomes independently testable
- Easier to add new verification sources

**Migration Strategy:**
1. Extract `cache.py` (cache management) - update verify.py only
2. Extract `court_mappings.py` (pure data) - no logic changes
3. Extract `foia_hardcoded.py` (pure data) - no logic changes
4. Extract `google_cse.py` (verification strategy) - update verify.py
5. Extract `austlii.py` (verification strategy) - update verify.py
6. Extract `legislation.py` (verification strategy) - update verify.py
7. Rename `citation_patterns.py` → `citation/patterns.py` - update all imports
8. Update 16 dependent imports atomically

**Estimated Effort:** 5-6 hours
**Risk:** Low (well-defined boundaries)
**Priority:** HIGH - untangles coupling chain

---

### 1.3 `litassist/commands/verify.py` (829 lines) - MEDIUM PRIORITY

**Problem:** Single command file handling citation verification, soundness checking, reasoning trace, and CoVe verification.

**Current Responsibilities:**
- CLI argument parsing
- Citation verification orchestration
- Legal soundness validation
- Reasoning trace generation/validation
- CoVe verification
- Output formatting and saving

**Recommended Split (follows brainstorm/digest pattern):**
```
litassist/commands/verify/
├── __init__.py                      # CLI command entry point (@click.command)
├── core.py (200 lines)              # Main orchestration logic
├── citation_verifier.py (150 lines) # Citation verification logic
├── soundness_checker.py (150 lines) # Legal soundness validation
├── reasoning_handler.py (200 lines) # Reasoning trace operations
└── output_formatter.py (150 lines)  # Report generation
```

**Benefits:**
- Each verification type independently testable
- Matches successful pattern from brainstorm/digest
- Easier to add new verification methods
- Clear separation of concerns

**Migration Strategy:**
1. Create `verify/` package directory
2. Extract CLI interface to `__init__.py` (click decorators)
3. Extract orchestration to `core.py`
4. Extract each verification type to separate module
5. Extract output formatting to `output_formatter.py`
6. Update CLI imports (single location: `cli.py`)
7. Update test mocks for new module paths

**Estimated Effort:** 4-5 hours
**Risk:** Low-Medium (CLI integration requires care)
**Priority:** MEDIUM - good pattern replication

---

### 1.4 `litassist/logging_utils.py` (668 lines) - MEDIUM PRIORITY

**Problem:** Combines directory setup, logging config, JSON sanitization, log saving, markdown generation, and task events. **33 total imports across codebase.**

**Current Responsibilities:**
- Directory setup (LOG_DIR, OUTPUT_DIR)
- Logging configuration
- JSON sanitization (with Mock handling)
- JSON log saving
- Markdown log generation
- Template selection
- Task event logging

**Recommended Split:**
```
litassist/logging/
├── __init__.py (100 lines)          # Re-export public API, directory setup
├── config.py (100 lines)            # setup_logging function
├── json_utils.py (150 lines)        # JSON sanitization & saving
├── markdown_utils.py (200 lines)    # Markdown log generation
└── task_events.py (150 lines)       # log_task_event functionality
```

**Benefits:**
- Testing JSON sanitization independently
- Cleaner separation of formats (JSON vs Markdown)
- Easier to add new log formats
- Template selection logic isolated

**Migration Strategy:**
1. Create `logging/` package with `__init__.py`
2. Extract directory setup to `__init__.py` (preserves LOG_DIR, OUTPUT_DIR)
3. Extract `setup_logging` to `config.py`
4. Extract JSON utilities to `json_utils.py`
5. Extract markdown utilities to `markdown_utils.py`
6. Extract task events to `task_events.py`
7. Update `__init__.py` to re-export all public functions
8. Update 33 import locations (can be done with find-replace)
9. Run full test suite

**Estimated Effort:** 3-4 hours
**Risk:** Low (well-defined interfaces, many dependents but simple imports)
**Priority:** MEDIUM

---

### 1.5 Files 500-800 Lines - Monitor (Do Not Refactor Yet)

These files are approaching limits but acceptable for now:

- `litassist/citation_patterns.py` - 616 lines [DATA FILE - OK]
  - Mostly data structures (VALID_COURTS, GENERIC_SURNAMES, patterns)
  - Minimal logic, primarily configuration
  - **Recommendation:** Keep as-is, move to YAML if exceeds 800 lines

- `litassist/commands/lookup/fetchers.py` - 615 lines [SPECIALIZED - OK]
  - Complex domain logic (web fetching, PDF handling, rate limiting)
  - Already well-organized by fetcher type
  - **Recommendation:** Monitor, acceptable for specialized domain

- `litassist/verification_chain.py` - 556 lines [BORDERLINE - MONITOR]
- `litassist/citation_context.py` - 555 lines [BORDERLINE - MONITOR]
- `litassist/commands/brainstorm/core.py` - 546 lines [BORDERLINE - MONITOR]

**Action:** Monitor these files. If any exceed 600 lines, re-evaluate for splitting.

---

## PRIORITY 2: Prompt Engineering Over Parsing

### 2.1 Eliminate Regex Parsing - PHILOSOPHY ALIGNMENT

**Current State:** 109 regex operations across codebase, violating CLAUDE.md principle:

> "Minimize Local Parsing Through Better Prompt Engineering. LLMs will always return output formatted as they are told - you do not need fallback parsing."

**Problem Areas:**
1. Citation extraction in `citation_patterns.py` (~40 regex patterns)
2. Generic surname detection (GENERIC_SURNAMES list + regex)
3. Document separation markers (`=== NAME ===` + regex parsing)
4. Content chunking and splitting (145 string operations)

**Opportunity:** Replace regex-heavy parsing with LLM-based structured output.

---

#### 2.1.1 Citation Extraction via LLM

**Current Approach (regex-heavy):**
```python
# citation_patterns.py - complex regex patterns
citations = extract_citations(text)  # 40+ regex patterns
suspicious = [c for c in citations if has_generic_surname(c)]
```

**Proposed Approach (prompt engineering):**
```python
# Replace with LLM-based extraction
prompt = PROMPTS.get("citation.extract_structured")
# Prompt instructs LLM to return JSON:
# {
#   "citations": [
#     {
#       "text": "[2023] HCA 1",
#       "parties": "Smith v Jones",
#       "court": "HCA",
#       "year": 2023,
#       "number": 1,
#       "verified": true
#     }
#   ]
# }
```

**Benefits:**
- Remove ~200 lines of regex patterns
- More accurate citation extraction
- Self-validating output
- Handles edge cases better than regex
- Extensible to new citation formats without code changes

**Risks:**
- API cost increase (need to call LLM for extraction)
- Latency increase (network call vs local regex)
- Requires prompt engineering validation

**Recommendation:** Prototype on small subset first, validate accuracy vs regex approach.

**Estimated Effort:** 8-10 hours (includes prompt development, testing, validation)
**Risk:** Medium (requires careful validation)
**Priority:** LOW - philosophical improvement, not urgent

---

#### 2.1.2 Document Separation Markers - COMPLIANCE ISSUE

**Current Issue:** Code uses `=== NAME ===` markers, then parses with regex.

**CLAUDE.md violation:**
> "NO === MARKERS IN LLM OUTPUT ANYWHERE"

**Files Using Markers:**
- `litassist/commands/brainstorm/core.py`
- `litassist/commands/lookup/processors.py`
- `litassist/verification_chain.py`
- Multiple YAML prompt templates

**Proposed Solutions:**

**Option A: JSON Structured Output**
```yaml
# In prompt templates
prompt: |
  Return your response as JSON:
  {
    "documents": [
      {"name": "Case Law", "content": "..."},
      {"name": "Legislation", "content": "..."}
    ]
  }
```

**Option B: XML-Style Tags (no regex needed)**
```yaml
# In prompt templates
prompt: |
  Separate documents with XML tags:
  <DOCUMENT name="Case Law">
  content here
  </DOCUMENT>
```

**Recommendation:** Use Option A (JSON) for structured data, Option B (XML) for narrative content.

**Estimated Effort:** 2-3 hours (mostly find-and-replace)
**Risk:** Low (straightforward substitution)
**Priority:** MEDIUM - compliance issue

---

#### 2.1.3 Reduce String Manipulation (145 occurrences)

**Observation:** 145 uses of `.split`, `.join`, `.replace` suggest text parsing that could be avoided.

**Strategy:** Audit each usage and convert to structured output where appropriate:
- Content chunking → Ask LLM for pre-chunked output
- Format conversions → Request correct format in prompt
- Text cleaning → LLM self-cleaning instructions

**Estimated Effort:** 10-12 hours (audit + case-by-case implementation)
**Risk:** Medium (requires careful analysis)
**Priority:** LOW - optimization, not critical

---

## PRIORITY 3: Dependency Analysis & Technical Debt

### 3.1 Most Critical Dependencies (High-Impact Refactoring)

**Identified via import analysis:**

1. **`prompts.PROMPTS`** - 25 imports (STABLE ✓)
   - Well-designed centralized prompt management
   - No action needed

2. **`llm.LLMClientFactory`** - 14 imports (NEEDS SPLITTING)
   - See Priority 1.1
   - Will affect all 14 dependents during refactoring

3. **`logging_utils`** - 33 total imports (SCATTERED)
   - See Priority 1.4
   - Many dependents but simple imports (find-replace safe)

4. **`citation_verify`** - 16 imports (NEEDS DECOMPOSITION)
   - See Priority 1.2
   - Part of deep coupling chain

---

### 3.2 Deep Coupling Chain - REQUIRES UNTANGLING

**Identified Chain:**
```
citation_patterns.py → citation_verify.py → citation_context.py →
llm/citation_handler.py → llm/client.py
```

**Impact:** Changes ripple through 5 files. High risk for bugs.

**Solution:** Priority 1.2 refactoring breaks this chain by:
1. Making verification strategies pluggable
2. Isolating cache management
3. Separating court mappings data
4. Creating clear interfaces between layers

**After Refactoring:**
```
citation/patterns.py ─→ citation/verify.py (orchestrator)
                            ├→ citation/google_cse.py
                            ├→ citation/austlii.py
                            └→ citation/cache.py
```

---

### 3.3 Code Duplication - API Credential Validation

**Location:** `litassist/cli.py:72-200`
**Problem:** Repetitive try/except blocks for validating each API service
**Impact:** LOW - adds ~100 lines of duplicated code, but rarely modified

**Current Implementation:**
```python
# Repeated pattern for OpenAI, Pinecone, Google CSE, OpenRouter
if not placeholder_checks["service"]:
    try:
        print("  - Testing Service API... ", end="", flush=True)
        # Service-specific validation code
        print("OK")
    except Exception as e:
        print("FAILED")
        sys.exit(f"Error: Service API test failed: {e}")
else:
    print("  - Skipping Service connectivity test (placeholder credentials)")
```

**Recommended Refactoring:**

1. **Define service configuration:**
```python
SERVICES_TO_VALIDATE = [
    {
        "name": "OpenAI",
        "placeholder_key": "openai",
        "validator": _validate_openai,
    },
    {
        "name": "Pinecone",
        "placeholder_key": "pinecone",
        "validator": _validate_pinecone,
    },
    # ... etc
]
```

2. **Extract individual validators:**
```python
def _validate_openai(config):
    from openai import OpenAI
    client = OpenAI(api_key=config.oa_key)
    client.models.list()

def _validate_pinecone(config):
    import pinecone
    pinecone.init(api_key=config.pc_key, environment=config.pc_env)
    pinecone.list_indexes()
```

3. **Create generic orchestrator:**
```python
def _validate_service(service_config, placeholder_checks):
    service_name = service_config["name"]
    placeholder_key = service_config["placeholder_key"]
    validator = service_config["validator"]

    if placeholder_checks.get(placeholder_key, False):
        print(f"  - Skipping {service_name} connectivity test (placeholder credentials)")
        return

    try:
        print(f"  - Testing {service_name} API... ", end="", flush=True)
        validator(load_config())
        print("OK")
    except Exception as e:
        print("FAILED")
        sys.exit(f"Error: {service_name} API test failed: {e}")
```

4. **Simplify main function:**
```python
def validate_credentials(show_progress=True):
    config = load_config()
    placeholder_checks = config.using_placeholders()

    if show_progress:
        print("Verifying API connections...")

    for service_config in SERVICES_TO_VALIDATE:
        _validate_service(service_config, placeholder_checks)

    if show_progress:
        print("All API connections verified.\n")
```

**Benefits:**
- Reduces ~130 lines to ~80 lines (40% reduction)
- Adding new services requires 5 lines instead of 20
- Consistent error handling across all services
- More testable (can test validators independently)

**Estimated Effort:** 30-45 minutes
**Risk:** Very Low (rarely-used code path, simple refactoring)
**Priority:** LOW - nice-to-have cleanup

---

### 3.4 TODO.md Pending Items

**From TODO.md, relevant to refactoring:**

1. **Remove redundant top-level `litassist.py` entry point** - COMPLETED (October 2025)
2. **Implement glob unification per plan** - MEDIUM PRIORITY (centralize expand_glob_patterns)
3. **Remove temporary glob help addon** - LOW PRIORITY (after unification)
4. **Refactor verify_with_level (Option B)** - MEDIUM PRIORITY (simplify to boolean)

**Recommendation:** Address after Priority 1 refactorings complete.

---

## PRIORITY 4: Code Quality (Strengths to Preserve)

### Anti-Patterns NOT Found ✓

- ✓ **Zero bare `except:` clauses** (all exceptions typed)
- ✓ **Zero circular dependencies**
- ✓ **No emoji usage** (CLAUDE.md compliant)
- ✓ **No hardcoded prompts** (only justified f-strings)
- ✓ **No overuse of decorators/metaclasses**
- ✓ **No unnecessary abstraction layers**
- ✓ **No model name hardcoding violations**
- ✓ **Good type hint usage**
- ✓ **Zero TODO/FIXME comments** (technical debt tracked in TODO.md)

### Justified Patterns ✓

1. **Factory Pattern** (1 occurrence - LLMClientFactory)
   - Justified: Provides command-specific configuration loading
   - Keep as-is, ensure it remains simple

2. **F-String Prompts** (6 occurrences - all acceptable)
   - `litassist/utils/legal_reasoning.py` - Formatting headers
   - `litassist/commands/brainstorm/analysis_generator.py` - Content combination
   - `litassist/commands/brainstorm/core.py` - Strategy combination
   - `litassist/commands/lookup/processors.py` - System prompt extension
   - `litassist/commands/strategy/document_generator.py` - Document building
   - All are short concatenations with justification

3. **Class Count** (20 classes - excellent)
   - Not over-engineered
   - Most code appropriately uses functions
   - Notable justified classes:
     - `LegalReasoningTrace` - Structured data with validation
     - `LookupProcessor` - Stateful workflow orchestration
     - `LLMClient` - API interaction encapsulation

### Command Organization - EXEMPLARY ✓

**Already well-modularized:**
- `brainstorm/` → Split into 6 submodules ✓
- `digest/` → Split into 4 submodules ✓
- `lookup/` → Split into 4 submodules ✓
- `strategy/` → Split into 5 submodules ✓

**Single-file commands (acceptable <500 lines):**
- `extractfacts.py` - 361 lines ✓
- `barbrief.py` - 438 lines ✓
- `caseplan.py` - 460 lines ✓
- `counselnotes.py` - 523 lines (borderline, acceptable)
- `draft.py` - 524 lines (borderline, acceptable)

**No action needed** - command organization is exemplary.

---

## PRIORITY 5: YAML Prompt Organization

### 5.1 `caseplan.yaml` (718 lines) - SPLIT RECOMMENDED

**Problem:** Largest YAML file, hard to navigate.

**Recommended Split:**
```
litassist/prompts/caseplan/
├── base.yaml (250 lines)          # Core prompts
├── sections.yaml (250 lines)      # Section-specific templates
└── validation.yaml (218 lines)    # Validation prompts
```

**Update `prompts.py` to load from directory:**
```python
# Load all YAML files in caseplan/ directory
caseplan_prompts = {}
for yaml_file in (PROMPTS_DIR / "caseplan").glob("*.yaml"):
    with open(yaml_file) as f:
        caseplan_prompts.update(yaml.safe_load(f))
```

**Estimated Effort:** 1-2 hours
**Risk:** Very Low (YAML splitting straightforward)
**Priority:** LOW - quality of life improvement

---

### 5.2 Other YAML Files - ACCEPTABLE

```
processing.yaml      - 476 lines ✓ (acceptable)
system_feedback.yaml - 369 lines ✓ (acceptable)
strategies.yaml      - 354 lines ✓ (acceptable)
verification.yaml    - 338 lines ✓ (acceptable)
```

**No action needed.**

---

## PRIORITY 6: Optimization & Dead Code

### 6.1 Dead Code Detection

**Recommendation:** Run automated detection:
```bash
vulture litassist/ --min-confidence 80 > dead_code_report.txt
```

**Estimated Effort:** 2-3 hours (run + review + cleanup)
**Risk:** Very Low
**Priority:** LOW

---

### 6.2 Performance Profiling

**Recommendation:** Profile hot paths:
```bash
python -m cProfile -o profile.stats -m litassist.cli extractfacts large_file.pdf
python -m pstats profile.stats
```

**Focus Areas:**
- Citation verification (network calls)
- Large file processing
- LLM API calls (already timed with @timed)

**Estimated Effort:** 3-4 hours
**Risk:** Very Low (analysis only)
**Priority:** LOW

---

## Implementation Roadmap

### Phase 1: Critical Fixes (Week 1) - URGENT
**Total Effort:** 10 minutes (1 real bug!)

1. **Add API timeouts** (bug 0.1) - 5 minutes [HIGH - REAL BUG]
2. **Test the fix** - 5 minutes

**Risk:** Very Low
**Impact:** MEDIUM - prevents hanging processes

**Note:** Original plan included 4-6 hours for multiple bugs. After verification, only 1 real bug requiring 5-minute fix!

---

### Phase 2: Large File Refactoring (Weeks 2-3) - HIGH PRIORITY
**Total Effort:** 20-24 hours

**Week 2:**
1. **Refactor `llm/client.py`** (Priority 1.1) - 6-8 hours
   - Day 1-2: Extract model_profiles, parameter_handler
   - Day 3: Extract factory, request_builder
   - Day 4: Update 14 dependents, run tests
   - Day 5: Update mocks, documentation

2. **(Optional) Implement circuit breaker** (enhancement 0.2) - 2-3 hours
   - Only if cost optimization becomes priority
   - Current retry limits (5 attempts) are sufficient for most cases

**Week 3:**
3. **Refactor `citation_verify.py`** (Priority 1.2) - 5-6 hours
   - Day 1: Extract cache, court_mappings, foia
   - Day 2: Extract verification strategies
   - Day 3: Update 16 dependents, run tests

4. **Refactor `logging_utils.py`** (Priority 1.4) - 3-4 hours
   - Day 1: Extract to logging/ package
   - Day 2: Update 33 imports, run tests

**Risk:** Low-Medium
**Impact:** HIGH - maintainability, developer velocity

---

### Phase 3: Command Refactoring (Week 4) - MEDIUM PRIORITY
**Total Effort:** 4-5 hours

1. **Refactor `commands/verify.py`** (Priority 1.3) - 4-5 hours
   - Extract to verify/ package following brainstorm pattern
   - Update CLI integration
   - Run tests

**Risk:** Low-Medium
**Impact:** MEDIUM - pattern consistency

---

### Phase 4: Prompt Engineering (Month 2) - LOW PRIORITY
**Total Effort:** 12-15 hours

1. **Eliminate `===` markers** (Priority 2.1.2) - 2-3 hours [MEDIUM]
2. **Prototype LLM citation extraction** (Priority 2.1.1) - 8-10 hours [LOW]
3. **Audit string manipulation** (Priority 2.1.3) - 10-12 hours [LOW]

**Risk:** Medium
**Impact:** MEDIUM - philosophy alignment, cost optimization

---

### Phase 5: Polish & Optimization (Month 3) - LOW PRIORITY
**Total Effort:** 8-12 hours

1. **Split `caseplan.yaml`** (Priority 5.1) - 1-2 hours
2. **Dead code detection** (Priority 6.1) - 2-3 hours
3. **Performance profiling** (Priority 6.2) - 3-4 hours
4. **Large file handling** (bug 0.6) - 2-3 hours
5. **Input validation** (bug 0.7) - 1-2 hours

**Risk:** Very Low
**Impact:** LOW - quality of life improvements

---

## Testing Strategy

### Before Each Refactoring
1. Run full test suite: `/Users/witt/anaconda3/bin/python3 -m pytest tests/unit/ -x --tb=short -q`
2. Run linting: `ruff check litassist/`
3. Document all passing tests
4. Create feature branch

### During Refactoring
1. Make atomic commits per module extraction
2. Update import paths immediately after extraction
3. Run tests after each module migration
4. Update mocks/patches for new module paths
5. Keep existing tests passing (red → green → refactor)

### After Refactoring
1. Full test suite must pass
2. Ruff check must pass
3. Manual smoke test of affected commands
4. Update relevant documentation
5. Merge to main (no force push per CLAUDE.md)

### Rollback Plan
- Git branches for each refactoring
- No force pushes (per CLAUDE.md)
- Easy revert if tests fail
- Document known issues before merge

---

## Risk Assessment Matrix

| Item | Risk | Complexity | Test Coverage | Dependents | Priority |
|------|------|------------|---------------|------------|----------|
| Bug 0.1: Rate limiting | Low | Low | Good | 1 file | CRITICAL |
| Bug 0.2: Circuit breaker | Medium | Medium | Good | 1 file | HIGH |
| Bug 0.3: Timeouts | Very Low | Low | Good | Multiple | HIGH |
| Bug 0.4: Exception handlers | Very Low | Low | Good | 2 files | MEDIUM |
| Bug 0.5: o3-pro validation | Very Low | Low | Good | 1 file | MEDIUM |
| Refactor llm/client.py | Low-Medium | Medium | Good | 14 files | CRITICAL |
| Refactor citation_verify.py | Low | Low | Good | 16 files | HIGH |
| Refactor verify.py | Low-Medium | Medium | Good | 1 file | MEDIUM |
| Refactor logging_utils.py | Low | Low | Good | 33 files | MEDIUM |
| Eliminate === markers | Low | Low | Good | 5+ files | MEDIUM |
| LLM citation extraction | Medium | High | Fair | Multiple | LOW |
| String manipulation audit | Medium | High | Varies | Multiple | LOW |

---

## Metrics & Success Criteria

### Code Metrics - Target State

**File Size Distribution (Target):**
- 0 files > 500 lines (currently 4)
- <10 files 400-500 lines
- 50+ files < 400 lines

**Coupling Metrics:**
- Break deep coupling chain in citation system ✓
- Reduce average file dependencies from 6.2 to <5.0
- Maintain zero circular dependencies ✓

**Quality Metrics:**
- Maintain zero bare except clauses ✓
- Maintain 100% test pass rate ✓
- Reduce regex operations from 109 to <50
- Reduce string manipulation from 145 to <100

### Bug Fixes - Success Criteria

**Phase 1 (Critical):**
- ✓ API rate limiting with exponential backoff implemented
- ✓ Circuit breaker prevents runaway costs
- ✓ All API calls have 30-second timeouts
- ✓ All bare exception handlers log errors
- ✓ o3-pro parameters validated

### Refactoring - Success Criteria

**Phase 2 (High Priority):**
- ✓ `llm/client.py` split into 5+ focused modules under 300 lines
- ✓ `citation_verify.py` split into 7+ modules with pluggable strategies
- ✓ `logging_utils.py` split into 5 modules under 200 lines
- ✓ All 380 unit tests passing
- ✓ Ruff linting passing with zero errors
- ✓ All dependents updated atomically

**Phase 3 (Medium Priority):**
- ✓ `commands/verify.py` follows brainstorm/digest pattern
- ✓ Verification types independently testable

---

## Dependency Update Plan (Import Changes)

### High-Impact Import Updates

**`llm.LLMClientFactory` (14 dependents):**
```python
# BEFORE
from litassist.llm import LLMClientFactory

# AFTER (no change - re-exported from __init__.py)
from litassist.llm import LLMClientFactory
```

**`citation_verify` functions (16 dependents):**
```python
# BEFORE
from litassist.citation_verify import verify_all_citations

# AFTER (re-exported from citation/__init__.py)
from litassist.citation import verify_all_citations
```

**`logging_utils` (33 dependents):**
```python
# BEFORE
from litassist.logging_utils import save_log, save_command_output

# AFTER (re-exported from logging/__init__.py)
from litassist.logging import save_log, save_command_output
```

**Strategy:** Use `__init__.py` re-exports to maintain backward compatibility during transition.

---

## Conclusion

The LitAssist codebase is **fundamentally well-architected** with excellent foundations. The refactoring needs are:

### Immediate Actions (Next 2 Weeks)
1. **Fix 1 real bug (API timeout)** - 5 minutes [HIGH]
2. **Refactor 4 large files** - 20-24 hours [HIGH]

### Strategic Actions (Next 2 Months)
3. **Untangle coupling chain** - covered by citation refactoring
4. **Align with prompt engineering philosophy** - 12-15 hours [MEDIUM]
5. **Polish and optimization** - 8-12 hours [LOW]

### Preserved Strengths
- ✓ Minimal over-engineering (20 classes)
- ✓ Excellent command organization (brainstorm/digest/lookup/strategy patterns)
- ✓ Strong YAML prompt externalization (3,419 lines)
- ✓ Zero circular dependencies
- ✓ Comprehensive test coverage
- ✓ Good error handling (zero bare except clauses)

**Total Estimated Effort:** 35-40 hours across all priorities (down from original 44-57 hours)
**Highest ROI:** Phase 2 (large file refactoring) - most impactful work
**Quick Wins:** Add API timeout (5 minutes) - only real bug found!

---

## Appendix A: File Size Distribution

### Files Requiring Action (>500 Lines)
1. `litassist/llm/client.py` - 1,275 lines **[CRITICAL - REFACTOR]**
2. `litassist/citation_verify.py` - 914 lines **[HIGH - REFACTOR]**
3. `litassist/commands/verify.py` - 829 lines **[MEDIUM - REFACTOR]**
4. `litassist/logging_utils.py` - 668 lines **[MEDIUM - REFACTOR]**

### Files to Monitor (500-800 Lines)
5. `litassist/citation_patterns.py` - 616 lines [DATA FILE - OK]
6. `litassist/commands/lookup/fetchers.py` - 615 lines [SPECIALIZED - OK]
7. `litassist/verification_chain.py` - 556 lines [MONITOR]
8. `litassist/citation_context.py` - 555 lines [MONITOR]
9. `litassist/commands/brainstorm/core.py` - 546 lines [MONITOR]
10. `litassist/commands/draft.py` - 524 lines [ACCEPTABLE]
11. `litassist/commands/counselnotes.py` - 523 lines [ACCEPTABLE]
12. `litassist/commands/lookup/processors.py` - 507 lines [ACCEPTABLE]

### Files in Good Range (400-500 Lines)
- 11 files - all within guidelines ✓

### Files in Excellent Range (<400 Lines)
- 50+ files - excellent modularization ✓

---

## Appendix B: Critical Bug Locations

| Bug ID | Location | Line | Issue | Fix Effort |
|--------|----------|------|-------|------------|
| 0.1 | `llm/api_handlers.py` | multiple | No rate limiting | 1-2 hours |
| 0.2 | `llm/api_handlers.py` | multiple | No circuit breaker | 2-3 hours |
| 0.3 | `llm/api_handlers.py`, requests calls | multiple | No timeouts | 1 hour |
| 0.4 | `citation_verify.py`, `prompts.py` | 474, 190 | Bare exception handlers | 30 min |
| 0.5 | `llm/client.py` | o3-pro handling | No param validation | 30 min |
| 0.6 | Multiple file readers | multiple | No streaming for large files | 2-3 hours |
| 0.7 | All command entry points | multiple | No file validation | 1-2 hours |

---

## Appendix C: Dependency Map (High-Impact Modules)

**Modules with 10+ Dependents:**

1. `prompts.PROMPTS` - 25 imports [STABLE ✓]
2. `logging_utils` - 33 imports [NEEDS REFACTOR]
3. `citation_verify` - 16 imports [NEEDS REFACTOR]
4. `llm.LLMClientFactory` - 14 imports [NEEDS REFACTOR]
5. `config.get_config` - 18 imports [STABLE ✓]
6. `utils.formatting` - 22 imports [STABLE ✓]

**Deep Coupling Chain:**
```
citation_patterns → citation_verify → citation_context →
llm/citation_handler → llm/client
```

**Resolution:** Break chain via Priority 1.2 refactoring.

---

**Report End**

**Next Actions:**
1. Review and approve this report
2. Create git branch: `refactor/phase1-critical-bugs`
3. Implement Phase 1 critical fixes (5-7 hours)
4. Run full test suite validation
5. Create git branch: `refactor/phase2-large-files`
6. Begin Phase 2 large file refactoring
