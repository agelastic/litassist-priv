# Test Status

## Working Tests ✅
- `test_basic.py` - Basic infrastructure tests
- `test_real_functionality.py` - Real function tests

## Broken Tests ❌
- `test_brainstorm.py` - File path issues
- `test_extractfacts.py` - File path issues
- `test_strategy.py` - Mock issues
- `test_llm.py` - Config mock issues
- `test_retriever.py` - Missing functions
- `test_utils.py` - Multiple issues

## Why Tests Are Failing

1. **File Path Issues**: Commands expect files that don't exist
   - Solution: Use `runner.isolated_filesystem()` properly

2. **Mock Issues**: Mocks don't match real implementation
   - Solution: Check actual function signatures

3. **Config Issues**: Tests expect CONFIG attributes that don't exist
   - Solution: Update mock CONFIG in conftest.py

## Fixed Examples

See `test_real_functionality.py` for examples of:
- Proper file handling in tests
- Correct function signatures
- Working mocks

## Next Steps

1. Fix one test file at a time
2. Use `test_real_functionality.py` as a template
3. Run locally before pushing
4. Update this file as tests are fixed