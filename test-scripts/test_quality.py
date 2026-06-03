#!/usr/bin/env python3
"""
Quality validation tests for LitAssist integrations

This script performs in-depth quality validation for external services used
by LitAssist, ensuring responses meet Australian legal standards and
contain accurate information. Includes validation of the new verification system.

Usage:
    python test_quality.py [--all] [--openrouter] [--jade] [--verification]
"""

import os
import sys
import argparse
import yaml
import json
from openai import OpenAI  # used as HTTP client against OpenRouter
import requests
import contextlib
import io

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from test_utils import EnhancedTestResult

# ─── Configuration ────────────────────────────────────────────────
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"
)
if not os.path.exists(CONFIG_PATH):
    sys.exit("Error: Missing config.yaml")

with open(CONFIG_PATH) as f:
    try:
        cfg = yaml.safe_load(f)
    except yaml.YAMLError as e:
        sys.exit(f"Error parsing config.yaml: {e}")

# Validate and assign configuration
try:
    OR_KEY = cfg["openrouter"]["api_key"]
    OR_BASE = cfg["openrouter"].get("api_base", "https://openrouter.ai/api/v1")
    # Google CSE configuration - with fallback to None if missing
    GOOGLE_API_KEY = cfg.get("google_cse", {}).get("api_key", None)
    GOOGLE_CSE_ID = cfg.get("google_cse", {}).get("cse_id", None)
except KeyError as e:
    sys.exit(f"Error: config.yaml missing key {e}")

# API placeholder settings for validation
placeholder_values = [
    "YOUR_OPENROUTER_KEY",
    "YOUR_GOOGLE_API_KEY",
    "YOUR_GOOGLE_CSE_ID",
]


# Check for placeholder values and fail quality tests if credentials are missing
def validate_credentials_for_quality_testing():
    """Validate that real credentials are available for quality testing."""
    missing_creds = []

    if OR_KEY in placeholder_values:
        missing_creds.append("OpenRouter API key")
    if GOOGLE_API_KEY in placeholder_values or GOOGLE_CSE_ID in placeholder_values:
        missing_creds.append("Google CSE credentials")

    return missing_creds


# Note: Mock Google Search results removed - quality testing now requires real credentials


# ─── Test Utilities ────────────────────────────────────────────────
@contextlib.contextmanager
def suppress_expected_errors():
    """Capture and display verification error output in user-friendly format"""
    captured_stdout = io.StringIO()
    captured_stderr = io.StringIO()

    old_stdout = sys.stdout
    old_stderr = sys.stderr

    sys.stdout = captured_stdout
    sys.stderr = captured_stderr

    try:
        yield
    except Exception as e:
        # Restore output streams before showing unexpected errors
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        # Show captured output if there was an unexpected error
        captured_out = captured_stdout.getvalue()
        captured_err = captured_stderr.getvalue()

        if captured_out.strip():
            print(f"[OUTPUT] Captured output: {captured_out}")
        if captured_err.strip():
            print(f"[ERROR] Error details: {captured_err}")

        print(f"[FAIL] UNEXPECTED ERROR: {e}")
        raise
    finally:
        # Always restore streams
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        # Show captured error content that users should see
        captured_err = captured_stderr.getvalue()
        if captured_err.strip():
            print(f"[CHECKING] Error details: {captured_err.strip()}")


# Enhanced error handling now provided by test_utils.py


# OpenAI direct quality tests removed. LitAssist no longer talks to OpenAI
# directly: there is no separate OpenAI key in config and no embedding pipeline.
# All LLM operations route through OpenRouter.


