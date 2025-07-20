# LitAssist Demo: TechStart v CloudCorp
## Modern Tech Contract Dispute - Comprehensive Demo Plan

### Overview
This demo showcases LitAssist's complete workflow for a modern commercial dispute involving a failed cloud services agreement. The case demonstrates all major features while remaining accessible to law students and practitioners.

## Case Summary

**TechStart Pty Ltd v CloudCorp Australia Pty Ltd**
- **Court**: Federal Court of Australia (Commercial List)
- **Claim**: $850,000 + interest + costs
- **Primary Cause**: Breach of Service Level Agreement
- **Secondary Claims**: Negligence, misleading conduct under ACL

## Phase 1: Base Documents to Create

### 1.1 Core Case File
**File**: `demo/case_facts.txt`
```
CLIENT DETAILS
- Name: TechStart Pty Ltd (ACN 123 456 789)
- Industry: Financial technology (payment processing)
- Size: 15 employees, $3.2M annual revenue
- CEO: Sarah Chen
- Founded: 2021

DEFENDANT DETAILS
- Name: CloudCorp Australia Pty Ltd (ACN 987 654 321)
- Industry: Cloud infrastructure provider
- Size: 500+ employees (multinational subsidiary)
- Key Contact: Michael Roberts (Account Manager)

CONTRACT DETAILS
- Title: Master Services Agreement for Cloud Infrastructure
- Date: 1 July 2023
- Term: 3 years
- Value: $180,000 per annum ($15,000/month)
- Key Terms: 99.9% uptime guarantee, 24/7 support, data sovereignty

KEY DATES
- Contract signed: 1 July 2023
- Service commenced: 15 July 2023
- First outage: 3 September 2023 (4 hours)
- Major outage: 15-17 October 2023 (52 hours)
- Notice of breach: 20 October 2023
- Termination: 15 November 2023

SERVICE FAILURES
1. September outage: 4 hours downtime during business hours
2. October outage: Complete service failure for 52 hours
3. Data corruption: 10% of transaction records corrupted
4. Support failures: No response to critical tickets for 48+ hours

LOSSES CLAIMED
- Direct losses from downtime: $450,000
- Customer compensation paid: $125,000
- Emergency migration costs: $75,000
- Lost customers (projected): $200,000
- Total claim: $850,000

EVIDENCE AVAILABLE
- Original service agreement
- Email correspondence during outages
- Support ticket history
- Expert report on service architecture
- Financial impact assessment
- Customer complaint records
```

### 1.2 Contract Excerpts
**File**: `demo/documents/service_agreement_excerpts.txt`
```
MASTER SERVICES AGREEMENT - KEY EXCERPTS

Clause 3.1 - Service Levels
CloudCorp guarantees 99.9% uptime for all Production Services, measured monthly. 
Uptime excludes scheduled maintenance windows (max 4 hours/month, with 7 days notice).

Clause 3.4 - Service Credits
Monthly Uptime | Service Credit
99.9% - 99.0% | 10% of monthly fee
99.0% - 95.0% | 25% of monthly fee
Below 95.0%   | 50% of monthly fee

Clause 8.2 - Limitation of Liability
CloudCorp's total liability under this Agreement shall not exceed the total fees 
paid in the 12 months preceding the claim. CloudCorp excludes all liability for 
consequential, indirect, or special damages.

Clause 8.5 - Exceptions to Limitations
The limitations in Clause 8.2 do not apply to:
(a) Breaches of confidentiality
(b) Wilful misconduct or gross negligence
(c) Death or personal injury

Clause 12.1 - Termination for Breach
Either party may terminate for material breach if the breach is not remedied 
within 30 days of written notice.

Clause 15.3 - Governing Law
This Agreement is governed by the laws of New South Wales, Australia.
```

