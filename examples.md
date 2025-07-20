---
layout: default
title: Examples
permalink: /examples/
---

# Examples

Real-world examples of using LitAssist in legal practice.

## Contract Dispute Case

### Scenario
Your client claims breach of a supply contract. The defendant alleges frustration due to COVID-19.

### Workflow

```bash
# 1. Create initial case facts
cat > case_facts.txt << EOF
Client: ABC Manufacturing Pty Ltd
Defendant: XYZ Supplies Limited
Contract: Supply Agreement dated 1 March 2020
Issue: Non-delivery of goods worth $500,000
Defence: Frustration due to COVID-19 restrictions
Jurisdiction: Supreme Court of Victoria
EOF

# 2. Generate case plan
litassist caseplan case_facts.txt --budget standard

# 3. Research frustration doctrine
litassist lookup "frustration of contract COVID-19 Victoria" --comprehensive

# 4. Analyze the contract
litassist digest supply_agreement.pdf --mode issues \
  --context "force majeure, frustration, pandemic"

# 5. Process correspondence
litassist digest correspondence/*.pdf --mode summary

# 6. Extract all facts
litassist extractfacts all_documents/*.pdf --verify

# 7. Generate strategies
litassist brainstorm --facts case_facts_extracted.txt --mode both

# 8. Develop approach
litassist strategy --facts case_facts_extracted.txt --reasoning-effort high

# 9. Draft statement of claim
litassist draft --type statement_of_claim --facts case_facts_extracted.txt \
  --instructions "Focus on: 1) No force majeure clause, 2) Defendant's continued operations, 3) Selective performance" \
  --verify
```

### Key Outputs
- Comprehensive research on COVID-19 frustration cases
- Identified weakness in defendant's frustration argument
- Strategic approach emphasizing selective performance
- Professional statement of claim with verified citations

## Employment Dispute

### Scenario
Executive termination with restraint of trade issues.

### Workflow

```bash
# 1. Initial assessment
litassist digest employment_contract.pdf --mode issues \
  --context "termination clauses, restraints, garden leave"

# 2. Research restraints
litassist lookup "restraint of trade employment executive NSW reasonableness" \
  --comprehensive

# 3. Extract facts from termination letter
litassist extractfacts termination_letter.pdf dismissal_meeting_notes.pdf

# 4. Counsel's opinion
litassist counselnotes senior_counsel_advice.pdf --extract

# 5. Urgent injunction brief
litassist barbrief \
  --case-name "Smith v TechCorp Pty Ltd" \
  --facts case_facts.txt \
  --hearing-type "urgent injunction" \
  --context "Seeking to restrain enforcement of 12-month non-compete" \
  --documents ./evidence/*.pdf \
  --verify
```

## Personal Injury Claim

### Scenario
Workplace injury with complex liability issues.

### Workflow

```bash
# 1. Process medical reports
for report in medical_reports/*.pdf; do
  litassist digest "$report" --mode summary
done

# 2. Extract injury details
litassist extractfacts medical_reports/*.pdf \
  --output injury_timeline.txt

# 3. Research similar cases
litassist lookup "workplace injury machine guarding duty of care" \
  --comprehensive

# 4. Analyze incident reports
litassist digest incident_report.pdf witness_statements.pdf \
  --mode issues --context "safety procedures, training, supervision"

# 5. Strategic planning
litassist brainstorm --facts injury_timeline.txt --mode orthodox

# 6. Draft affidavit
litassist draft --type affidavit --facts injury_timeline.txt \
  --instructions "First person perspective, chronological order, emphasis on safety breaches"
```

## Family Law Property Settlement

### Scenario
High net worth property settlement with complex asset structures.

### Workflow

```bash
# 1. Asset analysis
litassist digest financial_statements/*.pdf --mode summary \
  --context "asset values, liabilities, corporate structures"

# 2. Case law research
litassist lookup "family law property settlement trust assets corporate veil"

# 3. Extract financial facts
litassist extractfacts accountant_report.pdf valuation_reports.pdf

# 4. Strategy development
litassist strategy --facts financial_facts.txt \
  --brainstorm-file property_strategies.md \
  --reasoning-effort high

# 5. Draft outline of argument
litassist draft --type outline_of_submissions \
  --facts financial_facts.txt \
  --instructions "Four pools approach, emphasis on non-financial contributions"
```

## Criminal Defence Brief

### Scenario
Assault charge with self-defence claim.

### Workflow