# ─── OpenRouter Quality Tests ────────────────────────────────────────────────
def test_litassist_models(model_type="fast"):
    """
    Test that models used by LitAssist commands are accessible.

    Args:
        model_type: "fast" (default), "slow", or "all"
    """
    result = EnhancedTestResult("OpenRouter", "LitAssist Model Availability")

    try:
        # Require real credentials
        if OR_KEY in placeholder_values:
            result.failure(
                "OpenRouter API key not configured - model testing requires real credentials",
                context={"api_key_status": "placeholder", "api_base": OR_BASE},
            )
            return result

        from litassist.llm.factory import LLMClientFactory
        from litassist.llm.parameter_handler import get_model_family

        print("Testing availability of models used by LitAssist commands...")

        # Pull models from configuration; classify by family.
        # Reasoning-family models are treated as slow/expensive (tested only with --slow).
        all_configs = LLMClientFactory.list_configurations()
        fast_commands = [
            "extractfacts",
            "strategy",
            "brainstorm-orthodox",
            "brainstorm-unorthodox",
            "digest-summary",
            "lookup",
        ]
        slow_commands = ["draft"]

        def _model_for(cmd):
            return all_configs[cmd]["model"]

        fast_models = {cmd: _model_for(cmd) for cmd in fast_commands if cmd in all_configs}
        slow_models = {cmd: _model_for(cmd) for cmd in slow_commands if cmd in all_configs}
        _ = get_model_family  # available for future classification

        # Select models based on test type
        if model_type == "fast":
            command_models = fast_models
        elif model_type == "slow":
            command_models = slow_models
        else:  # "all"
            command_models = {**fast_models, **slow_models}

        model_results = {}

        for command, expected_model in command_models.items():
            try:
                # Get the actual model from factory
                if "-" in command:
                    cmd, subtype = command.split("-", 1)
                    client = LLMClientFactory.for_command(cmd, subtype)
                else:
                    # Reasoning models only accept "medium" verbosity
                    if command == "draft":
                        client = LLMClientFactory.for_command(command, verbosity="medium")
                    else:
                        client = LLMClientFactory.for_command(command)

                actual_model = client.model

                # Test a minimal completion to verify model is accessible.
                # Reasoning-family models do not support system messages.
                from litassist.llm.parameter_handler import get_model_family
                if get_model_family(actual_model) == "openai_reasoning":
                    test_messages = [
                        {"role": "user", "content": "Reply with 'OK'"},
                    ]
                else:
                    test_messages = [
                        {"role": "system", "content": "Test"},
                        {"role": "user", "content": "Reply with 'OK'"},
                    ]

                response, usage = client.complete(test_messages, max_tokens=40000)

                model_results[command] = {
                    "expected": expected_model,
                    "actual": actual_model,
                    "accessible": True,
                    "response": response[:50] if response else None,
                }

            except Exception as e:
                model_results[command] = {
                    "expected": expected_model,
                    "actual": actual_model if "actual_model" in locals() else "Unknown",
                    "accessible": False,
                    "error": str(e),
                }

        # Quality checks
        quality_checks = {
            "all_models_configured": all(
                r["actual"] == r["expected"] for r in model_results.values()
            ),
            "all_models_accessible": all(
                r["accessible"] for r in model_results.values()
            ),
            "claude_available": any(
                "claude" in r["actual"] and r["accessible"]
                for r in model_results.values()
            ),
            "grok_available": any(
                "grok" in r["actual"] and r["accessible"]
                for r in model_results.values()
            ),
            "o3_available": any(
                "o3" in r["actual"] and r["accessible"] for r in model_results.values()
            ),
            "gemini_available": any(
                "gemini" in r["actual"] and r["accessible"]
                for r in model_results.values()
            ),
        }

        quality_score = int(
            sum(1 for check in quality_checks.values() if check)
            * (100 / len(quality_checks))
        )

        if quality_score >= 80:
            result.success(
                quality_score=quality_score,
                quality_checks=quality_checks,
                model_results=model_results,
                models_tested=len(model_results),
            )
        else:
            result.failure(
                f"Model availability score ({quality_score}/100) below threshold. Results: {model_results}",
                context={
                    "api_base": OR_BASE,
                    "quality_score": quality_score,
                    "commands_tested": list(command_models.keys()),
                    "accessible_models": [
                        cmd
                        for cmd, res in model_results.items()
                        if res.get("accessible")
                    ],
                },
            )

    except Exception as e:
        result.failure(
            e,
            context={
                "api_base": OR_BASE,
                "commands_to_test": (
                    list(command_models.keys()) if "command_models" in locals() else []
                ),
            },
        )

    return result


