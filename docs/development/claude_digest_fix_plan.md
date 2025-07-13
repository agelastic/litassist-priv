# Fix Plan for Digest Command Issues

## Problem Summary

The `digest` command is experiencing critical issues with large files:
1. **Timeouts**: Even with 150K chunks, 2M files are timing out
2. **No Partial Saves**: Interrupt handling (Ctrl+C) doesn't save partial results
3. **Performance**: Too many chunks being created, causing excessive API calls

## Root Cause Analysis

### 1. Chunk Size Calculation Issue
- `CONFIG.max_chars` from config.yaml is 300K
- Model chunk limit for Claude is set to 150K
- Effective chunk size = min(300K, 150K) = 150K
- This creates ~14 chunks for a 2M file, leading to timeouts

### 2. Signal Handler Issues
- Signal handler is registered but `partial_save_data` may not be populated correctly
- Emergency save function may not be triggered during subprocess execution
- No debug logging to verify handler execution

### 3. Performance Bottlenecks
- Each chunk requires an LLM API call
- Final consolidation requires processing all chunk results
- No progress feedback during long operations

## Comprehensive Fix Plan

### 1. **Increase Effective Chunk Size to 300K**
```python
# Update MODEL_CHUNK_LIMITS in digest.py
MODEL_CHUNK_LIMITS = {
    "google": 30000,          # Conservative for Gemini
    "anthropic": 300000,      # Claude can handle 300K+ easily
    "openai": 100000,         # GPT-4 limit
    "x-ai": 100000,           # Grok limit
}
```
**Impact**: Reduces chunks for 2M file from 14 to 7 (50% reduction)

### 2. **Fix Interrupt Handling**
```python
# Add debug logging to signal handler
def signal_handler(signum, frame):
    print(f"\n[DEBUG] Signal {signum} received", file=sys.stderr)
    print(f"[DEBUG] Partial data chunks: {len(partial_save_data['chunks'])}", file=sys.stderr)
    emergency_save()
    sys.exit(1)

# Ensure partial_save_data is populated early
partial_save_data = {
    'chunks': [],
    'metadata': {'mode': mode, 'hint': hint, 'files': list(file)}
}
```

### 3. **Add Progress Feedback**
```python
# Add time estimation
total_chunks = len(chunks)
estimated_time = total_chunks * 15  # ~15 seconds per chunk
click.echo(info_message(f"Processing {total_chunks} chunks (estimated {estimated_time//60}m {estimated_time%60}s)"))

# Add progress counter
with click.progressbar(chunks, label=f"Analyzing {total_chunks} sections") as chunks_bar:
    for idx, chunk in enumerate(chunks_bar, start=1):
        # Show periodic updates
        if idx % 5 == 0:
            click.echo(f"\n{info_message(f'Processed {idx}/{total_chunks} chunks...')}")
```

### 4. **Optimize Consolidation for Large Files**
```python
# Hierarchical consolidation for many chunks
if len(chunk_analyses) > 10:
    # Process in batches of 5
    batch_size = 5
    batched_analyses = []
    
    for i in range(0, len(chunk_analyses), batch_size):
        batch = chunk_analyses[i:i+batch_size]
        # Consolidate each batch
        batch_content = "\n\n".join(batch)
        batch_result = consolidate_batch(batch_content)
        batched_analyses.append(batch_result)
    
    # Final consolidation of batches
    final_content = consolidate_final(batched_analyses)
```

### 5. **Add Configuration Options**
```python
@click.option("--chunk-size", type=int, help="Override default chunk size")
@click.option("--timeout", type=int, default=300, help="Timeout in seconds (default: 300)")
@click.option("--skip-consolidation", is_flag=True, help="Skip consolidation for very large files")
def digest(file, mode, hint, chunk_size, timeout, skip_consolidation):
    # Use custom chunk size if provided
    if chunk_size:
        effective_chunk_size = chunk_size
    
    # Apply timeout to LLM calls
    client.timeout = timeout
```

### 6. **Emergency Save Improvements**
```python
def emergency_save():
    """Enhanced emergency save with better error handling"""
    try:
        # Save whatever we have, even if incomplete
        if partial_save_data.get('chunks') or partial_save_data.get('metadata'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Build content from available data
            content_parts = []
            if partial_save_data.get('metadata'):
                content_parts.append(f"Metadata: {partial_save_data['metadata']}")
            
            if partial_save_data.get('chunks'):
                content_parts.append(f"\nProcessed {len(partial_save_data['chunks'])} chunks:")
                content_parts.extend(partial_save_data['chunks'])
            else:
                content_parts.append("\n[No chunks processed yet]")
            
            content = "\n\n".join(content_parts)
            content += "\n\n[INCOMPLETE - Process interrupted]"
            
            # Save with timestamp to avoid conflicts
            emergency_file = f"outputs/digest_{mode}_partial_{timestamp}.txt"
            with open(emergency_file, 'w') as f:
                f.write(content)
            
            click.echo(warning_message(f"\nPartial results saved to: {emergency_file}"))
    except Exception as e:
        # Last resort - print to stderr
        print(f"\n[EMERGENCY] Could not save partial results: {e}", file=sys.stderr)
        if partial_save_data.get('chunks'):
            print(f"[EMERGENCY] Processed {len(partial_save_data['chunks'])} chunks", file=sys.stderr)
```

## Implementation Priority

1. **High Priority** (Immediate fixes):
   - Increase chunk size to 300K for Claude
   - Fix emergency save to be more robust
   - Add debug logging for signal handlers

2. **Medium Priority** (User experience):
   - Add progress feedback and time estimates
   - Implement hierarchical consolidation
   - Add chunk-size override option

3. **Low Priority** (Nice to have):
   - Add timeout configuration
   - Add skip-consolidation option
   - Optimize batch processing

## Testing Plan

1. Test with files of various sizes:
   - 100K (should be 1 chunk)
   - 500K (should be 2 chunks)
   - 1M (should be 4 chunks)
   - 2M (should be 7 chunks)

2. Test interrupt handling:
   - Start processing large file
   - Press Ctrl+C after a few chunks
   - Verify partial results are saved

3. Test performance:
   - Measure time for 2M file before and after changes
   - Should see ~50% reduction in processing time

## Expected Outcomes

- **Reduced timeouts**: 50% fewer chunks means 50% faster processing
- **Reliable saves**: Partial results always saved on interrupt
- **Better UX**: Clear progress indicators and time estimates
- **Flexibility**: Users can override chunk size for their needs
- **Robustness**: Better error handling and recovery