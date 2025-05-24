# LitAssist Prompts Documentation

This document provides a comprehensive reference for all LLM prompts used in LitAssist, including the reasoning behind model selection, parameter choices, and prompt engineering techniques.

## Overview

LitAssist uses carefully crafted prompts across six commands, each optimized for specific legal tasks. The prompts follow consistent patterns while being tailored to their unique purposes.

## Command-Specific Prompts

### 1. lookup - Rapid Case-law Search

**Model**: `google/gemini-2.5-pro-preview`

**Parameters**:
- IRAC mode: `temperature=0, top_p=0.1`
- Broad mode: `temperature=0.5, top_p=0.9`

**System Prompt**:
```
Australian law only. Cite sources. Provide well-structured, concise responses focused on Victorian or federal law.
```

**User Prompt Structure**:
```
Question: [user's legal question]
Links:
[list of found legal resources from Google CSE or Jade.io]
```

**Design Rationale**:
- **Model Choice**: Gemini excels at processing web content and providing fast, accurate responses
- **Temperature Strategy**: Ultra-low for IRAC format ensures consistent legal analysis structure; moderate for broad mode allows exploration
- **Citation Guard**: Implements retry logic if proper citations aren't included
- **Purpose**: Rapid legal research with proper authority citations

---

### 2. digest - Mass Document Processing

**Model**: `anthropic/claude-3-sonnet`

**Parameters**:
- Summary mode: `temperature=0, top_p=0`
- Issues mode: `temperature=0.2, top_p=0.5`

**System Prompt**:
```
Australian law only. Structure your response logically with clear headings, bullet points and concise summaries.
```

**User Prompts**:

**Summary Mode**:
```
Provide a concise chronological summary:

[document chunk]
```

**Issues Mode**:
```
Identify any potential legal issues, claims, or admissions:

[document chunk]
```

**Design Rationale**:
- **Model Choice**: Claude provides excellent summarization with strong context retention across chunks
- **Temperature Strategy**: Zero temperature for summaries ensures factual consistency; slight temperature for issues allows creative problem-spotting
- **Chunk Processing**: Handles large documents by processing in segments
- **No Verification**: Low-stakes summarization doesn't require verification

---

### 3. extractfacts - Structured Fact Extraction

**Model**: `anthropic/claude-3-sonnet`

**Parameters**: `temperature=0, top_p=0.15`

**System Prompt**:
```
Australian law only. Extract factual information precisely under the requested headings. If information is not available for a heading, write "Not specified" or "To be determined".
```

**User Prompt Template**:
```
From the following document, extract and organize the information under EXACTLY these 10 headings. Include all relevant details:

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

Document:
[document chunk]
```

**Design Rationale**:
- **Model Choice**: Claude excels at structured extraction and following precise formatting requirements
- **Temperature Strategy**: Near-zero ensures facts are extracted, not invented
- **10-Heading Structure**: Provides consistency across all matters and ensures comprehensive coverage
- **Forced Verification**: Critical foundation document requiring accuracy
- **Chunk Handling**: Processes large documents while maintaining structure

---

### 4. brainstorm - Creative Strategy Generation

**Model**: `x-ai/grok-3-beta`

**Parameters**: `temperature=0.9, top_p=0.95`

**System Prompt**:
```
Australian law only. Provide practical, actionable legal strategies. Balance creativity with factual accuracy. When suggesting strategies, clearly distinguish between established legal approaches and more innovative options. For orthodox strategies, cite relevant case law or legislation. For unorthodox strategies, acknowledge any legal uncertainties or risks. Maintain logical structure throughout your response. End with a clear, definitive recommendation section without open-ended statements.
```

