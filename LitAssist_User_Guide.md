# LitAssist User Guide

## Introduction

LitAssist is a comprehensive legal workflow automation tool designed for Australian legal practice. It provides a structured end-to-end pipeline for litigation support:

```
ingest → analyse → structure → brainstorm → strategy → draft
```

This guide demonstrates how to use each workflow through a running example of a family court case, *Smith v Jones*, involving a complex child custody dispute with issues of interstate relocation and allegations of parental alienation.

```mermaid
graph TD
    A["Lookup - Research"] --> B["Digest - Analyse"]
    B --> C["ExtractFacts - Structure"]
    C --> D["Brainstorm - Generate Options"]
    D --> E["Strategy - Plan Approach"]
    E --> F["Draft - Create Documents"]
    
    G[Utilities] --> H["Test - API Connectivity"]
    G --> I["Audit Logging"]
    G --> J["Mock Mode"]
```

## Running Example: Smith v Jones

To illustrate each workflow in a practical context, we'll use a fictional family court case with the following characteristics:

**Case Overview:** Smith v Jones (Federal Circuit and Family Court of Australia, Division 1)

**Key Parties:**
- Jennifer Smith (mother, 38): Formerly resided in Sydney, recently relocated to Brisbane for a senior hospital position
- Michael Jones (father, 40): Still residing in Sydney
- Emily Jones (12) and Thomas Jones (8): Currently living with their mother in Brisbane

**Core Issues:**
1. **Complex Parenting Arrangements**: The parents previously had a consent order with a week-about arrangement when both lived in Sydney.
2. **Interstate Relocation**: Ms. Smith relocated with the children to Brisbane in January 2025, citing a career opportunity. Mr. Jones filed a contravention application in February 2025.
3. **Allegations of Parental Alienation**: Mr. Jones alleges Ms. Smith is "poisoning the children against him," while Ms. Smith claims Mr. Jones exhibits controlling behavior.

**Procedural Status:**
- Interim parenting orders issued in April 2025
- Final hearing scheduled for June 2025

This running example provides context for understanding how each LitAssist workflow contributes to managing a complex family law matter from initial research through to final submissions.

## Key Features

**Global Installation Benefits:**
- ✅ **Use from anywhere** - `litassist` command available in any directory
- ✅ **Local outputs** - All files created in your current working directory
- ✅ **Single configuration** - One global config with all your API keys
- ✅ **Project isolation** - Each case directory gets its own outputs/ and logs/ subdirectories

**File Management & Organization:**
- ✅ **Timestamped outputs** - All commands save to unique timestamped files (never overwrites)
- ✅ **Archive preservation** - Commands like extractfacts and brainstorm maintain both current files and timestamped archives
- ✅ **API keys in one secure location** - No duplication across projects
- ✅ **Automatic logging** - Every operation creates detailed audit logs
- ✅ **Australian English** - All outputs use Australian legal terminology

**Citation Verification & Quality Control:**
- ✅ **Zero-tolerance citation verification** - All legal references validated against AustLII database
- ✅ **Real-time online validation** - HEAD requests verify case existence during generation
- ✅ **Intelligent regeneration** - Commands automatically fix citation issues where possible
- ✅ **Quality over quantity** - Strategy commands discard options with unfixable citation problems
- ✅ **Enhanced error messages** - Clear explanations of citation failures with specific actions taken
- ✅ **Verification status transparency** - Always informed when verification runs and why

**Legal Reasoning & Analysis (New June 2025):**
- ✅ **Multi-section reasoning traces** - Brainstorm saves separate reasoning files for orthodox, unorthodox, and analysis sections
- ✅ **Transparent legal reasoning** - See the logic behind strategy selection and "most likely to succeed" analysis
- ✅ **Structured analysis** - Each reasoning trace includes issue, applicable law, application to facts, and conclusion
- ✅ **Comprehensive timing** - All operations timed and logged for performance monitoring
- ✅ **Centralized configuration** - Log format and other settings moved to config.yaml for consistency

## Citation Quality Control

LitAssist employs a comprehensive two-phase citation checking system to ensure all legal references are accurate and verifiable:

### Phase 1: Citation Validation (Offline Pattern Analysis)

**Purpose**: Detect potentially problematic citation patterns without requiring internet access

**What it catches**:
- **AI Hallucinations**: Generic case names like "Smith v Jones" that are commonly fabricated
- **Impossible Citations**: Future dates, non-existent courts, anachronistic references
- **Suspicious Patterns**: Placeholder names, single-letter parties, "Corporation v Corporation"
- **Format Issues**: Malformed parallel citations, unrealistic page numbers

**How it works**:
- Runs instantly as part of pattern matching
- Uses comprehensive pattern library based on Australian legal citation formats
- No internet connection required
- Provides immediate feedback on problematic patterns

**Example detections**:
```
GENERIC CASE NAME: Smith v Jones
→ FAILURE: Both parties use common surnames (possible AI hallucination)
→ ACTION: Flagging for manual verification

ANACHRONISTIC CITATION: [1970] FCAFC 123
→ FAILURE: Full Federal Court not established until 1977
→ ACTION: Excluding impossible historical reference
```

### Phase 2: Citation Verification (Online Database Checks)

**Purpose**: Confirm that citations actually exist in legal databases

**What it verifies**:
- **Australian Cases**: Checks against AustLII database
- **International Citations**: Recognizes UK, US, NZ citations as valid but not checkable
- **Traditional Citations**: Accepts format like "(1980) 146 CLR 40" temporarily
- **Medium-Neutral Citations**: Validates format like "[2020] HCA 41" and retrieves URLs

**How it works**:
- Makes HEAD requests to AustLII to verify case existence
- Handles international citations appropriately (marked as verified but not on AustLII)
- Provides URLs for verified Australian cases
- Runs during content generation to ensure accuracy

**Example verifications**:
```
[2020] HCA 41
→ Verified: True
→ URL: https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/HCA/2020/41.html

[1932] AC 562
→ Verified: True  
→ Reason: UK/International citation (Appeal Cases) - not available on AustLII
```

### How They Work Together

The two systems complement each other:

1. **Validation** runs first to catch obvious problems through pattern analysis
2. **Verification** confirms that remaining citations actually exist
3. Together they provide comprehensive quality control

**Example workflow**:
```
Input text: "See Smith v Jones [2025] HCA 99"

Phase 1 (Validation):
- Detects "Smith v Jones" as generic case name
- Detects "[2025] HCA 99" as future citation

Phase 2 (Verification):  
- Would check AustLII but validation already flagged issues
- Both problems reported to user
```

### Understanding Citation Logs

LitAssist creates two types of citation-related logs:

#### Citation Validation Logs
**Location**: `logs/citation_validation_YYYYMMDD-HHMMSS.{json|md}`

**When issues found**:
```markdown
## Details
- Method: validate_citation_patterns
- Input Text Length: 19560 characters
- Online Verification: True
- Issues Found: 3

## Issues Found
- GENERIC CASE NAME: Brown v Wilson
- FUTURE CITATION: [2026] VSC 123
- COURT NOT RECOGNIZED: [2020] XYZ 45
```

**When no issues found**: Minimal log showing successful validation

#### Citation Verification Session Logs
**Location**: `logs/citation_verification_session_YYYYMMDD-HHMMSS.{json|md}`

**Contents**:
```markdown
## Summary
- Citations Found: 15
- Verified: 12
- Unverified: 3

## Verified Citations
- [2020] HCA 41
- (1984) 155 CLR 549
- [2019] FCAFC 185

## Unverified Citations
- [2020] HCA 999: Not found on AustLII
- Smith v Jones: Generic case name pattern

## International Citations
- [1932] AC 562: UK citation - not on AustLII
- 123 U.S. 456: US citation - not on AustLII
```

### Command-Specific Citation Handling

Different commands handle citation issues differently:

| Command | Validation | Verification | Response to Issues |
|---------|------------|--------------|-------------------|
| lookup | ✓ | ✓ | Warnings in output |
| digest | ✓ | ✓ | Warnings per chunk |
| extractfacts | ✓ | ✓ | Enhanced error messages |
| brainstorm | ✓ | ✓ | Regenerates problematic strategies |
| strategy | ✓ | ✓ | Discards options with bad citations |
| draft | ✓ | ✓ | Appends warnings to draft |

### Best Practices

1. **Review all citation warnings** - They indicate potential reliability issues
2. **Check logs for patterns** - Frequent generic names may indicate AI hallucination
3. **Verify international citations manually** - System can't check non-Australian databases
4. **Use verification for critical documents** - Court filings should have zero citation issues

### Benefits

- **Professional Protection**: Prevents reliance on non-existent cases
- **Quality Assurance**: Ensures all legal references are verifiable
- **Audit Trail**: Complete logs for compliance and review
- **Time Savings**: Automatic detection prevents manual citation checking

## Installation and Setup

**Quick Installation:**
```bash
# Install with pipx (see INSTALLATION.md for detailed instructions)
brew install pipx
pipx install -e /path/to/litassist
pipx ensurepath && source ~/.zshrc

# Setup configuration
cd /path/to/litassist
cp config.yaml.template config.yaml
# Edit config.yaml with your API keys
```

**Verify Installation:**
```bash
litassist --help
litassist test  # Test API connectivity
```

For complete installation instructions, troubleshooting, and alternative methods, see [INSTALLATION.md](INSTALLATION.md).

## Configuration

### config.yaml Settings

**New June 2025 - Centralized Configuration**: Log format and other settings have been moved from CLI options to config.yaml for consistency and user convenience.

Key configuration options in the `general` section:
```yaml
general:
  heartbeat_interval: 10    # Progress indicator interval in seconds (default: 10)
  max_chars: 20000          # Maximum characters per chunk for document processing (default: 20000)
  rag_max_chars: 8000       # Maximum characters per chunk for RAG retrieval (default: 8000)
  log_format: "json"        # Format for audit logs: "json" or "markdown" (default: json)
```

### Log Format Configuration

