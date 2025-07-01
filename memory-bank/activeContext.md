# Active Context

## Current Work Focus
Maintaining the Memory Bank as the authoritative, up-to-date reference for LitAssist's architecture, workflows, and development state. Incorporating all June 2025 improvements, workflow clarifications, and best practices from the latest documentation.

**Latest update (7 January 2025):**
- COMPLETED: Counsel's Notes command implementation with comprehensive documentation suite
- FIXED: Added missing LLMClientFactory configuration for counselnotes command
- Full strategic analysis framework with 5-section structure (Overview, Opportunities, Risks, Recommendations, Management)
- Four JSON extraction modes (all, citations, principles, checklist) with structured output
- Multi-document cross-synthesis capabilities for complex case analysis
- Complete documentation: user guide, technical docs, examples, integration patterns
- Professional Australian legal context and citation verification integration
- LLMClientFactory integration: anthropic/claude-sonnet-4, temp=0.3, top_p=0.7, force_verify=True
- Ready for production use in Australian legal practice

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
1. **Integration Testing**: Comprehensive CLI testing of counselnotes command with real documents
2. **Performance Optimization**: Multi-document processing efficiency and large case file handling
3. **Advanced Features**: Custom prompt templates for specialized practice areas, batch processing
4. Continue to update Memory Bank after each major feature, bugfix, or workflow change.
5. Track progress on advanced features (IRAC/MIRAT enforcement, multi-model consensus, QA loops, cost-tracking, compound commands).
6. Ensure all new patterns, troubleshooting, and best practices are reflected in systemPatterns.md and techContext.md.
7. Periodically review Memory Bank for alignment with evolving documentation and codebase.

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
