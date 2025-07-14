# Glob Pattern Unification Plan for LitAssist

## Current State Analysis

### Temporary Help System (July 2025)
- **Status**: Temporary glob help addon (`litassist/prompts/glob_help_addon.yaml`) provides user guidance
- **Note**: Must be removed before implementing full unification to avoid confusion

### Commands WITH Glob Support (2 commands)
1. **brainstorm.py**
   - `--facts`: multiple=True, type=click.Path(), callback=expand_glob_patterns
   - `--research`: multiple=True, type=click.Path(), callback=expand_glob_patterns
   - Has its own `expand_glob_patterns` function (lines 194-222)

2. **barbrief.py**
   - `--strategies`: multiple=True, type=click.Path(), callback=expand_glob_patterns
   - `--research`: multiple=True, type=click.Path(), callback=expand_glob_patterns
   - `--documents`: multiple=True, type=click.Path(), callback=expand_glob_patterns
   - Has duplicate `expand_glob_patterns` function (lines 97-125)

### Commands WITHOUT Glob Support (5 commands)
1. **extractfacts.py**
   - Uses: `nargs=-1, type=click.Path(exists=True)`
   - No glob expansion - relies on shell

2. **digest.py**
   - Uses: `nargs=-1, type=click.Path(exists=True)`
   - No glob expansion - relies on shell

3. **draft.py**
   - Uses: `nargs=-1, type=click.Path(exists=True)`
   - No glob expansion - relies on shell

4. **counselnotes.py**
   - Uses: `nargs=-1, type=click.Path(exists=True)`
   - No glob expansion - relies on shell

5. **strategy.py**
   - `case_facts`: type=click.File("r") - single file only
   - `--strategies`: type=click.Path(exists=True) - single file only
   - No multiple file support at all

## Problems Identified

1. **Inconsistent User Experience**: Some commands support globs, others don't
2. **Code Duplication**: `expand_glob_patterns` duplicated in 2 files
3. **Different Approaches**: 
   - Some use `nargs=-1` (positional arguments)
   - Some use `multiple=True` (options with flags)
   - Some only accept single files
4. **Documentation Confusion**: Case generation plan shows examples that won't work without shell expansion
5. **Quoting Requirements**: Different between commands that expand vs rely on shell

## Proposed Solution

### Phase 1: Centralize Glob Expansion Function
1. Move `expand_glob_patterns` to `litassist/utils.py`
2. Remove duplicate implementations from brainstorm.py and barbrief.py
3. Add comprehensive tests for the function

### Phase 2: Add Glob Support to All Multi-File Commands
1. **extractfacts.py**: Add callback to expand globs
2. **digest.py**: Add callback to expand globs
3. **draft.py**: Add callback to expand globs
4. **counselnotes.py**: Add callback to expand globs

### Phase 3: Enhance Strategy Command
1. Change `--strategies` to support multiple files with glob expansion
2. Keep `case_facts` as single file (positional argument)
3. Update help text to clarify usage

### Phase 4: Standardize Help Text
Add consistent help text pattern:
```
"Path to [description]. Supports glob patterns (e.g., 'outputs/*.txt'). Use quotes to prevent shell expansion."
```

## Implementation Details

### 1. New utils.py Function
```python
def expand_glob_patterns(ctx, param, value):
    """
    Expand glob patterns in file paths for Click callbacks.
    
    This function:
    - Expands glob patterns (*, ?, []) to actual file paths
    - Validates that files exist
    - Removes duplicates while preserving order
    - Provides clear error messages for missing files
    
    Args:
        ctx: Click context
        param: Click parameter
        value: Tuple of paths/patterns from Click
        
    Returns:
        Tuple of expanded, validated file paths
        
    Raises:
        click.BadParameter: If no files match a pattern or file not found
    """
    if not value:
        return value
    
    expanded_paths = []
    for pattern in value:
        # Check if it's a glob pattern (contains *, ?, or [)
        if any(char in pattern for char in ['*', '?', '[']):
            # Expand the glob pattern
            matches = glob.glob(pattern)
            if not matches:
                raise click.BadParameter(f"No files matching pattern: {pattern}")
            expanded_paths.extend(matches)
        else:
            # Not a glob pattern, just verify the file exists
            if not os.path.exists(pattern):
                raise click.BadParameter(f"File not found: {pattern}")
            expanded_paths.append(pattern)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_paths = []
    for path in expanded_paths:
        if path not in seen:
            seen.add(path)
            unique_paths.append(path)
    
    return tuple(unique_paths)
```

