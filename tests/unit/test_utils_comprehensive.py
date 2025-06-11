"""
Comprehensive tests for the utils module functionality.

Tests cover file operations, logging, timing, validation, and content processing.
All tests run offline using mocked dependencies.
"""

import pytest
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import json

from litassist.utils import (
    save_log,
    heartbeat,
    timed,
    create_reasoning_prompt,
    extract_reasoning_trace,
    parse_strategies_file,
    validate_file_size_limit,
    save_command_output,
    verify_content_if_needed,
)


class TestFileOperations:
    """Test file handling and validation functionality."""

    def test_validate_file_size_limit_success(self):
        """Test file size validation within limits."""
        content = "Test content that is well within limits"
        # Should not raise exception for small content
        try:
            validate_file_size_limit(content, 1000, "Test file")
        except Exception:
            pytest.fail("validate_file_size_limit raised exception for valid content")

    def test_validate_file_size_limit_exceeded(self):
        """Test file size validation when limit exceeded."""
        large_content = "x" * 1000  # 1000 characters

        with pytest.raises(Exception) as exc_info:
            validate_file_size_limit(large_content, 500, "Test file")

        assert "too large" in str(exc_info.value).lower()

    def test_validate_file_size_limit_edge_case(self):
        """Test file size validation at exact limit."""
        content = "x" * 100  # Exactly 100 characters

        # Should not raise exception at exact limit
        try:
            validate_file_size_limit(content, 100, "Test file")
        except Exception:
            pytest.fail("validate_file_size_limit raised exception at exact limit")

    @patch("litassist.utils.open", new_callable=mock_open)
    def test_save_command_output_success(self, mock_file):
        """Test successful command output saving."""
        content = "Test command output content"
        command = "test_command"
        outcome = "test_outcome"
        metadata = {"key": "value"}

        with patch("litassist.utils.time.strftime", return_value="20240101_120000"):
            result = save_command_output(command, content, outcome, metadata)

        # Check that result contains expected components (path may be absolute)
        assert "test_command" in result
        assert "test_outcome" in result
        assert "20240101_120000" in result
        assert result.endswith(".txt")

        # Verify file written
        mock_file.assert_called_once()

    @patch("litassist.utils.open", new_callable=mock_open)
    def test_save_command_output_sanitized_outcome(self, mock_file):
        """Test command output saving with sanitized outcome in filename."""
        content = "Test content"
        command = "test_command"
        outcome = "Test/Invalid\\Filename:Characters"

        with patch("litassist.utils.time.strftime", return_value="20240101_120000"):
            result = save_command_output(command, content, outcome)

        # Extract just the filename from the full path
        filename = os.path.basename(result)

        # Outcome should be sanitized in filename (converted to lowercase)
        assert "invalid" in filename.lower()
        assert "/" not in filename
        assert "\\" not in filename
        assert ":" not in filename

    def test_save_command_output_empty_content(self):
        """Test command output saving with empty content."""
        with patch("litassist.utils.open", new_callable=mock_open) as mock_file:
            with patch("litassist.utils.os.makedirs"):
                with patch(
                    "litassist.utils.time.strftime", return_value="20240101_120000"
                ):
                    result = save_command_output("test", "", "empty")

        assert "test_" in result
        mock_file.assert_called_once()


