# LitAssist Development TODO

## Current State Summary

### Completed Features ✅
- All 6 core commands (lookup, digest, extractfacts, brainstorm, strategy, draft)
- Global installation via pipx
- Single configuration approach
- Outputs organized in `outputs/` directory
- Comprehensive documentation suite
- Australian legal focus throughout
- Timestamped outputs preventing data loss
- Multi-level verification system
- Zero-tolerance citation enforcement
- Clean CLI summaries instead of content dumps
- Comprehensive logging and timing instrumentation
- Fixed all ruff linting errors and removed unused dependencies
- Memory Bank initialized with core context, patterns, architecture, and technical setup

### Pending Tasks ⌛
- Implement advanced LLM prompting improvements from LLM_IMPROVEMENTS.md (IRAC/MIRAT, multi-model consensus, confidence scoring, adversarial testing)
- Develop integration tests for OpenRouter and extended RAG workflows
- Add cost-tracking system and quality-tier command options
- Create compound workflow commands (e.g., `workflow initial-advice`)
- Enhance QA loops: iterative improvement, contingency planning, multi-perspective reviews
- Update user/developer documentation to reflect new features when implemented
- Automate performance benchmarking and monitoring setup

### Next Steps 🚀
1. Commit `memory-bank/` directory and its files
2. Merge initial Memory Bank into main branch
3. Schedule sprint to implement high-impact prompt and verification enhancements
4. Begin development of integration testing suite per integration_testing_approach.md
5. Plan cost-tracking and workflow command prototypes

## Future Plans 📅
- See detailed LLM improvements in `docs/development/LLM_IMPROVEMENTS.md`  
- Integration test strategy in `docs/development/integration_testing_approach.md`  
- Cost-tracking and quality-tier features (planning in progress)  
- Compound workflow commands prototypes (e.g., `workflow initial-advice`)  
- Advanced QA loops: adversarial testing, iterative improvement loops, contingency planning  
- Performance benchmarking and monitoring setup  

## Notes
- Prioritize minimal whitespace changes to maintain clean diffs
- Reference Memory Bank for all session context and planning
