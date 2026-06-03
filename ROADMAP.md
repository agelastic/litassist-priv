# LitAssist Feature Roadmap

Last updated: 02/06/2026
**Status:** Strategic planning; roadmap items are aspirational unless marked DONE, PARTIALLY SUPERSEDED, or already implemented elsewhere
**Confidence:** 0.88

---

## Sources of Truth

- Registered commands: `litassist/commands/__init__.py`
- Current model assignments: `litassist/llm/model_configs.yaml`
- Active technical debt and reliability tasks: `TODO.md`
- This roadmap: strategic feature sequencing, not current implementation state

---

## Executive Summary

This roadmap prioritizes features for litassist based on **active litigation needs** over FOI and government affairs. The goal is to provide lawyer-like smart advice for legal and government dealings, advising on what to do when and how, with precision as the priority.

**Total Planned Work:** ~300-390 hours across 7 phases (updated Dec 2025; current model choices must be checked against `litassist/llm/model_configs.yaml` before implementation)

**Key Principle:** Litigation > FOI > Other matters

---

## API Research Findings (November 2025)

### JADE.io
- **Status:** NO public API available
- **History:** 2011 blog post about URL construction is deprecated
- **Conclusion:** Continue current approach (Google CSE + web scraping)

### AustLII SINO CGI API
- **Status:** Documentation GONE (both URLs return 410 Gone)
- **History:** Mentioned in old docs but no longer accessible
- **Conclusion:** Continue current approach (Google CSE + direct URL construction + web scraping)

### Available APIs
- **Queensland Legislation API:** Requires registration, limited to QLD legislation only
- **No other viable APIs** for Australian case law

### Recommended Strategy
**Continue current scraping approach** - This is the ONLY viable path for Australian legal databases. No programmatic APIs exist for JADE or AustLII currently.

---

## Feature Prioritization

Features are prioritized to support active litigation (ACT civil matters), professional complaints, and FOI reviews, with emphasis on systematic matter tracking, deadline management, and strategic advice generation.

---

## PHASE 1: ACTIVE LITIGATION FOUNDATION (Sprint 1)
**Duration:** 40-50 hours
**Goal:** Foundation + immediate court needs

### P0A-1: Matter Memory Module [ELEVATED TO P0]
**Effort:** 15-18 hours
**Priority:** CRITICAL - FOUNDATIONAL

**Purpose:** Track all active matters with systematic persistence

**Rationale:**
- Everything else depends on this
- Active litigation requires systematic tracking across multiple concurrent matters
- Critical deadline management
- Without this, Procedural Advisor cannot function

**Capabilities:**
- Matter-scoped storage: `~/.config/litassist/matters/{matter_id}/`
- Track per matter:
  - Facts (versioned)
  - Strategy decisions + reasoning
  - Correspondence (incoming/outgoing)
  - Timeline (events, deadlines)
  - Authorities (citations used, verification status)
  - Exhibits (registry, file paths, hashes)
  - Court filings and responses

**Example Matter Types:**
- `LITIGATION-001` - Civil litigation (ACT Magistrates Court)
- `COMPLAINT-001` - Professional complaint (Legal Services Commission)
- `FOI-001` - FOI review (OAIC)

**Implementation:**
- New module: `litassist/matter/`
- Commands:
  - `la matter create LITIGATION-001 --type litigation --court "ACT Magistrates"`
  - `la matter list`
  - `la matter show LITIGATION-001`
- All existing commands enhanced with `--matter {id}` flag (required, not auto-detect)
- Automatic output saving to matter directory
- Git-based versioning (local only, deterministic)

---

### P0A-2: ACT Magistrates Court Procedures Calculator [ELEVATED TO P0]
**Effort:** 8-10 hours
**Priority:** CRITICAL - IMMEDIATE NEED

**Purpose:** Critical deadline calculations for ACT litigation

**Rationale:**
- Defense/response due date calculations
- Applications and interlocutory deadlines
- Directions hearing preparation timeline
- Discovery timelines
- ACT Court Procedures Rules 2006 compliance

**Capabilities:**
- Service deadline calculations
- Filing deadlines by application type:
  - Defense due date
  - Reply to defense
  - Interlocutory applications (strike-out, summary judgment, etc.)
  - Discovery requests and objections
  - Witness lists and evidence
  - Trial preparation milestones
- Directions hearing preparation checklist
- Court rules compliance checking
- Plain text output for matter timeline integration

