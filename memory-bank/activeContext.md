# Active Context

## Current Work Focus
- **Verification System Fixes**: Critical fixes to preserve full document content during verification
- **Token Limit Improvements**: Increased verification limits to handle full brainstorm outputs
- **Code Simplification**: Removed redundant verify_with_level usage and local parsing
- **Memory Bank Maintenance**: Documenting all recent updates and improvements

**Latest update (7 July 2025 - Verification System):**
- FIXED: Missing "MOST LIKELY TO SUCCEED" section in brainstorm outputs
- FIXED: System instructions bleeding into verified content ("Australian law only...")
- FIXED: Content truncation due to low token limits (800-1536 → 8192-16384)
- REMOVED: ~25 lines of local parsing in brainstorm.py - trust LLM output
- SIMPLIFIED: verify_with_level now only used for "heavy" verification
- UPDATED: Prompt templates to preserve ALL sections and prevent instruction bleeding
- PRINCIPLE: Following CLAUDE.md - "minimize local parsing through better prompt engineering"

**Recent updates (6-7 July 2025):**
- ENHANCED: Strategy generation with 3-5 paragraphs per strategy (was 2-3 sentences)
- ADDED: Multiple input file support for extractfacts command
- UPDATED: Grok model to x-ai/grok-3
- INCREASED: Token limits to 32k for all generation models
- CONVENTION: Claude-generated files now prefixed with claude_
- CHANGED: Claude files no longer ignored by git

**Previous update (7 January 2025 - Barbrief):**
- COMPLETED: Barbrief command implementation for comprehensive barrister's briefs
- IMPLEMENTED: Full command structure with 10-section brief format
- FIXED: Critical bugs resolved during final testing:
  - Changed LLMClientFactory method from incorrect `get_client` to correct `for_command`
  - Fixed save_reasoning_trace to use 2 arguments instead of 3 (removed deprecated third parameter)
  - Prompt template syntax conversion from Jinja2 to Python format strings
- ADDED: LLMClientFactory configuration for barbrief using openai/o3-pro model
- KEY FEATURES:
  - 10-heading case facts validation from extractfacts command output
  - Multiple input support: strategies, research reports, supporting documents
  - Hearing-type specific formatting (trial, directions, interlocutory, appeal)
  - Citation verification integration with verify flag
  - 32K token limit (max_completion_tokens) for comprehensive output
  - Comprehensive error handling for API failures
  - Reasoning trace capture for transparency
- TESTING: 
  - All 11 unit tests passing in test_barbrief.py
  - CLI comprehensive tests added with mock files in test-scripts/
  - Integration with existing test suite validated
- DOCUMENTATION: 
  - Added to README with BYOK requirements and examples
  - User Guide updated with barbrief command documentation
  - Technical documentation complete in docs/commands/barbrief.md
  - Memory Bank files updated to reflect completion

**Previous update (7 January 2025 - CounselNotes):**
- COMPLETED: Counsel's Notes command implementation with comprehensive documentation suite
- Full strategic analysis framework with 5-section structure (Overview, Opportunities, Risks, Recommendations, Management)
- Four JSON extraction modes (all, citations, principles, checklist) with structured output
- Multi-document cross-synthesis capabilities for complex case analysis
- LLMClientFactory integration: anthropic/claude-sonnet-4, temp=0.3, top_p=0.7, force_verify=True

**Previous update (19 June 2025):**
- Completed lookup command refactoring to eliminate fragile regex parsing and leverage structured LLM output
- Implemented JSON-first extraction with regex fallback for --extract options (citations, principles, checklist)
- Added --context flag to lookup command for targeted analysis guidance
- Updated prompts to instruct LLM to return structured JSON for extraction requests
- Enhanced test suite to validate new --context functionality
- Updated user documentation to reflect improved extraction workflow

**Previous update (16 June 2025):**
- Synchronized all prompt YAML files and test suites so that tests only validate active (uncommented) templates.
- Commented out all test code for templates that are commented out in the YAML files, including in `test_prompt_templates.py` and `test_prompts.py`.
- Fixed all schema and accessibility checks for commented-out prompt keys (including lookup.yaml, documents.yaml, base.yaml).
- All tests now pass after these changes.

