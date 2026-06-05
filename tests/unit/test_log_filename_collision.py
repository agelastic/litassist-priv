"""
Regression test for save_log filename collision.

save_log used to format timestamps with second resolution. Two save_log
calls within the same wall-clock second produced identical filenames and
the second silently overwrote the first - relevant for the
curl_cffi-failure -> immediate-Jina-fallback path where Jina returns a
fast error.

Fix: microsecond-resolution timestamps via datetime.now().strftime(
"%Y%m%d-%H%M%S-%f").
"""

import json
import os
from unittest.mock import MagicMock, patch

from litassist.logging import save_log


def _save(tag, payload):
    fake_ctx = MagicMock()
    fake_ctx.obj = {"log_format": "json"}
    with patch("click.get_current_context", return_value=fake_ctx):
        save_log(tag, payload)


class TestLogFilenameCollision:
    def test_two_save_log_calls_same_second_both_persist(self, tmp_path):
        with patch.dict(os.environ, {"LITASSIST_LOG_DIR": str(tmp_path)}):
            _save("collision_regression", {"call": "first", "data": "curl_cffi failure"})
            _save("collision_regression", {"call": "second", "data": "jina failure"})

        files = sorted(tmp_path.glob("collision_regression_*.json"))
        assert len(files) == 2, (
            f"Expected 2 distinct files, got {len(files)} - second call overwrote first"
        )
        contents = [json.loads(f.read_text()) for f in files]
        calls = sorted(c["call"] for c in contents)
        assert calls == ["first", "second"]
