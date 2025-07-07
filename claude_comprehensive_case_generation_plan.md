# Comprehensive Case Document Generation Plan

This plan generates 50+ documents for the Osipov v Wong vehicle ownership dispute, maximizing coverage for downstream strategy analysis.

## PHASE 1: BRAINSTORMING (generates orthodox & unorthodox strategies automatically)
```bash
litassist brainstorm case_facts.txt --side plaintiff --area civil
```

## PHASE 2: EXTRACT FACTS FROM SOURCE DOCUMENTS
Extract structured facts from all PDF documents in the case bundle with a single command:
```bash
# Process all PDFs together into one consolidated fact sheet
litassist extractfacts "/Users/witt/Desktop/litassist/Car Docs for civil case 2025"/*.pdf

# Or specify individual files if needed
litassist extractfacts "/Users/witt/Desktop/litassist/Car Docs for civil case 2025/car_bundle.pdf" "/Users/witt/Desktop/litassist/Car Docs for civil case 2025/suncorp_bundle.pdf"

# Or mix case_facts.txt with PDFs to consolidate everything
litassist extractfacts case_facts.txt "/Users/witt/Desktop/litassist/Car Docs for civil case 2025"/*.pdf
```
Note: extractfacts now accepts multiple files and creates a single consolidated fact sheet with the 10 required headings from all sources.

## PHASE 3: EXTENSIVE CASE LAW RESEARCH (15+ research files)

### Gift elements research
```bash
litassist lookup "gift valid elements delivery acceptance donative intent motor vehicle" --mode irac --comprehensive
litassist lookup "incomplete gift presumed resulting trust vehicle registration ownership" --mode irac --comprehensive
litassist lookup "gift delivery constructive symbolic motor vehicle keys possession" --mode irac
```

### Presumption of advancement research  
```bash
litassist lookup "presumption advancement de facto relationship same-sex couples property" --mode irac --comprehensive
litassist lookup "presumption advancement rebuttal evidence contrary intention" --mode irac
litassist lookup "matrimonial cause de facto property settlement time limits ACT" --mode irac
```

### Alternative claims research
```bash
litassist lookup "detinue motor vehicle possession wrongful detention ACT law" --mode irac
litassist lookup "conversion trespass goods motor vehicle damages ACT" --mode irac
litassist lookup "constructive trust unjust enrichment vehicle purchase" --mode irac --comprehensive
litassist lookup "resulting trust purchase money motor vehicle registration" --mode irac
```

### Equitable defences research
```bash
litassist lookup "laches acquiescence delay family violence order restraining order excuse" --mode irac --comprehensive
litassist lookup "estoppel representation ownership motor vehicle conduct" --mode irac
litassist lookup "clean hands doctrine equity misconduct assault charges" --mode irac
```

### Procedural research
```bash
litassist lookup "ACT Magistrates Court civil jurisdiction equitable remedies sections 257 258" --mode irac
litassist lookup "service process family violence order legal practitioner exemption ACT" --mode irac
```

### Extract specific information
```bash
litassist lookup "gift motor vehicle de facto relationship ACT cases" --extract citations
litassist lookup "presumption advancement same-sex relationships" --extract principles
litassist lookup "detinue conversion motor vehicle remedies" --extract checklist
```

## PHASE 4: DIGEST DOCUMENTS (create summaries and issue spotting)
```bash
litassist digest "/Users/witt/Desktop/litassist/Car Docs for civil case 2025" --mode summary
litassist digest "/Users/witt/Desktop/litassist/Car Docs for civil case 2025" --mode issues --hint "ownership gift presumption advancement"
```

## PHASE 5: RESEARCH-INFORMED BRAINSTORMING (with lookup results)
After completing extensive case law research, run brainstorm again with research context:
```bash
# Run brainstorm with all lookup research files to generate research-grounded strategies
litassist brainstorm case_facts.txt --side plaintiff --area civil --research outputs/lookup_*.txt

# Or be selective with specific research themes
litassist brainstorm case_facts.txt --side plaintiff --area civil --research outputs/lookup_*gift*.txt --research outputs/lookup_*presumption*.txt --research outputs/lookup_*constructive*.txt

# Or use the extracted facts if available
litassist brainstorm outputs/extractfacts_*.txt --side plaintiff --area civil --research outputs/lookup_*.txt
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
litassist barbrief case_facts.txt --strategies outputs/brainstorm_*.txt --hearing trial
```

### With research files
```bash
litassist barbrief case_facts.txt --strategies outputs/brainstorm_*.txt --research outputs/lookup_*gift*.txt --research outputs/lookup_*presumption*.txt --hearing trial
```

### Comprehensive version
```bash
litassist barbrief case_facts.txt --strategies outputs/brainstorm_*.txt --research outputs/lookup_*.txt --supporting "/Users/witt/Desktop/litassist/Car Docs for civil case 2025/*.pdf" --instructions "Focus on rebutting presumption of advancement and establishing incomplete gift" --hearing trial --verify
```

## PHASE 8: STRATEGY ANALYSES

### Basic strategy
```bash
litassist strategy case_facts.txt --outcome "Recover vehicle purchase price of $40,364 from Marcus Wong"
```

### With brainstormed strategies
```bash
litassist strategy case_facts.txt --outcome "Recover vehicle purchase price through detinue or conversion claim" --strategies outputs/brainstorm_*.txt
```

### Multiple strategy runs with different outcomes
```bash
litassist strategy case_facts.txt --outcome "Establish resulting trust over vehicle"
litassist strategy case_facts.txt --outcome "Obtain order for return of vehicle or damages"
litassist strategy case_facts.txt --outcome "Rebut presumption of advancement and prove incomplete gift"
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
- Use wildcards (*.txt) to reference timestamped output files
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
- `strategy`: Only accepts 1 case facts file + 1 optional strategies file (LIMITED)
- `counselnotes`: Accepts multiple files (GOOD for synthesis)
- `barbrief`: Accepts case facts + strategies + multiple research files via --research flag
- `draft`: Accepts unlimited files with RAG support (BEST for final integration)