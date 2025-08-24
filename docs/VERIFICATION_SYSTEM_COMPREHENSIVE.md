# LitAssist Verification System - Comprehensive Documentation

## Table of Contents
1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Standard Verification Pipeline (Non-CoVe)](#standard-verification-pipeline-non-cove)
4. [Chain of Verification (CoVe) System](#chain-of-verification-cove-system)
5. [Citation Verification System](#citation-verification-system)
6. [Command-Specific Verification Usage](#command-specific-verification-usage)
7. [Model Configuration and Parameters](#model-configuration-and-parameters)
8. [Verification Flow Diagrams](#verification-flow-diagrams)
9. [Logging and Accountability](#logging-and-accountability)

## Executive Summary

The LitAssist verification system is a multi-layered legal document verification architecture designed specifically for Australian legal practice. It consists of two primary verification pathways:

1. **Standard Verification**: A three-stage pipeline including pattern validation, database verification, and LLM-based correction
2. **Chain of Verification (CoVe)**: A four-stage Meta-inspired verification system that generates questions, answers them independently, detects inconsistencies, and regenerates content when issues are found

The system ensures legal accuracy, citation validity, and Australian law compliance across all generated content.

## System Architecture

### Core Components

1. **`verification_chain.py`**: Orchestrates verification flows
   - `run_verification_chain()`: Standard verification pipeline
   - `run_cove_verification()`: Chain of Verification implementation
   - `format_cove_report()`: Reporting utilities

2. **`llm.py`**: LLM client with verification methods
   - `verify()`: Self-critique verification
   - `validate_and_verify_citations()`: Citation validation
   - `verify_with_level()`: Graduated verification (light/heavy)

3. **`citation_verify.py`**: Real-time citation verification
   - Jade.io database checking via Google Custom Search
   - Citation caching and pattern validation
   
4. **`citation_patterns.py`**: Offline citation pattern validation
   - Australian legal citation format checking
   - International citation recognition

## Standard Verification Pipeline (Non-CoVe)

### Overview
The standard verification pipeline is a three-stage process that runs automatically on high-risk commands unless explicitly disabled or replaced by CoVe.

### Stage 1: Pattern Validation (Offline)
```python
# Fast, offline validation using regex patterns
pattern_issues = validate_citation_patterns(content, enable_online=False)
```
- **Purpose**: Quick syntactic validation of citation formats
- **Speed**: <100ms
- **Coverage**: Australian and international citation patterns
- **Early Exit**: For high-risk commands (extractfacts, strategy, draft) if issues found

### Stage 2: Database Verification (Online)
```python
# Real-time Jade.io verification via Google CSE
verified, unverified = verify_all_citations(content)
```
- **Purpose**: Confirm citations exist in legal databases
- **Method**: Google Custom Search API → Jade.io
- **Caching**: 15-minute cache to avoid redundant API calls
- **Rate Limiting**: Respects API quotas with exponential backoff
- **Early Exit**: For strict commands (extractfacts, strategy) if unverified citations found

### Stage 3: LLM Verification (Self-Critique)
```python
# LLM-based comprehensive verification
client = LLMClientFactory.for_command("verification")
corrected_content, _ = client.verify(content, citation_context, reasoning_context)
```
- **Purpose**: Semantic verification and correction
- **Model**: Typically Claude Sonnet 4 or GPT-4
- **Parameters**: Temperature=0, top_p=0.2 (deterministic)
- **Context**: Can include citation and reasoning reports
- **Output**: Corrected document with issues fixed

### Verification Levels

#### Light Verification
- **Focus**: Australian English compliance only
- **Prompt**: `verification.light_verification`
- **Use Case**: Quick language standardization

#### Heavy Verification  
- **Focus**: Comprehensive legal accuracy
- **Prompt**: `verification.heavy_verification`
- **Checks**:
  - All citations verified
  - Legal reasoning validated
  - Procedural errors identified
  - Australian English compliance

## Chain of Verification (CoVe) System

### Concept Origin
Based on Meta's "Chain-of-Verification Reduces Hallucination in Large Language Models" paper, adapted for legal document verification.

### Implementation Philosophy
- **No Local Parsing**: Trust LLM outputs completely
- **Four Stages**: Questions → Answers → Verification → Regeneration
- **Separate Models**: Each stage uses independent LLM instance to avoid bias
- **Complete Regeneration**: Step 4 regenerates entire document when issues found

### CoVe Stages

#### Stage 1: Question Generation
```python
client_questions = LLMClientFactory.for_command("cove-questions")
questions = client_questions.complete(questions_prompt)
```
- **Purpose**: Generate 10 verification questions
- **Focus Areas**:
  - Citations accuracy
  - Dates consistency
  - Party names
  - Legal principles
  - Potential inconsistencies
- **Model**: Often uses different model than content generation

#### Stage 2: Independent Answering
```python
client_answers = LLMClientFactory.for_command("cove-answers")
answers = client_answers.complete(answers_prompt)
```
- **Purpose**: Answer questions using legal knowledge only
- **Method**: Questions answered WITHOUT seeing original document
- **Format**: Yes/No/Uncertain with explanations
- **Independence**: Prevents confirmation bias

#### Stage 3: Inconsistency Detection
```python
client_verify = LLMClientFactory.for_command("cove-verify")
issues = client_verify.complete(verify_prompt)
```
- **Purpose**: Compare Q&A against original document
- **Output**: Specific issues or "No issues found"
- **Decision Point**: Determines if regeneration needed

#### Stage 4: Content Regeneration (When Issues Found)
```python
client_final = LLMClientFactory.for_command("cove-final")
final_content = client_final.complete(regenerate_prompt)
```
- **Purpose**: Fix all identified issues
- **Method**: Complete document regeneration
- **Context**: Uses issues list and Q&A for guidance
- **Output**: Corrected, legally accurate document

### CoVe vs Standard Verification

| Aspect | Standard Verification | CoVe |
|--------|----------------------|------|
| **Stages** | 3 (Pattern, Database, LLM) | 4 (Questions, Answers, Verify, Regenerate) |
| **Models Used** | 1 (verification model) | 4 (separate for each stage) |
| **Citation Check** | Yes (Stage 2) | Indirect (through questions) |
| **Regeneration** | Inline corrections | Complete regeneration |
| **Use Trigger** | Default for high-risk commands | --cove flag |
| **Processing Time** | ~5-10 seconds | ~15-30 seconds |
| **Token Usage** | ~5-10K tokens | ~20-40K tokens |

## Citation Verification System

### Multi-Layer Citation Verification

#### Layer 1: Pattern Validation (Offline)
```python
# citation_patterns.py
MODERN_NEUTRAL = r'\[(\d{4})\]\s+([A-Z]+(?:CA|FC|CFamC\dA)?)\s+(\d+)'
TRADITIONAL = r'.*?\s*\((\d{4})\)\s*(\d+)\s*([A-Z]+)\s*(\d+)'
```
- **Australian Formats**: HCA, FCA, NSWSC, VSC, etc.
- **International**: UK, NZ, Canadian citations
- **Speed**: Instant pattern matching

#### Layer 2: Database Verification (Online)
```python
# citation_verify.py
def verify_via_jade(citation: str) -> bool:
    # Google CSE → Jade.io lookup
    search_url = f"{CONFIG.google_cse_url}?q={citation}+site:jade.io"
```
- **Primary Source**: Jade.io legal database
- **Fallback**: AustLII for older cases
- **Caching**: 15-minute result cache
- **Rate Limiting**: Automatic with backoff

#### Layer 3: Selective Regeneration
```python
# For failed citations
def _remove_and_regenerate_citations(content: str, unverified: List) -> str:
    # Surgical removal of bad citations
    # Targeted regeneration of affected sections
```
- **Strategy**: Remove unverified citations
- **Regeneration**: Only affected paragraphs
- **Preservation**: Keep verified content intact

### Citation Verification Configuration

```python
# From config.yaml
citation_verification:
  enabled: true
  strict_mode: true  # Fail on unverified
  cache_duration: 900  # 15 minutes
  max_retries: 3
  backoff_factor: 2
```

## Command-Specific Verification Usage

### High-Risk Commands (Always Verify)

#### extractfacts
```python
@click.option("--cove", is_flag=True, help="Use Chain of Verification instead of standard verification")
def extractfacts(..., cove):
    if cove:
        content, cove_results = run_cove_verification(content, 'extractfacts')
    else:
        content, _ = verify_content_if_needed(client, content, "extractfacts", verify_flag=True)
```
- **Default**: Standard 3-stage verification
- **With --cove**: Replaces standard with CoVe
- **Never**: Double verification (one OR the other)

#### strategy
```python
@click.option("--cove", is_flag=True, help="Use Chain of Verification instead of standard verification")
def strategy(..., cove):
    if cove:
        strategy_content, cove_results = run_cove_verification(strategy_content, 'strategy')
    else:
        strategy_content, _ = verify_content_if_needed(llm_client, strategy_content, "strategy", verify_flag=True)
```
- **Focus**: Legal strategy accuracy
- **Reasoning**: Creates consolidated reasoning trace
- **Verification**: Either standard or CoVe

#### draft
```python
@click.option("--cove", is_flag=True, help="Use Chain of Verification (experimental)")
def draft(..., cove):
    if cove:
        content, cove_results = run_cove_verification(content, 'draft')
```
- **Document Types**: Affidavits, claims, applications
- **Hallucination Detection**: `detect_factual_hallucinations()`
- **Placeholders**: [AGE TO BE PROVIDED], [ADDRESS TO BE CONFIRMED]

### Verification-Optional Commands

#### brainstorm
```python
# Always verifies unorthodox strategies
unorthodox_content, _ = unorthodox_client.complete(unorthodox_messages)
# Standard verification runs automatically in complete()
```
- **Orthodox**: Optional verification
- **Unorthodox**: Always verified (creative strategies need validation)

#### verify (Dedicated Verification Command)
```python
@click.option("--citations", is_flag=True)
@click.option("--soundness", is_flag=True)
@click.option("--reasoning", is_flag=True)
@click.option("--cove", is_flag=True)
def verify(file, citations, soundness, reasoning, cove):
```
- **Modular**: Can verify specific aspects
- **Default**: All three types if no flags
- **CoVe**: Adds as final stage after other verifications

### Commands with Optional CoVe

#### barbrief
```python
@click.option("--cove", is_flag=True, help="Apply Chain of Verification")
```
- **Purpose**: Barrister brief preparation
- **CoVe Usage**: Final quality check

#### counselnotes
```python
@click.option("--cove", is_flag=True, help="Apply Chain of Verification")
```
- **Purpose**: Counsel advice notes
- **CoVe Usage**: Ensure strategic accuracy

## Model Configuration and Parameters

### Verification Model Selection

```yaml
# config.yaml
commands:
  verification:
    model: anthropic/claude-sonnet-4
    temperature: 0.0
    top_p: 0.2
    max_tokens: 65536
    
  cove-questions:
    model: anthropic/claude-sonnet-4
    temperature: 0.3  # Some creativity for questions
    
  cove-answers:
    model: openai/gpt-4-turbo
    temperature: 0.0  # Factual answers
    
  cove-verify:
    model: anthropic/claude-sonnet-4
    temperature: 0.0  # Deterministic comparison
    
  cove-final:
    model: openai/o3-pro  # Premium regeneration
    max_completion_tokens: 65536
    reasoning_effort: medium
```

### Model-Specific Parameter Restrictions

#### OpenAI o3-pro (Reasoning Models)
```python
# Only these parameters allowed:
allowed_params = ['max_completion_tokens', 'reasoning_effort']
# NOT allowed: temperature, top_p, frequency_penalty, etc.
```

#### Standard Models
```python
# Full parameter support:
params = {
    'temperature': 0.0,
    'top_p': 0.2,
    'max_tokens': 65536,
    'frequency_penalty': 0.0,
    'presence_penalty': 0.0
}
```

### Verification Parameter Strategy

| Verification Type | Temperature | Top_p | Purpose |
|------------------|-------------|-------|---------|
| Citation Check | 0.0 | 0.2 | Deterministic validation |
| Legal Soundness | 0.0 | 0.2 | Consistent analysis |
| CoVe Questions | 0.3 | 0.5 | Creative question generation |
| CoVe Answers | 0.0 | 0.2 | Factual responses |
| CoVe Regeneration | 0.1 | 0.3 | Controlled creativity |

## Verification Flow Diagrams

### Standard Verification Flow
```
Content Input
    ↓
[Stage 1: Pattern Validation]
    ↓ (pass)
[Stage 2: Database Verification]
    ↓ (pass)
[Stage 3: LLM Self-Critique]
    ↓
Verified Content Output
```

### CoVe Flow
```
Content Input
    ↓
[Stage 1: Generate 10 Questions]
    ↓
[Stage 2: Answer Independently]
    ↓
[Stage 3: Detect Inconsistencies]
    ↓
Issues Found? → Yes → [Stage 4: Regenerate]
    ↓ No              ↓
Original Content    Regenerated Content
```

### Command Decision Flow
```
Command Execution
    ↓
Has --cove flag? → Yes → Run CoVe Only
    ↓ No
High-risk command? → Yes → Run Standard Verification
    ↓ No
Skip Verification
```

## Logging and Accountability

### Comprehensive Logging Structure

#### Standard Verification Logs
```json
{
  "verification_summary": {
    "command": "extractfacts",
    "stages": {
      "patterns": {"passed": true, "issues": []},
      "database": {"verified": 15, "unverified": 2},
      "llm": {"corrections_made": true}
    },
    "timestamp": "2024-11-13 10:30:00"
  }
}
```

#### CoVe Stage Logs
```json
{
  "cove_extractfacts_summary": {
    "stages": {
      "questions": {
        "prompt": "[FULL PROMPT]",
        "prompt_truncated": "[FIRST 500 CHARS]",
        "response": "[QUESTIONS]",
        "model": "claude-sonnet-4",
        "usage": {"total_tokens": 2500}
      },
      "answers": {...},
      "verification": {...},
      "regeneration": {
        "response": "[FULL REGENERATED CONTENT]",
        "content_changed": true
      }
    },
    "result": {
      "passed": false,
      "issues_found": "Citation inconsistencies..."
    }
  }
}
```

### Legal Accountability Features

1. **Full Prompt Storage**: Every prompt saved in full for CoVe
2. **Response Preservation**: Complete regenerated content logged
3. **Model Attribution**: Which model made each decision
4. **Token Tracking**: Cost accountability
5. **Timestamp Chain**: Audit trail of all operations
6. **Context Preservation**: Prior verification results included

### Output File Metadata

```python
# Added to all output files
metadata = {
    "Verification": "Chain of Verification (CoVe)" if cove else "Standard verification",
    "CoVe Status": "REGENERATED" if regenerated else "PASSED",
    "Model": client.model,
    "Issues Fixed": cove_results['cove']['issues'] if regenerated else None
}
```

## Best Practices and Guidelines

### When to Use CoVe

**Recommended:**
- Final document review before filing
- High-stakes legal documents
- Complex multi-party litigation
- Novel legal arguments
- When standard verification finds issues

**Not Recommended:**
- Quick drafts or iterations
- Simple correspondence
- Internal notes
- Time-sensitive matters (adds 15-30 seconds)

### Verification Strategy by Document Type

| Document Type | Default | Recommended |
|--------------|---------|-------------|
| Court Filings | Standard | CoVe for final |
| Legal Advice | Standard | Standard sufficient |
| Affidavits | Standard + Hallucination Detection | CoVe recommended |
| Strategies | Standard | CoVe for complex cases |
| Research | Citation verification only | Standard sufficient |

### Performance Considerations

#### Token Usage
- Standard Verification: ~5-10K tokens
- CoVe: ~20-40K tokens (4x more expensive)
- Citation Verification: Minimal (API calls only)

#### Processing Time
- Pattern Validation: <100ms
- Database Verification: 1-2s per citation
- LLM Verification: 3-5 seconds
- Full CoVe: 15-30 seconds

#### API Limits
- Google CSE: 100 queries/day (free tier)
- OpenRouter: Based on account limits
- Rate limiting: Automatic exponential backoff

## Conclusion

The LitAssist verification system provides comprehensive, multi-layered validation for Australian legal documents. The dual-pathway approach (Standard vs CoVe) offers flexibility between speed and thoroughness, while maintaining strict legal accuracy standards throughout.

Key strengths:
- **Legal Accountability**: Full audit trail for all verifications
- **Citation Accuracy**: Real-time Jade.io verification
- **Flexibility**: Choose verification depth based on needs
- **Australian Focus**: Tailored for Australian legal practice
- **Hallucination Prevention**: Multiple independent checks

The system ensures that all generated legal content meets professional standards while providing transparent, auditable verification processes suitable for legal practice requirements.