### 2. Commands to Update

#### extractfacts.py
Change from:
```python
@click.argument("source_files", nargs=-1, type=click.Path(exists=True), required=True)
```
To:
```python
@click.argument("source_files", nargs=-1, type=click.Path(), required=True, callback=expand_glob_patterns)
```

#### digest.py
Change from:
```python
@click.argument("documents", nargs=-1, type=click.Path(exists=True), required=True)
```
To:
```python
@click.argument("documents", nargs=-1, type=click.Path(), required=True, callback=expand_glob_patterns)
```

#### draft.py
Change from:
```python
@click.argument("documents", nargs=-1, type=click.Path(exists=True))
```
To:
```python
@click.argument("documents", nargs=-1, type=click.Path(), callback=expand_glob_patterns)
```

#### counselnotes.py
Change from:
```python
@click.argument("source_files", nargs=-1, type=click.Path(exists=True), required=True)
```
To:
```python
@click.argument("source_files", nargs=-1, type=click.Path(), required=True, callback=expand_glob_patterns)
```

#### strategy.py
Change from:
```python
@click.option(
    "--strategies",
    type=click.Path(exists=True),
    help="Optional: Pre-generated strategies file"
)
```
To:
```python
@click.option(
    "--strategies", 
    multiple=True,
    type=click.Path(),
    callback=expand_glob_patterns,
    help="Optional: Pre-generated strategies files. Supports glob patterns (e.g., 'outputs/brainstorm_*.txt')"
)
```

### 3. Import Updates
All commands will need:
```python
from litassist.utils import expand_glob_patterns
```

And remove local imports of glob if present.

## Benefits

1. **Consistent User Experience**: All commands handle globs the same way
2. **DRY Principle**: Single implementation of glob expansion
3. **Better Error Messages**: Clear feedback when patterns don't match
4. **No Shell Dependency**: Works consistently across different shells
5. **Backwards Compatible**: Existing usage still works

## Migration Guide for Users

### Before (Shell-Dependent)
```bash
# Works in bash/zsh but not in cmd/PowerShell
litassist digest outputs/lookup_*.txt

# Works everywhere but verbose
litassist digest outputs/lookup_gift.txt outputs/lookup_presumption.txt outputs/lookup_trust.txt
```

### After (Consistent Everywhere)
```bash
# Works in all shells with quotes
litassist digest 'outputs/lookup_*.txt'

# Also supports multiple patterns
litassist digest 'outputs/lookup_*gift*.txt' 'outputs/lookup_*trust*.txt'
```

## Testing Requirements

1. Unit tests for `expand_glob_patterns` in test_utils.py
2. Integration tests for each command with glob patterns
3. Test edge cases:
   - No matches for pattern
   - Mixed globs and explicit paths
   - Duplicate file handling
   - Special characters in filenames

## Documentation Updates

1. Update command help text with glob examples
2. Update user guide with glob pattern section
3. Update case generation plan with consistent examples
4. Add troubleshooting section for common glob issues

## Rollout Plan

0. **Phase 0**: Remove temporary help addon (delete `glob_help_addon.yaml`)
1. **Phase 1**: Implement centralized function (low risk)
2. **Phase 2**: Update commands that use nargs=-1 (medium risk)
3. **Phase 3**: Update strategy command (higher risk due to behavior change)
4. **Phase 4**: Documentation and testing
5. **Phase 5**: Deprecation notices if needed

## Estimated Impact

- **Code Changes**: ~200 lines (mostly moving/updating existing code)
- **User Impact**: Positive - more consistent and powerful
- **Breaking Changes**: None - all existing usage continues to work
- **Risk Level**: Low to Medium - mostly enhancing existing functionality