### 1.3 Email Correspondence
**File**: `demo/documents/email_correspondence.txt`
```
EMAIL THREAD: Critical Service Outage - October 2023

From: Sarah Chen <s.chen@techstart.com.au>
To: Michael Roberts <m.roberts@cloudcorp.com.au>
Date: 15 October 2023, 9:15 AM
Subject: URGENT: Complete service outage - need immediate response

Michael,

Our entire platform has been down since 3 AM. This is catastrophic - we process 
over $2M in payments daily. Our customers cannot access their accounts.

We've raised critical ticket #4521. No response after 6 hours.

This is completely unacceptable. Call me immediately.

Sarah Chen
CEO, TechStart

---

From: Michael Roberts <m.roberts@cloudcorp.com.au>
To: Sarah Chen <s.chen@techstart.com.au>
Date: 15 October 2023, 4:30 PM
Subject: RE: URGENT: Complete service outage

Sarah,

I've just seen your email. I'm escalating this internally. The technical team 
is investigating what appears to be a major infrastructure failure affecting 
multiple customers.

I'll update you within 2 hours.

Michael

---

From: Sarah Chen <s.chen@techstart.com.au>
To: Michael Roberts <m.roberts@cloudcorp.com.au>
Date: 16 October 2023, 11:00 AM
Subject: RE: URGENT: Complete service outage - Day 2

Michael,

It's been over 24 hours. We're losing customers. The Financial Times is asking 
for comment about our "system failures."

Your 99.9% uptime guarantee is meaningless if you can't even respond to critical 
issues. We've had to tell customers their funds are "temporarily inaccessible" - 
do you understand the regulatory implications?

If service isn't restored by EOD, we'll be seeking emergency court orders.

Sarah

---

From: CloudCorp Support <support@cloudcorp.com.au>
To: Sarah Chen <s.chen@techstart.com.au>
Date: 17 October 2023, 2:00 PM
Subject: Ticket #4521 - Service Restored

Dear Valued Customer,

We are pleased to inform you that service has been restored. The issue was caused 
by a cascading failure in our Sydney data center.

As per our Service Level Agreement, service credits will be applied to your account.

Thank you for your patience.

CloudCorp Support Team
```

### 1.4 Expert Report Summary
**File**: `demo/documents/expert_report_summary.txt`
```
EXPERT REPORT - EXECUTIVE SUMMARY
Dr. James Wu, Cloud Infrastructure Specialist

Engaged by: TechStart Pty Ltd
Matter: TechStart v CloudCorp
Date: 1 December 2023

OPINION SUMMARY:

1. INFRASTRUCTURE ANALYSIS
The October 2023 outage resulted from fundamental architectural flaws in 
CloudCorp's Sydney data center. Key findings:
- No proper failover mechanisms between availability zones
- Single point of failure in network routing
- Inadequate backup power systems

2. INDUSTRY STANDARDS
CloudCorp's infrastructure falls below industry standards:
- AWS, Azure, and Google Cloud all maintain redundant systems
- 99.9% uptime requires N+2 redundancy (CloudCorp had N+0)
- 52-hour recovery time indicates absence of disaster recovery planning

3. SERVICE LEVEL COMPLIANCE
Based on logs analyzed:
- Actual uptime for October 2023: 92.8%
- Annual uptime projection: 97.2%
- This represents a material breach of the 99.9% guarantee

4. CAUSATION
The extended outage was preventable with proper:
- Infrastructure investment
- Redundancy planning
- Disaster recovery procedures
- Competent technical management

CONCLUSION:
CloudCorp's service fell materially below both contractual requirements and 
industry standards, demonstrating negligence in infrastructure management.
```

### 1.5 Financial Impact Assessment
**File**: `demo/documents/financial_impact.txt`
```
FINANCIAL IMPACT ASSESSMENT
TechStart Pty Ltd - October 2023 Outage

Prepared by: Chen & Associates Chartered Accountants
Date: 25 November 2023

DIRECT LOSSES (15-17 October 2023):

1. Transaction Processing Fees Lost
   - Normal daily volume: $2.1M
   - Processing fee: 1.5%
   - Daily fee income: $31,500
   - 2.5 days lost: $78,750

2. Failed Transaction Penalties
   - Failed transactions: 3,847
   - Average penalty: $25
   - Total penalties: $96,175

3. Customer Refunds/Compensation
   - Compensation paid: 127 customers
   - Total amount: $125,000

4. Emergency Response Costs
   - Weekend staff overtime: $18,500
   - Consultant fees: $35,000
   - Emergency hosting: $21,500
   - Total: $75,000

SUBTOTAL DIRECT: $374,925

CONSEQUENTIAL LOSSES:

5. Lost Customers
   - Customers terminated: 12 enterprise accounts
   - Annual value: $485,000
   - Projected recovery (60%): $194,000
   - Net loss: $291,000

6. Reputation Damage
   - New customer acquisition cost increase: 40%
   - Projected impact (6 months): $184,075

SUBTOTAL CONSEQUENTIAL: $475,075

TOTAL LOSSES: $850,000

Note: These calculations are conservative and exclude potential regulatory fines.
```

## Phase 2: LitAssist Commands to Run

### Step 1: Initial Case Planning
```bash
# Generate comprehensive case plan
litassist caseplan demo/case_facts.txt --budget standard

# This will create:
# - caseplan_output.md (detailed workflow)
# - caseplan_commands_standard.sh (executable script)
```

