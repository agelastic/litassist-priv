"""
Tests for the Cloudflare/SPA detectors in litassist.commands.lookup.fetchers.

Pins production-critical behaviour:
- Real Cloudflare interstitial is flagged as a challenge
- Legitimate long content passes through unchanged
- reCAPTCHA-widget-bearing pages (e.g. fedcourt) are NOT false-positive
  flagged as Cloudflare challenges (regression for 26/05/2026)
- SPA-shell detector fires via both arms (marker-based, ratio-based)
- Substantive rendered content with framework markers is accepted
"""

from litassist.commands.lookup.fetchers import (
    _looks_like_challenge_page,
    _JINA_MIN_USEFUL_CHARS,
    _looks_like_spa_shell,
    _SPA_MIN_TEXT_LENGTH,
    _SPA_MIN_HTML_LENGTH,
    _SPA_TEXT_RATIO_THRESHOLD,
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

    def test_long_legitimate_content_accepted(self):
        body = (
            "Section 1 - Definitions. In this Act, unless the contrary intention "
            "appears, 'electronic communication' means a communication of "
            "information in the form of data, text or images by means of guided "
            "or unguided electromagnetic energy. Section 2 - Application... "
        ) * 50
        assert len(body) >= _JINA_MIN_USEFUL_CHARS
        assert _looks_like_challenge_page(body) == ""

    def test_recaptcha_widget_in_legitimate_page_not_rejected(self):
        """Regression for 26/05/2026: fedcourt.gov.au practice-note pages embed
        a Google reCAPTCHA widget. The bare 'captcha' substring used to fire
        the detector on real content; the marker has been narrowed."""
        real_prose = (
            "Section 1. Commercial Arbitration Practice Note. "
            "This practice note sets out the procedures to be followed. "
        ) * 100
        body = (
            f"<html><body><h1>Commercial Arbitration Practice Note</h1>"
            f"<p>{real_prose}</p>"
            "<div class='footer'>"
            "<p>* This online submission is protected by captcha</p>"
            "<script src='https://www.google.com/recaptcha/api.js'></script>"
            "<div class='g-recaptcha' data-sitekey='abc123'></div>"
            "</div></body></html>"
        )
        assert _looks_like_challenge_page(body) == "", (
            "Legitimate page with reCAPTCHA widget must NOT be flagged"
        )


class TestSpaShellDetection:
    def test_angular_shell_with_short_text_rejected(self):
        """SPA marker arm: framework marker present and extracted text small."""
        raw_html = (
            "<!doctype html><html><head><title>Jade</title></head>"
            "<body><app-root></app-root>"
            "<script src='main.js'></script>"
            "<script>var x=1;</script>"
            "</body></html>"
        )
        extracted = "Jade"
        reason = _looks_like_spa_shell(raw_html, extracted)
        assert reason and "<app-root" in reason

    def test_legitimate_prose_accepted(self):
        """SPA pass-through: substantial extracted text passes the marker arm."""
        prose = (
            "Section 1 - Definitions. In this Act, unless the contrary intention "
            "appears, 'electronic communication' means a communication of "
            "information in the form of data, text or images. "
        ) * 30
        raw_html = f"<html><body><article>{prose}</article></body></html>"
        assert len(prose) > _SPA_MIN_TEXT_LENGTH
        assert _looks_like_spa_shell(raw_html, prose) == ""

    def test_high_script_ratio_without_marker_rejected(self):
        """SPA ratio arm: large HTML, tiny extracted text, no framework marker."""
        raw_html = (
            "<html><body>"
            + ("<script>" + ("a" * 200) + "</script>") * 50
            + "<p>Hi</p>"
            + "</body></html>"
        )
        extracted = "Hi"
        assert len(raw_html) > _SPA_MIN_HTML_LENGTH
        ratio = len(extracted) / len(raw_html)
        assert ratio < _SPA_TEXT_RATIO_THRESHOLD
        reason = _looks_like_spa_shell(raw_html, extracted)
        assert reason and "text/html ratio" in reason