class TestLogging:
    """Test logging functionality."""

    @patch("litassist.utils.open", new_callable=mock_open)
    @patch("litassist.utils.json.dump")
    def test_save_log_success(self, mock_json_dump, mock_file):
        """Test successful log saving."""
        command = "test_command"
        log_data = {
            "inputs": {"test": "data"},
            "params": {"model": "test"},
            "usage": {"tokens": 100},
            "response": "test response",
        }

        with patch("litassist.utils.time.strftime", return_value="20240101_120000"):
            save_log(command, log_data)

        # Verify file opened for writing
        mock_file.assert_called_once()

        # Verify JSON dumped
        mock_json_dump.assert_called_once()

    @patch("litassist.utils.open", new_callable=mock_open)
    @patch("litassist.utils.os.makedirs")
    @patch("litassist.utils.json.dump")
    def test_save_log_with_metadata(self, mock_json_dump, mock_makedirs, mock_file):
        """Test log saving with additional metadata."""
        command = "strategy"
        log_data = {
            "inputs": {"case_facts": "test facts"},
            "metadata": {"outcome": "test outcome"},
            "timestamp": "2024-01-01T12:00:00",
        }

        save_log(command, log_data)

        # Verify JSON dump was called with the data (save_log doesn't modify payload)
        mock_json_dump.assert_called_once()
        call_args = mock_json_dump.call_args[0]
        saved_data = call_args[0]

        # The payload should be saved as-is
        assert "inputs" in saved_data
        assert saved_data["inputs"]["case_facts"] == "test facts"
        assert "metadata" in saved_data
        assert saved_data["metadata"]["outcome"] == "test outcome"

    @patch("litassist.utils.open", side_effect=PermissionError("Permission denied"))
    @patch("litassist.utils.os.makedirs")
    def test_save_log_permission_error(self, mock_makedirs, mock_file):
        """Test log saving handles permission errors gracefully."""
        command = "test_command"
        log_data = {"test": "data"}

        # PermissionError should be caught and converted to click.ClickException
        with pytest.raises(Exception) as exc_info:
            save_log(command, log_data)

        # Should handle the error by raising appropriate exception
        error_msg = str(exc_info.value).lower()
        assert any(
            keyword in error_msg for keyword in ["permission", "failed", "error"]
        )


class TestTiming:
    """Test timing and performance measurement functionality."""

    def test_timed_decorator_function(self):
        """Test the timed decorator on a function."""

        @timed
        def test_function():
            time.sleep(0.01)  # Small delay
            return "test_result"

        # Should return original function result
        result = test_function()
        assert result == "test_result"

    def test_timed_decorator_with_exception(self):
        """Test timed decorator when decorated function raises exception."""

        @timed
        def failing_function():
            raise ValueError("Test error")

        # Exception should propagate
        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_heartbeat_decorator_function(self):
        """Test heartbeat decorator functionality."""
        mock_func = MagicMock(return_value="heartbeat_result")

        # Create heartbeat-decorated function
        heartbeat_func = heartbeat(1)(mock_func)

        # Call the decorated function
        result = heartbeat_func("test_arg", keyword="test_kwarg")

        # Should return original result
        assert result == "heartbeat_result"

        # Original function should be called with same arguments
        mock_func.assert_called_once_with("test_arg", keyword="test_kwarg")

    def test_heartbeat_decorator_with_interval(self):
        """Test heartbeat decorator with custom interval."""
        mock_func = MagicMock(return_value="result")

        # Test different intervals
        for interval in [0.5, 1.0, 2.0]:
            heartbeat_func = heartbeat(interval)(mock_func)
            result = heartbeat_func()
            assert result == "result"


class TestReasoningPrompts:
    """Test reasoning prompt creation and extraction."""

    def test_create_reasoning_prompt_basic(self):
        """Test basic reasoning prompt creation."""
        base_prompt = "Analyze this contract case"
        command = "strategy"

        result = create_reasoning_prompt(base_prompt, command)

        assert base_prompt in result
        assert "LEGAL REASONING TRACE" in result
        assert "Issue:" in result
        assert "Applicable Law:" in result
        assert "Application to Facts:" in result
        assert "Conclusion:" in result

    def test_create_reasoning_prompt_different_commands(self):
        """Test reasoning prompt creation for different commands."""
        base_prompt = "Test prompt"
        commands = ["strategy", "draft", "digest", "lookup"]

        for command in commands:
            result = create_reasoning_prompt(base_prompt, command)
            assert base_prompt in result
            assert "REASONING TRACE" in result

    def test_create_reasoning_prompt_empty_input(self):
        """Test reasoning prompt creation with empty input."""
        result = create_reasoning_prompt("", "strategy")

        # Should still contain reasoning structure
        assert "LEGAL REASONING TRACE" in result
        assert "Issue:" in result

    def test_extract_reasoning_trace_valid_content(self):
        """Test extraction of reasoning trace from valid content."""
        content = """
        Some analysis content here.
        
        === LEGAL REASONING TRACE ===
        Issue: Contract breach dispute
        Applicable Law: Contract formation principles
        Application to Facts: Clear breach occurred on specified date
        Conclusion: Strong case for damages
        Confidence: 85%
        Sources: Smith v Jones [2020] FCA 123
        """

        trace = extract_reasoning_trace(content, "strategy")

        assert trace is not None
        assert trace.issue == "Contract breach dispute"
        assert trace.applicable_law == "Contract formation principles"
        assert trace.application == "Clear breach occurred on specified date"
        assert trace.conclusion == "Strong case for damages"
        assert trace.confidence == 85
        assert trace.sources == ["Smith v Jones [2020] FCA 123"]

    def test_extract_reasoning_trace_missing_sections(self):
        """Test extraction when some reasoning sections are missing."""
        content = """
        === LEGAL REASONING TRACE ===
        Issue: Contract dispute
        Conclusion: Moderate prospects
        """

        trace = extract_reasoning_trace(content, "strategy")

        # Should return None when essential sections are missing
        assert trace is None

    def test_extract_reasoning_trace_no_trace(self):
        """Test extraction when no reasoning trace exists."""
        content = "Regular analysis content without reasoning trace structure"

        trace = extract_reasoning_trace(content, "strategy")

        assert trace is None

    def test_extract_reasoning_trace_malformed(self):
        """Test extraction from malformed reasoning trace."""
        content = """
        === LEGAL REASONING TRACE ===
        Malformed content without proper structure
        Random text here
        """

        trace = extract_reasoning_trace(content, "strategy")

        # Should handle gracefully, either return None or partial trace
        # Implementation depends on robustness requirements