```bash
# 1. Analyze prosecution brief
litassist digest prosecution_brief.pdf --mode issues \
  --context "inconsistencies, credibility, self-defence elements"

# 2. Research self-defence
litassist lookup "self-defence excessive force proportionality Victoria criminal"

# 3. Witness statement analysis
litassist counselnotes witness_statements/*.pdf --extract \
  --output-dir witness_analysis/

# 4. Defence strategy
litassist brainstorm --facts case_facts.txt --mode both

# 5. Barrister's brief
litassist barbrief \
  --case-name "R v Johnson" \
  --facts case_facts.txt \
  --hearing-type "criminal trial" \
  --context "Self-defence under s322K Crimes Act" \
  --documents evidence/*.pdf
```

## Quick Advice Scenarios

### Lease Dispute
```bash
# Quick analysis and advice
litassist digest commercial_lease.pdf --mode issues --context "termination"
litassist lookup "commercial lease termination notice requirements NSW"
litassist draft --type advice_letter --facts lease_facts.txt
```

### Debt Recovery
```bash
# Streamlined debt recovery
litassist extractfacts invoices/*.pdf loan_agreement.pdf
litassist draft --type letter_of_demand --facts debt_facts.txt
```

### Contract Review
```bash
# Rapid contract assessment
litassist digest draft_agreement.pdf --mode issues \
  --context "liability, indemnity, termination"
litassist counselnotes contract_review_output.md
```

## Tips for Effective Use

### 1. Start Simple
Begin with basic commands and gradually incorporate advanced features.

### 2. Maintain Good Records
```bash
# Save all outputs
litassist lookup "topic" > research/topic_research.md
litassist brainstorm --facts case_facts.txt > strategy/initial_strategies.md
```

### 3. Use Descriptive File Names
```
case_facts_v1.txt
case_facts_after_discovery.txt
case_facts_final.txt
```

### 4. Chain Commands Effectively
```bash
# Extract then analyze
litassist extractfacts documents/*.pdf | \
litassist brainstorm --facts - | \
litassist strategy --facts case_facts.txt --brainstorm-file -
```

### 5. Verify Important Documents
Always use `--verify` flag for court documents:
```bash
litassist draft --type affidavit --facts case_facts.txt --verify
```

## Sample Files

Example case_facts.txt structure:
```
CASE OVERVIEW
- Case name: Smith v Jones Enterprises Pty Ltd
- Jurisdiction: Federal Court of Australia
- Claim amount: $2,500,000

KEY FACTS
- Contract signed: 15 March 2022
- Breach occurred: 10 September 2023
- Notice given: 15 September 2023
- Loss quantified by forensic accountant

PARTIES
- Applicant: Tech Innovations Pty Ltd (small tech startup)
- Respondent: Jones Enterprises Pty Ltd (large corporation)

ISSUES
1. Breach of software development agreement
2. Intellectual property ownership dispute
3. Consequential loss claims

EVIDENCE
- Original contract
- Email correspondence showing breach
- Expert report on losses
- Witness statements from 3 developers
```

## Integration Examples

### With Git
```bash
# Version control your legal work
git init legal-matter-12345
cd legal-matter-12345
litassist caseplan case_facts.txt --budget standard
git add .
git commit -m "Initial case plan and facts"
```

### With Document Management
```bash
# Organize outputs
OUTPUT_DIR="matters/2024/smith-v-jones"
mkdir -p "$OUTPUT_DIR"/{research,drafts,strategy}

litassist lookup "breach of contract" > "$OUTPUT_DIR/research/contract_law.md"
litassist draft --type statement_of_claim --facts case_facts.txt \
  > "$OUTPUT_DIR/drafts/statement_of_claim_v1.md"
```

### Automation Script
```bash
#!/bin/bash
# automated_case_analysis.sh

CASE_DIR=$1
cd "$CASE_DIR"

echo "Starting automated case analysis..."

# Process all documents
for doc in documents/*.pdf; do
  echo "Processing $doc..."
  litassist digest "$doc" --mode summary > "summaries/$(basename $doc .pdf).md"
done

# Extract facts
litassist extractfacts documents/*.pdf --output case_facts_auto.txt

# Generate strategies
litassist brainstorm --facts case_facts_auto.txt > strategy_report.md

echo "Analysis complete. Check strategy_report.md"
```

## Next Steps

- Review the [API Reference](/api) for all command options
- Read the [User Guide](/guide) for detailed explanations
- Check [GitHub](https://github.com/litassist/litassist) for updates