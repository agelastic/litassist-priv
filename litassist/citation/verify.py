"""
Main citation verification orchestration.

This module provides the primary functions for verifying citations against
Australian legal databases, coordinating between different verification strategies
and managing the verification workflow.
"""

import re
import time
from typing import List, Tuple

from litassist.timing import timed
from litassist.logging import save_log
from litassist.config import get_config
from litassist.citation_patterns import extract_citations, validate_citation_patterns

from .constants import HARDCODED_FOIA_FILES
from .legislation import normalize_citation, is_legislation_reference, check_international_citation
from .google_cse import search_legal_database_via_cse
from .austlii import verify_via_austlii_direct, is_traditional_citation_format
from .cache import get_from_cache, add_to_cache


@timed
def verify_single_citation(citation: str) -> Tuple[bool, str, str]:
    """
    Verify a single citation against available databases.

    Args:
        citation: Citation to verify

    Returns:
        Tuple of (exists, url, reason) where reason explains failure if any
    """
    # Normalize first
    normalized = normalize_citation(citation)

    # Check cache first
    cached = get_from_cache(normalized)
    if cached:
        return cached["exists"], cached.get("url", ""), cached.get("reason", "")

    # Check for hardcoded FOIA citations first
    if normalized in HARDCODED_FOIA_FILES:
        file_path = HARDCODED_FOIA_FILES[normalized]
        add_to_cache(
            normalized,
            exists=True,
            url=file_path,
            reason="FOIA citation - using pre-downloaded local file",
        )
        return True, file_path, "FOIA citation - using pre-downloaded local file"

    # Check for UK/International citations first (these are valid but not Australian)
    international_reason = check_international_citation(normalized)
    if international_reason:
        add_to_cache(
            normalized,
            exists=True,  # Valid but not Australian
            url="",
            reason=international_reason,
        )
        return True, "", international_reason

    # Skip verification for legislation - Acts and Regulations aren't in case law databases
    if is_legislation_reference(normalized):
        add_to_cache(
            normalized,
            exists=True,  # Legislation is assumed valid
            url="",
            reason="Legislation reference - verification skipped",
        )
        return True, "", "Legislation reference - verification skipped"

    # Check for format issues using offline validation
    format_issues = validate_citation_patterns(normalized, enable_online=False)
    if format_issues:
        # Format validation found problems - invalid citation format
        add_to_cache(
            normalized,
            exists=False,
            url="",
            reason=f"Invalid citation format: {format_issues[0]}",
        )
        return False, "", f"Invalid citation format: {format_issues[0]}"

    # Primary verification: Use Jade.io via Google CSE for ALL citations
    config = get_config()

    try:
        # Try Jade.io CSE first (primary source)
        exists_in_jade, url_jade = search_legal_database_via_cse(
            normalized, cse_id=config.cse_id, cse_name="Jade.io", timeout=5
        )
        if exists_in_jade:
            reason = "Verified via Jade.io CSE"
            add_to_cache(normalized, exists=True, url=url_jade, reason=reason)
            return True, url_jade, reason

        # Fallback to comprehensive CSE if configured and Jade didn't find it
        if hasattr(config, "cse_id_comprehensive") and config.cse_id_comprehensive:
            exists_in_comprehensive, url_comp = search_legal_database_via_cse(
                normalized,
                cse_id=config.cse_id_comprehensive,
                cse_name="Comprehensive legal sources",
                timeout=5,
            )
            if exists_in_comprehensive:
                reason = "Verified via comprehensive legal sources CSE"
                add_to_cache(normalized, exists=True, url=url_comp, reason=reason)
                return True, url_comp, reason

        # Final fallback to AustLII CSE if configured
        if hasattr(config, "cse_id_austlii") and config.cse_id_austlii:
            exists_in_austlii, url_austlii = search_legal_database_via_cse(
                normalized, cse_id=config.cse_id_austlii, cse_name="AustLII", timeout=5
            )
            if exists_in_austlii:
                reason = "Verified via AustLII CSE"
                add_to_cache(normalized, exists=True, url=url_austlii, reason=reason)
                return True, url_austlii, reason

        # NEW: Final fallback - try direct AustLII URL construction
        # Only attempt for Australian medium neutral citations
        if re.match(r"\[(\d{4})\]\s+([A-Z]+[A-Za-z]*)\s+(\d+)", normalized):
            exists_via_austlii, url_austlii, reason_austlii = verify_via_austlii_direct(
                normalized, timeout=5
            )
            if exists_via_austlii:
                add_to_cache(
                    normalized, exists=True, url=url_austlii, reason=reason_austlii
                )
                return True, url_austlii, reason_austlii

    except Exception:
        pass  # Fall through to mark as unverified

    # If all verification attempts fail, mark as UNVERIFIED
    reason = "Citation not found in online databases"
    add_to_cache(normalized, exists=False, url="", reason=reason)
    return False, "", reason