**Implementation:**
- New command: `la actcourt --calculate-deadline --served 2025-11-06 --type defense`
- New command: `la actcourt --checklist --hearing-type directions --date 2025-12-15`
- Pure calculation (no LLM, date arithmetic + rules)
- Integration: `la actcourt --matter LITIGATION-001 --update-timeline`
- Output: Deadline table + calendar reminders + plain text facts

---

### P0A-3: Letter Doctor [KEEP P0]
**Effort:** 8-10 hours
**Priority:** HIGH - QUALITY CONTROL

**Purpose:** Ensure all court and legal correspondence is strategically sound

**Rationale:**
- One bad letter undermines months of work
- Court correspondence requires professional tone
- Settlement/procedural correspondence is critical

**Capabilities:**
- Detect aggressive, defensive, emotional language
- Identify potential admissions or concessions
- Flag manipulative phrasing
- Suggest neutral alternatives
- Tone analysis (professional / defensive / aggressive / conciliatory)
- Legal risk assessment (defamation, contempt, professional conduct)
- Bias detection (cognitive biases in arguments)
- Court-specific tone guidance
- **Bias/Tone Scanning (integrated from research map):**
  - Modal language detection (likely, probably, usually)
  - Argumentative drift analysis
  - Agency/dominance shift detection (important for FVO contexts)
  - Optional `--bias-scan` flag for detailed bias analysis

**Implementation:**
- New module: `litassist/commands/doctor/`
- Commands:
  - `la doctor --input draft_letter.md --recipient court`
  - `la doctor --input draft_email.md --recipient opposing-counsel`
  - `la doctor --input draft.md --bias-scan` (detailed bias analysis)
- LLM: GPT-5.5 (critical analysis) + Claude Sonnet 4.6 (neutral rewrite)
- Output: Risk report + line-by-line suggestions + rewritten version + bias report (if --bias-scan)

---

### P0A-4: Legal Correspondence Analyzer [RENAMED, KEEP P0]
**Effort:** 10-12 hours
**Priority:** HIGH - IMMEDIATE TRIAGE

**Purpose:** Automated analysis of all incoming legal/court correspondence

**Rationale:**
- When defense/response filed, need instant analysis
- Extract obligations, threats, tactical moves
- Early warning system for procedural traps

**Capabilities:**

**Court/Legal Correspondence:**
- Classify type (defense, application, directions order, costs application)
- Extract obligations ("must file X by Y")
- Identify threats (strike-out motions, costs applications)
- Detect procedural defects in opponent's filings
- Flag admissions or concessions by opponent
- Identify weak points in opponent's case
- Suggest strategic response classification

**Government Correspondence:**
- Classify type (FOI decision, OAIC response, agency request)
- Extract statutory obligations
- Identify delay tactics
- Detect procedural defects in agency actions

**Implementation:**
- New module: `litassist/commands/analyze/`
- Commands:
  - `la analyze --input defense.pdf --type legal --opponent "Counsel A"`
  - `la analyze --input foi_decision.pdf --type government --agency DHA`
- LLM: Claude Sonnet 4.6 + GPT-5.5 cross-check for critical documents
- Output: Threat assessment + obligation checklist + strategic recommendation + deadline extraction

---

## PHASE 2: ACTIVE LITIGATION STRATEGIC (Sprint 2)
**Duration:** 40-50 hours
**Goal:** Strategic response and tactical planning

### P0B-6: Procedural Advisor / "What to Do Next" [KEEP P0]
**Effort:** 8-10 hours
**Priority:** HIGH

**Purpose:** Context-aware guidance on immediate next steps across all active matters

**Rationale:**
- Systematic approach prevents missed deadlines across multiple matters
- Risk-based prioritization (what happens if deadline missed?)

**Capabilities:**
- Analyze current state of ALL matters (or specific matter)
- Identify immediate obligations across matters
- Recommend next action with rationale per matter
- Prioritize across matters (urgent vs. important)
- Procedural compliance checks (court rules, FOI Act, complaint processes)
- Risk assessment
- Calendar integration (export deadlines)

**Implementation:**
- New module: `litassist/commands/next/`
- Commands:
  - `la next` (analyze all matters)
  - `la next --matter LITIGATION-001` (specific matter)
  - `la next --urgent` (only critical deadlines)
- Requires: Matter Memory from Sprint 1
- LLM: Claude Sonnet 4.6 (strategic prioritization)
- Output: Prioritized action list + deadline table + procedural guidance + risk warnings

---

### P0B-7: Tactical Response Generator [KEEP P0]
**Effort:** 15-20 hours
**Priority:** HIGH

**Purpose:** Analyze incoming litigation documents and generate strategic response options

**Rationale:**
- When defense/application filed, need immediate strategic analysis
- Generate multiple response options with pros/cons