## Recent Changes
- **MAJOR COMPLETION (January 7, 2025): Barbrief Command**
  - Complete implementation in `litassist/commands/barbrief.py`
  - Comprehensive barrister's brief generation with 10-section structure
  - Integration with extractfacts command for case facts validation
  - Support for multiple input types: strategies, research, supporting documents
  - Hearing-type specific formatting (trial, directions, interlocutory, appeal)
  - Full citation verification integration
  - Fixed critical implementation bugs during testing
  - Complete test suite with 11 unit tests and CLI integration tests
  - Full documentation suite: user guide, technical docs, examples

- **MAJOR COMPLETION (January 7, 2025): Counsel's Notes Command**
  - Complete implementation in `litassist/commands/counselnotes.py`
  - Strategic analysis framework with advocate perspective vs neutral digest
  - Four JSON extraction modes for structured data output
  - Multi-document synthesis and cross-document analysis
  - Full documentation suite: user guide, technical docs, examples
  - Integration with existing citation verification and LLM systems
  - Professional Australian legal context throughout

- Implemented major June 2025 improvements:
  - Lookup command overhaul: Jade.io-only, new --comprehensive flag, improved extract options, citation integration, code quality/linting
  - Multi-section reasoning traces for brainstorm; enhanced strategy integration
  - Complete timing coverage and comprehensive logging for all operations
  - Centralized configuration and log format in config.yaml
  - Clean CLI output and professional summaries
  - Output file timestamping and organization in outputs/ and logs/
  - Model selection and BYOK requirements for advanced commands
  - Two-phase citation verification and selective regeneration ("Option B")
- Added optional --hint argument to digest command (June 2025): allows users to provide a text hint to focus LLM analysis on topics related to the hint, supporting targeted processing of non-legal and general documents.
- Updated Memory Bank files for consistency with README, User Guide, and config.yaml.template
- Full Memory Bank review performed on 15 June 2025: all files confirmed up to date and synchronized with codebase and documentation. No changes required.
- 16 June 2025: Test suite and prompt YAMLs synchronized; all tests for commented-out templates are now commented out in the test code. All tests pass.

## Next Steps
1. **Branch Merge**: Merge feature/barbrief-command branch to master (ready for merge)
2. **Production Deployment**: Deploy barbrief command to production environment
3. **User Training**: Create tutorial materials for barbrief command usage
4. **Performance Monitoring**: Track o3-pro model performance and token usage
5. **Advanced Features**: Custom prompt templates for specialized hearing types
6. **Integration Enhancement**: Streamline workflow between extractfacts → barbrief
7. **Memory Bank Maintenance**: Continue systematic updates after major changes

## Active Decisions & Considerations
- Strict adherence to Memory Bank hierarchy and .clinerules formatting rules.
- Use pipx as the default install method; config.yaml in ~/.config/litassist/ for global use.
- Emphasize two-phase citation verification (Jade.io primary, offline fallback) and selective regeneration for quality control.
- Clarify brainstorm vs strategy distinction: brainstorm = creative exploration, strategy = tactical implementation.
- Maintain clean CLI output, timestamped files, and professional summaries as standard UX.

## Important Patterns & Preferences
- Use Markdown for all Memory Bank files.
- Include mermaid diagrams where they aid clarity (see projectbrief.md).
- Reference code, config, and docs accurately; avoid speculative content.
- Document all new workflow patterns, integration strategies, and troubleshooting tips.

## Learnings & Insights
- The Memory Bank is essential for onboarding, context retention, and planning after session resets.
- Centralizing architecture, workflow, and technical context streamlines future development and QA.
- Clear distinction and integration pattern between brainstorm and strategy commands improves user understanding and workflow efficiency.
- Periodic full reviews (as on 15 June 2025) ensure Memory Bank remains the authoritative, up-to-date reference for all development and planning.
