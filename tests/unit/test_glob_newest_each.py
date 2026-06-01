"""Tests for expand_glob_newest_each_callback (multi-value, newest-per-flag).

strategy --strategies is repeatable: one brainstorm set per flag. Each pattern
resolves INDEPENDENTLY to its most-recent match (by mtime), a literal path passes
through, and EVERY glob resolution is announced on the console (not only on a
multi-match) so the user always sees which file each flag bound to. This warn
policy is the only behavioural difference from the scalar
expand_glob_single_callback (which stays quiet on a single match).
"""

import os

import click
import pytest

from litassist.utils.file_ops import expand_glob_newest_each_callback


def _touch(path, mtime):
    """Create a file with a fixed mtime so 'newest' is deterministic."""
    path.write_text("x")
    os.utime(path, (mtime, mtime))
    return str(path)


def test_none_returns_none():
    # Invoked directly with None -> must round-trip (the body does `if strategies:`).
    assert expand_glob_newest_each_callback(None, None, None) is None


def test_empty_tuple_returns_empty():
    # multiple=True yields () when the option is omitted.
    assert expand_glob_newest_each_callback(None, None, ()) == ()


def test_literal_files_pass_through(tmp_path):
    a = tmp_path / "creative.txt"
    a.write_text("c")
    b = tmp_path / "research.txt"
    b.write_text("r")
    assert expand_glob_newest_each_callback(None, None, (str(a), str(b))) == (
        str(a),
        str(b),
    )


def test_each_flag_resolves_its_own_newest(tmp_path):
    # The dual-brainstorm case: one glob per set, each picking its own newest
    # and ignoring older same-prefix files from prior runs.
    c_old = _touch(tmp_path / "brainstorm_creative_20260101.txt", 1_000)
    c_new = _touch(tmp_path / "brainstorm_creative_20260103.txt", 3_000)
    r_old = _touch(tmp_path / "brainstorm_research_20260102.txt", 2_000)
    r_new = _touch(tmp_path / "brainstorm_research_20260104.txt", 4_000)
    value = (
        str(tmp_path / "brainstorm_creative_*.txt"),
        str(tmp_path / "brainstorm_research_*.txt"),
    )
    assert expand_glob_newest_each_callback(None, None, value) == (c_new, r_new)
    assert c_old and r_old  # both exist; newest of EACH prefix wins


def test_warns_on_every_glob_resolution(tmp_path, capsys):
    _touch(tmp_path / "only_20260101.txt", 1_000)
    expand_glob_newest_each_callback(None, None, (str(tmp_path / "only_*.txt"),))
    out = capsys.readouterr().out
    assert "Resolved" in out
    assert "only_20260101.txt" in out


def test_multi_match_warning_names_count(tmp_path, capsys):
    _touch(tmp_path / "b_1.txt", 1_000)
    _touch(tmp_path / "b_2.txt", 2_000)
    expand_glob_newest_each_callback(None, None, (str(tmp_path / "b_*.txt"),))
    out = capsys.readouterr().out
    assert "newest of 2" in out
    assert "b_2.txt" in out


def test_literal_passthrough_no_warning(tmp_path, capsys):
    f = tmp_path / "creative.txt"
    f.write_text("c")
    expand_glob_newest_each_callback(None, None, (str(f),))
    assert "Resolved" not in capsys.readouterr().out


def test_dedup_preserves_order(tmp_path):
    # Literal and a glob that resolves to the SAME file -> one entry, first wins.
    a = _touch(tmp_path / "x.txt", 1_000)
    result = expand_glob_newest_each_callback(
        None, None, (a, str(tmp_path / "x*.txt"))
    )
    assert result == (a,)


def test_zero_match_raises(tmp_path):
    with pytest.raises(click.BadParameter, match="No files matching pattern"):
        expand_glob_newest_each_callback(None, None, (str(tmp_path / "nope_*.txt"),))


def test_directory_rejected(tmp_path):
    with pytest.raises(click.BadParameter, match="directory"):
        expand_glob_newest_each_callback(None, None, (str(tmp_path),))


def test_missing_literal_raises(tmp_path):
    with pytest.raises(click.BadParameter, match="File not found"):
        expand_glob_newest_each_callback(None, None, (str(tmp_path / "missing.txt"),))
