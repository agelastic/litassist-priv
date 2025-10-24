"""
Document processing for draft command.

Handles document reading, categorization, and context building.
"""

import click
from typing import Dict, Tuple

from litassist.utils.file_ops import read_document, is_text_file
from litassist.logging import log_task_event


def read_and_categorize_documents(documents: Tuple[str]) -> Dict:
    """
    Read and categorize documents into structured content.

    Args:
        documents: Tuple of document paths

    Returns:
        Dict with keys: case_facts, strategies, other_text, pdf_documents
    """
    try:
        log_task_event(
            "draft",
            "reading",
            "start",
            "Reading input documents"
        )
    except Exception:
        pass

    structured_content = {
        "case_facts": "",
        "strategies": "",
        "other_text": [],
        "pdf_documents": [],
    }

    for doc_path in documents:
        text = read_document(doc_path)

        # Categorize documents by type - separate file type check from size check
        if is_text_file(doc_path):
            # For text files, categorize by content and handle large files appropriately
            if "case_facts" in doc_path.lower():
                if len(text) < 400000:
                    structured_content["case_facts"] = text
                    click.echo(
                        f"Using {doc_path} as CASE FACTS ({len(text)} characters)"
                    )
                else:
                    # Large case facts file - use embedding/retrieval
                    structured_content["pdf_documents"].append((doc_path, text))
                    click.echo(f"Will use embedding/retrieval for large {doc_path}")
            elif "strategies" in doc_path.lower() or "# Legal Strategies" in text:
                if len(text) < 400000:
                    structured_content["strategies"] = text
                    click.echo(
                        f"Using {doc_path} as LEGAL STRATEGIES ({len(text)} characters)"
                    )
                else:
                    # Large strategies file - use embedding/retrieval
                    structured_content["pdf_documents"].append((doc_path, text))
                    click.echo(f"Will use embedding/retrieval for large {doc_path}")
            else:
                if len(text) < 400000:
                    structured_content["other_text"].append((doc_path, text))
                    click.echo(
                        f"Using {doc_path} as supporting document ({len(text)} characters)"
                    )
                else:
                    # Large text file - use embedding/retrieval
                    structured_content["pdf_documents"].append((doc_path, text))
                    click.echo(f"Will use embedding/retrieval for large {doc_path}")
        else:
            # PDF files always use embedding/retrieval
            structured_content["pdf_documents"].append((doc_path, text))
            click.echo(f"Will use embedding/retrieval for {doc_path}")

    try:
        log_task_event(
            "draft",
            "reading",
            "end",
            f"Read {len(documents)} document(s)"
        )
    except Exception:
        pass

    return structured_content


def build_text_context(structured_content: Dict) -> str:
    """
    Build structured context from categorized documents.

    Args:
        structured_content: Dict with case_facts, strategies, other_text

    Returns:
        Combined text context with === markers
    """
    context_parts = []

    if structured_content["case_facts"]:
        context_parts.append(
            "=== CASE FACTS ===\n"
            + structured_content["case_facts"]
            + "\n=== END CASE FACTS ==="
        )

    if structured_content["strategies"]:
        context_parts.append(
            "=== LEGAL STRATEGIES FROM BRAINSTORMING ===\n"
            + structured_content["strategies"]
            + "\n=== END LEGAL STRATEGIES FROM BRAINSTORMING ==="
        )

    for doc_path, text in structured_content["other_text"]:
        context_parts.append(
            f"=== SUPPORTING DOCUMENT: {doc_path} ===\n{text}\n=== END SUPPORTING DOCUMENT: {doc_path} ==="
        )

    combined_text_context = "\n\n".join(context_parts) if context_parts else ""

    return combined_text_context
