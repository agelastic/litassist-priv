"""
Tests for fetch_attempt audit log fidelity.

The markdown formatter for fetch_attempt logs (in
litassist/logging/markdown_writers.py write_fetch_log_markdown) used to drop
forensically-important fields silently: rejection_reason, http_status,
content_size, cf_mitigated, cf_ray. Without these, you cannot tell from a
logs/ file whether a 'failed' fetch was a real Cloudflare challenge or a
detector false positive. Verified empirically 26/05/2026 - fedcourt false
positives were impossible to distinguish from real challenges in the audit
log.

These tests pin the formatter so the diagnostic fields stay in the output.
"""

import io

from litassist.logging.markdown_writers import write_fetch_log_markdown


def _render(payload):
    buf = io.StringIO()
    write_fetch_log_markdown(buf, "fetch_attempt", "20260526-160000", payload)
    return buf.getvalue()


class TestFetchAuditLogFidelity:
    def test_http_status_is_rendered(self):
        out = _render({
            "url": "https://example.com/page",
            "method": "curl_cffi",
            "status": "failed",
            "http_status": 403,
            "timestamp": 1716690000,
        })
        assert "HTTP Status" in out
        assert "403" in out

    def test_rejection_reason_is_rendered(self):
        out = _render({
            "url": "https://example.com/page",
            "method": "curl_cffi",
            "status": "failed",
            "rejection_reason": "challenge marker: 'just a moment...'",
            "timestamp": 1716690000,
        })
        assert "Rejection Reason" in out
        assert "just a moment" in out

    def test_content_size_is_rendered(self):
        out = _render({
            "url": "https://example.com/page",
            "method": "curl_cffi",
            "status": "failed",
            "content_size": 32198,
            "timestamp": 1716690000,
        })
        assert "Content Size" in out
        assert "32,198" in out

    def test_cf_mitigated_header_is_rendered(self):
        out = _render({
            "url": "https://example.com/page",
            "method": "curl_cffi",
            "status": "failed",
            "http_status": 403,
            "cf_mitigated": "challenge",
            "timestamp": 1716690000,
        })
        assert "Cloudflare Mitigation" in out
        assert "challenge" in out

    def test_cf_ray_is_rendered(self):
        out = _render({
            "url": "https://example.com/page",
            "method": "curl_cffi",
            "status": "failed",
            "cf_ray": "a01ab2a71da3e7c8-SYD",
            "timestamp": 1716690000,
        })
        assert "Cloudflare Ray ID" in out
        assert "a01ab2a71da3e7c8" in out

    def test_rewrite_target_is_rendered(self):
        """AustLII PDF -> HTML substitution records rewrite_target. Audit log
        must show what URL was actually fetched instead."""
        out = _render({
            "url": "https://www.austlii.edu.au/au/journals/Foo/2020/1.pdf",
            "method": "austlii_pdf_to_html",
            "status": "rewrite",
            "rewrite_target": "https://www.austlii.edu.au/au/journals/Foo/2020/1.html",
            "reason": "AustLII Cloudflare policy blocks PDF paths; HTML sibling reachable",
            "timestamp": 1716690000,
        })
        assert "Rewrite Target" in out
        assert "1.html" in out

    def test_false_positive_distinguishable_from_real_challenge(self):
        """The headline use case: given two audit log entries, one for a real
        challenge and one for a detector false positive, the rendered markdown
        must show enough information to tell them apart.
        """
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
            "http_status": 200,  # KEY: status is 200, not 403
            # No cf_mitigated header on a real 200 OK
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
