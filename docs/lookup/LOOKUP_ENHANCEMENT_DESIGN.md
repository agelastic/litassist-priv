# Lookup Command Enhancement Design

## Status Update (June 2025)

- Lookup is now Jade.io-only (no Google CSE or user-selectable engine).
- All citations are verified in real time against AustLII.
- The --comprehensive flag is available for exhaustive analysis.
- The --engine option and "search_engine" metadata are obsolete; all lookups use Jade.io.

## Overview

The lookup command currently produces unstructured text output that requires manual processing. This design document outlines enhancements to make lookup results actionable, structured, and integrated with other LitAssist commands.

## Current Limitations

1. **Output is unstructured text** - Difficult to extract specific information
2. **No integration** - Results can't be used by other commands
3. **No categorization** - All information mixed together
4. **Manual citation extraction** - Users must copy citations manually
5. **No templates** - Same format regardless of legal area

## Proposed Architecture

### 1. Structured Output Schema

```python
LookupResult = {
    "metadata": {
        "query": str,
        "timestamp": str,
        "legal_area": str,  # detected or specified
        "jurisdiction": str,
        # (Obsolete: always "jade" now)
"search_engine": str,  # always "jade"
        "mode": str  # irac/broad
    },
    
    "legal_principles": [
        {
            "principle": str,  # The legal rule/test
            "authority": str,  # Primary case establishing it
            "citations": [str],  # All relevant citations
            "paragraph_refs": [str],  # Specific paragraphs
            "qualification": str,  # Any limitations/exceptions
            "strength": str  # binding/persuasive/considered
        }
    ],
    
    "cases": [
        {
            "name": str,
            "citation": str,
            "year": int,
            "court": str,
            "court_hierarchy": int,  # 1=HC, 2=FCA/FCAFC, 3=State Supreme, etc.
            "judges": [str],
            "summary": str,
            "relevant_facts": [str],
            "outcome": str,
            "key_quotes": [
                {
                    "text": str,
                    "paragraph": str,
                    "judge": str
                }
            ],
            "subsequent_treatment": str,  # applied/distinguished/overruled
            "relevance_score": float  # 0-1 based on query match
        }
    ],
    
    "statutory_provisions": [
        {
            "title": str,
            "section": str,
            "text": str,
            "jurisdiction": str,
            "currency_date": str,
            "related_cases": [str]  # cases interpreting this section
        }
    ],
    
    "procedural_requirements": [
        {
            "requirement": str,
            "authority": str,
            "time_limit": str,
            "form_number": str,
            "notes": str
        }
    ],
    
    "practical_guidance": {
        "key_factors": [str],  # Checklist items
        "common_arguments": [str],
        "potential_defences": [str],
        "evidence_needed": [str],
        "strategic_considerations": [str]
    },
    
    "extracted_lists": {
        # Dynamic based on query
        "elements": [],  # For "elements of negligence"
        "factors": [],   # For "best interests factors"
        "grounds": [],   # For "grounds for appeal"
        "defences": [],  # For "defences to assault"
    }
}
```

### 2. Enhanced Command Interface

```python
@click.command()
@click.argument('question')
@click.option('--mode', type=click.Choice(['irac', 'broad']), default='irac')
# (Obsolete: --engine option is no longer available; all lookups use Jade.io)
# @click.option('--engine', type=click.Choice(['jade', 'austlii', 'general']), default='jade')
@click.option('--format', type=click.Choice(['text', 'structured', 'citations', 'checklist']), default='text')
@click.option('--extract', multiple=True, type=click.Choice([
    'principles', 'cases', 'elements', 'factors', 'quotes', 'procedural'
]))
@click.option('--legal-area', type=click.Choice([
    'criminal', 'family', 'civil', 'commercial', 'administrative', 'auto'
]), default='auto')
@click.option('--save-for', type=click.Choice(['draft', 'strategy', 'advice', 'submission']))
@click.option('--max-cases', type=int, default=10, help="Maximum number of cases to return")
@click.option('--min-year', type=int, help="Exclude cases before this year")
@click.option('--court-level', multiple=True, type=click.Choice([
    'hc', 'fca', 'fcafc', 'state-supreme', 'state-appeal', 'all'
]))
def lookup(question, mode, engine, format, extract, legal_area, save_for, max_cases, min_year, court_level):
    """Enhanced lookup with structured output and integration."""
```

### 3. Area-Specific Templates