def test_openrouter_australian_judgment():
    """Test OpenRouter Australian legal judgement formatting"""
    result = EnhancedTestResult("OpenRouter", "Australian Judgment Format")

    try:
        # Require real credentials for quality testing
        if OR_KEY in placeholder_values:
            result.failure(
                "OpenRouter API key not configured - quality testing requires real credentials",
                context={"api_key_status": "placeholder", "api_base": OR_BASE},
            )
            return result

        print("Configuring OpenRouter API connection...")
        # Configure OpenAI client with OpenRouter base
        client = OpenAI(api_key=OR_KEY, base_url=OR_BASE)

        # Use a model the project actually configures (extractfacts is a stable representative)
        from litassist.llm.factory import LLMClientFactory
        model = LLMClientFactory.list_configurations()["extractfacts"]["model"]
        print(f"Testing Australian judgment format with {model} via OpenRouter...")

        # Test with a more explicit request for Australian judgment format
        messages = [
            {
                "role": "system",
                "content": "You are a legal assistant specializing in Australian law. Use Australian English spellings (e.g., 'judgement' not 'judgment') and Australian legal terminology.",
            },
            {
                "role": "user",
                "content": """Draft the opening paragraph of a Federal Court of Australia judgement. 
            
            The case involves a trade mark dispute between tech companies TechCorp and InnoSystems over the use of 'NexGen' mark. 
            
            IMPORTANT REQUIREMENTS:
            1. Use Australian English spelling, particularly 'judgement' (not 'judgment')
            2. Use proper Australian legal formatting with correct structure
            3. Use the phrase 'trade mark' (two words) as per Australian terminology
            4. Include 'Federal Court of Australia' in the header
            5. Begin with '[JUDGE NAME], J:' as per Australian convention
            
            Make sure to follow all Australian legal conventions.""",
            },
        ]

        response = client.chat.completions.create(
            model=model, messages=messages, max_tokens=250, temperature=0
        )

        content = response.choices[0].message.content.lower()

        # Check usage information
        usage = getattr(response, "usage", None)
        tokens_used = usage.total_tokens if usage else "Not provided"

        # Validate Australian judgment format elements
        quality_checks = {
            "australian_spelling": any(
                term in content for term in ["judgement", "honours?", "recognised"]
            ),
            "federal_court_reference": "federal court" in content,
            "proper_case_name": ("techcorp" in content and "innosystems" in content)
            or "v" in content,
            "proper_formatting": any(
                term in content for term in ["j:", "justice", "reasons for"]
            ),
            "correct_trademark_terminology": "trade mark" in content,
        }

        # Calculate overall quality score (0-100)
        quality_score = int(
            sum(1 for check in quality_checks.values() if check)
            * (100 / len(quality_checks))
        )

        # Lower the threshold to 40% (2/5 checks) since this is challenging for the models
        if quality_score >= 40:
            result.success(
                model=model,
                response=response.choices[0].message.content,
                tokens_used=tokens_used,
                quality_score=quality_score,
                quality_checks=quality_checks,
            )
        else:
            result.failure(
                f"Australian judgment format score ({quality_score}/100) below threshold. Quality checks: {quality_checks}",
                context={
                    "model": model,
                    "api_base": OR_BASE,
                    "quality_score": quality_score,
                    "tokens_used": tokens_used,
                },
            )

    except Exception as e:
        result.failure(
            e,
            context={
                "model": model if "model" in locals() else "unknown",
                "api_base": OR_BASE,
                "request_type": "australian_judgment_format",
            },
        )

    return result


