# Comprehensive Case Document Generation Plan

This plan generates 50+ documents for the Osipov v Wong vehicle ownership dispute, maximizing coverage for downstream strategy analysis.

## Important: Updated Command Syntax (as of July 2025)
The `brainstorm` and `barbrief` commands have been updated:
- **NEW**: Brainstorm uses `--facts` option instead of positional argument
- **NEW**: Both commands support glob patterns for all file options
- **NEW**: Brainstorm automatically uses `case_facts.txt` if present in current directory
- **NEW**: Barbrief supports glob patterns for `--strategies`, `--research`, and `--documents`
- **CHANGE**: Quote glob patterns to prevent shell expansion: `'outputs/lookup_*.txt'`
- **FIXED**: Token limits now default to True (enabling 32K tokens for most models)
- **FIXED**: Default chunk size increased to 200K characters (~50K tokens)

## PHASE 1: BRAINSTORMING (generates orthodox & unorthodox strategies automatically)
```bash
# If case_facts.txt exists in current directory
litassist brainstorm --side plaintiff --area civil

# Or explicitly specify the facts file
litassist brainstorm --facts case_facts.txt --side plaintiff --area civil
```

## PHASE 2: EXTRACT FACTS FROM SOURCE DOCUMENTS
Extract structured facts from all PDF documents in the case bundle with a single command:

**[WARNING] IMPORTANT FILE SIZE LIMIT**: Each file must be under 1MB (1,000,000 characters). Large files like WhatsApp chat logs should be processed with `digest` instead.

```bash
# Process PDFs and case_facts together (if under 1MB each)
litassist extractfacts case_facts.txt *.pdf

# For large files like WhatsApp logs, use digest separately
litassist digest whatsapp_chat_log.txt --mode summary --hint "gift intent ownership discussions money transfers bank cheque payment December 2021"
```

### Recommended Approach for Mixed Document Types:
```bash
# Step 1: Extract facts from structured documents
litassist extractfacts case_facts.txt car_bundle.pdf suncorp_bundle.pdf

# Step 2: Digest large/conversational files separately  
litassist digest whatsapp_chat_log.txt --mode issues --hint "no gift mentioned payment arrangement driver licence Wong name registration"

# Step 3: Manually incorporate key findings from digest into case_facts.txt if needed
```

Note: extractfacts creates structured 10-heading output ideal for legal commands, while digest handles large unstructured content better.

## PHASE 3: EXTENSIVE CASE LAW RESEARCH (15+ research files)

### Gift elements research
```bash
litassist lookup "gift valid elements delivery acceptance donative intent motor vehicle bank cheque payment third party" --mode irac --comprehensive
litassist lookup "incomplete gift presumed resulting trust vehicle registration ownership" --mode irac --comprehensive
litassist lookup "gift delivery keys retention donor incomplete gift motor vehicle" --mode irac
```

### Presumption of advancement research  
```bash
litassist lookup "presumption advancement de facto relationship same-sex couples property Property (Relationships) Act ACT" --mode irac --comprehensive
litassist lookup "presumption advancement rebuttal evidence contrary intention bank cheque payment evidence rebuttal gift presumption" --mode irac --comprehensive
litassist lookup "matrimonial cause de facto property settlement time limits ACT Property (Relationships) Act" --mode irac --comprehensive
```

### Alternative claims research
```bash
litassist lookup "detinue motor vehicle possession wrongful detention ACT law owner lacks driver licence registration third party name" --mode irac --comprehensive
litassist lookup "conversion trespass goods motor vehicle damages ACT" --mode irac --comprehensive
litassist lookup "constructive trust unjust enrichment vehicle purchase" --mode irac --comprehensive
litassist lookup "resulting trust purchase money motor vehicle registration" --mode irac --comprehensive
```

### Equitable defences research
```bash
litassist lookup "laches acquiescence delay family violence order restraining order excuse civil proceedings delay excuse" --mode irac --comprehensive
litassist lookup "estoppel representation ownership motor vehicle conduct" --mode irac
```

