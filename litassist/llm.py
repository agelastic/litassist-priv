"""
LLM Client for LitAssist.

This module provides a unified interface for chat completions across different LLM providers,
handling parameter management and response processing.
"""

import openai
import re
from typing import List, Dict, Any, Tuple

from litassist.utils import timed
from litassist.config import CONFIG
from litassist.citation_verify import (
    verify_all_citations,
    remove_citation_from_text,
    is_core_citation,
    CitationVerificationError,
)


class LLMClient:
    """
    Wrapper for LLM API calls with support for completions and self-verification.

    This class provides a unified interface for chat completions across different LLM
    providers, handling parameter management and response processing. It supports both
    creative (high temperature) and deterministic (low temperature) generation, as well
    as legal self-critique verification.

    Attributes:
        model: The model identifier to use for completions (e.g., 'openai/gpt-4o').
        default_params: Default parameters dictionary for completions.

    Example:
        ```python
        # Initialize client with default parameters
        client = LLMClient("anthropic/claude-3-sonnet", temperature=0.2, top_p=0.8)

        # Run a completion
        content, usage = client.complete([
            {"role": "system", "content": "Australian law only."},
            {"role": "user", "content": "Explain adverse possession."}
        ])

        # Optional verification
        if needs_verification:
            corrections = client.verify(content)
        ```
    """

    def __init__(self, model: str, **default_params):
        """
        Initialize an LLM client for chat completions.

        Args:
            model: The model name to use (e.g., 'openai/gpt-4o', 'anthropic/claude-3-sonnet').
            **default_params: Default decoding parameters (temperature, top_p, etc.) to use
                             for all completions unless overridden.
        """
        self.model = model
        self.command_context = None  # Track which command is using this client

        # Set model-specific token limits if enabled in config and not explicitly specified
        if CONFIG.use_token_limits and "max_tokens" not in default_params:
            # These limits are carefully chosen to balance comprehensive responses with quality
            if "google/gemini" in model.lower():
                default_params["max_tokens"] = (
                    2048  # Gemini - reliable up to this length
                )
            elif "anthropic/claude" in model.lower():
                default_params["max_tokens"] = (
                    4096  # Claude - coherent for longer outputs
                )
            elif "openai/gpt-4" in model.lower():
                default_params["max_tokens"] = (
                    3072  # GPT-4/o - balanced limit for precision
                )
            elif "grok" in model.lower():
                default_params["max_tokens"] = (
                    1536  # Grok - more prone to hallucination
                )
            else:
                default_params["max_tokens"] = 2048  # Default safe limit

        self.default_params = default_params

    @timed
    def complete(
        self, messages: List[Dict[str, str]], **overrides
    ) -> Tuple[str, Dict[str, Any]]:
        # Enforce Australian English in system prompts if not already specified
        has_system_message = any(msg.get("role") == "system" for msg in messages)
        if has_system_message:
            for msg in messages:
                if msg.get("role") == "system" and "Australian English" not in msg.get(
                    "content", ""
                ):
                    msg[
                        "content"
                    ] += "\nUse Australian English spellings and terminology."
        else:
            # Add system message if none exists
            messages.insert(
                0,
                {
                    "role": "system",
                    "content": "Use Australian English spellings and terminology.",
                },
            )
        """
        Run a single chat completion with the configured model.

        Args:
            messages: List of message dictionaries, each containing 'role' (system/user/assistant)
                     and 'content' (the message text).
            **overrides: Optional parameter overrides for this specific completion that will
                        take precedence over the default parameters.

        Returns:
            A tuple containing:
                - The generated text content (str)
                - The usage statistics dictionary (with prompt_tokens, completion_tokens, etc.)

        Raises:
            Exception: If the API call fails or returns an error.
        """
        # Merge default and override parameters
        params = {**self.default_params, **overrides}

        # Set API base based on model type
        original_api_base = openai.api_base
        original_api_key = openai.api_key

        # Determine the correct model name
        model_name = self.model

        # Use OpenRouter for non-OpenAI models
        if "/" in self.model and not self.model.startswith("openai/"):
            openai.api_base = CONFIG.or_base
            openai.api_key = CONFIG.or_key
        else:
            # Extract just the model name for OpenAI models
            if self.model.startswith("openai/"):
                model_name = self.model.replace("openai/", "")

        # Invoke the chat completion
        try:
            response = openai.ChatCompletion.create(
                model=model_name, messages=messages, **params
            )
        finally:
            # Restore original settings
            openai.api_base = original_api_base
            openai.api_key = original_api_key
        # Extract content and usage
        content = response.choices[0].message.content
        usage = getattr(response, "usage", {})

        # STRICT CITATION VERIFICATION - Block output with unverified citations
        try:
            verified_content, verification_issues = self.validate_and_verify_citations(
                content, strict_mode=True
            )

            # If we got here, all citations are verified or were safely removed
            if verification_issues:
                # Log what was cleaned but still proceed
                print(f"⚠️  Citation verification: {verification_issues[0]}")
                content = verified_content

        except CitationVerificationError as e:
            # Strict mode failed - attempt retry with enhanced prompt
            print(f"🚫 {str(e)}")
            print("🔄 Retrying with enhanced citation instructions...")

            # Enhance the last user message with strict citation instructions
            enhanced_messages = messages.copy()
            if enhanced_messages and enhanced_messages[-1].get("role") == "user":
                enhanced_messages[-1]["content"] += (
                    "\n\nIMPORTANT: Use only real, verifiable Australian cases that exist on AustLII. "
                    "Do not invent case names. If unsure about a citation, omit it rather than guess."
                )

            # Retry with enhanced prompt
            try:
                retry_response = openai.ChatCompletion.create(
                    model=model_name, messages=enhanced_messages, **params
                )
                retry_content = retry_response.choices[0].message.content
                retry_usage = getattr(retry_response, "usage", {})

                # Verify the retry
                verified_retry_content, retry_issues = (
                    self.validate_and_verify_citations(retry_content, strict_mode=True)
                )

                # If retry succeeded, use it
                content = verified_retry_content
                usage = retry_usage
                if retry_issues:
                    print(f"✅ Retry successful: {retry_issues[0]}")
                else:
                    print("✅ Retry successful: All citations verified")

            except CitationVerificationError as retry_error:
                # Both attempts failed - this is a critical error
                print(f"💥 Retry also failed: {str(retry_error)}")
                raise CitationVerificationError(
                    "CRITICAL: Multiple attempts to generate content with verified citations failed. "
                    "The AI model is consistently generating unverifiable legal citations. "
                    "Manual intervention required."
                )

        return content, usage

    @timed
    def verify(self, primary_text: str) -> str:
        """
        Run a self-critique pass to identify and correct legal inaccuracies in text.

        Uses the same model as the client instance but with deterministic settings
        (temperature=0, top_p=0.2) to minimize variability in verification.

        Args:
            primary_text: The text content to verify for legal accuracy.

        Returns:
            A string containing corrections to any legal inaccuracies found.

        Raises:
            Exception: If the verification API call fails.
        """
        critique_prompt = [
            {
                "role": "system",
                "content": "Australian law only. Use Australian English spellings and terminology (e.g., 'judgement' not 'judgment', 'defence' not 'defense').",
            },
            {
                "role": "user",
                "content": primary_text
                + "\n\nIdentify and correct any legal inaccuracies above, and provide the corrected text only. Ensure all spellings follow Australian English conventions.",
            },
        ]
        # Use deterministic settings for verification with appropriate token limits
        params = {"temperature": 0, "top_p": 0.2}

        # Add model-specific token limits for verification if enabled in config
        if CONFIG.use_token_limits and "max_tokens" not in params:
            if "google/gemini" in self.model.lower():
                params["max_tokens"] = 1024  # Concise verification for Gemini
            elif "anthropic/claude" in self.model.lower():
                params["max_tokens"] = 1536  # Claude verification
            elif "openai/gpt-4" in self.model.lower():
                params["max_tokens"] = 1024  # GPT-4 verification
            elif "grok" in self.model.lower():
                params["max_tokens"] = 800  # Tighter limit for Grok
            else:
                params["max_tokens"] = 1024  # Default verification limit

        # Set API base based on model type
        original_api_base = openai.api_base
        original_api_key = openai.api_key

        # Determine the correct model name
        model_name = self.model

        # Use OpenRouter for non-OpenAI models
        if "/" in self.model and not self.model.startswith("openai/"):
            openai.api_base = CONFIG.or_base
            openai.api_key = CONFIG.or_key
        else:
            # Extract just the model name for OpenAI models
            if self.model.startswith("openai/"):
                model_name = self.model.replace("openai/", "")

        # Invoke the verification
        try:
            response = openai.ChatCompletion.create(
                model=model_name, messages=critique_prompt, **params
            )
        finally:
            # Restore original settings
            openai.api_base = original_api_base
            openai.api_key = original_api_key
        return response.choices[0].message.content

    def validate_and_verify_citations(
        self, content: str, strict_mode: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Validate and verify citations with strict real-time checking.

        Args:
            content: Text content to validate and verify
            strict_mode: If True, raise CitationVerificationError on unverified citations

        Returns:
            Tuple of (cleaned_content, issues_list)

        Raises:
            CitationVerificationError: If strict_mode=True and unverified citations found
        """
        # First do real-time verification
        verified_citations, unverified_citations = verify_all_citations(content)

        if unverified_citations and strict_mode:
            # Build error message
            error_msg = "CRITICAL: Unverified citations detected:\n"
            for citation, reason in unverified_citations:
                error_msg += f"- {citation}: {reason}\n"
            error_msg += "\nCannot proceed. Remove these citations and try again."
            raise CitationVerificationError(error_msg)

        # If not strict mode or no unverified citations, clean up the content
        cleaned_content = content
        issues = []

        for citation, reason in unverified_citations:
            # Add to issues list
            issues.append(f"UNVERIFIED: {citation} - {reason}")

            # Remove the citation from content
            cleaned_content = remove_citation_from_text(cleaned_content, citation)

        if unverified_citations:
            issues.insert(
                0,
                f"CITATION VERIFICATION WARNING: {len(unverified_citations)} citations removed as unverified",
            )

        return cleaned_content, issues

    def should_auto_verify(self, content: str, command: str = None) -> bool:
        """
        Determine if content should be automatically verified based on risk factors.

        Args:
            content: The generated content to analyze
            command: The command that generated this content (optional)

        Returns:
            True if auto-verification should be triggered
        """
        # Always verify critical foundation commands
        if command in ["extractfacts", "strategy"]:
            return True

        # Auto-verify Grok outputs (prone to hallucination)
        if "grok" in self.model.lower():
            return True

        # Auto-verify when output contains high-risk content
        risk_patterns = [
            r"\[\d{4}\]\s+\w+\s+\d+",  # Case citations
            r"\d+%",  # Percentage claims
            r'"must"|"cannot"|"will"',  # Strong legal conclusions
            r"section\s+\d+",  # Statutory references
            r"rule\s+\d+",  # Court rules
            r"paragraph\s+\d+",  # Paragraph references
        ]

        for pattern in risk_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        return False

    def validate_citations(self, content: str, enable_online: bool = True) -> List[str]:
        """
        Enhanced validation of Australian legal citations with pattern detection and optional online verification.

        This method performs two phases of validation:
        1. Offline pattern detection (Phase 1) - Always runs
        2. Online AustLII verification (Phase 2) - Runs if enable_online=True

        Args:
            content: Text content to validate
            enable_online: Whether to perform online AustLII verification after offline checks

        Returns:
            List of potential citation issues found
        """
        issues = []

        # ── Phase 1: Enhanced Pattern Detection ──────────────────────────

        # First, identify all complete citations to exclude their case names from generic checking
        complete_citations = set()

        # Find traditional citations: (Year) Volume Series Page
        traditional_pattern = r"([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)\s+v\s+([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)\s+\(\d{4}\)\s+\d+\s+[A-Z]+\s+\d+"
        traditional_matches = re.findall(traditional_pattern, content)
        for party1, party2 in traditional_matches:
            complete_citations.add(f"{party1} v {party2}")

        # Find medium-neutral citations: Case Name [Year] Court Number
        medium_neutral_pattern = r"([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)\s+v\s+([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)\s+\[\d{4}\]\s+[A-Z]+\s+\d+"
        medium_neutral_matches = re.findall(medium_neutral_pattern, content)
        for party1, party2 in medium_neutral_matches:
            complete_citations.add(f"{party1} v {party2}")

        # 1. Generic/Common Name Detection (only for standalone case names)
        case_name_pattern = r"([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)\s+v\s+([A-Za-z\'\-]+(?:\s+[A-Za-z\'\-]+)*)"
        all_case_names = re.findall(case_name_pattern, content)

        # Filter out case names that are part of complete citations
        case_names = []
        for party1, party2 in all_case_names:
            case_name = f"{party1} v {party2}"
            if case_name not in complete_citations:
                case_names.append((party1, party2))

        # Common generic surnames that are often hallucinated
        generic_surnames = [
            "smith",
            "jones",
            "brown",
            "wilson",
            "taylor",
            "johnson",
            "white",
            "martin",
            "anderson",
            "thompson",
            "davis",
            "miller",
            "moore",
            "jackson",
            "harris",
            "clark",
            "lewis",
            "robinson",
            "walker",
        ]

        # Placeholder-like names
        placeholder_patterns = [
            r"^(test|example|sample|demo|person|party|entity|company)$",
            r"^[a-z]$",  # Single letters
            r"^(abc|xyz|123)$",  # Simple patterns
            r"^(plaintiff|defendant|applicant|respondent)$",  # Role names
            r"^(doe|roe)$",  # Legal placeholders
        ]

        for party1, party2 in case_names:
            p1_lower = party1.lower().strip()
            p2_lower = party2.lower().strip()

            # Check for generic surnames - flag if either party is too generic
            p1_words = p1_lower.split()
            p2_words = p2_lower.split()

            # Only flag if BOTH parties have very generic single-word surnames
            if (
                len(p1_words) == 1
                and p1_lower in generic_surnames
                and len(p2_words) == 1
                and p2_lower in generic_surnames
            ):
                issues.append(f"Suspiciously generic case name: {party1} v {party2}")

            # Check for placeholder patterns
            for pattern in placeholder_patterns:
                if re.match(pattern, p1_lower) or re.match(pattern, p2_lower):
                    issues.append(f"Placeholder-like case name: {party1} v {party2}")
                    break

            # Check for single letters or very short names
            if (len(p1_lower) <= 2 or len(p2_lower) <= 2) and not any(
                c in "'" for c in party1 + party2
            ):
                issues.append(f"Suspiciously short case name: {party1} v {party2}")

        # 2. Court Identifier Validation
        # Valid court abbreviations (Australian + historical UK/Privy Council)
        valid_courts = {
            # Australian courts
            "HCA": {
                "name": "High Court of Australia",
                "established": 1903,
                "max_per_year": 100,
            },
            "FCA": {
                "name": "Federal Court of Australia",
                "established": 1977,
                "max_per_year": 2000,
            },
            "FCAFC": {
                "name": "Full Federal Court",
                "established": 1977,
                "max_per_year": 500,
            },
            "FamCA": {
                "name": "Family Court of Australia",
                "established": 1976,
                "max_per_year": 1000,
            },
            "FamCAFC": {
                "name": "Full Family Court",
                "established": 1976,
                "max_per_year": 200,
            },
            "NSWSC": {
                "name": "NSW Supreme Court",
                "established": 1824,
                "max_per_year": 5000,
            },
            "NSWCA": {
                "name": "NSW Court of Appeal",
                "established": 1966,
                "max_per_year": 500,
            },
            "NSWCCA": {
                "name": "NSW Court of Criminal Appeal",
                "established": 1912,
                "max_per_year": 500,
            },
            "VSC": {
                "name": "Victorian Supreme Court",
                "established": 1852,
                "max_per_year": 3000,
            },
            "VSCA": {
                "name": "Victorian Court of Appeal",
                "established": 1995,
                "max_per_year": 300,
            },
            "QSC": {
                "name": "Queensland Supreme Court",
                "established": 1861,
                "max_per_year": 2000,
            },
            "QCA": {
                "name": "Queensland Court of Appeal",
                "established": 1991,
                "max_per_year": 300,
            },
            "SASC": {
                "name": "SA Supreme Court",
                "established": 1837,
                "max_per_year": 1000,
            },
            "SASCFC": {
                "name": "SA Full Court",
                "established": 1837,
                "max_per_year": 200,
            },
            "WASC": {
                "name": "WA Supreme Court",
                "established": 1861,
                "max_per_year": 1500,
            },
            "WASCA": {
                "name": "WA Court of Appeal",
                "established": 1969,
                "max_per_year": 200,
            },
            "TASSC": {
                "name": "Tasmanian Supreme Court",
                "established": 1824,
                "max_per_year": 500,
            },
            "ACTSC": {
                "name": "ACT Supreme Court",
                "established": 1934,
                "max_per_year": 500,
            },
            "NTSC": {
                "name": "NT Supreme Court",
                "established": 1911,
                "max_per_year": 300,
            },
            # UK/Privy Council courts (historically relevant to Australian law)
            "AC": {
                "name": "Appeal Cases (Privy Council)",
                "established": 1875,
                "max_per_year": 9999,  # No strict limit for historical citations
            },
            "PC": {
                "name": "Privy Council",
                "established": 1833,
                "max_per_year": 9999,
            },
            "WLR": {
                "name": "Weekly Law Reports",
                "established": 1953,
                "max_per_year": 9999,
            },
            "QB": {
                "name": "Queen's Bench",
                "established": 1875,
                "max_per_year": 9999,
            },
            "KB": {
                "name": "King's Bench",
                "established": 1875,
                "max_per_year": 9999,
            },
            "Ch": {
                "name": "Chancery",
                "established": 1875,
                "max_per_year": 9999,
            },
        }

        # Find medium-neutral citations
        citation_pattern = r"\[(\d{4})\]\s+([A-Z]+)\s+(\d+)"
        citations = re.findall(citation_pattern, content)

        for year_str, court, number_str in citations:
            year = int(year_str)
            number = int(number_str)
            citation = f"[{year}] {court} {number}"

            # Skip validation for traditional citation formats (handled by citation_verify.py)
            if court in ["AC", "PC", "WLR", "QB", "KB", "Ch"]:
                # These are legitimate UK/Privy Council citations - skip detailed validation
                continue

            # Check if court exists in valid courts
            if court not in valid_courts:
                issues.append(f"Unknown court abbreviation in citation: {citation}")
                continue

            court_info = valid_courts[court]

            # Check if court existed in that year
            if year < court_info["established"]:
                issues.append(
                    f"Anachronistic citation - {court_info['name']} established {court_info['established']}: {citation}"
                )

            # Check if citation number is reasonable
            if number > court_info["max_per_year"]:
                issues.append(
                    f"Suspiciously high citation number for {court}: {citation}"
                )

            # Check for future years
            if year > 2025:
                issues.append(f"Future year in citation: {citation}")

        # 3. Report Series Validation
        report_patterns = [
            (
                r"\((\d{4})\)\s+(\d+)\s+(CLR)\s+\d+",
                "CLR",
                1903,
            ),  # Commonwealth Law Reports
            (
                r"\((\d{4})\)\s+(\d+)\s+(ALR)\s+\d+",
                "ALR",
                1973,
            ),  # Australian Law Reports
            (
                r"\((\d{4})\)\s+(\d+)\s+(FCR)\s+\d+",
                "FCR",
                1984,
            ),  # Federal Court Reports
            (r"\((\d{4})\)\s+(\d+)\s+(FLR)\s+\d+", "FLR", 1976),  # Family Law Reports
            (r"\((\d{4})\)\s+(\d+)\s+(NSWLR)\s+\d+", "NSWLR", 1960),  # NSW Law Reports
            (r"\((\d{4})\)\s+(\d+)\s+(VR)\s+\d+", "VR", 1957),  # Victorian Reports
            (r"\((\d{4})\)\s+(\d+)\s+(QR)\s+\d+", "QR", 1958),  # Queensland Reports
            (r"\((\d{4})\)\s+(\d+)\s+(SASR)\s+\d+", "SASR", 1970),  # SA State Reports
            (r"\((\d{4})\)\s+(\d+)\s+(WAR)\s+\d+", "WAR", 1899),  # WA Reports
        ]

        for pattern, series_name, established_year in report_patterns:
            report_citations = re.findall(pattern, content)
            for year_str, volume, series in report_citations:
                year = int(year_str)
                if year < established_year:
                    issues.append(
                        f"Report series {series_name} not published in {year} (established {established_year})"
                    )

        # 4. Additional Validation Patterns
        # Check for impossible page numbers
        page_pattern = r"(?:at|,)\s+(\d+)(?:-\d+)?(?:\s|,|\.|\)|$)"
        pages = re.findall(page_pattern, content)
        for page_str in pages:
            page = int(page_str)
            if page > 9999:  # Suspiciously high page number
                issues.append(f"Suspiciously high page number: {page}")

        # Check for malformed parallel citations
        parallel_pattern = (
            r"(\[\d{4}\]\s+[A-Z]+\s+\d+)\s*[;,]\s*(\[\d{4}\]\s+[A-Z]+\s+\d+)"
        )
        parallel_cites = re.findall(parallel_pattern, content)
        for cite1, cite2 in parallel_cites:
            year1 = re.search(r"\[(\d{4})\]", cite1).group(1)
            year2 = re.search(r"\[(\d{4})\]", cite2).group(1)
            if year1 != year2:
                issues.append(
                    f"Parallel citations with different years: {cite1} and {cite2}"
                )

        # 5. Known Hallucination Patterns
        # AI often creates cases with these patterns
        hallucination_indicators = [
            r"Corporation\s+v\s+Corporation",  # Two corporations with generic names
            r"Pty\s+Ltd\s+v\s+Pty\s+Ltd",  # Two Pty Ltds without proper names
            r"The\s+Queen\s+v\s+[A-Z](?:\s|$)",  # Criminal cases with single letter defendants
            r"(?:Re|In\s+re)\s+[A-Z](?:\s|$)",  # In re cases with single letters
            r"Ex\s+parte\s+[A-Z](?:\s|$)",  # Ex parte with single letters
        ]

        for pattern in hallucination_indicators:
            if re.search(pattern, content):
                matches = re.findall(pattern, content)
                for match in matches:
                    issues.append(
                        f"Potential AI hallucination pattern: {match.strip()}"
                    )

        # Remove duplicates from issues list
        unique_issues = list(dict.fromkeys(issues))

        # ── Phase 2: Online AustLII Verification (if enabled) ────────────────
        if enable_online:
            # Perform online verification for ALL citations, not just those flagged offline
            # This catches citations that pass pattern checks but don't actually exist
            try:
                from litassist.citation_verify import extract_citations
                all_citations = extract_citations(content)
                
                if all_citations:
                    verified_citations, unverified_citations = verify_all_citations(content)
                    
                    # Add online verification results to issues
                    for citation, reason in unverified_citations:
                        # Check if this citation was already flagged by offline validation
                        already_flagged = any(citation in issue for issue in unique_issues)
                        if not already_flagged:
                            # Distinguish between different types of online failures
                            if "Unknown court" in reason:
                                unique_issues.append(f"COURT NOT RECOGNIZED: {citation} - {reason}")
                            elif "Not found on AustLII" in reason:
                                unique_issues.append(f"CITATION NOT FOUND: {citation} - {reason}")
                            else:
                                unique_issues.append(f"ONLINE VERIFICATION FAILED: {citation} - {reason}")
                    
                    # Add summary of online verification if issues found
                    if unverified_citations:
                        online_only_issues = len([c for c, r in unverified_citations if not any(c in issue for issue in unique_issues[:len(issues)])])
                        if online_only_issues > 0:
                            unique_issues.append(f"AustLII check: {online_only_issues} citations not found in database")
            except Exception as e:
                # If online verification fails, just note it and continue
                unique_issues.append(f"Online verification unavailable: {str(e)}")

        # Add summary assessment if significant issues found
        if len(unique_issues) > 0:
            severity = (
                "high"
                if len(unique_issues) > 5
                else "medium" if len(unique_issues) > 2 else "low"
            )
            unique_issues.insert(
                0,
                f"CITATION RELIABILITY WARNING ({severity} risk): {len(unique_issues)} potential issues detected. Manual verification strongly recommended.",
            )

        return unique_issues

    def verify_with_level(self, primary_text: str, level: str = "medium") -> str:
        """
        Run verification with different depth levels.

        Args:
            primary_text: Text to verify
            level: Verification depth - "light", "medium", or "heavy"

        Returns:
            Verification feedback
        """
        if level == "light":
            # Just check Australian English compliance
            critique_prompt = [
                {
                    "role": "system",
                    "content": "Check only for Australian English spelling and terminology compliance.",
                },
                {
                    "role": "user",
                    "content": primary_text
                    + "\n\nCorrect any non-Australian English spellings or terminology.",
                },
            ]
        elif level == "heavy":
            # Full legal accuracy and citation check
            critique_prompt = [
                {
                    "role": "system",
                    "content": "Australian law expert. Thoroughly verify legal accuracy, citations, precedents, and reasoning.",
                },
                {
                    "role": "user",
                    "content": primary_text
                    + "\n\nProvide comprehensive legal accuracy review: verify all citations, check legal reasoning, identify any errors in law or procedure, and ensure Australian English compliance.",
                },
            ]
        else:  # medium (default)
            # Standard verification
            return self.verify(primary_text)

        # Use same verification logic with custom prompts
        params = {"temperature": 0, "top_p": 0.2}

        if CONFIG.use_token_limits:
            if "google/gemini" in self.model.lower():
                params["max_tokens"] = 1024
            elif "anthropic/claude" in self.model.lower():
                params["max_tokens"] = 1536 if level == "heavy" else 1024
            elif "openai/gpt-4" in self.model.lower():
                params["max_tokens"] = 1024
            elif "grok" in self.model.lower():
                params["max_tokens"] = 800
            else:
                params["max_tokens"] = 1024

        # Execute verification
        original_api_base = openai.api_base
        original_api_key = openai.api_key
        model_name = self.model

        if "/" in self.model and not self.model.startswith("openai/"):
            openai.api_base = CONFIG.or_base
            openai.api_key = CONFIG.or_key
        else:
            if self.model.startswith("openai/"):
                model_name = self.model.replace("openai/", "")

        try:
            response = openai.ChatCompletion.create(
                model=model_name, messages=critique_prompt, **params
            )
        finally:
            openai.api_base = original_api_base
            openai.api_key = original_api_key

        return response.choices[0].message.content
