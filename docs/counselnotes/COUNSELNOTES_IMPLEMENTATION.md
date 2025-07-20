# Counsel's Notes Command - Technical Implementation

## Overview

The `counselnotes` command provides strategic analysis and structured extraction from legal documents using an advocate's perspective. This document covers the technical implementation details, architecture patterns, and integration with the LitAssist system.

## Command Architecture

### Core Module Structure

```
litassist/commands/counselnotes.py
├── counselnotes()           # Main Click command interface
├── process_documents()      # Document processing pipeline
├── generate_strategic_analysis()  # Strategic analysis generation
├── generate_extraction()    # Structured JSON extraction
└── verify_citations()       # Citation verification integration
```

### Key Dependencies

- **LLMClientFactory**: Model selection and configuration
- **PROMPTS**: YAML-based prompt template system
- **Citation Verification**: Real-time validation via Jade.io
- **File Processing**: Document reading and chunking utilities
- **Progress Tracking**: Real-time progress indicators

## Implementation Patterns

### 1. LLMClientFactory Integration

```python
def counselnotes():
    client = LLMClientFactory.for_command("counselnotes")
    # Uses anthropic/claude-sonnet-4 for balanced analysis
```

**Benefits:**
- Centralized model configuration
- Consistent parameter application
- Easy model switching for different analysis types

### 2. YAML-Based Prompt Management

```python
def generate_strategic_analysis(content):
    prompt = PROMPTS.get("counselnotes_strategic_analysis")
    # Structured prompts in litassist/prompts/processing.yaml
```

**Template Structure:**
- `counselnotes_strategic_analysis`: Main strategic analysis framework
- `counselnotes_extract_*`: Extraction mode templates (all, citations, principles, checklist)
- `counselnotes_synthesis`: Multi-document cross-synthesis prompts

### 3. Document Processing Pipeline

```python
def process_documents(files):
    for file_path in files:
        content = read_document(file_path)
        if len(content) > CONFIG.max_chars:
            chunks = create_chunks(content, CONFIG.max_chars)
            # Process each chunk with progress tracking
        else:
            # Direct processing for smaller documents
```

**Features:**
- Automatic chunking for large documents
- Progress bars with timing information
- Memory-efficient processing
- Error handling for unsupported formats

### 4. Citation Verification Integration

```python
def verify_citations(text, verify_flag):
    if verify_flag:
        verification_results = citation_verify.verify_citations(text)
        # Real-time validation against Jade.io database
        # Enhanced error messages for failure types
```

**Verification Modes:**
- **Optional verification**: Via `--verify` flag
- **Pattern validation**: Offline detection of problematic patterns
- **Online validation**: Real-time checks against Australian legal databases
- **Enhanced error reporting**: Specific failure types and actions taken

## Strategic Analysis Framework

### Five-Section Analysis Structure

1. **Case Overview & Position**
   - Strategic strengths and vulnerabilities assessment
   - Client's position relative to opposing party
   - Key factual advantages and disadvantages

2. **Tactical Opportunities**
   - Procedural advantages to exploit
   - Evidence strengths to emphasize
   - Settlement leverage points
   - Opposing party vulnerabilities

3. **Risk Assessment**
   - Litigation exposure and cost considerations
   - Evidence gaps or weaknesses
   - Potential adverse findings
   - Mitigation strategies

4. **Strategic Recommendations**
   - Priority actions and next steps
   - Resource allocation priorities
   - Alternative dispute resolution considerations
   - Recommended litigation approach

5. **Case Management Notes**
   - Key deadlines and milestones
   - Witness considerations and availability
   - Expert evidence requirements
   - Discovery/disclosure strategy

### Implementation Details

```python
def generate_strategic_analysis(documents_content):
    # LLMClientFactory provides configured client
    client = LLMClientFactory.for_command("counselnotes")
    # Uses anthropic/claude-sonnet-4, temp=0.3, top_p=0.7, force_verify=True
    
    # Multi-document synthesis
    if len(documents_content) > 1:
        synthesis_prompt = PROMPTS.get("processing.counselnotes.synthesis")
        # Cross-document analysis for consistent themes
    
    # Strategic analysis with advocate perspective
    analysis_prompt = PROMPTS.get("processing.counselnotes.strategic_analysis")
    
    return client.complete(
        prompt=analysis_prompt,
        context=documents_content
        # Configuration parameters handled by LLMClientFactory
    )
```

## JSON Extraction Modes

