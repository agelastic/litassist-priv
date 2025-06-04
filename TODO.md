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
- Fixed extractfacts duplicate headings for multi-chunk documents
- File size validation to prevent token limit issues
- Enhanced draft command to handle large text files via RAG

### Recent Fixes
- Extractfacts: Fixed duplicate headings for multi-chunk documents
- Brainstorm/Strategy: Added file size validation (50k/100k char limits)
- Config: Fixed global configuration path resolution
- Draft: Routes large text files through embedding/retrieval

## Features Discussed but Not Implemented

### 1. Enhanced Legal Reasoning (High Priority)
- [ ] IRAC/MIRAT framework enforcement
- [ ] Legal reasoning traces showing premise → application → conclusion
- [ ] Multi-model consensus for critical tasks
- [ ] Iterative improvement loops
- [ ] Confidence scoring on all outputs

### 2. Advanced Citation Intelligence
- [ ] Case hierarchy awareness (HC > FCA > State)
- [ ] Temporal relevance scoring
- [ ] Overruled/distinguished case detection
- [ ] Automatic citation validation against AustLII
- [ ] Flag suspicious citations (e.g., "Smith v Jones")

### 3. Probability Methodology Enhancement
- [ ] Structured probability calculations with base rates
- [ ] Decision tree analysis
- [ ] Risk factor quantification
- [ ] Confidence intervals on predictions
- [ ] Show calculation methodology transparently

### 4. Multi-Stage Document Refinement
- [ ] Draft → Review → Polish workflow
- [ ] Peer review simulation
- [ ] Counter-argument generation
- [ ] Adversarial testing built into brainstorm
- [ ] Iterative improvement with targeted questions

### 5. Quality Assurance Features
- [ ] Automated testing of actual LLM outputs
- [ ] Quality metrics tracking
- [ ] Cost vs quality trade-off options
- [ ] Performance benchmarking system
- [ ] Output quality scoring

## Cleanup Needed

### Code Organization
- [ ] Extract long functions in strategy.py (multi-stage generation)
- [ ] Move prompt templates to separate files
- [ ] Centralize duplicate chunking logic
- [ ] Create shared validation functions

### Error Handling
- [ ] Standardize error messages across commands
- [ ] Make API errors more user-friendly
- [ ] Better handling of partial failures (e.g., one chunk fails)
- [ ] Add retry logic for transient failures

### Testing
- [ ] Add integration tests for actual LLM calls
- [ ] Expand mock test coverage for edge cases
- [ ] Create tests for multi-chunk document handling
- [ ] Add performance benchmarks

### Documentation
- [ ] Expand CLAUDE.md testing section
- [ ] Verify all example files exist
- [ ] Document API costs per command
- [ ] Add troubleshooting guide
- [ ] Create video tutorials

## Recommended New Features

### 1. Priority: Legal Reasoning Traces
Add structured reasoning to all analytical commands:
```python
reasoning_template = """
Legal Issue: {issue}
Applicable Law: {law} 
Application to Facts: {application}
Conclusion: {conclusion}
Confidence: {confidence}%
"""
```

### 2. Citation Verification Service
- [ ] Verify case names against AustLII API
- [ ] Check year ranges for plausibility
- [ ] Build local cache of common citations
- [ ] Flag placeholder citations

### 3. Cost Tracking System
- [ ] Calculate cost per API call
- [ ] Add cost totals to logs
- [ ] Monthly cost reports
- [ ] Cost optimization suggestions
- [ ] Budget alerts

### 4. Workflow Commands
Create compound commands for common workflows:
- [ ] `litassist workflow initial-advice case.pdf`
- [ ] `litassist workflow discovery-response documents/`
- [ ] `litassist workflow settlement-position`
- [ ] `litassist workflow appeal-prospects`

### 5. Quality Tier System
Let users choose quality/cost trade-offs:
- [ ] `--quality fast` (single pass, no verification)
- [ ] `--quality balanced` (default)
- [ ] `--quality high` (multi-pass, full verification)
- [ ] `--quality max` (multi-model consensus)

### 6. Precedent Library
- [ ] Local database of commonly cited cases
- [ ] Cache case summaries from AustLII
- [ ] Offline citation checking
- [ ] Reduce API calls for common queries
- [ ] Auto-update important cases

### 7. Smart Document Detection
- [ ] Auto-detect document types (affidavit, submission, letter)
- [ ] Apply appropriate templates automatically
- [ ] Suggest relevant workflows based on content
- [ ] Warn about missing required sections

### 8. Advanced Features
- [ ] Email integration for client communications
- [ ] Court deadline calculator
- [ ] Conflict checking against matter database
- [ ] Time tracking integration
- [ ] Billing code suggestions

## Implementation Priority

### Immediate (1 day)
- [ ] Add cost tracking to all commands
- [ ] Fix any remaining test files in .gitignore
- [ ] Verify all example files exist
- [ ] Update README with current feature set

### Short-term (1 week)
- [ ] Implement legal reasoning traces
- [ ] Add basic citation verification
- [ ] Create first workflow command
- [ ] Standardize error messages

### Medium-term (2-4 weeks)
- [ ] Extract prompts to template files
- [ ] Implement quality tier system
- [ ] Add precedent caching
- [ ] Build integration test suite

### Long-term (1-2 months)
- [ ] Multi-model consensus for critical tasks
- [ ] Full adversarial testing system
- [ ] Performance benchmarking
- [ ] Workflow automation suite

## Technical Debt

### Refactoring Needs
- [ ] Split large command files into smaller modules
- [ ] Create abstract base class for commands
- [ ] Implement proper dependency injection
- [ ] Add type hints throughout

### Performance Optimization
- [ ] Implement concurrent chunk processing
- [ ] Add caching layer for embeddings
- [ ] Optimize Pinecone queries
- [ ] Reduce redundant API calls

### Security Enhancements
- [ ] Add API key encryption at rest
- [ ] Implement audit logging for compliance
- [ ] Add user access controls
- [ ] Secure document handling

## Future Vision

### LitAssist 2.0
- Real-time collaboration features
- Web interface alongside CLI
- Integration with practice management systems
- Mobile app for court appearances
- Voice input for dictation

### AI Enhancements
- Fine-tuned models for Australian law
- Automatic legal research agents
- Predictive case outcome modeling
- Natural language legal queries

### Practice Integration
- Direct filing with court systems
- Integration with legal databases
- Automatic time recording
- Client portal integration

## Notes

- Always maintain Australian legal focus
- Prioritize accuracy over features
- Keep backward compatibility
- Document all breaking changes
- Consider solo practitioners' needs

## Contributing Guidelines

When implementing features:
1. Always add tests
2. Update relevant documentation
3. Consider API costs
4. Maintain consistent style
5. Add examples for new features

---
Last Updated: 2024-05-24