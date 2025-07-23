# Changelog

All notable changes to LitAssist will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive citation verification system with real-time Jade.io validation
- Legal reasoning trace capture across all commands for accountability
- Heartbeat progress indicators for long-running operations
- Advanced reasoning models support (o3-pro) for strategic analysis
- Barrister's brief generation command (barbrief)
- Counsel notes strategic analysis command
- Case plan generation for litigation planning

### Changed
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