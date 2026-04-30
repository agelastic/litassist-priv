# LitAssist Development TODO

Last updated: 30/04/2026

**Note:** Strategic feature planning (litigation support, advisory capabilities, new commands) is now in [ROADMAP.md](ROADMAP.md). This file focuses on bugs, technical debt, and code quality improvements.

---

## Current State Summary

### Completed Features [DONE]
- All 11 core commands (lookup, digest, extractfacts, brainstorm, strategy, draft, verify, verify-cove, counselnotes, barbrief, caseplan)
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
  - All 407 unit tests passing
  - Comprehensive documentation updates across all user/dev docs
- **November 2025: Verification System Enhancements & Tooling**
  - Added --heavy flag to verify command for premium verification using gpt-5-pro
  - Added --noverify flag to extractfacts, draft, and strategy commands for skipping verification
  - Changed default verify-soundness from gpt-5-pro to claude-opus-4.1 (cost optimization)
  - Fixed verify_content_if_needed() to properly respect verify_flag parameter
  - Citation validation improvements with header analysis for PDF content
  - PDF search validation with automatic retry logic (up to 3 attempts)
  - Anti-injection prompt protection added for all LLM calls
  - Raw pre-verification output persistence for audit trail compliance
  - All 392 tests passing
- **November 2025: Token Limit System Removal**
  - Removed global token limit system (use_token_limits flag and automatic 16K output limits)
  - Increased input file size limits: brainstorm (50K→600K), caseplan (50K→600K), strategy (100K+100K→600K combined)
  - Clarified thinking_effort as reasoning budget (not output limit)
  - Quality prioritized over cost - models use API defaults for comprehensive outputs
  - Deprecation warnings added for old config files
  - All 390 tests passing

### Pending Tasks [IN PROGRESS]
- [x] ~~Fix lookup `--comprehensive` help/behavior mismatch~~ - Already correct (verified Oct 2025)
- [x] ~~Enable `openrouter.api_base` setting~~ - Not needed (OpenAI SDK v1.0+ architecture change)
- [ ] Implement circuit‑breaker (`safety_cutoff`) in retry logic [AG-124] - OPTIONAL enhancement (has 5-retry limit)
- [x] ~~Remove redundant top‑level `litassist.py` entry point~~ - COMPLETED (Oct 2025)
- [x] ~~Fail fast on config load errors~~ - Already implemented (verified Oct 2025)
- [ ] REMOVE temporary glob help addon after unification (delete glob_help_addon.yaml, remove concatenation logic)
- [ ] IMPLEMENT full glob unification (centralize expand_glob_patterns, update 5+ commands)
- [x] ~~Develop manual validation scripts for OpenRouter and extended RAG workflows (in test-scripts/)~~ - COMPLETED (test_integrations.py, test_quality.py, test_cli_comprehensive.sh exist)
- [ ] Enhance QA loops: iterative improvement, contingency planning, multi-perspective reviews
- [ ] Keep documentation current with new features as they are implemented
- [ ] Automate performance benchmarking and monitoring setup [MON]
- [ ] Implement OpenAI API fine-tuning per platform recommendations
- [ ] Add LLM response streaming functionality
- [ ] Expose model configuration parameters via CLI/env vars
- [ ] Develop "student mode" with newcomer-friendly explanations
- [x] ~~Add thinking trace logging system~~ - COMPLETED (LegalReasoningTrace class exists and used throughout)
- [x] ~~Integrate o3-pro coding standards~~ - COMPLETED (o3-pro model extensively integrated with proper parameter handling)
- [ ] Adopt Jules framework for test instrumentation (evaluate if still desired)
- [ ] **Refactor verify_with_level (Option B)**: Replace with boolean parameter `verify(content, comprehensive=False)` where comprehensive=True uses heavy verification prompt and comprehensive=False uses standard verification. This simplifies the API and removes the unused "light" level and redundant "medium" wrapper. NOTE: --heavy flag (Nov 2025) may already satisfy this need - evaluate if refactoring still needed. [DEBT]
- [ ] **Add optional reasoning trace file output**: Implement `--save-reasoning` flag for commands (strategy, draft, verify, etc.) to optionally save reasoning traces as separate files for auditing purposes. Currently reasoning traces are embedded in main output only. Implementation removed 2025-07-08 but may be useful for professional liability requirements.
- [ ] **Migrate off Google Custom Search JSON API by 01/01/2027**: Google has announced the JSON API is being retired in favour of Vertex AI Search (favourable alternative for <=50 domains) or the new full web search solution. LitAssist uses the JSON API in `litassist/citation/google_cse.py`, `litassist/commands/lookup/search.py`, `litassist/citation_context.py`, `litassist/cli.py` (startup ping), and two test-scripts. All three configured CSEs (Jade.io, AustLII, Comprehensive) are well under the 50-domain threshold and none use "Search the entire web", so the transition target is Vertex AI Search. Design sketch in `docs/development/GOOGLE_CSE_MIGRATION_PLAN.md`. No urgent action; deadline 01/01/2027.
- [x] ~~Document July 2025 upgrades in all user/dev/system docs~~ - COMPLETED

## Critical Bugs to Fix [HIGH PRIORITY]

### Code Quality Issues
- [x] ~~**Fix thread safety in progress indicator**: No error handling if progress thread fails. Add exception handling and timeout~~

### Performance & Reliability
_No critical bugs identified - all items below verified as already implemented or false alarms:_
- ~~Rate limiting~~ - Already exists (tenacity with exponential backoff)
- ~~Circuit breaker~~ - Has retry limits (5 attempts), full circuit breaker is nice-to-have but not critical
- ~~Bare exceptions~~ - All exceptions are properly typed and logged
- ~~o3-pro validation~~ - Validation exists via effort mapping
- ~~Large file handling~~ - MemoryError is caught and handled gracefully
- ~~Input validation~~ - Click validates file existence automatically at entry points

### Next Steps
1. Review and prioritize remaining TODO items for next sprint
2. Consider implementing circuit-breaker enhancement for API retries
3. Evaluate glob unification plan for implementation (also in ROADMAP.md P4-25)
4. Review ongoing prompt optimization opportunities (October 2025 model strategy implemented)
5. See ROADMAP.md for strategic feature implementation planning

## Future Plans

**Strategic Features:** See [ROADMAP.md](ROADMAP.md) for comprehensive feature planning (litigation support, advisory capabilities, matter management, FOI tools, etc.)

**Technical Documentation:**
- Historical LLM analysis in `docs/prompts/llm_enhancement_recommendations.md` (pre-October 2025, superseded by three-tier model strategy)
- Current model strategy in `docs/development/LLM_MODEL_STRATEGY.md`
- Testing approach in `docs/testing/test_README.md`

**Technical Enhancements:**
- Advanced QA loops: adversarial testing, iterative improvement loops, contingency planning
- Performance benchmarking and monitoring setup
- LLM response streaming functionality
- OpenAI API fine-tuning integration  

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
