"""
Offline unit tests for the pure functions in test-scripts/test_judge_eval.py
(the P-JUDGE eval harness). The harness itself makes real API calls and is
run manually; these tests cover only its parsing/scoring logic, which is
stdlib-only and importable without config.yaml.
"""

import importlib.util
import json
from pathlib import Path

import pytest

HARNESS_PATH = (
    Path(__file__).parent.parent.parent / "test-scripts" / "test_judge_eval.py"
)

spec = importlib.util.spec_from_file_location("judge_eval_harness", HARNESS_PATH)
harness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(harness)


def make_response(payload, prefix="Some working analysis.\n", suffix=""):
    """Build a judge response string around a JSON payload."""
    return (
        f"{prefix}{harness.JUDGE_START}\n"
        f"{json.dumps(payload)}\n"
        f"{harness.JUDGE_END}{suffix}"
    )


VALID_PAYLOAD = {
    "case_id": "case1",
    "dimensions": {
        "citation_grounding": {
            "score": 80,
            "band": "good",
            "rationale": "r",
            "flags": [],
        },
        "faithfulness": {
            "score": 90,
            "band": "excellent",
            "rationale": "r",
            "flags": ["x"],
        },
    },
    "context_starved_citations": [
        {
            "cite": "(1999) 201 CLR 1",
            "retrieval_class": "authorised_report",
            "judge_could_verify_from_sources": False,
        }
    ],
    "overall": 85,
    "summary": "s",
}


class TestExtractJudgeJson:
    def test_valid_block_parses(self):
        parsed = harness.extract_judge_json(make_response(VALID_PAYLOAD))
        assert parsed["case_id"] == "case1"
        assert parsed["dimensions"]["citation_grounding"]["score"] == 80

    def test_trailing_whitespace_tolerated(self):
        parsed = harness.extract_judge_json(
            make_response(VALID_PAYLOAD, suffix="\n   \n")
        )
        assert parsed["case_id"] == "case1"

    def test_missing_start_marker_raises(self):
        text = json.dumps(VALID_PAYLOAD) + "\n" + harness.JUDGE_END
        with pytest.raises(harness.JudgeFormatError):
            harness.extract_judge_json(text)

    def test_missing_end_marker_raises(self):
        text = harness.JUDGE_START + "\n" + json.dumps(VALID_PAYLOAD)
        with pytest.raises(harness.JudgeFormatError):
            harness.extract_judge_json(text)

    def test_invalid_json_raises(self):
        text = f"{harness.JUDGE_START}\nnot json at all\n{harness.JUDGE_END}"
        with pytest.raises(harness.JudgeFormatError):
            harness.extract_judge_json(text)

    def test_content_after_end_marker_raises(self):
        with pytest.raises(harness.JudgeFormatError):
            harness.extract_judge_json(
                make_response(VALID_PAYLOAD, suffix="\ntrailing prose")
            )