@timed
def verify_all_citations(text: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Verify all citations in text content.

    Args:
        text: Text content containing citations

    Returns:
        Tuple of (verified_citations, unverified_citations_with_reasons)
    """
    start_time = time.time()
    citations = extract_citations(text)
    verified = []
    unverified = []

    # Enhanced logging to capture full details for audit
    detailed_results = []

    for citation in citations:
        exists, url, reason = verify_single_citation(citation)

        # Capture full details for logging
        citation_detail = {
            "citation": citation,
            "verified": exists,
            "url": url if url else None,
            "reason": reason if reason else None,
            "is_traditional": is_traditional_citation_format(citation),
            "is_international": (
                "UK/International citation" in reason if reason else False
            ),
        }
        detailed_results.append(citation_detail)

        if exists:
            verified.append(citation)
        else:
            unverified.append((citation, reason))

    # Enhanced logging with full citation details
    log_data = {
        "method": "verify_all_citations",
        "input_text_length": len(text),
        "citations_found": len(citations),
        "citations_verified": len(verified),
        "citations_unverified": len(unverified),
        "verified_citations": verified,
        "unverified_citations": [
            {"citation": cit, "reason": reason} for cit, reason in unverified
        ],
        "detailed_results": detailed_results,
        "international_citations": [
            d for d in detailed_results if d.get("is_international", False)
        ],
        "traditional_citations": [
            d for d in detailed_results if d.get("is_traditional", False)
        ],
        "processing_time_ms": round((time.time() - start_time) * 1000, 2),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Log the overall verification session
    save_log("citation_verification_session", log_data)

    return verified, unverified


def remove_citation_from_text(text: str, citation: str) -> str:
    """
    Surgically remove a citation from text while preserving readability.

    Args:
        text: Original text
        citation: Citation to remove

    Returns:
        Text with citation removed and cleaned up
    """
    # Escape special regex characters in citation
    escaped_citation = re.escape(citation)

    # Pattern to match citation with surrounding context
    patterns = [
        # Pattern 1: "as held in [citation]"
        rf"\s+as\s+(?:held|established|decided|ruled)\s+in\s+{escaped_citation}",
        # Pattern 2: "([citation])"
        rf"\s*\(\s*{escaped_citation}\s*\)",
        # Pattern 3: "— [citation]"
        rf"\s*[—–-]\s*\*?{escaped_citation}\*?",
        # Pattern 4: "; [citation]"
        rf"\s*;\s*{escaped_citation}",
        # Pattern 5: ", [citation]"
        rf"\s*,\s*{escaped_citation}",
        # Pattern 6: Just the citation itself
        rf"\s*{escaped_citation}",
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            # Remove the pattern
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            break

    # Clean up any double spaces or awkward punctuation
    text = re.sub(r"[ \t]+", " ", text)  # Only collapse spaces/tabs, preserve newlines
    text = re.sub(r"\s*\.\s*\.", ".", text)  # Remove double periods
    text = re.sub(r"\s+,", ",", text)  # Fix spacing before commas
    text = re.sub(r"\s+\.", ".", text)  # Fix spacing before periods

    return text.strip()


def is_core_citation(text_section: str, citation: str) -> bool:
    """
    Determine if a citation is core to a text section or just supporting.

    Args:
        text_section: Section of text containing the citation
        citation: The citation to evaluate

    Returns:
        True if citation appears to be core/essential to the argument
    """
    # Look for the citation in the text
    citation_pos = text_section.find(citation)
    if citation_pos == -1:
        return False

    # Check if it's in the first sentence (usually indicates core importance)
    first_sentence_end = text_section.find(".")
    if first_sentence_end != -1 and citation_pos < first_sentence_end:
        return True

    # Check if it's the only citation in this section
    all_citations = extract_citations(text_section)
    if len(all_citations) == 1:
        return True

    # Check for key phrases that indicate core citation
    text_before_citation = text_section[:citation_pos].lower()
    core_indicators = [
        "established in",
        "held in",
        "decided in",
        "per",
        "in the leading case",
        "landmark case",
        "seminal case",
    ]

    for indicator in core_indicators:
        if (
            indicator in text_before_citation[-50:]
        ):  # Check last 50 chars before citation
            return True

    return False
