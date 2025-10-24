"""
LLM Verification Module for LitAssist.

This module provides verification and citation validation functionality for LLM-generated content,
ensuring legal accuracy and citation integrity in Australian legal contexts.
"""

import re
from typing import List, Tuple

from litassist.timing import timed
from litassist.utils.core import heartbeat
from litassist.utils.formatting import warning_message
from litassist.config import get_config
from litassist.prompts import PROMPTS
from litassist.citation.verify import (
    verify_all_citations,
    remove_citation_from_text,
)
from litassist.citation.exceptions import CitationVerificationError


class LLMVerificationMixin:
    """
    Mixin class providing verification and citation validation functionality for LLM clients.

    This mixin provides methods for:
    - Content verification and self-critique
    - Citation validation and verification
    - Risk-based auto-verification logic
    - Multi-level verification depth control

    Designed to be mixed into LLMClient instances to add verification capabilities.
    """

    @heartbeat()
    @timed
    def verify(
        self,
        primary_text: str,
        citation_context: str = None,
        reasoning_context: str = None,
    ) -> Tuple[str, str]:
        """
        Run a self-critique pass to identify and correct legal inaccuracies in text.

        Uses the same model as the client instance but with deterministic settings
        (temperature=0, top_p=0.2) to minimize variability in verification.

        Args:
            primary_text: The text content to verify for legal accuracy.
            citation_context: Optional citation verification report to inform analysis.
            reasoning_context: Optional reasoning trace analysis to inform verification.

        Returns:
            Tuple of (corrections to any legal inaccuracies found, model name used for verification).

        Raises:
            Exception: If the verification API call fails.
        """
        # Use prompts from centralized system - no fallbacks allowed
        base_prompt = PROMPTS.get("verification.base_prompt")
        # Select appropriate critique prompt based on available context
        if citation_context and reasoning_context:
            # Both contexts available - use comprehensive soundness check
            self_critique = PROMPTS.get("verification.soundness_with_context")
        else:
            # Standard verification
            self_critique = PROMPTS.get("verification.self_critique")

        # Build the full text with optional verification contexts using === separators
        full_text = primary_text
        if citation_context:
            full_text += "\n\n# Previous Verification: Citations\n\n" + citation_context
        if reasoning_context:
            full_text += (
                "\n\n# Previous Verification: Reasoning Analysis\n\n"
                + reasoning_context
            )

        critique_prompt = [
            {
                "role": "system",
                "content": base_prompt,
            },
            {
                "role": "user",
                "content": full_text + "\n\n" + self_critique,
            },
        ]
        # Let the factory configuration handle all parameters
        params = {}
        verification_result, usage = self.complete(
            critique_prompt, skip_citation_verification=True, **params
        )
        return verification_result, self.model

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
        issues = []

        # Optionally perform offline pattern validation if enabled in config
        config = get_config()
        if config.offline_validation:
            pattern_issues = self.validate_citations(content, enable_online=False)
            if pattern_issues:
                issues.extend(pattern_issues)
                print(
                    warning_message(
                        f"Offline validation found {len(pattern_issues)} potential issues"
                    )
                )

        # Always do real-time online database verification
        _, unverified_citations = verify_all_citations(content)

        if unverified_citations and strict_mode:
            # Categorize issues for better error messages
            format_errors = []
            existence_errors = []
            verification_errors = []

            for citation, reason in unverified_citations:
                # Don't block for offline validation warnings - treat as warnings only
                if "OFFLINE VALIDATION ONLY" in reason:
                    continue  # Skip - these are warnings, not errors
                elif "format" in reason.lower() and "not found" not in reason.lower():
                    format_errors.append((citation, reason))
                elif (
                    "not found" in reason.lower() or "case not found" in reason.lower()
                ):
                    existence_errors.append((citation, reason))
                else:
                    verification_errors.append((citation, reason))

            # Only raise error if there are actual blocking issues
            blocking_errors = format_errors + existence_errors + verification_errors

            if blocking_errors:
                # Build categorized error message using templates
                categorized_issues = ""

                try:
                    if existence_errors:
                        categorized_issues += (
                            PROMPTS.get("warnings.citation_not_found_header") + "\n"
                        )
                        for citation, reason in existence_errors:
                            categorized_issues += (
                                PROMPTS.get(
                                    "warnings.citation_error_item",
                                    citation=citation,
                                    reason=reason,
                                )
                                + "\n"
                            )
                        categorized_issues += "\n"

                    if format_errors:
                        categorized_issues += (
                            PROMPTS.get("warnings.citation_format_issues_header") + "\n"
                        )
                        for citation, reason in format_errors:
                            categorized_issues += (
                                PROMPTS.get(
                                    "warnings.citation_error_item",
                                    citation=citation,
                                    reason=reason,
                                )
                                + "\n"
                            )
                        categorized_issues += "\n"

                    if verification_errors:
                        categorized_issues += (
                            PROMPTS.get(
                                "warnings.citation_verification_problems_header"
                            )
                            + "\n"
                        )
                        for citation, reason in verification_errors:
                            categorized_issues += (
                                PROMPTS.get(
                                    "warnings.citation_error_item",
                                    citation=citation,
                                    reason=reason,
                                )
                                + "\n"
                            )
                        categorized_issues += "\n"

                    error_msg = PROMPTS.get(
                        "warnings.citation_verification_failed",
                        categorized_issues=categorized_issues.rstrip(),
                    )

                except (KeyError, ValueError):
                    # Fallback to hardcoded if templates not available
                    error_msg = "[CRITICAL] Citation verification failed:\n\n"

                    if existence_errors:
                        error_msg += "[NOT FOUND] CASES NOT FOUND IN DATABASE:\n"
                        for citation, reason in existence_errors:
                            error_msg += f"   • {citation}\n     -> {reason}\n"
                        error_msg += "\n"

                    if format_errors:
                        error_msg += "[WARNING] CITATION FORMAT ISSUES:\n"
                        for citation, reason in format_errors:
                            error_msg += f"   • {citation}\n     -> {reason}\n"
                        error_msg += "\n"

                    if verification_errors:
                        error_msg += "[VERIFICATION] VERIFICATION PROBLEMS:\n"
                        for citation, reason in verification_errors:
                            error_msg += f"   • {citation}\n     -> {reason}\n"
                        error_msg += "\n"

                    error_msg += "[ACTION REQUIRED] These citations appear to be AI hallucinations.\n"
                    error_msg += "   Remove these citations and regenerate, or verify them independently."

                raise CitationVerificationError(error_msg)

        # If not strict mode or no unverified citations, clean up the content
        cleaned_content = content

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
        # Check if factory has set force verification
        if hasattr(self, "_enforce_citations") and self._enforce_citations:
            return True

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
        Validate citations using pattern-based checking.

        Delegates to citation_patterns module for the actual validation logic.

        Args:
            content: Text content to validate
            enable_online: Whether to perform online database verification after offline checks

        Returns:
            List of potential citation issues found
        """
        from litassist.citation_patterns import validate_citation_patterns

        return validate_citation_patterns(content, enable_online)

    def verify_with_level(
        self, primary_text: str, level: str = "medium"
    ) -> Tuple[str, str]:
        """
        Run verification with different depth levels.

        Args:
            primary_text: Text to verify
            level: Verification depth - "light" (spelling only) or "heavy" (comprehensive)
                  Any other value defaults to standard verification

        Returns:
            Tuple of (verification feedback, model name used for verification)
        """
        if level == "light":
            # Just check Australian English compliance
            try:
                light_verification = PROMPTS.get("verification.light_verification")
            except KeyError:
                light_verification = "Check only for Australian English spelling and terminology compliance.\n\nCorrect any non-Australian English spellings or terminology."

            critique_prompt = [
                {
                    "role": "system",
                    "content": light_verification.split("\n\n")[0],
                },
                {
                    "role": "user",
                    "content": primary_text
                    + "\n\n"
                    + light_verification.split("\n\n")[-1],
                },
            ]
        elif level == "heavy":
            # Full legal accuracy and citation check - no fallbacks allowed
            system_prompt = PROMPTS.get("verification.heavy_verification_system")
            heavy_verification = PROMPTS.get("verification.heavy_verification")

            critique_prompt = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": primary_text + "\n\n" + heavy_verification,
                },
            ]
        else:
            # For any other level, use standard verification
            # This maintains backward compatibility
            return self.verify(primary_text)

        # Use the appropriate verification model based on level
        from litassist.llm.factory import LLMClientFactory

        if level == "light":
            verification_client = LLMClientFactory.for_command("verification-light")
        elif level == "heavy":
            verification_client = LLMClientFactory.for_command("verification-heavy")
        else:
            verification_client = LLMClientFactory.for_command("verification")
        
        # Let the factory configuration handle all parameters
        params = {}
        verification_result, usage = verification_client.complete(
            critique_prompt, skip_citation_verification=True, **params
        )
        return verification_result, verification_client.model


class LLMVerificationClient:
    """
    Standalone verification client for content verification without requiring a full LLM client.

    This class provides verification capabilities that can be used independently,
    useful for verification-only operations or when you need verification functionality
    without the full LLM client overhead.
    """

    def __init__(self, model: str = "anthropic/claude-opus-4.1", **params):
        """
        Initialize a verification-specific LLM client.

        Args:
            model: The model to use for verification (defaults to Opus for accuracy)
            **params: Additional parameters for the verification model
        """
        from litassist.llm.client import LLMClient

        # Create a lightweight LLM client configured for verification
        verification_params = {"temperature": 0, "top_p": 0.2, **params}

        self.client = LLMClient(model, **verification_params)

        # Apply the verification mixin
        self.client.__class__ = type(
            "LLMClientWithVerification",
            (self.client.__class__, LLMVerificationMixin),
            {},
        )

    def verify_content(
        self, content: str, citation_context: str = None, reasoning_context: str = None
    ) -> Tuple[str, str]:
        """
        Verify content for legal accuracy and correctness.

        Args:
            content: The content to verify
            citation_context: Optional citation verification context
            reasoning_context: Optional reasoning analysis context

        Returns:
            Tuple of (verification feedback, model name used)
        """
        return self.client.verify(content, citation_context, reasoning_context)

    def verify_citations(
        self, content: str, strict_mode: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Verify and validate citations in content.

        Args:
            content: Content to verify citations for
            strict_mode: Whether to use strict verification mode

        Returns:
            Tuple of (cleaned content, list of issues)
        """
        return self.client.validate_and_verify_citations(content, strict_mode)

    def assess_verification_need(self, content: str, command: str = None) -> bool:
        """
        Assess whether content needs verification based on risk factors.

        Args:
            content: Content to assess
            command: Command that generated the content

        Returns:
            True if verification is recommended
        """
        return self.client.should_auto_verify(content, command)

    def verify_with_depth(self, content: str, level: str = "medium") -> Tuple[str, str]:
        """
        Verify content with specified depth level.

        Args:
            content: Content to verify
            level: Verification level ("light", "medium", "heavy")

        Returns:
            Tuple of (verification feedback, model name used)
        """
        return self.client.verify_with_level(content, level)