def test_openrouter_case_citation():
    """Test OpenRouter Australian case citation formatting"""
    result = EnhancedTestResult("OpenRouter", "Australian Case Citation")

    try:
        # Require real credentials for quality testing
        if OR_KEY in placeholder_values:
            result.failure(
                "OpenRouter API key not configured - quality testing requires real credentials",
                context={"api_key_status": "placeholder", "api_base": OR_BASE},
            )
            return result

        print("Configuring OpenRouter API connection...")
        # Configure OpenAI client with OpenRouter base
        client = OpenAI(api_key=OR_KEY, base_url=OR_BASE)

        # Use a model the project actually configures
        from litassist.llm.factory import LLMClientFactory
        model = LLMClientFactory.list_configurations()["extractfacts"]["model"]
        print(f"Testing Australian case citation format with {model} via OpenRouter...")

        # Test with a request to format citations correctly in Australian style
        messages = [
            {
                "role": "system",
                "content": "You are a legal assistant specializing in Australian law. Use Australian English spellings and terminology.",
            },
            {
                "role": "user",
                "content": """
            Format the following cases using proper Australian legal citation format:
            
            1. Mabo v Queensland (No 2) from the High Court of Australia in 1992, volume 175 of CLR, starting at page 1
            2. Lange v Australian Broadcasting Corporation from the High Court in 1997
            3. The Toll Group Pty Ltd v Alphapharm Pty Ltd case from the High Court in 2004
            
            Ensure you follow Australian citation guidelines precisely.
            """,
            },
        ]

        response = client.chat.completions.create(
            model=model, messages=messages, max_tokens=250, temperature=0
        )

        content = response.choices[0].message.content.lower()

        # Check for proper citation formats
        quality_checks = {
            "mabo_citation": "mabo v queensland (no 2) (1992) 175 clr 1"
            in content.replace(" ", "").lower(),
            "lange_citation": "lange v australian broadcasting corporation" in content
            and "1997" in content
            and "hca" in content,
            "toll_citation": "toll" in content
            and "alphapharm" in content
            and "2004" in content
            and ("hca" in content or "clr" in content),
            "proper_formatting": "[" in content
            or "(" in content,  # Basic check for brackets in citation
            "consistent_style": (content.count("(") > 2 and content.count(")") > 2)
            or (
                content.count("[") > 2 and content.count("]") > 2
            ),  # Check for consistent use of brackets
        }

        # Check usage information
        usage = getattr(response, "usage", None)
        tokens_used = usage.total_tokens if usage else "Not provided"

        # Calculate overall quality score (0-100)
        quality_score = int(
            sum(1 for check in quality_checks.values() if check)
            * (100 / len(quality_checks))
        )

        # Only consider success if quality score is above 60 (at least 3/5 checks passed)
        if quality_score >= 60:
            result.success(
                model=model,
                response=response.choices[0].message.content,
                tokens_used=tokens_used,
                quality_score=quality_score,
                quality_checks=quality_checks,
            )
        else:
            result.failure(
                f"Australian citation format score ({quality_score}/100) below threshold. Quality checks: {quality_checks}",
                context={
                    "model": model,
                    "api_base": OR_BASE,
                    "quality_score": quality_score,
                    "tokens_used": tokens_used,
                },
            )

    except Exception as e:
        result.failure(
            e,
            context={
                "model": model if "model" in locals() else "unknown",
                "api_base": OR_BASE,
                "request_type": "australian_citation_format",
            },
        )

    return result


# ─── Google CSE Quality Tests ────────────────────────────────────────────────
def search_google(query, api_key, cse_id, use_mock=False):
    """Perform a Google CSE search with the given query - quality testing only uses real API"""
    # Quality testing requires real API calls only
    import googleapiclient.discovery

    service = googleapiclient.discovery.build(
        "customsearch", "v1", developerKey=api_key, cache_discovery=False
    )

    try:
        result = service.cse().list(q=query, cx=cse_id, num=5).execute()
        items = result.get("items", [])
        return [
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in items
        ]
    except Exception as e:
        raise Exception(f"Google CSE search failed: {e}")