### Procedural research
```bash
litassist lookup "ACT Magistrates Court civil jurisdiction equitable remedies sections 257 258" --mode irac
litassist lookup "service process family violence order legal practitioner exemption ACT" --mode irac
```

### Payment and ownership evidence research
```bash
litassist lookup "bank cheque payment third party ownership evidence motor vehicle" --mode irac --comprehensive
litassist lookup "family violence order civil proceedings ACT contact restrictions service" --mode irac --comprehensive
litassist lookup "vehicle registration owner lacks licence third party arrangement" --mode irac
```

### Extract specific information
```bash
litassist lookup "gift motor vehicle de facto relationship ACT cases" --extract citations
litassist lookup "presumption advancement same-sex relationships" --extract principles
```

## PHASE 4: DIGEST DOCUMENTS (create summaries and issue spotting)
```bash
# Process all PDFs and text files in the directory
litassist digest *.pdf whatsapp_chat.txt --mode summary
litassist digest *.pdf whatsapp_chat.txt --mode issues --hint "ownership gift presumption advancement bank cheque Osipov payment Wong registration"

# Or process specific files
litassist digest car_bundle.pdf suncorp_bundle.pdf whatsapp_chat.txt --mode summary
```
Note: digest now accepts multiple files and creates a consolidated digest with clear source attribution for each document.

## PHASE 5: RESEARCH-INFORMED BRAINSTORMING (with lookup results)
After completing extensive case law research, run brainstorm again with research context:

### [RECOMMENDED] for Osipov v Wong case:
```bash
# Use selective research themes focusing on core legal theories with glob patterns
litassist brainstorm --side plaintiff --area civil --research 'outputs/lookup_*gift*.txt' --research 'outputs/lookup_*presumption*.txt' --research 'outputs/lookup_*constructive*.txt'

# Or if you need to specify facts file explicitly
litassist brainstorm --facts case_facts.txt --side plaintiff --area civil --research 'outputs/lookup_*gift*.txt' --research 'outputs/lookup_*presumption*.txt' --research 'outputs/lookup_*constructive*.txt'
```

**Why this approach is best:**
- Focuses on the three core legal theories: gift elements, presumption of advancement, and constructive trust
- Avoids information overload from procedural/peripheral research
- Keeps strategies targeted on strongest arguments
- Prevents token limit issues

### Alternative approaches (less recommended):
```bash
# Option 2: Use ALL research with glob pattern (may be too broad)
litassist brainstorm --side plaintiff --area civil --research 'outputs/lookup_*.txt'

# Option 3: Use multiple facts files with selective research
litassist brainstorm --facts 'outputs/extractfacts_*.txt' --side plaintiff --area civil --research 'outputs/lookup_*gift*.txt' --research 'outputs/lookup_*presumption*.txt' --research 'outputs/lookup_*constructive*.txt'

# Option 4: Mix specific and glob patterns
litassist brainstorm --facts case_facts.txt --facts extracted_facts.txt --side plaintiff --area civil --research specific_research.txt --research 'outputs/lookup_*trust*.txt'
```

Note: The --research flag enriches orthodox strategies with case law precedents while maintaining creative unorthodox strategies. This creates a second brainstorm output that combines early creativity with later research insights.

## PHASE 6: COUNSEL NOTES (from multiple sources)
Wait for brainstorm output files (both early and research-informed), then:
```bash
# Basic version with original case facts
litassist counselnotes outputs/brainstorm_*.txt case_facts.txt

# With extracted facts from PDFs
litassist counselnotes outputs/brainstorm_*.txt outputs/extractfacts_*.txt

# With research files
litassist counselnotes outputs/brainstorm_*.txt outputs/lookup_*.txt --extract all

# Comprehensive version with all sources
litassist counselnotes outputs/brainstorm_*.txt outputs/lookup_*.txt outputs/digest_*.txt outputs/extractfacts_*.txt --extract principles --verify
```

## PHASE 7: BAR BRIEFS (multiple versions with research)
Note: Can use either early brainstorm or research-informed brainstorm strategies, or both:

### Basic version
```bash
litassist barbrief case_facts.txt --strategies 'outputs/brainstorm_*.txt' --hearing-type trial
```

### With research files
```bash
litassist barbrief case_facts.txt --strategies 'outputs/brainstorm_*.txt' --research 'outputs/lookup_*gift*.txt' --research 'outputs/lookup_*presumption*.txt' --hearing-type trial
```

### Comprehensive version
```bash
litassist barbrief case_facts.txt --strategies 'outputs/brainstorm_*.txt' --research 'outputs/lookup_*.txt' --documents '*.pdf' --instructions "Focus on rebutting presumption of advancement and establishing incomplete gift" --hearing-type trial --verify
```

## PHASE 8: STRATEGY ANALYSES

**IMPORTANT: Why use brainstormed strategies?**
The strategy command intelligently uses brainstormed strategies as foundations for generating concrete strategic options. When provided:
- It extracts "MOST LIKELY TO SUCCEED" strategies first
- Ranks remaining strategies using LLM analysis
- Transforms creative legal theories into actionable plans
- Ensures consistency from ideation through implementation

**Note**: Strategy command accepts only ONE strategies file at a time. Use different brainstorm outputs for different strategic approaches.

### Strategy 1: Use early brainstorm (creative approaches)
```bash
# Replace [timestamp] with actual timestamp from your early brainstorm file
litassist strategy case_facts.txt --outcome "Recover vehicle purchase price of $40,364 from Marcus Wong" --strategies outputs/brainstorm_plaintiff_civil_[timestamp].txt
```

### Strategy 2: Use research-informed brainstorm (precedent-backed approaches)
```bash
# Replace [timestamp] with actual timestamp from your research-informed brainstorm file
litassist strategy case_facts.txt --outcome "Establish resulting trust over vehicle" --strategies outputs/brainstorm_plaintiff_civil_[timestamp].txt
```

### Strategy 3: Fresh generation for alternative perspectives
```bash
# Generate without strategies to get fresh perspectives
litassist strategy case_facts.txt --outcome "Obtain order for return of vehicle or damages"
```

### Strategy 4: Target specific legal theories with appropriate brainstorm
```bash
# Use early brainstorm for presumption of advancement strategy
litassist strategy case_facts.txt --outcome "Rebut presumption of advancement and prove incomplete gift" --strategies outputs/brainstorm_plaintiff_civil_[timestamp].txt

# Use research-informed brainstorm for constructive trust strategy
litassist strategy case_facts.txt --outcome "Establish constructive trust based on unjust enrichment" --strategies outputs/brainstorm_plaintiff_civil_[timestamp].txt
```

### Additional strategic variations
```bash
# Defensive strategy using early brainstorm
litassist strategy case_facts.txt --outcome "Defeat any counterclaim for assault damages" --strategies outputs/brainstorm_plaintiff_civil_[timestamp].txt

# Settlement strategy using research-informed brainstorm
litassist strategy case_facts.txt --outcome "Achieve favorable settlement preserving plaintiff's financial position" --strategies outputs/brainstorm_plaintiff_civil_[timestamp].txt

# FVO/timing defense strategy
litassist strategy case_facts.txt --outcome "Overcome laches defense using FVO restrictions as excuse for delay" --strategies outputs/brainstorm_plaintiff_civil_[timestamp].txt

# Payment evidence strategy
litassist strategy case_facts.txt --outcome "Prove ownership through bank cheque payment trail despite registration in Wong's name" --strategies outputs/brainstorm_plaintiff_civil_[timestamp].txt

# Practical enforcement strategy
litassist strategy case_facts.txt --outcome "Force Wong to sell vehicle and remit proceeds through court order" --strategies outputs/brainstorm_plaintiff_civil_[timestamp].txt
```

## PHASE 9: DRAFT DOCUMENTS

