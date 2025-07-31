# Using LitAssist with Non-Legal Documents

**Last Updated**: July 20, 2025

While LitAssist is optimized for legal documents and Australian litigation workflows, it can be adapted to work with non-legal documents with some limitations and adjustments. This guide provides recommendations for processing various document types.

**Important**: If you're unsure whether to use `extractfacts` or `digest`, see [Understanding ExtractFacts vs Digest Commands](LitAssist_User_Guide.md#understanding-extractfacts-vs-digest-commands) in the main User Guide for a detailed comparison.

## Digest Command

The `digest` command offers the most flexibility for non-legal documents:

```bash
# For financial documents (bank statements, invoices)
litassist digest financial_statement.pdf --mode summary

# For commercial documents (purchase agreements, contracts)
litassist digest purchase_agreement.pdf --mode summary
```

### Recommendations for Different Document Types

| Document Type | Recommended Mode | Expected Results | Limitations |
|---------------|------------------|------------------|-------------|
| Bank statements | `summary` | Chronological financial events | May over-interpret into legal contexts |
| Purchase agreements | `summary` | Contract terms and obligations | Works well but may emphasize legal aspects |
| Medical records | `summary` | Timeline of medical events | Clinical terms may be misinterpreted |
| Technical documents | `summary` | Sequential breakdown of technical content | May miss technical nuances |
| Email correspondence | `summary` | Chronological communication summary | Context between emails may be lost |

### Best Practices

1. **Always use `--mode summary`** for non-legal documents
2. **Avoid `--mode issues`** which specifically looks for legal problems
3. **Consider document chunks** carefully - financial statements may benefit from smaller chunks
4. **Review results critically** - the model attempts to apply legal frameworks

## ExtractFacts Command

The `extractfacts` command is the most restrictive as it enforces a rigid 10-heading legal structure required by `strategy` and `brainstorm` commands:

```bash
# Not recommended for direct use on non-legal documents
litassist extractfacts purchase_agreement.pdf
```

**Key Limitations**: ExtractFacts creates structured legal foundations for downstream commands but has no `--context` option and only supports `--verify`. Use `digest` for flexible document analysis.

### Forced Categorization Issues

The command will force any content into these legal headings:
1. Parties
2. Background
3. Key Events
4. Legal Issues ← particularly problematic for non-legal documents
5. Evidence Available
6. Opposing Arguments ← may create artificial conflicts
7. Procedural History ← irrelevant for most non-legal documents
8. Jurisdiction ← irrelevant for most non-legal documents
9. Applicable Law ← will stretch to find legal connections
10. Client Objectives

### Recommended Workaround

For non-legal documents that need to be used with `strategy` or `brainstorm` commands:

1. **Use `digest` first**: Run `digest --mode summary` (optionally with `--context` for focused analysis) to understand content
2. **Manual structure creation**: Create a `case_facts.txt` file with all 10 headings
3. **Adapt content**: Fill relevant sections with content from digest output
4. **Placeholder strategy**: For irrelevant headings, add minimal placeholder content to satisfy validation
5. **File naming**: Save as `case_facts.txt` for downstream commands

## Strategy Command

The `strategy` command strictly enforces the 10-heading structure and will fail if any heading is missing:

```bash
# Will only work with properly formatted case_facts.txt
litassist strategy case_facts.txt --outcome "Negotiate improved terms on purchase agreement"
```

### Processing Mixed Document Sets

For handling multiple related but non-legal documents (e.g., financial records, correspondence, and contracts):

1. **Initial Processing**:
   - Process each document with `digest --mode summary`
   - Note key information from each document

2. **Manual Consolidation**:
   - Create a single `case_facts.txt` file
   - Include all 10 required headings
   - Distribute information under appropriate headings
   - Adapt commercial concepts to legal framework:
     - "Parties" → contracting entities
     - "Legal Issues" → contractual questions or disputes
     - "Jurisdiction" → governing law of agreements
     - "Applicable Law" → relevant regulations or contract law

3. **Validation Check**:
   - Ensure all headings are present exactly as listed
   - Run the `strategy` command with appropriate outcome

## Command Choice Quick Reference

| Need | Use Command | Why |
|------|-------------|-----|
| **Understand document content** | `digest --mode summary` | Flexible analysis, supports `--context` |
| **Focus on specific topics** | `digest --mode summary --context "payment terms"` | Targeted analysis with context |
| **Prepare for strategy/brainstorm** | `digest` → manual `case_facts.txt` | ExtractFacts forces legal structure |
| **Direct legal structuring** | `extractfacts` (only for legal docs) | Creates required 10-heading format |

## Example: Processing a Purchase Agreement

```bash
# Step 1: Get a summary of the document (optionally with focus)
litassist digest purchase_agreement.pdf --mode summary --context "payment terms and obligations"

# Step 2: Manually create case_facts.txt with all 10 headings
# (Include information from digest output)

# Step 3: Run strategy with business-oriented outcome
litassist strategy case_facts.txt --outcome "Negotiate more favorable payment terms"
```

## Limitations and Considerations

- The tools are optimized for legal analysis - outputs will have a legal perspective
- Australian legal context is assumed in all processing
- Financial or business concepts may be reinterpreted in legal terms
- The 10-heading structure is rigid and cannot be modified
- Some creative adaptation is necessary for truly non-legal documents

## Conclusion

While LitAssist is primarily designed for legal workflows, the `digest` command offers reasonable flexibility for non-legal documents. For workflows requiring `strategy` or `brainstorm` commands, manual pre-processing and adaptation to the required structure is necessary.
