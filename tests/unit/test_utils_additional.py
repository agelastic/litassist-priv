"""
Additional unit tests for utility functions and command helpers.
"""

import os
import click
import pytest

from litassist.utils.file_ops import validate_file_size
from litassist.utils.core import (
    parse_strategies_file,
    validate_side_area_combination,
)
from litassist.commands.brainstorm import analyze_research_size
from litassist.utils.file_ops import expand_glob_patterns_callback as expand_glob_patterns


class DummyClient:
    """Dummy LLM client for testing regeneration logic."""

    def validate_citations(self, text):
        # No citation issues
        return []

    def complete(self, messages):
        # Not used when no regeneration needed
        return ("", {})


def test_validate_file_size_success(tmp_path):
    # Create a small temp file
    file_path = tmp_path / "test.txt"
    content = "Hello World"
    file_path.write_text(content)
    # Should return content without error
    result = validate_file_size(str(file_path), max_size=100)
    assert result == content


def test_validate_file_size_too_large(tmp_path):
    # Create a large temp file
    file_path = tmp_path / "big.txt"
    big_content = "x" * 200
    file_path.write_text(big_content)
    # Expect ClickException for size > max_size
    with pytest.raises(click.ClickException) as excinfo:
        validate_file_size(str(file_path), max_size=100)
    assert "file too large" in str(excinfo.value)


def test_parse_strategies_file_counts_and_metadata():
    text = (
        "# Side: plaintiff\n"
        "# Area: civil\n\n"
        "## ORTHODOX STRATEGIES\n"
        "### 1. Strategy One\n"
        "### 2. Strategy Two\n\n"
        "## UNORTHODOX STRATEGIES\n"
        "### Strategy 1: Strategy A\n\n"
        "## MOST LIKELY TO SUCCEED\n"
        "1. Strategy One\n"
        "2. Strategy A\n"
    )
    parsed = parse_strategies_file(text)
    assert parsed["metadata"]["side"] == "plaintiff"
    assert parsed["metadata"]["area"] == "civil"
    assert parsed["orthodox_count"] == 2
    assert parsed["unorthodox_count"] == 1
    assert parsed["most_likely_count"] == 2


def test_validate_side_area_combination_warns_for_invalid(capsys):
    # 'accused' not valid for 'civil'
    validate_side_area_combination("accused", "civil")
    captured = capsys.readouterr()
    assert "Warning" in captured.out
    # No exception raised


def test_validate_side_area_combination_no_warning_for_valid(capsys):
    # 'defendant' valid for 'civil'
    validate_side_area_combination("defendant", "civil")
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_analyze_research_size_small(monkeypatch, capsys):
    # Patch token counter to small values
    monkeypatch.setattr(
        "litassist.commands.brainstorm.research_handler.count_tokens_and_words",
        lambda text: (100, 50),
    )
    result = analyze_research_size(["data"], ["file1.txt"])
    # Expect no threshold exceed
    assert result["file_count"] == 1
    assert result["total_tokens"] == 100
    assert result["total_words"] == 50
    assert not result["exceeds_threshold"]
    # Only info message printed
    captured = capsys.readouterr()
    assert "[INFO]" in captured.out
    assert "[WARNING]" not in captured.out


def test_analyze_research_size_large(monkeypatch, capsys):
    # Patch token counter to large values
    monkeypatch.setattr(
        "litassist.commands.brainstorm.research_handler.count_tokens_and_words",
        lambda text: (200000, 100000),
    )
    result = analyze_research_size(["data"], ["file1.txt"])
    # Expect threshold exceeded
    assert result["exceeds_threshold"]
    captured = capsys.readouterr()
    # Should include info, warning, and additional info
    assert "[INFO]" in captured.out
    assert "[WARNING]" in captured.out