### Draft various documents using RAG
```bash
litassist draft case_facts.txt outputs/strategy_*.txt "Draft originating application for ACT Magistrates Court seeking declaration of ownership and damages for detinue" --verify

litassist draft case_facts.txt outputs/barbrief_*.txt "Draft comprehensive legal submissions on incomplete gift and presumption of advancement" --verify

litassist draft case_facts.txt outputs/counselnotes_*.txt "Draft witness statement for Vitaly Osipov covering all aspects of vehicle purchase" --verify

litassist draft case_facts.txt outputs/strategy_*.txt outputs/lookup_*.txt "Draft memorandum of advice on prospects of success" --diversity 0.8
```

### Alternative drafts
```bash
litassist draft case_facts.txt "Draft letter before action to Marcus Wong demanding return of vehicle"
litassist draft case_facts.txt outputs/brainstorm_*.txt "Draft particulars of claim for conversion and detinue"
litassist draft case_facts.txt outputs/barbrief_*.txt "Draft opening submissions for trial"
```

### FVO-compliant and practical documents
```bash
# FVO-compliant service document
litassist draft case_facts.txt "Draft affidavit of service through legal practitioner complying with FVO restrictions" --verify

# Payment evidence affidavit
litassist draft case_facts.txt "Draft affidavit exhibiting bank cheque and payment evidence with chain of custody" --verify

# Practical relief orders
litassist draft case_facts.txt "Draft proposed orders for sale of vehicle and payment of proceeds" --verify
```

## PHASE 10: EXTRACT FACTS (from all generated documents)
```bash
# Extract facts from all generated documents in one command
litassist extractfacts outputs/brainstorm_*.txt outputs/barbrief_*.txt outputs/strategy_*.txt outputs/counselnotes_*.txt

# Or process each type separately if needed
litassist extractfacts outputs/brainstorm_*.txt
litassist extractfacts outputs/barbrief_*.txt outputs/draft_*.txt
```

## PHASE 11: VERIFICATION OF KEY DOCUMENTS
```bash
litassist verify outputs/draft_*application*.txt --citations
litassist verify outputs/draft_*submissions*.txt --soundness --reasoning
litassist verify outputs/draft_*memorandum*.txt
```

## PHASE 12: RESEARCH SYNTHESIS (Consolidate all research findings)
Create intermediate synthesis documents to consolidate the extensive research:

### Step 1: Synthesize all legal research
```bash
# Combine all lookup research and digest findings into a research synthesis
litassist counselnotes outputs/lookup_*.txt outputs/digest_*.txt outputs/extractfacts_*.txt --extract all --verify
# This creates: outputs/counselnotes_lookup_digest_extractfacts_[timestamp].txt
```

### Step 2: Synthesize strategic materials
```bash
# Combine brainstormed strategies with the research synthesis
litassist counselnotes outputs/brainstorm_*.txt outputs/counselnotes_lookup_*.txt --extract principles
# This creates: outputs/counselnotes_brainstorm_counselnotes_[timestamp].txt
```

### Step 3: Create final comprehensive synthesis
```bash
# Combine everything including barbrief into final synthesis
litassist counselnotes outputs/counselnotes_brainstorm_*.txt outputs/barbrief_*.txt outputs/draft_*.txt --verify
# This creates: outputs/counselnotes_counselnotes_barbrief_draft_[timestamp].txt
```

## PHASE 13: FINAL COMPREHENSIVE STRATEGY
Use the synthesized documents to create the master strategy:
```bash
# Now strategy command can use the comprehensive synthesis
litassist strategy case_facts.txt --outcome "Comprehensive recovery of vehicle value through all available causes of action" --strategies outputs/counselnotes_counselnotes_barbrief_*.txt --verify
```

## PHASE 14: FINAL INTEGRATION DOCUMENT (Optional but Recommended)
For the most comprehensive integration, use draft command which can access ALL files:
```bash
# Create final strategic litigation roadmap using ALL outputs
litassist draft outputs/case_facts_*.txt outputs/extractfacts_*.txt outputs/brainstorm_*.txt outputs/lookup_*.txt outputs/counselnotes_*.txt outputs/barbrief_*.txt outputs/strategy_*.txt outputs/digest_*.txt outputs/draft_*.txt "Create comprehensive strategic litigation roadmap synthesizing all research, analysis, strategies, and recommendations for recovering vehicle value through all available causes of action" --verify
```