**Previous behavior**: Required `--log-format` CLI option every time
```bash
# Old way - had to specify every time
litassist --log-format markdown lookup "contract law"
```

**New behavior**: Set once in config.yaml, use everywhere
```yaml
# In config.yaml
general:
  log_format: "markdown"  # Set your preference once
```

```bash
# Now just run commands - uses config.yaml setting
litassist lookup "contract law"

# Override config.yaml for one-off changes
litassist --log-format json lookup "contract law"  
```

**Benefits**:
- ✅ Set your preference once in config.yaml
- ✅ Consistent logging format across all commands
- ✅ CLI option still available for overrides
- ✅ Aligns with other configuration patterns

## Working Directory Setup

LitAssist works from any directory and creates outputs locally:

```bash
# Create project directory for Smith v Jones case
mkdir ~/legal-cases/smith-v-jones-2025
cd ~/legal-cases/smith-v-jones-2025

# LitAssist will create outputs/ and logs/ directories here
# All commands use global config but create outputs locally
```

## Output File Management

### Timestamped Output Files
All LitAssist commands save their results to timestamped text files in the `outputs/` directory, ensuring no output is ever lost:

**Manual Working Files** (created and edited by user):
- `case_facts.txt` - Manually maintained case facts file
- `strategies.txt` - Manually maintained strategies file

**Timestamped Archive Files** (never overwritten):
- `lookup_[query_slug]_YYYYMMDD_HHMMSS.txt` - Search results
- `digest_[mode]_[filename_slug]_YYYYMMDD_HHMMSS.txt` - Document analysis
- `extractfacts_[filename_slug]_YYYYMMDD_HHMMSS.txt` - Extracted facts from documents
- `brainstorm_[area]_[side]_YYYYMMDD_HHMMSS.txt` - Generated legal strategies
- `strategy_[outcome_slug]_YYYYMMDD_HHMMSS.txt` - Strategic analysis and draft documents
- `draft_[query_slug]_YYYYMMDD_HHMMSS.txt` - Generated legal drafts

**Example output after running commands:**
```
smith-v-jones-2025/
├── case_facts.txt                                    # Manually created/edited
├── strategies.txt                                    # Manually created/edited
├── outputs/                                          # All command outputs
│   ├── extractfacts_smith_jones_file_20250523_143022.txt
│   ├── brainstorm_family_plaintiff_20250523_144501.txt
│   ├── strategy_interim_orders_20250523_150245.txt
│   └── draft_outline_submissions_20250523_151030.txt
└── logs/                                             # Detailed audit logs
    ├── extractfacts_20250523-143022.md
    ├── brainstorm_20250523-144501.md
    └── strategy_20250523-150245.md
```

### Benefits of Timestamped Files
- **No data loss** - Previous outputs are never overwritten
- **Version history** - Track evolution of strategies and arguments
- **Easy sharing** - Send specific timestamped files to colleagues
- **Manual control** - Working files (case_facts.txt, strategies.txt) remain under user control

## Clean CLI Output Format

**All LitAssist commands now show clean summaries instead of dumping full content to your terminal.**

### What You See on Screen
Every command follows this consistent, professional output pattern:

```
✅ [Command] complete!
📄 Output saved to: outputs/[filename]_YYYYMMDD_HHMMSS.txt
📊 [Processing statistics and summary]
💡 View full [content]: open outputs/[filename]_YYYYMMDD_HHMMSS.txt
```

### Example: Before vs After

**Before (overwhelming terminal output):**
```bash
$ litassist lookup "contract formation elements"
[2000+ lines of legal analysis dumped to terminal]
```

**After (clean summary):**
```bash
$ litassist lookup "contract formation elements"
Found links:
- https://austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/HCA/1893/23.html
- https://austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/HCA/1968/1.html

✅ Lookup complete!
📄 Output saved to: outputs/lookup_contract_formation_elements_20250606_143022.txt
📊 Legal analysis for: contract formation elements
🔍 Searched 2 sources:
   1. Carlill v Carbolic Smoke Ball Co
   2. Australian Woollen Mills v Commonwealth
💡 View full analysis: open outputs/lookup_contract_formation_elements_20250606_143022.txt
```

### Benefits of Clean Output
- **Readable terminal** - No overwhelming text walls
- **Clear file locations** - Always know where your content is saved
- **Processing transparency** - See exactly what was done
- **Professional workflow** - Focus on next steps, not parsing output
- **Full content preserved** - Everything saved to timestamped files

### Accessing Full Content
To read the complete analysis, drafts, or strategies:
```bash
# Option 1: Use the provided command
open outputs/lookup_contract_formation_elements_20250606_143022.txt

# Option 2: Use any text editor
code outputs/lookup_contract_formation_elements_20250606_143022.txt
vim outputs/lookup_contract_formation_elements_20250606_143022.txt

# Option 3: View in terminal
cat outputs/lookup_contract_formation_elements_20250606_143022.txt
```

## Workflow 1: Lookup - Rapid Case-Law Search

**Pipeline Phase**: Ingest (Research)

### Purpose

The `lookup` command performs rapid searches on AustLII for relevant case law using Google Custom Search, then processes the results through Gemini to produce a structured legal answer with citations.

### Command

```bash
./litassist.py lookup "your legal question" [--mode irac|broad] [--engine google|jade] [--extract citations|principles|checklist]
```

Options:
- `--mode`: Choose between IRAC (Issue, Rule, Application, Conclusion) or a broader exploration
- `--engine`: Choose search engine - 'google' for AustLII via CSE (default), 'jade' for Jade.io
- `--extract`: Extract specific information in a structured format for workflow efficiency

#### Search Engine and Mode Combinations

**Search Engines:**
- **Google CSE** (default): Searches AustLII (austlii.edu.au) via Google Custom Search for comprehensive Australian legal database coverage
- **Jade**: Uses Jade.io for recent cases and landmark decisions, with fallback to curated topic-specific cases

**Analysis Modes:**
- **IRAC** (default): Structured legal analysis (Issue, Rule, Application, Conclusion) with precise, deterministic answers
- **Broad**: Creative exploration for more expansive legal thinking

**Recommended Combinations:**
- **Google + IRAC**: Standard research for structured case law analysis from comprehensive AustLII database
- **Google + Broad**: Creative legal research using full AustLII coverage 
- **Jade + IRAC**: Focused analysis using recent/landmark cases when AustLII access is limited
- **Jade + Broad**: Exploratory research with curated high-quality cases

#### Extract Options for Workflow Efficiency

The `--extract` option formats output for specific professional workflows:

**Extract Citations (`--extract citations`)**
- **Purpose**: Generate clean citation lists for court documents and research databases
- **Output**: Formatted list of case citations and legislation references
- **Use Cases**:
  - Building a "Cases Cited" section for court briefs
  - Adding citations to advice letters and legal opinions
  - Creating research databases for complex matters
  - Quick reference lists for oral arguments

**Extract Principles (`--extract principles`)**
- **Purpose**: Extract legal rules and principles in structured format for client communications
- **Output**: Bullet-pointed legal principles suitable for advice letters
- **Use Cases**:
  - Client advice letters requiring clear legal explanations
  - Training materials for junior lawyers
  - Settlement negotiations explaining legal positions
  - Mediation briefs summarizing applicable law

**Extract Checklist (`--extract checklist`)**
- **Purpose**: Generate actionable requirements and practical steps
- **Output**: Checkbox format listing evidence needed and steps to take
- **Use Cases**:
  - Pre-trial preparation ensuring complete coverage
  - File review checklists for complex matters
  - Due diligence processes
  - Client intake procedures for specific legal areas
  - Junior lawyer training and supervision

**Benefits of Extract Options:**
- **Copy-paste ready**: Clean, structured output eliminates manual formatting
- **Context switching reduction**: Get exactly what you need without parsing walls of text
- **Professional output**: Client-ready formatting for immediate use
- **Quality assurance**: Structured checklists ensure nothing is missed

### Example Usage

#### Standard Lookup

In our *Smith v Jones* case, we might need to quickly research the legal framework for parental alienation:

```bash
./litassist.py lookup "What is the legal framework for determining parental alienation in Australian family court cases?" --mode irac
```

#### Using Extract Options

**For court brief preparation (citations needed):**
```bash
./litassist.py lookup "self defence assault requirements" --extract citations
```

**For client advice letter (principles needed):**
```bash
./litassist.py lookup "negligence medical malpractice elements" --extract principles
```

**For case preparation (checklist needed):**
```bash
./litassist.py lookup "unfair dismissal evidence requirements" --extract checklist
```

**Output Example**:
```
Issue: What legal framework do Australian family courts use to determine cases involving parental alienation?

Rule: In Australia, parental alienation is addressed primarily through the Family Law Act 1975 (Cth), which emphasizes the best interests of the child as the paramount consideration in parenting matters. In Karabes v Karabes [2019] FamCAFC 3, the Full Court clarified that while parental alienation is not explicitly defined in the legislation, courts must consider:
1. The benefit to children of having a meaningful relationship with both parents (s60CC(2)(a))
2. The need to protect children from physical or psychological harm (s60CC(2)(b))
3. The willingness and ability of each parent to facilitate a relationship between the child and the other parent (s60CC(3)(c))

Application: When determining whether parental alienation has occurred, courts examine evidence of one parent systematically denigrating the other parent or deliberately interfering with parent-child contact without justification. In Miles & Zanelli [2022] FedCFamC1A 20, Justice Kent emphasized that courts must distinguish between legitimate protective behaviors and unjustified alienating behaviors. Evidence is typically provided through experts such as family consultants, psychiatrists, or psychologists as seen in Kappas & Drakos [2018] FamCA 37.

Conclusion: Australian family courts address parental alienation through the best interests framework of the Family Law Act. Courts apply a thorough examination of evidence regarding parental behavior and expert testimony, weighing the importance of meaningful relationships with both parents against any genuine protective concerns. Courts can order various remedies including changes to parenting arrangements, therapy interventions, or in extreme cases, changes to the child's primary residence as demonstrated in Ralton & Ralton [2016] FCWA 65.

Sources:
- Family Law Act 1975 (Cth), sections 60B, 60CC, https://www.austlii.edu.au/cgi-bin/viewdb/au/legis/cth/consol_act/fla1975114/
- Karabes v Karabes [2019] FamCAFC 3, https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FamCAFC/2019/3.html | https://jade.io/article/632302
- Miles & Zanelli [2022] FedCFamC1A 20, https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FedCFamC1A/2022/20.html | https://jade.io/article/909183  
- Kappas & Drakos [2018] FamCA 37, https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FamCA/2018/37.html | https://jade.io/article/572418
- Ralton & Ralton [2016] FCWA 65, https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/wa/FCWA/2016/65.html | https://jade.io/article/460030
```