**Capabilities:**

**Defense Analysis:**
- Parse incoming defense
- Identify admissions, denials, weak arguments
- Spot procedural defects or late filings
- Generate 3-5 response options:
  - File reply addressing denials
  - Apply to strike out deficient defense
  - Seek summary judgment on admitted facts
  - Request particulars of vague defenses
  - Proceed straight to discovery
- Timing recommendations (respond immediately vs. wait vs. apply)
- Risk assessment per option (probability of success, cost, time)
- Draft response templates

**Application Analysis:**
- Analyze opponent's applications (strike-out, summary judgment, etc.)
- Identify weaknesses
- Generate defense strategy
- Counter-application opportunities

**3-Variant Output (integrated from research map):**
- Conservative response option (low risk, procedural focus)
- Adversarial response option (aggressive, maximum pressure)
- Neutral/balanced response option (professional, measured)
- Each variant includes risk assessment and CoVe verification
- Comparison matrix showing trade-offs

**Implementation:**
- New module: `litassist/commands/respond/`
- Commands:
  - `la respond --input defense.pdf --matter LITIGATION-001 --type defense`
  - `la respond --input application.pdf --matter LITIGATION-001 --type application`
  - `la respond --input defense.pdf --matter LITIGATION-001 --variants` (3-variant output)
- Loads matter context from Matter Memory
- LLM: Claude Sonnet 4.6 (strategic reasoning) + o3-pro (extended tactical analysis)
- Output: Strategic analysis + response options matrix + timing advice + draft templates + variant comparison

---

### P0B-8: Litigation Tactical Planner [ENHANCED caseplan]
**Effort:** 10-12 hours
**Priority:** MEDIUM-HIGH

**Purpose:** Strategic tactical guidance for litigation, not just workflow automation

**Rationale:**
- Current caseplan generates workflow
- Need tactical advice: when to file, when to delay, procedural tactics
- Lawyer-like strategic judgment

**Enhancements to Existing caseplan:**

**Litigation Tactics:**
- Timing Strategy: Early trial listing for pressure vs. late for more preparation
- Interlocutory Tactics: When to apply for summary judgment, strike-out opportunities
- Discovery Strategy: Broad vs. narrow discovery scope
- Settlement Strategy: Optimal settlement windows
- Witness Strategy: Who to call, order of testimony, preparation priorities
- Cost Orders: When to seek indemnity costs
- Procedural Pressure: Using applications to pressure settlement

**Implementation:**
- Enhance existing `caseplan` command
- New flag: `la caseplan --matter LITIGATION-001 --tactical`
- Add `--tactical` flag for strategic guidance layer
- LLM: o3-pro (extended reasoning for complex tactical decisions)
- Output: Current workflow bash script + NEW SECTION: Tactical Advisory
- Integration: Loads matter context, past strategic decisions

**Status (29/05/2026):** Prerequisite hardening of the existing `caseplan`
shipped on the `caseplan-upgrade` branch: generated-command safety (shlex
round-trip), fail-loud extraction, assessment `--context`, empty-file guard,
Opus 4.7 full-plan model, and a canonical command-output rule in the plan
prompt. That work also drove a per-model parameter-translation overhaul (Opus
4.7/4.8 drop sampling and gain the xhigh/max effort tier; GPT-5.5 xhigh;
Grok 4.20 / Gemini / o3 verbosity handling). The `--tactical` / `--matter` layer
itself is NOT built and remains DEFERRED: without matter state it overlaps the
`strategy` command, so it is blocked on **P0A-1 (Matter Memory)**. When built,
route tactical to its own model-config key (o3-pro per this item), not the
standard full-plan model, and ship `--tactical` together with `--matter`.

---

## PHASE 3: STRATEGIC DEPTH (Sprint 3-4)
**Duration:** 55-70 hours
**Goal:** Opponent intelligence, negotiation, risk analysis, quality assurance

### P1-9: Opponent Profiling System [ELEVATED TO P1]
**Effort:** 8-10 hours
**Priority:** HIGH

**Purpose:** Track patterns and tactics of specific opponents and counsel

**Rationale:**
- Pattern recognition improves strategic advice
- Historical behavior predicts future tactics
- Specific lawyer tactics matter (not just generic approaches)

**Opponent Profile Types:**
- **Individual opponents** (litigation parties)
- **Opposing counsel** (lawyers representing opponents)
- **Government agencies** (FOI/complaint handling)
- **Agency officers** (specific individuals in government matters)