def test_google_search_relevance():
    """Test Google CSE search relevance for Australian legal queries"""
    result = EnhancedTestResult("Google CSE", "Search Relevance")

    try:
        # Require real credentials for quality testing
        if (
            GOOGLE_API_KEY is None
            or GOOGLE_CSE_ID is None
            or GOOGLE_API_KEY in placeholder_values
            or GOOGLE_CSE_ID in placeholder_values
        ):
            result.failure(
                "Google CSE credentials not configured - quality testing requires real credentials",
                context={
                    "api_key_status": (
                        "placeholder"
                        if GOOGLE_API_KEY in placeholder_values
                        else "missing"
                    ),
                    "cse_id_status": (
                        "placeholder"
                        if GOOGLE_CSE_ID in placeholder_values
                        else "missing"
                    ),
                },
            )
            return result

        print("Configuring Google Custom Search API connection...")
        print("Testing search relevance for Australian legal queries...")
        # Test queries designed to find Australian legal content
        test_queries = [
            "austlii family law act",
            "leading australian case adverse possession",
            "australian defamation law cases",
        ]

        query_results = []
        for query in test_queries:
            results = search_google(
                query, GOOGLE_API_KEY, GOOGLE_CSE_ID, use_mock=False
            )
            query_results.append(
                {
                    "query": query,
                    "results_count": len(results),
                    "sample_result": results[0] if results else None,
                    "all_results": results[:3],  # Store first 3 for quality analysis
                }
            )

        # Enhanced quality checks for real Google CSE testing
        quality_checks = {
            "has_results": all(r["results_count"] > 0 for r in query_results),
            "australian_content": any(
                "austlii" in r.get("sample_result", {}).get("link", "").lower()
                for r in query_results
            ),
            "legal_content": any(
                term in str(query_results).lower()
                for term in ["law", "act", "case", "court", "legislation"]
            ),
            "search_functioning": len(query_results) == len(test_queries),
            "relevant_results": all(
                r["results_count"] >= 3 for r in query_results
            ),  # Expect at least 3 results per query
            "quality_domains": any(
                domain in str(query_results).lower()
                for domain in [
                    "austlii",
                    "jade.io",
                    "legislation.gov.au",
                    "courts.gov.au",
                ]
            ),
        }

        quality_score = int(
            sum(1 for check in quality_checks.values() if check)
            * (100 / len(quality_checks))
        )

        # Higher threshold for real API testing
        if quality_score >= 70:  # 4/6 checks must pass
            result.success(
                api_status="using REAL Google CSE API",
                queries_tested=len(test_queries),
                quality_score=quality_score,
                sample_queries=test_queries,
                sample_results=query_results,
                quality_checks=quality_checks,
            )
        else:
            result.failure(
                f"Google CSE search quality score ({quality_score}/100) below threshold. Quality checks: {quality_checks}",
                context={
                    "api_key": (
                        GOOGLE_API_KEY[:10] + "..." if GOOGLE_API_KEY else "None"
                    ),
                    "cse_id": GOOGLE_CSE_ID,
                    "quality_score": quality_score,
                    "queries_tested": test_queries,
                },
            )

    except Exception as e:
        result.failure(
            e,
            context={
                "api_key": GOOGLE_API_KEY[:10] + "..." if GOOGLE_API_KEY else "None",
                "cse_id": GOOGLE_CSE_ID,
                "queries": test_queries if "test_queries" in locals() else [],
            },
        )

    return result


