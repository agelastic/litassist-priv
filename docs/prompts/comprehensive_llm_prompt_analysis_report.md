# Comprehensive LLM Prompt Analysis Report

**Last Updated**: July 20, 2025
**Note**: This is a historical analysis document. Model references reflect pre-October 2025 configurations. Current models (October 2025): GPT-5 Pro/GPT-5 for verification, Claude Sonnet 4.5 for legal reasoning, Grok 4 for creative strategies, o3-pro for technical drafting.

## I. Introduction
This report provides a comprehensive analysis of the LLM prompts used in the LitAssist tool. It covers identified prompts, their associated commands, purposes, effectiveness, suggested improvements, and an evaluation of the LLM models used for each.

---

## II. Identified LLM Prompts, Commands, and Purposes
### base.australian_law
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: all
- **Purpose**: To ensure all LLM outputs adhere to Australian law and use Australian English.
- **Full Prompt Text**:
  ```yaml
  Australian law only. Use Australian English spellings and terminology.
  ```

### base.citation_standards
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: all
- **Purpose**: To enforce proper Australian citation formats for all legal documents.
- **Full Prompt Text**:
  ```yaml
  Cite all cases with proper Australian citation format. Include year, court, and case number.
  ```

### base.accuracy_standards
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: all
- **Purpose**: To ensure all factual information provided by the LLM is accurate and verifiable.
- **Full Prompt Text**:
  ```yaml
  Ensure all facts are accurate and verifiable. Do not invent or assume information.
  ```

### base.verification_standards
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: all
- **Purpose**: To ensure all legal citations are verifiable on specified Australian legal databases and legal principles have authority.
- **Full Prompt Text**:
  ```yaml
  All citations must be verifiable on AustLII or BarNet Jade. All legal principles must have supporting authority.
  ```

### commands.extractfacts.system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: extractfacts
- **Purpose**: System prompt for the 'extractfacts' command, instructing it to extract facts precisely under headings and handle missing information.
- **Full Prompt Text**:
  ```yaml
  Australian law only. Extract factual information precisely under the requested headings. If information is not available for a heading, write 'Not specified' or 'To be determined'.
  ```

### commands.lookup.system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: System prompt for the 'lookup' command, emphasizing Australian law, source citation, and well-structured, concise responses focused on Victorian or federal law.
- **Full Prompt Text**:
  ```yaml
  Australian law only. Cite sources. Provide well-structured, concise responses focused on Victorian or federal law.
  ```

### commands.brainstorm.system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: brainstorm
- **Purpose**: General system prompt for the 'brainstorm' command, focusing on practical, actionable Australian legal strategies, balancing creativity with accuracy, and requiring a definitive recommendation.
- **Full Prompt Text**:
  ```yaml
  Australian law only. Provide practical, actionable legal strategies. Balance creativity with factual accuracy. When suggesting strategies, clearly distinguish between established legal approaches and more innovative options. For orthodox strategies, cite relevant case law or legislation. For unorthodox strategies, acknowledge any legal uncertainties or risks. Maintain logical structure throughout your response. End with a clear, definitive recommendation section without open-ended statements.
  ```

### commands.brainstorm.orthodox_system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: brainstorm
- **Purpose**: System prompt for generating 'orthodox' strategies in the 'brainstorm' command, emphasizing conservative, well-established approaches with strong precedential support.
- **Full Prompt Text**:
  ```yaml
  Australian law only. Provide conservative, well-established legal strategies with strong precedential support. Cite relevant case law or legislation for each strategy. Focus on proven approaches with minimal legal risk.
  ```

### commands.brainstorm.unorthodox_system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: brainstorm
- **Purpose**: System prompt for generating 'unorthodox' strategies in the 'brainstorm' command, encouraging creative, innovative approaches while acknowledging uncertainties.
- **Full Prompt Text**:
  ```yaml
  Australian law only. Provide creative, innovative legal strategies that push boundaries. Acknowledge legal uncertainties and risks. Suggest novel approaches while maintaining ethical boundaries.
  ```

### commands.brainstorm.analysis_system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: brainstorm
- **Purpose**: System prompt for the analysis phase of the 'brainstorm' command, instructing objective analysis of strategies based on merit, support, and likelihood.
- **Full Prompt Text**:
  ```yaml
  Australian law only. Analyze strategies objectively. Consider legal merit, factual support, precedential strength, and judicial likelihood. Provide clear reasoning for selections.
  ```

### commands.strategy.system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: strategy
- **Purpose**: System prompt for the 'strategy' command, defining the persona as an Australian civil litigation expert focused on specific courts, analyzing facts for strategic options.
- **Full Prompt Text**:
  ```yaml
  Australian civil litigation expert focusing on Family Court, Federal Circuit Court, and state Supreme Courts. You must analyze case facts and produce strategic options for achieving a specific outcome.
  ```

### commands.strategy.ranking_system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: strategy
- **Purpose**: System prompt for ranking strategies objectively for a specific outcome within the 'strategy' command.
- **Full Prompt Text**:
  ```yaml
  Australian law only. Rank strategies objectively for the specific outcome.
  ```

### commands.draft.system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: draft
- **Purpose**: System prompt for the 'draft' command, setting the persona as a senior Australian barrister drafting high-quality, compliant legal documents.
- **Full Prompt Text**:
  ```yaml
  You are a senior Australian barrister with expertise in drafting high-quality legal documents. Create professional, well-structured documents that comply with Australian court rules and legal conventions.
  ```

### commands.digest.system
- **File Location**: `litassist/prompts/base.yaml`
- **Associated Command(s)**: digest
- **Purpose**: System prompt for the 'digest' command, requiring logical structure, clear headings, bullet points, and concise summaries under Australian law.
- **Full Prompt Text**:
  ```yaml
  Australian law only. Structure your response logically with clear headings, bullet points and concise summaries.
  ```

### documents.statement_of_claim
- **File Location**: `litassist/prompts/documents.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Provides a template structure for a Statement of Claim.
- **Full Prompt Text**:
  ```yaml
  IN THE {court_name}
  FILE NO: {file_number}

  BETWEEN:

  {plaintiff_name}
                                                  Plaintiff

  AND:

  {defendant_name}
                                                  Defendant

  STATEMENT OF CLAIM

  The Plaintiff claims:

  1. [First claim with particulars]

  2. [Second claim with particulars]

  3. [Additional claims as needed]

  AND THE PLAINTIFF CLAIMS:

  (a) [Specific relief sought]
  (b) [Additional relief]
  (c) Interest pursuant to [relevant provision]
  (d) Costs
  (e) Such further or other relief as this Honourable Court deems just

  DATED: [Date]

  [Signature block]
  ```

### documents.originating_application
- **File Location**: `litassist/prompts/documents.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Provides a template structure for an Originating Application.
- **Full Prompt Text**:
  ```yaml
  IN THE {court_name}
  FILE NO: {file_number}

  IN THE MATTER OF [relevant Act/Rules]

  AND IN THE MATTER OF [specific provision]

  BETWEEN:

  {applicant_name}
                                                  Applicant

  AND:

  {respondent_name}
                                                  Respondent

  ORIGINATING APPLICATION

  The Applicant applies for the following orders:

  1. [First order sought]

  2. [Second order sought]

  3. [Additional orders as needed]

  The grounds of this application are:

  (a) [First ground with facts]

  (b) [Second ground with facts]

  (c) [Additional grounds as needed]

  This application is made in reliance on:
  - [Affidavit of X dated Y]
  - [Other supporting material]

  DATED: [Date]

  [Signature block]
  ```

### documents.affidavit
- **File Location**: `litassist/prompts/documents.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Provides a template structure for an Affidavit.
- **Full Prompt Text**:
  ```yaml
  IN THE {court_name}
  FILE NO: {file_number}

  BETWEEN:

  {party_1_name}
                                                  {party_1_role}

  AND:

  {party_2_name}
                                                  {party_2_role}

  AFFIDAVIT OF {deponent_name}

  I, {deponent_full_name}, {deponent_occupation} of {deponent_address}, STATE ON OATH/AFFIRM:

  1. I am the {deponent_role} in these proceedings and make this affidavit from my own knowledge except where otherwise stated.

  2. Where I depose to matters based on information and belief, I identify the source of that information and believe those matters to be true.

  3. [Substantive paragraphs with facts]

  4. [Additional paragraphs as needed]

  SWORN/AFFIRMED at {location} )
  in the State of {state}        )
  on {date}                      )

  Before me:

  _______________________         _______________________
  Signature of Deponent           Signature of Witness

  _______________________
  Name and qualification of witness
  ```

### documents.notice_of_motion
- **File Location**: `litassist/prompts/documents.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Provides a template structure for a Notice of Motion.
- **Full Prompt Text**:
  ```yaml
  IN THE {court_name}
  FILE NO: {file_number}

  BETWEEN:

  {moving_party}
                                                  {moving_party_role}

  AND:

  {responding_party}
                                                  {responding_party_role}

  NOTICE OF MOTION

  TAKE NOTICE that the {moving_party_role} will move this Honourable Court at {time} on {date} at {court_address} for the following orders:

  1. [First order sought]

  2. [Second order sought]

  3. [Additional orders as needed]

  4. Such further or other orders as the Court deems fit

  5. Costs

  This motion will be made on the grounds set out in the supporting affidavit of {deponent} filed herewith.

  DATED: [Date]

  [Signature block]
  ```

