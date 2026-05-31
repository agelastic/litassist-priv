"""Tests for expand_glob_single_callback (scalar path/glob resolution).

Single-input path args (strategy --strategies, verify FILE) receive caseplan
globs like 'outputs/brainstorm_*.txt'. This callback resolves such a glob to the
MOST RECENT matching file (mirroring resolve_case_facts_file's recency pick),
passes a literal file through, and fails loudly on a zero-match or a directory.
"""

import os

import click
import pytest

from litassist.utils.file_ops import expand_glob_single_callback


def _touch(path, mtime):
    """Create an empty file with a fixed mtime so 'newest' is deterministic."""
    path.write_text("x")
    os.utime(path, (mtime, mtime))
    return str(path)


def test_literal_existing_file_passes_through(tmp_path):
    f = tmp_path / "case_facts.txt"
    f.write_text("facts")
    assert expand_glob_single_callback(None, None, str(f)) == str(f)


def test_none_returns_none():
    # Optional arg omitted -> None must round-trip (body does `if strategies:`).
    assert expand_glob_single_callback(None, None, None) is None


def test_glob_resolves_to_newest(tmp_path):
    older = _touch(tmp_path / "brainstorm_20260101_000000_000000000.txt", 1_000)
    newer = _touch(tmp_path / "brainstorm_20260102_000000_000000000.txt", 2_000)
    pattern = str(tmp_path / "brainstorm_*.txt")
    assert expand_glob_single_callback(None, None, pattern) == newer
    assert older  # both exist; newest wins regardless of lexical order


def test_single_match_glob_no_warning(tmp_path, capsys):
    # Exactly one match is unambiguous: resolve it WITHOUT the multi-match warning.
    only = _touch(tmp_path / "draft_memo_20260101_000000_000000000.txt", 1_000)
    pattern = str(tmp_path / "draft_memo_*.txt")
    assert expand_glob_single_callback(None, None, pattern) == only
    assert "Matched" not in capsys.readouterr().out


def test_glob_zero_match_raises(tmp_path):
    with pytest.raises(click.BadParameter, match="No files matching pattern"):
        expand_glob_single_callback(None, None, str(tmp_path / "nope_*.txt"))


def test_directory_rejected(tmp_path):
    with pytest.raises(click.BadParameter, match="directory"):
        expand_glob_single_callback(None, None, str(tmp_path))


def test_missing_literal_raises(tmp_path):
    with pytest.raises(click.BadParameter, match="File not found"):
        expand_glob_single_callback(None, None, str(tmp_path / "missing.txt"))