```python
LEGAL_AREA_TEMPLATES = {
    "criminal": {
        "extract_patterns": {
            "elements": "elements of {offence}",
            "defences": "defences available",
            "sentencing": "sentencing range and factors"
        },
        "output_structure": {
            "offence_elements": [],
            "available_defences": [],
            "sentencing_principles": [],
            "mitigating_factors": [],
            "aggravating_factors": [],
            "comparable_sentences": []
        },
        "prompts": {
            "system": "Focus on criminal law principles, elements, defences, and sentencing.",
            "extraction": "Extract offence elements, defences, and sentencing considerations."
        }
    },
    
    "family": {
        "extract_patterns": {
            "factors": "best interests factors",
            "principles": "parenting principles",
            "procedure": "procedural requirements"
        },
        "output_structure": {
            "best_interests_factors": [],
            "risk_considerations": [],
            "presumptions": [],
            "procedural_steps": [],
            "evidence_checklist": []
        },
        "prompts": {
            "system": "Focus on family law, best interests of children, and Part VII considerations.",
            "extraction": "Extract factors courts consider in parenting matters."
        }
    },
    
    "civil": {
        "extract_patterns": {
            "elements": "cause of action elements",
            "damages": "heads of damage",
            "limitation": "limitation periods"
        },
        "output_structure": {
            "cause_of_action": [],
            "required_elements": [],
            "damages_available": [],
            "limitation_period": "",
            "defences": []
        }
    },
    
    "commercial": {
        "extract_patterns": {
            "duties": "director duties",
            "breach": "breach indicators",
            "remedies": "available remedies"
        },
        "output_structure": {
            "statutory_duties": [],
            "breach_indicators": [],
            "defences": [],
            "remedies": [],
            "procedural_requirements": []
        }
    },
    
    "administrative": {
        "extract_patterns": {
            "grounds": "review grounds",
            "errors": "jurisdictional errors",
            "procedure": "judicial review procedure"
        },
        "output_structure": {
            "review_grounds": [],
            "jurisdictional_errors": [],
            "time_limits": [],
            "standing_requirements": [],
            "remedies": []
        }
    }
}
```

### 4. Integration Points

```python
class LookupResultManager:
    """Manages structured lookup results for use by other commands."""
    
    def save_for_draft(self, results: dict, filename: str):
        """Format results for draft command consumption."""
        draft_ready = {
            "authorities": self._format_citations(results),
            "quotes": self._extract_key_quotes(results),
            "principles": self._summarize_principles(results)
        }
        save_json(f"lookup_for_draft_{filename}.json", draft_ready)
    
    def save_for_strategy(self, results: dict, filename: str):
        """Format results for strategy command consumption."""
        strategy_ready = {
            "legal_framework": results['legal_principles'],
            "procedural_requirements": results['procedural_requirements'],
            "risk_factors": self._extract_risk_factors(results),
            "success_indicators": self._analyze_outcomes(results)
        }
        save_json(f"lookup_for_strategy_{filename}.json", strategy_ready)
    
    def save_as_checklist(self, results: dict, filename: str):
        """Create actionable checklist from results."""
        checklist = {
            "evidence_required": [],
            "legal_elements": [],
            "procedural_steps": [],
            "deadlines": [],
            "forms_needed": []
        }
        # Extract actionable items from results
        save_markdown(f"checklist_{filename}.md", checklist)
```

### 5. Output Formats

#### Text Format (Current)
```
Legal Research Results
Query: "negligence elements NSW"
...
```

#### Structured Format (JSON)
```json
{
  "metadata": {...},
  "legal_principles": [...],
  "cases": [...],
  "practical_guidance": {...}
}
```

#### Citations Format
```
AUTHORITIES

High Court
---------
Doe v Smith [2023] HCA 15 at [45]-[47]
  - Principle: Duty of care in novel situations
  - Applied in: Brown v Green [2024] NSWCA 8

Federal Court
------------
...
```

#### Checklist Format
```markdown
# Legal Checklist: Negligence Claim

## Elements to Prove
- [ ] Duty of care existed
  - Authority: Donoghue v Stevenson [1932] AC 562
  - Test: Reasonable foreseeability
- [ ] Breach of duty
  - Standard: Reasonable person test (s 5B Civil Liability Act)
- [ ] Causation
  - But for test: s 5D(1)(a)
  - Scope of liability: s 5D(1)(b)
- [ ] Damage not too remote
  - Test: Wagon Mound (No 1)

## Evidence Needed
- [ ] Expert report on standard of care
- [ ] Witness statements
- [ ] Medical evidence of injury
```

### 6. Enhanced Prompts

```python
def build_enhanced_prompt(question: str, options: dict) -> str:
    """Build sophisticated prompt based on options."""
    
    base_prompt = f"""
    Legal Question: {question}
    
    Provide structured analysis including:
    1. Legal principles with authorities
    2. Relevant cases with full citations
    3. Procedural requirements if applicable
    4. Practical guidance for practitioners
    """
    
    if options['extract']:
        base_prompt += f"\n\nSpecifically extract: {', '.join(options['extract'])}"
    
    if options['legal_area'] != 'auto':
        template = LEGAL_AREA_TEMPLATES[options['legal_area']]
        base_prompt += f"\n\nFocus on {options['legal_area']} law considerations."
        base_prompt += f"\n{template['prompts']['extraction']}"
    
    if options['court_level']:
        base_prompt += f"\n\nPrioritize authorities from: {', '.join(options['court_level'])}"
    
    if options['min_year']:
        base_prompt += f"\n\nFocus on recent authorities (after {options['min_year']})"
    
    return base_prompt
```

