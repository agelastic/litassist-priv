# Counsel's Notes Command Guide

**Last Updated**: October 12, 2025

The `counselnotes` command provides strategic analysis and tactical insights for legal documents from an advocate's perspective, complementing the neutral analysis provided by the `digest` command.

## Overview

Unlike the `digest` command which provides factual, neutral analysis, `counselnotes` offers:
- **Strategic perspective** from an advocate's viewpoint
- **Risk assessment** and tactical opportunities
- **Settlement considerations** and procedural advantages
- **Structured extraction** of citations, principles, and action items
- **Cross-document synthesis** for comprehensive case analysis

## Quick Start

### Basic Strategic Analysis
```bash
# Analyse a single document strategically
litassist counselnotes contract.pdf

# Analyse multiple documents with cross-synthesis
litassist counselnotes brief.pdf affidavit.pdf response.pdf

# Include citation verification
litassist counselnotes --verify case_bundle.pdf
```

### Structured Data Extraction
```bash
# Extract all structured elements as JSON
litassist counselnotes --extract all case_files.pdf

# Extract only citations
litassist counselnotes --extract citations pleadings.pdf

# Extract legal principles with authorities
litassist counselnotes --extract principles judgment.pdf

# Extract tactical checklist
litassist counselnotes --extract checklist case_docs.pdf
```

## Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--extract` | Extract structured data in JSON format | `--extract all` |
| `--verify` | Enable citation verification | `--verify` |

### Extraction Modes

#### `--extract all`
Extracts comprehensive strategic information in JSON format:
```json
{
  "strategic_summary": "Brief overview of case position and opportunities",
  "key_citations": ["Case v Name [2023] HCA 1", "Legislation Act 1987 (NSW)"],
  "legal_principles": [
    {
      "principle": "Contract formation requires consideration",
      "authority": "Smith v Jones [2023] HCA 1"
    }
  ],
  "tactical_checklist": [
    "Review witness statements for consistency",
    "Prepare comprehensive discovery plan"
  ],
  "risk_assessment": "Assessment of litigation risks and mitigation strategies",
  "recommendations": [
    "Proceed with settlement negotiations",
    "Consider summary judgment application"
  ]
}
```

#### `--extract citations`
Extracts only legal authorities:
```json
{
  "citations": [
    "Commonwealth v Tasmania [1983] HCA 21",
    "Contract Law Act 1987 (NSW) s 42",
    "Federal Court Rules 2011 (Cth) r 26.01"
  ]
}
```

#### `--extract principles`
Extracts legal principles with supporting authorities:
```json
{
  "principles": [
    {
      "principle": "Good faith obligation in contract performance",
      "authority": "Renard Constructions v Minister for Public Works [1992] HCA 19"
    }
  ]
}
```

#### `--extract checklist`
Creates actionable tactical checklist:
```json
{
  "checklist": [
    "Verify all witness statements are consistent with pleadings",
    "Prepare discovery plan within 14 days of directions",
    "Assess prospects for summary judgment application",
    "Consider timing for mediation referral"
  ]
}
```

## Strategic Analysis Framework

The `counselnotes` command analyses documents using a structured framework:

### 1. Case Overview & Position
- Overall case strength assessment
- Client's strategic position
- Key factual advantages and disadvantages

### 2. Tactical Opportunities
- Procedural advantages to exploit
- Evidence strengths to emphasise
- Opposing party vulnerabilities
- Settlement leverage points

### 3. Risk Assessment
- Litigation risks and exposure
- Evidence gaps or weaknesses
- Potential adverse findings
- Cost-benefit considerations

### 4. Strategic Recommendations
- Recommended litigation approach
- Priority actions and next steps
- Resource allocation priorities
- Alternative dispute resolution considerations

### 5. Case Management Notes
- Key deadlines and milestones
- Witness considerations
- Expert evidence requirements
- Discovery/disclosure strategy

## Workflow Integration

### Typical Litigation Workflow
```bash
# 1. Initial document analysis (neutral)
litassist digest case_files.pdf

# 2. Strategic analysis (advocate perspective)
litassist counselnotes --extract all case_files.pdf

# 3. Generate strategic options
litassist strategy case_facts.txt

# 4. Draft legal documents
litassist draft case_facts.txt "statement of claim"
```

