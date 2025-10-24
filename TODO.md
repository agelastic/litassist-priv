# LitAssist Development TODO

## Current State Summary

### Completed Features [DONE]
- All 9 core commands (lookup, digest, extractfacts, brainstorm, strategy, draft, verify, counselnotes, barbrief)
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
- CounselNotes command for strategic advocate analysis (January 2025)
- Barbrief command for comprehensive barrister's briefs (January 2025)
- **October 2025: Major LLM Model Upgrade** - Implemented three-tier strategy
  - Tier 1: GPT-5 Pro for critical verification (<1% hallucination rate)
  - Tier 2: GPT-5 for fast verification (1.4% hallucination rate)
  - Tier 3: Claude Sonnet 4.5 for legal reasoning (state-of-the-art for litigation)
  - Upgraded 20+ commands with 40-50% cost reduction while improving quality
  - All 380 unit tests passing
  - Comprehensive documentation updates across all user/dev docs

### Pending Tasks [IN PROGRESS]
- [x] ~~Fix lookup `--comprehensive` help/behavior mismatch~~ - Already correct (verified Oct 2025)
- [x] ~~Enable `openrouter.api_base` setting~~ - Not needed (OpenAI SDK v1.0+ architecture change)
- [ ] Implement circuit‑breaker (`safety_cutoff`) in retry logic [AG-124] - OPTIONAL enhancement (has 5-retry limit)
- [x] ~~Remove redundant top‑level `litassist.py` entry point~~ - COMPLETED (Oct 2025)
- [x] ~~Fail fast on config load errors~~ - Already implemented (verified Oct 2025)
- [ ] REMOVE temporary glob help addon after unification (delete glob_help_addon.yaml, remove concatenation logic)
- [ ] IMPLEMENT full glob unification per claude_glob_unification_plan.md (centralize expand_glob_patterns, update 5+ commands)
- [ ] Implement advanced LLM prompting improvements from LLM_IMPROVEMENTS.md (IRAC/MIRAT, multi-model consensus, confidence scoring, adversarial testing) [EPIC-LLM]
- [ ] Develop manual validation scripts for OpenRouter and extended RAG workflows (in test-scripts/) [QA]
- [ ] Add cost-tracking system and quality-tier command options [TECH]
- [ ] Create compound workflow commands (e.g., `workflow initial-advice`) [UX]
- [ ] Enhance QA loops: iterative improvement, contingency planning, multi-perspective reviews
- [ ] Update user/developer documentation to reflect new features when implemented
- [ ] Automate performance benchmarking and monitoring setup [MON]
- [ ] Implement OpenAI API fine-tuning per platform recommendations
- [ ] Add LLM response streaming functionality
- [ ] Expose model configuration parameters via CLI/env vars
- [ ] Develop "student mode" with newcomer-friendly explanations
- [ ] Add thinking trace logging system
- [ ] Integrate o3-pro coding standards
- [ ] Adopt Jules framework for test instrumentation
- [ ] **Refactor verify_with_level (Option B)**: Replace with boolean parameter `verify(content, comprehensive=False)` where comprehensive=True uses heavy verification prompt and comprehensive=False uses standard verification. This simplifies the API and removes the unused "light" level and redundant "medium" wrapper. See plan details from 2025-07-07. [DEBT]
- [ ] **Add optional reasoning trace file output**: Implement `--save-reasoning` flag for commands (strategy, draft, verify, etc.) to optionally save reasoning traces as separate files for auditing purposes. Currently reasoning traces are embedded in main output only. Implementation removed 2025-07-08 but may be useful for professional liability requirements.
- [ ] **Implement circuit breaker for API retries**: Add safety_cutoff parameter to disable retries after N failures/hour (see AG-124)
- [ ] **Document July 2025 upgrades in all user/dev/system docs**: Large document chunking, tiktoken integration, verification model switch to Claude 4 Opus, prompt/policy refinements, zero-emoji policy, expanded test coverage, and file size warnings.

## Critical Bugs to Fix [HIGH PRIORITY]

### API & Network Issues
- [ ] **Add API call timeouts**: API calls in `api_handlers.py` can hang indefinitely. Add 30-second timeout parameter to `client.chat.completions.create()` calls (lines 278, 285)