**Capabilities:**
- Track per opponent:
  - Tactic library (delay tactics, procedural moves, settlement offers)
  - Historical outcomes (settlement rates, trial results)
  - Communication patterns (aggressive, conciliatory, evasive)
  - Financial capacity (cost orders risk)
  - Professional reputation
- Predict next moves based on past behavior
- Update profiles after each interaction
- Generate "What to expect next" predictions

**Implementation:**
- New module: `litassist/opponent/`
- Storage: `~/.config/litassist/matters/profiles/{opponent}.yaml`
- Commands:
  - `la profile --create "Opponent A" --type individual`
  - `la profile --update "Counsel A" --matter LITIGATION-001 --event "defense filed"`
  - `la profile --analyze "Opponent A"` (generate predictions)
- LLM: Claude Sonnet 4.6 (pattern analysis)
- Output: Opponent dossier + predicted tactics + recommended counter-tactics

---

### P1-10: Negotiation Strategy Generator [KEEP P1]
**Effort:** 10-12 hours
**Priority:** MEDIUM-HIGH

**Purpose:** Strategic negotiation planning for settlements

**Rationale:**
- Most cases settle - negotiation strategy is critical
- BATNA analysis critical for good outcomes
- Settlement probability assessment needed

**Capabilities:**

**Settlement Strategy:**
- BATNA: Trial outcome probability × expected judgment - trial costs
- Opening position: Full claim value + costs
- Walk-away position: Minimum acceptable outcome
- Concession strategy: What to offer, when, in what order
- Opponent's incentives analysis
- Settlement probability assessment
- Multiple scenarios with probability weighting:
  - Scenario A: Full claim + costs (example probability)
  - Scenario B: Cash settlement at value (example probability)
  - Scenario C: Compromised settlement (example probability)
  - Scenario D: No settlement, proceed to trial (example probability)
- Timing: Settle now vs. after discovery vs. door of court

**Implementation:**
- New module: `litassist/commands/negotiate/`
- Commands:
  - `la negotiate --matter LITIGATION-001 --type settlement --stage pre-discovery`
- LLM: Claude Sonnet 4.6 (strategic reasoning) + o3-pro (probability calculations)
- Uses opponent profile for pattern analysis
- Output: Negotiation strategy + BATNA analysis + concession matrix + scenario probabilities

---

### P1-11: Risk Assessment Framework [KEEP P1]
**Effort:** 12-15 hours
**Priority:** MEDIUM-HIGH

**Purpose:** Probability-based risk analysis for litigation decisions

**Rationale:**
- User wants ACTUAL PERCENTAGES (not qualitative)
- "Should I settle?" requires quantified risk-benefit analysis
- Professional advice includes probability judgments

**Capabilities:**

**Litigation Risk Analysis:**
- Cause of action probability assessment
- Overall case probability (weighted average)
- Expected value calculation:
  - EV = P(success) × judgment - P(failure) × adverse costs - own costs
- Downside risk analysis
- Procedural risks:
  - Strike-out risk assessment
  - Summary judgment probability
  - Adverse costs orders likelihood

**Settlement Decision Analysis:**
- Compare: Settlement offer vs. Expected trial value
- Risk-adjusted settlement threshold
- Decision tree: Accept offer vs. Proceed to trial

**Implementation:**
- New module: `litassist/commands/risk/`
- Commands:
  - `la risk --matter LITIGATION-001 --analysis full`
  - `la risk --matter LITIGATION-001 --scenario "settle-at-20k"`
- LLM: o3-pro (probabilistic reasoning, extended thinking)
- Uses legal analysis from strategy/brainstorm outputs
- Output: Risk report + probability matrix + expected value calculations + decision recommendation

---

### P1-12: Multi-Model Cross-Checks [KEEP P1]
**Effort:** 8-10 hours
**Priority:** MEDIUM

**Purpose:** Quality assurance for critical litigation documents

**Rationale:**
- Court submissions must be perfect
- Cross-checks catch reasoning errors, hallucinations
- Precision requirement

**Capabilities:**
- Run critical documents through 2+ models independently
- Compare reasoning paths (not just conclusions)
- Flag disagreements for human review
- Confidence scoring based on agreement
- Model specialization:
  - Claude Sonnet 4.6: Legal reasoning, strategy
  - GPT-5: Verification, fact-checking
  - o3-pro: Extended reasoning, probability

**Use Cases:**
- Court submissions (affidavits, applications, submissions)
- Settlement offer analysis
- Defense response strategy
- High-stakes correspondence

**Implementation:**
- Extend existing verification system in `litassist/verification_chain.py`
- New flag: `la verify --input submission.md --cross-check --matter LITIGATION-001`
- Output: Agreement level + disagreements highlighted + confidence score

