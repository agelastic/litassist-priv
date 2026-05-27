# Lookup Command Use Cases and Workflows

Last updated: 27/05/2026

## Overview

This document provides real-world examples of how lawyers use the lookup command in daily practice.

The lookup command searches Jade and AustLII via Google CSE and uses `google/gemini-3.5-flash` (per `litassist/llm/model_configs.yaml`) to synthesise results. Key options:

- `--mode irac` (default) — structured IRAC analysis; `--mode broad` — wider discursive answer
- `--extract citations|principles|checklist` — extract a specific output type
- `--comprehensive` — exhaustive analysis using up to 40 sources
- `--context` — additional context string appended to the query
- `--output` — save result to a named file

## Source coverage and known limitations

The lookup command's content-fetching layer was reworked in May 2026 for Cloudflare resilience. What this means for practitioners:

### What you reliably get full text for
- **AustLII HTML** — case judgments, legislation, journal articles served as HTML
- **AustLII PDF URLs with an HTML sibling** — most journal articles and reported cases (the lookup chain transparently substitutes `<path>.pdf` for `<path>.html` since AustLII Cloudflare-blocks direct PDF access)
- **Australian government sites served as PDF** — finance.gov.au, accc.gov.au, supremecourt.nsw.gov.au, fedcourt.gov.au speech documents
- **legislation.gov.au** legislation pages (including `/latest/text` ToC pattern which follows to the real document)
- **State government and tribunal sites** (fairwork.gov.au, fedcourt.gov.au practice notes, apsc.gov.au, aemc.gov.au)
- **Local `.pdf`, `.rtf`, `.txt`, `.md` files** — pass a filesystem path instead of a URL and lookup reads it directly

### What you get citation-only stub content for
- **AustLII PDF URLs without a full HTML sibling** — some journal articles (notably older issues of VUWLawRw, AukULawRw) publish only the PDF; the `.html` URL exists but contains only the title and journal citation. The CSE snippet plus the citation is what reaches the LLM.

### What is unrecoverable
- **AustLII bill explanatory memos** (`/legis/cth/bill_em/*.pdf`) — Cloudflare-blocked, no HTML sibling, returns 404
- **Jade.io main domain** — skipped pending the planned cookie-reuse implementation (see TODO.md `[SOON]` entry). The `ndfv.jade.io` subdomain still works.

### Behind-the-scenes mechanics
You generally do not need to know these, but useful when interpreting audit logs in `logs/`:

- Primary transport is `curl_cffi` with Chrome 136 TLS impersonation; Jina is fallback for Cloudflare challenges, SPA-rendered sites, and non-text payloads.
- `fetch_attempt_*.md` audit logs record HTTP status, Cloudflare headers, content size, and rejection reason — enough to tell why a particular source contributed full text, a stub, or nothing.
- Audit log file names are microsecond-resolution (`YYYYMMDD-HHMMSS-MICROSECONDS`) so the curl-failure record and the immediate-Jina-fallback record both survive on disk.

## Criminal Law Use Cases

### Use Case 1: Preparing Bail Application

**Scenario**: Defence lawyer needs authorities on exceptional circumstances for serious offences.

**Without --extract**:
```bash
litassist lookup "exceptional circumstances bail serious offences NSW"
```
*Result*: Wall of text mixing cases, legislation, and commentary
*Pain*: Manually extract each case citation, copy to Word, format properly

**With --extract**:
```bash
litassist lookup "exceptional circumstances bail serious offences NSW" --extract citations
```
*Result*:
```
CITATIONS FOUND:
Bail Act 2013 (NSW) s 16B
R v Tikomaimaleya [2017] NSWSC 83
DPP v Tikomaimaleya [2015] NSWCA 83
R v Young [2019] NSWSC 1345
```
*Benefit*: Copy entire list directly into submissions

### Use Case 2: Advising Client on Defences

**Scenario**: Client charged with assault, need to explain self-defence requirements.

**Without --extract**:
```bash
litassist lookup "self defence assault NSW elements"
# Read through output
# Manually create checklist
# Draft advice letter
```

