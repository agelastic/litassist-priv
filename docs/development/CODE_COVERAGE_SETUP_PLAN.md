# Code Coverage Setup Plan for LitAssist

## Current Situation
- No coverage tools currently installed
- `.gitignore` already configured to ignore coverage files (lines 98-102)
- `pytest.ini` exists but doesn't have coverage configuration

## Setting Up Code Coverage

### 1. Install Coverage Tools
```bash
pip install pytest-cov coverage
```

### 2. Update pytest.ini
Add coverage options to the `addopts` section:
```ini
addopts = 
    -v
    --tb=short
    --cov=litassist
    --cov-report=term-missing
    --cov-report=html
    --cov-branch
```

### 3. Create .coveragerc Configuration
Create a `.coveragerc` file in the project root:
```ini
[run]
source = litassist
omit = 
    */tests/*
    */test_*
    */__pycache__/*
    */venv/*
    */.venv/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError
    if __name__ == '__main__':
    if TYPE_CHECKING:
    @abstract
precision = 2
show_missing = True

[html]
directory = htmlcov
```

## Running Coverage Reports

### Basic Coverage Report
```bash
pytest --cov=litassist tests/unit/
```

### Detailed HTML Report
```bash
pytest --cov=litassist --cov-report=html tests/unit/
open htmlcov/index.html  # View in browser
```

### Check Specific File Coverage
```bash
pytest --cov=litassist/llm --cov-report=term-missing tests/unit/test_llm*.py
```

### Find Unreachable Code
```bash
# Run with branch coverage
pytest --cov=litassist --cov-branch --cov-report=term-missing tests/unit/

# Look for lines that show 0% coverage - these are never executed
```

## How This Would Have Helped

With coverage reports, we would have seen:
- Lines 942-943 (the redundant check) showing 0% coverage
- A "branch not taken" indicator on line 942
- Clear evidence that this code path was never executed

## Benefits of Coverage Reports

1. **Identify dead code** - Lines with 0% coverage that aren't error handlers
2. **Find missing tests** - Important logic paths not covered
3. **Track test quality** - Aim for 80%+ coverage on critical modules
4. **Detect redundancies** - Multiple checks for same condition show partial coverage

## Optional: Add to CI/CD
Add to GitHub Actions or other CI:
```yaml
- name: Run tests with coverage
  run: |
    pytest --cov=litassist --cov-report=xml tests/unit/
    
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
```

This would automatically flag PRs that reduce coverage or have unreachable code.

## Implementation Priority

**Low Priority** - The codebase already has good test coverage and the redundant code issue was caught by code review. Coverage reports would be a nice-to-have for future development but aren't critical.

## Notes

- The redundant code on lines 942-943 of llm.py was already removed
- Existing tests are comprehensive but all use non-empty choices arrays
- Coverage reports would help identify similar unreachable code patterns