def test_expand_glob_patterns(tmp_path):
    # Create files in tmp_path
    file1 = tmp_path / "a.txt"
    file2 = tmp_path / "b.log"
    file1.write_text("x")
    file2.write_text("y")
    # Change cwd to tmp_path
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        # Exact path
        result = expand_glob_patterns(None, None, (str(file1),))
        assert result == (str(file1),)
        # Glob pattern (should match 'a.txt')
        res2 = expand_glob_patterns(None, None, ("*.txt",))
        assert isinstance(res2, tuple)
        # Resolve returned path and compare to original file
        assert len(res2) == 1
        assert os.path.abspath(res2[0]) == str(file1)
        # No match raises
        with pytest.raises(click.BadParameter):
            expand_glob_patterns(None, None, ("*.md",))
    finally:
        os.chdir(cwd)


def test_regenerate_bad_strategies_no_issues(monkeypatch):
    from litassist.commands.brainstorm import regenerate_bad_strategies

    # Prepare content with two strategies
    original = "## ORTHODOX STRATEGIES\n\n1. Strategy One\n2. Strategy Two\n"
    # Patch PROMPTS.get to avoid missing key errors
    monkeypatch.setattr(
        "litassist.commands.brainstorm.PROMPTS",
        type("P", (), {"get": lambda *args, **kwargs: ""})(),
    )
    # Use dummy client that reports no citation issues
    client = DummyClient()
    result = regenerate_bad_strategies(client, original, "", "orthodox")
    # Should start with header and include both strategies
    assert result.startswith("## ORTHODOX STRATEGIES")
    assert "1. Strategy One" in result
    assert "2. Strategy Two" in result


def test_expand_glob_pattern(tmp_path, monkeypatch):
    """Test the expand_glob_pattern utility function."""
    from litassist.utils.file_ops import expand_glob_pattern
    
    # Create test files
    file1 = tmp_path / "test1.txt"
    file2 = tmp_path / "test2.txt" 
    dir1 = tmp_path / "subdir"
    dir1.mkdir()
    file1.write_text("content1")
    file2.write_text("content2")
    
    # Mock click.echo to capture warnings
    warnings = []
    def mock_echo(msg):
        if "[WARNING]" in str(msg) or "Skipping" in str(msg):
            warnings.append(msg)
    
    monkeypatch.setattr("click.echo", mock_echo)
    
    # Save current directory
    cwd = os.getcwd()
    try:
        # Test glob pattern matching files
        os.chdir(tmp_path)
        result = expand_glob_pattern("*.txt")
        assert len(result) == 2
        assert str(file1.name) in result or str(file2.name) in result
        
        # Test empty pattern
        result = expand_glob_pattern("")
        assert result == []
        
        # Test pattern with directory (should warn)
        result = expand_glob_pattern("*")
        assert len(result) == 2  # Only files, not directory
        assert len(warnings) == 1  # Should have warned about directory
        assert "subdir" in str(warnings[0])
    finally:
        os.chdir(cwd)


def test_process_reference_files(tmp_path, monkeypatch, capsys):
    """Test the process_reference_files utility function."""
    from litassist.utils.file_ops import process_reference_files
    
    # Create test files
    ref1 = tmp_path / "reference1.txt"
    ref1.write_text("Reference content 1")
    
    # Mock read_document for PDF
    def mock_read_document(path):
        if path.endswith(".pdf"):
            return "PDF content from reference2"
        return ref1.read_text()
    
    monkeypatch.setattr(
        "litassist.utils.file_ops.read_document",
        mock_read_document
    )
    
    # Save current directory and change to temp directory for glob patterns
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        
        # Test with glob pattern
        context, files = process_reference_files("*.txt", purpose="reference")
        assert "reference1.txt" in context
        assert "Reference content 1" in context
        assert len(files) == 1
        assert "reference1.txt" in files
        
        # Test with --cove flag requirement (flag not set)
        context, files = process_reference_files(
            "*.txt", 
            purpose="CoVe",
            require_flag="--cove",
            flag_enabled=False
        )
        assert context == ""
        assert files == []
        captured = capsys.readouterr()
        assert "requires --cove flag" in captured.out
        
        # Test with flag enabled
        context, files = process_reference_files(
            "reference*.txt",
            purpose="CoVe",
            require_flag="--cove", 
            flag_enabled=True,
            show_char_count=True
        )
        assert "reference1.txt" in context
        assert len(files) == 1
        captured = capsys.readouterr()
        assert "19 chars" in captured.out  # Length of "Reference content 1"
    finally:
        os.chdir(cwd)
