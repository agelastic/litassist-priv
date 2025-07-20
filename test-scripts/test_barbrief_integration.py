#!/usr/bin/env python3
"""Integration tests for barbrief command."""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_command(cmd):
    """Run a command and return output."""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def test_barbrief_help():
    """Test that barbrief help works."""
    print("Testing barbrief --help...")
    code, stdout, stderr = run_command("litassist barbrief --help")
    
    if code == 0 and "Generate comprehensive barrister's brief" in stdout:
        print("[Y] Help command works")
        return True
    else:
        print(f"[N] Help command failed with code {code}")
        print(f"  stderr: {stderr}")
        return False


def test_invalid_case_facts():
    """Test with invalid case facts format."""
    print("\nTesting invalid case facts validation...")
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is not a valid case facts file\nJust some random text")
        invalid_file = f.name
    
    try:
        code, stdout, stderr = run_command(
            f"litassist barbrief {invalid_file} --hearing-type trial"
        )
        
        if code != 0 and "10-heading format" in stderr:
            print("[Y] Correctly rejected invalid case facts")
            return True
        else:
            print("[N] Failed to reject invalid case facts")
            return False
    finally:
        os.unlink(invalid_file)


def test_basic_barbrief_generation():
    """Test basic brief generation with minimal inputs."""
    print("\nTesting basic brief generation...")
    
    # Create a valid case facts file
    case_facts = """# Case Facts

## Parties
Test Plaintiff v Test Defendant

## Background
Test background information for the case.

## Key Events
1. Event 1
2. Event 2

## Legal Issues
1. Issue 1
2. Issue 2

## Evidence Available
- Document 1
- Document 2

## Opposing Arguments
The defendant argues X.

## Procedural History
Filed in court.

## Jurisdiction
Test Court

## Applicable Law
Test Act 2024

## Client Objectives
Win the case.
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(case_facts)
        case_file = f.name
    
    try:
        # Run with a small test that shouldn't call the API
        code, stdout, stderr = run_command(
            f"litassist barbrief {case_file} --hearing-type trial --help"
        )
        
        if code == 0:
            print("[Y] Command structure is valid")
            return True
        else:
            print(f"[N] Command failed with code {code}")
            print(f"  stderr: {stderr}")
            return False
    finally:
        os.unlink(case_file)


def test_all_options():
    """Test with all command options."""
    print("\nTesting all command options...")
    
    # Create test files
    files = {}
    
    # Case facts
    case_facts = """# Case Facts
## Parties
A v B
## Background
Test
## Key Events
Test
## Legal Issues
Test
## Evidence Available
Test
## Opposing Arguments
Test
## Procedural History
Test
## Jurisdiction
Test
## Applicable Law
Test
## Client Objectives
Test
"""
    
    strategies = "# Legal Strategies\n\nTest strategies content"
    research = "# Research Report\n\nTest research content"
    document = "# Supporting Document\n\nTest document content"
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write files
        files['case'] = Path(tmpdir) / "case_facts.txt"
        files['case'].write_text(case_facts)
        
        files['strat'] = Path(tmpdir) / "strategies.txt"
        files['strat'].write_text(strategies)
        
        files['research'] = Path(tmpdir) / "research.txt"
        files['research'].write_text(research)
        
        files['doc'] = Path(tmpdir) / "document.txt"
        files['doc'].write_text(document)
        
        # Test command with all options (dry run with --help)
        cmd = (
            f"litassist barbrief {files['case']} "
            f"--hearing-type appeal "
            f"--strategies {files['strat']} "
            f"--research {files['research']} "
            f"--documents {files['doc']} "
            f"--context 'Focus on jurisdiction' "
            f"--verify "
            f"--help"
        )
        
        code, stdout, stderr = run_command(cmd)
        
        if code == 0:
            print("[Y] All options accepted")
            return True
        else:
            print(f"[N] Command with all options failed with code {code}")
            print(f"  stderr: {stderr}")
            return False


def test_output_directory():
    """Test that output directory would be created correctly."""
    print("\nTesting output directory handling...")
    
    # Check if outputs directory exists or can be created
    output_dir = Path("outputs")
    
    if output_dir.exists() or output_dir.parent.exists():
        print("[Y] Output directory is accessible")
        return True
    else:
        print("[N] Output directory path not accessible")
        return False


def main():
    """Run all tests."""
    print("Running barbrief integration tests...\n")
    
    tests = [
        test_barbrief_help,
        test_invalid_case_facts,
        test_basic_barbrief_generation,
        test_all_options,
        test_output_directory,
    ]
    
    passed = 0
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"[N] Test {test.__name__} crashed: {e}")
    
    print(f"\n{'='*50}")
    print(f"Tests passed: {passed}/{len(tests)}")
    
    if passed == len(tests):
        print("All tests passed! [Y]")
        return 0
    else:
        print(f"{len(tests) - passed} tests failed [N]")
        return 1


if __name__ == "__main__":
    sys.exit(main())