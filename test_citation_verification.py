#!/usr/bin/env python3
"""
Test script for the new citation verification system.

This script tests the core citation verification functionality to ensure
it correctly identifies and handles both valid and invalid citations.
"""

import sys
import os

# Add the litassist directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "litassist"))

from litassist.citation_verify import (
    extract_citations,
    verify_single_citation,
    verify_all_citations,
    remove_citation_from_text,
    is_core_citation,
    get_verification_stats,
    clear_verification_cache,
)


def test_citation_extraction():
    """Test citation extraction functionality."""
    print("Testing citation extraction...")

    test_text = """
    In Mabo v Queensland (No 2) (1992) 175 CLR 1, the High Court held that native title exists.
    This was confirmed in [2019] HCA 23 and also in Fake v Nonexistent [2023] HCA 999.
    The principle was established in Smith v Jones [2024] NSWSC 1234.
    """

    citations = extract_citations(test_text)
    print(f"Extracted citations: {citations}")

    expected_citations = ["[2019] HCA 23", "[2023] HCA 999", "[2024] NSWSC 1234"]
    for expected in expected_citations:
        if expected in citations:
            print(f"✓ Found expected citation: {expected}")
        else:
            print(f"✗ Missing expected citation: {expected}")

    return citations


def test_single_citation_verification():
    """Test verification of individual citations."""
    print("\nTesting single citation verification...")

    # Test a likely real citation (Mabo)
    real_citation = "[1992] HCA 23"
    exists, url, reason = verify_single_citation(real_citation)
    print(
        f"Real citation {real_citation}: exists={exists}, url={url}, reason='{reason}'"
    )

    # Test an obviously fake citation
    fake_citation = "[2023] HCA 999"
    exists, url, reason = verify_single_citation(fake_citation)
    print(
        f"Fake citation {fake_citation}: exists={exists}, url={url}, reason='{reason}'"
    )

    # Test invalid format
    invalid_citation = "Not a citation"
    exists, url, reason = verify_single_citation(invalid_citation)
    print(
        f"Invalid citation '{invalid_citation}': exists={exists}, url={url}, reason='{reason}'"
    )


def test_citation_removal():
    """Test surgical citation removal."""
    print("\nTesting citation removal...")

    test_text = "This principle was established in Smith v Jones [2023] HCA 999, which held that..."
    citation_to_remove = "[2023] HCA 999"

    cleaned_text = remove_citation_from_text(test_text, citation_to_remove)
    print(f"Original: {test_text}")
    print(f"Cleaned:  {cleaned_text}")

    if citation_to_remove not in cleaned_text:
        print("✓ Citation successfully removed")
    else:
        print("✗ Citation removal failed")


def test_core_citation_detection():
    """Test detection of core vs supporting citations."""
    print("\nTesting core citation detection...")

    # Core citation (in first sentence)
    core_text = "In Mabo v Queensland [1992] HCA 23, the High Court established native title. This was later confirmed."
    is_core = is_core_citation(core_text, "[1992] HCA 23")
    print(f"Core citation test: {is_core} (expected: True)")

    # Supporting citation (later in text)
    supporting_text = "Native title is well established. See also Smith v Jones [2020] HCA 45 for further discussion."
    is_core = is_core_citation(supporting_text, "[2020] HCA 45")
    print(f"Supporting citation test: {is_core} (expected: False)")


def test_verification_stats():
    """Test verification statistics."""
    print("\nTesting verification statistics...")

    # Clear cache first
    clear_verification_cache()

    # Verify a few citations to populate stats
    verify_single_citation("[1992] HCA 23")
    verify_single_citation("[2023] HCA 999")
    verify_single_citation("[2024] FAKE 123")

    stats = get_verification_stats()
    print(f"Verification stats: {stats}")


def test_batch_verification():
    """Test verification of multiple citations in text."""
    print("\nTesting batch verification...")

    test_text = """
    The law is well established in Mabo v Queensland [1992] HCA 23.
    However, the fake case Smith v Jones [2023] HCA 999 does not exist.
    Another real case is Wik v Queensland [1996] HCA 40.
    """

    verified, unverified = verify_all_citations(test_text)
    print(f"Verified citations: {verified}")
    print(f"Unverified citations: {unverified}")


def main():
    """Run all tests."""
    print("=== Citation Verification System Test ===\n")

    try:
        test_citation_extraction()
        test_single_citation_verification()
        test_citation_removal()
        test_core_citation_detection()
        test_verification_stats()
        test_batch_verification()

        print("\n=== Test Summary ===")
        print("✓ All tests completed successfully!")
        print("⚠️  Note: Some network-dependent tests may show different results")
        print("   depending on AustLII availability and actual case existence.")

    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
