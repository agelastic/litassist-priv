"""
Test for fetch_attempt audit log fidelity.

The markdown formatter for fetch_attempt logs (in
litassist/logging/markdown_writers.py write_fetch_log_markdown) used to
drop forensically-important fields silently: rejection_reason, http_status,
content_size, cf_mitigated, cf_ray. Without these, you cannot tell from a
logs/ file whether a 'failed' fetch was a real Cloudflare challenge or a
detector false positive.

The test below pins the headline use case: distinguishing a real challenge
from a false positive must be possible from the rendered markdown.
"""

import io

from litassist.logging.markdown_writers import write_fetch_log_markdown


def _render(payload):
    buf = io.StringIO()
    write_fetch_log_markdown(buf, "fetch_attempt", "20260526-160000", payload)
    return buf.getvalue()


class TestFetchAuditLogFidelity:
    def test_false_positive_distinguishable_from_real_challenge(self):
        """Given two audit log entries, one for a real challenge and one for a
        detector false positive, the rendered markdown must show enough
        information to tell them apart. Implicitly verifies that http_status,
        rejection_reason, content_size, cf_mitigated all render."""
        real_challenge = _render({
            "url": "https://example.com/blocked",
            "method": "curl_cffi",
            "status": "failed",
            "http_status": 403,
            "cf_mitigated": "challenge",
            "cf_ray": "a01abcdef-SYD",
            "rejection_reason": "challenge marker: 'just a moment...'",
            "content_size": 31963,
            "timestamp": 1716690000,
        })
        false_positive = _render({
            "url": "https://example.com/legitimate",
            "method": "curl_cffi",
            "status": "failed",
            "http_status": 200,
            "rejection_reason": "challenge marker: 'please complete the captcha'",
            "content_size": 89301,
            "timestamp": 1716690000,
        })
        # Real challenge has HTTP 403, false positive has HTTP 200
        assert "403" in real_challenge
        assert "200" in false_positive
        # Real challenge has cf-mitigated header, false positive does not
        assert "Cloudflare Mitigation" in real_challenge
        assert "Cloudflare Mitigation" not in false_positive
        # Both expose rejection_reason and content_size
        assert "Rejection Reason" in real_challenge
        assert "Rejection Reason" in false_positive
        assert "31,963" in real_challenge
        assert "89,301" in false_positive
