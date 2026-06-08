"""
Comprehensive tests for the utils module functionality.

Tests cover file operations, logging, timing, validation, and content processing.
All tests run offline using mocked dependencies.
"""

import pytest
import os
import threading
import time
from unittest.mock import patch, MagicMock, mock_open

from litassist.utils.core import heartbeat, parse_strategies_file
from litassist.timing import timed
from litassist.utils.legal_reasoning import (
    create_reasoning_prompt,
    extract_reasoning_trace,
    verify_content_if_needed,
)
from litassist.utils.file_ops import validate_file_size_limit
from litassist.logging import save_log, save_command_output


class TestFileOperations:
    """Test file handling and validation functionality."""

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

    @patch("litassist.logging.output_saver.open", new_callable=mock_open)
    def test_save_command_output_sanitized_outcome(self, mock_file):
        """Test command output saving with sanitized outcome in filename."""
        content = "Test content"
        command = "test_command"
        outcome = "Test/Invalid\\Filename:Characters"

        with patch(
            "litassist.logging.output_saver.time.strftime", return_value="20240101_120000"
        ):
            result = save_command_output(command, content, outcome)

        # Extract just the filename from the full path
        filename = os.path.basename(result)

        # Outcome should be sanitized in filename (converted to lowercase)
        assert "invalid" in filename.lower()
        assert "/" not in filename
        assert "\\" not in filename
        assert ":" not in filename


class TestLogging:
    """Test logging functionality."""

    @patch(
        "builtins.open", side_effect=PermissionError("Permission denied")
    )
    @patch("litassist.logging.os.makedirs")
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
        """timed must populate timing metadata on (content, usage_dict) returns."""

        @timed
        def returns_tuple():
            time.sleep(0.01)
            return "content", {}

        content, usage = returns_tuple()
        assert content == "content"
        timing = usage.get("timing")
        assert timing is not None, "timed did not attach timing metadata"
        assert timing["duration_seconds"] >= 0.01
        assert "start_time" in timing and "end_time" in timing

    def test_timed_decorator_with_exception(self):
        """Test timed decorator when decorated function raises exception."""

        @timed
        def failing_function():
            raise ValueError("Test error")

        # Exception should propagate
        with pytest.raises(ValueError, match="Test error"):
            failing_function()

    def test_heartbeat_decorator_with_interval(self, monkeypatch):
        """heartbeat must propagate the configured interval to Event.wait."""
        env = os.environ.copy()
        env.pop("PYTEST_CURRENT_TEST", None)

        captured_timeouts = []
        # Semaphore (not Event) so signalling does not trip the Event.wait spy.
        captured_signal = threading.Semaphore(0)
        real_wait = threading.Event.wait

        def spying_wait(self, timeout=None):
            # Only react to the heartbeat thread's own wait(0.05). Unrelated
            # Event.wait calls in pytest/threading internals pass through
            # unchanged, otherwise they would signal captured_signal early
            # and let fn() return before the heartbeat thread emits a ping.
            if timeout == 0.05:
                captured_timeouts.append(timeout)
                captured_signal.release()
                # End the thread on first wait so it does not sleep further.
                self.set()
                return real_wait(self, 0)
            return real_wait(self, timeout)

        monkeypatch.setattr(threading.Event, "wait", spying_wait)

        with patch.dict(os.environ, env, clear=True):
            with patch("litassist.utils.core.click.echo") as mock_echo:

                @heartbeat(0.05)
                def fn():
                    # Block deterministically until the heartbeat thread
                    # reaches its done.wait(0.05) call.
                    assert captured_signal.acquire(timeout=1.0), (
                        "heartbeat thread did not reach Event.wait(0.05) "
                        "within 1s"
                    )
                    return "result"

                assert fn() == "result"

        assert mock_echo.call_count >= 1, "heartbeat thread did not emit a ping"
        assert 0.05 in captured_timeouts, (
            f"heartbeat did not pass interval=0.05 to Event.wait; "
            f"captured={captured_timeouts}"
        )

    @patch("litassist.utils.core.click.echo", side_effect=OSError("Broken pipe"))
    def test_heartbeat_ping_thread_handles_exception(self, mock_echo):
        """Test that heartbeat ping thread handles exceptions without crashing."""
        # Remove PYTEST_CURRENT_TEST so click.echo is actually called in ping()
        env = os.environ.copy()
        env.pop("PYTEST_CURRENT_TEST", None)

        with patch.dict(os.environ, env, clear=True):

            def slow_function():
                time.sleep(0.1)
                return "done"

            decorated = heartbeat(0.01)(slow_function)
            result = decorated()

            assert result == "done"
            assert mock_echo.called


