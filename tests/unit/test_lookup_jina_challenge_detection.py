"""
Tests for Jina challenge-page detection in litassist.commands.lookup.fetchers.

When AustLII (or any Cloudflare-protected site) blocks Jina's fetch, Jina
returns the bot-challenge HTML as a successful HTTP 200. Without detection,
that ~900-char interstitial would flow downstream to the LLM as if it were
the requested legal document. The detector rejects such responses.
"""

from litassist.commands.lookup.fetchers import (
    _looks_like_challenge_page,
    _JINA_MIN_USEFUL_CHARS,
)


# Captured from a real fetch_attempt audit log entry produced by AustLII +
# Cloudflare in the field.
_REAL_CLOUDFLARE_INTERSTITIAL = """[Source: https://www.austlii.edu.au/cgi-bin/viewdoc/au/legis/cth/num_act/ca1989172/]

Title: Just a moment...

URL Source: https://www.austlii.edu.au/cgi-bin/viewdoc/au/legis/cth/num_act/ca1989172/

Warning: Target URL returned error 403: Forbidden
Warning: This page maybe requiring CAPTCHA, please make sure you are authorized to access this page.

Markdown Content:
# Just a moment...

# www.austlii.edu.au

## Performing security verification

This website uses a security service to protect against malicious bots. This page is displayed while the website verifies you are not a bot.

## Verification successful. Waiting for www.austlii.edu.au to respond

Ray ID: a0148cfadb4eca15

Performance and Security by Cloudflare
"""


class TestChallengeDetection:
    def test_real_cloudflare_interstitial_rejected(self):
        reason = _looks_like_challenge_page(_REAL_CLOUDFLARE_INTERSTITIAL)
        assert reason, "Real Cloudflare interstitial must be flagged as a challenge page"

    def test_empty_body_rejected(self):
        assert _looks_like_challenge_page("") == "empty body"

    def test_short_body_rejected_as_too_short(self):
        text = "x" * 100
        reason = _looks_like_challenge_page(text)
        assert reason.startswith("too short")

    def test_long_legitimate_content_accepted(self):
        # Plausible legal-document text well over the threshold and without any
        # challenge markers.
        body = (
            "Section 1 - Definitions. In this Act, unless the contrary intention "
            "appears, 'electronic communication' means a communication of "
            "information in the form of data, text or images by means of guided "
            "or unguided electromagnetic energy. Section 2 - Application... "
        ) * 50
        assert len(body) >= _JINA_MIN_USEFUL_CHARS
        assert _looks_like_challenge_page(body) == ""

    def test_captcha_marker_in_otherwise_long_body_rejected(self):
        body = "lorem ipsum " * 500  # long enough to clear the size threshold
        body += "\nPlease complete the CAPTCHA to continue.\n"
        body += "lorem ipsum " * 200
        assert len(body) >= _JINA_MIN_USEFUL_CHARS
        assert _looks_like_challenge_page(body), (
            "CAPTCHA marker must override the size threshold"
        )

    def test_marker_matching_is_case_insensitive(self):
        body = "JUST A MOMENT...\n" + ("padding text " * 200)
        assert _looks_like_challenge_page(body), "Markers must match case-insensitively"

    def test_target_url_error_marker_rejected(self):
        body = "Warning: Target URL returned error 403: Forbidden\n" + (
            "x" * (_JINA_MIN_USEFUL_CHARS + 100)
        )
        reason = _looks_like_challenge_page(body)
        assert reason and "error 403" in reason.lower()