### Code Quality Issues
- [ ] **Fix thread safety in progress indicator**: No error handling if progress thread fails. Add exception handling and timeout

### Performance & Reliability
_No critical bugs identified - all items below verified as already implemented or false alarms:_
- ~~Rate limiting~~ - Already exists (tenacity with exponential backoff)
- ~~Circuit breaker~~ - Has retry limits (5 attempts), full circuit breaker is nice-to-have but not critical
- ~~Bare exceptions~~ - All exceptions are properly typed and logged
- ~~o3-pro validation~~ - Validation exists via effort mapping
- ~~Large file handling~~ - MemoryError is caught and handled gracefully
- ~~Input validation~~ - Click validates file existence automatically at entry points

### Next Steps
1. Commit `memory-bank/` directory and its files
2. Merge initial Memory Bank into main branch
3. Schedule sprint to implement high-impact prompt and verification enhancements
4. Enhance manual API validation scripts per updated testing approach
5. Plan cost-tracking and workflow command prototypes
6. Review and prioritize new TODO items for implementation

## Future Plans
- See detailed LLM improvements in `docs/development/LLM_IMPROVEMENTS.md`  
- Integration test strategy in `docs/development/integration_testing_approach.md`  
- Cost-tracking and quality-tier features (planning in progress)  
- Compound workflow commands prototypes (e.g., `workflow initial-advice`)  
- Advanced QA loops: adversarial testing, iterative improvement loops, contingency planning  
- Performance benchmarking and monitoring setup  

## Implementation Concerns & Considerations

### Key Architectural Implementation Points
1. **OpenAI Fine-tuning Integration**: Review `litassist/llm.py` integration points, extend LLMClient factory pattern to support fine-tuned model endpoints
2. **Streaming Implementation**: Update CLI output handlers in `litassist/cli.py`, modify response processing in command modules (`litassist/commands/`), add progress indicators
3. **Student Mode**: Leverage existing prompt templates in `litassist/prompts/`, extend base.yaml and system_feedback.yaml with beginner-friendly variants
4. **Model Configuration**: Extend `litassist/config.py` with new environment variable mappings, update `config.yaml.template` with streaming/model options
5. **Thinking Traces**: Add new logging handlers in `litassist/utils.py`, extend output directory structure for trace files
6. **o3-pro Standards**: Review existing code patterns in `litassist/commands/` modules, update linting rules in `setup.py` and `requirements-ci.txt`
7. **Jules Framework**: Integrate with existing test infrastructure in `tests/unit/`, update `test-scripts/` directory structure
8. **Config Exposure**: Add CLI arguments in `litassist/cli.py`, extend configuration validation in `litassist/config.py`

### Technical Architecture Concerns
- **Jules Framework Integration**: Need to research Jules framework documentation and compatibility with existing test infrastructure
- **o3-pro Standards**: Requires clarification on specific coding standards and how they integrate with current Python/legal domain patterns
- **Model Config Exposure**: Risk of breaking existing config.yaml structure; need backward compatibility strategy
- **Fine-tuning Implementation**: Requires OpenAI API credits, training data preparation, and evaluation metrics - significant cost implications
- **Streaming Architecture**: Major refactor needed for CLI output handling, progress indicators, and error handling during streaming
- **Student Mode Design**: Risk of prompt bloat; need clear separation between expert and beginner explanations
- **Thinking Traces**: Potential performance impact on response times; need configurable verbosity levels

### Integration Risks  
- New features may conflict with existing zero-tolerance citation enforcement
- Streaming could interfere with current output timestamping and file organization
- Model config changes might break OpenRouter integration
- Student mode explanations could dilute legal accuracy requirements

### Resource & Timeline Concerns
- Fine-tuning requires significant API budget and data preparation time
- Jules framework adoption may require team training
- Multiple concurrent LLM architecture changes increase testing complexity
- Student mode requires extensive legal domain expertise for accurate simplification

## Notes
- Prioritize minimal whitespace changes to maintain clean diffs
- Reference Memory Bank for all session context and planning
- Consider implementing features incrementally with feature flags to minimize integration risk
- Establish clear success criteria and rollback plans for each major change