### Extraction Mode Implementation

```python
def generate_extraction(content, mode):
    extraction_templates = {
        "all": "counselnotes_extract_all",
        "citations": "counselnotes_extract_citations", 
        "principles": "counselnotes_extract_principles",
        "checklist": "counselnotes_extract_checklist"
    }
    
    prompt_key = extraction_templates[mode]
    prompt = PROMPTS.get(prompt_key)
    
    # JSON-first extraction following June 2025 patterns
    response = client.complete(prompt, content)
    
    # Parse and validate JSON structure
    try:
        parsed_json = json.loads(response)
        return json.dumps(parsed_json, indent=2)
    except json.JSONDecodeError:
        # Fallback handling for malformed JSON
        return create_structured_fallback(response)
```

### Extract Mode Specifications

#### `--extract all`
```json
{
  "strategic_summary": "Brief overview of case position",
  "key_citations": ["Case v Name [2023] HCA 1"],
  "legal_principles": [
    {
      "principle": "Legal rule or concept",
      "authority": "Supporting case or statute"
    }
  ],
  "tactical_checklist": ["Actionable item"],
  "risk_assessment": "Assessment of litigation risks",
  "recommendations": ["Strategic recommendation"]
}
```

#### `--extract citations`
```json
{
  "citations": [
    "Commonwealth v Tasmania [1983] HCA 21",
    "Contract Law Act 1987 (NSW) s 42"
  ]
}
```

#### `--extract principles`
```json
{
  "principles": [
    {
      "principle": "Good faith in contract performance",
      "authority": "Renard Constructions v Minister [1992] HCA 19"
    }
  ]
}
```

#### `--extract checklist`
```json
{
  "checklist": [
    "Verify witness statement consistency",
    "Prepare discovery plan within 14 days",
    "Assess summary judgment prospects"
  ]
}
```

## Multi-Document Processing

### Cross-Document Synthesis

```python
def process_multiple_documents(files):
    contents = []
    for file_path in files:
        content = read_document(file_path)
        contents.append({
            'filename': file_path.name,
            'content': content,
            'length': len(content)
        })
    
    # Cross-document synthesis analysis
    synthesis_analysis = generate_synthesis(contents)
    
    # Combined strategic analysis
    combined_content = merge_documents(contents)
    strategic_analysis = generate_strategic_analysis(combined_content)
    
    return {
        'synthesis': synthesis_analysis,
        'strategic_analysis': strategic_analysis
    }
```

### Synthesis Features

- **Common Theme Identification**: Identifies consistent issues across documents
- **Contradiction Detection**: Highlights conflicting information between documents
- **Gap Analysis**: Identifies missing information or evidence
- **Unified Recommendations**: Provides strategic advice based on complete picture

## Error Handling and Validation

### Document Processing Errors

```python
def safe_document_processing(file_path):
    try:
        content = read_document(file_path)
        if not content.strip():
            raise ValueError(f"Document {file_path} appears to be empty")
        return content
    except Exception as e:
        click.echo(f"Error processing {file_path}: {str(e)}", err=True)
        return None
```

### JSON Validation

```python
def validate_extraction(json_text, mode):
    try:
        data = json.loads(json_text)
        required_keys = get_required_keys_for_mode(mode)
        
        for key in required_keys:
            if key not in data:
                raise ValidationError(f"Missing required key: {key}")
        
        return data
    except json.JSONDecodeError as e:
        # Provide structured fallback
        return create_fallback_structure(json_text, mode)
```

### Citation Verification Error Handling

```python
def handle_citation_verification(text, verify_enabled):
    if not verify_enabled:
        return text
    
    try:
        verification_results = citation_verify.verify_citations(text)
        
        if verification_results.has_issues:
            # Append detailed warnings about citation issues
            warnings = format_citation_warnings(verification_results)
            return f"{text}\n\n{warnings}"
        
        return text
    except Exception as e:
        # Log error but don't fail the command
        logger.warning(f"Citation verification failed: {e}")
        return text
```

## Performance Optimizations

### Chunking Strategy

```python
def create_optimized_chunks(content, max_chars):
    # Strategic chunking that preserves document structure
    paragraphs = content.split('\n\n')
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        if len(current_chunk + paragraph) <= max_chars:
            current_chunk += paragraph + '\n\n'
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = paragraph + '\n\n'
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks
```

### Progress Tracking

