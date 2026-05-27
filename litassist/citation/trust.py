"""Trusted-host validation for legal-database verification.

Centralised so citation_context.py, google_cse.py, lookup processors, and
fetchers all use one parsed-hostname trust check instead of vulnerable
substring matching against arbitrary URLs.
"""

from urllib.parse import urlparse


# Authoritative sources for Australian legal citations. Matched as the full
# hostname or a `.suffix` subdomain — never as a substring of an arbitrary URL.
TRUSTED_LEGAL_HOSTS = frozenset(
    {
        "austlii.edu.au",
        "jade.io",
        "legislation.gov.au",
        "hcourt.gov.au",
        "fedcourt.gov.au",
        "ag.gov.au",
    }
)


def is_trusted_legal_host(url: str) -> bool:
    """Return True when ``url``'s parsed hostname is a trusted legal source.

    Uses full-host or registered-suffix equality, NOT substring matching, so
    attacker hostnames like ``austlii.edu.au.evil.invalid`` or
    ``evil.example.com/path?ref=austlii.edu.au`` are rejected.
    """
    if not url:
        return False
    try:
        host = (urlparse(url).hostname or "").lower()
    except (ValueError, AttributeError):
        return False
    if not host:
        return False
    return any(
        host == suffix or host.endswith("." + suffix) for suffix in TRUSTED_LEGAL_HOSTS
    )
