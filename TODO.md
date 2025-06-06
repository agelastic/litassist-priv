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

### Recent Major Implementations ✅ (Since May 2024)

#### Citation Verification & Quality Control
- ✅ **Comprehensive Citation Verification**: Real-time AustLII validation for all legal references
- ✅ **Online Citation Validation**: HEAD requests to verify case existence during generation  
- ✅ **Enhanced Error Messages**: Specific failure types (e.g., "GENERIC CASE NAME", "FUTURE CITATION") with clear actions
- ✅ **Selective Regeneration**: "Option B" implementation - only regenerates content with citation issues
- ✅ **Zero-tolerance Enforcement**: Blocks unverified citations in strategy-generating commands
- ✅ **Citation Pattern Detection**: Flags suspicious patterns, generic names, future dates

#### Legal Reasoning Traces & Analysis
- ✅ **Reasoning Trace Structure**: Created LegalReasoningTrace class and extraction functions
- [ ] **Reasoning Trace Integration**: NOT fully integrated across all commands (only partially in some)
- [ ] **Reasoning Trace Storage**: `*_reasoning.txt` files planned but not consistently implemented
- ✅ **Multi-Model Analysis**: Claude 3.5 Sonnet IS used for strategy ranking
- ✅ **Consistent Analysis Standards**: Same criteria for "most likely to succeed" across brainstorm and strategy

#### Intelligent Strategy Integration  
- ✅ **Strategy Command Enhancement**: Builds directly on brainstormed strategies as foundations
- ✅ **Intelligent Strategy Prioritization**: Claude 3.5 Sonnet ranks strategies for specific outcomes
- ✅ **Efficiency-First Approach**: Avoids duplicate analysis when "most likely" strategies available
- ✅ **Smart Gap-Filling**: Intelligent analysis only for remaining slots when insufficient pre-analyzed strategies
- ✅ **Duplicate Strategy Prevention**: Deduplicates strategies by title across all sections

#### Verification & Quality Systems
- ✅ **Automatic Verification**: Mandatory for extractfacts and strategy commands
- ✅ **Smart Auto-Verification**: Triggered for brainstorm (Grok models) and draft (citations detected)
- ✅ **Verification Status Messaging**: Clear user feedback for all verification scenarios
- ✅ **Enhanced Verification Depth**: Heavy verification for foundational documents

#### Command Enhancements
- ✅ **Lookup Extract Options**: `--extract citations|principles|checklist` for workflow efficiency
- ✅ **Strategy Output Organization**: Main strategy file + separate reasoning traces
- ✅ **Individual Option Generation**: Quality-over-quantity approach for strategy command
- ✅ **Enhanced User Feedback**: Clear progress indicators and reasoning explanations

### Recent Fixes
- Extractfacts: Fixed duplicate headings for multi-chunk documents
- Brainstorm/Strategy: Added file size validation (50k/100k char limits)  
- Config: Fixed global configuration path resolution
- Draft: Routes large text files through embedding/retrieval
- Strategy: Fixed UnboundLocalError with target_options variable scope
- Strategy: Fixed duplicate strategy selection across most_likely and orthodox sections

## Features Discussed but Not Implemented

### 1. Enhanced Legal Reasoning (Partially Implemented)
- [ ] IRAC/MIRAT framework enforcement (only mentioned in lookup mode, not enforced)
- ✅ **Legal reasoning traces**: Basic structure exists in utils.py but not fully integrated
- ✅ **Multi-model analysis**: Claude 3.5 Sonnet IS used for strategy ranking
- [ ] Iterative improvement loops
- [ ] Confidence scoring on all outputs (structure exists but not populated)

### 2. Advanced Citation Intelligence (Largely Implemented)
- [ ] Case hierarchy awareness (HC > FCA > State)
- [ ] Temporal relevance scoring
- [ ] Overruled/distinguished case detection
- ✅ **Automatic citation validation against AustLII**: Real-time HEAD requests implemented
- ✅ **Flag suspicious citations**: Generic names, future dates, impossible citations detected

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

### 1. Legal Reasoning Traces (Structure Created, Not Fully Implemented)
⚠️ **PARTIAL**: Structure exists but not integrated across all commands:
```python
# Structure defined in utils.py but not consistently used:
Legal Issue: {issue}
Applicable Law: {law} 
Application to Facts: {application}
Conclusion: {conclusion}
Confidence: {confidence}%  # Field exists but not populated
Sources: {sources}
```

### 2. Citation Verification Service (Implemented)
- ✅ **Verify case names against AustLII API**: Real-time verification implemented
- ✅ **Check year ranges for plausibility**: Future date detection and court establishment validation
- ✅ **Flag placeholder citations**: Generic name detection (Smith v Jones, etc.)
- [ ] Build local cache of common citations

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
- ⚠️ **Implement legal reasoning traces**: Structure created but not integrated
- ✅ **Add citation verification**: COMPLETED (comprehensive AustLII implementation)
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

## Recent Development Highlights

### Major Quality Improvements (December 2024)
The recent implementation cycle focused heavily on **quality control and efficiency**:

1. **Citation Verification Revolution**: From basic validation to comprehensive AustLII integration with real-time verification
2. **Strategy Integration**: Transformed brainstorm → strategy from independent commands to intelligent pipeline
3. **Quality over Quantity**: "Option B" implementation prioritizes correct information over fixed quantities
4. **Analysis Efficiency**: Smart duplicate detection prevents wasted analysis while maintaining quality
5. **User Experience**: Enhanced feedback shows exactly what's happening and why

### Technical Debt Reduction
- Fixed variable scope bugs in strategy command
- Implemented proper deduplication logic
- Enhanced error messaging with specific failure types
- Unified analysis standards across commands using Claude 3.5 Sonnet

### Next Priority Items
Given the substantial progress on citation verification and legal reasoning:

**Immediate Focus (Next 1-2 weeks)**:
1. **Cost tracking system** - Now that quality is solid, optimize costs
2. **Workflow commands** - Build on the solid foundation
3. **Performance optimization** - Reduce redundant API calls further

**Upcoming Priorities**:
1. Quality tier system (fast/balanced/high/max)
2. Precedent caching to reduce costs
3. First compound workflow command

---
Last Updated: 2024-12-06