### Cross-Document Synthesis
When processing multiple documents, `counselnotes` automatically:
- Identifies common themes and issues across documents
- Synthesises strategic opportunities from combined evidence
- Highlights contradictions or gaps between documents
- Provides unified tactical recommendations

## Use Cases

### 1. Initial Case Assessment
```bash
# Analyse initial brief and supporting documents
litassist counselnotes --extract all brief.pdf exhibits.pdf
```
**Output**: Comprehensive strategic overview with risk assessment and recommendations.

### 2. Pre-Trial Preparation
```bash
# Extract tactical checklist for trial preparation
litassist counselnotes --extract checklist --verify witness_statements.pdf expert_reports.pdf
```
**Output**: Actionable checklist with citation verification for accuracy.

### 3. Settlement Preparation
```bash
# Strategic analysis for settlement negotiations
litassist counselnotes correspondence.pdf valuations.pdf
```
**Output**: Strategic analysis focused on settlement leverage and risks.

### 4. Appeal Preparation
```bash
# Extract legal principles for appeal grounds
litassist counselnotes --extract principles --verify judgment.pdf trial_transcripts.pdf
```
**Output**: Legal principles with authorities for appeal arguments.

## Best Practices

### Document Preparation
- **Ensure document quality**: Use clear, searchable PDFs or well-formatted text files
- **Include all relevant materials**: Combine related documents for better synthesis
- **Organise chronologically**: Present documents in logical sequence

### Strategic Analysis
- **Compare with digest output**: Use `counselnotes` alongside `digest` for complete perspective
- **Verify citations**: Always use `--verify` flag for documents citing legal authorities
- **Cross-reference recommendations**: Check strategic advice against available evidence

### Output Management
- **Use descriptive filenames**: Outputs are automatically timestamped for organization
- **Archive analysis**: Keep strategic analysis separate from factual digest
- **Track changes**: Re-run analysis as new documents become available

## Integration with Other Commands

### Complementary Commands
- **`digest`**: Provides neutral factual analysis to complement strategic perspective
- **`extractfacts`**: Generates structured case facts for further analysis
- **`strategy`**: Uses strategic insights to generate specific tactical options
- **`draft`**: Incorporates strategic analysis into document drafting
- **`verify`**: Validates citations and legal reasoning in outputs

### Workflow Examples

#### Complete Case Analysis
```bash
# Step 1: Extract structured facts
litassist extractfacts case_materials.pdf

# Step 2: Strategic analysis
litassist counselnotes --extract all case_materials.pdf

# Step 3: Generate strategy options
litassist strategy case_facts.txt --outcome "summary judgment"

# Step 4: Draft pleadings
litassist draft case_facts.txt "statement of claim"
```

#### Document Review Workflow
```bash
# Step 1: Neutral digest
litassist digest --mode issues opposing_brief.pdf

# Step 2: Strategic response analysis
litassist counselnotes --verify opposing_brief.pdf

# Step 3: Extract tactical opportunities
litassist counselnotes --extract checklist opposing_brief.pdf
```

## Comparison: Counselnotes vs Digest

| Aspect | Digest (Neutral) | Counselnotes (Strategic) |
|--------|------------------|--------------------------|
| **Perspective** | Objective, factual | Advocate, tactical |
| **Purpose** | Document understanding | Strategic planning |
| **Output Focus** | Chronology and issues | Opportunities and risks |
| **Best For** | Initial review | Case strategy development |
| **Client Use** | Background briefing | Strategic discussions |
| **Integration** | Facts → Strategy | Analysis → Tactics |

## Troubleshooting

### Common Issues

#### Large Document Processing
**Issue**: Documents too large for processing
**Solution**: 
- Break large documents into logical sections
- Use multiple `counselnotes` commands for different document sets
- Ensure documents are under file size limits

#### Citation Verification Failures
**Issue**: Citations marked as invalid during verification
**Solution**:
- Review document OCR quality
- Check citation format against Australian legal citation standards
- Use `--verify` flag selectively for documents with known good citations

#### Inconsistent Strategic Analysis
**Issue**: Strategic advice seems contradictory
**Solution**:
- Review input documents for completeness
- Ensure all relevant materials are included
- Compare with `digest` output for factual consistency

### Performance Considerations
- **Processing time**: Strategic analysis takes longer than basic digest
- **Token usage**: Complex analysis may consume more API tokens
- **Memory usage**: Multiple large documents require sufficient system memory