### Step 2: Legal Research
```bash
# Research breach of contract principles
litassist lookup "breach of contract service level agreement Australia" --comprehensive

# Research limitation clauses
litassist lookup "limitation of liability clauses gross negligence Australia" --comprehensive

# Research consequential loss
litassist lookup "consequential loss contractual damages technology agreements" --comprehensive
```

### Step 3: Document Analysis
```bash
# Analyze the service agreement
litassist digest demo/documents/service_agreement_excerpts.txt --mode issues --context "breach, liability, termination"

# Analyze email correspondence
litassist digest demo/documents/email_correspondence.txt --mode summary --context "notice, acknowledgment, response times"

# Analyze expert report
litassist digest demo/documents/expert_report_summary.txt --mode issues --context "negligence, industry standards"

# Extract comprehensive facts
litassist extractfacts demo/documents/*.txt --output demo/case_facts_extracted.txt --verify
```

### Step 4: Strategy Development
```bash
# Generate litigation strategies
litassist brainstorm --facts demo/case_facts_extracted.txt --mode both

# Develop targeted approach
litassist strategy --facts demo/case_facts_extracted.txt --reasoning-effort high
```

### Step 5: Document Drafting
```bash
# Draft statement of claim
litassist draft --type statement_of_claim --facts demo/case_facts_extracted.txt --instructions "Focus on: 1) Material breach of uptime guarantee, 2) Gross negligence exception to liability cap, 3) Misleading conduct regarding infrastructure capabilities" --verify

# Draft CEO affidavit
litassist draft --type affidavit --facts demo/case_facts_extracted.txt --instructions "Sarah Chen affidavit focusing on business impact, customer loss, emergency response efforts" --verify

# Draft outline of submissions for urgent injunction
litassist draft --type outline_of_submissions --facts demo/case_facts_extracted.txt --instructions "Urgent injunction to preserve evidence and prevent disposal of infrastructure logs" --verify
```

### Step 6: Barrister's Brief
```bash
# Comprehensive brief for summary judgment application
litassist barbrief --case-name "TechStart v CloudCorp" --facts demo/case_facts_extracted.txt --hearing-type "summary judgment" --context "Clear breach of SLA, extensive documentary evidence, no factual disputes" --documents demo/documents/*.txt --verify
```

## Phase 3: Expected Outputs Structure

```
demo/
├── README.md                           # Demo overview and guide
├── case_facts.txt                      # Initial client interview
├── case_facts_extracted.txt            # Structured facts after extraction
├── documents/
│   ├── service_agreement_excerpts.txt
│   ├── email_correspondence.txt
│   ├── expert_report_summary.txt
│   └── financial_impact.txt
├── outputs/
│   ├── 01_planning/
│   │   ├── caseplan_output.md
│   │   └── caseplan_commands_standard.sh
│   ├── 02_research/
│   │   ├── lookup_breach_of_contract.md
│   │   ├── lookup_limitation_clauses.md
│   │   └── lookup_consequential_loss.md
│   ├── 03_analysis/
│   │   ├── digest_agreement_issues.md
│   │   ├── digest_correspondence_summary.md
│   │   └── digest_expert_issues.md
│   ├── 04_strategy/
│   │   ├── brainstorm_strategies.md
│   │   └── strategy_analysis.md
│   ├── 05_drafts/
│   │   ├── statement_of_claim.md
│   │   ├── affidavit_sarah_chen.md
│   │   └── outline_urgent_injunction.md
│   └── 06_brief/
│       └── barbrief_summary_judgment.md
└── educational/
    ├── workflow_guide.md               # How this case demonstrates LitAssist
    ├── legal_principles.md             # Key legal concepts illustrated
    └── student_exercises.md            # Practice questions based on outputs
```

## Phase 4: Educational Components

### Learning Objectives Demonstrated
1. **Contract Interpretation**: How SLAs function in commercial agreements
2. **Limitation Clauses**: When they apply and exceptions
3. **Evidence Preparation**: From emails to structured legal documents
4. **Strategic Thinking**: Multiple approaches to the same facts
5. **Professional Drafting**: Court-ready documents with proper citations

### Key Takeaways for Students
- Real workflow from client interview to court documents
- How AI assists without replacing legal judgment
- Importance of verification and quality control
- Time savings while maintaining professional standards

## Implementation Notes

1. **Realism**: All facts and documents feel authentic while being fictional
2. **Complexity**: Case has enough depth to showcase all features
3. **Clarity**: Each document serves a clear purpose in the workflow
4. **Education**: Outputs include enough detail to learn from

This demo will give viewers a comprehensive understanding of LitAssist's capabilities while teaching practical legal skills applicable to modern commercial litigation.