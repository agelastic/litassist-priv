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
            "https://www.austlii.edu.au/au/cases/cth/HCA/1992/23.html",
            "https://austlii.edu.au/foo",
            "https://classic.austlii.edu.au/au/legis/cth/consol_act/ma1958118/",
            "https://jade.io/article/12345",
            "https://www.legislation.gov.au/C2004A02562/2025-02-21/2025-02-21/text/original/pdf",
            "https://www.hcourt.gov.au/judgments/2023.html",
            "https://www.fedcourt.gov.au/digital-law-library/judgments/2023.html",
            # Schemeless URLs: urlparse used to treat these as paths and
            # return hostname=None, so a real trusted host was rejected.
            "austlii.edu.au/foo",
            "www.austlii.edu.au/au/cases/cth/HCA/1992/23.html",
            "//jade.io/article/12345",
            "legislation.gov.au",
        ],
    )
    def test_trusted_hosts_are_accepted(self, url):
        assert is_trusted_legal_host(url) is True

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.invalid/foo",
            "https://attacker.com/austlii.edu.au/case.html",
            "https://austlii.edu.au.attacker.invalid/case.html",
            "https://trusted.example.com.attacker.invalid/foo",
            "https://legislation.gov.au.evil.invalid/path",
            "https://jade.io.attacker.invalid/article",
            "https://www.gov.au.attacker.invalid/foo",
            "",
            "not-a-url",
            "https://example.gov.au",
        ],
    )
    def test_attacker_hosts_are_rejected(self, url):
        assert is_trusted_legal_host(url) is False, (
            f"Substring trust used to accept {url}; parsed-host check must reject."
        )

    def test_invalid_input_returns_false(self):
        assert is_trusted_legal_host(None) is False  # type: ignore[arg-type]


pytestmark = [pytest.mark.unit, pytest.mark.offline]
