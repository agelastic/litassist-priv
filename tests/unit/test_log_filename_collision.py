"""
Regression test for save_log filename collision.

save_log used to format timestamps with second resolution
(`time.strftime("%Y%m%d-%H%M%S")`). Two save_log calls within the same
wall-clock second produced identical filenames and the second silently
overwrote the first. Verified empirically 26/05/2026 - 50ms gap collides.

In the lookup fetcher, the curl_cffi-failure -> immediate-Jina-fallback path
routinely produces two save_log calls in the same second when Jina returns
a fast error (e.g. invalid API key auth failure). The curl_cffi diagnostic
record (rejection_reason, http_status, cf_mitigated, cf_ray) was being
silently lost.

Fix: microsecond-resolution timestamps via datetime.now().strftime(
"%Y%m%d-%H%M%S-%f"). This test pins that behaviour.
"""

import json
from unittest.mock import MagicMock, patch

from litassist.logging import save_log


def _save(tag, payload):
    """Call save_log with a JSON-format ctx so both records reach disk."""
    fake_ctx = MagicMock()
    fake_ctx.obj = {"log_format": "json"}
    with patch("click.get_current_context", return_value=fake_ctx):
        save_log(tag, payload)


class TestLogFilenameCollision:
    def test_two_save_log_calls_same_second_both_persist(self, tmp_path):
        """Two save_log calls back-to-back must produce two distinct files."""
        # The save_log function uses module-level LOG_DIR. Patch to tmp_path
        # so we don't pollute the real logs/ directory.
        with patch("litassist.logging.LOG_DIR", str(tmp_path)):
            _save("collision_regression", {"call": "first", "data": "curl_cffi failure"})
            _save("collision_regression", {"call": "second", "data": "jina failure"})

        files = sorted(tmp_path.glob("collision_regression_*.json"))
        assert len(files) == 2, (
            f"Expected 2 distinct files, got {len(files)} - second call overwrote first. "
            f"Files: {[f.name for f in files]}"
        )

        # Verify both records are preserved (the curl_cffi record is the
        # forensically important one that used to be lost)
        contents = [json.loads(f.read_text()) for f in files]
        calls = sorted(c["call"] for c in contents)
        assert calls == ["first", "second"], (
            f"Expected both 'first' and 'second' records preserved, got {calls}"
        )

    def test_three_save_log_calls_same_burst_all_persist(self, tmp_path):
        """Stress: three calls in tight succession all survive."""
        with patch("litassist.logging.LOG_DIR", str(tmp_path)):
            for i in range(3):
                _save("burst_regression", {"call": i})

        files = sorted(tmp_path.glob("burst_regression_*.json"))
        assert len(files) == 3, (
            f"Expected 3 distinct files in tight burst, got {len(files)}"
        )

    def test_filename_format_includes_microseconds(self, tmp_path):
        """Filename must have the YYYYMMDD-HHMMSS-MICROSECONDS shape that
        guarantees uniqueness."""
        with patch("litassist.logging.LOG_DIR", str(tmp_path)):
            _save("format_check", {"data": "test"})

        files = list(tmp_path.glob("format_check_*.json"))
        assert len(files) == 1
        # filename pattern: format_check_YYYYMMDD-HHMMSS-MICROSECONDS.json
        name = files[0].stem  # strip .json
        parts = name.rsplit("_", 1)
        assert len(parts) == 2
        timestamp = parts[1]
        # 20260526-181953-572662 -> three dash-separated components
        date_part, time_part, micros_part = timestamp.split("-")
        assert len(date_part) == 8, f"date part wrong: {date_part!r}"
        assert len(time_part) == 6, f"time part wrong: {time_part!r}"
        assert len(micros_part) == 6, f"microseconds part wrong: {micros_part!r}"
        assert micros_part.isdigit()