```python
@timed
def counselnotes():
    # Automatic timing via decorator
    
    with click.progressbar(files, label='Processing documents') as bar:
        for file_path in bar:
            process_single_document(file_path)
    
    # Real-time progress indicators during LLM processing
    with progress_indicator("Generating strategic analysis"):
        analysis = generate_strategic_analysis(content)
```

## Integration with LitAssist Ecosystem

### Command Registration

```python
# In litassist/commands/__init__.py
from .counselnotes import counselnotes

def get_commands():
    return {
        'counselnotes': counselnotes,
        # ... other commands
    }
```

### Output File Management

```python
def save_counselnotes_output(content, file_prefix, extraction_mode=None):
    if extraction_mode:
        filename = f"counselnotes_{extraction_mode}_{timestamp}.json"
    else:
        filename = f"counselnotes_strategic_{timestamp}.txt"
    
    output_path = save_command_output(content, filename)
    return output_path
```

### Audit Trail Integration

```python
def create_audit_log(command_details):
    log_data = {
        'command': 'counselnotes',
        'files_processed': command_details.files,
        'extraction_mode': command_details.extraction_mode,
        'verification_enabled': command_details.verify,
        'processing_time': command_details.duration,
        'output_files': command_details.outputs
    }
    
    save_log(log_data, f"counselnotes_{timestamp}")
```

## Testing Strategy

### Unit Test Coverage

```python
# tests/unit/test_counselnotes_basic.py
class TestCounselNotesBasic:
    def test_strategic_analysis_mode(self):
        # Test basic strategic analysis functionality
        
    def test_extraction_modes(self):
        # Test all four extraction modes
        
    def test_citation_verification(self):
        # Test citation verification integration
        
    def test_multi_document_processing(self):
        # Test cross-document synthesis
        
    def test_error_handling(self):
        # Test various error scenarios
```

### Integration Test Patterns

```bash
# test-scripts/test_counselnotes.sh
#!/bin/bash

# Test strategic analysis
litassist counselnotes examples/test_document.pdf

# Test extraction modes
litassist counselnotes --extract all examples/test_document.pdf
litassist counselnotes --extract citations examples/test_document.pdf

# Test verification
litassist counselnotes --verify examples/test_document.pdf

# Test multi-document processing
litassist counselnotes doc1.pdf doc2.pdf doc3.pdf
```

## Configuration and Customization

### Model Configuration

```yaml
# config.yaml
llm:
  models:
    counselnotes: "anthropic/claude-opus-4"
    
  parameters:
    counselnotes:
      temperature: 0.3
      max_tokens: 4096
      top_p: 0.8
```

### Prompt Customization

```yaml
# litassist/prompts/processing.yaml
counselnotes_strategic_analysis: |
  You are an experienced barrister reviewing legal documents from an advocate's perspective.
  
  Analyze the following document(s) strategically, focusing on:
  1. Case Overview & Position
  2. Tactical Opportunities  
  3. Risk Assessment
  4. Strategic Recommendations
  5. Case Management Notes
  
  Documents to analyze:
  {content}
```

## Future Enhancement Opportunities

### Planned Features

1. **Template Integration**: Pre-defined templates for different practice areas
2. **Collaborative Analysis**: Multi-user strategic planning support
3. **Integration APIs**: Direct integration with case management systems
4. **Advanced Filtering**: Document section-specific analysis
5. **Export Formats**: Direct export to Word, PDF, case management systems

### Architectural Considerations

1. **Scalability**: Async processing for large document sets
2. **Security**: Enhanced encryption for sensitive legal documents
3. **Compliance**: Audit trail enhancements for regulatory requirements
4. **Performance**: Caching strategies for repeated analysis
5. **Extensibility**: Plugin architecture for custom analysis types

## Maintenance and Monitoring

### Performance Metrics

- Document processing time per page
- LLM response time and token usage
- Citation verification success rates
- Error rates by document type
- User satisfaction with strategic analysis quality

### Monitoring Integration

```python
def track_performance_metrics(command_execution):
    metrics = {
        'documents_processed': len(command_execution.files),
        'total_processing_time': command_execution.duration,
        'extraction_mode': command_execution.extraction_mode,
        'verification_enabled': command_execution.verify,
        'token_usage': command_execution.token_usage,
        'citation_verification_results': command_execution.citation_results
    }
    
    # Send to monitoring system
    monitor.track('counselnotes_execution', metrics)
```

This implementation follows LitAssist's established patterns while providing unique strategic analysis capabilities specifically designed for litigation support workflows in Australian legal practice.