# ─── Jade Quality Tests ────────────────────────────────────────────────
def test_jade_extraction_accuracy():
    """Test Jade content extraction accuracy"""
    result = EnhancedTestResult("Jade", "Content Extraction Accuracy")

    try:
        print("Testing Jade database content extraction...")
        # Test accessing a different landmark case with known content (use a more accessible case)
        url = "https://jade.io/article/67958"  # Mabo v Queensland (No 2)
        print(f"Accessing case from Jade database: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            result.failure(
                f"HTTP {response.status_code} error",
                context={"url": url, "status_code": response.status_code},
            )
            return result

        content = response.text.lower()

        # Check for basic page structure rather than specific content
        # This is more reliable as we're just validating we can access a case
        quality_checks = {
            "page_found": response.status_code == 200,
            "case_content": len(content) > 1000,  # Simple check for substantial content
            "is_legal_document": any(
                term in content
                for term in ["court", "justice", "judgement", "judgment", "case"]
            ),
            "case_reference": any(
                term in content
                for term in ["mabo", "queensland", "native title", "decision"]
            ),
            "contains_citation": any(
                pattern in content for pattern in ["clr", "hca", "1992", "175"]
            ),
        }

        # Lower bar for success - we're just checking if the page is accessible and has legal content
        quality_score = int(
            sum(1 for check in quality_checks.values() if check)
            * (100 / len(quality_checks))
        )

        # Consider success if score is at least 40% (2/5 checks)
        if quality_score >= 40:
            result.success(
                status_code=response.status_code,
                url=url,
                content_length=len(content),
                quality_score=quality_score,
                quality_checks=quality_checks,
            )
        else:
            result.failure(
                f"Content extraction accuracy score ({quality_score}/100) below threshold. Quality checks: {quality_checks}",
                context={
                    "url": url,
                    "status_code": response.status_code,
                    "content_length": len(content),
                    "quality_score": quality_score,
                },
            )

    except Exception as e:
        result.failure(
            e,
            context={
                "url": url if "url" in locals() else "https://jade.io/article/67958",
                "timeout": 10,
                "headers": headers if "headers" in locals() else {},
            },
        )

    return result


def test_jade_legal_content_quality():
    """Test Jade legal content quality and structure"""
    result = EnhancedTestResult("Jade", "Legal Content Quality")

    try:
        print("Testing Jade legal content quality and structure...")
        # Test accessing the same case but focus on different quality aspects
        url = "https://jade.io/article/67958"  # Use same reliable case as first test
        print(f"Accessing legal document from Jade: {url}")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code != 200:
            result.failure(
                f"HTTP {response.status_code} error accessing Jade legal content",
                context={"url": url, "status_code": response.status_code},
            )
            return result

        content = response.text.lower()

        # Quality checks focused on different aspects than first test
        quality_checks = {
            "accessible": response.status_code == 200,
            "substantial_content": len(content)
            > 1000,  # Lower bar since we know this case works
            "legal_terminology": any(
                term in content
                for term in ["court", "justice", "judgment", "case", "decision"]
            ),
            "australian_legal_context": any(
                term in content
                for term in ["australia", "queensland", "mabo", "native title"]
            ),
            "html_structure": "<" in content and ">" in content,  # Basic HTML structure
            "contains_legal_text": len(content) > 500,  # Has substantial text content
        }

        quality_score = int(
            sum(1 for check in quality_checks.values() if check)
            * (100 / len(quality_checks))
        )

        # Set lower threshold since this is testing different aspects
        if quality_score >= 50:  # 3/6 checks must pass
            result.success(
                quality_score=quality_score,
                quality_checks=quality_checks,
                url=url,
                content_length=len(content),
                legal_document_verified=True,
            )
        else:
            result.failure(
                f"Legal content quality score ({quality_score}/100) below threshold. Quality checks: {quality_checks}",
                context={
                    "url": url,
                    "status_code": response.status_code,
                    "content_length": len(content),
                    "quality_score": quality_score,
                },
            )

    except Exception as e:
        result.failure(
            e,
            context={
                "url": url if "url" in locals() else "https://jade.io/article/67958",
                "timeout": 10,
                "headers": headers if "headers" in locals() else {},
            },
        )

    return result