### 7. Post-Processing Pipeline

```python
class LookupPostProcessor:
    """Process raw LLM output into structured format."""
    
    def process(self, raw_output: str, options: dict) -> dict:
        """Main processing pipeline."""
        # 1. Parse raw output
        parsed = self.parse_raw_output(raw_output)
        
        # 2. Extract structured data
        results = {
            "metadata": self.build_metadata(options),
            "legal_principles": self.extract_principles(parsed),
            "cases": self.extract_cases(parsed),
            "statutory_provisions": self.extract_statutes(parsed),
            "procedural_requirements": self.extract_procedure(parsed),
            "practical_guidance": self.extract_guidance(parsed)
        }
        
        # 3. Apply area-specific extraction
        if options['legal_area'] != 'auto':
            results['extracted_lists'] = self.area_specific_extraction(
                parsed, options['legal_area']
            )
        
        # 4. Rank and filter
        results = self.rank_by_relevance(results)
        results = self.filter_by_options(results, options)
        
        # 5. Validate citations
        results = self.validate_citations(results)
        
        return results
    
    def extract_cases(self, parsed: dict) -> List[dict]:
        """Extract structured case information."""
        cases = []
        for case_text in parsed.get('cases', []):
            case = {
                "name": self.extract_case_name(case_text),
                "citation": self.extract_citation(case_text),
                "year": self.extract_year(case_text),
                "court": self.extract_court(case_text),
                "court_hierarchy": self.determine_hierarchy(court),
                "summary": self.extract_summary(case_text),
                "key_quotes": self.extract_quotes(case_text)
            }
            cases.append(case)
        return cases
```

### 8. Example Workflows

#### Criminal Defence Workflow
```bash
# 1. Research defences
litassist lookup "defences to assault NSW" \
  --legal-area criminal \
  --extract defences,elements \
  --format structured \
  --save-for strategy

# 2. Use in strategy
litassist strategy case_facts.txt \
  --outcome "Acquittal on self-defence" \
  --research lookup_defences_to_assault.json

# 3. Draft submissions
litassist draft case_facts.txt "submissions on self-defence" \
  --authorities lookup_defences_to_assault.json
```

#### Family Law Workflow
```bash
# 1. Research relocation factors
litassist lookup "relocation best interests child" \
  --legal-area family \
  --extract factors \
  --format checklist

# 2. Create evidence checklist
# Output: checklist_relocation_factors.md with evidence needed

# 3. Draft affidavit
litassist draft case_facts.txt "affidavit addressing relocation factors" \
  --template family-affidavit \
  --factors checklist_relocation_factors.md
```

### 9. Implementation Phases

#### Phase 1: Core Structure (1 week)
- Implement structured output schema
- Basic parsing and extraction
- JSON output format

#### Phase 2: Legal Area Templates (1 week)
- Implement area-specific templates
- Enhanced prompts per area
- Extraction patterns

#### Phase 3: Integration (2 weeks)
- Save-for functionality
- Integration with draft command
- Integration with strategy command

#### Phase 4: Advanced Features (2 weeks)
- Citation validation
- Court hierarchy ranking
- Checklist generation
- Multiple output formats

### 10. Testing Strategy

```python
# Test structured extraction
def test_extract_criminal_defences():
    result = lookup("assault defences", legal_area="criminal")
    assert "available_defences" in result["extracted_lists"]
    assert len(result["cases"]) > 0
    assert all(case["court"] for case in result["cases"])

# Test integration
def test_lookup_to_draft_integration():
    lookup_result = lookup("negligence", save_for="draft")
    draft_result = draft("advice letter", authorities="lookup_negligence.json")
    assert lookup_result["cases"][0]["citation"] in draft_result
```

### 11. Migration Path

1. **Backward Compatibility**: Keep text format as default
2. **Opt-in Structure**: Use --format structured for new format
3. **Gradual Integration**: Other commands check for structured format
4. **Documentation**: Clear examples of new workflows

### 12. Success Metrics

- **Reduced Manual Work**: 80% less time extracting citations
- **Integration Usage**: 50% of lookups used by other commands
- **Accuracy**: 95% citation validation success
- **User Satisfaction**: Positive feedback on structured output

## Conclusion

This enhancement transforms lookup from an information retrieval tool into an integrated legal research system that:
1. Produces actionable, structured output
2. Integrates seamlessly with other commands
3. Provides area-specific intelligence
4. Reduces manual processing time
5. Improves accuracy through validation

The phased implementation allows gradual rollout while maintaining backward compatibility.
