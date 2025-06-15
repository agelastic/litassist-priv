# Minimal Lookup Enhancement Design

## Status Update (June 2025)

- Lookup is now Jade.io-only (no Google CSE or user-selectable engine).
- All citations are verified in real time against AustLII.
- The --comprehensive flag is available for exhaustive analysis.
- Citation validation is always performed; warnings are provided for unverifiable citations.

## Problem
Lookup output is a wall of text that users must manually process to extract citations and principles.

## Minimal Useful Solution

### 1. Add Basic Structure to Output

Instead of pure text, add simple sections:

```
=== LEGAL PRINCIPLES ===
1. Self-defence requires reasonable belief of imminent threat
   - R v Katarzynski [2002] NSWSC 613 at [23]

2. Force used must be proportionate to threat
   - R v Brown [2019] NSWCCA 123 at [45]

=== KEY CASES ===
R v Katarzynski [2002] NSWSC 613
- Facts: Defendant claimed self-defence in assault case
- Held: Test is purely subjective belief of threat
- Quote: "The critical question is what the accused believed..." [23]

=== PRACTICAL CHECKLIST ===
□ Evidence of threat
□ Defendant's subjective belief
□ Proportionality of response
□ No avenue of escape

=== CITATIONS LIST ===
R v Katarzynski [2002] NSWSC 613
R v Brown [2019] NSWCCA 123
Crimes Act 1900 (NSW) s 418
```

### 2. Simple Command Enhancement

Add just ONE new option:

```python
@click.option('--extract', type=click.Choice(['citations', 'principles', 'checklist']), 
              help="Extract specific information")
```

Examples:
```bash
# Get just citations for copying into a document
litassist lookup "self defence assault" --extract citations

# Get principles for advice letter
litassist lookup "negligence elements" --extract principles  

# Get checklist for file notes
litassist lookup "unfair dismissal requirements" --extract checklist
```

### 3. Enhanced Prompt (Minimal Change)

Add to existing prompt:

```python
if extract:
    prompt += f"\n\nAlso provide a clear '{extract.upper()}' section that lists just the {extract} in a format easy to copy and use."
```

### 4. Simple Post-Processing

```python
def format_lookup_output(content: str, extract: str = None) -> str:
    """Add basic structure to lookup output."""
    
    # If extract option used, pull out just that section
    if extract == 'citations':
        # Find all citations using simple regex
        citations = re.findall(r'\[\d{4}\][\s\w]+\d+', content)
        citations += re.findall(r'\(\d{4}\)\s+\d+\s+\w+\s+\d+', content)
        return "CITATIONS FOUND:\n" + "\n".join(sorted(set(citations)))
    
    elif extract == 'principles':
        # Extract numbered principles
        # Simple implementation - just find sentences before citations
        pass
        
    # Otherwise, add basic structure markers
    structured = content
    structured = structured.replace("Legal principles", "=== LEGAL PRINCIPLES ===")
    structured = structured.replace("Key cases", "=== KEY CASES ===")
    # etc.
    
    return structured
```

### 5. Output File Naming

Make output files more useful:

```python
# Current: lookup_what_defences_exist_to_adv_20250524_140000.txt
# Better: lookup_citations_self_defence_20250524.txt (when using --extract)
```

### 6. Future Integration (Don't Build Yet)

The structured sections make future integration easy:
- Other commands could read the "CITATIONS LIST" section
- Copy-paste is easier with clear sections
- But we're NOT building parsing logic yet

## Implementation Steps

1. **Add --extract option** (30 min)
2. **Modify prompt slightly** (15 min)
3. **Add basic section markers to output** (1 hour)
4. **Test with real queries** (1 hour)

Total: ~3 hours of work

## Benefits

- **Immediate value**: Users can extract citations quickly
- **No breaking changes**: Default behavior unchanged  
- **Simple to implement**: Just formatting, no complex parsing
- **Foundation for future**: Structure enables later integration

## Examples

### Current Output
```
The principle of self-defence in NSW is found in various cases including 
R v Katarzynski [2002] NSWSC 613 where the court held that...
[wall of text continues]
```

### Enhanced Output (default)
```
=== LEGAL PRINCIPLES ===
1. Self-defence requires reasonable belief of imminent threat
   - R v Katarzynski [2002] NSWSC 613 at [23]

=== KEY CASES ===
[structured case summaries]

=== CITATIONS LIST ===
[clean list of citations]
```

### Enhanced Output (--extract citations)
```
CITATIONS FOUND:
Crimes Act 1900 (NSW) s 418
R v Brown [2019] NSWCCA 123  
R v Katarzynski [2002] NSWSC 613
```

## Not Included (Avoid Overengineering)

- ❌ JSON output
- ❌ Complex parsing
- ❌ Integration with other commands
- ❌ Area-specific templates
- ❌ Database storage
- ❌ Citation validation

Just make the output more useful for copy-paste workflows that lawyers actually do.
