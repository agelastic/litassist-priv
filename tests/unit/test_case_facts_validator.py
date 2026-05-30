"""Tests for the shared 10-heading case-facts validator.

The validator must accept the formats `extractfacts` is actually told to
produce (numbered/bold headings with the description inline) as well as the
plain own-line style, so that downstream commands (strategy, barbrief) do not
reject genuine extractfacts output.
"""

from litassist.prompts import PROMPTS
from litassist.utils.case_facts import validate_case_facts_format

_HEADINGS = [
    "Parties",
    "Background",
    "Key Events",
    "Legal Issues",
    "Evidence Available",
    "Opposing Arguments",
    "Procedural History",
    "Jurisdiction",
    "Applicable Law",
    "Client Objectives",
]


def test_accepts_extractfacts_format_template():
    """The exact case_facts_10_heading template must validate."""
    template = PROMPTS.get_format_template("case_facts_10_heading")
    assert validate_case_facts_format(template) is True


def test_accepts_numbered_bold_inline_headings():
    """`N. **Heading**: description` (extractfacts style) must validate."""
    content = "\n".join(
        f"{i}. **{h}**: some description text" for i, h in enumerate(_HEADINGS, 1)
    )
    assert validate_case_facts_format(content) is True


def test_accepts_own_line_headings():
    """`Heading:` on its own line with content on the next line must validate."""
    content = "\n".join(f"{h}:\nsome content" for h in _HEADINGS)
    assert validate_case_facts_format(content) is True


def test_rejects_missing_heading():
    content = "\n".join(f"{h}:\nx" for h in _HEADINGS if h != "Jurisdiction")
    assert validate_case_facts_format(content) is False


def test_does_not_match_heading_word_mid_prose():
    """A heading word buried mid-sentence is not a heading line."""
    content = "\n".join(f"{h}:\nx" for h in _HEADINGS if h != "Parties")
    content += "\nthe parties later agreed to settle"  # not a heading line
    assert validate_case_facts_format(content) is False