**User Prompt Template**:
```
Based on these case facts, generate comprehensive legal strategies for the [plaintiff/defendant/accused] in this [civil/criminal/family/commercial/administrative] law matter.

CASE FACTS:
[case facts content]

Provide your response in EXACTLY this format:

## ORTHODOX STRATEGIES

1. [Strategy Title]
   [Brief explanation (1-2 sentences)]
   Key principles: [Legal principles or precedents]

[Continue for 10 orthodox strategies]

## UNORTHODOX STRATEGIES

1. [Strategy Title]
   [Brief explanation (1-2 sentences)]
   Key principles: [Legal principles or precedents]

[Continue for 10 unorthodox strategies]

## MOST LIKELY TO SUCCEED

1. [Strategy Title from above]
   [Why this strategy is most likely to succeed]

[List 3-5 strategies total that are most likely to succeed]
```

**Design Rationale**:
- **Model Choice**: Grok provides maximum creativity and unconventional thinking
- **Temperature Strategy**: High temperature encourages novel legal approaches
- **Format Structure**: Channels creativity into actionable strategies
- **Auto-Verification**: High-temperature outputs prone to hallucination need checking
- **Success Identification**: Forces prioritization of strategies

---

### 5. strategy - Strategic Analysis & Recommendations

**Model**: `openai/gpt-4o`

**Parameters**: `temperature=0.2, top_p=0.9, presence_penalty=0.0, frequency_penalty=0.0`

**System Prompt**:
```
Australian civil litigation expert focusing on Family Court, Federal Circuit Court, and state Supreme Courts. You must analyze case facts and produce strategic options for achieving a specific outcome.

[If strategies provided]: You have been provided with brainstormed strategies including [X] strategies marked as most likely to succeed. Pay particular attention to these when developing your strategic options.

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

[Continue for 3-5 options total]

Requirements:
- Australian law only
- Use real case citations with pinpoint references
- Be specific about probability percentages based on precedents
- Identify genuine hurdles based on the case facts provided
- Note actual missing facts from the case materials
```

**Multi-Stage Generation**:

**Stage 1 - Strategic Options** (above)

**Stage 2 - Next Steps**:
```
Based on the strategic options above, provide EXACTLY 5 immediate next steps.

# RECOMMENDED NEXT STEPS

1. [Specific action with reference to relevant rules/requirements]
[Continue for 5 steps]
```

**Stage 3 - Document Drafting**:
Generates either:
- Statement of Claim
- Originating Application  
- Affidavit

Based on the desired outcome keywords.

**Design Rationale**:
- **Model Choice**: GPT-4o provides balanced analysis with strong legal reasoning
- **Temperature Strategy**: Low temperature keeps advice grounded while allowing strategic insight
- **Probability Estimates**: The LLM provides subjective probability assessments based on its training data about similar cases - these are NOT calculated but rather the model's opinion formatted as percentages
- **Multi-Stage Approach**: Builds comprehensive strategic package
- **Integration**: Can incorporate brainstormed strategies marked as "most likely to succeed"
- **Forced Verification**: High-stakes strategic advice requires review

---

### 6. draft - Citation-rich Legal Drafting

**Model**: `openai/gpt-4o`

**Parameters**: `temperature=0.5, top_p=0.8, presence_penalty=0.1, frequency_penalty=0.1`

**Dynamic System Prompts**:

**For case_facts.txt**:
```
Australian law only. You have been provided with structured case facts. Use these facts as the foundation for your legal draft. Ensure consistency with the facts provided and do not introduce new factual claims.
```

**For strategies.txt**:
```
Australian law only. You have been provided with legal strategies for this matter. Consider these strategic approaches when drafting, particularly those marked as most likely to succeed. Ensure your draft aligns with the recommended strategic direction.
```

**For general documents**:
```
Australian law only. Draft a legally precise document with proper citations and structure. Follow Australian legal drafting conventions and ensure all arguments are well-supported.
```

**User Prompt Structure**:
```
Context:
[Retrieved passages from PDFs via RAG, or full text from case_facts.txt/strategies.txt]

Task: Draft [user's specific query]
```