## Australian Legal Context

The `counselnotes` command is specifically designed for Australian legal practice:

### Legal Framework Compliance
- **Citation formats**: Recognises Australian case law and legislation citation patterns
- **Court procedures**: Considers Australian court rules and practice directions
- **Legal principles**: Applies Australian legal concepts and terminology
- **Jurisdictional considerations**: Accounts for federal and state court differences

### Professional Standards
- **Ethical compliance**: Analysis maintains Australian legal professional standards
- **Confidentiality**: Respects client privilege and confidentiality requirements
- **Quality assurance**: Outputs require qualified legal counsel review before use
- **Audit trails**: Maintains comprehensive logging for professional accountability

### Practice Area Integration
- **Commercial law**: Contract disputes, corporate matters, insolvency
- **Litigation**: Civil proceedings, appeals, interlocutory applications
- **Family law**: Parenting disputes, property settlements, domestic violence
- **Criminal law**: Summary and indictable offences, appeals, sentencing
- **Administrative law**: Judicial review, tribunal proceedings, regulatory matters

## Output Files and Management

### File Naming Convention
- **Strategic Analysis**: `counselnotes_strategic_YYYYMMDD_HHMMSS.txt`
- **JSON Extractions**: `counselnotes_[mode]_YYYYMMDD_HHMMSS.json`
- **Verification Reports**: `counselnotes_verification_YYYYMMDD_HHMMSS.txt`

### File Organization
```
matter_directory/
├── documents/
│   ├── brief.pdf
│   ├── affidavit.pdf
│   └── correspondence.pdf
├── outputs/
│   ├── counselnotes_strategic_20250107_143022.txt
│   ├── counselnotes_all_20250107_143156.json
│   └── counselnotes_checklist_20250107_143340.json
└── logs/
    └── counselnotes_20250107-143022.md
```

### Integration with Case Management
- **Export capabilities**: JSON outputs integrate with practice management systems
- **Version control**: Timestamped files enable historical comparison
- **Team collaboration**: Structured outputs facilitate team review and discussion
- **Client reporting**: Strategic summaries suitable for client communication

## Advanced Features

### Multi-Document Analysis
When processing multiple documents, the command performs:
- **Cross-referencing**: Identifies connections between different documents
- **Synthesis**: Combines insights from multiple sources
- **Gap analysis**: Identifies missing information or evidence
- **Conflict detection**: Highlights contradictory information

### Citation Quality Control
Comprehensive citation verification includes:
- **Pattern validation**: Detects generic or suspicious case names
- **Online verification**: Real-time checking against AustLII database
- **International recognition**: Identifies UK, US, and other international citations
- **Format compliance**: Ensures Australian citation standards

### Customization Options
Advanced users can:
- **Customize prompts**: Modify analysis templates for specific practice areas
- **Batch processing**: Process multiple matters efficiently
- **Integration APIs**: Connect with external case management systems
- **Reporting templates**: Create standardized output formats

### Model Configuration
The `counselnotes` command uses a preconfigured LLM setup optimized for strategic legal analysis:
- **Model**: `openai/o3-pro` for advanced reasoning and strategic analysis
- **Reasoning Effort**: `high` for comprehensive strategic insights
- **Max Completion Tokens**: `8192` for detailed multi-section output
- **Verification**: Enabled for automatic citation verification and legal accountability

**October 2025 Update**: Upgraded to o3-pro for superior strategic reasoning capabilities, enabling deeper tactical analysis and more sophisticated case assessments. This configuration requires BYOK (Bring Your Own Key) setup through OpenRouter.

## Support and Resources

### Example Files
- `examples/example_counselnotes_output.txt`: Complete strategic analysis sample
- `examples/example_counselnotes_extractions.json`: All extraction mode examples

### Technical Documentation
- `docs/counselnotes/COUNSELNOTES_IMPLEMENTATION.md`: Technical implementation details
- Integration patterns and customization guidance

### Getting Help
- Use `litassist counselnotes --help` for command-specific guidance
- Review example outputs for expected format and content
- Consult technical documentation for advanced configuration options

---

*The `counselnotes` command provides sophisticated strategic analysis capabilities while maintaining the professional standards required for Australian legal practice. All outputs are draft analysis requiring qualified legal counsel review before use in formal proceedings.*
