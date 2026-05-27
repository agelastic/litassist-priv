"""Regression tests for citation-validation markdown rendering.

`validate_citation_patterns` logs the flag under the key `enable_online`,
while the markdown writer used to read `online_enabled` and silently
rendered the flag as False. This test exercises both shapes.
"""

import io

import pytest

from litassist.logging.markdown_writers import write_citation_validation_markdown


class TestCitationValidationMarkdown:
    def test_enable_online_key_is_rendered_true(self):
        buf = io.StringIO()
        payload = {
            "method": "validate_citation_patterns",
            "issues": [],
            "enable_online": True,
            "timestamp": "2026-05-27 12:00:00",
        }
        write_citation_validation_markdown(buf, "tag", "ts", payload)
        out = buf.getvalue()
        assert "**Online Enabled**: True" in out, (
            f"enable_online=True must render as True, got: {out!r}"
        )

    def test_online_enabled_key_still_works_for_legacy_logs(self):
        # Backward compatibility: older log entries that used the writer's
        # historical key name must still render correctly.
        buf = io.StringIO()
        payload = {
            "method": "validate_citation_patterns",
            "issues": [],
            "online_enabled": True,
            "timestamp": "2026-05-27 12:00:00",
        }
        write_citation_validation_markdown(buf, "tag", "ts", payload)
        assert "**Online Enabled**: True" in buf.getvalue()

    def test_neither_key_present_renders_false_default(self):
        buf = io.StringIO()
        payload = {"method": "validate_citation_patterns", "issues": []}
        write_citation_validation_markdown(buf, "tag", "ts", payload)
        assert "**Online Enabled**: False" in buf.getvalue()


pytestmark = [pytest.mark.unit, pytest.mark.offline]