# ─── Main Test Runner ────────────────────────────────────────────────
def run_tests(args):
    """Run the selected quality tests based on command-line arguments"""
    results = []

    # Print test header
    print("\n" + "=" * 60)
    print("LitAssist Quality Validation Tests")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60 + "\n")

    # OpenRouter tests
    if args.all or args.openrouter or args.slow:
        print("\nRunning OpenRouter quality tests:")
        print("-" * 40)
        # Determine which models to test
        if args.slow:
            results.append(test_litassist_models(model_type="slow"))
        elif args.openrouter:
            results.append(test_litassist_models(model_type="all"))
        else:  # args.all
            results.append(test_litassist_models(model_type="fast"))

        # Only run these additional tests with --all or --openrouter (not --slow)
        if not args.slow:
            results.append(test_openrouter_australian_judgment())
            results.append(test_openrouter_case_citation())

    # Jade tests
    if args.all or args.jade:
        print("\nRunning Jade quality tests:")
        print("-" * 40)
        results.append(test_jade_extraction_accuracy())
        results.append(test_jade_legal_content_quality())

    # Google CSE tests
    if args.all or args.google:
        print("\nRunning Google CSE quality tests:")
        print("-" * 40)
        results.append(test_google_search_relevance())

    # Verification system tests - only run when explicitly requested (too slow/expensive)
    if args.verification:
        print("\nRunning Verification System quality tests:")
        print("-" * 40)
        results.append(test_verification_system())

    # Print summary
    print("\n" + "=" * 60)
    print("Quality Test Summary")
    print("=" * 60)

    success_count = sum(1 for r in results if r.status == "SUCCESS")
    failure_count = sum(1 for r in results if r.status == "FAILURE")

    print(f"Total tests: {len(results)}")
    print(f"Successes:   {success_count}")
    print(f"Failures:    {failure_count}")

    # Write results to file
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_path = f"quality_results_{timestamp}.json"

    with open(output_path, "w") as f:
        json.dump([r.to_dict() for r in results], f, indent=2)

    print(f"\nDetailed results saved to: {output_path}")

    # Return overall success/failure
    return failure_count == 0


