"""Tests for litassist.citation.trust trusted-host validation.

URL trust checks across citation_context.py, google_cse.py and lookup
processors must use parsed-hostname equality, not substring matching against
the raw URL.
"""

import pytest

from litassist.citation.trust import is_trusted_legal_host


class TestIsTrustedLegalHost:
    @pytest.mark.parametrize(
        "url",
        [
            # Full URL on trusted host.
            "https://www.austlii.edu.au/au/cases/cth/HCA/1992/23.html",
            # Schemeless URL (urlparse used to put the host into the path).
            "austlii.edu.au/foo",
            # Subdomain of a trusted suffix.
            "https://classic.austlii.edu.au/au/legis/cth/consol_act/ma1958118/",
        ],
    )
    def test_trusted_hosts_are_accepted(self, url):
        assert is_trusted_legal_host(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            # Trusted-host substring inside an attacker hostname.
            "https://austlii.edu.au.attacker.invalid/case.html",
            # Trusted-host substring inside the path / query string.
            "https://attacker.com/austlii.edu.au/case.html",
            # Random .gov.au host that is not in the trusted set.
            "https://example.gov.au",
            # Empty input.
            "",
        ],
    )
    def test_attacker_or_unknown_hosts_are_rejected(self, url):
        assert is_trusted_legal_host(url) is False


pytestmark = [pytest.mark.unit, pytest.mark.offline]