class TestValidateDimensions:
    def test_exact_match_passes(self):
        harness.validate_dimensions(
            VALID_PAYLOAD, ["citation_grounding", "faithfulness"]
        )

    def test_missing_declared_dimension_raises(self):
        with pytest.raises(harness.JudgeFormatError):
            harness.validate_dimensions(
                VALID_PAYLOAD,
                ["citation_grounding", "faithfulness", "structure"],
            )

    def test_undeclared_extra_dimension_raises(self):
        with pytest.raises(harness.JudgeFormatError):
            harness.validate_dimensions(VALID_PAYLOAD, ["citation_grounding"])

    def test_score_out_of_range_raises(self):
        bad = json.loads(json.dumps(VALID_PAYLOAD))
        bad["dimensions"]["faithfulness"]["score"] = 101
        with pytest.raises(harness.JudgeFormatError):
            harness.validate_dimensions(bad, ["citation_grounding", "faithfulness"])

    def test_non_integer_score_raises(self):
        bad = json.loads(json.dumps(VALID_PAYLOAD))
        bad["dimensions"]["faithfulness"]["score"] = "90"
        with pytest.raises(harness.JudgeFormatError):
            harness.validate_dimensions(bad, ["citation_grounding", "faithfulness"])

    def test_invalid_band_raises(self):
        bad = json.loads(json.dumps(VALID_PAYLOAD))
        bad["dimensions"]["faithfulness"]["band"] = "superb"
        with pytest.raises(harness.JudgeFormatError):
            harness.validate_dimensions(bad, ["citation_grounding", "faithfulness"])

    def test_boolean_score_raises(self):
        bad = json.loads(json.dumps(VALID_PAYLOAD))
        bad["dimensions"]["faithfulness"]["score"] = True
        with pytest.raises(harness.JudgeFormatError):
            harness.validate_dimensions(bad, ["citation_grounding", "faithfulness"])

    def test_non_dict_payload_raises_format_error(self):
        with pytest.raises(harness.JudgeFormatError):
            harness.validate_dimensions([], ["citation_grounding"])

    def test_null_dimension_entry_raises_format_error(self):
        bad = json.loads(json.dumps(VALID_PAYLOAD))
        bad["dimensions"]["faithfulness"] = None
        with pytest.raises(harness.JudgeFormatError):
            harness.validate_dimensions(bad, ["citation_grounding", "faithfulness"])


class TestScoring:
    def test_recompute_overall_mean(self):
        dims = {
            "a": {"score": 80},
            "b": {"score": 90},
        }
        assert harness.recompute_overall(dims) == 85

    def test_recompute_overall_rounds(self):
        dims = {
            "a": {"score": 80},
            "b": {"score": 85},
        }
        # mean 82.5; round-half-to-even gives 82
        assert harness.recompute_overall(dims) == 82

    def test_grounding_coverage_no_citations_is_full(self):
        assert harness.grounding_coverage(0, 0) == 1.0

    def test_grounding_coverage_partial(self):
        assert harness.grounding_coverage(4, 1) == 0.75

    def test_grounding_cap_applies(self):
        assert harness.apply_grounding_cap(95, 0.75) == 75

    def test_grounding_cap_no_effect_below_ceiling(self):
        assert harness.apply_grounding_cap(60, 0.75) == 60

    def test_recompute_overall_empty_raises_format_error(self):
        with pytest.raises(harness.JudgeFormatError):
            harness.recompute_overall({})


class TestBaselineComparison:
    BASELINE = {
        "tolerance": 8,
        "cases": {
            "case1": {"citation_grounding": 80, "faithfulness": 90},
        },
    }

    def test_within_tolerance_no_regression(self):
        results = {"case1": {"citation_grounding": 73, "faithfulness": 95}}
        regressions, _ = harness.compare_to_baseline(results, self.BASELINE)
        assert regressions == []

    def test_below_tolerance_is_regression(self):
        results = {"case1": {"citation_grounding": 71, "faithfulness": 90}}
        regressions, _ = harness.compare_to_baseline(results, self.BASELINE)
        assert len(regressions) == 1
        assert "citation_grounding" in regressions[0]

    def test_improvement_is_note_not_regression(self):
        results = {"case1": {"citation_grounding": 80, "faithfulness": 99}}
        regressions, notes = harness.compare_to_baseline(results, self.BASELINE)
        assert regressions == []
        assert any("faithfulness" in n for n in notes)

    def test_new_case_is_note_not_regression(self):
        results = {"case_new": {"citation_grounding": 50}}
        regressions, notes = harness.compare_to_baseline(results, self.BASELINE)
        assert regressions == []
        assert any("case_new" in n for n in notes)

    def test_empty_baseline_dict_no_crash(self):
        results = {"case1": {"citation_grounding": 73}}
        regressions, notes = harness.compare_to_baseline(results, {})
        assert regressions == []
        assert any("case1" in n for n in notes)