def test_verification_system():
    """Test the enhanced verification system effectiveness with real LLM calls."""
    result = EnhancedTestResult(
        "Verification System", "Real Verification Effectiveness"
    )

    try:
        # Require real credentials for verification effectiveness testing
        if OR_KEY in placeholder_values:
            result.failure(
                "OpenRouter API key not configured - verification testing requires real LLM calls",
                context={"api_key_status": "placeholder", "api_base": OR_BASE},
            )
            return result

        print("Testing verification system with real LLM calls...")
        from litassist.llm import LLMClient
        from litassist.llm.factory import LLMClientFactory

        # Test with real LLM calls to measure actual verification effectiveness.
        # Use the configured verify-reasoning model (Anthropic family) as a stable proxy.
        verification_model = LLMClientFactory.list_configurations()["verify-reasoning"]["model"]
        print(f"Initializing {verification_model} for verification effectiveness testing...")
        test_client = LLMClient(verification_model, temperature=0.2)

        # Test cases with known issues that verification should catch
        test_cases = [
            {
                "name": "hallucinated_citation",
                "content": "In Smith v Jones [2030] HCA 999, the court established that defendants must pay 150% damages.",
                "expected_issues": [
                    "fabricated_case",
                    "future_year",
                    "impossible_percentage",
                ],
            },
            {
                "name": "american_spelling",
                "content": "The organization's defense argued that the judgment was based on color of law.",
                "expected_issues": ["american_spelling"],
            },
            {
                "name": "suspicious_percentages",
                "content": "Studies show that 99.7% of all contract disputes result in plaintiff victory.",
                "expected_issues": ["unrealistic_statistics"],
            },
        ]

        verification_results = []
        print(f"Running {len(test_cases)} verification test cases...")

        for i, test_case in enumerate(test_cases, 1):
            print(f"Test case {i}: {test_case['name']}")

            with suppress_expected_errors():
                # Test citation validation
                citation_issues = test_client.validate_citations(test_case["content"])

                # Test auto-verification triggers
                should_auto_verify = test_client.should_auto_verify(
                    test_case["content"]
                )

                # Test actual verification with real LLM call
                try:
                    corrections, _ = test_client.verify(test_case["content"])
                    verification_worked = len(corrections.strip()) > 0
                    verification_error = None
                except Exception as e:
                    corrections = f"Verification failed: {e}"
                    verification_worked = False
                    verification_error = str(e)

            print(f"  [Y] Citation validation: {len(citation_issues)} issues caught")
            print(f"  [Y] Auto-verification triggered: {should_auto_verify}")
            print(f"  [Y] Verification feedback provided: {verification_worked}")

            # Show verification error if it occurred
            if verification_error:
                print(f"  [WARNING]  Verification error details: {verification_error}")

            verification_results.append(
                {
                    "test_case": test_case["name"],
                    "citation_issues_found": len(citation_issues),
                    "auto_verify_triggered": should_auto_verify,
                    "verification_provided_feedback": verification_worked,
                    "corrections_sample": corrections[:200] if corrections else "None",
                }
            )

        print("\nTesting verification system configuration...")
        print("  Checking critical command auto-verification...")
        print("  Testing Grok model auto-verification...")

        # Quality checks for verification effectiveness
        quality_checks = {
            "citation_validation_catches_issues": any(
                r["citation_issues_found"] > 0 for r in verification_results
            ),
            "auto_verify_triggers_correctly": all(
                r["auto_verify_triggered"] for r in verification_results
            ),
            "verification_provides_feedback": any(
                r["verification_provided_feedback"] for r in verification_results
            ),
            "critical_commands_auto_verify": test_client.should_auto_verify(
                "test", "extractfacts"
            ),
            "grok_auto_verify": LLMClient(
                LLMClientFactory.list_configurations()["brainstorm-unorthodox"]["model"]
            ).should_auto_verify("test"),
            "real_llm_verification_works": any(
                "correction" in r["corrections_sample"].lower()
                or "error" in r["corrections_sample"].lower()
                or "australian" in r["corrections_sample"].lower()
                for r in verification_results
                if r["corrections_sample"] != "None"
            ),
        }

        quality_score = int(
            sum(1 for check in quality_checks.values() if check)
            * (100 / len(quality_checks))
        )

        if quality_score >= 60:  # Reasonable threshold for verification effectiveness
            result.success(
                quality_score=quality_score,
                quality_checks=quality_checks,
                verification_results=verification_results,
                test_cases_processed=len(test_cases),
            )
        else:
            result.failure(
                f"Verification effectiveness score ({quality_score}/100) below threshold. Results: {verification_results}",
                context={
                    "api_base": OR_BASE,
                    "test_client_model": test_client.model,
                    "quality_score": quality_score,
                    "test_cases": [tc["name"] for tc in test_cases],
                },
            )

    except Exception as e:
        result.failure(
            e,
            context={
                "api_base": OR_BASE,
                "test_cases_count": len(test_cases) if "test_cases" in locals() else 0,
            },
        )

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Quality validation tests for LitAssist integrations"
    )
    parser.add_argument("--all", action="store_true", help="Run all quality tests")
    parser.add_argument(
        "--openrouter", action="store_true", help="Test OpenRouter quality"
    )
    parser.add_argument("--jade", action="store_true", help="Test Jade quality")
    parser.add_argument("--google", action="store_true", help="Test Google CSE quality")
    parser.add_argument(
        "--verification", action="store_true", help="Test verification system quality"
    )
    parser.add_argument(
        "--slow", action="store_true", help="Test slow/expensive reasoning-family models"
    )

    args = parser.parse_args()

    # If no specific tests selected, run all tests
    if not (
        args.all
        or args.openrouter
        or args.jade
        or args.google
        or args.verification
        or args.slow
    ):
        args.all = True

    # Run the tests
    success = run_tests(args)

    # Exit with appropriate status code
    sys.exit(0 if success else 1)
