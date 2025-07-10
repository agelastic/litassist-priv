#!/usr/bin/env python3
"""
Manual test script for verify command implementation.
Run this to test the verify command without pytest dependencies.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Test sample content
SAMPLE_LEGAL_TEXT = """
In the landmark case of Mabo v Queensland (No 2) [1992] HCA 23, the High Court 
recognized native title in Australia. This decision overturned the doctrine of 
terra nullius.

The principle established in Donoghue v Stevenson [1932] AC 562 regarding 
duty of care remains fundamental to negligence law.

As stated in Smith v Jones [2025] NSWSC 999, the test for causation requires...
(Note: This is a fictional future case for testing)
"""

SAMPLE_WITH_REASONING = """
Legal analysis of contract breach...

=== LEGAL REASONING TRACE ===
Issue: Whether the defendant breached the service contract by failing to deliver on time
Applicable Law: Contract law principles regarding breach and remedies under Australian Consumer Law
Application to Facts: The defendant agreed to deliver goods by March 1 but delivered on March 15
Conclusion: The defendant materially breached the contract entitling plaintiff to damages
Confidence: 85%
Sources: Hadley v Baxendale (1854) 9 Exch 341; Competition and Consumer Act 2010
"""

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    import importlib.util

    try:
        spec = importlib.util.find_spec("litassist.commands.verify")
        if spec is None:
            raise ImportError("verify module not found")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)  # type: ignore
        assert hasattr(module, "verify")
        assert hasattr(module, "_format_citation_report")
        assert hasattr(module, "_parse_soundness_issues")
        assert hasattr(module, "_verify_reasoning_trace")
        print("[PASS] All imports successful")
        return True
    except Exception as e:
        print(f"[FAIL] Import error: {e}")
        return False

def test_helper_functions():
    """Test helper functions directly."""
    print("\nTesting helper functions...")
    
    try:
        from litassist.commands.verify import (
            _format_citation_report, 
            _parse_soundness_issues,
            _verify_reasoning_trace
        )
        from litassist.utils import LegalReasoningTrace
        
        # Test citation report formatting
        report = _format_citation_report(
            verified=["Case1 [2020] HCA 1"], 
            unverified=[("Case2 [2025] FCA 999", "Future date")],
            total_found=2
        )
        assert "# Citation Verification Report" in report
        assert "[PASS] Case1 [2020] HCA 1" in report
        print("[PASS] Citation report formatting works")
        
        # Test soundness issue parsing
        issues = _parse_soundness_issues("The document contains an error in citation format.")
        assert len(issues) >= 1
        print("[PASS] Soundness issue parsing works")
        
        # Test reasoning trace verification
        trace = LegalReasoningTrace(
            issue="Test issue",
            applicable_law="Test law principles",
            application="Test application to facts",
            conclusion="Test conclusion",
            confidence=85,
            sources=["Test source"],
            command="verify"
        )
        status = _verify_reasoning_trace(trace)
        assert status["complete"]
        print("[PASS] Reasoning trace verification works")
        
        return True
    except Exception as e:
        print(f"[FAIL] Helper function test failed: {e}")
        return False

def test_command_structure():
    """Test the command can be imported and has correct structure."""
    print("\nTesting command structure...")
    
    try:
        from litassist.commands.verify import verify
        
        # Check it's a Click command
        assert hasattr(verify, 'name')
        assert verify.name == 'verify'
        
        # Check it has the right parameters
        params = {p.name for p in verify.params}
        assert 'file' in params
        assert 'citations' in params
        assert 'soundness' in params
        assert 'reasoning' in params
        
        print("[PASS] Command structure is correct")
        return True
    except Exception as e:
        print(f"[FAIL] Command structure test failed: {e}")
        return False

def test_llm_config():
    """Test that LLMClientFactory has verify configuration."""
    print("\nTesting LLM configuration...")
    
    try:
        from litassist.llm import LLMClientFactory
        
        # Check verify config exists
        assert 'verify' in LLMClientFactory.COMMAND_CONFIGS
        config = LLMClientFactory.COMMAND_CONFIGS['verify']
        
        # Check expected settings
        assert config['model'] == 'anthropic/claude-sonnet-4'
        assert config['temperature'] == 0
        assert config['top_p'] == 0.2
        assert not config['force_verify']
        
        print("[PASS] LLM configuration is correct")
        return True
    except Exception as e:
        print(f"[FAIL] LLM configuration test failed: {e}")
        return False

def test_file_operations():
    """Test file reading and writing operations."""
    print("\nTesting file operations...")
    
    try:
        from litassist.commands.verify import _format_citation_report
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(SAMPLE_LEGAL_TEXT)
            temp_path = f.name
        
        # Test reading
        with open(temp_path, 'r') as f:
            content = f.read()
        assert "Mabo v Queensland" in content
        
        # Test writing report
        report = _format_citation_report([], [], 0)
        report_path = temp_path.replace('.txt', '_citations.txt')
        with open(report_path, 'w') as f:
            f.write(report)
        
        # Verify report was written
        with open(report_path, 'r') as f:
            saved_report = f.read()
        assert "# Citation Verification Report" in saved_report
        
        # Cleanup
        os.unlink(temp_path)
        os.unlink(report_path)
        
        print("[PASS] File operations work correctly")
        return True
    except Exception as e:
        print(f"[FAIL] File operations test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Testing Verify Command Implementation ===\n")
    
    results = []
    results.append(("Imports", test_imports()))
    results.append(("Helper Functions", test_helper_functions()))
    results.append(("Command Structure", test_command_structure()))
    results.append(("LLM Config", test_llm_config()))
    results.append(("File Operations", test_file_operations()))
    
    print("\n=== Test Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS] PASS" if result else "[FAIL] FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All tests passed! The verify command implementation is working correctly.")
    else:
        print("\n[WARNING]  Some tests failed. Please check the implementation.")
        sys.exit(1)

if __name__ == "__main__":
    main()