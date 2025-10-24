"""
Case facts validation for barbrief command.

Validates that case facts follow the required 10-heading format.
"""

from litassist.utils.core import timed


@timed
def validate_case_facts(content: str) -> bool:
    """
    Validate that case facts follow the 10-heading format.

    Args:
        content: The case facts content to validate

    Returns:
        True if valid, False otherwise
    """
    required_headings = [
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

    content_lower = content.lower()
    return all(heading.lower() in content_lower for heading in required_headings)
