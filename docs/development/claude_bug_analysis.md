# LitAssist Bug Analysis Report

## Critical Bugs (High Priority)

### 1. Citation Cache Memory Leak
**Location**: `litassist/citation_verify.py`
**Issue**: Global `_citation_cache` has no size limit or eviction mechanism
**Impact**: Memory exhaustion during long-running sessions
**Fix**: Implement LRU cache with max size:
```python
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size=1000):
        self.cache = OrderedDict()
        self.max_size = max_size
    
    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
        return self.cache.get(key)
    
    def set(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
```

### 2. No API Rate Limiting
**Location**: Throughout LLM client code
**Issue**: No rate limiting or exponential backoff for API calls
**Impact**: API rate limit errors causing cascading failures
**Fix**: Add tenacity retry with exponential backoff:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3), 
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type((RateLimitError, APIConnectionError))
)
def api_call_with_retry():
    # API call logic
```

### 3. Missing Circuit Breaker
**Location**: `TODO.md:41` - Not implemented
**Issue**: Failed APIs retry indefinitely
**Impact**: Cost overruns and service degradation
**Fix**: Implement circuit breaker pattern:
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
            else:
                raise CircuitBreakerOpenError()
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
            raise
```

### 4. No API Call Timeouts
**Location**: Various API calls
**Issue**: API calls can hang indefinitely
**Impact**: Application hangs on network issues
**Fix**: Add timeouts to all requests:
```python
# In llm.py
response = openai.ChatCompletion.create(
    model=model_name,
    messages=messages,
    timeout=30,  # 30 second timeout
    **params
)

# For requests library calls
response = requests.post(url, timeout=30)
```

## Medium Priority Bugs

### 5. Bare Exception Handlers
**Examples**: 
- `citation_verify.py:474`: `except Exception: pass`
- `prompts.py:190`: `except KeyError: pass`
**Fix**: Add proper logging:
```python
import logging
logger = logging.getLogger(__name__)

try:
    # code
except Exception as e:
    logger.error(f"Failed to verify citation: {e}", exc_info=True)
    # Handle appropriately
```

### 6. Missing o3-pro Parameter Validation
**Location**: `litassist/llm.py`
**Issue**: `reasoning_effort` parameter has no validation
**Fix**: Add validation in get_model_parameters:
```python
if model_family == "openai_reasoning" and "reasoning_effort" in params:
    if params["reasoning_effort"] not in ["low", "medium", "high"]:
        raise ValueError(f"Invalid reasoning_effort: {params['reasoning_effort']}")
```

### 7. Memory Issues with Large Files
**Location**: `litassist/utils.py:630`
**Issue**: Catches MemoryError after loading entire file
**Fix**: Stream large files:
```python
def process_file_stream(filepath, chunk_size=1024*1024):
    with open(filepath, 'r') as f:
        while chunk := f.read(chunk_size):
            yield chunk
```

## Low Priority Bugs

### 8. Thread Safety in Progress Indicator
**Location**: `litassist/utils.py:687-696`
**Fix**: Add exception handling:
```python
try:
    progress_thread.join(timeout=1)
except Exception as e:
    logger.warning(f"Progress thread error: {e}")
```

### 9. Missing Input Validation
**Location**: Command entry points
**Fix**: Validate files exist:
```python
if not os.path.exists(file_path):
    raise click.ClickException(f"File not found: {file_path}")
```

## Summary

The most critical issues are:
1. **Memory leak** in citation cache (unbounded growth)
2. **No rate limiting** for API calls (service disruption risk)
3. **Missing circuit breaker** (cost/reliability risk)
4. **No timeouts** on API calls (hanging risk)

These should be addressed immediately to improve system reliability and prevent production issues.