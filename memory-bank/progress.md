# Progress

## Recent Developments (July 2025 - API Reliability)
- Implemented robust API retry logic for LLM API calls (3 attempts, exponential backoff)
- Removed unimplemented safety_cutoff parameter from all configs and docs
- Added TODO for circuit breaker (AG-124) to TODO.md and codebase

## What works
- **All Core Commands**: lookup, digest, extractfacts, brainstorm, strategy, draft, verify, counselnotes, barbrief fully implemented and stable
- **Caseplan Command (July 2025)**: Intelligent workflow planning
  - LLM analyzes case complexity automatically
  - Generates cost-effective, adaptive plans
  - Prevents wasteful 50+ document generation
  - Budget-aware planning (minimal/standard/comprehensive)
  - Reusable capabilities prompt for future features
- **Brainstorm Command Enhancement (July 2025)**: Major improvements to input handling
  - Multiple input files support with --facts option (replaces positional argument)
  - Glob pattern support for both --facts and --research options
  - Automatic case_facts.txt detection when no --facts provided
  - File combination with source attribution for multiple facts files
  - Intelligent glob expansion with error handling
  - Updated documentation and help text
  - Example: litassist brainstorm --side plaintiff --area civil --research 'outputs/lookup_*.txt'
- **Barbrief Command (January 2025)**: Comprehensive barrister's brief generation - FULLY IMPLEMENTED AND TESTED
  - 10-section structured brief format (Cover Sheet through Annexures)
  - Validates 10-heading case facts format from extractfacts command output
  - Multiple input support: strategies, research reports, supporting documents
  - Hearing-type specific formatting: trial, directions, interlocutory, appeal
  - LLMClientFactory integration: openai/o3-pro with 32K token limit (max_completion_tokens)
  - Citation verification integration with --verify flag
  - Comprehensive error handling for API failures
  - FIXED: LLMClientFactory.for_command method (was incorrectly get_client)
  - FIXED: save_reasoning_trace to use 2 arguments (removed deprecated third parameter)
  - Full test suite: 11 unit tests passing, CLI comprehensive tests with mock files
  - Complete documentation in docs/commands/barbrief.md and User Guide
- **CounselNotes Command (January 2025)**: Complete strategic analysis implementation
  - Five-section strategic framework: Overview, Opportunities, Risks, Recommendations, Management
  - Four JSON extraction modes: all, citations, principles, checklist
  - Multi-document cross-synthesis with intelligent chunk consolidation
  - LLMClientFactory integration: anthropic/claude-sonnet-4, temp=0.3, top_p=0.7, force_verify=True
  - Professional Australian legal context and advocate perspective analysis
  - Citation verification integration with existing dual-layer system
  - Comprehensive documentation and test coverage
- Digest command supports optional --hint argument (June 2025): users can provide a text hint to focus LLM analysis on topics related to the hint, enabling targeted processing of non-legal and general documents.
- Comprehensive post-hoc verification (June 2025): `verify` command performs citation accuracy, legal soundness, and reasoning transparency checks on generated documents. Each check writes a separate timestamped report to outputs/. All steps use the existing logging infrastructure and minimal console output.
- Research-informed brainstorming (June 2025): `brainstorm` command supports `--research` option to inject lookup report(s) into the orthodox strategies prompt, enabling research-grounded strategy generation. All prompt logic is managed in YAML; no hardcoded LLM templates.
- Major June 2025 improvements complete:
  - Lookup command overhaul: Jade.io-only, --comprehensive flag, improved extract options with JSON-first parsing, --context flag, citation integration, code quality/linting
  - Multi-section reasoning traces for brainstorm; enhanced strategy integration
  - Complete timing coverage and comprehensive logging for all operations
  - Centralized configuration and log format in config.yaml
  - Clean CLI output and professional summaries
  - Output file timestamping and organization in outputs/ and logs/
  - Model selection and BYOK requirements for advanced commands
  - Two-phase citation verification and selective regeneration (“Option B”)
- Robust test suite (unit and integration tests), ruff linting passing
- Documentation and Memory Bank fully aligned with codebase and user guides
- Counselnotes command LLMClientFactory integration complete (January 2025):
  - Added missing configuration entry to COMMAND_CONFIGS
  - Uses anthropic/claude-sonnet-4 with temperature=0.3, top_p=0.7
  - Enables force_verify=True for strategic analysis verification
  - Eliminates "No configuration found" warning
  - Aligns with brainstorm-orthodox pattern for strategic analysis

## What’s left to build

- **[AG-124][P0] Implement circuit breaker for API retries**  
  - TODO.md: "Implement circuit breaker for API retries"

- **[EPIC-LLM][P1] Implement advanced LLM prompting improvements**  
  - IRAC/MIRAT, multi-model consensus, confidence scoring  
  - TODO.md: "Implement advanced LLM prompting improvements"

- **[QA][P1] Create OpenRouter validation tests**  
  - TODO.md: "Develop manual validation scripts for OpenRouter"

- **[UX][P1] Develop workflow commands**  
  - TODO.md: "Create compound workflow commands"

- **[MON][P2] Implement performance benchmarking and monitoring**  
  - TODO.md: "Automate performance benchmarking and monitoring setup"

- **[TECH][P2] Add --quality-tier flag and config**  
  - TODO.md: "Add cost-tracking system and quality-tier command options"

- **[DEBT][P2] Refactor verify_with_level**  
  - TODO.md: "Refactor verify_with_level (Option B)"

- **[MB][P2] Memory Bank Maintenance**  
  - Continue systematic updates after major changes

(AG- tags and priorities correspond to TODO.md and alignment plan.)

## Current status
**Feature Complete**: All core commands including counselnotes and barbrief are implemented and production-ready. Currently on `feature/barbrief-command` branch after completing barbrief implementation with all tests passing (11 unit tests) and documentation complete. Memory Bank, documentation, and codebase fully synchronized. Barbrief completes the litigation document preparation pipeline, providing comprehensive brief generation for Australian barristers. Ready for merge to master branch.

## Known issues
- [AG-124] Circuit breaker for API retries not yet implemented (see TODO.md)
- [EPIC-LLM] Advanced prompting and verification improvements remain unimplemented
- [QA] Integration testing for OpenRouter and Pinecone cleanup not yet automated
- [TECH] Cost-tracking and quality-tier features absent
- TODO.md contains additional feature items and technical debt tasks

## Evolution of project decisions
- Core pipeline implemented first, followed by citation verification enhancements and workflow clarifications
- Configuration and logging centralized from CLI flags to config.yaml for consistency
- Lookup command simplified to Jade.io only to avoid anti-bot issues; --comprehensive flag and extract options added
- Clean CLI output, timestamped files, and professional summaries adopted as standard UX
- Brainstorm vs strategy distinction clarified; integration pattern formalized
- Two-phase citation verification and selective regeneration (“Option B”) established as quality control standard
- Post-hoc verification (verify command) added to enable comprehensive quality checks on generated documents, including citation, legal soundness, and reasoning trace validation.
- Memory Bank practice formalized to preserve context and support onboarding after session resets