---

### P1-13: Temporal Integrity Score (TIS) [KEEP P1]
**Effort:** 12-15 hours
**Priority:** MEDIUM

**Purpose:** Ensure all legal authorities are current law

**Rationale:**
- CRITICAL FOR PRECISION
- Citing overruled precedent = malpractice
- Courts may rely on outdated authorities

**Capabilities:**
- Per-citation freshness assessment
- Treatment classification: followed, distinguished, overruled, superseded
- Fetch citing cases from JADE/AustLII (via Google CSE + scraping)
- LLM analysis of case treatment
- Aggregate TIS per document
- Warnings: overruled, distinguished, superseded, aged (>10 years with no treatment)

**Technical Implementation:**
1. Google CSE: Search "citing:[CITATION]" on JADE
2. Scraping: Fetch full text of citing cases
3. LLM (Claude Sonnet 4.6): Analyze treatment
4. Calculate TIS score: Recency + Treatment

**Implementation:**
- Extend `citation/verify.py` with TIS module
- New module: `litassist/citation/temporal.py`
- Commands:
  - `la verify --input legal_memo.md --tis --threshold 70`
  - `la tis --citation "[2020] HCA 15"` (single citation analysis)
- Output: Per-citation TIS + aggregate document score + warnings + recommendations

---

### P1-14: Evidence Chain Tracker [NEW]
**Effort:** 10-12 hours
**Priority:** MEDIUM

**Purpose:** Track evidence systematically for litigation matters

**Rationale:**
- Complex causes of action require systematic proof chains
- Need evidence compilation and gap analysis

**Capabilities:**
- Track exhibits by category:
  - Ownership/contractual evidence
  - Performance/breach evidence
  - Demand/notice evidence
  - Loss/damage evidence
- Link evidence to facts and causes of action
- Identify gaps
- Exhibit preparation (numbering, descriptions)
- Chronological evidence timeline
- Witness evidence mapping (who can prove what)

**Implementation:**
- Part of Matter Memory: `matters/LITIGATION-001/evidence/`
- Commands:
  - `la evidence --matter LITIGATION-001 --add exhibit_a.pdf --category ownership --fact "Contract executed"`
  - `la evidence --matter LITIGATION-001 --gaps` (identify missing evidence)
  - `la evidence --matter LITIGATION-001 --chain "breach"` (show evidence chain)
- Output: Evidence registry + gap analysis + exhibit list

---

## PHASE 4: SECONDARY MATTERS (Sprint 5)
**Duration:** 55-67 hours (includes P2-19 Bias Divergence Detector: 10-12h)
**Goal:** Professional complaints, FOI, administrative matters, quality assurance

### P2-15: Professional Complaint Support [NEW]
**Effort:** 10-12 hours
**Priority:** MEDIUM

**Purpose:** Strategic guidance for professional complaints (legal services, medical, etc.)

**Rationale:**
- Professional complaint processes are jurisdiction-specific
- Evidence compilation and strategic timing matter

**Capabilities:**
- Complaint process guidance:
  - Investigation stages
  - Evidence requirements
  - Response strategies
  - Typical outcomes and timelines
- Evidence compilation:
  - Organize supporting evidence
  - Link evidence to complaint grounds
  - Identify evidence gaps
- Strategic advice:
  - When to provide additional evidence
  - How to respond to requests
  - Settlement vs. hearing decision support
- Jurisdiction-specific compliance

**Implementation:**
- New module: `litassist/commands/complaint/`
- Commands:
  - `la complaint --matter COMPLAINT-001 --stage investigation`
  - `la complaint --matter COMPLAINT-001 --evidence-compile`
- LLM: Claude Sonnet 4.6 (process knowledge)
- Output: Process guidance + evidence checklist + strategic advice

---

### P2-16: FOI Strategic Advisor [DEMOTED FROM P0, ENHANCED]
**Effort:** 12-15 hours (Commonwealth), +4-6h per jurisdiction
**Priority:** MEDIUM

**Purpose:** Strategic FOI planning and tactical guidance

**Rationale:**
- FOI matters require strategic approach, not just timeline tracking
- Agency delay tactics are predictable

**Capabilities:**

**Strategic Planning:**
- Analyze request scope, optimal framing
- Identify high-value vs. low-value documents
- Recommend FOI Act sections to invoke
- Timing strategy

**Tactical Response:**
- Analyze agency responses (delays, partial releases, exemptions)
- Counter-tactics for agency delay strategies
- Extension negotiation recommendations
- Deemed refusal vs. negotiation decision support
- OAIC/tribunal appeal strategy and timing

