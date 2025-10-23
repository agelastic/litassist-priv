# LitAssist Logging Infrastructure Documentation

**Last Updated**: October 23, 2025
**Status**: Current and Accurate

## Overview

The litassist codebase implements a comprehensive structured logging system using the `log_task_event` function to track all stages of command execution, including file I/O, LLM interactions, and processing stages. This provides complete visibility into command execution for debugging, auditing, and performance monitoring.

**Location**: `litassist/logging_utils.py:606`
**Usage**: 178 occurrences across commands (October 2025)

## Core Components

### 1. log_task_event Function

The central logging function that records structured events:

```python
log_task_event(
    command: str,                        # The command name (e.g., "draft", "verify")
    stage: str,                          # The execution stage (e.g., "init", "processing")
    event: str,                          # The event type (e.g., "start", "end", "llm_call")
    message: str = "",                   # Human-readable description
    details: Optional[Dict[str, Any]] = None  # Optional details (model info, counts, etc.)
)
```

**Note**: The parameter is called `details` (not `metadata`) in the actual implementation.

### 2. Standard Event Patterns

All commands follow these consistent patterns:

#### Command Lifecycle
- `init/start` - Command begins execution
- `init/end` - Command completes execution

#### File Operations
- `reading/start` - Beginning file read
- `reading/end` - File read complete with size info
- `reference/processed` - Reference files processed

#### LLM Interactions
- `{stage}/llm_call` - Before sending prompt to LLM
- `{stage}/llm_response` - After receiving LLM response

#### Processing Stages
- `{stage}/start` - Stage begins
- `{stage}/end` - Stage completes

### 3. Error Handling

All logging calls are wrapped in try/except blocks to prevent logging failures from disrupting command execution:

```python
try:
    log_task_event(
        "command_name",
        "stage",
        "event",
        "message",
        {"key": "value"}
    )
except Exception:
    pass
```

## Command-Specific Implementations

### 1. Simple Commands (extractfacts, counselnotes)

Basic linear flow with clear stages:

```
init/start
├── reading/start
├── reading/end
├── extraction/start
├── extraction/llm_call
├── extraction/llm_response
├── extraction/end
├── verification/start
├── verification/end
└── init/end
```

### 2. Multi-Stage Commands (verify)

Commands with multiple optional verification stages:

```
init/start
├── reading/start
├── reading/end
├── citations/start (if --citations)
│   ├── citations/fetching_start
│   ├── citations/fetching_end
│   └── citations/end
├── reasoning/start (if --reasoning)
│   ├── reasoning/llm_call
│   ├── reasoning/llm_response
│   └── reasoning/end
├── soundness/start (if --soundness)
│   ├── soundness/llm_call
│   ├── soundness/llm_response
│   └── soundness/end
├── cove/start (if --cove)
│   └── cove/end
└── init/end
```

### 3. Branching Commands (caseplan)

Commands with different execution modes:

```
init/start
├── reading/start
├── reading/end
├── [Budget Assessment Mode]
│   ├── assessment/start
│   ├── assessment/llm_call
│   ├── assessment/llm_response
│   └── assessment/end
├── [Full Plan Mode]
│   ├── plan/start
│   ├── plan/llm_call
│   ├── plan/llm_response
│   ├── plan/commands_extracted
│   └── plan/end
└── init/end
```

### 4. Iterative Commands (digest)

Commands processing multiple files with consolidation:

```
init/start
├── [For each file]
│   ├── file_processing/start
│   ├── file_processing/chunked
│   ├── [Single chunk]
│   │   ├── single_chunk/start
│   │   ├── processing/llm_call
│   │   ├── processing/llm_response
│   │   └── single_chunk/end
│   ├── [Multiple chunks]
│   │   ├── multi_chunk/start
│   │   ├── [For each chunk]
│   │   │   ├── chunk_processing/llm_call
│   │   │   └── chunk_processing/llm_response
│   │   ├── multi_chunk/end
│   │   ├── consolidation/start
│   │   ├── consolidation/llm_call
│   │   ├── consolidation/llm_response
│   │   └── consolidation/end
│   └── file_processing/end
├── cross_file/start (if multiple files)
├── cross_file/end
└── init/end
```

