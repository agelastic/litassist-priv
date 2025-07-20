---
layout: default
title: User Guide
permalink: /guide/
---

# User Guide

Welcome to the LitAssist User Guide. This comprehensive guide will help you master all aspects of LitAssist for your legal practice.

## Quick Start

New to LitAssist? Start here:

1. **[Installation Guide](/installation)** - Get LitAssist up and running
2. **[Your First Case Plan](#your-first-case-plan)** - Create your first workflow
3. **[Command Overview](#command-overview)** - Understand available commands

## Your First Case Plan

The `caseplan` command is your starting point for any litigation matter:

```bash
# Create a basic case facts file
echo "Client: John Smith
Defendant: ABC Corporation
Issue: Breach of contract
Amount claimed: $50,000" > case_facts.txt

# Generate a case plan
litassist caseplan case_facts.txt --budget standard

# Execute the generated workflow
bash caseplan_commands_standard.txt
```

## Command Overview

### Research & Analysis
- **[lookup](#lookup)** - Legal research and case law
- **[digest](#digest)** - Document summarization
- **[extractfacts](#extractfacts)** - Fact extraction

### Strategy & Planning
- **[brainstorm](#brainstorm)** - Strategy generation
- **[strategy](#strategy)** - Strategic analysis
- **[counselnotes](#counselnotes)** - Advocate analysis

### Document Generation
- **[draft](#draft)** - Legal document drafting
- **[barbrief](#barbrief)** - Barrister's briefs

## Detailed Command Guides

### Lookup
Research case law and legal principles with AI-powered analysis.

```bash
# Basic search
litassist lookup "negligence duty of care"

# Comprehensive analysis
litassist lookup "vicarious liability employees" --comprehensive
```

**Tips:**
- Use specific legal terms for better results
- Include jurisdiction when relevant
- Enable comprehensive mode for detailed analysis

### Digest
Process large documents into structured summaries.

```bash
# Chronological summary
litassist digest contract.pdf --mode summary

# Issue spotting
litassist digest witness_statements.pdf --mode issues --context "credibility"
```

**Supported formats:** PDF, DOCX, TXT

### ExtractFacts
Convert unstructured documents into structured case facts.

```bash
# Extract with verification
litassist extractfacts client_interview.pdf --verify

# Custom output location
litassist extractfacts documents/*.pdf --output my_case_facts.txt
```

### Brainstorm
Generate creative legal strategies and arguments.

```bash
# Both orthodox and unorthodox strategies
litassist brainstorm --facts case_facts.txt --mode both

# Focus on unorthodox approaches
litassist brainstorm --facts case_facts.txt --mode unorthodox
```

### Strategy
Develop comprehensive legal strategies with probability assessments.

```bash
# High-effort strategic analysis
litassist strategy --facts case_facts.txt --reasoning-effort high

# Build on brainstorm results
litassist strategy --facts case_facts.txt --brainstorm-file brainstorm_output.md
```

### Draft
Create professional legal documents with proper citations.

```bash
# Draft an affidavit
litassist draft --type affidavit --facts case_facts.txt --verify

# Custom instructions
litassist draft --type statement_of_claim --facts case_facts.txt \
  --instructions "Focus on breach of fiduciary duty"
```

**Available document types:**
- statement_of_claim
- defence
- affidavit
- witness_statement
- outline_of_submissions
- notice_of_motion

### CounselNotes
Strategic analysis for barristers and advocates.

```bash
# Analyze legal opinion
litassist counselnotes senior_counsel_advice.pdf --extract

# Custom output directory
litassist counselnotes brief.pdf --extract --output-dir ./counsel_analysis/
```

### BarBrief
Comprehensive barrister's briefs for litigation.

```bash
# Summary judgment application
litassist barbrief --case-name "Smith v Jones" \
  --facts case_facts.txt \
  --hearing-type "summary judgment" \
  --documents ./evidence/*.pdf
```

## Workflows

### Complete Litigation Workflow

```bash
# 1. Start with case planning
litassist caseplan initial_facts.txt --budget comprehensive

# 2. Research relevant law
litassist lookup "contract breach remedies" --comprehensive

# 3. Process evidence
litassist digest evidence/*.pdf --mode issues

# 4. Extract structured facts
litassist extractfacts witness_statements/*.pdf

# 5. Generate strategies
litassist brainstorm --facts case_facts_extracted.txt

# 6. Develop approach
litassist strategy --facts case_facts_extracted.txt

# 7. Draft documents
litassist draft --type statement_of_claim --facts case_facts_extracted.txt
```

### Quick Advisory Workflow

```bash
# 1. Digest client documents
litassist digest client_contract.pdf --mode summary

# 2. Research specific issue
litassist lookup "frustration of contract COVID-19"

# 3. Generate advice structure
litassist counselnotes research_output.md
```

## Best Practices

### File Organization
```
case_folder/
├── facts/
│   ├── case_facts.txt
│   └── extracted_facts.txt
├── documents/
│   ├── contracts/
│   └── correspondence/
├── research/
│   └── lookup_results.md
├── strategy/
│   ├── brainstorm_output.md
│   └── strategy_analysis.md
└── drafts/
    └── statement_of_claim_draft.md
```

### Version Control
- Use git for tracking changes
- Commit after each major step
- Tag important milestones

### Quality Assurance
- Always use `--verify` for final documents
- Review AI-generated content
- Validate citations independently
- Keep audit logs of all commands

## Advanced Usage

### Custom Prompts
```bash
# Use custom context
litassist digest document.pdf --context "Focus on limitation periods and notice requirements"

# Detailed instructions
litassist draft --type affidavit --facts case_facts.txt \
  --instructions "Emphasize timeline discrepancies, include exhibit references"
```

### Batch Processing
```bash
# Process multiple documents
for file in documents/*.pdf; do
  litassist digest "$file" --mode summary
done

# Extract facts from all witness statements
litassist extractfacts witness_statements/*.pdf --output combined_facts.txt
```

### Integration
```bash
# Export to JSON for integration
litassist lookup "negligence" --output-format json > results.json

# Pipeline commands
litassist digest contract.pdf | litassist extractfacts - > facts.txt
```

## Troubleshooting

### Common Issues

**API Timeouts**
- Reduce document size
- Use `--reasoning-effort low` for faster results
- Check internet connection

**Citation Verification Failures**
- Ensure Google CSE is configured for Jade.io
- Check daily API limits
- Use `--no-verify` for drafts

**Memory Issues**
- Process large documents in chunks
- Close other applications
- Increase system swap space

## Full Documentation

For complete documentation, see:
- **[Comprehensive User Guide](https://github.com/litassist/litassist/blob/main/docs/user/LitAssist_User_Guide.md)**
- **[API Reference](/api)**
- **[Examples](/examples)**

## Getting Help

- **GitHub Issues**: [Report bugs or request features](https://github.com/litassist/litassist/issues)
- **Email Support**: support@litassist.io
- **Community**: Join our discussion forum