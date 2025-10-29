<!-- markdownlint-disable MD041 -->
### CRITICAL: Minimal Changes Philosophy

**ALWAYS USE MINIMAL CHANGES POSSIBLE**. This is the #1 rule:
NEVER OVERENGINEER EVER

1. Never refactor unless explicitly asked
2. Make the smallest change that fixes the problem
3. Don't "improve" code while fixing something else
4. Don't extract constants, functions, or patterns
5. Don't update related code unless it's broken and does not run
6. Do not insert any silent fallbacks without obtaining the user's explicit approval
7. Prefer inline fixes over architectural changes
8. One fix = one narrowly scoped change
9. Prefer deleting unnecessary parsing logic to adding more
10. Use local text processing with regexes only when there is no sane alternative to it. Confirm with the user every time.

**Red Flags for Over-Engineering:**

- Creating classes for single functions
- Factories with only one product type
- Decorators that could be simple function calls
- Abstractions without multiple concrete implementations

### Code Analysis & Verification Requirements

**CRITICAL**: Always verify functionality before proposing changes:

1. Always read and understand code before suggesting changes, never guess
2. Investigate each function's purpose thoroughly throughout the codebase
3. Confirm that the fix you propose will actually fix the problem, by analysing codebase. NO GUESSING
4. ALWAYS Check dependencies  - Understand how functions are used before moving/changing them
5. Verify functionality still works after any modifications you do

### Code Quality Standards

1. All code must pass `ruff check` before you declare your fix complete
2. All, absolutely all tests with pytest must pass before you say "fix complete"
3. Update TODO.md and relevant docs when making changes

### Refactoring Guidelines

**Core Principle**: Transform large files (1000+ lines) into focused modules under 500 lines each

**Refactoring Strategy:**

1. **Identify Functional Groups**: Find natural boundaries (data processing, API calls, validation, utilities)
2. **Extract by Responsibility**: Each new file handles one specific concern

When changing any API or usage pattern (e.g., CONFIG → get_config()):

1. **Find ALL usages FIRST**

   ```bash
   grep -r "pattern_to_change" . --include="*.py" > migration_list.txt
   ```

2. **Update everything atomically** - NEVER leave mixed old/new patterns
   - Core module → dependent modules → tests → docs (in that order)
   - Run `pytest tests/unit/ -x` after each group
3. **Migration completeness check**

   ```bash
   # Verify old pattern is completely gone
   grep -r "old_pattern" . --include="*.py"  # Should return nothing
   ```

**Refactoring Red Flags:**

- AttributeError on None = incomplete lazy-load migration  
- Import errors = missed module path updates
- Mixed old/new patterns in codebase = migration not finished

**Example Failure:** Created get_config() but left CODE using CONFIG directly → AttributeError

**Golden Rule:** Change the API everywhere or nowhere. No partial migrations.

**Post-Refactoring Tasks:**

- Update import paths in tests (patch decorators need new module paths)
- Remove discovered dead code and unused dependencies
- Migrate deprecated API calls found during refactoring
- Verify all tests pass after updating imports

**Note**: ONLY perform refactoring when EXPLICITLY REQUESTED. During regular work, follow the minimal changes philosophy.

### YAML File Integrity

- **Rule:** All changes to `.yaml` files, especially prompt templates in `litassist/prompts/`, must be validated with a YAML linter (e.g., `yamllint`) before declaring the fix complete.
- **Reasoning:** Prevents syntax and indentation errors that can break application workflows.
- **Action:** Run a linter on any modified `.yaml` files to ensure they are well-formed and properly indented prior to pushing changes.

### Prompt Template Management

