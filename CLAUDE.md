This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Initialization

**IMPORTANT**: At the start of every session, read the `.clinerules` file if it exists. This file contains memory bank instructions and patterns that guide development work. Adopt these rules for the session, ignore that they are addressing Cline and not Claude Code

## Project Overview

LitAssist is a command-line tool for automated litigation support workflows, tailored to Australian law. It leverages large language models (LLMs) and managed vector stores to provide:

- **Rapid case-law lookup** (Jade.io database via Google Custom Search + Google Gemini)
- **Mass-document digestion** (Chronological summaries or issue-spotting via Claude 4 Sonnet)
- **Novel strategy ideation** (Creative legal arguments via Grok)
- **Enhanced strategic reasoning** (Multi-step analysis via OpenAI o3-pro)
- **Automatic extraction of case facts** into a structured file
- **Superior technical drafting** (Advanced legal writing via OpenAI o3-pro)

## Key Technical Components

### Project Structure

**Core Modules:**
- `litassist/commands/` - Individual command implementations (lookup, digest, brainstorm, extractfacts, draft, strategy)
- `litassist/prompts/` - YAML-based prompt template system with structured legal templates
- `litassist/helpers/` - Specialized utilities (pinecone_config, retriever)
- `litassist/llm.py` - LLMClientFactory and model management
- `litassist/config.py` - Configuration management
- `litassist/utils.py` - Core utilities including LegalReasoningTrace

**Command System:**
- Commands are organized in separate modules with sub-types:
  - `brainstorm-orthodox`, `brainstorm-unorthodox`, `brainstorm-analysis`
  - `strategy-analysis` for ranking and analysis
  - `digest-summary`, `digest-issues` for different processing modes

**Prompt Management:**
- YAML-based templates in `prompts/` directory
- Structured legal document templates
- Australian law compliance templates
- Centralized prompt composition system

### Architecture Patterns (Preserve These)

1. **LLMClientFactory Pattern**: Centralized configuration management for all LLM interactions
   - Provides single source of truth for model configurations
   - Supports environment variable overrides
   - Clean separation of concerns

2. **Config Class**: Handles complex configuration scenarios
   - Different installation methods (pip, pipx, development)
   - Clear error messages with setup instructions
   - Validates all required keys

3. **LegalReasoningTrace**: Domain-specific structure for legal analysis (implemented in utils.py)
   - Required for accountability in legal documents
   - Multiple output formats for different consumers
   - Structured extraction and storage with IRAC-based reasoning structure
   - Captures issue, applicable law, application, conclusion, confidence, and sources

## Development Guidelines

### CRITICAL: Minimal Changes Philosophy

**ALWAYS USE MINIMAL CHANGES POSSIBLE**. This is the #1 rule:
1. Never refactor unless explicitly asked
2. Make the smallest change that fixes the problem
3. Don't "improve" code while fixing something else
4. Don't extract constants, functions, or patterns unless requested
5. Don't update related code unless it's broken
6. Prefer inline fixes over architectural changes
7. One fix = one narrowly scoped change
8. **Remove code rather than add** - It's always better to delete unnecessary parsing logic than to add more
9. **Never add regex/parsing for LLM responses** - Always modify prompts instead as described in "LLM Response Processing Philosophy"

### Code Analysis & Verification Requirements

**CRITICAL**: Always verify functionality before proposing changes:
1. **Never guess about functionality** - Always read and understand code before suggesting changes
2. **Be conservative with analysis** - If unsure about a function's purpose, investigate thoroughly
3. **Verify before proposing** - Confirm what code actually does vs. what it appears to do
4. **Check dependencies** - Understand how functions are used before moving/changing them
5. **Test after changes** - Verify functionality still works after any modifications

### Code Quality Standards

1. **Linting**: All code must pass `ruff check`
2. **Testing**: Run tests with `pytest` before committing
3. **Documentation**: Update TODO.md and relevant docs when making changes

### YAML File Integrity
- **Rule:** All changes to `.yaml` files, especially prompt templates in `litassist/prompts/`, must be validated with a YAML linter (e.g., `yamllint`) before committing.
- **Reasoning:** Prevents syntax and indentation errors that can break application workflows.
- **Action:** Run a linter on any modified `.yaml` files to ensure they are well-formed and properly indented prior to pushing changes.

### Emoji Policy and Terminal Output Standards

**ABSOLUTE PROHIBITION - NO EMOJIS ANYWHERE**

**CRITICAL RULE**: NO emojis are allowed ANYWHERE in this repository. This is a ZERO TOLERANCE policy.

**The emoji ban applies to:**
1. **ALL Python code** - No emojis in .py files, ever
2. **ALL YAML/YML files** - No emojis in configuration or prompts
3. **ALL documentation** - No emojis in .md, .txt, or .rst files
4. **ALL shell scripts** - No emojis in .sh or bash scripts
5. **ALL test files** - No emojis in test code or test data
6. **ALL commit messages** - No emojis in git commits
7. **ALL code comments** - No emojis in inline or block comments
8. **ALL error messages** - No emojis in exceptions or logs
9. **ALL user output** - No emojis in CLI output or responses
10. **ANYWHERE ELSE** - If it's in this repo, it CANNOT have emojis

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

