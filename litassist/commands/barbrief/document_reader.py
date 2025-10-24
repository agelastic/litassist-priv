"""
Document reading and input processing for barbrief command.

Handles reading of case facts, strategies, research, and supporting documents.
"""

import click
from typing import Tuple, Dict

from litassist.utils.file_ops import read_document
from litassist.utils.text_processing import count_tokens_and_words
from litassist.utils.formatting import warning_message


def read_all_documents(
    case_facts: str,
    strategies: Tuple[str, ...],
    research: Tuple[str, ...],
    documents: Tuple[str, ...]
) -> Dict[str, any]:
    """
    Read and consolidate all input documents.

    Args:
        case_facts: Path to case facts file
        strategies: Tuple of strategy file paths
        research: Tuple of research file paths
        documents: Tuple of supporting document paths

    Returns:
        Dictionary containing all read content and metadata

    Raises:
        click.ClickException: If file reading fails
    """
    # Read case facts
    click.echo("Reading case facts...")
    case_facts_content = read_document(case_facts)

    # Read optional strategy files
    strategies_content = ""
    if strategies:
        if len(strategies) == 1:
            click.echo("Reading strategies...")
            strategies_content = read_document(strategies[0])
        else:
            click.echo(f"Reading {len(strategies)} strategy files...")
            strategy_parts = []
            for strategy_file in strategies:
                content = read_document(strategy_file)
                strategy_parts.append(
                    f"=== SOURCE: {strategy_file} ===\n{content}\n=== END SOURCE: {strategy_file} ==="
                )
            strategies_content = "\n\n".join(strategy_parts)

    # Read research documents
    research_docs = []
    for research_file in research:
        click.echo(f"Reading research: {research_file}")
        research_docs.append(read_document(research_file))

    # Read supporting documents
    supporting_docs = []
    for doc_file in documents:
        click.echo(f"Reading document: {doc_file}")
        supporting_docs.append(read_document(doc_file))

    return {
        "case_facts_content": case_facts_content,
        "strategies_content": strategies_content,
        "research_docs": research_docs,
        "supporting_docs": supporting_docs,
    }


def estimate_input_size(content_dict: Dict[str, any]) -> None:
    """
    Estimate total input size and warn if large.

    Args:
        content_dict: Dictionary containing all document content
    """
    total_content = (
        content_dict["case_facts_content"]
        + "\n"
        + content_dict["strategies_content"]
        + "\n"
        + "\n".join(content_dict["research_docs"])
        + "\n"
        + "\n".join(content_dict["supporting_docs"])
    )
    total_tokens, _ = count_tokens_and_words(total_content)

    # Warn if large
    if total_tokens > 80000:
        click.echo(
            warning_message(
                f"Large input detected ({total_tokens:,} tokens). "
                f"This may exceed API limits. Consider using fewer documents."
            )
        )
