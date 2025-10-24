"""
Prompt construction for draft command.

Builds system and user prompts based on available content.
"""

from typing import Dict

from litassist.prompts import PROMPTS
from litassist.utils.legal_reasoning import create_reasoning_prompt


def build_system_prompt(structured_content: Dict) -> str:
    """
    Build system prompt based on available content types.

    Args:
        structured_content: Dict with case_facts, strategies, other_text

    Returns:
        Complete system prompt string
    """
    system_prompt = PROMPTS.get("processing.draft.system_prompt_base")

    if structured_content["case_facts"] and structured_content["strategies"]:
        system_prompt += PROMPTS.get(
            "processing.draft.context_case_facts_and_strategies"
        )
    elif structured_content["case_facts"]:
        system_prompt += PROMPTS.get("processing.draft.context_case_facts_only")
    elif structured_content["strategies"]:
        system_prompt += PROMPTS.get("processing.draft.context_strategies_only")

    system_prompt += PROMPTS.get("processing.draft.general_instructions")

    return system_prompt


def build_user_prompt(query: str, context: str) -> str:
    """
    Build user prompt with context and reasoning trace.

    Args:
        query: Document type or drafting query
        context: Combined context string

    Returns:
        Complete user prompt with reasoning trace
    """
    # Create user prompt using centralized template
    user_template = PROMPTS.get("processing.draft.user_prompt_template")
    base_user_prompt = user_template.format(
        document_type=query, user_request=f"Context:\n{context}"
    )

    # Add reasoning trace to user prompt
    user_prompt = create_reasoning_prompt(base_user_prompt, "draft")

    return user_prompt
