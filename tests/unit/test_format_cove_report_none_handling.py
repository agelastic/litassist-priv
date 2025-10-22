"""Test that format_cove_report handles None values gracefully.

This test ensures the fix for the TypeError bug where format_cove_report
would fail with "sequence item 10: expected str instance, NoneType found"
when any of the cove_data values were None.
"""

from litassist.verification_chain import format_cove_report


class TestFormatCoveReportNoneHandling:
    """Test format_cove_report handles None values correctly."""

    def test_handles_none_questions(self):
        """Should handle None questions value gracefully."""
        cove_results = {
            "cove": {
                "questions": None,  # Explicitly None
                "answers": "Some answers",
                "issues": "Some issues",
                "passed": False,
            }
        }
        report = format_cove_report(cove_results)
        assert "No questions generated" in report
        assert isinstance(report, str)

    def test_handles_none_answers(self):
        """Should handle None answers value gracefully."""
        cove_results = {
            "cove": {
                "questions": "Some questions",
                "answers": None,  # Explicitly None
                "issues": "Some issues",
                "passed": False,
            }
        }
        report = format_cove_report(cove_results)
        assert "No answers generated" in report
        assert isinstance(report, str)

    def test_handles_none_issues(self):
        """Should handle None issues value gracefully."""
        cove_results = {
            "cove": {
                "questions": "Some questions",
                "answers": "Some answers",
                "issues": None,  # Explicitly None - this was item 10 in the error
                "passed": True,
            }
        }
        report = format_cove_report(cove_results)
        assert "No issues checked" in report
        assert isinstance(report, str)

    def test_handles_all_none_values(self):
        """Should handle all None values gracefully."""
        cove_results = {
            "cove": {
                "questions": None,
                "answers": None,
                "issues": None,
                "passed": False,
            }
        }
        report = format_cove_report(cove_results)
        assert "No questions generated" in report
        assert "No answers generated" in report
        assert "No issues checked" in report
        assert isinstance(report, str)

    def test_handles_missing_cove_key(self):
        """Should handle missing cove key gracefully."""
        cove_results = {}
        report = format_cove_report(cove_results)
        assert "No questions generated" in report
        assert "No answers generated" in report
        assert "No issues checked" in report
        assert isinstance(report, str)

    def test_handles_empty_cove_dict(self):
        """Should handle empty cove dict gracefully."""
        cove_results = {"cove": {}}
        report = format_cove_report(cove_results)
        assert "No questions generated" in report
        assert "No answers generated" in report
        assert "No issues checked" in report
        assert isinstance(report, str)

    def test_normal_case_still_works(self):
        """Should still work correctly with normal string values."""
        cove_results = {
            "cove": {
                "questions": "Question 1\nQuestion 2",
                "answers": "Answer 1\nAnswer 2",
                "issues": "Issue 1\nIssue 2",
                "passed": False,
            }
        }
        report = format_cove_report(cove_results)
        assert "Question 1" in report
        assert "Answer 1" in report
        assert "Issue 1" in report
        assert "ISSUES FOUND" in report
        assert isinstance(report, str)