## Notes
- All outputs are automatically timestamped and saved in the `outputs/` directory (note: "outputs" not "output")
- Use wildcards (*.txt) to reference timestamped output files - remember to quote them!
- The dual brainstorming approach:
  - **Phase 1**: Early creative brainstorm based purely on case facts (generates initial creative thinking)
  - **Phase 5**: Research-informed brainstorm using --research flag (enhances orthodox strategies with precedents)
  - Both generate separate output files with orthodox and unorthodox strategies
  - Each also creates 3 additional reasoning trace files: *_orthodox_reasoning.txt, *_unorthodox_reasoning.txt, *_analysis_reasoning.txt
- The `strategy` command creates an additional *_reasoning.txt file
- The `barbrief` command may create *_reasoning.txt files
- Brainstorm ALWAYS performs verification automatically (no --verify flag needed or accepted)
- Many other commands have automatic verification enabled (extractfacts, barbrief, strategy)
- Commands can accept multiple input files for comprehensive analysis
- **NEW**: Glob patterns now supported in brainstorm (--facts, --research) and barbrief (--strategies, --research, --documents)
- **FIXED**: Token limits default to True (32K tokens) and chunk size increased to 200K chars

## Synthesis Approach (Option B)
This workflow implements a multi-stage synthesis approach to overcome the strategy command's limitation of only accepting one case facts file and one strategies file:
1. **Phase 12**: Creates three levels of synthesis using counselnotes to consolidate ~50 documents into digestible summaries
2. **Phase 13**: The strategy command uses the final synthesis document, ensuring it's informed by all research
3. **Phase 14**: Optional but recommended - uses draft command for true comprehensive integration since it can access ALL files directly

The dual brainstorming approach (Phase 1 and Phase 5) ensures:
- Early creative strategies are not constrained by existing case law
- Later research-informed strategies benefit from comprehensive legal precedents
- Maximum strategic coverage through both approaches

## Key Commands and Their Input Capabilities
- `extractfacts`: NOW accepts multiple files - consolidates into single fact sheet (IMPROVED!)
  - [WARNING] Each file must be under 1MB limit
- `digest`: NOW accepts multiple files - creates consolidated digest with source attribution (IMPROVED!)
  - Better for large files and unstructured content
- `strategy`: Only accepts 1 case facts file + 1 optional strategies file (LIMITED)
- `counselnotes`: Accepts multiple files (GOOD for synthesis)
- `barbrief`: Accepts case facts + strategies + multiple research files via --research flag
- `draft`: Accepts unlimited files with RAG support (BEST for final integration)

## Common Issues and Solutions

### File Too Large Error
**Problem**: "Source file too large (X characters). Please provide a file under 1,000,000 characters."

**Solution**: 
1. Use `digest` instead of `extractfacts` for large files
2. Split large files into smaller chunks
3. Extract only relevant portions of chat logs/correspondence

### Handling Mixed Document Types
**Best Practice**:
- Structured legal documents (contracts, affidavits) → `extractfacts`
- Large conversational files (WhatsApp, emails) → `digest` with `--hint`
- Combine insights manually in case_facts.txt

### Token Limit Issues (FIXED July 2025)
**Previous Issue**: Commands producing empty or truncated output despite having content
**Solution**: Token limits now default to True in config, enabling 32K tokens for most models
**Note**: If you still experience issues, ensure your config.yaml has `use_token_limits: true`

### Glob Pattern Usage
**Best Practice**: Always quote glob patterns to prevent shell expansion
- [Y] CORRECT: `--research 'outputs/lookup_*.txt'`
- [N] WRONG: `--research outputs/lookup_*.txt`

### YAML Configuration Issues
**Problem**: AttributeError when sections in config.yaml contain only comments
**Solution**: Fixed in code - commented sections now handled gracefully