### 5. Modular Commands (lookup, brainstorm)

Commands with processing distributed across multiple modules:

**lookup/**
- `__init__.py`: Command orchestration logging
- `search.py`: CSE search logging
- `processors.py`: LLM processing and truncation logging

**brainstorm/**
- `core.py`: Main workflow logging
- `orthodox_generator.py`: Orthodox strategy generation logging
- `unorthodox_generator.py`: Unorthodox strategy generation logging

### 6. RAG Pipeline Commands (draft)

Commands with specialized pipeline stages:

```
init/start
├── reading/start
├── reading/end
├── [If using RAG]
│   ├── indexing/start
│   ├── embedding/start
│   ├── embedding/end
│   ├── pinecone/start
│   ├── pinecone/end
│   ├── retrieval/start
│   ├── retrieval/end
│   └── indexing/end
├── generation/llm_call
├── generation/llm_response
├── verification/start
├── verification/end
├── hallucination/start
├── hallucination/end
└── init/end
```

## Details (Metadata) Standards

### Model Information
Always include model info for LLM operations:
```python
{"model": client.model}
```

### Counts and Metrics
Include relevant counts:
```python
{
    "files": len(files),
    "chunks": chunk_count,
    "tokens": token_count,
    "citations": citation_count
}
```

### Status Information
Include status for conditional operations:
```python
{
    "regenerated": True/False,
    "issues": issue_count,
    "mode": "summary/issues"
}
```

**Parameter Name**: Use `details` (not `metadata`) when calling `log_task_event()`

## Stage Naming Conventions

### Primary Stages
- `init` - Command initialization
- `reading` - File reading operations
- `processing` - Main processing logic
- `generation` - Content generation
- `verification` - Verification passes
- `consolidation` - Combining results

### Sub-stages
- `extraction` - Extracting information
- `analysis` - Analyzing content
- `fetching` - Fetching external data
- `embedding` - Creating embeddings
- `retrieval` - Retrieving from vector stores

### Specialized Stages
- `citations` - Citation verification
- `reasoning` - Reasoning trace generation
- `soundness` - Legal soundness checks
- `cove` - Chain of Verification
- `hallucination` - Hallucination detection
- `truncation` - Document truncation for token limits

## Usage Examples

### Basic Command Logging

```python
# Command start
try:
    log_task_event(
        "extractfacts",
        "init",
        "start",
        "Starting fact extraction",
        {"model": LLMClientFactory.get_model_for_command("extractfacts")}
    )
except Exception:
    pass

# File reading
try:
    log_task_event(
        "extractfacts",
        "reading",
        "start",
        "Reading input documents"
    )
except Exception:
    pass

content = read_document(file_path)

try:
    log_task_event(
        "extractfacts",
        "reading",
        "end",
        f"Read {len(file)} document(s)"
    )
except Exception:
    pass
```

### LLM Call Logging

```python
# Before LLM call
try:
    log_task_event(
        command="draft",
        stage="generation",
        event="llm_call",
        message="Sending draft generation prompt to LLM",
        details={"model": client.model}
    )
except Exception:
    pass

response, usage = client.complete(messages)

# After LLM response
try:
    log_task_event(
        command="draft",
        stage="generation",
        event="llm_response",
        message="Draft LLM response received",
        details={"model": client.model}
    )
except Exception:
    pass
```

### Conditional Stage Logging

```python
if citations:
    try:
        log_task_event(
            "verify",
            "citations",
            "start",
            "Starting citation verification"
        )
    except Exception:
        pass
    
    # ... citation verification logic ...
    
    try:
        log_task_event(
            "verify",
            "citations",
            "end",
            f"Citation verification complete - {len(verified)} verified"
        )
    except Exception:
        pass
```

### Loop Processing Logging

```python
for i, chunk in enumerate(chunks, 1):
    try:
        log_task_event(
            command="digest",
            stage="chunk_processing",
            event="llm_call",
            message=f"Processing chunk {i}/{len(chunks)}",
            details={"model": client.model, "chunk": i, "total": len(chunks)}
        )
    except Exception:
        pass

    # ... process chunk ...
```

## Benefits

### 1. Debugging
- Complete execution trace for every command
- Clear visibility into which stage failed
- Metadata helps reproduce issues

### 2. Performance Monitoring
- Track time between start/end events
- Monitor LLM call frequency
- Identify bottlenecks in processing

### 3. Auditing
- Complete record of all LLM interactions
- Track model usage and costs
- Compliance with legal requirements

### 4. User Transparency
- Users can see exactly what the system is doing
- Clear progress indication for long-running commands
- Helpful for understanding complex workflows

## Implementation Checklist

When adding logging to a new command:

- [ ] Add `log_task_event` to imports
- [ ] Add init/start at command beginning
- [ ] Add init/end at command completion
- [ ] Log all file reading operations
- [ ] Log all LLM calls and responses with model info
- [ ] Log major processing stages with start/end
- [ ] Include relevant metadata (counts, status, etc.)
- [ ] Wrap all logging in try/except blocks
- [ ] Use consistent stage naming
- [ ] Test that logging doesn't break command execution

## Command Coverage Status

All commands have comprehensive logging:

| Command | Status | Events | Key Stages |
|---------|--------|--------|------------|
| strategy | ✅ Complete | 14 | init, reading, generation, verification |
| brainstorm | ✅ Complete | 20+ | init, reading, orthodox, unorthodox, consolidation |
| barbrief | ✅ Complete | 12 | init, reading, generation, verification |
| extractfacts | ✅ Complete | 10 | init, reading, extraction, consolidation |
| counselnotes | ✅ Complete | 10 | init, reading, extraction/analysis, consolidation |
| draft | ✅ Complete | 15 | init, reading, indexing, RAG pipeline, generation |
| verify-cove | ✅ Complete | 8 | init, reading, reference, cove pipeline |
| verify | ✅ Complete | 18 | init, citations, reasoning, soundness, cove |
| lookup | ✅ Complete | 15 | init, search, CSE, fetching, generation |
| digest | ✅ Complete | 21 | init, file processing, chunks, consolidation |
| caseplan | ✅ Complete | 12 | init, assessment/plan modes, command extraction |

## Future Enhancements

Potential improvements to the logging infrastructure:

1. **Structured Output Format**: Export logs in JSON/CSV for analysis
2. **Log Levels**: Add DEBUG/INFO/WARNING/ERROR levels
3. **Performance Metrics**: Auto-calculate duration between start/end
4. **Cost Tracking**: Calculate API costs from token usage
5. **Visualization**: Generate execution flow diagrams from logs
6. **Alerting**: Trigger alerts on specific error patterns
7. **Log Aggregation**: Centralized logging service integration
8. **User Preferences**: Allow users to control logging verbosity

## Related Documentation

- **LLM_MODEL_STRATEGY.md** - LLM configuration and usage patterns
- **ARCHITECTURE_ANALYSIS_2025.md** - Overall architecture including logging approach
- **CLAUDE.md** - Development guidelines including logging requirements

## Conclusion

The comprehensive logging infrastructure provides complete visibility into litassist command execution, supporting debugging, auditing, and performance monitoring while maintaining clean error handling that doesn't disrupt command execution. The consistent patterns and naming conventions make the logs easy to understand and analyze.

**Current Status** (October 2025):
- ✅ All commands have comprehensive logging (178 total log_task_event calls)
- ✅ Consistent patterns across all command types
- ✅ Error handling prevents logging failures from breaking commands
- ✅ Metadata/details included for all LLM calls

**Document Status**: Current and accurate as of October 23, 2025

---

**Document Owner**: Development Team
**Created**: ~June-August 2025
**Last Reviewed**: October 23, 2025
**Status**: Current - matches actual implementation