**Extract Examples:**

**Citations Output** (using `--extract citations`):
```
CITATIONS FOUND:
Crimes Act 1900 (NSW) s 418
R v Brown [2019] NSWCCA 123
R v Katarzynski [2002] NSWSC 613
R v Smith [2020] NSWDC 45
```

**Principles Output** (using `--extract principles`):
```
LEGAL PRINCIPLES:
• Self-defence requires reasonable belief of imminent threat to person or property
• Force used must be proportionate to the perceived threat
• Defendant's subjective belief is critical, not objective reasonableness
• No duty to retreat if threat is imminent and escape not safely possible
• Burden of proof shifts to prosecution to disprove self-defence beyond reasonable doubt
```

**Checklist Output** (using `--extract checklist`):
```
PRACTICAL CHECKLIST:
□ Evidence of threat made against defendant
□ Defendant's subjective belief documented
□ Proportionality of response to threat level
□ Witness statements supporting threat perception
□ No available avenue of safe retreat
□ Medical evidence of injuries sustained
□ Police statements and reports
□ Character evidence supporting credibility
```

### Advanced Usage and Workflow Integration

#### Combining Extract Options with Other Parameters

**Strategic Research Combinations:**
```bash
# For complex constitutional matters - use Jade for landmark cases + broad analysis
./litassist.py lookup "implied freedom of political communication" --engine jade --mode broad --extract principles

# For urgent court prep - use Google for comprehensive coverage + structured analysis  
./litassist.py lookup "summary judgment applications" --engine google --mode irac --extract checklist

# For client communications - extract principles in accessible format
./litassist.py lookup "unfair contract terms consumer law" --mode broad --extract principles
```

#### File Organization and Naming

**Output Structure:**
```
outputs/
├── lookup_citations_contract_breach_20250406_143022.txt
├── lookup_principles_negligence_20250406_143156.txt
├── lookup_checklist_defamation_20250406_143340.txt
└── lookup_constitutional_law_20250406_143445.txt (default format)
```

**File Naming Convention:**
- `lookup_[extract]_[question_slug]_[timestamp].txt` (with extract option)
- `lookup_[question_slug]_[timestamp].txt` (default format)
- Question slug: First 50 chars, special chars removed, spaces as underscores

#### Integration with LitAssist Command Pipeline

**End-to-End Workflow Examples:**

**1. Court Brief Preparation Workflow**
```bash
# Step 1: Research legal framework and collect citations
./litassist.py lookup "negligence medical malpractice" --extract citations

# Step 2: Analyze case documents for facts
./litassist.py digest case_bundle.pdf --mode issues

# Step 3: Extract structured facts for strategy
./litassist.py extractfacts medical_reports.pdf

# Step 4: Draft argument using research and facts
./litassist.py draft case_facts.txt "negligence argument medical malpractice"
```

**2. Client Advice Letter Workflow**
```bash
# Step 1: Research principles in client-friendly format
./litassist.py lookup "employment termination unfair dismissal" --extract principles

# Step 2: Analyze employment documents
./litassist.py digest employment_file.pdf --mode summary

# Step 3: Create advice structure using principles from lookup output
# Copy principles from outputs/lookup_principles_employment_*.txt into advice letter template
```

**3. Due Diligence Workflow**
```bash
# Step 1: Create compliance checklist
./litassist.py lookup "corporate governance ASX requirements" --extract checklist

# Step 2: Analyze corporate documents against checklist
./litassist.py digest board_minutes.pdf --mode issues

# Step 3: Cross-reference findings with compliance requirements
# Use checklist from outputs/lookup_checklist_corporate_*.txt as review framework
```

#### Real-World Integration Patterns

**Pattern 1: Research → Analysis → Action**
- **Lookup (extract citations)** → **Digest (mode issues)** → **Draft argument**
- Establishes legal authority, identifies case issues, creates persuasive document

**Pattern 2: Principles → Facts → Strategy** 
- **Lookup (extract principles)** → **Extractfacts** → **Brainstorm strategies**
- Understands law, structures facts, develops arguments

**Pattern 3: Checklist → Review → Compliance**
- **Lookup (extract checklist)** → **Digest documents** → **Manual compliance review**
- Creates framework, analyzes documents, ensures completeness

#### Workflow Efficiency Tips

**Copying Output Between Commands:**
```bash
# Extract citations for court brief
./litassist.py lookup "contract formation requirements" --extract citations

# Copy citations from outputs/lookup_citations_contract_*.txt
# Paste into draft command input file for automatic citation inclusion

./litassist.py draft case_facts.txt "contract formation argument" 
# LitAssist will incorporate the existing research into the draft
```

**File Management for Complex Matters:**
```bash
# Organize lookup results by legal area
mkdir research_negligence research_contract research_defamation

# Move relevant lookup outputs to topic folders
mv outputs/lookup_*negligence* research_negligence/
mv outputs/lookup_*contract* research_contract/
```

**Iterative Research Refinement:**
```bash
# Start broad, then narrow focus
./litassist.py lookup "contract law" --mode broad --extract principles
./litassist.py lookup "specific performance remedies" --mode irac --extract citations  
./litassist.py lookup "equity specific performance discretion" --engine jade --extract checklist
```

#### Performance and Cost Considerations

**Efficient Research Strategies:**
- Use `--extract citations` when you only need case references (faster processing)
- Use `--engine jade` for specific topic areas with known landmark cases
- Use `--mode irac` for structured legal analysis, `--mode broad` for creative approaches
- Combine extract options with targeted questions rather than broad topics

**Output Reuse:**
- Extract outputs are designed for copy-paste into other documents
- Citations lists can be directly included in court briefs
- Principles sections can be incorporated into advice letters
- Checklists can serve as templates for multiple similar matters

### Next in Pipeline

After establishing the relevant legal frameworks through `lookup`, you can proceed to the `digest` workflow to analyze the case documents in detail.

## Workflow 2: Digest - Large Document Processing

**Pipeline Phase**: Analyse

### Purpose

The `digest` command processes large documents by splitting them into manageable chunks and using Claude to either summarize content chronologically or identify potential legal issues in each section.

### Command

```bash
./litassist.py digest <file> [--mode summary|issues]
```

Options:
- `--mode`: Choose between chronological summary or issue-spotting (default: summary)

**Output**: All analysis saved to timestamped files: `digest_[mode]_[filename_slug]_YYYYMMDD_HHMMSS.txt`

**Citation Quality Control**: All digest outputs undergo automatic citation verification. If any citations are found to be invalid or unverifiable, clear warnings are displayed at the top of each chunk's output explaining the specific issues and actions taken.

### Handling Non-Legal Documents

While designed for legal content, the `digest` command can process various document types:

**Works well with**:
- Bank statements → Produces chronological financial events (use `--mode summary`)
- Commercial agreements → Extracts key terms and conditions
- Medical reports → Summarizes findings chronologically

**Limitations**:
- The system prompt specifies "Australian law only" which may affect interpretation
- Financial terms may be framed in legal contexts
- `--mode issues` is less effective for non-legal content

**Best practices**:
- Always use `--mode summary` for non-legal documents
- Use outputs as a starting point for further analysis
- All results saved to timestamped files: `lookup_[query_slug]_YYYYMMDD_HHMMSS.txt`

### Example Usage

For the *Smith v Jones* case, we have received a lengthy affidavit from our client that needs to be broken down:

```bash
./litassist.py digest examples/smith_affidavit.pdf --mode issues
```

**Output Example**:
```
--- Chunk 1 ---
Potential Legal Issues:

1. Jurisdictional Questions
   There appears to be a potential jurisdictional dispute as Ms. Smith has relocated from NSW to Queensland with the children without Mr. Jones's consent. This raises issues under Family Law Act s65DAA regarding relocation and may trigger the need for a specific "relocation order" from the court.

2. Parental Responsibility
   Ms. Smith's unilateral decision-making regarding the children's schooling and medical care potentially conflicts with the requirement for joint consultation on major long-term issues under s61DA of the Family Law Act, particularly as there seems to have been a previous parenting order establishing equal shared parental responsibility.

3. Family Violence Allegations
   Ms. Smith makes several references to "controlling behavior" and "emotional manipulation" which, while not explicitly characterized as family violence, could potentially be framed as coercive control under s4AB(2) of the Family Law Act. However, the allegations lack specific incidents and may require further particulars.

--- Chunk 2 ---
Potential Legal Issues:

4. Best Interests Considerations
   The children's expressed wishes to remain with their mother in Queensland raises consideration of s60CC(3)(a) regarding children's views, particularly for the 12-year-old child whose views may be given greater weight due to age and maturity.

5. Parental Alienation Concerns
   Mr. Jones's allegations that Ms. Smith is "poisoning the children against him" raise potential parental alienation issues. This relates to s60CC(3)(c) regarding the willingness of each parent to facilitate a relationship between the children and the other parent.
   
...
```

### Next in Pipeline

After analyzing the documents with `digest`, you need to extract key facts in a structured format using the `extractfacts` workflow.

## Workflow 3: ExtractFacts - Deterministic Fact Extraction

**Pipeline Phase**: Structure

### Purpose

The `extractfacts` command processes a document to extract relevant case facts and organizes them into a structured format with ten standard headings, providing a foundation for other commands that require structured facts.

**Note**: Input documents must be text-searchable PDFs for optimal fact extraction.