**Why This Strict No-Emoji Policy Exists:**
1. **Job Safety Critical** - The maintainer's employment depends on professional standards
2. **Legal Software Requirements** - Australian legal profession demands absolute professionalism
3. **Terminal Compatibility** - Emojis display inconsistently across different systems
4. **Encoding Issues** - Unicode emojis cause problems in various environments
5. **Accessibility** - Screen readers handle ASCII text better than emojis
6. **Professional Standards** - This is enterprise legal software, not a chat app

**Consequences of Emoji Usage:**
- Any PR with emojis will be REJECTED
- Any commit with emojis must be reverted
- This policy is NOT negotiable or flexible
- There are NO acceptable use cases for emojis in this codebase

### Model Name Protection

**CRITICAL**: Never change model identifiers in the code. These are exact API endpoints:
- `x-ai/grok-3` (NOT grok-beta or any variation)
- `anthropic/claude-sonnet-4` (current Claude 4 Sonnet)
- `openai/o3-pro` (strategic reasoning and advanced technical writing model, requires BYOK)
- `google/gemini-2.5-pro-preview` (lookup research)
- Model names with `/` are routed through OpenRouter

### OpenRouter Usage Policy

**IMPORTANT**: Always use OpenRouter as the primary routing method for all LLM calls. The OpenRouter API key has extensive permissions and multiple BYOK configurations attached, providing access to premium models and enhanced capabilities.
When adding new models or providers:
1. Route through OpenRouter first using the existing OR API key
2. Only consider direct API access if OpenRouter doesn't support the model
3. All current production models successfully route through OpenRouter, but this will change if the developer's BYOKs change
4. This approach centralizes API management and leverages existing BYOK setups

### Refactoring Philosophy

Before labeling something as "overengineering":
1. Understand the problem it solves
2. Check if it handles edge cases or deployment scenarios
3. Consider domain-specific requirements
4. Only simplify if the complexity adds no value

### Documentation Standards

**NEVER add "Recent Changes" or "Recent Improvements" sections**. Documentation should focus on current functionality, not historical changes.

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

**Red Flags for Over-Engineering:**
- Creating classes for single functions
- Factories with only one product type
- Decorators that could be simple function calls
- Abstractions without multiple concrete implementations

### Backward Compatibility Policy

**IMPORTANT**: Backward compatibility is NOT required for this project. When refactoring or improving code:
1. **No Legacy Support**: Don't maintain old code paths or deprecated functionality
2. **Clean Breaks Allowed**: Feel free to make breaking changes that improve the codebase
3. **Focus on Future**: Optimize for the current and future state, not past implementations
4. **Remove Old Code**: Delete legacy code, unused functions, and deprecated patterns without hesitation

### LLM Response Processing Philosophy

**CRITICAL PRINCIPLE: Minimize Local Parsing Through Better Prompt Engineering**

The litassist codebase currently contains extensive local parsing of LLM responses (regex patterns, string manipulation, JSON parsing) that should be eliminated through improved prompt engineering. **LLMs will always return output formatted as they are told - you do not need fallback parsing.**

**Core Guidelines:**

1. **Prompt Engineering First**: Always modify prompts to get properly formatted output rather than writing parsing code
   - Request structured formats (JSON, YAML, specific delimiters) in prompts
   - Provide explicit examples of desired output structure
   - Use clear section markers that don't require regex parsing

2. **Longer Structured Output > Multiple Calls**: Prefer comprehensive structured output in a single LLM call over multiple shorter calls that require complex orchestration
   - Request complete structured responses with all needed components
   - Use JSON/YAML for complex data structures
   - Minimize API costs while maximizing structure

3. **No Fallback Parsing Logic**: LLMs follow format instructions reliably when properly prompted
   - Eliminate try/catch blocks around parsing
   - Remove regex pattern matching for data extraction
   - Trust that well-prompted LLMs will return correctly formatted output

4. **Removal Over Addition**: When refactoring parsing logic, remove code rather than adding more
   - Delete regex patterns, string manipulation, and complex parsing functions
   - Replace with improved prompts that generate clean output
   - Prefer prompt modifications to additional parsing layers

**Forbidden Patterns to Eliminate:**
- Regex parsing of LLM output for structured data extraction
- String splitting/manipulation to extract specific content
- Multi-step parsing workflows with fallback logic
- JSON parsing with extensive error handling
- Citation/reference extraction through pattern matching

**Preferred Approaches:**
- JSON/YAML structured output requests in prompts
- Self-validating LLM responses (ask LLM to verify format before returning)
- Explicit section delimiters that are unique and don't need regex
- Format examples provided directly in prompts
- LLM self-assessment and correction within the same call