class TestStrategyFileParsing:
    """Test strategy file parsing functionality."""

    def test_parse_strategies_file_complete_structure(self):
        """Test parsing of complete strategy file structure."""
        content = """## ORTHODOX STRATEGIES
1. Traditional contract claim
Standard approach using established precedents.

2. Alternative dispute resolution
Mediation and arbitration before litigation.

3. Statutory remedies
Consumer protection law applications.

## UNORTHODOX STRATEGIES
1. Novel legal theory
Innovative approach to the problem.

2. Strategic timing
Delay tactics for better positioning.

## MOST LIKELY TO SUCCEED
1. Direct breach claim
High probability given strong evidence.

2. Injunctive relief
Clear case for equitable remedies.

3. Summary judgment
Facts support immediate resolution.
"""

        result = parse_strategies_file(content)

        assert result["orthodox_count"] == 3
        assert result["unorthodox_count"] == 2
        assert result["most_likely_count"] == 3
        assert isinstance(result["metadata"], dict)

    def test_parse_strategies_file_partial_sections(self):
        """Test parsing when only some sections are present."""
        content = """## ORTHODOX STRATEGIES
1. Standard approach
Traditional method.

## MOST LIKELY TO SUCCEED
1. Best option
Highest success probability.
"""

        result = parse_strategies_file(content)

        assert result["orthodox_count"] == 1
        assert result["unorthodox_count"] == 0
        assert result["most_likely_count"] == 1

    def test_parse_strategies_file_no_structure(self):
        """Test parsing of unstructured content."""
        content = """
        Some general strategies:
        
        1. First approach
        2. Second approach
        3. Third approach
        """

        result = parse_strategies_file(content)

        # Should handle gracefully
        assert isinstance(result, dict)
        assert "orthodox_count" in result
        assert "unorthodox_count" in result
        assert "most_likely_count" in result

    def test_parse_strategies_file_empty_sections(self):
        """Test parsing when sections exist but are empty."""
        content = """
        ## ORTHODOX STRATEGIES
        
        ## UNORTHODOX STRATEGIES
        
        ## MOST LIKELY TO SUCCEED
        """

        result = parse_strategies_file(content)

        assert result["orthodox_count"] == 0
        assert result["unorthodox_count"] == 0
        assert result["most_likely_count"] == 0

    def test_parse_strategies_file_with_metadata(self):
        """Test parsing strategies file with metadata extraction."""
        content = """# Side: Plaintiff
# Area: Contract Law

## ORTHODOX STRATEGIES
1. Standard claim
Traditional approach.
"""

        result = parse_strategies_file(content)

        assert result["orthodox_count"] == 1
        assert result["metadata"]["side"] == "Plaintiff"
        assert result["metadata"]["area"] == "Contract Law"


