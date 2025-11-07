#!/usr/bin/env python3
"""
Test script for citation fetching improvements.

Tests the citation fetching system with a mix of real and fake citations
to verify that:
1. Phase 1 (structure-aware validation) works correctly
2. Phase 2 (top-3 result validation) catches citations in ranks 2-3
3. Phase 3 (failure tracking) provides clear failure reasons
4. Query variant removal didn't hurt success rates

Run with: python3 test_citation_fetching.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from litassist.citation_context import fetch_citation_context
from litassist.utils.formatting import (
    success_message,
    warning_message,
    info_message,
    stats_message,
)
import click


# Test citations - mix of real (should succeed) and fake (should fail)
TEST_CITATIONS = {
    "Real cases (should succeed)": [
        "[2022] HCA 34",  # Nguyen v Minister - recent HCA case
        "[2021] HCA 18",  # Palmer v Ayres - recent HCA case
        "[2020] HCA 5",   # Smethurst v Commissioner - recent HCA case
    ],
    "Legislation (should succeed)": [
        "Freedom of Information Act 1982 (Cth)",  # Has hardcoded URL
        "Privacy Act 1988 (Cth)",  # Common legislation
    ],
    "Fake citations (should fail)": [
        "Smith v Jones [2023] NSWCA 999",  # Fake case
        "[2099] HCA 999",  # Future case (doesn't exist)
        "Imaginary Act 3000 (Cth)",  # Fake legislation
    ],
    "Edge cases": [
        "[2015] FCA 123",  # Older case - may or may not exist
        "[2018] NSWSC 456",  # State court case
    ],
}


def print_section_header(title):
    """Print a formatted section header."""
    click.echo("\n" + "=" * 80)
    click.echo(f"  {title}")
    click.echo("=" * 80)


def print_citation_result(citation, content_length=None, reason=None):
    """Print result for a single citation."""
    if content_length:
        click.echo(f"  ✓ {citation}")
        click.echo(f"    Retrieved: {content_length:,} characters")
    else:
        click.echo(f"  ✗ {citation}")
        click.echo(f"    Reason: {reason}")


def analyze_log_for_strategies():
    """
    Analyze the most recent log file for validation strategies and result ranks.
    Returns statistics about what strategies and ranks succeeded.
    """
    import glob
    import json
    from collections import Counter

    log_files = sorted(glob.glob("logs/litassist_*.log"), reverse=True)
    if not log_files:
        return None, None

    latest_log = log_files[0]

    strategies = []
    ranks = []

    try:
        with open(latest_log, 'r') as f:
            for line in f:
                if "validation_strategy_succeeded" in line:
                    try:
                        log_entry = json.loads(line.split(" - ")[-1])
                        if "strategy" in log_entry:
                            strategies.append(log_entry["strategy"])
                    except (json.JSONDecodeError, IndexError):
                        pass

                if "_validated" in line and "result_rank" in line:
                    try:
                        log_entry = json.loads(line.split(" - ")[-1])
                        if "result_rank" in log_entry:
                            ranks.append(log_entry["result_rank"])
                    except (json.JSONDecodeError, IndexError):
                        pass
    except Exception:
        return None, None

    return Counter(strategies) if strategies else None, Counter(ranks) if ranks else None


def main():
    """Run citation fetching tests."""
    print_section_header("Citation Fetching Test Suite")
    click.echo("Testing citation fetching improvements:")
    click.echo("  - Phase 1: Structure-aware validation")
    click.echo("  - Phase 2: Top-3 result validation")
    click.echo("  - Phase 3: Failure tracking")
    click.echo("\nThis will make real API calls to Google CSE and may take 1-2 minutes.")

    # Flatten all test citations
    all_citations = []
    for category, citations in TEST_CITATIONS.items():
        all_citations.extend(citations)

    click.echo(info_message(f"Testing {len(all_citations)} citations..."))
    click.echo("")

    # Fetch all citations
    context, failures = fetch_citation_context(all_citations)

    # Create failure dict for easier lookup
    failure_dict = dict(failures)

    # Display results by category
    for category, citations in TEST_CITATIONS.items():
        print_section_header(category)

        for citation in citations:
            if citation in context:
                print_citation_result(citation, len(context[citation]))
            else:
                reason = failure_dict.get(citation, "Unknown error")
                print_citation_result(citation, reason=reason)

    # Summary statistics
    print_section_header("Summary Statistics")

    total = len(all_citations)
    succeeded = len(context)
    failed = len(failures)
    success_rate = (succeeded / total * 100) if total > 0 else 0

    click.echo(stats_message(f"Total citations tested: {total}"))
    click.echo(success_message(f"Successfully fetched: {succeeded} ({success_rate:.1f}%)"))
    if failed > 0:
        click.echo(warning_message(f"Failed to fetch: {failed} ({100-success_rate:.1f}%)"))

    # Show failure reasons breakdown
    if failures:
        click.echo("\n" + info_message("Failure Reasons:"))
        reason_counts = {}
        for _, reason in failures:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True):
            click.echo(f"  - {reason}: {count}")

    # Analyze log for validation strategies and result ranks
    click.echo("\n" + info_message("Analyzing validation strategies from logs..."))
    strategies, ranks = analyze_log_for_strategies()

    if strategies:
        click.echo("\nValidation Strategies Used:")
        for strategy, count in strategies.most_common():
            click.echo(f"  - {strategy}: {count}")

    if ranks:
        click.echo("\nResult Rank Distribution (which CSE result succeeded):")
        for rank in sorted(ranks.keys()):
            count = ranks[rank]
            click.echo(f"  - Rank {rank}: {count} citations")

        rank_2_3 = ranks.get(2, 0) + ranks.get(3, 0)
        if rank_2_3 > 0:
            click.echo(success_message(
                f"\nPhase 2 benefit: {rank_2_3} citations found in ranks 2-3 "
                "(would have been missed without top-3 validation)"
            ))

    # Expected results guidance
    print_section_header("Expected Results")
    click.echo("Real cases (HCA): Should have ~90-100% success rate")
    click.echo("Legislation: Should have ~80-100% success rate")
    click.echo("Fake citations: Should have 0% success rate (all failures)")
    click.echo("Edge cases: May succeed or fail depending on availability")

    # API usage estimate
    print_section_header("API Usage")
    click.echo(f"Estimated Google CSE queries: {total * 2} queries")
    click.echo("(Assumes ~2 queries per citation on average)")
    click.echo(f"Time taken: ~{total * 3} seconds (with rate limiting)")

    click.echo("\n" + success_message("Test complete!"))
    click.echo("\nTo see detailed logs, check: logs/litassist_*.log")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        click.echo("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n{warning_message(f'Test failed: {e}')}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
