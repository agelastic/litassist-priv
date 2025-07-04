# Active Context

## Current Work Focus
- **Barbrief Feature Branch**: Currently on `feature/barbrief-command` branch after completing implementation
- **Latest Implementation**: Barbrief command for comprehensive barrister's briefs
- **Memory Bank Maintenance**: Updating Memory Bank with barbrief implementation details
- **Feature Complete**: Barbrief command tested and documented, ready for integration

**Latest update (7 January 2025):**
- COMPLETED: Barbrief command implementation for comprehensive barrister's briefs
- IMPLEMENTED: Full command structure with 10-section brief format
- FIXED: Prompt template syntax conversion from Jinja2 to Python format strings
- ADDED: LLMClientFactory configuration for barbrief using openai/o3-pro model
- KEY FEATURES:
  - 10-heading case facts validation from extractfacts
  - Multiple input support: strategies, research reports, supporting documents
  - Hearing-type specific formatting (trial, directions, interlocutory, appeal)
  - Citation verification integration with verify flag
  - 32K token limit (max_completion_tokens) for comprehensive output
  - Comprehensive error handling for API failures
- TESTING: Integration tests pass, unit tests for validation complete
- DOCUMENTATION: Added to README with BYOK requirements and examples

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
1. **Branch Merge**: Prepare counselnotes feature branch for merge to master
2. **Integration Testing**: Final validation of counselnotes command with diverse legal documents
3. **Performance Validation**: Confirm multi-document processing efficiency
4. **User Acceptance**: Validate counselnotes meets Australian legal practice requirements
5. **Production Deployment**: Deploy counselnotes to production environment
6. **Advanced Features**: Custom prompt templates for specialized practice areas
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