**Timeline Tracking:**
- Statutory clocks (extensions, deemed refusals, deadlines)
- Review milestones
- Multiple matters coordination

**Implementation Stages:**

**Stage 1 (Commonwealth FOI):** 8-10 hours
- New module: `litassist/commands/foi/`
- Commands:
  - `la foi --type strategy --input agency_decision.pdf`
  - `la foi --type timeline --lodged 2025-01-15 --matter FOI-001`
  - `la foi --import foi_log.csv` (CSV import)
- LLM: Claude Sonnet 4.6
- Output: Strategic advice + timeline table + draft correspondence

**Stage 2 (QLD RTI):** 4-6 hours
**Stage 3 (ACT FOI):** 4-6 hours
**Stage 4 (Gmail Integration):** 6-8 hours - SEPARATE FEATURE (Phase 6)

---

### P2-17: Administrative Complaint Drafter [NEW]
**Effort:** 8-10 hours
**Priority:** MEDIUM-LOW

**Purpose:** Draft administrative complaints to government agencies

**Rationale:**
- Government agency complaints have specific formats
- Evidence compilation and timing matter

**Capabilities:**
- Analyze background information
- Identify potential complaint grounds
- Draft complaint:
  - Grounds for complaint
  - Evidence compilation
  - Relevant statutory sections
  - Procedural requirements
- Strategic timing advice
- Risk assessment

**Implementation:**
- New module: `litassist/commands/admin/`
- Commands:
  - `la admin --type complaint --agency DHA`
  - `la admin --draft --evidence-from matters/FOI-001/`
- LLM: Claude Sonnet 4.6 + o3-pro (strategic timing)
- Output: Draft complaint + evidence checklist + strategic timing advice

---

### P2-18: Cost-of-Obstruction Ledger [KEEP P2]
**Effort:** 8-10 hours
**Priority:** LOW (triggered by events)

**Purpose:** Track incremental costs from opponent delay tactics

**Rationale:**
- Document delay tactics for costs orders
- Pre-judgment interest calculation

**Capabilities:**
- Track timeline delays and costs incurred
- Categorize obstruction:
  - Late defenses/responses
  - Frivolous applications
  - Discovery abuse
  - Needless adjournments
- Calculate incremental costs per delay
- Pre-judgment interest calculation
- Costs orders argument preparation
- Pattern documentation for indemnity costs application

**Implementation:**
- New module: `litassist/commands/costs/`
- Commands:
  - `la costs --matter LITIGATION-001 --track-obstruction`
  - `la costs --matter LITIGATION-001 --event "late defense filed" --delay 15 --cost 500`
- CSV export for evidence
- Output: Obstruction ledger + costs breakdown + pre-judgment interest + indemnity costs argument

---

### P2-19: Bias Divergence Detector [NEW - from research map]
**Effort:** 10-12 hours
**Priority:** MEDIUM
**Dependency:** Requires P1-12 Multi-Model Cross-Checks

**Purpose:** Detect uncertainty by comparing model outputs on bias-sensitive issues

**Rationale:**
- Inspired by systematic-investing research: model divergence signals uncertainty
- Where models disagree, human review is warranted
- Reduces overconfidence in LLM outputs

**Capabilities:**
- Run same prompt through 2-3 models independently
- Compare outputs for substantive divergence (not just wording)
- Flag areas where models disagree as requiring human review
- Use divergence as "uncertainty interval" indicator
- Confidence scoring based on agreement level

**Use Cases:**
- Risk assessments where bias could affect probability estimates
- Strategic advice where different models suggest different approaches
- Settlement recommendations where stakes are high

**Implementation:**
- Extend `litassist/verification_chain.py` with divergence detection
- New module: `litassist/verification/divergence.py`
- Commands:
  - `la verify --input strategy.md --divergence-check`
  - `la verify --input risk_assessment.md --divergence-check --models claude,gpt5,o3`
- LLM: Run through Claude Sonnet 4.6, GPT-5.5, and optionally o3-pro
- Output: Divergence report + agreement/disagreement matrix + confidence score + flagged sections

---

## PHASE 5: PRECISION TOOLS (Sprint 6)
**Duration:** 28-40 hours (includes P3-22 Simulated-Adversary Drafts: 8-10h)
**Goal:** Citation quality, compliance, and robustness testing

### P3-19: Pinpoint Validation [KEEP P3]
**Effort:** 6-8 hours
**Priority:** MEDIUM

**Purpose:** Verify paragraph numbers in citations