**With --extract**:
```bash
litassist lookup "self defence assault NSW elements" --extract checklist
```
*Result*:
```
PRACTICAL CHECKLIST:
[] Accused believed conduct necessary to defend self/another
[] Conduct was reasonable response in circumstances as accused perceived
[] Accused's belief based on reasonable grounds
[] No opportunity to retreat safely
[] Force used was proportionate to threat
```
*Benefit*: Use checklist in client conference and file notes

### Use Case 3: Sentencing Submissions

**Scenario**: Need sentencing range for drug supply offences.

**With --extract**:
```bash
litassist lookup "sentencing range drug supply NSW" --extract principles
```
*Example output structure*:
```
=== SENTENCING PRINCIPLES ===
1. Objective seriousness assessed by quantity and role
   - R v Clark [2019] NSWCCA 123 at [45]

2. Commercial supply attracts full-time imprisonment
   - Nguyen v R [2020] NSWCCA 234 at [23]

=== SENTENCING RANGE ===
Low-level street dealing: 12-18 months (ICO available)
- R v Smith [2021] NSWDC 456 - 12 months ICO

Mid-level supply: 2-4 years
- R v Jones [2020] NSWDC 789 - 3 years, NPP 18 months

=== MITIGATING FACTORS ===
[] Early guilty plea (25% discount)
[] Assistance to authorities
[] Drug rehabilitation efforts
```

## Family Law Use Cases

### Use Case 4: Relocation Application

**Scenario**: Parent wants to relocate with children interstate.

**Without --extract**:
```bash
litassist lookup "relocation best interests child factors"
# Scroll through pages of text
# Try to identify each factor mentioned
# Cross-reference with client's circumstances
```

**With --extract**:
```bash
litassist lookup "relocation best interests child factors" --extract principles
```
*Result*:
```
LEGAL PRINCIPLES:
1. Relocation not determined by presumption but best interests
   - AMS v AIF [1999] HCA 26 at [41]

2. Court must weigh competing proposals realistically
   - U v U [2002] HCA 36 at [80]

3. Reasons for relocation must be bona fide
   - Morgan v Miles [2007] FamCAFC 230 at [44]

4. Impact on relationship with non-relocating parent critical
   - Godfrey & Sanders [2007] FamCA 102 at [65]
```
*Benefit*: Structure affidavit around these principles

### Use Case 5: Property Settlement Factors

**With --extract**:
```bash
litassist lookup "property settlement s79 factors contributions" --extract principles
```
*Example output structure*:
```
=== S.79 FACTORS ===
1. Identify and value property pool
   - Stanford v Stanford [2012] HCA 52

2. Assess contributions (s.79(4)(a)-(c))
   - Financial contributions
   - Non-financial contributions
   - Homemaker contributions
   - Post-separation contributions

3. Future needs factors (s.75(2))
   [] Age and health
   [] Income and earning capacity
   [] Care of children
   [] Length of marriage

=== RECENT APPROACH ===
High wealth cases: Detailed contributions analysis
- Kane & Kane [2023] FamCAFC 123
```

## Commercial Law Use Cases

### Use Case 6: Director Duties Breach

**Scenario**: Advising on potential breach of director duties.

**With --extract**:
```bash
litassist lookup "breach director duties insolvent trading" --extract checklist
```
*Result*:
```
DIRECTOR DUTIES CHECKLIST:
[] Company incurred debt
[] Company was insolvent at time OR became insolvent
[] Reasonable grounds to suspect insolvency
[] Director aware OR ought to have been aware
[] Defence: Reasonable grounds to expect solvency
[] Defence: Reasonable steps to prevent debt

Key Dates to Establish:
[] When insolvency began
[] When each debt incurred
[] When director knew/should have known
```

### Use Case 7: Contract Dispute Research

**Pain point**: Getting clean citations for pleadings.

**With --extract**:
```bash
litassist lookup "repudiation contract principles" --extract citations
# Then in draft command:
litassist draft "statement of claim for repudiation"
# Manually paste citations from lookup
```

## Civil Litigation Use Cases

### Use Case 8: Negligence Advice

**Scenario**: Initial advice on medical negligence claim.

