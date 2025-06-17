# Progress

## What works
- All seven core CLI commands (lookup, digest, extractfacts, brainstorm, strategy, draft, verify) fully implemented, stable, and tested
- Comprehensive post-hoc verification (June 2025): `verify` command performs citation accuracy, legal soundness, and reasoning transparency checks on generated documents. Each check writes a separate timestamped report to outputs/. All steps use the existing logging infrastructure and minimal console output.
- Research-informed brainstorming (June 2025): `brainstorm` command supports `--research` option to inject lookup report(s) into the orthodox strategies prompt, enabling research-grounded strategy generation. All prompt logic is managed in YAML; no hardcoded LLM templates.
- Major June 2025 improvements complete:
  - Lookup command overhaul: Jade.io-only, --comprehensive flag, improved extract options, citation integration, code quality/linting
  - Multi-section reasoning traces for brainstorm; enhanced strategy integration
  - Complete timing coverage and comprehensive logging for all operations
  - Centralized configuration and log format in config.yaml
  - Clean CLI output and professional summaries
  - Output file timestamping and organization in outputs/ and logs/
  - Model selection and BYOK requirements for advanced commands
  - Two-phase citation verification and selective regeneration (“Option B”)
- Robust test suite (unit and integration tests), ruff linting passing
- Documentation and Memory Bank fully aligned with codebase and user guides

## What’s left to build
- Implement advanced features from LLM_IMPROVEMENTS.md (e.g., IRAC/MIRAT enforcement, multi-model consensus, confidence scoring)
- Develop integration tests for OpenRouter and extended RAG workflows
- Add cost-tracking, quality-tier system, and workflow compound commands
- Enhance QA loops (adversarial testing, iterative improvement loops) and performance benchmarking
- Continue to update Memory Bank after each major feature, bugfix, or workflow change

## Current status
Core pipeline, post-hoc verification, and all major improvements are complete and stable. Memory Bank, documentation, and codebase are fully synchronized. Focus is now on advanced features, QA, and workflow enhancements.

## Known issues
- Several advanced prompting and verification improvements remain unimplemented
- Integration testing for OpenRouter and Pinecone cleanup not yet automated
- Cost-tracking and quality-tier features absent
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