**Capabilities:**
- Detect paragraph symbols, ranges
- Fetch case document, verify paragraph exists
- Degrade to nearest match with warning
- Show corrections

**Citation Integrity Scoring (integrated from research map):**
- Combined with P3-20 to produce `citation_integrity_score` (0-100)
- Score components:
  - Format correctness (AGLC compliance)
  - Database verification status
  - Pinpoint accuracy
  - Currency (not overruled, from P1-13 TIS)

**Implementation:**
- Extend `citation/verify.py`
- Scrape via Google CSE + JADE/AustLII
- Output: Valid/Invalid + corrections + integrity score

---

### P3-20: AGLC Validator [KEEP P3]
**Effort:** 6-8 hours
**Priority:** MEDIUM

**Purpose:** Enforce Australian Guide to Legal Citation format

**Capabilities:**
- Normalize neutral citations
- Verify parallel cites
- Enforce pinpoint format
- Resolve JADE/AustLII URLs
- Contribute to citation integrity score (see P3-19)

**Implementation:**
- Extend `citation/verify.py`
- AGLC 4th edition rules
- Output: Format corrections + AGLC compliance score component

---

### P3-21: Cross-Source Concordance [KEEP P3]
**Effort:** 8-10 hours
**Priority:** MEDIUM

**Purpose:** Verify same authority across JADE + AustLII

**Capabilities:**
- Resolve each authority against two providers
- Record titles and URLs
- Flag disagreements
- Choose canonical by policy

**Implementation:**
- Extend `citation/verify.py`
- Two-provider verification via Google CSE + scraping
- Output: Concordance report

---

### P3-22: Simulated-Adversary Drafts [NEW - from research map]
**Effort:** 8-10 hours
**Priority:** MEDIUM
**Dependency:** Optional synergy with P1-9 Opponent Profiling

**Purpose:** Stress-test arguments by generating opposing counsel's likely response

**Rationale:**
- Identifies weaknesses before filing
- Anticipates opponent's counter-arguments
- Improves robustness of submissions

**Capabilities:**
- Take draft submission (application, affidavit, submissions)
- Generate adversary's response using adversarial prompt
- Identify weaknesses in original draft
- Suggest strengthening changes
- Optional: Use opponent profile (from P1-9) for tailored simulation

**Adversary Simulation:**
- Counter-arguments to each point
- Procedural challenges (standing, jurisdiction, timeliness)
- Factual challenges (credibility, gaps, contradictions)
- Legal challenges (authority currency, distinguishing cases)
- Weakness severity rating (critical / major / minor)

**Implementation:**
- New module: `litassist/commands/adversary/`
- Commands:
  - `la adversary --input submission.md --matter LITIGATION-001`
  - `la adversary --input submission.md --opponent "Counsel A"` (uses profile)
  - `la draft --input case_facts.md --adversary-test` (integrated mode)
- LLM: Claude Sonnet 4.6 (adversarial reasoning) + GPT-5.5 (weakness identification)
- Output: Adversary response + weakness report + strengthening recommendations

---

## PHASE 6: INFRASTRUCTURE (Sprint 7)
**Duration:** 25-35 hours
**Goal:** Technical polish and infrastructure

### P4-22: Verify Release Gate [REFRAMED]
**Effort:** 4-6 hours
**Priority:** LOW

**Purpose:** Quality checklist before sending critical documents

**Capabilities:**
- Aggregate verification errors
- Severity mapping (critical / major / minor)
- Pass/fail threshold (configurable)
- Pre-send checklist

**Implementation:**
- Extend existing verify command
- Command: `la verify --gate --input submission.md --threshold major`
- Output: Pass/fail + error summary

---

### P4-23: PDF Preflight Normalisation [KEEP P4]
**Effort:** 8-10 hours
**Priority:** LOW

**Purpose:** Ensure PDF text extraction quality

**Capabilities:**
- Text layer extraction + page mapping
- OCR fallback
- Glyph sanity checks
- Pass/fail signal

**Implementation:**
- Enhance existing `utils/file_ops.py:read_document()`
- Add OCR support
- Output: Extracted text + quality report

---

### P4-24: Retrieval Guardrails [SUPERSEDED]
**Status:** Obsolete. Removed when the RAG pipeline was deleted in the
`remove-pinecone-rag` branch (May 2026). `draft` is now a single
full-context call against the configured model; there is no retrieval
stage to guard. If hallucination control in long-context drafts becomes
a need, the right surface is the existing CoVe / citation-verification
chain in `litassist/verification_chain.py`, not a re-introduced
retrieval pipeline.

---

### P4-25: Glob Unification [DONE]
**Effort:** 2-3 hours
**Priority:** LOW

