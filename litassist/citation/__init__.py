"""
Citation verification package.

This package provides comprehensive citation verification against Australian legal
databases, including Jade.io and AustLII, with support for UK/International citations
and legislation references.

Re-exports all public APIs for backward compatibility with code that previously
imported from litassist.citation_verify.
"""

# Exception classes
from .exceptions import (
    CitationVerificationError,
    TestVerificationError,
    in_test_mode,
)

# Cache management
from .cache import (
    _citation_cache,
    _cache_lock,
    get_verification_stats,
    clear_verification_cache,
)

# Legislation and normalization
from .legislation import (
    normalize_citation,
    is_legislation_reference,
    check_international_citation,
)

# AustLII verification
from .austlii import (
    construct_austlii_url,
    verify_via_austlii_direct,
    is_traditional_citation_format,
)

# Google CSE verification
from .google_cse import (
    search_legal_database_via_cse,
    search_jade_via_google_cse,
)

# Main verification functions
from .verify import (
    verify_single_citation,
    verify_all_citations,
    remove_citation_from_text,
    is_core_citation,
)

# Constants (for advanced use)
from .constants import (
    COURT_MAPPINGS,
    UK_INTERNATIONAL_COURTS,
    HARDCODED_FOIA_FILES,
    PROJECT_ROOT,
)

__all__ = [
    # Exceptions
    "CitationVerificationError",
    "TestVerificationError",
    "in_test_mode",
    # Cache
    "_citation_cache",
    "_cache_lock",
    "get_verification_stats",
    "clear_verification_cache",
    # Legislation
    "normalize_citation",
    "is_legislation_reference",
    "check_international_citation",
    # AustLII
    "construct_austlii_url",
    "verify_via_austlii_direct",
    "is_traditional_citation_format",
    # Google CSE
    "search_legal_database_via_cse",
    "search_jade_via_google_cse",
    # Main verification
    "verify_single_citation",
    "verify_all_citations",
    "remove_citation_from_text",
    "is_core_citation",
    # Constants
    "COURT_MAPPINGS",
    "UK_INTERNATIONAL_COURTS",
    "HARDCODED_FOIA_FILES",
    "PROJECT_ROOT",
]
