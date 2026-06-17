"""Tests for OpenRouter actual-cost + generation-id capture and accumulation."""

from unittest.mock import Mock, patch

from litassist.llm.client import LLMClient
from litassist.llm.response_parser import extract_content_and_usage


def _resp(content, *, cost, gen_id, prompt=10, completion=20):
    r = Mock()
    r.id = gen_id
    r.choices = [Mock()]
    r.choices[0].message = Mock(content=content)
    r.choices[0].message.tool_calls = None
    r.choices[0].finish_reason = "stop"
    r.choices[0].error = None
    usage = {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": prompt + completion,
        "cost": cost,
    }
    r.usage = Mock(model_dump=lambda: dict(usage))
    return r


def test_response_parser_captures_cost_and_generation_id():
    _content, usage = extract_content_and_usage(
        _resp("hi", cost=0.0123, gen_id="gen-abc")
    )
    assert usage["cost"] == 0.0123
    assert usage["generation_id"] == "gen-abc"


@patch("litassist.config.CONFIG")
@patch("litassist.llm.client.execute_api_call_with_retry")
def test_complete_returns_actual_cost(mock_execute, mock_config):
    mock_config.or_key = "test_key"
    mock_execute.return_value = _resp("Answer", cost=0.5, gen_id="gen-1")

    client = LLMClient(model="anthropic/claude-sonnet-4.6", temperature=0.2)
    _content, usage = client.complete(
        [{"role": "user", "content": "Q"}], skip_citation_verification=True
    )
    assert usage["cost"] == 0.5
    assert usage["generation_ids"] == ["gen-1"]


@patch("litassist.config.CONFIG")
@patch("litassist.llm.client.execute_api_call_with_retry")
def test_complete_sums_cost_across_two_billed_calls(mock_execute, mock_config):
    """The empty-response fallback makes a SECOND billed call; the returned cost
    must be the sum of both, not just the final response (the undercount bug)."""
    mock_config.or_key = "test_key"
    # First call returns empty content + no tool_calls -> triggers fallback call.
    empty = _resp("", cost=0.30, gen_id="gen-first")
    final = _resp("Final answer", cost=0.20, gen_id="gen-second")
    mock_execute.side_effect = [empty, final]

    # disable_tools False (default) so the empty-response fallback path runs.
    client = LLMClient(model="anthropic/claude-sonnet-4.6", temperature=0.2)
    _content, usage = client.complete(
        [{"role": "user", "content": "Q"}], skip_citation_verification=True
    )
    assert mock_execute.call_count == 2
    assert usage["cost"] == 0.5  # 0.30 + 0.20, not just the final 0.20
    assert usage["generation_ids"] == ["gen-first", "gen-second"]