**Purpose:** Centralize glob pattern expansion

**Status:** Complete

**Implementation:**
- Glob expansion centralised in `utils/file_ops.py`
- `extractfacts`, `digest`, `draft`, and `counselnotes` route their FILE
  arguments through `expand_glob_patterns_callback`, matching `brainstorm`
  and `barbrief`
- Temporary `prompts/glob_help_addon.yaml` removed

**Completed (June 2026):**
- `strategy --strategies` is now a multiple-files interface (`multiple=True` via
  `expand_glob_newest_each_callback`): repeatable, one brainstorm set per flag,
  each flag resolving to its own newest match. `parse_strategies_files` merges the
  sets. This closes the last deferred item under P4-25.

---

### P4-26: FOI Gmail Integration [SEPARATE FEATURE]
**Effort:** 6-8 hours
**Priority:** LOW

**Purpose:** Automated FOI tracking via Gmail labels

**Capabilities:**
- OAuth authentication
- Label-based tracking
- Automatic deadline extraction

**Implementation:**
- Extend FOI module
- Commands: `la foi --setup-gmail`, `la foi --sync-gmail`
- Output: Synced correspondence + extracted deadlines

---

## DEPRIORITISED (Phase 7+)

### DEP-27: Evidence-Pack Exporter / Court Document Bundling
**Effort:** 15-20 hours
**Priority:** SUPER LOW

**Purpose:** Automated trial bundle preparation
**Status:** Deferred indefinitely

---

### DEP-28: Judge Analytics
**Effort:** 20-30 hours
**Priority:** NONE (productization)

**Purpose:** Judge decision pattern analysis
**Status:** Deprioritized - productization feature

---

### DEP-29: Web UI / Packaging
**Effort:** 40-60 hours
**Priority:** NONE (productization)

**Purpose:** Web interface, external packaging
**Status:** Deprioritized - possible in 1+ years

---

## Implementation Notes

### Example Matter Structure

```bash
# Example matter types
la matter create LITIGATION-001 --type litigation --court "ACT Magistrates Court"
la matter create COMPLAINT-001 --type complaint --agency QLSC
la matter create FOI-001 --type foi-review --agency OAIC
```

### Opponent Profile Examples

```bash
# Example profiles
la profile --create "Opponent A" --type individual
la profile --create "Counsel A" --type lawyer
la profile --create "Agency A" --type government
```

### FOI Implementation Staging

**Stage 1:** Commonwealth FOI + CSV import (8-10h)
**Stage 2:** QLD RTI (4-6h)
**Stage 3:** ACT FOI (4-6h)
**Stage 4:** Gmail integration (6-8h) - SEPARATE

### LLM Strategy by Use Case

**Note:** For current model assignments and upgrade recommendations, see `LLM_USE_REVIEW_AND_MODEL_RECOMMENDATIONS_2026-02.md` (more recent and authoritative).

**Strategic Reasoning & Legal Analysis:**
- Model: Claude Sonnet 4.6
- Use Cases: Correspondence analysis, legal reasoning, strategy generation
- Rationale: Cost-effective, 80% cost reduction

**Critical Verification:**
- Model: GPT-5.5
- Use Cases: Document verification, cross-checks
- Rationale: <1% hallucination rate

**Extended Reasoning & Probability:**
- Model: o3-pro
- Use Cases: Tactical planning, risk assessment, probability calculations
- Rationale: Extended thinking for complex decisions

---

## Confidence Assessment

**Overall Confidence: 0.88**

### High Confidence (0.92+)
- Feature relevance for active litigation
- Current codebase can support these features
- Matter Memory is foundational
- API research conclusions

### Medium-High Confidence (0.85-0.90)
- Effort estimates (based on similar existing commands)
- LLM model choices (proven in existing commands)
- Implementation approach

### Medium Confidence (0.75-0.85)
- TIS accuracy (treatment classification by LLM)
- Risk assessment probability calibration
- Opponent profiling effectiveness

### Lower Confidence (0.60-0.70)
- Negotiation strategy quality
- Evidence Chain Tracker adoption

---

## Next Steps

**Sprint 1 Sequence:**
1. Matter Memory Module (15-18h)
2. ACT Court Procedures Calculator (8-10h)
3. Letter Doctor (8-10h)
4. Legal Correspondence Analyzer (10-12h)

**Total Phase 1 Effort:** 40-50 hours

---

**Status:** Strategic planning; roadmap items are aspirational unless marked DONE, PARTIALLY SUPERSEDED, or already implemented elsewhere
**Next Review:** After Phase 1 completion
