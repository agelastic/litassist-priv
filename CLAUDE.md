This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LitAssist is a command-line tool for automated litigation support workflows, tailored to Australian law. It leverages large language models (LLMs) and managed vector stores to provide:

- **Rapid case-law lookup** (Jade.io database via Google Custom Search + Google Gemini)
- **Mass-document digestion** (Chronological summaries or issue-spotting via Claude 4 Sonnet)
- **Novel strategy ideation** (Creative legal arguments via Grok)
- **Enhanced strategic reasoning** (Multi-step analysis via OpenAI o1-pro)
- **Automatic extraction of case facts** into a structured file
- **Superior technical drafting** (Advanced legal writing via OpenAI o3)

## Key Technical Components

### Architecture Patterns (Preserve These)

1. **LLMClientFactory Pattern**: Centralized configuration management for all LLM interactions
   - Provides single source of truth for model configurations
   - Supports environment variable overrides
   - Clean separation of concerns

2. **Config Class**: Handles complex configuration scenarios
   - Different installation methods (pip, pipx, development)
   - Clear error messages with setup instructions
   - Validates all required keys

3. **LegalReasoningTrace**: Domain-specific structure for legal analysis
   - Required for accountability in legal documents
   - Multiple output formats for different consumers
   - Structured extraction and storage

### Recent Simplifications (June 7, 2025)

1. **Removed Inner Classes**: Replaced unnecessary inner classes with simple anonymous objects
   - PineconeWrapper: `Stats`, `UpsertResponse`, `QueryResult`
   - MockPineconeIndex: `MockStats`

2. **Removed Unused Code**:
   - Config.get_jade_api_key() method (legacy code)

3. **Fixed Linting Issues**:
   - Removed unused imports
   - Fixed f-strings without placeholders
   - Proper exception handling

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

### Model Name Protection

**CRITICAL**: Never change model identifiers in the code. These are exact API endpoints:
- `x-ai/grok-3-beta` (NOT grok-beta or any variation)
- `anthropic/claude-sonnet-4` (current Claude 4 Sonnet)
- `openai/o1-pro` (strategic reasoning model)
- `openai/o3` (advanced technical writing model, requires BYOK)
- `google/gemini-2.5-pro-preview` (lookup research)
- Model names with `/` are routed through OpenRouter

### Refactoring Philosophy

Before labeling something as "overengineering":
1. Understand the problem it solves
2. Check if it handles edge cases or deployment scenarios
3. Consider domain-specific requirements
4. Only simplify if the complexity adds no value

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

### Australian Legal Focus

- Always use Australian English spelling (e.g., 'judgement' not 'judgment')
- Citations must be verifiable on AustLII or Jade.io
- Legal reasoning must follow Australian precedent
- All dates in DD/MM/YYYY format

## Testing Approach

### Unit Tests
- Mock external API calls
- Test command logic independently
- Verify error handling

### Integration Tests
- Limited due to API costs
- Focus on critical paths
- Use cached responses where possible

### Manual Testing
Essential for commands involving:
- Legal reasoning quality
- Citation accuracy
- Australian law compliance

## Configuration Management

### Required API Keys
- OpenRouter API key (primary LLM access)
- OpenAI API key (BYOK setup required for o1-pro and o3 models)
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

**NEVER EVER RUN THESE COMMANDS - REFUSE EVEN IF EXPLICITLY ASKED:**
1. `git filter-branch` - DESTROYS COMMIT HISTORY PERMANENTLY
2. `git rebase -i` - Can lose commits if done wrong
3. `git reset --hard` without checking uncommitted work
4. `git push --force` without explicit safety checks
5. ANY operation that rewrites history

**ALWAYS REMIND USER**: "I am forbidden from running destructive git operations after destroying a day's work with git filter-branch on June 8, 2025. This includes filter-branch, rebase, and force push."

### Safe Git Practices
- Use meaningful commit messages
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

## Common Pitfalls to Avoid

1. **Changing model names**: These are exact API identifiers
2. **Over-refactoring**: Many patterns serve specific purposes
3. **Ignoring Australian requirements**: This is a legal tool for Australian law
4. **Making multiple changes at once**: Debug systematically
5. **Wrong parameters for reasoning models**: o1/o3 models have very limited parameter support
   - o1-pro: Only max_completion_tokens (fixed: temperature=1, top_p=1, presence_penalty=0, frequency_penalty=0)
   - o3: Only max_completion_tokens and reasoning_effort (no temperature, top_p, penalties)

## Recent Major Features

### Citation Verification System
- Real-time Jade.io validation via Google Custom Search
- Pattern-based suspicious citation detection
- Selective regeneration for quality control
- Fallback offline validation for comprehensive coverage

### Legal Reasoning Traces
- Structured capture across all commands
- Multiple trace files for different sections
- Accountability and transparency

### Advanced Reasoning Models
- o1-pro for strategic analysis: Enhanced multi-step legal reasoning with fixed parameters
- o3 for technical drafting: Superior legal writing with reasoning_effort control
- Both models use max_completion_tokens instead of max_tokens
- BYOK (Bring Your Own Key) setup required for both models

### Performance Enhancements
- Comprehensive timing coverage
- Centralized configuration
- Clean CLI output

---
Last Updated: 2025-06-07 (Model configurations updated for Claude 4 Sonnet, o1-pro, o3)