class TestScoreCase:
    def make_case(self):
        return {
            "case_id": "case1",
            "dimensions": ["citation_grounding", "faithfulness"],
            "expected_citations": [
                {
                    "cite": "(1999) 201 CLR 1",
                    "fetchable": False,
                    "retrieval_class": "authorised_report",
                },
                {
                    "cite": "Smith v Jones [2020] HCA 1",
                    "fetchable": True,
                    "retrieval_class": "fetchable",
                },
            ],
        }

    def test_cap_feeds_recomputed_overall(self):
        # judge: grounding 100, faithfulness 90; one of two cites starved ->
        # coverage 0.5 caps grounding at 50, overall = mean(50, 90) = 70
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["dimensions"]["citation_grounding"]["score"] = 100
        response = make_response(payload)
        result = harness.score_case(self.make_case(), response)
        assert result["grounding_coverage"] == 0.5
        assert result["dimensions"]["citation_grounding"] == 50
        assert result["overall"] == 70
        assert result["capped_note"]

    def test_unmatched_starved_cite_surfaced(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["context_starved_citations"].append(
            {
                "cite": "Unknown v Nobody [1900] FAKE 1",
                "retrieval_class": "authorised_report",
                "judge_could_verify_from_sources": False,
            }
        )
        result = harness.score_case(self.make_case(), make_response(payload))
        assert result["unmatched_starved_cites"] == ["Unknown v Nobody [1900] FAKE 1"]
        # unmatched cites do not affect coverage
        assert result["grounding_coverage"] == 0.5

    def test_case_id_mismatch_raises(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["case_id"] = "other"
        with pytest.raises(harness.JudgeFormatError):
            harness.score_case(self.make_case(), make_response(payload))

    def test_missing_starved_array_raises(self):
        # fail closed: a missing context-starvation report must never be
        # treated as "everything verified" (coverage 1.0, no cap)
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        del payload["context_starved_citations"]
        with pytest.raises(harness.JudgeFormatError):
            harness.score_case(self.make_case(), make_response(payload))

    def test_null_starved_array_raises(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["context_starved_citations"] = None
        with pytest.raises(harness.JudgeFormatError):
            harness.score_case(self.make_case(), make_response(payload))

    def test_non_dict_starved_entry_raises(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["context_starved_citations"] = ["(1999) 201 CLR 1"]
        with pytest.raises(harness.JudgeFormatError):
            harness.score_case(self.make_case(), make_response(payload))

    def test_starved_entry_without_cite_raises(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["context_starved_citations"] = [{"retrieval_class": "authorised_report"}]
        with pytest.raises(harness.JudgeFormatError):
            harness.score_case(self.make_case(), make_response(payload))

    def test_empty_starved_array_means_full_coverage(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["context_starved_citations"] = []
        result = harness.score_case(self.make_case(), make_response(payload))
        assert result["grounding_coverage"] == 1.0

    def test_dict_starved_value_raises(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["context_starved_citations"] = {}
        with pytest.raises(harness.JudgeFormatError):
            harness.score_case(self.make_case(), make_response(payload))

    def test_non_string_cite_in_starved_entry_raises(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["context_starved_citations"] = [
            {"cite": 42, "retrieval_class": "authorised_report"}
        ]
        with pytest.raises(harness.JudgeFormatError):
            harness.score_case(self.make_case(), make_response(payload))

    def test_mixed_valid_invalid_starved_entries_raise(self):
        payload = json.loads(json.dumps(VALID_PAYLOAD))
        payload["context_starved_citations"].append("not an object")
        with pytest.raises(harness.JudgeFormatError):
            harness.score_case(self.make_case(), make_response(payload))


class TestCitationsTable:
    def test_table_lists_cite_and_class(self):
        expected = [
            {
                "cite": "Smith v Jones [2020] HCA 1",
                "fetchable": True,
                "retrieval_class": "fetchable",
            },
            {
                "cite": "(1999) 201 CLR 1",
                "fetchable": False,
                "retrieval_class": "authorised_report",
            },
        ]
        table = harness.build_citations_table(expected)
        assert "Smith v Jones [2020] HCA 1 | fetchable" in table
        assert "(1999) 201 CLR 1 | authorised_report" in table