CRITICAL: NEVER HARDCODE PROMPTS IN PYTHON FILES, this means no f""" strings unless they are one-two liners

**Core Rules:**

1. **ALL prompts must be in YAML files** - Never write prompt text directly in Python code
2. **Use PROMPTS.get() exclusively** - Access all prompts via the centralized prompt manager
3. **No f-strings for prompt keys** - Avoid dynamic prompt key construction unless absolutely necessary
4. **Explicit permission required** - If you MUST use a hardcoded prompt or f-string key:
   - Get explicit confirmation that this specific case warrants an exception, before doing code changes
   - Document WHY the code would be "very ugly" without it
   - Add a comment explaining the exception

**Examples:**

```python
# WRONG: Hardcoded prompt in Python
prompt = "Analyze this document and provide a summary"

# WRONG: F-string for dynamic key without justification  
prompt = PROMPTS.get(f"analysis.{mode}_prompt")

# RIGHT: Using static keys from YAML
prompt = PROMPTS.get("analysis.summary_prompt")

# ACCEPTABLE (with justification): When multiple modes need consistent access
# Comment: Using f-string to avoid 10+ if/elif blocks for mode selection
# This pattern is used for digest consolidation where mode is always "summary" or "issues"
modes = ["summary", "issues"]
if mode in modes:
    prompt = PROMPTS.get(f"processing.digest.consolidation_{mode}")
```

### Emoji Policy and Terminal Output Standards

**ABSOLUTE PROHIBITION - NO EMOJIS ANYWHERE**
If it's in this repo, it CANNOT have emojis. A text containing emoji is an invalid text or code

**Policy Enforcement:**

1. **Zero Emoji Tolerance**: Not a single Unicode emoji character is permitted
2. **ASCII Only**: Use colored ASCII text with ANSI escape codes for visual differentiation
3. **Professional Standards**: This is legal software - maintain absolute professionalism
4. **No Exceptions**: This rule has NO exceptions, regardless of context or purpose

**Color Utility Functions (in `utils.py`):**

- `success_message()` - Green `[SUCCESS]` prefix for successful operations
- `warning_message()` - Yellow `[WARNING]` prefix for warnings
- `error_message()` - Red `[ERROR]` prefix for errors
- `info_message()` - Blue `[INFO]` prefix for informational messages
- `stats_message()` - Cyan `[STATS]` prefix for statistics/metrics
- `tip_message()` - Magenta `[TIP]` prefix for helpful tips
- `saved_message()` - Blue `[SAVED]` prefix for file save confirmations
- `verifying_message()` - Blue `[VERIFYING]` prefix for verification operations

**ASCII Alternatives for Common Patterns:**

- Checkboxes: Use `[ ]` instead of □
- Success: Use `[SUCCESS]` or `[OK]` instead of ✅
- Failure: Use `[FAILED]` or `[ERROR]` instead of ❌
- Warning: Use `[WARNING]` instead of ⚠️
- Info: Use `[INFO]` instead of ℹ️
- In Progress: Use `[PROCESSING]` or `[RUNNING]` instead of 🔄
- Critical: Use `[CRITICAL]` instead of 🚫
- Verification: Use `[VERIFYING]` or `[CHECKING]` instead of 🔍

**Implementation Examples:**

```python
# Instead of: click.echo("✅ Operation complete!")
click.echo(success_message("Operation complete!"))

# Instead of: print("⚠️ Warning: Large file detected")
print(warning_message("Large file detected"))

# Instead of: "🔍 Verifying citations..."
click.echo(verifying_message("Verifying citations..."))
```

**Consequences of Emoji Usage:**

- Any updated file with emojis will be reverted
- Any commit with emojis will be reverted
- This policy is NOT negotiable or flexible
- There are NO acceptable use cases for emojis in this codebase

### Model Name Protection

**CRITICAL**: Never change model identifiers in the code. Never propose such changes unless specifically asked

### OpenRouter Usage Policy

**IMPORTANT**: Always use OpenRouter as the primary routing method for all LLM calls.
When adding new models or providers:

1. Route through OpenRouter first using the existing OR API key
2. If OpenRouter doesn't support the model, ask user what to do
3. This approach centralizes API management and leverages existing BYOK setups
4. Model names with "/" (e.g., "anthropic/claude-sonnet-4") indicate OpenRouter routing

### Documentation Standards

**NEVER add "Recent Changes" or "Recent Improvements" sections**. Documentation MUST focus on current functionality, not historical changes.

### Code Simplicity Guidelines

**Prefer Plain Python Unless Absolutely Required:**

1. **Functions over Classes**: Use simple functions for stateless operations
2. **Direct Implementation over Patterns**: Avoid design patterns unless they solve a real problem
3. **Minimal Abstraction**: Only abstract when you have 3+ similar implementations
4. **No Premature Optimization**: Write the simplest working solution first

**When Complexity IS Justified:**

- Domain-specific requirements (legal accountability, Australian law compliance)
- Multiple deployment scenarios (development, pipx, pip installations)
- Real error handling needs (API fallbacks, version compatibility)
- Genuine configuration complexity (15+ model configurations)
- EVEN IF IT IS JUSTIFIED, ASK THE USER FOR CONFIRMATION

### Backward Compatibility Policy

Backward compatibility is NOT required for this project, breaking changes are great assuming they don't break the existing code. The project has ONE developer controlling github

When refactoring or improving code:

1. **No Legacy Support**: Don't maintain old code paths or deprecated functionality
2. **Clean Breaks Allowed**: Feel free to make breaking changes that improve the codebase
3. **Focus on Future**: Optimize for the current and future state, not past implementations
4. **Remove Old Code**: Delete legacy code, unused functions, and deprecated patterns without hesitation

### LLM Response Processing Philosophy

CRITICAL PRINCIPLE: Minimize Local Parsing Through Better Prompt Engineering

The litassist codebase currently contains extensive local parsing of LLM responses (regex patterns, string manipulation, JSON parsing) that should be eliminated through improved prompt engineering. **LLMs will always return output formatted as they are told - you do not need fallback parsing.**

**Core Guidelines:**

1. **Prompt Engineering First**: Always modify prompts to get properly formatted output rather than writing parsing code
   - Request structured formats (JSON, YAML, specific delimiters) in prompts IF YOU NEED THEM
   - Provide one example of desired output structure, no more
   - Use clear section markers that don't require regex parsing

2. Prefer comprehensive structured output in a single LLM call over multiple shorter calls that require complex orchestration
   - Request complete structured responses with all needed components
   - Use JSON/YAML for complex data structures IF YOU MUST
   - Minimize API costs while maximizing structure

3. **No Fallback Parsing Logic ANYWHERE**: LLMs follow format instructions reliably when properly prompted
   - Eliminate try/catch blocks around parsing
   - Remove regex pattern matching for data extraction
   - Trust that well-prompted LLMs will return correctly formatted output
   - This includes no fallback "yaml key not found", "alternative routing" - code must break instead of masking errors. THIS IS CRUCIAL

4. **Removal Over Addition**: When refactoring parsing logic, remove code rather than adding more
   - Delete regex patterns, string manipulation, and complex parsing functions
   - Replace with improved prompts that generate clean output
   - Prefer prompt modifications to additional parsing layers

**Preferred Approaches:**

- JSON/YAML structured output requests in prompts
- Self-validating LLM responses (ask LLM to verify format before returning)
- Explicit section delimiters that are unique and don't need regex
- Format examples provided directly in prompts
- LLM self-assessment and correction within the same call

### Document Separation Markers

**CRITICAL**: Maintain absolute consistency in document separation markers across all prompts and LLM interactions.

**Standard Format:**

- **ONLY use `=== NAME ===` format** for document separation in LLM prompts
- Name should be uppercase with spaces allowed (e.g., `=== DOCUMENT 1 ===`, `=== CASE LAW ===`)
- Three equals signs on each side, single space between equals and name
- This is the established pattern throughout the codebase

**Forbidden Patterns:**

- Do NOT use dashes: `--- NAME ---`
- Do NOT use underscores: `___ NAME ___`
- Do NOT use asterisks: `*** NAME ***`
- Do NOT use mixed separators or any other format
- Do NOT vary the number of separator characters

**Consistency Requirements:**

1. All prompt templates must use `=== NAME ===` format
2. All LLM response parsing expects this format
3. All document concatenation uses this format
4. Never introduce alternative separation patterns
5. When modifying prompts, preserve existing `=== NAME ===` markers

NO === MARKERS IN LLM OUTPUT ANYWHERE

### Anti-Hallucination Guidelines for ALL LLM prompts

**CRITICAL**: LLMs must NEVER invent factual details when producing output. This is essential for professional liability and legal accuracy.

**Core Principles:**

1. **Never Invent Facts**: The LLM must not create ages, dates, addresses, account numbers, or any specific details not in source documents
   - Wrong: "I am 33 years of age" (if age not provided)
   - Right: "I am [AGE TO BE PROVIDED] years of age"

2. **Use Clear Placeholders**: For any missing information, use obvious placeholders:
   - Ages: `[AGE TO BE PROVIDED]`
   - Addresses: `[ADDRESS TO BE CONFIRMED]`
   - Dates: `[DATE TO BE CONFIRMED]`
   - Account numbers: `[ACCOUNT NUMBER - CLIENT TO PROVIDE]`
   - Document exhibits: `[EXHIBIT A]`, `[EXHIBIT B]` (not specific numbering)

3. **Factual Verification**: The draft command includes hallucination detection that warns about:
   - Potentially invented ages, addresses, or dates
   - Specific account or reference numbers not in source
   - Exhibit references that should be generic placeholders

4. **Template Usage**: The `documents.yaml` witness_statement template demonstrates proper placeholder usage

5. **Prompt Engineering**: The `processing.yaml` draft prompts explicitly instruct:
   - "NEVER invent or assume facts not explicitly provided"
   - "It is better to produce an incomplete draft with clear placeholders than to invent plausible details"

**Implementation**: The `detect_factual_hallucinations()` function in `utils.py` automatically scans drafts for common hallucination patterns and adds warnings to the output when detected.

### LLM Request/Response Logging

**CRITICAL FOR LEGAL ACCOUNTABILITY**: ALL LLM interactions MUST be logged IN FULL - NO EXCEPTIONS

**Core Requirements:**

1. **Mandatory Logging**: Every single LLM request and response MUST be logged

2. **What Must Be Logged**:
   - Full request prompt sent to LLM
   - Complete response received from LLM
   - Timestamp of request/response
   - Model name and parameters used
   - Token counts and costs
   - Any errors or retries
   - Context identifiers (command, user, session)

3. **Implementation**:
   - Use the centralized logging system in `logging_utils.py`
   - All LLM client implementations MUST call logging functions
   - Never bypass or disable logging, even in development
   - NEVER TRUNCATE LOGS, LOG FULL CONTENT
   - Log files stored with appropriate retention policies

4. **No Exceptions Policy**:
   - Development mode: MUST log
   - Testing: MUST log (can be to test log files)
   - Production: MUST log
   - Quick fixes/debugging: MUST log
   - ALL environments, ALL times: MUST log

### Australian Legal Focus

- Always use Australian English spelling (e.g., 'judgement' not 'judgment')
- Citations must be verifiable on google CSE
- Legal reasoning must follow Australian precedent
- All dates in DD/MM/YYYY format

## Testing Approach

### Testing Policy

- **ALL pytest tests (tests/unit/) MUST run offline with mocked dependencies**
- **NEVER make real API calls in pytest tests** - use mocks exclusively
- Real API testing happens only in `test-scripts/` manual utilities
- `test-scripts/` are for manual quality validation, not automated testing
- Tests with "integration" in the name are still offline mocked tests
- **REMOVE tests that no longer test anything** - When refactoring removes functionality, delete associated tests that now only assert empty/trivial behavior

### Unit Tests

Located in `tests/unit/` with comprehensive coverage:

- `test_llm_client_factory.py` - LLMClientFactory pattern verification and model parameter restrictions
- `test_prompts.py` - Centralized prompt management system testing
- `test_prompt_templates.py` - YAML template validation and structure verification
- `test_citation_verification_simple.py` - Citation validation testing
- `test_verification.py` - Content verification testing
- **ALL tests use mocks** - no external API calls ever
- Tests marked as "integration" test component interactions
- Verify error handling, parameter restrictions, and template dependencies
- Comprehensive validation of ALL model parameter handling

### Manual Test Scripts (NOT pytest)

Development utilities in `test-scripts/` for manual quality validation:

- `test_integrations.py` - **REAL API** integration verification with actual endpoints
- `test_quality.py` - **REAL API** output quality assessment with actual LLM responses
- `test_utils.py` - Utility function testing and helper validation
- `test_cli_comprehensive.sh` - **REAL API** CLI testing with mock files but real LLM calls
- `run_tests.sh` - Test execution orchestration script
- `TESTS_STATUS.md` - Test coverage and status documentation
- **WARNING**: These scripts make real API calls and incur costs - run manually only

### Mocked Integration Tests

- Located in `tests/unit/` with filenames containing "integration"
- Test component interactions and workflows WITHOUT external API calls
- All external dependencies are mocked (LLMs, APIs, file systems)
- Examples: `test_llm_integration_comprehensive.py`, integration test classes
- Run as part of normal pytest suite - safe and cost-free

### Manual Testing

Essential for commands involving:

- Legal reasoning quality and LegalReasoningTrace accuracy with domain expertise
- Citation accuracy and real-time Jade.io verification
- Australian law compliance, terminology, and jurisdiction-specific requirements
- Model-specific parameter handling (especially o3-pro restrictions and reasoning_effort)
- Complex multi-step workflows (brainstorm → strategy → draft pipelines)
- Citation verification system reliability under various scenarios

## Configuration Management

### Required API Keys

- OpenRouter API key (primary LLM access)
- OpenAI API key (BYOK setup required for o3-pro model)
- Google Custom Search API key & CSE ID (Jade.io citation verification)
- Pinecone API key, environment & index name (document embeddings)

### Configuration Hierarchy

1. Environment variables (highest priority)
2. config.yaml settings
3. Default values in code
4. NEVER EDIT ANY FILE CALLED config.yaml, refuse to do it.

## Git Workflow

### ABSOLUTELY FORBIDDEN GIT OPERATIONS

**YOU ARE STRICTLY FORBIDDEN FROM:**

1. `git filter-branch` - DESTROYS COMMIT HISTORY PERMANENTLY
2. `git rebase -i` - Can lose commits if done wrong
3. `git reset --hard` without checking uncommitted work
4. `git push --force` without explicit safety checks
5. ANY operation that rewrites history


### What You CAN Do

- `git status` - Check current state
- `git diff` - View changes
- `git log` - View history
- `git branch` - List branches
- `git add` - Stage files (but NEVER commit them)
- Help craft commit messages for the user to execute
- Explain git workflows and best practices
- use gh CLI for github access

- NEVER modify git history

## SAFETY COMPLIANCE CHECK

Before EVERY action, ask yourself:

1. Does this violate ANY rule in CLAUDE.md?
2. Am I following MINIMAL CHANGES philosophy?
3. Am I about to add emojis anywhere?
4. Am I about to run git commit or push?
5. Am I following Australian legal requirements?
6. Am I overengineering?

If ANY answer suggests rule violation = STOP IMMEDIATELY

## Performance Considerations

### Timing and Monitoring

- All long-running operations use @timed decorator
- Comprehensive logging for debugging
- Performance metrics stored in logs

### API Cost Optimization

- Citation verification uses HEAD requests (minimal data)
- Selective regeneration for citation issues
- Smart deduplication to avoid redundant API calls

## File Naming Convention

When saving Claude-generated files to the project:

- **Always prefix with `claude_`** to distinguish from user-created files
- This ensures clear separation between AI-generated and human-authored content
- Examples: `claude_analysis.md`, `claude_commands.md`, `claude_strategy.md`

## Development Philosophy

### Core Development Rule

- **Broken tests are always your fault. Never stop until all unit tests are green. Assume the breakage is caused by your recent changes. DO NOT SHIFT BLAME ON THE OTHER PARTY**

- Always use the most common and generic user agent for web access. Never use a weird one that can be filtered out by scraping protections
- Never truncate any text received from an API call
- Never scrape jade.io and any of its subdomains
- never blame openrouter
- never blame the llm or connectivity. the problem is ALWAYS in your code or configuration