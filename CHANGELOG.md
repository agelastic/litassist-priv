# Changelog

Last updated: 22/05/2026

All notable changes to LitAssist will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive citation verification system with real-time Jade.io validation
- Reasoning trace capture across all commands for accountability
- Heartbeat progress indicators for long-running operations
- Advanced reasoning models support (o3-pro) for strategic analysis
- Barrister's brief generation command (barbrief)
- Counsel notes strategic analysis command
- Case plan generation for litigation planning

### Changed

#### November 2025: Token Limit System Removal
- Removed the global token limit system (use_token_limits flag and automatic 16K output limits)
- Increased input file size limits: brainstorm (50K to 600K), caseplan (50K to 600K), strategy (100K+100K to 600K combined)
- Clarified thinking_effort as a reasoning budget rather than an output limit
- Quality prioritised over cost: models use API defaults for comprehensive outputs
- Deprecation warnings added for old config files
- All 390 tests passing

#### November 2025: Verification System Enhancements & Tooling
- Added `--heavy` flag to the verify command for premium verification using gpt-5-pro
- Added `--noverify` flag to extractfacts, draft, and strategy commands for skipping verification
- Changed default verify-soundness model from gpt-5-pro to claude-opus-4.1 (cost optimisation)
- Fixed `verify_content_if_needed()` to properly respect the verify_flag parameter
- Citation validation improvements with header analysis for PDF content
- PDF search validation with automatic retry logic (up to 3 attempts)
- Anti-injection prompt protection added for all LLM calls
- Raw pre-verification output persistence for audit trail compliance
- All 392 tests passing

#### October 2025: Major Model Upgrade - Three-Tier Strategy Implementation
- **Implemented three-tier model strategy** for optimal accuracy and cost-efficiency:
  - Tier 1: GPT-5 Pro for critical verification (<1% hallucination rate)
  - Tier 2: GPT-5.1 for fast verification (1.4% hallucination rate)
  - Tier 3: Claude Sonnet 4.5 for legal reasoning (state-of-the-art for litigation)
- **Upgraded 20+ commands** to new models based on June-October 2025 releases:
  - Claude Opus 4.1 → Claude Sonnet 4.5 (14 commands, 80% cost reduction)
  - Claude Sonnet 4 → Claude Sonnet 4.5 (6 commands, improved reasoning)
  - New GPT-5 Pro implementation (3 critical verification commands)
  - New GPT-5.1 implementation (2 standard verification commands)
  - Grok 3 → Grok 4 (unorthodox brainstorming upgrade)
- **Expected impact**: 40-50% overall cost reduction while improving quality
- **Key improvements**:
  - Superior legal reasoning: "state of the art on complex litigation tasks"
  - Enhanced accuracy: <1.6% hallucination rate on all verification
  - Extended thinking mode for complex multi-step analysis
  - Preserved old configurations as comments for rollback capability
- All 407 unit tests passing with updated model configurations
- Comprehensive documentation updates across README, user guide, and dev docs

#### Previous Changes
- Removed pattern-based citation validation in favor of online verification only
- Improved verification system with increased token limits
- Standardized CLI flags to use --context across all commands
- Enhanced prompt template system with centralized YAML management

### Fixed
- Citation verification no longer flags valid NSW tribunal citations
- Brainstorm command streaming API errors resolved
- Barbrief command progress indicator issues fixed
- Verification system now preserves full document content

### Security
- No security vulnerabilities reported

## [1.0.0] - 2025-01-23

### Added
- Initial release of LitAssist
- Core commands: lookup, digest, brainstorm, extractfacts, strategy, draft, verify
- Australian legal citation support
- Integration with multiple LLM providers (OpenAI, Anthropic, Google, xAI)
- Comprehensive prompt template system
- Document chunking and processing capabilities
- Strategic litigation planning features

### Notes
This is the first stable release of LitAssist, providing AI-powered litigation support specifically designed for Australian legal practitioners.