**Citation Quality Control**: ExtractFacts includes mandatory citation verification with enhanced error messages. Any problematic citations are flagged with specific failure reasons (e.g., "GENERIC CASE NAME", "FUTURE CITATION") and clear actions taken (e.g., "Flagging for manual verification", "Excluding impossible future case"). This ensures the extracted facts provide a reliable foundation for subsequent strategic analysis.

### Command

```bash
./litassist.py extractfacts <file>
```

**Note:** This command includes automatic verification for accuracy and completeness - no additional flag needed. The --verify flag is ignored as verification is mandatory for this foundational command.

### Required Output Format

The `extractfacts` command produces a `case_facts.txt` file with EXACTLY these 10 required headings:

1. **Parties**: Identify all parties involved in the matter
2. **Background**: Provide context including relationship between parties
3. **Key Events**: List significant events in chronological order with dates
4. **Legal Issues**: Enumerate the legal questions to be addressed
5. **Evidence Available**: Catalog all available evidence and documents
6. **Opposing Arguments**: Summarize the counterparty's position
7. **Procedural History**: Detail the procedural steps taken to date
8. **Jurisdiction**: Specify the relevant court/tribunal
9. **Applicable Law**: List statutes, regulations, and principles that apply
10. **Client Objectives**: State what the client aims to achieve

This structured format is used by both the `brainstorm` and `strategy` commands. The `strategy` command in particular performs strict validation requiring ALL headings to be present exactly as listed above.

Example files are available in the `/examples` directory:
- `example_strategy_headers.txt` - Template with all required headings
- `example_extractfacts_output.txt` - Sample output from extractfacts 
- `example_case_facts.txt` - Complete example with all headings populated

### Handling Non-Legal Documents

The `extractfacts` command is specifically designed for legal documents and forces content into a rigid 10-heading structure:

**Compatible document types**:
- Legal proceedings (optimal use case)
- Commercial contracts (reasonable fit with some adaptation)

**Challenging document types**:
- Bank statements (financial data forced into legal categories)
- Personal documents (may produce stretched interpretations)
- Medical records (terminology misalignments)

**Workarounds for non-legal documents**:
1. First use `digest --mode summary` to understand the document's content
2. Manually create a `case_facts.txt` file following the 10-heading format
3. Focus on relevant sections (leave others minimal but present)
4. Ensure all 10 headings exist in the file even if some have minimal content

### Example Usage

Now we need to create a structured fact sheet for the *Smith v Jones* case:

```bash
./litassist.py extractfacts examples/smith_jones_file.pdf
```

**Output Example**:

The command creates:
- `extractfacts_[filename_slug]_YYYYMMDD_HHMMSS.txt` - Timestamped output file with structured facts
- Note: To use with other commands, manually create/update `case_facts.txt`

```
1. Parties
Applicant: Jennifer Smith (mother, 38)
Respondent: Michael Jones (father, 40)
Children: Emily Jones (12) and Thomas Jones (8)

2. Background
Parties had jointly-owned property in Sydney.
Ms. Smith accepted senior position in Brisbane hospital.
Children enrolled in Brisbane schools since February 2025.
Mr. Jones continues to reside in Sydney.
Current communication between parties is minimal and strained.

3. Key Events
- 2012: Parties married in Sydney
- 2013: Emily born
- 2017: Thomas born
- 2022: Parties separated but continued living in Sydney home
- 2023: Consent parenting orders established (week-about arrangement)
- January 2025: Ms. Smith relocated with children to Brisbane (citing job opportunity)
- February 2025: Mr. Jones filed contravention application

4. Legal Issues
1. Whether relocation constitutes breach of consent orders
2. Best interests assessment under s60CC considerations
3. Weight of children's views given their ages
4. Allegations of parental alienation

5. Evidence Available
1. Consent orders dated August 2023
2. School enrollment records
3. Employment contract from Brisbane hospital
4. Father's contravention application
5. Email correspondence between parties

...
```

### Next in Pipeline

With the structured case facts in place, you can now use the `brainstorm` workflow to generate novel legal arguments or remedies.

## Workflow 4: Brainstorm - Comprehensive Legal Strategy Generation

**Pipeline Phase**: Brainstorm

### Purpose

The `brainstorm` command uses Grok's creative capabilities to generate a comprehensive set of litigation strategies based on the facts provided, tailored to your specific party side and legal area. The command produces both orthodox and unorthodox strategies, along with an assessment of which are most likely to succeed.

**Output**: The brainstormed strategies are saved to:
- `brainstorm_[area]_[side]_YYYYMMDD_HHMMSS.txt` - Main strategies file with comprehensive strategy options
- `brainstorm_[area]_[side]_YYYYMMDD_HHMMSS_orthodox_reasoning.txt` - Legal reasoning behind orthodox strategy selection
- `brainstorm_[area]_[side]_YYYYMMDD_HHMMSS_unorthodox_reasoning.txt` - Reasoning behind unorthodox strategy development  
- `brainstorm_[area]_[side]_YYYYMMDD_HHMMSS_analysis_reasoning.txt` - **Most important:** Analysis of why certain strategies are "most likely to succeed"
- Note: To use with other commands, manually create/update `strategies.txt`

**New June 2025 - Multi-Section Reasoning Traces**: The brainstorm command now captures the legal reasoning behind each major section, providing unprecedented transparency into the strategic analysis process.

**Quality Control ("Option B" Implementation)**: When citation issues are detected, brainstorm uses selective regeneration - only individual strategies with citation problems are regenerated, while verified strategies are preserved unchanged. This "quality over quantity" approach ensures users receive fewer but higher-quality strategies rather than many options requiring manual review for citation issues.

### Command

```bash
./litassist.py brainstorm <case_facts_file> --side <party_side> --area <legal_area> [--verify]
```

Required parameters:
- `--side`: Which side you are representing (options depend on area):
  - Criminal cases: `accused` only
  - Civil/Commercial cases: `plaintiff` or `defendant`
  - Family/Administrative cases: `plaintiff`, `defendant`, or `respondent`
