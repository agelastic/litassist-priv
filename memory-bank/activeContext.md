# Active Context

## Current Work Focus
Maintaining the Memory Bank as the authoritative, up-to-date reference for LitAssist’s architecture, workflows, and development state. Incorporating all June 2025 improvements, workflow clarifications, and best practices from the latest documentation.

## Recent Changes
- Implemented major June 2025 improvements:
  - Lookup command overhaul: Jade.io-only, new --comprehensive flag, improved extract options, citation integration, code quality/linting
  - Multi-section reasoning traces for brainstorm; enhanced strategy integration
  - Complete timing coverage and comprehensive logging for all operations
  - Centralized configuration and log format in config.yaml
  - Clean CLI output and professional summaries
  - Output file timestamping and organization in outputs/ and logs/
  - Model selection and BYOK requirements for advanced commands
  - Two-phase citation verification and selective regeneration (“Option B”)
- Updated Memory Bank files for consistency with README, User Guide, and config.yaml.template
- Full Memory Bank review performed on 15 June 2025: all files confirmed up to date and synchronized with codebase and documentation. No changes required.

## Next Steps
1. Continue to update Memory Bank after each major feature, bugfix, or workflow change.
2. Track progress on advanced features (IRAC/MIRAT enforcement, multi-model consensus, QA loops, cost-tracking, compound commands).
3. Ensure all new patterns, troubleshooting, and best practices are reflected in systemPatterns.md and techContext.md.
4. Periodically review Memory Bank for alignment with evolving documentation and codebase.

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