### documents.outline_submissions
- **File Location**: `litassist/prompts/documents.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Provides a template structure for an Outline of Submissions.
- **Full Prompt Text**:
  ```yaml
  IN THE {court_name}
  FILE NO: {file_number}

  BETWEEN:

  {party_1}
                                                  {party_1_role}

  AND:

  {party_2}
                                                  {party_2_role}

  {PARTY_ROLE}'S OUTLINE OF SUBMISSIONS

  I. INTRODUCTION

  1. [Brief overview of the matter and issues]

  II. STATEMENT OF FACTS

  2. [Relevant factual background]

  III. ISSUES

  3. The issues for determination are:
     (a) [First issue]
     (b) [Second issue]
     (c) [Additional issues]

  IV. ARGUMENT

  A. [First Issue Heading]

  4. [Legal submissions on first issue]

  B. [Second Issue Heading]

  5. [Legal submissions on second issue]

  V. CONCLUSION

  6. For the reasons set out above, the {Party} respectfully submits that [orders sought].

  DATED: [Date]

  [Counsel's name]
  Counsel for the {Party}
  ```

### documents.interlocutory_application
- **File Location**: `litassist/prompts/documents.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Provides a template structure for an Interlocutory Application.
- **Full Prompt Text**:
  ```yaml
  IN THE {court_name}
  FILE NO: {file_number}

  BETWEEN:

  {applicant}
                                                  Applicant

  AND:

  {respondent}
                                                  Respondent

  INTERLOCUTORY APPLICATION

  The Applicant applies for:

  1. [Urgent/interim relief sought]

  2. [Additional orders]

  3. That the costs of this application be [costs order sought]

  GROUNDS:

  This application is made on the following grounds:

  1. [Urgency/special circumstances]

  2. [Legal basis for relief]

  3. [Balance of convenience/irreparable harm]

  EVIDENCE:

  This application is supported by:
  - Affidavit of [name] sworn/affirmed [date]
  - [Other evidence]

  SERVICE:

  This application has been/will be served on [parties] by [method] on [date].

  DATED: [Date]

  [Signature block]
  ```

### formats.case_facts_10_heading
- **File Location**: `litassist/prompts/formats.yaml`
- **Associated Command(s)**: extractfacts, strategy
- **Purpose**: Defines a 10-heading structure for organizing case facts.
- **Full Prompt Text**:
  ```yaml
  1. **Parties**: Identify all parties involved in the matter, including their roles and relevant characteristics
  2. **Background**: Provide context about the relationship between parties and circumstances leading to the dispute
  3. **Key Events**: List significant events in chronological order with dates where available
  4. **Legal Issues**: Enumerate the legal questions that need to be addressed
  5. **Evidence Available**: Catalog all available evidence, documents, and potential witnesses
  6. **Opposing Arguments**: Summarize the other party's position and claims
  7. **Procedural History**: Detail any court proceedings, orders, or legal steps taken to date
  8. **Jurisdiction**: Specify the relevant court or tribunal and basis for jurisdiction
  9. **Applicable Law**: List relevant statutes, regulations, and legal principles
  10. **Client Objectives**: State what the client hopes to achieve
  ```

### formats.strategic_options
- **File Location**: `litassist/prompts/formats.yaml`
- **Associated Command(s)**: brainstorm, strategy
- **Purpose**: Defines the output format for presenting strategic options.
- **Full Prompt Text**:
  ```yaml
  **[Strategy Title]**
  - **Approach:** [Brief description]
  - **Legal Basis:** [Relevant law/precedent]
  - **Likelihood:** [High/Medium/Low with reasoning]
  - **Timeline:** [Expected duration]
  - **Resources:** [Required resources]
  - **Risks:** [Key risks and mitigation]
  ```

### formats.irac_structure
- **File Location**: `litassist/prompts/formats.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Defines the IRAC (Issue, Rule, Application, Conclusion) structure for legal analysis.
- **Full Prompt Text**:
  ```yaml
  **Issue**: [Legal question to be resolved]
  **Rule**: [Applicable law, statute, or precedent]
  **Application**: [How the law applies to these facts]
  **Conclusion**: [The likely legal outcome]
  ```

### formats.chronological_summary
- **File Location**: `litassist/prompts/formats.yaml`
- **Associated Command(s)**: digest
- **Purpose**: Defines the format for a chronological summary.
- **Full Prompt Text**:
  ```yaml
  **CHRONOLOGICAL SUMMARY**

  - **[Date]**: [Event description]
  - **[Date]**: [Event description]
  - **[Date]**: [Event description]
  ```

### formats.citation_extraction
- **File Location**: `litassist/prompts/formats.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Defines the format for extracting and listing citations (cases and legislation).
- **Full Prompt Text**:
  ```yaml
  **CITATIONS**

  Cases:
  - [Case Name] [Year] [Court] [Citation]
  - [Case Name] [Year] [Court] [Citation]

  Legislation:
  - [Act Name] [Year] [Jurisdiction] s [Section]
  - [Act Name] [Year] [Jurisdiction] s [Section]
  ```

### formats.principles_extraction
- **File Location**: `litassist/prompts/formats.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Defines the format for extracting legal principles with supporting authorities.
- **Full Prompt Text**:
  ```yaml
  **LEGAL PRINCIPLES**

  1. [Principle statement] - [Supporting case/statute]
  2. [Principle statement] - [Supporting case/statute]
  3. [Principle statement] - [Supporting case/statute]
  ```

### formats.checklist_extraction
- **File Location**: `litassist/prompts/formats.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Defines the format for extracting practical checklist items.
- **Full Prompt Text**:
  ```yaml
  **PRACTICAL CHECKLIST**

  □ [Action item with specific requirement]
  □ [Evidence needed with description]
  □ [Procedural step with deadline]
  □ [Document to obtain or prepare]
  ```

### lookup.research_assistant.system_prompt
- **File Location**: `litassist/prompts/lookup.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: System prompt for the Jade.io research aspect of the 'lookup' command, reiterating focus on Australian law, citations, structure, and conciseness.
- **Full Prompt Text**:
  ```yaml
  system_prompt: |
    Australian law only. Cite sources. Provide well-structured, concise responses focused on Victorian or federal law.
  ```

### lookup.extraction_instructions.citations
- **File Location**: `litassist/prompts/lookup.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Provides specific instructions when citation extraction is requested with the 'lookup' command.
- **Full Prompt Text**:
  ```yaml
  citations: |
    Also provide a clear 'CITATIONS' section that lists all case citations and legislation references in a format easy to copy and use.
  ```

### lookup.extraction_instructions.principles
- **File Location**: `litassist/prompts/lookup.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Provides specific instructions when legal principles extraction is requested with the 'lookup' command.
- **Full Prompt Text**:
  ```yaml
  principles: |
    Also provide a clear 'LEGAL PRINCIPLES' section that lists the key legal rules and principles in a structured format suitable for advice letters.
  ```

### lookup.extraction_instructions.checklist
- **File Location**: `litassist/prompts/lookup.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Provides specific instructions when checklist extraction is requested with the 'lookup' command.
- **Full Prompt Text**:
  ```yaml
  checklist: |
    Also provide a clear 'PRACTICAL CHECKLIST' section that lists actionable requirements, evidence needed, and steps to take.
  ```

### lookup.comprehensive_analysis.requirements
- **File Location**: `litassist/prompts/lookup.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Defines requirements for a comprehensive analysis in the 'lookup' command, including thorough review, authority hierarchy, and jurisdictional variations.
- **Full Prompt Text**:
  ```yaml
  requirements: |
    EXHAUSTIVE ANALYSIS REQUIREMENTS:
    - Review ALL provided sources thoroughly (expect 20-40 sources)
    - Identify primary and secondary authorities with hierarchy
    - Cross-reference between sources for consistency/conflicts
    - Include minority opinions and dissenting views where relevant
    - Distinguish binding vs persuasive authorities by jurisdiction
    - Analyze temporal evolution of legal principles
    - Consider jurisdictional variations across Australian states/territories
  ```

### lookup.comprehensive_analysis.citation_requirements
- **File Location**: `litassist/prompts/lookup.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Defines specific citation requirements for comprehensive analysis in 'lookup', such as parallel citations and distinguishing ratio/obiter.
- **Full Prompt Text**:
  ```yaml
  citation_requirements: |
    COMPREHENSIVE CITATION REQUIREMENTS:
    - Cite ALL relevant cases from the sources with parallel citations
    - Reference specific paragraphs/sections when applicable
    - Distinguish between ratio decidendi and obiter dicta
    - Group citations by authority level (High Court → Federal → State)
  ```

### lookup.comprehensive_analysis.output_structure
- **File Location**: `litassist/prompts/lookup.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Defines a detailed output structure for comprehensive analysis in 'lookup'.
- **Full Prompt Text**:
  ```yaml
  output_structure: |
    EXHAUSTIVE OUTPUT STRUCTURE:
    - Executive Summary (2-3 paragraphs)
    - Comprehensive Legal Framework
    - Authority Hierarchy Analysis
    - Detailed Case Analysis by jurisdiction
    - Synthesis and Conflicts Resolution
    - Practical Application with confidence levels
    - Conclusion with Confidence Assessment
  ```

### lookup.standard_analysis.instructions
- **File Location**: `litassist/prompts/lookup.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Provides instructions for standard analysis in the 'lookup' command (when not using '--comprehensive').
- **Full Prompt Text**:
  ```yaml
  instructions: |
    Cite sources. Analyze the provided sources (typically 5) to provide well-structured, comprehensive responses with clear sections. Begin with a summary, then provide analysis with supporting case law from all relevant sources, and end with a definitive conclusion. Cross-reference between sources where applicable.
  ```

### lookup.standard_user_template
- **File Location**: `litassist/prompts/lookup.yaml`
- **Associated Command(s)**: lookup
- **Purpose**: Formats the user's question and provided links for the 'lookup' command.
- **Full Prompt Text**:
  ```yaml
  standard_user_template: |
    Question: {question}
    Links:
    {links}
  ```

### processing.digest.summary_mode
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: digest
- **Purpose**: Instructs the 'digest' command to create a chronological summary with a specific format.
- **Full Prompt Text**:
  ```yaml
  summary_mode: |
    Create a chronological summary of the document focusing on key events, dates, and parties. Structure as:

    **CHRONOLOGICAL SUMMARY**

    - **[Date]**: [Event description]
    - **[Date]**: [Event description]
    - **[Date]**: [Event description]

    Include all significant developments, procedural steps, and factual events in chronological order.
  ```

### processing.digest.issues_mode
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: digest
- **Purpose**: Instructs the 'digest' command to identify and analyze legal issues with a specific structure.
- **Full Prompt Text**:
  ```yaml
  issues_mode: |
    Identify and analyze legal issues present in the document. Structure as:

    **LEGAL ISSUES ANALYSIS**

    **Issue 1: [Issue Name]**
    - **Description:** [What the issue involves]
    - **Legal Framework:** [Relevant law/precedent]
    - **Analysis:** [Discussion of the issue]
    - **Significance:** [Why this matters]

    **Issue 2: [Issue Name]**
    [Same structure...]

    Focus on substantive legal questions, procedural issues, and areas requiring legal analysis.
  ```

### processing.digest.system_prompt
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: digest
- **Purpose**: General system prompt for the 'digest' command, focusing on comprehensive, accurate, well-organized extraction with a neutral tone.
- **Full Prompt Text**:
  ```yaml
  system_prompt: |
    Extract and organize information from this document. Focus on being comprehensive, accurate, and well-organized. Use clear paragraph structure and bullet points where appropriate. Maintain a neutral, analytical tone throughout.
  ```

### processing.draft.system_prompt_base
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Base system prompt for the 'draft' command, reiterating the persona of a senior Australian barrister.
- **Full Prompt Text**:
  ```yaml
  system_prompt_base: |
    You are a senior Australian barrister with expertise in drafting high-quality legal documents. Create professional, well-structured documents that comply with Australian court rules and legal conventions.
  ```

### processing.draft.context_case_facts_and_strategies
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Adds context to the 'draft' system prompt when both case facts and strategies are provided.
- **Full Prompt Text**:
  ```yaml
  context_case_facts_and_strategies: " You have been provided with structured case facts and legal strategies from brainstorming. Use the case facts as the factual foundation and consider the strategies when developing your arguments, particularly any marked as 'most likely to succeed'."
  ```

### processing.draft.context_case_facts_only
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Adds context to the 'draft' system prompt when only case facts are provided.
- **Full Prompt Text**:
  ```yaml
  context_case_facts_only: " You have been provided with structured case facts. Use these as the factual foundation for your draft."
  ```

### processing.draft.context_strategies_only
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Adds context to the 'draft' system prompt when only strategies are provided.
- **Full Prompt Text**:
  ```yaml
  context_strategies_only: " You have been provided with legal strategies from brainstorming. Consider these strategies, particularly any marked as 'most likely to succeed'."
  ```

### processing.draft.general_instructions
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Provides general drafting instructions regarding thoroughness, conciseness, accuracy, organization, citation, consistency, and avoiding speculation.
- **Full Prompt Text**:
  ```yaml
  general_instructions: " Be thorough but concise. Focus on legal accuracy, relevant precedents, and clear organization. Use section headings, numbered paragraphs, and proper legal citation format. Maintain internal consistency throughout and ensure all claims are supported by the provided context. Avoid speculation beyond the provided information."
  ```

### processing.draft.context_aware_prompt
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: draft
- **Purpose**: User-facing prompt template for the 'draft' command when context (facts/strategies) is provided, asking to draft a document type incorporating this context and meeting several quality criteria.
- **Full Prompt Text**:
  ```yaml
  context_aware_prompt: |
    Context from case analysis:
    {context}

    Draft a {document_type} that incorporates the strategic direction and legal arguments identified above. Ensure the document is:
    - Professionally formatted
    - Legally sound
    - Strategically aligned
    - Court-rule compliant
    - Evidence-based where applicable
  ```

### processing.draft.user_prompt_template
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: draft
- **Purpose**: Basic user-facing prompt template for the 'draft' command when a simple user request is made.
- **Full Prompt Text**:
  ```yaml
  user_prompt_template: |
    Draft a {document_type}: {user_request}
  ```

### processing.extraction.chunk_facts_prompt
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: extractfacts
- **Purpose**: Prompt for extracting raw facts from a document chunk during the 'extractfacts' process, listing fact categories.
- **Full Prompt Text**:
  ```yaml
  chunk_facts_prompt: |
    From this excerpt (part {chunk_num} of {total_chunks}), extract any facts relevant to:
    - Parties involved
    - Background/context
    - Key events with dates
    - Legal issues raised
    - Evidence mentioned
    - Arguments made
    - Procedural matters
    - Jurisdictional details
    - Applicable laws
    - Client objectives

    Just extract the raw facts found in this excerpt:
  ```

### processing.extraction.chunk_system_prompt
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: extractfacts
- **Purpose**: System prompt for processing a single chunk in 'extractfacts', emphasizing comprehensiveness but restricting to info in the excerpt.
- **Full Prompt Text**:
  ```yaml
  chunk_system_prompt: |
    Extract facts from this document excerpt. Be comprehensive but only include information actually present in this excerpt.
  ```

### processing.extraction.organize_facts_prompt
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: extractfacts
- **Purpose**: Prompt for organizing all extracted raw facts (from chunks) into the 10 standard headings.
- **Full Prompt Text**:
  ```yaml
  organize_facts_prompt: |
    Organize the following extracted facts into these 10 headings:

    {format_instructions}

    Raw facts to organize:
    {all_facts}

    Important:
    - Only include information that was actually in the document
    - If information for a heading is not available, write "Not specified in the document"
    - Maintain chronological order for events
    - Be comprehensive but factual
  ```

### processing.extraction.organize_system_prompt
- **File Location**: `litassist/prompts/processing.yaml`
- **Associated Command(s)**: extractfacts
- **Purpose**: System prompt for the fact organization step in 'extractfacts', emphasizing precision, consistency, and avoiding duplication.
- **Full Prompt Text**:
  ```yaml
  organize_system_prompt: |
    Organize the extracted facts precisely under the requested headings. Ensure consistency and avoid duplication.
  ```

### strategies.brainstorm.orthodox_prompt
- **File Location**: `litassist/prompts/strategies.yaml`
- **Associated Command(s)**: brainstorm
- **Purpose**: User prompt for generating 10 orthodox legal strategies in 'brainstorm', detailing characteristics and required output format for each.
- **Full Prompt Text**:
  ```yaml
  orthodox_prompt: |
    Generate 10 ORTHODOX legal strategies - established, conservative approaches that follow conventional wisdom and accepted practice. Focus on:

    - Precedent-based arguments
    - Traditional legal remedies
    - Conservative interpretations
    - Established case law
    - Standard procedural approaches
    - Well-settled legal principles
    - Conventional dispute resolution
    - Risk-averse strategies

    For each strategy, provide:
    1. Strategy name/title
    2. Brief description (2-3 sentences)
    3. Legal basis or precedent
    4. Likelihood of success
    5. Key considerations
  ```

### strategies.brainstorm.unorthodox_prompt
- **File Location**: `litassist/prompts/strategies.yaml`
- **Associated Command(s)**: brainstorm
- **Purpose**: User prompt for generating 10 unorthodox legal strategies in 'brainstorm', detailing characteristics and required output format.
- **Full Prompt Text**:
  ```yaml
  unorthodox_prompt: |
    Generate 10 UNORTHODOX legal strategies - creative, innovative approaches that think outside conventional frameworks. Focus on:

    - Novel legal arguments
    - Creative use of existing law
    - Innovative procedural approaches
    - Cross-jurisdictional precedents
    - Emerging legal principles
    - Strategic forum shopping
    - Unconventional remedy combinations
    - Disruptive legal theories

    For each strategy, provide:
    1. Strategy name/title
    2. Brief description (2-3 sentences)
    3. Legal basis or novel interpretation
    4. Risk assessment
    5. Innovation factor
  ```

### strategies.brainstorm.analysis_prompt
- **File Location**: `litassist/prompts/strategies.yaml`
- **Associated Command(s)**: brainstorm
- **Purpose**: User prompt for analyzing all generated strategies (orthodox and unorthodox) and selecting the 5 most promising ones, with detailed criteria and output requirements, plus a final recommendation.
- **Full Prompt Text**:
  ```yaml
  analysis_prompt: |
    Analyze ALL the strategies above and select EXACTLY 5 of the most promising strategies.

    **SELECTION CRITERIA:**
    - Legal merit and strength of precedent
    - Practical feasibility given available resources
    - Risk/reward ratio
    - Timeline considerations
    - Client objectives alignment
    - Jurisdictional factors
    - Available evidence strength

    **REQUIRED ANALYSIS:**
    For each of the 5 selected strategies, provide:
    1. **Why this strategy was selected** (detailed reasoning)
    2. **Implementation roadmap** (step-by-step approach)
    3. **Resource requirements** (time, cost, expertise needed)
    4. **Risk assessment** (potential downsides and mitigation)
    5. **Success probability** (realistic percentage with reasoning)

    **IMPORTANT:** You must return exactly 5 strategies. If you cannot find 5 high-quality strategies, you must still provide 5, but for the lower-quality ones, you must explicitly state why they are not recommended.

    **FINAL RECOMMENDATION:**
    Conclude with your #1 recommended strategy and a compelling 2-3 paragraph justification.
  ```

### strategies.brainstorm.regeneration_prompt
- **File Location**: `litassist/prompts/strategies.yaml`
- **Associated Command(s)**: brainstorm
- **Purpose**: User prompt for regenerating strategic analysis based on feedback, incorporating it while maintaining rigor and focus.
- **Full Prompt Text**:
  ```yaml
  regeneration_prompt: |
    Based on the following feedback: "{feedback}"

    Please regenerate the strategic analysis, incorporating this feedback while maintaining the same analytical rigor and Australian legal focus.

    {citation_instructions}
  ```

### strategies.strategy.strategic_options_instructions
- **File Location**: `litassist/prompts/strategies.yaml`
- **Associated Command(s)**: strategy
- **Purpose**: Provides exact formatting instructions for the strategic options section of the 'strategy' command output.
- **Full Prompt Text**:
  ```yaml
  strategic_options_instructions: |
    For the strategic options section, use EXACTLY this format:

    # STRATEGIC OPTIONS FOR: [OUTCOME IN CAPS]

    ## OPTION 1: [Title of Strategy]
    * **Probability of Success**: [X]%
    * **Principal Hurdles**:
      1. [Description of hurdle] — *[Case citation with pinpoint reference]*
      2. [Description of hurdle] — *[Case citation with pinpoint reference]*
    * **Critical Missing Facts**:
      - [Missing fact 1]
      - [Missing fact 2]

    ## OPTION 2: [Title of Strategy]
    [Same format as above]

    [Continue for 3-5 options total]

    Requirements:
    - Australian law only
    - Use real case citations with pinpoint references (e.g., Smith v Jones [2015] HCA 5 [27])
    - Be specific about probability percentages based on precedents
    - Identify genuine hurdles based on the case facts provided
    - Note actual missing facts from the case materials
    - Do not introduce facts not in the case materials
  ```

### strategies.strategy.next_steps_prompt
- **File Location**: `litassist/prompts/strategies.yaml`
- **Associated Command(s)**: strategy
- **Purpose**: Prompts for generating 5 immediate next steps based on the strategic options for the 'strategy' command.
- **Full Prompt Text**:
  ```yaml
  next_steps_prompt: |
    Based on the strategic options above, provide EXACTLY 5 immediate next steps that should be taken within the next 2-4 weeks. Format as:

    **IMMEDIATE NEXT STEPS (2-4 weeks):**

    1. **[Action Item]** - [Specific task description with timeline]
    2. **[Action Item]** - [Specific task description with timeline]
    3. **[Action Item]** - [Specific task description with timeline]
    4. **[Action Item]** - [Specific task description with timeline]
    5. **[Action Item]** - [Specific task description with timeline]

    Each step should be:
    - Specific and actionable
    - Have a clear timeline
    - Identify responsible party
    - Include expected outcome
  ```

### strategies.strategy.document_generation_context
- **File Location**: `litassist/prompts/strategies.yaml`
- **Associated Command(s)**: strategy
- **Purpose**: Provides context for document drafting if the 'strategy' command leads to a draft, linking it to the recommended strategy.
- **Full Prompt Text**:
  ```yaml
  document_generation_context: |
    Based on the strategic analysis above, the recommended approach is to proceed with: {recommended_strategy}

    This document should align with that strategic direction and incorporate the key legal arguments identified.

    Document requirements:
    - Follow Australian court formatting requirements
    - Use proper legal citations
    - Maintain professional tone
    - Include all required sections
    - Reference supporting evidence where applicable
  ```

### strategies.strategy.unique_title_requirement
- **File Location**: `litassist/prompts/strategies.yaml`
- **Associated Command(s)**: strategy
- **Purpose**: Instructs the LLM to use unique titles for each strategic approach in the 'strategy' command.
- **Full Prompt Text**:
  ```yaml
  unique_title_requirement: |
    CRITICAL: Use a UNIQUE TITLE that clearly distinguishes this strategic approach. Do not reuse titles from other options.
  ```

### verification.self_critique
- **File Location**: `litassist/prompts/verification.yaml`
- **Associated Command(s)**: brainstorm, draft, extractfacts, strategy
- **Purpose**: Prompts the LLM to identify and correct legal inaccuracies in its own output and ensure Australian English compliance.
- **Full Prompt Text**:
  ```yaml
  self_critique: |
    Identify and correct any legal inaccuracies above, and provide the corrected text only. Ensure all spellings follow Australian English conventions.
  ```

### verification.citation_retry_instructions
- **File Location**: `litassist/prompts/verification.yaml`
- **Associated Command(s)**: lookup, digest, extractfacts, brainstorm, strategy, draft
- **Purpose**: Provides enhanced instructions for citation accuracy when an LLM generation attempt needs a retry due to citation issues.
- **Full Prompt Text**:
  ```yaml
  citation_retry_instructions: |
    IMPORTANT: Use only real, verifiable Australian cases that exist in Australian legal databases. Do not invent case names. If unsure about a citation, omit it rather than guess.
  ```

### verification.light_verification
- **File Location**: `litassist/prompts/verification.yaml`
- **Associated Command(s)**: lookup, digest, extractfacts, brainstorm, strategy, draft
- **Purpose**: Prompts for a light verification focusing only on Australian English spelling and terminology compliance.
- **Full Prompt Text**:
  ```yaml
  light_verification: |
    Check only for Australian English spelling and terminology compliance.
    Correct any non-Australian English spellings or terminology.
  ```

### verification.heavy_verification
- **File Location**: `litassist/prompts/verification.yaml`
- **Associated Command(s)**: extractfacts, strategy
- **Purpose**: Prompts for a comprehensive legal accuracy review, including citations, reasoning, errors in law/procedure, and Australian English.
- **Full Prompt Text**:
  ```yaml
  heavy_verification: |
    Provide comprehensive legal accuracy review: verify all citations, check legal reasoning, identify any errors in law or procedure, and ensure Australian English compliance.
  ```

### verification.system_prompt
- **File Location**: `litassist/prompts/verification.yaml`
- **Associated Command(s)**: extractfacts, strategy
- **Purpose**: System prompt for heavy verification, establishing an 'Australian law expert' persona for thorough review.
- **Full Prompt Text**:
  ```yaml
  system_prompt: |
    Australian law expert. Thoroughly verify legal accuracy, citations, precedents, and reasoning.
  ```

---

## III. Analysis of Prompt Effectiveness
### base.australian_law
- **Effectiveness Assessment**: Highly effective. Clear, concise, and fundamental for a tool targeted at Australian legal practice. Its application to 'all' commands ensures consistency.

### base.citation_standards
- **Effectiveness Assessment**: Highly effective. Sets a clear standard for citations, crucial for legal document accuracy and verifiability. Broad application is appropriate.

### base.accuracy_standards
- **Effectiveness Assessment**: Highly effective. Critical for maintaining trust and reliability in a legal context. Prevents invention of information.

### base.verification_standards
- **Effectiveness Assessment**: Highly effective. Reinforces citation quality and the need for authoritative support for legal claims, vital for practical legal work.

### commands.extractfacts.system
- **Effectiveness Assessment**: Effective. Clearly defines the task, the expected output structure (though headings are detailed elsewhere), and how to manage missing data ('Not specified' or 'To be determined'). Aligns with the user guide's description of 'extractfacts' for structuring information.

### commands.lookup.system
- **Effectiveness Assessment**: Effective. Sets clear expectations for jurisdiction, citation, structure, and conciseness. Aligns with the 'lookup' command's purpose of rapid case-law search and structured legal answers.

### commands.brainstorm.system
- **Effectiveness Assessment**: Effective. Guides the LLM towards generating creative yet legally sound strategies, distinguishing orthodox/unorthodox approaches, and ensuring a clear output structure. Matches the user guide's description of 'brainstorm' for comprehensive strategy generation.

### commands.brainstorm.orthodox_system
- **Effectiveness Assessment**: Effective. Clearly defines 'orthodox' and directs the LLM to focus on low-risk, proven strategies with supporting citations. This is crucial for the 'brainstorm' command's ability to generate diverse strategy types.

### commands.brainstorm.unorthodox_system
- **Effectiveness Assessment**: Effective. Guides the LLM towards innovative thinking, pushing legal boundaries responsibly. Important for the 'brainstorm' command's creative ideation aspect.

### commands.brainstorm.analysis_system
- **Effectiveness Assessment**: Effective. Ensures a critical evaluation of the generated strategies, which is key to the 'brainstorm' command's goal of identifying 'most likely to succeed' options.

### commands.strategy.system
- **Effectiveness Assessment**: Effective. Establishes a clear expert persona and task (analyzing case facts for strategic options to achieve a specific outcome). Aligns with the user guide's description of 'strategy' for tactical implementation plans.

### commands.strategy.ranking_system
- **Effectiveness Assessment**: Effective. Focuses the LLM on objective ranking, which is a key part of the 'strategy' command's analysis to provide actionable, prioritized options.

### commands.draft.system
- **Effectiveness Assessment**: Effective. Creates a strong persona focused on quality, structure, and compliance, which is essential for the 'draft' command. Aligns with the user guide's goal of producing persuasive, well-cited submissions.

### commands.digest.system
- **Effectiveness Assessment**: Effective. Provides clear instructions on output format and style for the 'digest' command, ensuring usability of the digested information. Aligns with the user guide's description of 'digest' for processing large documents.

### documents.statement_of_claim
- **Effectiveness Assessment**: Highly effective. Offers a standard, fillable structure for a common court document, significantly aiding the 'draft' command. The use of placeholders like {court_name} makes it adaptable.

### documents.originating_application
- **Effectiveness Assessment**: Highly effective. Similar to the Statement of Claim, it provides a crucial, standardized template for the 'draft' command, enhancing efficiency and consistency.

### documents.affidavit
- **Effectiveness Assessment**: Highly effective. Offers a detailed and compliant structure for affidavits, including critical components like deponent information and jurat. Essential for the 'draft' command.

### documents.notice_of_motion
- **Effectiveness Assessment**: Highly effective. Standardizes the creation of Notices of Motion, ensuring necessary details are prompted for, benefiting the 'draft' command.

### documents.outline_submissions
- **Effectiveness Assessment**: Highly effective. Gives a logical flow and standard sections for legal submissions, greatly assisting the 'draft' command in producing structured arguments.

### documents.interlocutory_application
- **Effectiveness Assessment**: Highly effective. Offers a clear and concise template for urgent/interim applications, crucial for the 'draft' command in time-sensitive situations.

### formats.case_facts_10_heading
- **Effectiveness Assessment**: Highly effective. This standardized format is crucial for consistency between 'extractfacts' output and 'strategy' input, as highlighted by the user guide's strict format requirements for the 'strategy' command. Ensures all key factual areas are covered.

### formats.strategic_options
- **Effectiveness Assessment**: Effective. Provides a clear and structured way to present strategies, including approach, legal basis, likelihood, timeline, resources, and risks. This aids in the clarity and usability of outputs from 'brainstorm' and 'strategy'.

### formats.irac_structure
- **Effectiveness Assessment**: Highly effective. IRAC is a standard legal analysis method. Providing this format helps the 'lookup' command generate responses that are familiar and useful to legal professionals, as shown in the user guide's example output for 'lookup'.

### formats.chronological_summary
- **Effectiveness Assessment**: Effective. Provides a simple and clear format for the 'digest' command when in 'summary' mode, making it easy to follow events over time.

### formats.citation_extraction
- **Effectiveness Assessment**: Highly effective. Clear structure for listing citations, vital for the 'lookup --extract citations' use case described in the user guide for building citation lists.

### formats.principles_extraction
- **Effectiveness Assessment**: Highly effective. Structured format for principles is ideal for the 'lookup --extract principles' use case (e.g., for advice letters) mentioned in the user guide.

### formats.checklist_extraction
- **Effectiveness Assessment**: Highly effective. The checkbox format is very user-friendly for the 'lookup --extract checklist' use case (e.g., pre-trial prep) from the user guide.

### lookup.research_assistant.system_prompt
- **Effectiveness Assessment**: Effective. Reinforces the core requirements for the 'lookup' command's research tasks. It's largely similar to `commands.lookup.system` from `base.yaml` but could be tailored for specific nuances of Jade.io interaction if any.

### lookup.extraction_instructions.citations
- **Effectiveness Assessment**: Effective. Clearly tells the LLM to add a 'CITATIONS' section and format it for easy use, directly supporting the '--extract citations' functionality.

### lookup.extraction_instructions.principles
- **Effectiveness Assessment**: Effective. Instructs the LLM to create a 'LEGAL PRINCIPLES' section in a structured format suitable for advice letters, aligning with the '--extract principles' use case.

### lookup.extraction_instructions.checklist
- **Effectiveness Assessment**: Effective. Guides the LLM to create a 'PRACTICAL CHECKLIST' with actionable items, supporting the '--extract checklist' functionality.

### lookup.comprehensive_analysis.requirements
- **Effectiveness Assessment**: Effective. Sets high standards for the '--comprehensive' flag in 'lookup', pushing for deeper and broader analysis than the standard mode. Details are specific and cover important analytical dimensions.

### lookup.comprehensive_analysis.citation_requirements
- **Effectiveness Assessment**: Effective. Adds rigor to citation practice for comprehensive analysis, ensuring a higher quality of academic or detailed research output.

### lookup.comprehensive_analysis.output_structure
- **Effectiveness Assessment**: Effective. Provides a clear, multi-section structure for exhaustive output, ensuring that the analysis is well-organized and covers all required aspects.

### lookup.standard_analysis.instructions
- **Effectiveness Assessment**: Effective. Clear instructions for the default 'lookup' mode: cite sources, analyze provided sources (typically 5), structure with summary, analysis, and conclusion. Cross-referencing is a good addition.

### lookup.standard_user_template
- **Effectiveness Assessment**: Effective. Simple and clear templating of user question and context (links) for the LLM to process.

### processing.digest.summary_mode
- **Effectiveness Assessment**: Effective. Clearly defines the task (chronological summary) and the expected output format (reiterating `formats.chronological_summary`), ensuring consistency for the 'summary' mode.

### processing.digest.issues_mode
- **Effectiveness Assessment**: Effective. Clearly defines the task for 'issues' mode and provides a detailed structure for each issue (Description, Legal Framework, Analysis, Significance). This helps in generating useful, structured output for legal issue spotting.

### processing.digest.system_prompt
- **Effectiveness Assessment**: Effective. This is a good overarching prompt that sets the quality standard for the digest command's operations, complementing `commands.digest.system` from `base.yaml`.

### processing.draft.system_prompt_base
- **Effectiveness Assessment**: Effective. Consistent reinforcement of the expert persona. This is identical to `commands.draft.system` in `base.yaml` and serves as a good foundation layer for more specific draft instructions.

### processing.draft.context_case_facts_and_strategies
- **Effectiveness Assessment**: Effective. Instructs the LLM to use facts as a foundation and consider strategies, particularly those marked 'most likely to succeed'. This aligns with the user guide's description of how 'draft' uses various inputs.

### processing.draft.context_case_facts_only
- **Effectiveness Assessment**: Effective. Focuses the LLM on using the provided case facts as the factual basis for the draft.

### processing.draft.context_strategies_only
- **Effectiveness Assessment**: Effective. Guides the LLM to consider the provided strategies, especially those marked 'most likely to succeed'.

### processing.draft.general_instructions
- **Effectiveness Assessment**: Highly effective. This is a comprehensive set of instructions covering key aspects of good legal drafting. Crucial for quality.

### processing.draft.context_aware_prompt
- **Effectiveness Assessment**: Effective. Clearly structures the request to the LLM, incorporating the previously supplied context and listing explicit quality requirements (formatted, sound, aligned, compliant, evidence-based).

### processing.draft.user_prompt_template
- **Effectiveness Assessment**: Effective. Simple template for straightforward drafting requests, specifying document type and user's specific request.

### processing.extraction.chunk_facts_prompt
- **Effectiveness Assessment**: Effective. Clearly lists the types of facts to look for within a chunk and emphasizes extracting only raw facts present in that specific excerpt. Important for the multi-chunk processing logic of 'extractfacts'.

### processing.extraction.chunk_system_prompt
- **Effectiveness Assessment**: Effective. Reinforces the boundaries for chunk-based processing: be thorough for the given text but do not go beyond it.

### processing.extraction.organize_facts_prompt
- **Effectiveness Assessment**: Highly effective. This is the core prompt that assembles the final structured output of 'extractfacts'. It references the `format_instructions` (which would be `formats.case_facts_10_heading`) and gives clear rules about sourcing and completeness.

### processing.extraction.organize_system_prompt
- **Effectiveness Assessment**: Effective. Guides the LLM to accurately map the collected raw facts to the specified 10 headings, ensuring a clean final output. This complements `commands.extractfacts.system` from `base.yaml`.

### strategies.brainstorm.orthodox_prompt
- **Effectiveness Assessment**: Highly effective. Very detailed in what constitutes 'orthodox' (precedent-based, traditional, conservative, etc.) and specifies the exact information required for each strategy (name, description, legal basis, likelihood, considerations). This structured approach is crucial for generating useful content.

### strategies.brainstorm.unorthodox_prompt
- **Effectiveness Assessment**: Highly effective. Similar to the orthodox prompt, it clearly defines 'unorthodox' (novel, creative, innovative, etc.) and the specific output requirements (name, description, legal basis/interpretation, risk, innovation factor). Essential for the creative aspect of 'brainstorm'.

### strategies.brainstorm.analysis_prompt
- **Effectiveness Assessment**: Highly effective. This prompt drives the critical analysis phase of 'brainstorm'. It specifies selection criteria, detailed analysis points for each selected strategy, the exact number to return (5), and how to handle cases where fewer than 5 high-quality strategies are found. The final recommendation part is also key.

### strategies.brainstorm.regeneration_prompt
- **Effectiveness Assessment**: Effective. Allows for iterative refinement of brainstormed strategies by incorporating feedback, which is a valuable feature for improving results. The inclusion of `{citation_instructions}` placeholder is good for quality control.

### strategies.strategy.strategic_options_instructions
- **Effectiveness Assessment**: Highly effective. Extremely specific formatting requirements (title, probability, hurdles with citations, missing facts) ensure the 'strategy' command produces highly structured and detailed tactical options. The emphasis on real case citations with pinpoint references is crucial for legal utility.

### strategies.strategy.next_steps_prompt
- **Effectiveness Assessment**: Effective. Focuses on actionable outcomes by requesting specific, timed, and responsible action items. The format provided is clear.

### strategies.strategy.document_generation_context
- **Effectiveness Assessment**: Effective. Ensures that any document drafted as part of the 'strategy' output is aligned with the recommended strategic direction and meets basic legal document standards.

### strategies.strategy.unique_title_requirement
- **Effectiveness Assessment**: Moderately effective. While good practice, the LLM might still struggle with 'uniqueness' without more specific constraints or examples. However, it's a useful instruction to prevent repetition.

### verification.self_critique
- **Effectiveness Assessment**: Effective. A good general self-correction mechanism. Its application to core commands like 'extractfacts', 'brainstorm', 'strategy', and 'draft' (especially when auto-triggered or optionally enabled as per user guide) enhances reliability.

### verification.citation_retry_instructions
- **Effectiveness Assessment**: Highly effective. This is a critical prompt for quality control, emphasizing the use of real, verifiable Australian cases and discouraging invention. Its broad application across all commands that generate citable content is appropriate.

### verification.light_verification
- **Effectiveness Assessment**: Effective for its specific, limited purpose. Useful for ensuring language consistency without a full legal review. The user guide doesn't specify when this is used over other verification prompts, but it's a sensible, scoped check.

### verification.heavy_verification
- **Effectiveness Assessment**: Highly effective. This is essential for commands like 'extractfacts' and 'strategy' where accuracy is paramount, as noted by their mandatory verification in the user guide. The prompt is comprehensive in its review criteria.

### verification.system_prompt
- **Effectiveness Assessment**: Effective. Sets the correct expert persona for the LLM when performing heavy verification, reinforcing the expected standard of review for 'extractfacts' and 'strategy'.

---

## IV. Suggested Improvements
### base.australian_law
- **Original Purpose**: To ensure all LLM outputs adhere to Australian law and use Australian English.
- **Original Effectiveness Assessment**: Highly effective. Clear, concise, and fundamental for a tool targeted at Australian legal practice. Its application to 'all' commands ensures consistency.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Consider appending: "Where applicable, explicitly state if the legal principles discussed are Commonwealth, State or Territory-based. If State or Territory, specify which one (e.g., New South Wales, Victoria)."
    **Rationale**: Adds a layer of jurisdictional specificity, which is crucial in Australian law.
- **Cost/Time Implications**: Minor increase in token output if jurisdiction is frequently specified. Negligible processing cost.

### base.citation_standards
- **Original Purpose**: To enforce proper Australian citation formats for all legal documents.
- **Original Effectiveness Assessment**: Highly effective. Sets a clear standard for citations, crucial for legal document accuracy and verifiability. Broad application is appropriate.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Change to: "Cite all cases and legislative materials strictly in accordance with the latest edition of the Australian Guide to Legal Citations (AGLC). For cases, include medium neutral citations where available, alongside reported citations. Include pinpoint references (e.g., paragraph numbers or sections) whenever specific parts of a source are relied upon."
    **Rationale**: Specifies AGLC, which is the de facto standard, and emphasizes pinpoint referencing for better precision.
- **Cost/Time Implications**: Slightly longer prompt. May marginally increase processing time for the LLM to ensure AGLC compliance. Output length may increase with more detailed citations.

### base.accuracy_standards
- **Original Purpose**: To ensure all factual information provided by the LLM is accurate and verifiable.
- **Original Effectiveness Assessment**: Highly effective. Critical for maintaining trust and reliability in a legal context. Prevents invention of information.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add: "If uncertainty or ambiguity exists in source materials, this must be explicitly stated in the output. Do not make assumptions to fill gaps in information. Clearly distinguish between established facts and reasoned inferences."
    **Rationale**: Promotes transparency about the limits of available information and encourages critical handling of source material.
- **Cost/Time Implications**: Minor increase in prompt length. May lead to slightly longer, more nuanced outputs, increasing token count. Worth it for improved accuracy and trustworthiness.

### base.verification_standards
- **Original Purpose**: To ensure all legal citations are verifiable on specified Australian legal databases and legal principles have authority.
- **Original Effectiveness Assessment**: Highly effective. Reinforces citation quality and the need for authoritative support for legal claims, vital for practical legal work.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Specify databases more explicitly if possible: "All citations must be verifiable on AustLII, BarNet Jade, or official court/government legislation websites. When citing legal principles, directly reference the primary source (case or legislation) that establishes or best illustrates that principle."
    **Rationale**: Provides clearer guidance on acceptable verification sources and encourages direct sourcing for principles.
- **Cost/Time Implications**: Minor prompt length increase. No significant impact on processing cost.

### commands.extractfacts.system
- **Original Purpose**: System prompt for the 'extractfacts' command, instructing it to extract facts precisely under headings and handle missing information.
- **Original Effectiveness Assessment**: Effective. Clearly defines the task, the expected output structure (though headings are detailed elsewhere), and how to manage missing data ('Not specified' or 'To be determined'). Aligns with the user guide's description of 'extractfacts' for structuring information.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "When extracting facts for 'Key Events', ensure strict chronological order. If dates are ambiguous, note the ambiguity. For 'Legal Issues', phrase as questions where possible."
    **Rationale**: Improves structure for key events and clarity for legal issues.
  - **Focus**: Correctness
    **Suggestion**: Add: "If information seems contradictory within the source, extract both contradictory points and note the contradiction."
    **Rationale**: Ensures comprehensive extraction even with imperfect source material.
- **Cost/Time Implications**: Slightly longer prompt. May result in more detailed output if contradictions are found. Beneficial for thoroughness.

### commands.lookup.system
- **Original Purpose**: System prompt for the 'lookup' command, emphasizing Australian law, source citation, and well-structured, concise responses focused on Victorian or federal law.
- **Original Effectiveness Assessment**: Effective. Sets clear expectations for jurisdiction, citation, structure, and conciseness. Aligns with the 'lookup' command's purpose of rapid case-law search and structured legal answers.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "Structure responses to clearly distinguish between direct findings from sources and any synthesis or brief analysis performed. If providing analysis (e.g., IRAC structure), ensure each component logically follows from the previous."
    **Rationale**: Encourages clearer separation of information types and reinforces logical flow in analysis.
  - **Focus**: Correctness
    **Suggestion**: Add: "Prioritize primary sources (legislation and case law) over secondary sources when available and appropriate for the query."
    **Rationale**: Guides the LLM to prefer more authoritative sources.
- **Cost/Time Implications**: Minor prompt length increase. Could lead to slightly more structured and thus longer responses. Quality gain justifies it.

### commands.brainstorm.system
- **Original Purpose**: General system prompt for the 'brainstorm' command, focusing on practical, actionable Australian legal strategies, balancing creativity with accuracy, and requiring a definitive recommendation.
- **Original Effectiveness Assessment**: Effective. Guides the LLM towards generating creative yet legally sound strategies, distinguishing orthodox/unorthodox approaches, and ensuring a clear output structure. Matches the user guide's description of 'brainstorm' for comprehensive strategy generation.
- **Suggested Improvements**:
  - **Focus**: Creativity and Originality
    **Suggestion**: Add: "Think broadly: consider procedural tactics, evidentiary angles, negotiation leverage points, and alternative dispute resolution methods in addition to substantive legal arguments. For each strategy, briefly note what makes it distinct or innovative if applicable."
    **Rationale**: Encourages a wider range of strategic thinking and explicit identification of novelty.
  - **Focus**: Logical Strength
    **Suggestion**: Add: "The final recommendation section must synthesize the analysis and provide a compelling, multi-faceted justification for the #1 strategy, considering client objectives, risk tolerance, and resource implications."
    **Rationale**: Strengthens the justification requirement for the top recommendation.
- **Cost/Time Implications**: Moderate increase in prompt length. May lead to more diverse and detailed strategies, increasing token usage. Using a more capable model (e.g., Claude 3 Opus or GPT-4 Turbo) for the 'brainstorm' command, especially with these enhanced instructions, could yield significant quality improvements in creativity and analysis, justifying the cost.

### commands.brainstorm.orthodox_system
- **Original Purpose**: System prompt for generating 'orthodox' strategies in the 'brainstorm' command, emphasizing conservative, well-established approaches with strong precedential support.
- **Original Effectiveness Assessment**: Effective. Clearly defines 'orthodox' and directs the LLM to focus on low-risk, proven strategies with supporting citations. This is crucial for the 'brainstorm' command's ability to generate diverse strategy types.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add: "For each orthodox strategy, cite the primary legal authority (e.g., specific legislation section or leading case) that underpins it. Explain how the strategy aligns with established legal practice."
    **Rationale**: Reinforces the need for strong authoritative backing for orthodox strategies.
- **Cost/Time Implications**: Slight increase in prompt length and potentially output length due to more detailed explanations. Negligible processing cost.

### commands.brainstorm.unorthodox_system
- **Original Purpose**: System prompt for generating 'unorthodox' strategies in the 'brainstorm' command, encouraging creative, innovative approaches while acknowledging uncertainties.
- **Original Effectiveness Assessment**: Effective. Guides the LLM towards innovative thinking, pushing legal boundaries responsibly. Important for the 'brainstorm' command's creative ideation aspect.
- **Suggested Improvements**:
  - **Focus**: Creativity and Originality
    **Suggestion**: Add: "For unorthodox strategies, explicitly state the element of novelty (e.g., a new interpretation of existing law, application of principles from a different legal area, a novel procedural approach). Also, identify potential counter-arguments or reasons why this strategy is not commonly used."
    **Rationale**: Pushes for clearer articulation of innovation and a balanced view by considering downsides.
- **Cost/Time Implications**: Moderate increase in prompt length. Output will likely be longer and more detailed. This is acceptable for the 'unorthodox' section where deeper exploration is desired.

### commands.brainstorm.analysis_system
- **Original Purpose**: System prompt for the analysis phase of the 'brainstorm' command, instructing objective analysis of strategies based on merit, support, and likelihood.
- **Original Effectiveness Assessment**: Effective. Ensures a critical evaluation of the generated strategies, which is key to the 'brainstorm' command's goal of identifying 'most likely to succeed' options.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "When analyzing, adopt a 'devil's advocate' perspective. For each selected strategy, identify its weakest point or the primary obstacle to its success, and briefly suggest how it might be mitigated. Justify selections with explicit reference to the provided case facts and client objectives."
    **Rationale**: Encourages more robust analysis by forcing consideration of weaknesses and mitigation, and stronger grounding in case specifics.
- **Cost/Time Implications**: Longer prompt. Output of the analysis will be more detailed and longer. This is a critical reasoning step, so increased token usage is justified for higher quality analysis. May benefit from a more advanced model.

### commands.strategy.system
- **Original Purpose**: System prompt for the 'strategy' command, defining the persona as an Australian civil litigation expert focused on specific courts, analyzing facts for strategic options.
- **Original Effectiveness Assessment**: Effective. Establishes a clear expert persona and task (analyzing case facts for strategic options to achieve a specific outcome). Aligns with the user guide's description of 'strategy' for tactical implementation plans.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "Your analysis should yield 3-5 distinct strategic options, each clearly articulating a pathway to the specified outcome. For each option, detail the core legal argument, key actions, and anticipated challenges. Emphasize practical executability."
    **Rationale**: Provides more specific guidance on the nature and number of strategic options expected.
- **Cost/Time Implications**: Slightly longer prompt. Could lead to more detailed strategic options. Given 'strategy' uses o1-pro (as per user guide), which is already an advanced model, this should be handled well. Cost implications are within the acceptable range for quality improvement.

### commands.strategy.ranking_system
- **Original Purpose**: System prompt for ranking strategies objectively for a specific outcome within the 'strategy' command.
- **Original Effectiveness Assessment**: Effective. Focuses the LLM on objective ranking, which is a key part of the 'strategy' command's analysis to provide actionable, prioritized options.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "When ranking strategies, provide a brief rationale for each rank, comparing its pros and cons against the other presented options, specifically in relation to achieving the stated outcome."
    **Rationale**: Requires explicit justification for rankings, making the advice more transparent and robust.
- **Cost/Time Implications**: Prompt length increase. Output will be longer due to justifications. Acceptable for enhancing clarity of strategic advice.

### commands.draft.system
- **Original Purpose**: System prompt for the 'draft' command, setting the persona as a senior Australian barrister drafting high-quality, compliant legal documents.
- **Original Effectiveness Assessment**: Effective. Creates a strong persona focused on quality, structure, and compliance, which is essential for the 'draft' command. Aligns with the user guide's goal of producing persuasive, well-cited submissions.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add: "Ensure the tone is appropriate for the specified document type and its intended audience (e.g., court, opposing counsel, client). All legal assertions must be citable to provided materials or generally accepted Australian legal principles."
    **Rationale**: Adds nuance regarding tone and reinforces the need for citable assertions.
  - **Focus**: Logical Strength
    **Suggestion**: Add: "Structure the document with clear, logical flow, using headings and subheadings as appropriate. Arguments should be built incrementally, with each point supporting the overall objective of the document."
    **Rationale**: Emphasizes structural integrity and coherent argumentation.
- **Cost/Time Implications**: Slightly longer prompt. The 'draft' command uses o3 (as per user guide), which is a very capable model. These instructions should refine output quality with acceptable cost increase. Quality of draft documents is paramount.

### commands.digest.system
- **Original Purpose**: System prompt for the 'digest' command, requiring logical structure, clear headings, bullet points, and concise summaries under Australian law.
- **Original Effectiveness Assessment**: Effective. Provides clear instructions on output format and style for the 'digest' command, ensuring usability of the digested information. Aligns with the user guide's description of 'digest' for processing large documents.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "When summarizing, prioritize information that is legally significant or directly relevant to potential disputes or key obligations. Identify any ambiguities or missing information in the source document that could be legally pertinent."
    **Rationale**: Guides the LLM to filter for legal relevance and spot potential issues, making the digest more than just a neutral summary.
- **Cost/Time Implications**: Slightly longer prompt. May produce more insightful, and thus slightly longer, digests. Benefits should outweigh minor cost increase.

### documents.statement_of_claim
- **Original Purpose**: Provides a template structure for a Statement of Claim.
- **Original Effectiveness Assessment**: Highly effective. Offers a standard, fillable structure for a common court document, significantly aiding the 'draft' command. The use of placeholders like {court_name} makes it adaptable.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Review placeholders to ensure they cover all typical variations and perhaps add optional sections or common clauses as comments, e.g., `<!-- If applicable, add details of representative capacity -->` or specific types of relief.
    **Rationale**: Increases comprehensiveness and adaptability of the template.
- **Cost/Time Implications**: Increased template size is negligible in cost. Improves usability for the 'draft' command.

### documents.originating_application
- **Original Purpose**: Provides a template structure for an Originating Application.
- **Original Effectiveness Assessment**: Highly effective. Similar to the Statement of Claim, it provides a crucial, standardized template for the 'draft' command, enhancing efficiency and consistency.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Consider adding more specific placeholders for common types of relief sought in originating applications or references to specific court rules sections if they vary often, e.g., `{specific_rule_authorizing_application}`.
    **Rationale**: Makes the template more dynamic and directly prompts for rule-specific information.
- **Cost/Time Implications**: Negligible cost for template expansion. Enhances utility.

### documents.affidavit
- **Original Purpose**: Provides a template structure for an Affidavit.
- **Original Effectiveness Assessment**: Highly effective. Offers a detailed and compliant structure for affidavits, including critical components like deponent information and jurat. Essential for the 'draft' command.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add a placeholder or instruction for annexures/exhibits, e.g., "4. Annexed hereto and marked '{annexure_mark}' is a true copy of [description of document]." Ensure placeholders for witness qualification are clear.
    **Rationale**: Covers a common and important part of affidavits.
- **Cost/Time Implications**: Negligible. Improves completeness.

### documents.notice_of_motion
- **Original Purpose**: Provides a template structure for a Notice of Motion.
- **Original Effectiveness Assessment**: Highly effective. Standardizes the creation of Notices of Motion, ensuring necessary details are prompted for, benefiting the 'draft' command.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Include an optional placeholder for return date/time if not the standard, or if it needs to be calculated/confirmed, e.g., `TAKE NOTICE that the {moving_party_role} will move this Honourable Court at {time_placeholder} on {date_placeholder} or so soon thereafter as the business of the Court may allow...`
    **Rationale**: Adds flexibility for non-standard hearing times.
- **Cost/Time Implications**: Negligible. Small improvement to flexibility.

### documents.outline_submissions
- **Original Purpose**: Provides a template structure for an Outline of Submissions.
- **Original Effectiveness Assessment**: Highly effective. Gives a logical flow and standard sections for legal submissions, greatly assisting the 'draft' command in producing structured arguments.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Within 'IV. ARGUMENT', suggest a structure for each point: e.g., `A. [First Issue Heading]\n    4.1. [Legal Principle/Proposition]\n        - [Authority 1]\n        - [Authority 2]\n    4.2. [Application to Facts]\n    4.3. [Conclusion on this Issue]`
    **Rationale**: Provides a micro-structure for arguments, enhancing logical presentation.
- **Cost/Time Implications**: Increases template complexity slightly. Could guide the LLM to produce more robust and well-structured draft submissions. Output may be longer but higher quality.

### documents.interlocutory_application
- **Original Purpose**: Provides a template structure for an Interlocutory Application.
- **Original Effectiveness Assessment**: Highly effective. Offers a clear and concise template for urgent/interim applications, crucial for the 'draft' command in time-sensitive situations.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add placeholders for essential elements like undertaking as to damages if it's commonly required for such applications, e.g., "The Applicant undertakes to abide by any order the Court may make as to damages, in case the Court shall hereafter be of opinion that the Respondent shall have sustained any, by reason of this order, which the Applicant ought to pay."
    **Rationale**: Includes a critical component often needed for interlocutory relief.
- **Cost/Time Implications**: Negligible cost for adding a common clause to the template.

### formats.case_facts_10_heading
- **Original Purpose**: Defines a 10-heading structure for organizing case facts.
- **Original Effectiveness Assessment**: Highly effective. This standardized format is crucial for consistency between 'extractfacts' output and 'strategy' input, as highlighted by the user guide's strict format requirements for the 'strategy' command. Ensures all key factual areas are covered.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: For 'Evidence Available', suggest sub-categorization if helpful, e.g., 'Documentary Evidence', 'Witness Statements', 'Expert Reports'. For 'Applicable Law', suggest distinguishing 'Statute' and 'Case Law'.
    **Rationale**: Could provide more granular structure within the existing headings, aiding clarity.
- **Cost/Time Implications**: This is a format definition, so changes impact how LLMs are *told* to structure data, not a direct LLM prompt itself for generation. Minimal impact on processing cost, but enhances clarity of structured output.

### formats.strategic_options
- **Original Purpose**: Defines the output format for presenting strategic options.
- **Original Effectiveness Assessment**: Effective. Provides a clear and structured way to present strategies, including approach, legal basis, likelihood, timeline, resources, and risks. This aids in the clarity and usability of outputs from 'brainstorm' and 'strategy'.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add a field for 'Key Assumptions' made when evaluating this strategy, and 'Metrics for Success' (how would one know if this strategy is working?).
    **Rationale**: Adds depth to the strategic thinking by making assumptions explicit and defining success criteria.
- **Cost/Time Implications**: Expands the format definition. If LLMs are prompted to fill these new fields, outputs from 'brainstorm' and 'strategy' will be longer and require more detailed generation. This is a valuable trade-off for more robust strategic planning.

### formats.irac_structure
- **Original Purpose**: Defines the IRAC (Issue, Rule, Application, Conclusion) structure for legal analysis.
- **Original Effectiveness Assessment**: Highly effective. IRAC is a standard legal analysis method. Providing this format helps the 'lookup' command generate responses that are familiar and useful to legal professionals, as shown in the user guide's example output for 'lookup'.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Consider adding 'Authorities:' or 'Citations:' as a sub-element under 'Rule' to ensure explicit linkage of rules to their sources within the IRAC structure itself.
    **Rationale**: Reinforces the direct connection between the stated rule and its legal backing.
- **Cost/Time Implications**: Minor change to format definition. Promotes better citation practice within IRAC. Negligible cost.

### formats.chronological_summary
- **Original Purpose**: Defines the format for a chronological summary.
- **Original Effectiveness Assessment**: Effective. Provides a simple and clear format for the 'digest' command when in 'summary' mode, making it easy to follow events over time.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add an optional 'Significance/Implication' sub-bullet for key events if the LLM is able to infer it during digest.
    **Rationale**: Could make the summary more insightful, bridging summarization and basic analysis.
- **Cost/Time Implications**: If implemented, would require the 'digest' command's prompts to ask for this, potentially increasing its processing per chunk. Could be a valuable enhancement for more insightful digests.

### lookup.extraction_instructions.citations
- **Original Purpose**: Provides specific instructions when citation extraction is requested with the 'lookup' command.
- **Original Effectiveness Assessment**: Effective. Clearly tells the LLM to add a 'CITATIONS' section and format it for easy use, directly supporting the '--extract citations' functionality.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Specify AGLC for formatting: "Also provide a clear 'CITATIONS' section that lists all case citations and legislation references in AGLC format. Separate Case Law from Legislation."
    **Rationale**: Ensures standardized and correct citation formatting.
- **Cost/Time Implications**: Minor prompt change. Ensures higher quality output for a key feature. Negligible cost.

### lookup.comprehensive_analysis.requirements
- **Original Purpose**: Defines requirements for a comprehensive analysis in the 'lookup' command, including thorough review, authority hierarchy, and jurisdictional variations.
- **Original Effectiveness Assessment**: Effective. Sets high standards for the '--comprehensive' flag in 'lookup', pushing for deeper and broader analysis than the standard mode. Details are specific and cover important analytical dimensions.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "Identify any conflicting authorities or unresolved legal questions within the analyzed sources. Provide a brief synthesis of the overall state of the law on the topic based on the sources reviewed."
    **Rationale**: Pushes for deeper analytical insight beyond summarizing sources.
- **Cost/Time Implications**: Increases analytical demand on the LLM. Output will be longer and more complex. Justified for a 'comprehensive' mode. May benefit from a highly capable model.

### lookup.standard_analysis.instructions
- **Original Purpose**: Provides instructions for standard analysis in the 'lookup' command (when not using '--comprehensive').
- **Original Effectiveness Assessment**: Effective. Clear instructions for the default 'lookup' mode: cite sources, analyze provided sources (typically 5), structure with summary, analysis, and conclusion. Cross-referencing is a good addition.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "Begin with a concise executive summary (1-2 sentences) of the main finding before launching into the detailed analysis. Conclude by explicitly answering the user's question based on the analysis."
    **Rationale**: Improves scannability and ensures the user's core question is directly addressed in the conclusion.
- **Cost/Time Implications**: Minor prompt addition. Should improve clarity and directness of answers with minimal cost.

### processing.digest.summary_mode
- **Original Purpose**: Instructs the 'digest' command to create a chronological summary with a specific format.
- **Original Effectiveness Assessment**: Effective. Clearly defines the task (chronological summary) and the expected output format (reiterating `formats.chronological_summary`), ensuring consistency for the 'summary' mode.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add: "Include full dates (DD/MM/YYYY) where available. If only partial dates are present, represent them as accurately as possible (e.g., 'Mid-2023', 'September 2023'). Note any ambiguities in dating directly."
    **Rationale**: Improves precision in chronological reporting.
- **Cost/Time Implications**: Slightly more detailed instructions, minimal impact on cost.

### processing.digest.issues_mode
- **Original Purpose**: Instructs the 'digest' command to identify and analyze legal issues with a specific structure.
- **Original Effectiveness Assessment**: Effective. Clearly defines the task for 'issues' mode and provides a detailed structure for each issue (Description, Legal Framework, Analysis, Significance). This helps in generating useful, structured output for legal issue spotting.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Under 'Analysis', add: "Briefly explain how the facts in this document segment relate to the identified legal framework for this issue. State any preliminary conclusions or questions that arise from this connection."
    **Rationale**: Encourages a more explicit application of law to facts within each identified issue, making the analysis more robust.
- **Cost/Time Implications**: May increase the length and complexity of the analysis for each issue. This is desirable for deeper issue spotting and likely justifies the moderate increase in token usage per chunk.

### processing.extraction.chunk_facts_prompt
- **Original Purpose**: Prompt for extracting raw facts from a document chunk during the 'extractfacts' process, listing fact categories.
- **Original Effectiveness Assessment**: Effective. Clearly lists the types of facts to look for within a chunk and emphasizes extracting only raw facts present in that specific excerpt. Important for the multi-chunk processing logic of 'extractfacts'.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add: "Extract verbatim quotes for critical pieces of evidence or statements where precise wording is important, clearly indicating they are quotes."
    **Rationale**: Ensures key phrases are captured accurately.
- **Cost/Time Implications**: May slightly increase output size if many quotes are extracted. Improves fidelity of fact extraction.

### processing.extraction.organize_facts_prompt
- **Original Purpose**: Prompt for organizing all extracted raw facts (from chunks) into the 10 standard headings.
- **Original Effectiveness Assessment**: Highly effective. This is the core prompt that assembles the final structured output of 'extractfacts'. It references the `format_instructions` (which would be `formats.case_facts_10_heading`) and gives clear rules about sourcing and completeness.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "After populating the headings, include a brief 'Confidence Score' section (High/Medium/Low) reflecting the overall clarity and completeness of the information found in the document for this structured summary, with a one-sentence justification."
    **Rationale**: Provides a useful meta-assessment of the extraction quality.
- **Cost/Time Implications**: Adds a small analytical step after organization. Output will be slightly longer. Potentially useful for user to gauge reliability. May require a slightly more capable model for this meta-analysis part or very clear instructions.

### strategies.brainstorm.orthodox_prompt
- **Original Purpose**: User prompt for generating 10 orthodox legal strategies in 'brainstorm', detailing characteristics and required output format for each.
- **Original Effectiveness Assessment**: Highly effective. Very detailed in what constitutes 'orthodox' (precedent-based, traditional, conservative, etc.) and specifies the exact information required for each strategy (name, description, legal basis, likelihood, considerations). This structured approach is crucial for generating useful content.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: For 'Key considerations', add: "specifically address potential downsides or limitations even for these orthodox approaches."
    **Rationale**: Ensures a balanced view, even for conservative strategies.
- **Cost/Time Implications**: Minor addition, encourages more thorough thinking. Negligible cost.

### strategies.brainstorm.unorthodox_prompt
- **Original Purpose**: User prompt for generating 10 unorthodox legal strategies in 'brainstorm', detailing characteristics and required output format.
- **Original Effectiveness Assessment**: Highly effective. Similar to the orthodox prompt, it clearly defines 'unorthodox' (novel, creative, innovative, etc.) and the specific output requirements (name, description, legal basis/interpretation, risk, innovation factor). Essential for the creative aspect of 'brainstorm'.
- **Suggested Improvements**:
  - **Focus**: Creativity and Originality
    **Suggestion**: Add: "For each unorthodox strategy, suggest an analogy or a conceptual parallel from a different domain if it helps clarify the novel approach. Explicitly state why this strategy, despite being unorthodox, might be uniquely suited to the specific case facts or client objectives."
    **Rationale**: Pushes for more creative explanation and stronger justification for unorthodox suggestions.
- **Cost/Time Implications**: May increase length and cognitive load on the LLM. Use of a highly creative model (like Grok, as mentioned in user guide) is suitable here. Increased token count for better creative output is acceptable for this specific feature.

### strategies.brainstorm.analysis_prompt
- **Original Purpose**: User prompt for analyzing all generated strategies (orthodox and unorthodox) and selecting the 5 most promising ones, with detailed criteria and output requirements, plus a final recommendation.
- **Original Effectiveness Assessment**: Highly effective. This prompt drives the critical analysis phase of 'brainstorm'. It specifies selection criteria, detailed analysis points for each selected strategy, the exact number to return (5), and how to handle cases where fewer than 5 high-quality strategies are found. The final recommendation part is also key.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: For 'Implementation roadmap', request: "Outline 3-5 key sequential steps. For 'Success probability', provide a percentage AND a qualitative justification (e.g., '70% - High, because X and Y strengths align well with Z vulnerability of opponent'). For the FINAL RECOMMENDATION, also include a brief discussion of the primary alternative strategy considered and why the #1 choice is superior."
    **Rationale**: Adds more structure to roadmap and success probability, and depth to the final recommendation by requiring comparison.
- **Cost/Time Implications**: Increases the detail required in the analysis. Output will be significantly longer and more structured. This is a core reasoning task, so increased cost for higher quality is justified. Benefits from a strong analytical model.

### strategies.strategy.strategic_options_instructions
- **Original Purpose**: Provides exact formatting instructions for the strategic options section of the 'strategy' command output.
- **Original Effectiveness Assessment**: Highly effective. Extremely specific formatting requirements (title, probability, hurdles with citations, missing facts) ensure the 'strategy' command produces highly structured and detailed tactical options. The emphasis on real case citations with pinpoint references is crucial for legal utility.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add to 'Principal Hurdles': "For each hurdle, also specify if it's a legal, factual, or practical hurdle." Add a new section under each option: "* **Ethical Considerations**: [Briefly note any ethical implications or duties to be mindful of when pursuing this option.]"
    **Rationale**: Categorizing hurdles improves clarity. Adding ethical considerations is vital for responsible legal AI.
- **Cost/Time Implications**: Expands the output format. LLM needs to perform additional classification (hurdle type) and generate ethical considerations. This is a significant quality improvement, likely justifying the increased token usage and processing by the o1-pro model.

### verification.self_critique
- **Original Purpose**: Prompts the LLM to identify and correct legal inaccuracies in its own output and ensure Australian English compliance.
- **Original Effectiveness Assessment**: Effective. A good general self-correction mechanism. Its application to core commands like 'extractfacts', 'brainstorm', 'strategy', and 'draft' (especially when auto-triggered or optionally enabled as per user guide) enhances reliability.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "Review the response for logical consistency. Are there any contradictions? Does the reasoning flow clearly? Are there any unstated assumptions that should be made explicit? Provide the corrected text, and if useful, a brief note on the nature of key corrections made."
    **Rationale**: Expands self-critique to cover logical structure and transparency of assumptions.
- **Cost/Time Implications**: Increases the scope of self-critique. The LLM performing verification will use more tokens/time. This is a direct investment in quality. A 'verification step' inherently has higher cost but is crucial.

### verification.citation_retry_instructions
- **Original Purpose**: Provides enhanced instructions for citation accuracy when an LLM generation attempt needs a retry due to citation issues.
- **Original Effectiveness Assessment**: Highly effective. This is a critical prompt for quality control, emphasizing the use of real, verifiable Australian cases and discouraging invention. Its broad application across all commands that generate citable content is appropriate.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add: "Ensure citations are to the most authoritative version of a case (e.g., High Court over a lower court on the same matter if discussing a principle established by HCA). Verify year and court identifiers meticulously. If providing a direct quote, ensure the pinpoint reference is to the exact paragraph/page of the quote."
    **Rationale**: Adds more specific guidance for choosing among multiple citations and for quoting.
- **Cost/Time Implications**: Minor prompt length increase. Reinforces best practices for citation, minimal cost impact.

### verification.heavy_verification
- **Original Purpose**: Prompts for a comprehensive legal accuracy review, including citations, reasoning, errors in law/procedure, and Australian English.
- **Original Effectiveness Assessment**: Highly effective. This is essential for commands like 'extractfacts' and 'strategy' where accuracy is paramount, as noted by their mandatory verification in the user guide. The prompt is comprehensive in its review criteria.
- **Suggested Improvements**:
  - **Focus**: Logical Strength
    **Suggestion**: Add: "Assess the practical applicability of any advice or strategy. Are there any overlooked practical impediments? Is the advice actionable? Consider if alternative interpretations of the law or facts exist and if they have been adequately addressed."
    **Rationale**: Broadens the heavy verification to include practical considerations and alternative viewpoints.
- **Cost/Time Implications**: Further increases the thoroughness of the heavy verification step. This will add to token usage and processing time but is in line with the 'heavy' nature of this verification. Essential for critical outputs from 'extractfacts' and 'strategy'.

### verification.system_prompt
- **Original Purpose**: System prompt for heavy verification, establishing an 'Australian law expert' persona for thorough review.
- **Original Effectiveness Assessment**: Effective. Sets the correct expert persona for the LLM when performing heavy verification, reinforcing the expected standard of review for 'extractfacts' and 'strategy'.
- **Suggested Improvements**:
  - **Focus**: Correctness
    **Suggestion**: Add: "You are an experienced Australian Barrister acting as a meticulous reviewer. Your task is to identify any errors, omissions, or areas of improvement in the provided legal text. Focus on legal accuracy, citation correctness (AGLC standards), logical coherence, completeness, and practical applicability in an Australian legal context. Be exacting."
    **Rationale**: Strengthens the persona and clarifies the high standard of review expected.
- **Cost/Time Implications**: Minor prompt length increase. Reinforces the quality expectation for the verification step.

---

## V. Evaluation of LLM Model Appropriateness
### base.australian_law
- **Associated Command(s)**: all
- **Current LLM Model** (October 2025): Varies by command (lookup: google/gemini-2.5-pro, digest/extractfacts: anthropic/claude-sonnet-4.5, brainstorm: x-ai/grok-4 & anthropic/claude-sonnet-4.5, strategy: anthropic/claude-sonnet-4.5, draft: openai/o3-pro)
- **Appropriateness Evaluation**: Generally appropriate as this is a foundational instruction. All listed models are capable of understanding and applying such a general constraint. The suggested improvement for jurisdictional specificity is also within their capabilities.
- **Alternative Model Suggestions**: None.

### base.citation_standards
- **Associated Command(s)**: all
- **Current LLM Model**: Varies by command
- **Appropriateness Evaluation**: Generally appropriate. Enforcing AGLC might be challenging for some models consistently. The models used for `draft` (o3) and `strategy` (o1-pro) should be highly capable. Gemini 2.5 Pro, Claude Sonnet, and Grok should also manage, but consistency across all might vary. The suggested improvement for strict AGLC and pinpoint references is crucial and tests model precision.
- **Alternative Model Suggestions**:
  - **Model**: openai/o3 or openai/o1-pro
    **Justification**: For any command where AGLC precision is absolutely paramount and current model struggles, consider routing through a high-precision model like o3 or o1-pro specifically for citation formatting if feasible, though this would complicate logic.

### base.accuracy_standards
- **Associated Command(s)**: all
- **Current LLM Model**: Varies by command
- **Appropriateness Evaluation**: Appropriate. All models should be able to follow instructions about not inventing information. The suggestion to explicitly state uncertainty is a good way to manage hallucination risk within the capability of these models.
- **Alternative Model Suggestions**: None.

### base.verification_standards
- **Associated Command(s)**: all
- **Current LLM Model**: Varies by command
- **Appropriateness Evaluation**: Appropriate. This prompt supports external verification processes. Models should be able to understand the need for verifiable citations.
- **Alternative Model Suggestions**: None.

### commands.extractfacts.system
- **Associated Command(s)**: extractfacts
- **Current LLM Model**: anthropic/claude-sonnet-4
- **Appropriateness Evaluation**: Appropriate. Claude Sonnet is good for precise extraction and adherence to structure. The suggested improvements for chronological order and contradiction handling are within its capabilities.
- **Alternative Model Suggestions**:
  - **Model**: anthropic/claude-3-opus-20240229
    **Justification**: If higher accuracy in complex documents or better contradiction handling is needed, Opus could offer a step up in nuanced understanding, justifying the cost for foundational fact extraction.

### commands.lookup.system
- **Associated Command(s)**: lookup
- **Current LLM Model**: google/gemini-2.5-pro-preview
- **Appropriateness Evaluation**: Appropriate. Gemini 2.5 Pro is designed for fast and accurate information retrieval and synthesis. The suggestions for clearer structure and source prioritization are well within its capabilities.
- **Alternative Model Suggestions**: None.

### commands.brainstorm.system
- **Associated Command(s)**: brainstorm
- **Current LLM Model**: x-ai/grok-3 (generation), anthropic/claude-sonnet-4 (analysis)
- **Appropriateness Evaluation**: Generation (Grok): Appropriate, as Grok is highlighted for creative capabilities. The suggested improvements aim to broaden this creativity. Analysis (Claude Sonnet): Appropriate for the structured analysis part. The suggested improvement for a more compelling justification for the #1 strategy would be handled by Claude Sonnet.
- **Alternative Model Suggestions**:
  - **Model**: anthropic/claude-3-opus-20240229 (for analysis if Sonnet is insufficient)
    **Justification**: If the analysis part (done by Claude Sonnet) needs deeper reasoning for the final recommendation, Opus could be considered for the analysis model, though Sonnet is likely adequate.

### commands.brainstorm.orthodox_system
- **Associated Command(s)**: brainstorm
- **Current LLM Model**: x-ai/grok-3
- **Appropriateness Evaluation**: Appropriate. Grok should be able to generate conservative strategies when properly guided. The suggested improvement to cite primary legal authority reinforces this.
- **Alternative Model Suggestions**: None.

### commands.brainstorm.unorthodox_system
- **Associated Command(s)**: brainstorm
- **Current LLM Model**: x-ai/grok-3
- **Appropriateness Evaluation**: Highly appropriate. Grok's strength is creativity, which is exactly what's needed for unorthodox strategies. The suggested improvements to articulate novelty and consider counter-arguments should leverage Grok's capabilities well.
- **Alternative Model Suggestions**: None.

### commands.brainstorm.analysis_system
- **Associated Command(s)**: brainstorm
- **Current LLM Model**: anthropic/claude-sonnet-4
- **Appropriateness Evaluation**: Appropriate. Claude Sonnet is capable of structured analysis and following detailed instructions for evaluation. The 'devil's advocate' suggestion should enhance its analytical output.
- **Alternative Model Suggestions**:
  - **Model**: anthropic/claude-3-opus-20240229 or openai/o1-pro
    **Justification**: For an even more robust 'devil's advocate' analysis and deeper strategic insight during the selection phase, a more powerful reasoning model like Opus or o1-pro could be beneficial, justifying the cost for this critical selection step.

### commands.strategy.system
- **Associated Command(s)**: strategy
- **Current LLM Model**: openai/o1-pro (generation)
- **Appropriateness Evaluation**: Highly appropriate. o1-pro is specified for enhanced multi-step legal reasoning, which is exactly what this system prompt for generating strategic options requires. The suggested improvements for detailing core arguments and practical executability align with o1-pro's strengths.
- **Alternative Model Suggestions**: None.

### commands.strategy.ranking_system
- **Associated Command(s)**: strategy
- **Current LLM Model**: anthropic/claude-sonnet-4 (analysis, as per user guide for strategy analysis part)
- **Appropriateness Evaluation**: Appropriate. Claude Sonnet should be capable of ranking strategies and providing rationales as suggested. If this prompt applies to the o1-pro generation phase, o1-pro is also highly capable.
- **Alternative Model Suggestions**:
  - **Model**: openai/o1-pro (if ranking is part of generation) or anthropic/claude-3-opus-20240229 (if ranking is a distinct analysis step and Sonnet is not sufficient)
    **Justification**: If deeper comparative analysis for ranking is needed, Opus or ensuring o1-pro handles this would be better. o1-pro is already in use for the generation.

### commands.draft.system
- **Associated Command(s)**: draft
- **Current LLM Model**: openai/o3
- **Appropriateness Evaluation**: Highly appropriate. o3 is described as superior for technical legal writing. The suggested improvements regarding tone, citable assertions, and logical flow are complex tasks that a model like o3 is best suited for.
- **Alternative Model Suggestions**: None.

### commands.digest.system
- **Associated Command(s)**: digest
- **Current LLM Model**: anthropic/claude-sonnet-4
- **Appropriateness Evaluation**: Appropriate. Claude Sonnet is good for reliable document summarization and structured output. The suggestion to prioritize legally significant information and identify ambiguities should be manageable.
- **Alternative Model Suggestions**:
  - **Model**: anthropic/claude-3-haiku-20240307
    **Justification**: If cost is a major concern for digesting very large volumes and the current quality of Claude Sonnet is sufficient, Haiku could be tested for cost-effectiveness. However, for legal significance filtering, Sonnet is likely a better balance.

### documents.statement_of_claim
- **Associated Command(s)**: draft
- **Current LLM Model**: openai/o3
- **Appropriateness Evaluation**: N/A (This is a template, not an LLM generation instruction that directly depends on model capability for its own execution. The 'draft' command's LLM (o3) will use this template.) o3 is highly appropriate for filling such templates accurately.
- **Alternative Model Suggestions**: None.

### documents.originating_application
- **Associated Command(s)**: draft
- **Current LLM Model**: openai/o3
- **Appropriateness Evaluation**: N/A (Template. o3 will use this.)
- **Alternative Model Suggestions**: None.

### documents.affidavit
- **Associated Command(s)**: draft
- **Current LLM Model**: openai/o3
- **Appropriateness Evaluation**: N/A (Template. o3 will use this.)
- **Alternative Model Suggestions**: None.

### documents.notice_of_motion
- **Associated Command(s)**: draft
- **Current LLM Model**: openai/o3
- **Appropriateness Evaluation**: N/A (Template. o3 will use this.)
- **Alternative Model Suggestions**: None.

### documents.outline_submissions
- **Associated Command(s)**: draft
- **Current LLM Model**: openai/o3
- **Appropriateness Evaluation**: N/A (Template. o3 will use this.) The suggested improvement for micro-structuring arguments would be well-handled by o3's advanced reasoning when it fills this template.
- **Alternative Model Suggestions**: None.

### documents.interlocutory_application
- **Associated Command(s)**: draft
- **Current LLM Model**: openai/o3
- **Appropriateness Evaluation**: N/A (Template. o3 will use this.)
- **Alternative Model Suggestions**: None.

### formats.case_facts_10_heading
- **Associated Command(s)**: extractfacts, strategy
- **Current LLM Model**: anthropic/claude-sonnet-4 (for extractfacts), openai/o1-pro (for strategy input)
- **Appropriateness Evaluation**: N/A (Format definition. These models are instructed to follow this format.) The models are capable of adhering to this structured format.
- **Alternative Model Suggestions**: None.

### formats.strategic_options
- **Associated Command(s)**: brainstorm, strategy
- **Current LLM Model**: x-ai/grok-3 / anthropic/claude-sonnet-4 (brainstorm), openai/o1-pro (strategy)
- **Appropriateness Evaluation**: N/A (Format definition.) These models are capable of populating this structured format. The suggested additions (Key Assumptions, Metrics for Success) would require more nuanced generation, which o1-pro and Grok/Claude-Sonnet are suited for.
- **Alternative Model Suggestions**: None.

### formats.irac_structure
- **Associated Command(s)**: lookup
- **Current LLM Model**: google/gemini-2.5-pro-preview
- **Appropriateness Evaluation**: N/A (Format definition.) Gemini 2.5 Pro is well-suited to generate content in this standard legal analysis format.
- **Alternative Model Suggestions**: None.

### formats.chronological_summary
- **Associated Command(s)**: digest
- **Current LLM Model**: anthropic/claude-sonnet-4
- **Appropriateness Evaluation**: N/A (Format definition.) Claude Sonnet can effectively produce summaries in this clear format. The suggested 'Significance/Implication' sub-bullet would be a good test of Sonnet's inference capabilities.
- **Alternative Model Suggestions**: None.

### lookup.extraction_instructions.citations
- **Associated Command(s)**: lookup
- **Current LLM Model**: google/gemini-2.5-pro-preview
- **Appropriateness Evaluation**: Appropriate. Gemini 2.5 Pro should be able to follow the instruction to create a separate, formatted list. AGLC specification is a good addition.
- **Alternative Model Suggestions**: None.

### lookup.comprehensive_analysis.requirements
- **Associated Command(s)**: lookup
- **Current LLM Model**: google/gemini-2.5-pro-preview
- **Appropriateness Evaluation**: Appropriate. Gemini 2.5 Pro is a powerful model capable of handling comprehensive analysis. The suggested addition to identify conflicting authorities and synthesize the state of law enhances this comprehensive review.
- **Alternative Model Suggestions**: None.

### lookup.standard_analysis.instructions
- **Associated Command(s)**: lookup
- **Current LLM Model**: google/gemini-2.5-pro-preview
- **Appropriateness Evaluation**: Appropriate. The model can handle these instructions for a standard lookup. The suggested addition of an executive summary and direct conclusion is a good refinement.
- **Alternative Model Suggestions**: None.

### processing.digest.summary_mode
- **Associated Command(s)**: digest
- **Current LLM Model**: anthropic/claude-sonnet-4
- **Appropriateness Evaluation**: Appropriate. Sonnet is good for summarization tasks. The suggested improvement on date precision is a minor refinement.
- **Alternative Model Suggestions**: None.

### processing.digest.issues_mode
- **Associated Command(s)**: digest
- **Current LLM Model**: anthropic/claude-sonnet-4
- **Appropriateness Evaluation**: Appropriate. Sonnet can handle structured issue spotting. The suggestion to more explicitly link facts to legal framework within the analysis pushes for slightly deeper reasoning, which Sonnet should manage.
- **Alternative Model Suggestions**:
  - **Model**: anthropic/claude-3-sonnet-20240229 (ensure latest Sonnet) or anthropic/claude-3-opus-20240229
    **Justification**: If the depth of analysis in 'issues_mode' needs significant improvement, especially the connection of facts to law, Opus would offer better reasoning. Ensuring the latest Sonnet version is used is also good.

### processing.extraction.chunk_facts_prompt
- **Associated Command(s)**: extractfacts
- **Current LLM Model**: anthropic/claude-sonnet-4
- **Appropriateness Evaluation**: Appropriate. Sonnet is suitable for this kind of focused extraction from chunks. Requesting verbatim quotes is a good addition.
- **Alternative Model Suggestions**: None.

### processing.extraction.organize_facts_prompt
- **Associated Command(s)**: extractfacts
- **Current LLM Model**: anthropic/claude-sonnet-4
- **Appropriateness Evaluation**: Appropriate. Sonnet can organize extracted facts into headings. The 'Confidence Score' suggestion adds a meta-analytical layer which Sonnet might handle, but would need clear instructions or could benefit from a slightly more advanced model if results are inconsistent.
- **Alternative Model Suggestions**:
  - **Model**: anthropic/claude-3-opus-20240229
    **Justification**: If the 'Confidence Score' and its justification prove too complex for Sonnet to do reliably, Opus could handle this meta-analysis more effectively.

### strategies.brainstorm.orthodox_prompt
- **Associated Command(s)**: brainstorm
- **Current LLM Model**: x-ai/grok-3
- **Appropriateness Evaluation**: Appropriate. Grok should be able to generate these, and the prompt already provides strong guidance. Adding a 'downsides' consideration is a minor tweak.
- **Alternative Model Suggestions**: None.

### strategies.brainstorm.unorthodox_prompt
- **Associated Command(s)**: brainstorm
- **Current LLM Model**: x-ai/grok-3
- **Appropriateness Evaluation**: Highly appropriate for Grok's creative strengths. The suggestions to use analogies and stronger justifications leverage this well.
- **Alternative Model Suggestions**: None.

### strategies.brainstorm.analysis_prompt
- **Associated Command(s)**: brainstorm
- **Current LLM Model**: anthropic/claude-sonnet-4
- **Appropriateness Evaluation**: Appropriate for analysis. The suggested improvements for roadmap structure, success probability, and comparative final recommendation add more depth, which Sonnet should handle. However, this is a complex reasoning task.
- **Alternative Model Suggestions**:
  - **Model**: anthropic/claude-3-opus-20240229 or openai/o1-pro
    **Justification**: For the highest quality analysis, especially with the added depth of comparing strategies in the final recommendation, a more powerful model like Opus or o1-pro would be beneficial for this critical analysis step.

### strategies.strategy.strategic_options_instructions
- **Associated Command(s)**: strategy
- **Current LLM Model**: openai/o1-pro
- **Appropriateness Evaluation**: Highly appropriate. o1-pro is designed for this kind of detailed strategic output. Adding ethical considerations and hurdle categorization are good refinements for this advanced model.
- **Alternative Model Suggestions**: None.

### verification.self_critique
- **Associated Command(s)**: brainstorm, draft, extractfacts, strategy
- **Current LLM Model**: Varies (typically a capable model is used for verification, often different from the generation model)
- **Appropriateness Evaluation**: Appropriate. The model performing verification needs strong analytical skills. The suggestion to expand critique to logical consistency and unstated assumptions is good. The models listed for verification (often a powerful one like GPT-4 or Claude Opus if not specified otherwise) should be capable.
- **Alternative Model Suggestions**: None.

### verification.citation_retry_instructions
- **Associated Command(s)**: lookup, digest, extractfacts, brainstorm, strategy, draft
- **Current LLM Model**: Varies by command
- **Appropriateness Evaluation**: Appropriate. This prompt is an instruction for the generating model when it retries. All primary models for these commands should be able to benefit from these clearer instructions on retry.
- **Alternative Model Suggestions**: None.

### verification.heavy_verification
- **Associated Command(s)**: extractfacts, strategy
- **Current LLM Model**: Likely a powerful model (e.g., as used for `--verify` generally, not necessarily the command's primary model)
- **Appropriateness Evaluation**: Appropriate. Heavy verification implies a strong analytical model. The suggestions to assess practical applicability and alternative interpretations fit a comprehensive review by a capable model.
- **Alternative Model Suggestions**:
  - **Model**: anthropic/claude-3-opus-20240229 or openai/gpt-4-turbo
    **Justification**: Ensuring that 'heavy_verification' uses one of the most capable models available is key to its effectiveness, as it's a critical quality gate.

### verification.system_prompt
- **Associated Command(s)**: extractfacts, strategy
- **Current LLM Model**: Likely a powerful model (as per heavy_verification)
- **Appropriateness Evaluation**: Appropriate. Sets the correct expert persona for the LLM when performing heavy verification, reinforcing the expected standard of review for 'extractfacts' and 'strategy'.
- **Alternative Model Suggestions**: None.

---

## VI. Conclusion
This analysis has reviewed the LLM prompts within the LitAssist system. Key findings include:
- A diverse range of prompts are used, from foundational instructions to command-specific templates and formatting guides.
- Most prompts are generally effective for their stated purposes, particularly the foundational and formatting prompts.
- Opportunities for improvement exist across many prompts, focusing on enhancing clarity for correctness (e.g., AGLC adherence, jurisdictional specificity), bolstering logical strength (e.g., requiring explicit reasoning, structured analysis), and fostering more creativity where appropriate (e.g., in brainstorming unorthodox strategies).
- The LLM models currently assigned to commands are largely appropriate, though for tasks requiring deep reasoning or high creativity (like advanced brainstorming analysis or complex strategy generation), leveraging more powerful models like Claude 3 Opus, GPT-4 Turbo, or ensuring o1-pro/o3 are used for their specialized tasks, could yield significant quality gains, justifying potential cost increases.
- Document templates and format definitions are highly effective and crucial for structured output, forming a strong backbone for the system.
Implementing the suggested prompt refinements and considering targeted model upgrades for specific tasks are recommended to further enhance the quality, reliability, and utility of LitAssist outputs.
