"""
Document generation functions for strategy command.

This module handles the generation of legal documents based on strategy analysis.
"""

import click
from litassist.prompts import PROMPTS


def determine_document_type(outcome: str) -> str:
    """
    Determine the appropriate document type based on the desired outcome.

    Args:
        outcome: The desired legal outcome

    Returns:
        Document type string ('claim', 'application', or 'affidavit')
    """
    outcome_lower = outcome.lower()

    # Default to statement of claim
    doc_type = "claim"

    # Check for injunction/application indicators
    if any(
        term in outcome_lower
        for term in [
            "injunct",
            "restrain",
            "order",
            "declaration",
            "specific performance",
        ]
    ):
        doc_type = "application"
    elif any(
        term in outcome_lower for term in ["affidavit", "evidence", "witness", "sworn"]
    ):
        doc_type = "affidavit"

    return doc_type


def generate_draft_document(
    llm_client,
    system_prompt: str,
    user_prompt: str,
    strategy_content: str,
    outcome: str,
    doc_type: str = None,
) -> str:
    """
    Generate a draft legal document based on strategy analysis.

    Args:
        llm_client: The LLM client for generation
        system_prompt: System prompt for the LLM
        user_prompt: User prompt containing case facts
        strategy_content: Generated strategy content
        outcome: Desired legal outcome
        doc_type: Document type (if None, will be determined automatically)

    Returns:
        Generated document content

    Raises:
        click.ClickException: If document generation fails
    """
    if doc_type is None:
        doc_type = determine_document_type(outcome)

    # Get document format templates
    doc_formats = {
        "claim": PROMPTS.get("documents.statement_of_claim"),
        "application": PROMPTS.get("documents.originating_application"),
        "affidavit": PROMPTS.get("documents.affidavit"),
    }

    # Use centralized document generation context
    doc_context = PROMPTS.get("strategies.strategy.document_generation_context")
    doc_prompt = f"""{
        doc_context.format(
            recommended_strategy=f"draft a {doc_type.upper()} to achieve the outcome: '{outcome}'"
        )
    }

{doc_formats.get(doc_type, doc_formats["claim"])}"""

    try:
        document_content, _ = llm_client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": strategy_content},
                {"role": "user", "content": doc_prompt},
            ]
        )
        return document_content
    except Exception as e:
        raise click.ClickException(f"LLM document generation error: {e}")