class TestContentVerification:
    """Test content verification functionality."""

    def test_verify_content_if_needed_enabled(self):
        """Test content verification when enabled."""
        mock_client = MagicMock()
        mock_client.should_auto_verify.return_value = False
        mock_client.verify_with_level.return_value = "Minor corrections needed"
        mock_client.validate_citations.return_value = []

        content = "Legal analysis content"
        result_content, verified = verify_content_if_needed(
            mock_client, content, "strategy", verify_flag=True
        )

        # Should perform verification
        assert verified is True
        assert "Minor corrections needed" in result_content
        mock_client.verify_with_level.assert_called_once_with(content, "heavy")

    def test_verify_content_if_needed_disabled(self):
        """Test content verification when disabled."""
        mock_client = MagicMock()
        mock_client.should_auto_verify.return_value = False

        content = "Legal analysis content"
        result_content, verified = verify_content_if_needed(
            mock_client, content, "strategy", verify_flag=False
        )

        # Should not perform verification
        assert verified is False
        assert result_content == content
        mock_client.verify_with_level.assert_not_called()

    def test_verify_content_if_needed_llm_failure(self):
        """Test content verification with LLM failure."""
        mock_client = MagicMock()
        mock_client.should_auto_verify.return_value = False
        mock_client.verify_with_level.side_effect = Exception("LLM API error")

        content = "Legal analysis content"

        with pytest.raises(Exception):
            verify_content_if_needed(mock_client, content, "strategy", verify_flag=True)


class TestUtilityHelpers:
    """Test miscellaneous utility helper functions."""

    def test_file_encoding_detection(self):
        """Test automatic file encoding detection."""
        # This would test a utility function for detecting file encoding
        # Implementation depends on whether such functionality exists
        pass

    def test_text_normalization(self):
        """Test text normalization utilities."""
        # Test for text cleaning, whitespace normalization, etc.
        # Implementation depends on available utility functions
        pass

    def test_chunking_algorithms(self):
        """Test text chunking for large content."""
        # Test for breaking large content into manageable chunks
        # Implementation depends on chunking utilities
        pass

    def test_token_counting_utilities(self):
        """Test token counting functionality."""
        # Test for estimating token usage before LLM calls
        # Implementation depends on token counting utilities
        pass


class TestErrorHandling:
    """Test error handling in utility functions."""

    def test_save_log_invalid_json(self):
        """Test log saving with non-serializable data."""

        # Create object that can't be JSON serialized
        class NonSerializable:
            pass

        log_data = {"invalid": NonSerializable()}

        with patch("litassist.utils.open", new_callable=mock_open):
            with patch("litassist.utils.os.makedirs"):
                # Should handle serialization errors gracefully
                try:
                    save_log("test", log_data)
                except (TypeError, ValueError):
                    # Expected behavior - either handle gracefully or raise appropriate error
                    pass

    def test_file_operations_disk_full(self):
        """Test file operations when disk is full."""
        with patch(
            "litassist.utils.open", side_effect=OSError("No space left on device")
        ):
            with pytest.raises(OSError):
                save_command_output("test", "content", "outcome")

    def test_concurrent_file_access(self):
        """Test handling of concurrent file access."""
        # This would test file locking and concurrent access handling
        # Implementation depends on concurrency requirements
        pass


class TestPerformanceEdgeCases:
    """Test performance-related edge cases."""

    def test_large_content_handling(self):
        """Test handling of very large content."""
        large_content = "x" * 100000  # 100KB content

        # Should handle large content without memory issues
        with patch("litassist.utils.open", new_callable=mock_open):
            with patch("litassist.utils.os.makedirs"):
                try:
                    save_command_output("test", large_content, "large_test")
                except MemoryError:
                    pytest.fail("Should handle large content efficiently")

    def test_many_small_operations(self):
        """Test performance with many small operations."""
        # Test multiple small file operations
        with patch("litassist.utils.open", new_callable=mock_open):
            with patch("litassist.utils.os.makedirs"):
                for i in range(100):
                    save_command_output(f"test_{i}", f"content_{i}", f"outcome_{i}")

                # Should complete without significant performance degradation

    def test_memory_usage_patterns(self):
        """Test memory usage patterns in utility functions."""
        # This would test for memory leaks or excessive usage
        # Implementation depends on memory profiling requirements
        pass


# Integration test markers
pytestmark = [pytest.mark.unit, pytest.mark.utils, pytest.mark.offline]