- `--area`: Legal area of the matter - `criminal`, `civil`, `family`, `commercial`, or `administrative`
- `--verify` (optional): Run AI verification to review strategy viability and identify risks. Automatically enabled when using Grok models due to hallucination tendencies (see [Using the --verify Switch](#using-the--verify-switch))

**Note**: The command will warn you if you use incompatible side/area combinations (e.g., "plaintiff" in criminal cases) but will still generate strategies.

### Example Usage

For the *Smith v Jones* case, we can use the structured facts to generate comprehensive legal strategies:

```bash
./litassist.py brainstorm examples/case_facts.txt --side plaintiff --area family
```

**Output Example**:
```
--- Family Law Strategies for Plaintiff ---

## ORTHODOX STRATEGIES

1. Best Interests Argument
   Focus on how the relocation to Brisbane serves the best interests of the children under s60CC of the Family Law Act. Emphasize improved quality of life, educational opportunities, and financial security.
   Key legal principles: Family Law Act 1975 (Cth) s60CA, s60CC; MRR v GR [2010] HCA 4, https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/HCA/2010/4.html.

2. Children's Views Application
   Present evidence of 12-year-old Emily's expressed desire to remain in Brisbane, arguing her views should be given substantial weight due to her age and maturity.
   Key legal principles: Family Law Act 1975 (Cth) s60CC(3)(a); Bondelmonte v Bondelmonte [2017] HCA 8, https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/HCA/2017/8.html | https://jade.io/article/522221.

3. Equal Shared Parental Responsibility Retention
   Argue that relocation does not necessitate changing equal shared parental responsibility, as technological solutions enable joint decision-making despite distance.
   Key legal principles: Family Law Act 1975 (Cth) s61DA; Goode & Goode [2006] FamCA 1346, https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FamCA/2006/1346.html | https://jade.io/article/5859.

[continues with 7 more orthodox strategies...]

## UNORTHODOX STRATEGIES

1. "Digital Domicile" Argument
   Assert that children's established online relationships with friends and family in Sydney constitute a digital domicile that mitigates relocation impacts, as geographic moves are less disruptive in the digital age.
   Key legal principles: Morgan & Miles [2007] FamCA 1230, https://www.austlii.edu.au/cgi-bin/viewdoc/au/cases/cth/FamCA/2007/1230.html; emerging international jurisprudence on technology in family law.

2. Educational Innovation Metric
   Commission specialized educational assessment comparing teaching methodologies between Brisbane and Sydney schools, establishing that Brisbane schools offer pedagogical approaches uniquely beneficial for these specific children.
   Key legal principles: Rice v Asplund [1979] FamCA 84 (material change threshold); s60CC(3)(f) regarding educational needs.

[continues with 8 more unorthodox strategies...]

## MOST LIKELY TO SUCCEED

1. Best Interests Argument
   Provides the strongest foundation as courts consistently prioritize children's interests above all other considerations.

2. Meaningful Relationship Maintenance Plan
   Practical and cooperative approach demonstrating willingness to facilitate father's relationship, addressing the court's primary concerns.

3. Substantial & Significant Time Alternative
   Realistic proposal that acknowledges the father's rights while adapting to the reality of distance.

4. Expert Evidence Strategy
   Independent expert opinion carries significant weight, particularly if a family consultant supports the current arrangements.

5. Status Quo Continuation
   Courts are often reluctant to disrupt settled arrangements where children are thriving.
```

### Next in Pipeline

With comprehensive strategies generated, you can now use the `strategy` workflow to develop targeted legal options for achieving specific outcomes.

## Workflow 5: Strategy - Generate Legal Options

**Pipeline Phase**: Strategy

### Purpose

The `strategy` command analyzes case facts to generate strategic legal options, recommended actions, and draft documents tailored to achieving a specific outcome. It produces comprehensive analysis including probability assessments, critical hurdles, and prioritized next steps.

**Output**: All analysis saved to timestamped files: 
- `strategy_[outcome_slug]_YYYYMMDD_HHMMSS.txt` - Main strategic options and recommendations
- `strategy_[outcome_slug]_YYYYMMDD_HHMMSS_reasoning.txt` - Detailed legal reasoning traces for each option

### Command

```bash
./litassist.py strategy <case_facts_file> --outcome <desired_outcome> [--strategies <strategies_file>]
```

Required parameters:
- `--outcome`: A single sentence describing the desired outcome

Optional parameters:
- `--strategies`: Path to strategies.txt from brainstorm command. When provided, the command efficiently uses pre-analyzed "most likely to succeed" strategies, with intelligent gap-filling analysis only when needed

**Note:** This command includes automatic verification for accuracy - no additional flag needed. If you use the --verify flag, you'll see a warning that it's being ignored since verification is mandatory for strategic analysis.

**Intelligent Strategy Prioritization**: Strategy now efficiently uses brainstormed strategies as foundations for strategic options. When strategies.txt is provided:

- **If "most likely to succeed" strategies exist**: Uses them directly without re-analysis (maximum efficiency)
- **If insufficient "most likely" strategies**: Intelligently analyzes remaining strategies to fill gaps using Claude 3.5 Sonnet
- **If no "most likely" section**: Analyzes all available strategies and ranks them specifically for the desired outcome

This efficiency-first approach avoids duplicate analysis while ensuring brainstormed work directly feeds into strategic planning with intelligent gap-filling when needed.

**Quality Control ("Option B" Implementation)**: Strategy uses individual generation with immediate validation - each strategic option is generated and verified separately. Options with citation issues are immediately discarded rather than presented with warnings. This ensures users only see strategic options with verified citations, preventing professional liability risks from relying on options with known citation problems. Additionally, reasoning traces are saved to separate `*_reasoning.txt` files for transparency while keeping the main strategy file focused and actionable.

### Strict Format Requirements

The `strategy` command has strict input requirements:

**Required headings structure**:
The input file must contain EXACTLY these 10 headings in this order:

1. **Parties**
2. **Background** 
3. **Key Events**
4. **Legal Issues**
5. **Evidence Available**
6. **Opposing Arguments**
7. **Procedural History**
8. **Jurisdiction**
9. **Applicable Law**
10. **Client Objectives**

These headings must exactly match those created by the `extractfacts` command. The command performs strict validation and will fail with an error if any heading is missing or named differently.

**Required input format notes**:
- Validation explicitly checks for each heading ("Parties:", "Background:", etc.)
- Using different capitalization or wording will cause validation to fail
- Command will terminate with "Case facts file does not follow the required 10-heading structure" error if format requirements aren't met
- For example files showing the correct format, see `/examples/example_strategy_headers.txt`

**Processing mixed document sets**:
1. For multiple related documents (e.g., contract, financial statements, correspondence):
   - Process each document using `digest` first
   - Extract key information relevant to each heading
   - Manually create a consolidated `case_facts.txt` file
   - Ensure all 10 headings are present

**Benefits of rigid structure**:
- Enables structured data extraction (like legal issues extraction)
- Forces comprehensive analysis across all aspects
- Ensures consistent input for strategic analysis

**Limitations**:
- Less flexible for non-litigation contexts
- Requires preprocessing for non-standard documents
- May require manual reformatting

### Example Usage

For the *Smith v Jones* case, we can generate strategic options for specific litigation outcomes:

```bash
# Using case facts only
./litassist.py strategy examples/case_facts.txt --outcome "Secure interim orders allowing children to remain in Brisbane"

# Using case facts + brainstormed strategies (recommended workflow)
./litassist.py strategy examples/case_facts.txt --outcome "Secure interim orders allowing children to remain in Brisbane" --strategies strategies.txt
```

**When using --strategies option**: The command uses an efficiency-first approach:

**Scenario 1 - Complete "Most Likely" Available (Best Case)**:
```
📋 Using 3 pre-analyzed 'most likely to succeed' strategies
```
No additional analysis needed - maximum time and cost savings.

**Scenario 2 - Insufficient "Most Likely" (Smart Gap-Filling)**:
```
📋 Using 2 pre-analyzed 'most likely to succeed' strategies
🧠 Analyzing remaining 15 strategies to fill 2 slots...
📊 Intelligently selected 2 additional strategies
```
Minimal additional analysis to complete the strategic options.

**Scenario 3 - No "Most Likely" Section (Full Analysis)**:
```
🧠 No 'most likely' strategies found - analyzing 17 strategies for 'interim orders'...
📊 Selected top 4 strategies based on legal analysis
```
Comprehensive analysis only when pre-analysis isn't available.

**Output Example**:
```
# STRATEGIC OPTIONS FOR: SECURE INTERIM ORDERS ALLOWING CHILDREN TO REMAIN IN BRISBANE

## OPTION 1: Application for Continuation of Interim Arrangements
* **Probability of Success**: 75%

* **Principal Hurdles**:
  1. Overcoming presumption against changing established living arrangements — *Rice v Asplund (1979) FLC 90-725*
  2. Addressing father's contravention application regarding unauthorized relocation — *Family Law Act 1975 s70NAE*

* **Critical Missing Facts**:
  - Evidence of children's adjustment to Brisbane schools
  - Financial comparison of mother's earning capacity in each location


## OPTION 2: Urgent Application based on Best Interests
* **Probability of Success**: 70%

* **Principal Hurdles**:
  1. Establishing urgency justifying immediate determination — *Johns & Johns [2004] FamCA 348*
  2. Demonstrating material change in circumstances — *Goode & Goode [2006] FamCA 1346*

* **Critical Missing Facts**:
  - Expert evidence regarding children's psychological wellbeing
  - Documentation of father's capacity to maintain contact


# RECOMMENDED NEXT STEPS

1. Obtain urgent affidavit from children's school counselors regarding adjustment
2. File Form 4 Application for Interim Orders within 7 days
3. Arrange independent children's lawyer appointment per s68L
4. Commission family report focusing on relocation impact
5. Document all attempts to facilitate father's contact with children


# DRAFT APPLICATION

IN THE FEDERAL CIRCUIT AND FAMILY COURT OF AUSTRALIA
FAMILY LAW DIVISION

File No: SYD2025/0123

### APPLICATION FOR INTERIM PARENTING ORDERS

**BETWEEN:**
JENNIFER SMITH
Applicant

**AND:**
MICHAEL JONES
Respondent

The Applicant applies for the following orders:

1. That pending final determination of these proceedings, the children Emily Jones (born 15/05/2013) and Thomas Jones (born 22/09/2017) live with the Applicant in Brisbane, Queensland.

2. That the children spend time with the Respondent:
   (a) Each alternate weekend from Friday after school to Sunday 6pm;
   (b) For half of all school holiday periods;
   (c) By electronic communication at times agreed between the parties.

3. That the parties have equal shared parental responsibility for major long-term decisions concerning the children.

**GROUNDS:**

1. The children have resided in Brisbane since January 2025 and are enrolled in schools there.

2. The Applicant's employment in Brisbane provides significantly enhanced financial security for the children.

3. Both children have adjusted well to their new environment as evidenced by school reports and counselor assessments.

4. The proposed orders facilitate meaningful time between the children and the Respondent while providing stability in the children's primary residence.

5. The best interests of the children are served by maintaining their current living arrangements pending final determination.

**Filed:** [Date]
**Applicant's Solicitor:** [Details]
```

### Next in Pipeline

With strategic options identified, you can now create comprehensive legal documents using the `draft` workflow.

```mermaid
gantt
    title Smith v Jones Case Progression Timeline
    dateFormat YYYY-MM-DD
    
    section Research
    Lookup parental alienation law     :done, r1, 2025-05-01, 1d
    Lookup relocation precedents       :done, r2, 2025-05-02, 1d
    
    section Analysis
    Digest affidavit                   :done, a1, after r2, 2d
    Digest response                    :done, a2, after a1, 1d
    Extract structured facts           :done, a3, after a2, 1d
    
    section Strategy
    Brainstorm legal strategies        :done, s1, after a3, 2d
    Select winning arguments           :done, s2, after s1, 1d
    Generate strategic options         :done, s3, after s2, 2d
    Prepare draft application          :done, s4, after s3, 1d
    
    section Drafting
    Create submissions outline         :active, d1, after s4, 3d
    Final document preparation         :d2, after d1, 2d
```

## Workflow 6: Draft - Retrieval-Augmented Drafting

**Pipeline Phase**: Draft

### Purpose

The `draft` command creates well-supported legal drafts with intelligent document recognition and context building. It produces comprehensive legal documents by combining case facts, strategies, and supporting materials into persuasive, well-cited submissions.

### Document Processing Modes

**Small Files (Direct LLM Processing):**
- Text files (.txt) under 50,000 characters passed directly to LLM
- Provides complete context and comprehensive drafts
- **Recommended for case facts and strategies**

**Large Files (Embedding/Retrieval):**
- PDFs and large files processed through Pinecone RAG
- Extracts relevant passages using semantic search
- More limited context but handles large documents

### File Format Requirements

**CRITICAL: Use .txt extensions for structured documents**

```bash
# ✅ CORRECT - Direct processing, rich context
./litassist.py draft case_facts.txt strategies.txt "submissions"

# ❌ INCORRECT - Forces embedding/retrieval, limited context  
./litassist.py draft case_facts.md strategies.md "submissions"
```

**Why file extensions matter:**
- `.txt` files: Processed directly by LLM (full context)
- `.md` files: Forced into embedding/retrieval (snippets only)
- `.pdf` files: Always use embedding/retrieval (appropriate for large documents)

### Automatic Document Type Detection

- **Files named `case_facts.txt`** → Recognized as structured case facts
- **Files named `strategies.txt`** → Recognized as brainstormed legal strategies  
- **Files containing `"# Legal Strategies"` header** → Recognized as brainstorm output
- **Other text files** → Treated as supporting documents
- **PDFs and large files** → Use embedding/retrieval for relevant passages

### Smart Context Building

The command structures different document types with clear headers:
- `=== CASE FACTS ===` - Structured factual foundation
- `=== LEGAL STRATEGIES FROM BRAINSTORMING ===` - Strategic options and precedents
- `=== SUPPORTING DOCUMENT: filename ===` - Additional context
- `=== Retrieved Context ===` - Relevant passages from large documents

### Adaptive Prompting

System instructions change based on document types provided:
- **Case facts only**: Focus on factual foundation
- **Strategies only**: Consider strategic options marked as "most likely to succeed"
- **Both**: Use facts as foundation, incorporate strategic analysis
- **Supporting docs**: Additional context for comprehensive drafting

**Output**: All drafts saved to timestamped files: `draft_[query_slug]_YYYYMMDD_HHMMSS.txt`

**Citation Quality Control**: Draft outputs undergo comprehensive citation verification. Any unverifiable legal references are flagged with detailed warnings appended to the draft, including specific failure types and recommended actions. Auto-verification is triggered when content contains case citations, statutory references, or strong legal conclusions.

### Command

```bash
./litassist.py draft <document> [<document> ...] <query> [--diversity FLOAT] [--verify]
```

Arguments:
- `<document>`: One or more paths to knowledge base documents (PDF or text files)
  - Can combine multiple sources: `case_facts.txt strategies.txt`
  - Text files are passed entirely to the LLM
  - PDFs use embedding/retrieval for relevant chunks
- `<query>`: The legal topic or argument to draft (must be the last argument)

Options:
- `--diversity`: Control diversity of search results (0.0-1.0) - only applies to PDF/large file processing
- `--verify`: Optional AI verification to check citations, arguments, and compliance. Automatically triggered when content contains case citations, statutory references, percentage claims, or strong legal conclusions to ensure accuracy in high-stakes legal drafting (see [Using the --verify Switch](#using-the--verify-switch))

### Brainstorm vs Strategy Integration

**Understanding the difference between brainstorm and strategy outputs:**

| Aspect | Brainstorm Output | Strategy Output |
|--------|-------------------|-----------------|
| **Content Type** | Comprehensive legal strategies with citations | Strategic analysis + basic application |
| **Legal Foundation** | Rich precedents and principles for each strategy | Focused tactical recommendations |
| **Draft Integration** | Excellent for substantive legal writing | Provides planning context |
| **Auto-Recognition** | Contains `"# Legal Strategies"` header | Generic document format |
| **Best Use** | **Foundation for comprehensive drafts** | Tactical planning and simple applications |

### Recommended Integration Workflows

**Optimal Workflow (Brainstorm → Draft):**
```bash
# 1. Generate comprehensive strategies with legal foundations
./litassist.py brainstorm case_facts.txt --side plaintiff --area family

# 2. Use brainstorm output for rich legal drafting (automatically recognized)
./litassist.py draft case_facts.txt brainstorm_family_plaintiff_20250606_143022.txt "comprehensive outline of submissions"
```

**Alternative Workflow (Strategy → Draft):**
```bash
# 1. Generate tactical analysis for specific outcome
./litassist.py strategy case_facts.txt --outcome "secure interim orders"

# 2. Use strategy output as supporting document (requires manual integration)
./litassist.py draft case_facts.txt strategy_interim_orders_20250606_143022.txt "detailed submissions"
```

**Why brainstorm output is preferred for drafting:**
- **Richer legal citations**: Each strategy includes relevant precedents and principles
- **Multiple strategic angles**: Draft can weave together various approaches
- **Automatic recognition**: Integrates seamlessly as structured strategies
- **Comprehensive coverage**: 10 orthodox + 10 unorthodox + analysis provides depth

### Example Usage

For our *Smith v Jones* case, we can now draft a submission on the relocation issue using different input combinations:

```bash
# Using just the case facts (basic drafting)
./litassist.py draft case_facts.txt "outline of submissions regarding relocation of children in Smith v Jones"

# Using case facts + brainstorm output (RECOMMENDED - rich legal foundation)
./litassist.py draft case_facts.txt brainstorm_family_plaintiff_20250606_143022.txt "comprehensive outline of submissions"

# Using case facts + strategy output (tactical context)
./litassist.py draft case_facts.txt strategy_interim_orders_20250606_143022.txt "submissions for interim hearing"

# Using multiple sources including PDFs (comprehensive context)
./litassist.py draft case_facts.txt brainstorm_family_plaintiff_20250606_143022.txt examples/smith_bundle.pdf "comprehensive submission on relocation"
```

**File naming for optimal integration:**
```bash
# For automatic recognition, use these patterns:
cp brainstorm_family_plaintiff_20250606_143022.txt strategies.txt
./litassist.py draft case_facts.txt strategies.txt "submissions"

# Or use direct file references (brainstorm auto-recognized by header):
./litassist.py draft case_facts.txt brainstorm_family_plaintiff_20250606_143022.txt "submissions"
```

**Output Example**:
```
# OUTLINE OF SUBMISSIONS
## SMITH v JONES (SYD2025/0123)
### ISSUE OF RELOCATION OF CHILDREN

1. INTRODUCTION

1.1 These submissions are made on behalf of the Applicant mother, Ms. Jennifer Smith, who seeks final parenting orders permitting her and the children, Emily (12) and Thomas (8), to remain in Brisbane.

1.2 The relocation occurred in January 2025 due to Ms. Smith's acceptance of a senior position at Brisbane Children's Hospital, which represents a significant career advancement and provides enhanced financial security for the children.

2. LEGAL FRAMEWORK

2.1 The paramount consideration is the best interests of the children (s60CA, Family Law Act 1975).

2.2 As noted in MRR v GR [2010] HCA 4 at [15]: "a court cannot order a person to live in a particular place. But it can, consistent with the terms of the Act, frame parenting orders in a way which could have the practical effect of requiring a parent to reside in a particular location if that parent wishes to have the child reside with or spend time with him or her."

2.3 In Morgan & Miles [2007] FamCA 1230, the Court emphasized that relocation cases are not a separate category of case but must be determined according to the same principles as all parenting cases, with the best interests of the children as the paramount consideration.

3. PRIMARY CONSIDERATIONS (s60CC(2))

3.1 Benefit to children of meaningful relationship with both parents
...

[Content continues with well-structured legal arguments incorporating citations from the document]
```

### Troubleshooting Draft Quality Issues

**Problem: "Result file is barebones!" or limited content**

**Diagnosis: Check your CLI output for these indicators:**
```bash
Will use embedding/retrieval for case_facts.md    # ❌ Problem!
Will use embedding/retrieval for strategies.md    # ❌ Problem!
```

**Solution: File format correction**
```bash
# Convert to .txt for direct processing
cp case_facts.md case_facts.txt
cp strategies.md strategies.txt

# Re-run with proper extensions
./litassist.py draft case_facts.txt strategies.txt "comprehensive outline of submissions"
```

**Expected CLI output with correct setup:**
```bash
Using case_facts.txt as CASE FACTS (12,543 characters)      # ✅ Direct processing
Using strategies.txt as LEGAL STRATEGIES (8,932 characters) # ✅ Direct processing
```

**Why this matters:**
- **Direct processing**: Full document context, rich comprehensive drafts
- **Embedding/retrieval**: Limited snippets, basic skeletal drafts
- **File size check**: Files over 50,000 characters automatically use embedding regardless of extension

**Quick fixes for common issues:**
```bash
# Check file sizes
wc -c case_facts.md strategies.md

# If over 50KB, break into smaller files or use PDF processing
# If under 50KB, simply rename extensions:
mv case_facts.md case_facts.txt
mv strategies.md strategies.txt
```

### Advanced Usage Patterns

**Multi-stage drafting workflow:**
```bash
# Stage 1: Research and strategy
./litassist.py lookup "contract formation elements" --extract principles
./litassist.py brainstorm case_facts.txt --side plaintiff --area commercial

# Stage 2: Comprehensive drafting using research foundation
./litassist.py draft case_facts.txt brainstorm_commercial_plaintiff_*.txt "detailed contract dispute submissions"

# Stage 3: Tactical planning for specific outcomes
./litassist.py strategy case_facts.txt --outcome "summary judgment application" --strategies strategies.txt
```

**Document combination strategies:**
```bash
# Maximum context for complex matters
./litassist.py draft case_facts.txt strategies.txt expert_reports.pdf witness_statements.pdf "comprehensive submissions"

# Focused drafting for specific applications
./litassist.py draft case_facts.txt strategy_interim_orders_*.txt "urgent application for interim relief"
```


## Workflow 7: Test - API Connectivity Verification

**Pipeline Phase**: Utility

### Purpose

The `test` command verifies API connectivity with all external services used by LitAssist. It attempts to validate credentials for OpenAI, Pinecone, and Google CSE by making test API calls and reports success or failure for each service.

### Command

```bash
./litassist.py test
```

### Example Usage

Before beginning work on the *Smith v Jones* case, you can verify that all API connections are working properly:

```bash
./litassist.py test
```

**Output Example**:
```
Verifying API connections...
  - Testing OpenAI API... OK
  - Testing Pinecone API... OK
  - Testing Google CSE API... OK
All API connections verified.
```

This command is particularly useful when:
- Setting up LitAssist for the first time
- Troubleshooting connectivity issues
- After updating API keys in your config.yaml
- Before beginning important work to ensure all services are available

## End-to-End Pipeline Example

To demonstrate how these five workflows combine into a seamless end-to-end pipeline for the *Smith v Jones* case:

1. **Ingest (Lookup)**: Research legal frameworks for parental alienation and relocation cases in Australian family law.
   ```bash
   ./litassist.py lookup "What is the legal framework for determining parental alienation in Australian family court cases?"
   ./litassist.py lookup "What factors do Australian courts consider in relocation cases?" --mode broad
   ```

2. **Analyse (Digest)**: Process and analyze case documents to identify key issues and chronology.
   ```bash
   ./litassist.py digest examples/smith_affidavit.pdf --mode issues
   ./litassist.py digest examples/jones_response.pdf --mode summary
   ```

3. **Structure (ExtractFacts)**: Extract and organize case facts into a structured format.
   ```bash
   ./litassist.py extractfacts examples/smith_jones_file.pdf
   ```

4. **Brainstorm**: Generate comprehensive legal strategies tailored to party side and legal area.
   ```bash
   ./litassist.py brainstorm examples/case_facts.txt --side plaintiff --area family
   ```

5. **Strategy**: Generate targeted strategic options and draft documents for specific outcomes.
   ```bash
   ./litassist.py strategy examples/case_facts.txt --outcome "Secure interim orders allowing children to remain in Brisbane"
   ```

6. **Draft**: Create comprehensive legal submissions using brainstormed strategies and case facts.
   ```bash
   # RECOMMENDED: Use brainstorm output for rich legal foundation
   ./litassist.py draft case_facts.txt brainstorm_family_plaintiff_20250606_143022.txt "comprehensive outline of submissions"
   
   # Alternative: Basic drafting with just case facts
   ./litassist.py draft case_facts.txt "outline of submissions regarding relocation of children in Smith v Jones"
   
   # Or combine with original documents for maximum context
   ./litassist.py draft case_facts.txt brainstorm_family_plaintiff_20250606_143022.txt examples/smith_bundle.pdf "comprehensive submission on relocation"
   ```

## Conclusion

LitAssist streamlines legal workflows by automating research, analysis, and drafting processes. By following the end-to-end pipeline demonstrated in this guide, legal professionals can efficiently handle complex cases like *Smith v Jones* while ensuring thorough research, structured analysis, and well-supported legal arguments.

## Global Options

Options available for all commands:

```bash
./litassist.py [GLOBAL OPTIONS] <command> [ARGS] [OPTIONS]
```

- `--log-format [json|markdown]` - Set audit log format (default: json)
  - JSON format: Structured format for programmatic analysis
  - Markdown format: Human-readable format with clear sections
- `--verbose` - Enable detailed debug logging

## Using the --verify Switch

### Overview
The `--verify` switch is available for commands that generate substantive legal content. It runs a second AI model to critique and review the primary output, helping identify potential issues, gaps, or areas for improvement.

### Commands with --verify Support

| Command | Has --verify | Purpose of Verification |
|---------|--------------|------------------------|
| lookup | ❌ No | Simple search results don't need verification |
| digest | ❌ No | Summaries are straightforward factual extracts |
| extractfacts | ❌ No* | Automatic heavy verification enabled for foundational accuracy (**⚠️ warns if --verify used**) |
| brainstorm | ✅ Yes | Optional verification, auto-enabled for Grok models due to hallucination tendency |
| strategy | ❌ No* | Automatic heavy verification enabled for strategic accuracy (**⚠️ warns if --verify used**) |
| draft | ✅ Yes | Optional verification, auto-triggered for legal citations/references |

*Commands marked with * include automatic verification regardless of the flag and will warn users if they attempt to use --verify.

### Warning Messages

**When --verify flag is ignored:**
```bash
# strategy command with --verify flag
$ litassist strategy case_facts.txt --outcome "..." --verify
⚠️  Note: --verify flag ignored - strategy command always uses verification for accuracy

# extractfacts command with --verify flag  
$ litassist extractfacts document.pdf --verify
⚠️  Note: --verify flag ignored - extractfacts command always uses verification for accuracy
```

**When verification is auto-enabled:**
```bash
# brainstorm command (Grok models)
$ litassist brainstorm case_facts.txt --side plaintiff --area civil
ℹ️  Note: Verification auto-enabled for Grok models due to hallucination tendency

# strategy command (always enabled)
$ litassist strategy case_facts.txt --outcome "..."
ℹ️  Note: Strategy command automatically uses verification for accuracy
```

These warnings help users understand when their explicit --verify flags are being overridden versus when verification is automatically applied.

### When to Use --verify

**For commands that support --verify (brainstorm, draft):**

**Always use for:**
- 🏛️ Court filings and formal submissions (draft)
- 💡 Novel or high-risk legal strategies (brainstorm)
- 📄 Documents that will be relied upon by others
- 🎯 High-stakes matters with significant consequences

**Optional for:**
- 🔍 Initial research and exploration
- 📝 Early drafts and brainstorming
- 🔄 Iterative work where you'll manually review
- 💰 Cost-sensitive projects (verification doubles API costs)
- ⏱️ Time-critical tasks (adds 10-30+ seconds)

**Note:** Some commands (extractfacts, strategy) include automatic verification regardless of this flag.

### Automatic Verification Triggers

**Commands with automatic verification (always enabled):**
- `extractfacts` - Critical fact accuracy required for foundational documents
- `strategy` - High-stakes strategic recommendations require mandatory verification

**Commands with conditional auto-verification:**
- `brainstorm` - Automatically enabled when using Grok models due to hallucination tendencies
- `draft` - Automatically triggered when content contains:
  - Case citations (e.g., `[2020] HCA 5`, `Smith v Jones`)
  - Percentage claims (e.g., "75% likely", "90% chance")
  - Strong legal conclusions ("must", "cannot", "will")
  - Statutory references (e.g., "section 5", "s 42")
  - Court rules (e.g., "rule 15")
  - Paragraph references (e.g., "paragraph 12")

**Real-Time Citation Verification (All Commands):**
Beyond AI verification, all commands now include automatic citation verification that:
- Validates every legal citation against the AustLII database
- Flags problematic patterns (generic names, future dates, impossible citations)
- Provides specific error messages explaining failure types and actions taken
- Automatically regenerates content when possible (brainstorm) or provides clear warnings (other commands)

### Understanding Verification Results

#### extractfacts (automatic verification)
**Output location:** Appended to main output file after "VERIFICATION NOTES:"

**What it reviews:**
- Presence of all 10 required headings
- Completeness of information under each heading
- Factual consistency across sections
- Missing context or important details

**How to use results:**
1. Read the verification critique carefully
2. Open your `case_facts.txt` file
3. Add any missing information identified
4. Restructure sections if formatting issues noted
5. Cross-reference with source documents for gaps

**Example verification:**
```
VERIFICATION NOTES:
- "Key Dates" section missing specific filing deadlines mentioned in para 45
- "Remedy Sought" could include alternative relief options
- Consider adding witness availability to "Witnesses" section
```

#### brainstorm --verify (optional, auto for Grok)
**Output location:** Separate file `outputs/brainstorm_verification_[area]_[side]_[timestamp].txt`

**What it reviews:**
- Legal viability of proposed strategies
- Missing strategic angles
- Risk assessment of each approach
- Creative alternatives not considered
- Practical implementation challenges

**Citation Quality Control:** In addition to AI verification, brainstorm automatically:
- Validates all legal citations against AustLII database
- Regenerates only strategies with citation issues (selective regeneration)
- Preserves verified strategies unchanged
- Provides enhanced error messages for any remaining citation problems

**How to use results:**
1. Open both `brainstorm_*.txt` and `brainstorm_verification_*.txt` files in outputs/
2. Create or update your `strategies.txt` file
3. Incorporate suggested additional strategies
4. Add risk warnings for flagged approaches
4. Note implementation challenges for client discussions
5. All citation issues are automatically handled - no manual verification needed

**Example verification:**
```
VERIFICATION NOTES on Strategy #3:
- High risk of costs order if unsuccessful
- Consider protective costs order application first
- Alternative approach: seek leave for limited discovery
```

#### strategy (automatic verification)
**Output location:** End of main output file under "Strategic Legal Review" and separate reasoning file

**What it reviews:**
- Feasibility of recommended approaches
- Procedural requirements and timelines
- Missing precedents or authorities
- Cost-benefit analysis accuracy
- Alternative strategic options

**Citation Quality Control:** Strategy includes mandatory:
- Individual generation and validation of each strategic option
- Immediate discard of options with citation issues
- Detailed legal reasoning traces saved to separate `*_reasoning.txt` file
- Zero tolerance for unverified citations in strategic recommendations

**How to use results:**
1. Review verification notes before presenting to client
2. Research any additional authorities mentioned
3. Add procedural steps that were missed
4. Adjust probability assessments if warranted
5. Prepare responses to identified weaknesses
6. Consult reasoning file for detailed legal analysis behind each option

**Example verification:**
```
VERIFICATION NOTES:
- Interim injunction requires undertaking as to damages
- Consider defendant's likely cross-application
- Review recent Full Court authority in Chen v State [2024]
```

#### draft --verify (optional, auto-triggered for citations/statutory references)
**Output location:** Appended to draft after clear separator

**What it reviews:**
- Citation accuracy and relevance
- Argument structure and logic flow
- Persuasiveness and tone
- Missing authorities or precedents
- Compliance with court rules
- Australian legal writing conventions

**Citation Quality Control:** Draft includes comprehensive:
- Real-time validation of all legal citations against AustLII
- Enhanced error messages for unverifiable references
- Automatic flagging of problematic citation patterns
- Clear warnings appended to draft with specific failure types and actions

**How to use results:**
1. Treat as editorial review from senior counsel
2. Address any citation warnings immediately - these indicate real verification failures
3. Strengthen weak arguments identified
4. Add missing authorities to footnotes
5. Refine language and structure
6. Ensure compliance issues are addressed
7. Citation verification warnings require immediate attention before use

**Example verification:**
```
VERIFICATION NOTES:
- Para 12: Citation format should be (2019) 266 CLR 1, not [2019] HCA 23
- Para 18-20: Argument lacks transitional logic between negligence and causation
- Consider adding High Court authority on proportionality test
- Tone in para 31 may be too adversarial for interlocutory application
```

### Cost and Performance Impact

**For optional verification (brainstorm, draft):**

| Aspect | Without --verify | With --verify |
|--------|-----------------|---------------|
| API Calls | 1 | 2 |
| Cost | Base cost | ~2x base cost |
| Time | 5-15 seconds | 15-45 seconds |
| Output Files | 1 | 1-2 files |

**For strategy command with --strategies option:**

| Scenario | Analysis Calls | Cost Impact | Time Savings |
|----------|---------------|-------------|--------------|
| Complete "Most Likely" (3-4 strategies) | 0 additional | Minimal | Maximum |
| Insufficient "Most Likely" (1-2 strategies) | 1 partial analysis | ~25-50% of full | Significant |
| No "Most Likely" section | 1 full analysis | Full analysis cost | Moderate |

**Note:** Commands with automatic verification (extractfacts, strategy) always include verification costs, but strategy now minimizes duplicate analysis costs.

### Best Practices

1. **Development workflow:** Run without --verify during development, add it for final versions (brainstorm, draft)
2. **Collaborative review:** Share both main output and verification notes with colleagues
3. **Documentation:** Save verification results as part of your case file
4. **Iterative improvement:** Use verification feedback to refine your prompts and inputs
5. **Quality tracking:** Periodically run with --verify to monitor output quality (where optional)

### Important Notes

- **Not automatic corrections:** AI verification provides suggestions, not fixes
- **Human judgment required:** All suggestions must be evaluated by qualified counsel
- **Different models:** Verification often uses different AI models for diverse perspectives
- **No verification loops:** Running --verify multiple times on same content provides diminishing returns
- **Citation verification is automatic:** Real-time citation verification against AustLII runs on all commands regardless of --verify flag
- **Zero tolerance for bad citations:** Strategic commands (brainstorm, strategy) automatically regenerate or discard content with citation issues
- **Enhanced error messages:** Citation failures include specific explanations (e.g., "GENERIC CASE NAME", "FUTURE CITATION") and actions taken

## LLM Models and Parameter Configuration

### Model Selection by Command

Each LitAssist command uses a specific LLM model chosen for its strengths:

| Command | Generation Model | Analysis Model | Primary Purpose |
|---------|------------------|----------------|-----------------|
| lookup | `google/gemini-2.5-pro-preview` | N/A | Fast, accurate legal research |
| digest | `anthropic/claude-3-sonnet` | N/A | Reliable document summarization |
| extractfacts | `anthropic/claude-3-sonnet` | N/A | Precise fact extraction |
| brainstorm | `x-ai/grok-3-beta` | `anthropic/claude-3.5-sonnet` | Creative generation + expert analysis |
| strategy | `openai/gpt-4o` | `anthropic/claude-3.5-sonnet` | Strategic development + intelligent ranking |
| draft | `openai/gpt-4o` | N/A | Persuasive legal writing |

### Temperature and Sampling Parameters

LitAssist uses carefully tuned parameters for each command to balance accuracy with appropriate creativity:

#### Factual/Deterministic Commands

**lookup** (`google/gemini-2.5-pro-preview`):
```python
temperature=0, top_p=0.2
```
- **Purpose**: Case law search requires maximum accuracy
- **Effect**: Near-deterministic responses with minimal variation
- **Why**: Legal citations and case summaries must be consistent

**extractfacts** (`anthropic/claude-3-sonnet`):
```python
temperature=0, top_p=0.15
```
- **Purpose**: Structured fact extraction demands precision
- **Effect**: Highly deterministic with virtually no randomness
- **Why**: Facts must be extracted consistently across runs

**digest - Summary Mode** (`anthropic/claude-3-sonnet`):
```python
temperature=0, top_p=0
```
- **Purpose**: Chronological summaries need complete consistency
- **Effect**: Fully deterministic output
- **Why**: Document summaries should not vary between runs

#### Analytical Commands

**digest - Issues Mode** (`anthropic/claude-3-sonnet`):
```python
temperature=0.2, top_p=0.5
```
- **Purpose**: Issue-spotting benefits from slight variation
- **Effect**: Mostly consistent with minor creative elements
- **Why**: Different perspectives can reveal different issues

**strategy** (`openai/gpt-4o` for generation, `anthropic/claude-3.5-sonnet` for analysis):
```python
# Generation: temperature=0.2, top_p=0.9, presence_penalty=0.0, frequency_penalty=0.0
# Analysis: temperature=0.2, top_p=0.8
```
- **Generation Purpose**: Create detailed strategic options with reliability and insight
- **Analysis Purpose**: Intelligent ranking of brainstormed strategies for specific outcomes
- **Why**: Combines strategic development with expert strategy prioritization

#### Creative Commands

**draft** (`openai/gpt-4o`):
```python
temperature=0.5, top_p=0.8, presence_penalty=0.1, frequency_penalty=0.1
```
- **Purpose**: Persuasive writing requires eloquence
- **Effect**: Balanced creativity with coherent arguments
- **Why**: Legal drafts need varied language while maintaining precision
- **Penalties**: Reduce repetitive phrases and improve readability

**brainstorm** (`x-ai/grok-3-beta` for generation, `anthropic/claude-3.5-sonnet` for analysis):
```python
# Generation: temperature=0.9, top_p=0.95
# Analysis: temperature=0.2, top_p=0.8
```
- **Generation Purpose**: Generate novel and unorthodox strategies with high creativity
- **Analysis Purpose**: Expert evaluation of "most likely to succeed" strategies
- **Why**: Combines creative ideation with consistent legal analysis

#### Verification Parameters

All models when used for `--verify`:
```python
temperature=0, top_p=0.2
```
- **Purpose**: Critique and error-checking must be consistent
- **Effect**: Deterministic verification results
- **Why**: Verification feedback should not vary

### Understanding the Parameters

**temperature** (0.0 to 1.0+):
- Controls randomness in token selection
- 0 = deterministic (always pick most likely token)
- 0.5 = balanced creativity
- 1.0+ = high creativity/randomness

**top_p** (0.0 to 1.0):
- Controls nucleus sampling (cumulative probability)
- 0.1 = only most likely tokens
- 0.5 = moderate token variety
- 0.95 = wide token selection

**presence_penalty** (-2.0 to 2.0):
- Penalizes tokens based on presence in text
- Positive values reduce repetition of ideas
- Used in drafting to improve variety

**frequency_penalty** (-2.0 to 2.0):
- Penalizes tokens based on frequency
- Positive values reduce word repetition
- Used in drafting for better flow

### Token Limits

When `use_token_limits: false` (default), models use their default token limits (typically 4096+).

When `use_token_limits: true` in the `llm` section of config.yaml, LitAssist applies conservative token limits:

| Model | Completion Tokens | Verification Tokens |
|-------|-------------------|---------------------|
| `google/gemini-*` | 2048 | 1024 |
| `anthropic/claude-*` | 4096 | 1536 |
| `openai/gpt-4*` | 3072 | 1024 |
| `x-ai/grok-*` | 1536 | 800 |
| Others | 2048 | 1024 |

These limits balance comprehensive responses with model reliability and cost control.

**Note**: Token limits are not directly configurable. You can only enable/disable the conservative limits via `use_token_limits`. Custom token limits would require modifying the source code.

### Document Chunking vs Token Limits

LitAssist has two separate systems for managing text size:

#### 1. Document Chunking (Input Processing)

Controls how large documents are split before sending to the AI:

```yaml
general:
  max_chars: 20000       # For digest/extractfacts (default: 20000 ≈ 4000 words)
  rag_max_chars: 8000    # For draft embeddings (default: 8000 ≈ 1600 words)
```

**When documents exceed these limits:**
- `digest`: Processes each chunk separately, then combines results
- `extractfacts`: Analyzes chunks sequentially to build complete fact list
- `draft`: Creates separate embeddings for each chunk in Pinecone

**Example with 100-page PDF:**
- With `max_chars: 20000`: Creates ~15-20 chunks
- With `max_chars: 10000`: Creates ~30-40 chunks (more API calls, more focused processing)

#### 2. Token Limits (Output Generation)

Controls how much text the AI can generate in responses:

```yaml
llm:
  use_token_limits: false    # Default: let models use their natural limits
```

- `false`: Models use their default limits (usually 4096+ tokens)
- `true`: Applies conservative limits (1536-4096 tokens depending on model)

**Key differences:**
| Aspect | Document Chunking | Token Limits |
|--------|------------------|--------------|
| **Purpose** | Split large inputs | Control output length |
| **Units** | Characters (≈ 5 chars/word) | Tokens (≈ 1.3 tokens/word) |
| **Applies to** | Documents being processed | AI responses |
| **Config location** | `general` section | `llm` section |
| **Customizable** | Yes, via config | Only on/off via config |

### When to Adjust These Settings

**Document Chunking (`max_chars`, `rag_max_chars`):**
- **Decrease** (e.g., 10000) if documents have distinct sections that shouldn't be mixed
- **Increase** (e.g., 40000) if documents have long continuous narratives
- **Trade-off**: Smaller chunks = more API calls but more focused analysis

**Token Limits (`use_token_limits`):**
- **Enable** (`true`) if responses are too verbose or meandering
- **Disable** (`false`) if you need comprehensive, detailed outputs
- **Trade-off**: Limited tokens = concise but potentially incomplete responses

### Customization Notes

While LitAssist's parameters are optimized for legal work, advanced users can:
1. Modify parameters in the source code for different use cases
2. Enable/disable token limits via `use_token_limits` in config.yaml
3. Adjust document chunking via `max_chars` and `rag_max_chars` in config.yaml
4. Use different models by changing model strings (requires API support)

**Warning**: Changing parameters may significantly affect output quality and consistency. The default values represent extensive testing for Australian legal contexts.

## Testing with Mock Mode

When using placeholder API keys in your config.yaml file:
- Some commands will enter mock mode automatically
- This allows testing the CLI without active API subscriptions
- Mock mode provides sample responses to demonstrate functionality:
  - `lookup`: Returns sample AustLII results
  - `digest`: Uses local test document processing
  - `brainstorm`: Generates theoretical strategies
  - Other commands will indicate they require valid credentials

To exit mock mode, update config.yaml with valid API keys.

## Audit Logging

All command executions are logged for audit purposes:
- Logs stored in `logs/` directory
- Format: `logs/<command>_YYYYMMDD-HHMMSS.{json|md}`
- Contents include metadata, inputs, prompts, responses, and token usage
- Logs contain sensitive data - ensure proper access controls and encryption at rest

## Legal Disclaimer

All outputs from LitAssist are draft documents only and must be reviewed by qualified legal counsel before use in formal proceedings.
