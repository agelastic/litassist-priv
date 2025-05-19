# Test Improvement Roadmap

This document tracks the test failures and provides a roadmap for fixing them.

## Current Status

- ✅ Basic test infrastructure is working
- ✅ CI/CD pipeline passes with basic tests
- ⚠️ Many unit tests need fixing due to:
  - File path issues in CLI tests
  - Mock configuration issues
  - Function signature mismatches
  - Missing imports

## Test Categories

### 1. Working Tests
- `test_basic.py` - All passing ✅

### 2. Command Tests (Need Fixing)
- `test_brainstorm.py` - File path issues
- `test_extractfacts.py` - File path issues  
- `test_strategy.py` - Mock issues

### 3. Module Tests (Need Fixing)
- `test_llm.py` - Mock configuration issues
- `test_retriever.py` - Missing function issues
- `test_utils.py` - Various issues

## Fix Priority

1. **High Priority** - Core functionality tests
   - Fix file path issues in command tests
   - Fix mock configuration for LLM tests
   - Fix function signatures in utils tests

2. **Medium Priority** - Integration tests
   - Add proper mocking for external services
   - Fix retriever tests
   - Add error handling tests

3. **Low Priority** - Edge cases
   - Performance tests
   - Stress tests
   - UI/formatting tests

## Implementation Plan

### Phase 1: Fix Critical Tests (Week 1)
- [ ] Fix all file path issues using `isolated_filesystem()`
- [ ] Update mock configurations to match actual code
- [ ] Fix function signatures and imports

### Phase 2: Improve Coverage (Week 2)
- [ ] Add missing test cases
- [ ] Improve mock quality
- [ ] Add integration test suite

### Phase 3: Enable Full CI/CD (Week 3)
- [ ] Remove `continue-on-error` from workflow
- [ ] Enable coverage reporting
- [ ] Add test quality metrics

## Known Issues

1. **File Path Problems**
   - CLI tests fail because files don't exist
   - Solution: Use `runner.isolated_filesystem()`

2. **Mock CONFIG Issues**
   - Some tests expect attributes that don't exist
   - Solution: Update mock to match actual CONFIG

3. **Import Issues**
   - Some modules not properly mocked
   - Solution: Mock at correct level

4. **Function Signatures**
   - Test calls don't match actual functions
   - Solution: Review and update all calls

## Next Steps

1. Start with command tests (highest value)
2. Fix one test file at a time
3. Run locally before pushing
4. Update this document as tests are fixed