**With --extract**:
```bash
litassist lookup "medical negligence elements duty breach causation NSW" --extract principles
```
*Example output structure*:
```
=== NEGLIGENCE ELEMENTS ===
1. Duty of care
   - Doctor-patient relationship established
   - Rogers v Whitaker [1992] HCA 58

2. Breach - s.5O Civil Liability Act 2002 (NSW)
   - Failure to meet standard of reasonable professional
   - Expert evidence required on standard

3. Causation - s.5D Civil Liability Act 2002 (NSW)
   - Factual: but for test
   - Scope: appropriate attribution

4. Damage
   - Personal injury
   - Economic loss
   - Care costs

=== LIMITATION PERIOD ===
3 years from discoverability - s.50C(1)
Long-stop 12 years - s.50C(2)
```

### Use Case 9: Discovery Objections

**With --extract**:
```bash
litassist lookup "proportionality discovery Federal Court" --extract principles
```
*Use in*:
```bash
litassist draft "objections to discovery categories"
# Copy principles into draft for authority
```

## Administrative Law Use Cases

### Use Case 10: Judicial Review Grounds

**Scenario**: Challenging immigration decision.

**With --extract**:
```bash
litassist lookup "judicial review grounds immigration jurisdictional error" --extract checklist
```
*Example output structure*:
```
=== GROUNDS FOR REVIEW ===
1. Jurisdictional error
   - Failed to consider relevant consideration
   - Craig v South Australia [1995] HCA 58

2. Procedural fairness
   - Failed to give opportunity to comment
   - Kioa v West [1985] HCA 81

=== PROCEDURAL REQUIREMENTS ===
[] File within 35 days - s.477 Migration Act
[] Form 62 - Federal Circuit Court
[] Supporting affidavit
[] $1,000 filing fee
```

## Workflow Integration Examples

### Workflow 1: Full Advice Process

```bash
# 1. Research
litassist lookup "unfair dismissal remedies"

# 2. Extract key points
litassist lookup "unfair dismissal remedies" --extract principles > research.txt

# 3. Extract facts
litassist extractfacts client_termination_letter.pdf

# 4. Draft advice
litassist draft case_facts.txt "advice on unfair dismissal prospects"
# Manually incorporate research.txt authorities
```

### Workflow 2: Urgent Court Application

```bash
# Morning: Get authorities
litassist lookup "urgent injunction principles" --extract citations

# Draft application
litassist draft case_facts.txt "urgent injunction application"
# Copy-paste citations

# Get procedural requirements
litassist lookup "urgent injunction procedure Federal Court" --extract checklist
```

### Workflow 3: Local RTF judgment file

**Scenario**: Solicitor received an older case judgment as an `.rtf` file from another practitioner or downloaded from an archive. Need to extract holdings without re-typing.

```bash
# Pass the .rtf path directly - lookup-adjacent commands accept it
litassist extractfacts old_judgment_2018.rtf

# Or use as input file for downstream commands
litassist counselnotes "key authority for our position" --research old_judgment_2018.rtf
```

**Result**: `litassist/utils/rtf.py` extracts plain text via `striprtf` and wraps with `[RTF DOCUMENT EXTRACTED]` markers before the content reaches the LLM. Works for AustLII RTF case files too (some older cases on AustLII publish in RTF format).

### Workflow 4: Settlement Conference Prep

```bash
# Get recent settlement ranges
litassist lookup "personal injury settlements motor vehicle"

# Extract principles for negotiation
litassist lookup "Calderbank offers costs consequences" --extract principles

# Prepare position
litassist strategy case_facts.txt --outcome "Settlement $200-300k"
```

## Benefits

### Time Savings
- Manual citation extraction from unstructured output: 15-20 minutes
- With `--extract citations`: under 30 seconds

### Accuracy
- Manual extraction risks missing citations; `--extract` captures all systematically

### Usability
- Plain output requires reading in full; `--extract` jumps directly to the relevant section

### Integration
- Structured sections make copy-paste into submissions and file notes reliable

## Common Patterns

1. **Citation Extraction**: `--extract citations` — most common; use for pleadings and submissions
2. **Checklist Generation**: `--extract checklist` — procedural matters and client conferences
3. **Principles Summary**: `--extract principles` — advice letters and affidavit structure
4. **Deep Research**: `--comprehensive` — exhaustive analysis when thoroughness matters