**Design Rationale**:
- **Model Choice**: GPT-4o excels at legal drafting with proper citation integration
- **Temperature Strategy**: Moderate temperature balances precision with persuasive writing
- **Penalty Parameters**: Reduces repetitive phrasing common in legal writing
- **Context Awareness**: System prompt adapts based on input document type
- **RAG Integration**: Large PDFs processed through embedding/retrieval for relevant passages
- **Small File Handling**: case_facts.txt and strategies.txt included in full for complete context
- **Heavy Verification**: Legal documents require thorough review

---

## Prompt Engineering Techniques

### 1. Structured Output Enforcement
All prompts include detailed format specifications to ensure consistent, parseable outputs.

### 2. Australian Law Enforcement
Every system prompt begins with "Australian law only" and includes Australian-specific requirements.

### 3. Progressive Enhancement
Commands build on each other:
- `extractfacts` → creates case_facts.txt
- `brainstorm` → asks LLM to suggest strategies
- `strategy` → asks LLM for probability estimates, procedural steps, and draft documents
- `draft` → asks LLM to create polished legal documents

### 4. Temperature Philosophy
- **0.0**: Pure fact extraction (extractfacts summary mode)
- **0.0-0.2**: Structured analysis (extractfacts, strategy)
- **0.5**: Balanced creativity (draft, lookup broad mode)
- **0.9**: Maximum creativity (brainstorm)

### 5. Verification Strategy
- **None**: Low-stakes summaries (digest)
- **Auto**: High-temperature/hallucination-prone models (brainstorm with Grok)
- **Forced**: Foundation documents (extractfacts, strategy)
- **Optional**: User discretion (draft)

### 6. Citation Requirements
- Lookup: Must include sources from provided links
- Brainstorm: Orthodox strategies need case law
- Strategy: Requires pinpoint references
- Draft: Integrates citations from context

### 7. Chunk Processing
- Digest and extractfacts process documents in chunks
- Each chunk processed independently
- Results combined maintaining structure

### 8. Context Integration
- Draft command intelligently recognizes document types
- Strategy command can incorporate brainstormed strategies
- Commands share consistent fact structure

## Model Selection Rationale

| Model | Strengths | Used For |
|-------|-----------|----------|
| `google/gemini-2.5-pro-preview` | Fast, web-aware, good with links | Legal research (lookup) |
| `anthropic/claude-3-sonnet` | Excellent structure, reliable extraction | Summaries, fact extraction |
| `x-ai/grok-3-beta` | Maximum creativity, unconventional thinking | Strategy brainstorming |
| `openai/gpt-4o` | Balanced, excellent drafting, strong analysis | Strategic planning, document drafting |

## Configuration Impact

### Token Limits
When `use_token_limits: true` in config.yaml:
- Gemini: 2048 tokens (1024 for verification)
- Claude: 4096 tokens (1536 for verification)
- GPT-4o: 3072 tokens (1024 for verification)
- Grok: 1536 tokens (800 for verification)

### Document Chunking
- `max_chars`: Controls chunk size for digest/extractfacts
- `rag_max_chars`: Controls chunk size for draft embeddings
- Smaller chunks = more focused processing but more API calls

## Best Practices for Prompt Modification

1. **Maintain Australian Focus**: Always include "Australian law only"
2. **Preserve Structure**: Keep format specifications for downstream compatibility
3. **Test Temperature Changes**: Small changes can significantly impact output
4. **Verify Citations**: Ensure any changes maintain citation accuracy
5. **Consider Verification**: Higher stakes = need for verification
6. **Document Changes**: Update this file when modifying prompts

## Future Considerations

1. **Prompt Versioning**: Track prompt changes over time
2. **A/B Testing**: Compare prompt variations for effectiveness
3. **User Customization**: Allow prompt modifications via config
4. **Multilingual Support**: Extend beyond Australian English
5. **Specialized Domains**: Add prompts for specific legal areas