"""Tests for save_command_output's output-location and header behaviour.

Every litassist command funnels its output through save_command_output. A
caseplan-generated Python runner places one run's files in a fresh per-run dir by
setting LITASSIST_OUTPUT_DIR, which the saver honours when no explicit output_dir
is passed; an explicit output_dir is never redirected. The runner itself must be
saved WITHOUT the standard text header, so it stays executable Python.
"""

import os

from litassist.logging import save_command_output


def test_env_dir_used_when_output_dir_omitted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "outputs" / "run_20260601_120000_000001"
    monkeypatch.setenv("LITASSIST_OUTPUT_DIR", str(run_dir))

    path = save_command_output("brainstorm_creative", "content", "")

    assert os.path.dirname(path) == str(run_dir)
    assert os.path.isfile(path)


def test_default_outputs_dir_when_env_unset(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LITASSIST_OUTPUT_DIR", raising=False)

    path = save_command_output("brainstorm_creative", "content", "")

    assert os.path.dirname(path) == str(tmp_path / "outputs")
    assert os.path.isfile(path)


def test_explicit_output_dir_is_not_redirected(tmp_path, monkeypatch):
    # updatefacts passes output_dir explicitly; the env var must not override it.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv(
        "LITASSIST_OUTPUT_DIR", str(tmp_path / "outputs" / "run_x")
    )

    path = save_command_output(
        "case_facts", "content", "", output_dir=str(tmp_path)
    )

    assert os.path.dirname(path) == str(tmp_path)


def test_include_header_false_writes_only_content(tmp_path, monkeypatch):
    # The Python runner is saved header-less so it stays executable: no title,
    # metadata, "Timestamp:" line, or 80-dash divider before the body.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LITASSIST_OUTPUT_DIR", raising=False)
    body = "#!/usr/bin/env python3\nimport os\nprint('hi')\n"

    path = save_command_output(
        "caseplan_commands", body, "", include_header=False
    )

    with open(path, encoding="utf-8") as fh:
        written = fh.read()
    assert written == body


def test_default_includes_header(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LITASSIST_OUTPUT_DIR", raising=False)

    path = save_command_output("digest", "the body", "")

    with open(path, encoding="utf-8") as fh:
        written = fh.read()
    assert written != "the body"
    assert "Timestamp:" in written
    assert "the body" in written
