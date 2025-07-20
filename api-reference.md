---
layout: default
title: API Reference
permalink: /api/
---

# API Reference

Complete command reference for LitAssist CLI.

## Global Options

```bash
litassist [--log-format json|markdown] [--verbose] COMMAND
```

- `--log-format`: Output format for audit logs (json or markdown)
- `--verbose`: Enable debug-level logging

## Commands

### caseplan

Generate a comprehensive litigation workflow plan.

```bash
litassist caseplan CASE_FACTS [OPTIONS]
```

**Arguments:**
- `CASE_FACTS`: Path to case facts file

**Options:**
- `--context`: Additional context to guide analysis
- `--budget`: Budget level (minimal/standard/comprehensive)

**Example:**
```bash
litassist caseplan case_facts.txt --budget standard
```

### lookup

Research case law and legal principles.

```bash
litassist lookup QUERY [OPTIONS]
```

**Arguments:**
- `QUERY`: Legal query or topic

**Options:**
- `--comprehensive`: Enable comprehensive analysis
- `--include-commentary`: Include legal commentary

**Example:**
```bash
litassist lookup "negligence duty of care" --comprehensive
```

### digest

Process and summarize legal documents.

```bash
litassist digest FILE [OPTIONS]
```

**Arguments:**
- `FILE`: Path to document file

**Options:**
- `--mode`: Processing mode (summary/issues)
- `--context`: Focus area for analysis

**Example:**
```bash
litassist digest contract.pdf --mode issues
```

### extractfacts

Extract structured facts from documents.

```bash
litassist extractfacts FILE [OPTIONS]
```

**Arguments:**
- `FILE`: Path to document file

**Options:**
- `--output`: Output file path (default: case_facts_extracted.txt)
- `--verify`: Enable verification

**Example:**
```bash
litassist extractfacts witness_statement.pdf --verify
```

### brainstorm

Generate legal strategies and arguments.

```bash
litassist brainstorm [OPTIONS]
```

**Options:**
- `--facts`: Path to case facts file
- `--mode`: Strategy mode (orthodox/unorthodox/both)

**Example:**
```bash
litassist brainstorm --facts case_facts.txt --mode both
```

### strategy

Develop targeted legal strategies.

```bash
litassist strategy --facts FACTS_FILE [OPTIONS]
```

**Options:**
- `--facts`: Path to case facts file (required)
- `--brainstorm-file`: Path to brainstorm output
- `--reasoning-effort`: Effort level (low/medium/high)

**Example:**
```bash
litassist strategy --facts case_facts.txt --reasoning-effort high
```

### draft

Draft legal documents with citations.

```bash
litassist draft --type DOC_TYPE --facts FACTS_FILE [OPTIONS]
```

**Options:**
- `--type`: Document type (statement_of_claim/affidavit/etc)
- `--facts`: Path to case facts file
- `--instructions`: Additional drafting instructions
- `--verify`: Enable citation verification

**Example:**
```bash
litassist draft --type affidavit --facts case_facts.txt --verify
```

### counselnotes

Generate strategic advocate analysis.

```bash
litassist counselnotes FILE [OPTIONS]
```

**Arguments:**
- `FILE`: Path to input document

**Options:**
- `--extract`: Extract structured data
- `--output-dir`: Output directory for extractions

**Example:**
```bash
litassist counselnotes legal_opinion.pdf --extract
```

### barbrief

Create comprehensive barrister's briefs.

```bash
litassist barbrief [OPTIONS]
```

**Options:**
- `--case-name`: Name of the case
- `--facts`: Path to case facts
- `--documents`: Path to document bundle
- `--hearing-type`: Type of hearing
- `--context`: Additional context
- `--verify`: Enable verification

**Example:**
```bash
litassist barbrief --case-name "Smith v Jones" --facts case_facts.txt --hearing-type "summary judgment"
```

### test

Test API connectivity and configuration.

```bash
litassist test
```

Validates credentials for:
- OpenRouter API
- OpenAI API
- Google Custom Search API
- Pinecone API

## Output Formats

Most commands support structured output formats:

- **JSON**: Machine-readable format for integration
- **Markdown**: Human-readable documentation format
- **Text**: Plain text for simple consumption

## Error Handling

LitAssist provides detailed error messages:

- **API Errors**: Connection and authentication issues
- **Validation Errors**: Invalid inputs or parameters
- **Processing Errors**: Document processing failures

## Rate Limits

Be aware of API rate limits:

- OpenRouter: Varies by model
- Google CSE: 100 queries/day (free tier)
- Pinecone: Based on subscription

## Best Practices

1. Always start with `caseplan` for structured workflows
2. Use `--verify` flag for important documents
3. Save command outputs for audit trails
4. Review generated content before use
5. Keep case facts files updated

## Environment Variables

Override configuration with environment variables:

```bash
LITASSIST_LOG_FORMAT=json
LITASSIST_VERBOSE=true
LITASSIST_CONFIG_PATH=/custom/path/config.yaml
```

## Support

For detailed usage examples and tutorials, see:
- [User Guide](/guide)
- [Examples](/examples)
- [GitHub Issues](https://github.com/litassist/litassist/issues)