# Active Context

## Current Work Focus

- **Infrastructure & Architecture Improvements (July 18, 2025):**
  - Added comprehensive architectural documentation (`ARCHITECTURE Codex.md` and `ARCHITECTURE Gemini.md`) detailing system design, component relationships, and data flow.
  - Implemented GitHub Actions CI/CD pipeline for automated testing on PRs (Python 3.11 and 3.12).
  - Added pre-commit hooks for running pytest with fast-fail on every commit.
  - Enhanced caseplan command to generate executable bash scripts extracting all CLI commands from workflow plans.
  - Created comprehensive LaTeX article documenting the LitAssist workflow system.

- **Testing Infrastructure Updates (July 18, 2025):**
  - Replaced `tempfile` with pytest's `tmp_path` fixture throughout unit tests for better test isolation.
  - Added new unit tests: `test_digest_command.py`, `test_extractfacts_command.py`, `test_utils_additional.py`.
  - Updated Python version requirement to >=3.11 (from 3.8) and refined project licensing information.
  - Enhanced test coverage for barbrief and caseplan commands.

- **Documentation & Planning (July 18, 2025):**
  - Created multiple analysis and planning documents: CLI coloring fix plan, high priority bugfix plan, model configuration updates.
  - Moved various Claude analysis documents to `docs/development/` for better organization.
  - Updated .gitignore with comprehensive development patterns for better workspace management.

- **Large Document Handling & Token Counting (July 2025):**
  - Implemented chunk-based processing in `digest` and `strategy` commands to handle large legal documents (split into 50k token chunks for LLM processing).
  - Integrated `tiktoken` for accurate token counting in research file analysis and input size management.
  - Brainstorm command now analyzes research file size, warns users for >128k tokens, and displays file/token/word stats.
  - All commands updated to use improved error handling and user feedback for large input files.

- **Verification & Model Upgrades (July 2025):**
  - Switched verification system to use Claude 4 Opus for higher accuracy and context window.
  - Broadened citation search scope and increased file size limits for extractfacts and lookup commands.
  - Two-phase citation verification and selective regeneration remain standard.

- **Prompt & Policy Refinements (July 2025):**
  - Major prompt YAML updates: barbrief.yaml, strategies.yaml, verification.yaml, caseplan.yaml, formats.yaml, glob_help_addon.yaml, lookup.yaml, system_feedback.yaml.
  - Enforced zero-emoji policy and standardized ASCII/ANSI output across all commands and documentation.
  - Improved code formatting and removed unused imports (e.g., verifying_message from strategy.py).
  - Enhanced error handling, logging, and user feedback throughout the CLI.

**Latest update (18 July 2025 - Infrastructure, Testing, and Documentation):**
- ADDED: GitHub Actions CI/CD pipeline and pre-commit hooks for automated testing.
- ADDED: Comprehensive architectural documentation and LaTeX article on LitAssist.
- ENHANCED: caseplan command now generates executable bash scripts from workflow plans.
- UPDATED: Python requirement to >=3.11, improved test infrastructure with tmp_path.
- EXPANDED: Documentation with analysis/planning docs moved to proper locations.
- IMPROVED: .gitignore with comprehensive development patterns.

**Previous update (8 July 2025 - Token Limit Configuration & Brainstorm Enhancement):**
- CHANGED: Default use_token_limits from False to True in config.py
- FIXED: Counselnotes empty output issue caused by low API default token limits
- UPDATED: All models now use 32K token limits when use_token_limits is enabled
- UPDATED: Documentation to reflect new default behavior
- INSIGHT: use_token_limits: false doesn't mean "no limits", it means "API defaults" (~4K)

## Next Steps

1. **[AG-124][P0] Implement circuit breaker for API retries**  
   - Add safety_cutoff parameter and logic  
   - TODO.md: "Implement circuit breaker for API retries"

2. **[EPIC-LLM][P1] Implement advanced LLM prompting improvements**  
   - IRAC/MIRAT, multi-model consensus, confidence scoring  
   - TODO.md: "Implement advanced LLM prompting improvements"

3. **[QA][P1] Create OpenRouter validation tests**  
   - TODO.md: "Develop manual validation scripts for OpenRouter"

4. **[UX][P1] Develop workflow commands**  
   - TODO.md: "Create compound workflow commands"

5. **[MON][P2] Implement performance benchmarking and monitoring**  
   - TODO.md: "Automate performance benchmarking and monitoring setup"

6. **[TECH][P2] Add --quality-tier flag and config**  
   - TODO.md: "Add cost-tracking system and quality-tier command options"

7. **[DEBT][P2] Refactor verify_with_level**  
   - TODO.md: "Refactor verify_with_level (Option B)"

8. **[MB][P2] Memory Bank Maintenance**  
   - Continue systematic updates after major changes

(AG- tags and priorities correspond to TODO.md and alignment plan.)

## Active Decisions & Considerations
- Strict adherence to Memory Bank hierarchy and .clinerules formatting rules.
- Use pipx as the default install method; config.yaml in ~/.config/litassist/ for global use.
- Emphasize two-phase citation verification (Jade.io primary, offline fallback) and selective regeneration for quality control.
- Clarify brainstorm vs strategy distinction: brainstorm = creative exploration, strategy = tactical implementation.
- Maintain clean CLI output, timestamped files, and professional summaries as standard UX.
- Enforce zero-emoji policy and standardized output in all code and documentation.

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
- Large document handling and token counting are now core to all major workflows.
- Prompt engineering and policy enforcement (e.g., zero-emoji) are critical for professional output and compliance.
