"""Unit tests for brainstorm strategy extraction (Defect 1a: fail loud on refusal).

`_extract_strategies` previously fell back to splitting on blank lines and
returning up to 15 chunks when no `### Strategy N:` headers were present. That
turned a model refusal (no headers) into 15 fabricated "strategies", which the
stricter final counter `parse_strategies_file` then reported as 0 - masking the
refusal with no error. These tests pin the corrected, fail-loud behaviour:
no headers -> no strategies (empty list), and well-formed headers still parse.
"""

from litassist.commands.brainstorm.core import _extract_strategies


REFUSAL_BLOB = """I must decline to generate the requested unorthodox legal strategies.

The request asks me to produce boundary-pushing tactics that risk encouraging
improper conduct inconsistent with the complainant's obligations.

I will not fabricate strategies that have no established precedent, as doing so
would risk presenting misleading material as grounded legal strategy.

I am able to provide orthodox advice on strengthening the complaint using the
existing evidence if the request is reframed in that conventional direction.
"""


def test_extract_strategies_returns_empty_on_refusal():
    """A refusal with no strategy headers must yield zero strategies, not
    fabricated blank-line-split chunks."""
    assert _extract_strategies(REFUSAL_BLOB, "unorthodox") == []


def test_extract_strategies_parses_wellformed_headers():
    """Well-formed `### Strategy N:` output must still parse (guards the fix
    against zeroing out legitimate strategies)."""
    content = (
        "## UNORTHODOX STRATEGIES\n\n"
        "### Strategy 1: Establish breach of disclosure obligations\n"
        "Reasoning for strategy one.\n\n"
        "### Strategy 2: Seek compensation orders\n"
        "Reasoning for strategy two.\n"
    )
    result = _extract_strategies(content, "unorthodox")
    assert len(result) == 2
    assert result[0].startswith("### Strategy 1:")
    assert result[1].startswith("### Strategy 2:")