class TestReasoningPrompts:
    """Test reasoning prompt creation and extraction."""

    def test_create_reasoning_prompt_basic(self):
        """Test basic reasoning prompt creation."""
        base_prompt = "Analyze this contract case"
        command = "strategy"

        result = create_reasoning_prompt(base_prompt, command)

        assert base_prompt in result
        # Check that some form of strategic reasoning header is present
        assert (
            "Overall Strategic Reasoning" in result
            or "Overall Orthodox Strategic Reasoning" in result
            or "Overall Unorthodox Strategic Reasoning" in result
            or "Strategy Selection Reasoning" in result
        )
        assert "Issue:" in result
        assert "Applicable Law:" in result
        assert "Application to Facts:" in result
        assert "Conclusion:" in result

    def test_create_reasoning_prompt_empty_input(self):
        """Test reasoning prompt creation with empty input."""
        result = create_reasoning_prompt("", "strategy")

        # Should still contain reasoning structure
        assert "Strategic Reasoning" in result or "Selection Reasoning" in result
        assert "Issue:" in result

    def test_extract_reasoning_trace_valid_content(self):
        """Test extraction of reasoning trace from valid content."""
        content = """
        Some analysis content here.
        
        ## Overall Strategic Reasoning
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
        ## Overall Strategic Reasoning
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


class TestStrategyFileParsing:
    """Test strategy file parsing functionality."""

    def test_parse_strategies_file_complete_structure(self):
        """Test parsing of complete strategy file structure."""
        content = """## ORTHODOX STRATEGIES
### 1. Traditional contract claim
Standard approach using established precedents.

### 2. Alternative dispute resolution
Mediation and arbitration before litigation.

### 3. Statutory remedies
Consumer protection law applications.

## UNORTHODOX STRATEGIES
### Strategy 1: Novel legal theory
Innovative approach to the problem.

### Strategy 2: Strategic timing
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
### 1. Standard approach
Traditional method.

## MOST LIKELY TO SUCCEED
1. Best option
Highest success probability.
"""

        result = parse_strategies_file(content)

        assert result["orthodox_count"] == 1
        assert result["unorthodox_count"] == 0
        assert result["most_likely_count"] == 1

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
### 1. Standard claim
Traditional approach.
"""

        result = parse_strategies_file(content)

        assert result["orthodox_count"] == 1
        assert result["metadata"]["side"] == "Plaintiff"
        assert result["metadata"]["area"] == "Contract Law"


class TestContentVerification:
    """Test content verification functionality."""

    @patch("litassist.verification_chain.run_verification_chain")
    def test_verify_content_if_needed_enabled(self, mock_run_verification_chain):
        """Test content verification when enabled."""
        # Mock the verification chain for strategy command
        mock_run_verification_chain.return_value = (
            "Legal analysis content",
            {"llm": {"corrections_made": False}},
        )

        mock_client = MagicMock()
        mock_client.should_auto_verify.return_value = False
        mock_client.validate_citations.return_value = []

        content = "Legal analysis content"
        result_content, verified, _ = verify_content_if_needed(
            mock_client, content, "strategy", verify_flag=True
        )

        # Strategy command uses verification chain, returns False when no corrections
        assert verified is False
        assert result_content == content
        mock_run_verification_chain.assert_called_once_with(content, "strategy", heavy=False)

    @patch("litassist.verification_chain.run_verification_chain")
    def test_verify_content_if_needed_disabled(self, mock_run_verification_chain):
        """Test content verification when disabled."""
        # Mock the verification chain for strategy command
        mock_run_verification_chain.return_value = (
            "Legal analysis content",
            {"llm": {"corrections_made": False}},
        )

        mock_client = MagicMock()
        mock_client.should_auto_verify.return_value = False

        content = "Legal analysis content"
        result_content, verified, _ = verify_content_if_needed(
            mock_client, content, "strategy", verify_flag=False
        )

        # With verify_flag=False, verification is skipped
        assert verified is False
        assert result_content == content
        mock_run_verification_chain.assert_not_called()

    def test_verify_content_if_needed_llm_failure(self):
        """An LLM verify failure must propagate.

        Uses a non-high-risk command ("lookup") so verification goes through the
        passed client's verify() - the path the mock targets. High-risk commands
        (extractfacts/strategy/draft) route to run_verification_chain instead and
        ignore the passed client, so they would not exercise this mock.
        """
        mock_client = MagicMock()
        mock_client.should_auto_verify.return_value = False
        mock_client.verify.side_effect = Exception("LLM API error")

        content = "Legal analysis content"

        with pytest.raises(Exception):
            verify_content_if_needed(mock_client, content, "lookup", verify_flag=True)

    @patch("litassist.verification_chain.run_verification_chain")
    def test_verify_content_if_needed_with_corrections(
        self, mock_run_verification_chain
    ):
        """Test verification chain when corrections are made."""
        # Mock the verification chain to return corrections
        mock_run_verification_chain.return_value = (
            "Corrected legal analysis content",
            {"llm": {"corrections_made": True}},
        )

        mock_client = MagicMock()
        content = "Legal analysis content"

        result_content, verified, _ = verify_content_if_needed(
            mock_client, content, "strategy", verify_flag=True
        )

        # Should return corrected content and True when corrections made
        assert verified is True
        assert result_content == "Corrected legal analysis content"
        mock_run_verification_chain.assert_called_once_with(content, "strategy", heavy=False)

class TestErrorHandling:
    """Test error handling in utility functions."""

    def test_file_operations_disk_full(self):
        """Test file operations when disk is full."""
        with patch(
            "litassist.logging.output_saver.open",
            side_effect=OSError("No space left on device"),
        ):
            with pytest.raises(OSError):
                save_command_output("test", "content", "outcome")


# Integration test markers
pytestmark = [pytest.mark.unit, pytest.mark.utils, pytest.mark.offline]