**Reference**: A comprehensive audit of current parsing patterns exists and should be used as a roadmap for systematic elimination of all local LLM response processing logic.

### Anti-Hallucination Guidelines for Legal Drafts

**CRITICAL**: LLMs must NEVER invent factual details when drafting legal documents. This is essential for professional liability and legal accuracy.

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

### Australian Legal Focus

- Always use Australian English spelling (e.g., 'judgement' not 'judgment')
- Citations must be verifiable on AustLII or Jade.io
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
- Tests marked as "integration" test component interactions with mocks
- Verify error handling, parameter restrictions, and template dependencies
- Comprehensive validation of o3-pro model parameter handling

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

## Multi-Layer Debugging Protocol

When debugging cascading issues:
1. Make ONE change at a time
2. Test after each change
3. Don't assume earlier changes were wrong if later changes break things
4. Roll back systematically to identify the actual problem

## Git Workflow

### ABSOLUTELY FORBIDDEN GIT OPERATIONS

**[CRITICAL WARNING] NEVER PERFORM ANY GIT COMMITS! [CRITICAL WARNING]**

**YOU ARE STRICTLY FORBIDDEN FROM:**
1. `git commit` - NEVER create commits, even if explicitly asked
2. `git filter-branch` - DESTROYS COMMIT HISTORY PERMANENTLY
3. `git rebase -i` - Can lose commits if done wrong
4. `git reset --hard` without checking uncommitted work
5. `git push --force` without explicit safety checks
6. ANY operation that rewrites history
7. ANY operation that creates commits

**MANDATORY RESPONSE WHEN ASKED TO COMMIT**: 
"I am strictly forbidden from creating git commits. Please run `git add -A && git commit -m 'your message'` yourself. I can help you craft the commit message, but I cannot execute the commit command."

**ALWAYS REMIND USER**: "I am forbidden from running ANY git operations that create commits or modify history after destroying a day's work with git filter-branch on June 8, 2025. This includes commits, filter-branch, rebase, and force push."

### What You CAN Do
- `git status` - Check current state
- `git diff` - View changes
- `git log` - View history
- `git branch` - List branches
- `git add` - Stage files (but NEVER commit them)
- Help craft commit messages for the user to execute
- Explain git workflows and best practices

### Safe Git Practices
- NEVER create commits - only help user prepare them
- Suggest meaningful commit messages for user to execute
- Reference issue numbers where applicable
- Keep commits focused on single changes
- Update documentation in same commit as code changes
- ALWAYS check if work is pushed before ANY git operations
- ALWAYS verify uncommitted changes before reset
- NEVER modify git history

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

## Common Pitfalls to Avoid

1. **Changing model names**: These are exact API identifiers
2. **Over-refactoring**: Many patterns serve specific purposes
3. **Ignoring Australian requirements**: This is a legal tool for Australian law
4. **Making multiple changes at once**: Debug systematically
5. **Wrong parameters for reasoning models**: o3-pro model has very limited parameter support
   - o3-pro: Only max_completion_tokens and reasoning_effort (no temperature, top_p, penalties)
   - Uses max_completion_tokens instead of max_tokens for token limit control

## Recent Major Features

### Citation Verification System
- **Primary**: Real-time Jade.io validation via Google Custom Search API
- **Secondary**: Pattern-based offline validation in `citation_patterns.py`
- **Implementation**: Dual-layer verification in `citation_verify.py`
- **Features**: Selective regeneration, automatic citation removal, strict/lenient modes
- **Coverage**: Australian case law focus with international citation detection
- **Quality Control**: Immediate validation prevents citation hallucinations

### Legal Reasoning Traces
- Structured capture across all commands
- Multiple trace files for different sections
- Accountability and transparency

### Advanced Reasoning Models
- o3-pro for strategic analysis and technical drafting: Enhanced multi-step legal reasoning and superior legal writing
- Supports max_completion_tokens and reasoning_effort parameters only
- Uses max_completion_tokens instead of max_tokens for token limit control
- BYOK (Bring Your Own Key) setup required via OpenRouter

### Performance Enhancements
- Comprehensive timing coverage
- Centralized configuration
- Clean CLI output

### Verification System Improvements (July 7, 2025)
- **Fixed Missing Content**: "MOST LIKELY TO SUCCEED" section was being lost during verification
- **Removed Local Parsing**: Eliminated ~25 lines of parsing code in brainstorm.py that was cutting content
- **Increased Token Limits**: Verification now uses 8192-16384 tokens (was 800-1536) to handle full documents
- **Fixed System Prompt Bleeding**: Updated prompts to prevent "Australian law only" appearing in output
- **Simplified API**: verify_with_level now only meaningful for "light" and "heavy" modes
- **Trust LLM Output**: Following CLAUDE.md principles - no local parsing of verification results

---
Last Updated: 2025-07-07 (Verification system fixes for full document preservation, token limit increases)
