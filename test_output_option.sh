#!/bin/bash
# Test --output option for all CLI commands

set -e  # Exit on error

echo "Testing --output option for all commands..."

# Create test files if they don't exist
echo "Creating test files..."
echo "Test case facts" > test_facts.txt
echo "Test strategies" > test_strategies.txt
echo "Test document" > test_document.txt

# Test extractfacts
echo "1. Testing extractfacts --output"
litassist extractfacts test_document.txt --output my_facts 2>/dev/null | grep -q "my_facts" && echo "✓ extractfacts works" || echo "✗ extractfacts failed"

# Test digest
echo "2. Testing digest --output"
litassist digest test_document.txt --output my_digest 2>/dev/null | grep -q "my_digest" && echo "✓ digest works" || echo "✗ digest failed"

# Test brainstorm
echo "3. Testing brainstorm --output"
litassist brainstorm --facts test_facts.txt --side plaintiff --area civil --output my_brainstorm 2>/dev/null | grep -q "my_brainstorm" && echo "✓ brainstorm works" || echo "✗ brainstorm failed"

# Test lookup
echo "4. Testing lookup --output"
litassist lookup "test question" --output my_lookup 2>/dev/null | grep -q "my_lookup" && echo "✓ lookup works" || echo "✗ lookup failed"

# Test draft
echo "5. Testing draft --output"
litassist draft test_document.txt --query "test brief" --output my_draft 2>/dev/null | grep -q "my_draft" && echo "✓ draft works" || echo "✗ draft failed"

# Test barbrief
echo "6. Testing barbrief --output"
# Note: barbrief requires specific 10-heading format, so this might fail
litassist barbrief test_facts.txt --hearing-type trial --output my_brief 2>/dev/null | grep -q "my_brief" && echo "✓ barbrief works" || echo "✗ barbrief (expected - needs proper case facts)"

# Test strategy (multi-output)
echo "7. Testing strategy --output (multi-output)"
litassist strategy test_facts.txt --outcome "win case" --output my_strategy 2>/dev/null | grep -q "my_strategy" && echo "✓ strategy works" || echo "✗ strategy failed"

# Test caseplan (multi-output) 
echo "8. Testing caseplan --output (multi-output)"
litassist caseplan test_facts.txt --budget minimal --output my_plan 2>/dev/null | grep -q "my_plan" && echo "✓ caseplan works" || echo "✗ caseplan failed"

# Test counselnotes
echo "9. Testing counselnotes --output"
litassist counselnotes test_document.txt --output my_notes 2>/dev/null | grep -q "my_notes" && echo "✓ counselnotes works" || echo "✗ counselnotes failed"

# Test verify (multi-output)
echo "10. Testing verify --output (multi-output)"
litassist verify test_document.txt --output my_verify 2>/dev/null | grep -q "my_verify" && echo "✓ verify works" || echo "✗ verify failed"

echo ""
echo "Testing complete! Check outputs/ directory for generated files."

# Clean up test files
rm -f test_facts.txt test_strategies.txt test_document.txt

echo "Test files cleaned up."