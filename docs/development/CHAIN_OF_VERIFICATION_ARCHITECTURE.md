# Chain of Verification Architecture for LitAssist

## Executive Summary
A streamlined Chain of Verification approach that builds upon existing components without deprecation or migration complexity. This architecture creates a clean, modular verification pipeline using the current codebase as foundation.

## Current Architecture Assessment
- **Pattern Validation**: `citation_patterns.py` - Offline hallucination detection
- **Database Verification**: `citation_verify.py` - Real-time Jade.io/Google CSE verification  
- **LLM Integration**: `llm.py` - Integrated verification in LLMClient
- **Command Handling**: Scattered verification logic across commands

## Proposed Architecture: Verification Chain Pattern

### Core Design Philosophy
**Build upon existing components** rather than replace them. Create a thin orchestration layer that coordinates existing verification capabilities.

### Directory Structure (Minimal Addition)
```
litassist/
├── verification/
│   ├── __init__.py
│   ├── chain.py              # 50-line orchestrator
│   ├── stages.py             # Thin wrappers around existing modules
│   └── config.py             # Command-specific settings
```

### Implementation Strategy: Single Commit Approach

#### 1. Create Verification Chain (1 file, 50 lines)
```python
# litassist/verification/chain.py
class VerificationChain:
    def __init__(self, stages):
        self.stages = stages
    
    def verify(self, content, context):
        for stage in self.stages:
            result = stage.process(content, context)
            if result.should_stop:
                return result
        return VerificationResult.success(content)
```

#### 2. Stage Wrappers (1 file, 100 lines)
```python
# litassist/verification/stages.py
from litassist.citation_patterns import validate_citation_patterns
from litassist.citation_verify import verify_all_citations

class PatternStage:
    def process(self, content, context):
        issues = validate_citation_patterns(content, enable_online=False)
        return StageResult(issues)

class DatabaseStage:
    def process(self, content, context):
        verified, unverified = verify_all_citations(content)
        return StageResult(unverified)
```

#### 3. Configuration Layer (1 file, 30 lines)
```python
# litassist/verification/config.py
COMMAND_CONFIGS = {
    'extractfacts': {'strict': True, 'stages': ['pattern', 'database', 'llm']},
    'strategy': {'strict': True, 'stages': ['pattern', 'database', 'llm']},
    'brainstorm': {'strict': False, 'stages': ['pattern', 'database']},
    'lookup': {'strict': False, 'stages': ['pattern', 'database']},
    'draft': {'strict': True, 'stages': ['pattern', 'database', 'llm']},
}
```

### Integration with Existing LLMClient

#### Minimal Refactoring Required
```python
# In llm.py - add 3 lines
from litassist.verification.chain import VerificationChain
from litassist.verification.config import get_chain_for_command

# In LLMClient.complete() - add 1 line
verification_chain = get_chain_for_command(self.command_context)
```

### Verification Flow Examples

#### High-Risk Commands (extractfacts, strategy)
```
Pattern Validation → Database Verification → LLM Self-Critique
```

#### Medium-Risk Commands (draft, barbrief)  
```
Pattern Validation → Database Verification
```

#### Low-Risk Commands (lookup, digest)
```
Pattern Validation → Database Verification (Warning Mode)
```

### Configuration by Command

| Command | Strict Mode | Stages | Behavior |
|---------|-------------|--------|----------|
| extractfacts | True | Pattern + Database + LLM | Block on failure |
| strategy | True | Pattern + Database + LLM | Block on failure |
| brainstorm | False | Pattern + Database | Continue with warnings |
| lookup | False | Pattern + Database | Continue with warnings |
| draft | True | Pattern + Database + LLM | Block on failure |
| barbrief | True | Pattern + Database + LLM | Block on failure |
| caseplan | False | Pattern + Database | Continue with warnings |
| digest | False | Pattern + Database | Continue with warnings |

### Implementation Checklist

#### Files to Create (3 new files)
- [ ] `litassist/verification/__init__.py` (empty)
- [ ] `litassist/verification/chain.py` (50 lines)
- [ ] `litassist/verification/stages.py` (100 lines)
- [ ] `litassist/verification/config.py` (30 lines)

#### Files to Modify (1 file)
- [ ] `litassist/llm.py` (add 4 lines for integration)

#### No Changes Required
- [ ] `citation_patterns.py` (keep as-is)
- [ ] `citation_verify.py` (keep as-is)
- [ ] Individual command files (no changes needed)

### Architecture Benefits

1. **Zero Deprecation**: Existing components remain untouched
2. **Single Commit**: Entire feature in ~200 lines of new code
3. **Backward Compatible**: All existing functionality preserved
4. **Extensible**: Easy to add new stages or sources
5. **Configurable**: Command-specific behavior without code changes

### Usage Example

```python
# In any command
from litassist.verification.chain import VerificationChain
from litassist.verification.config import get_chain_for_command

chain = get_chain_for_command('strategy')
result = chain.verify(content, context={'command': 'strategy'})
```

This creates a clean Chain of Verification that coordinates existing components without any breaking changes or complex migration requirements.
