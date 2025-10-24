"""
Brief section preparation for barbrief command.

Handles preparation of sections and content for the barrister's brief.
"""

from typing import List, Optional, Dict, Any
from litassist.utils.core import timed


@timed
def prepare_brief_sections(
    case_facts: str,
    strategies: Optional[str],
    research_docs: List[str],
    supporting_docs: List[str],
    context: Optional[str],
    hearing_type: str,
) -> Dict[str, Any]:
    """
    Prepare the sections and content for the barrister's brief.

    Args:
        case_facts: Structured case facts content
        strategies: Optional brainstormed strategies
        research_docs: List of research/lookup reports
        supporting_docs: List of supporting documents
        context: Optional additional context
        hearing_type: Type of hearing

    Returns:
        Dictionary containing prepared sections
    """
    sections = {
        "case_facts": case_facts,
        "hearing_type": hearing_type,
        "has_strategies": bool(strategies),
        "strategies": strategies or "",
        "research_count": len(research_docs),
        "research_content": "\n\n---\n\n".join(research_docs),
        "supporting_count": len(supporting_docs),
        "supporting_content": "\n\n---\n\n".join(supporting_docs),
        "context": context or "No specific context provided.",
    }

    return sections
