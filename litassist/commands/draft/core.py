"""
Citation-rich drafting via RAG & GPT-4o.

This module implements the 'draft' command which uses Retrieval-Augmented Generation
to create well-supported legal drafts. The process embeds document chunks, stores them
in Pinecone, retrieves relevant passages using MMR re-ranking, and generates a draft
with GPT-4o that incorporates these citations.
"""

import click

from litassist.logging import save_log, save_command_output, log_task_event
from litassist.timing import timed
from litassist.utils.formatting import info_message
from litassist.utils.legal_reasoning import (
    detect_factual_hallucinations,
    verify_content_if_needed,
)
from litassist.utils.core import show_command_completion
from litassist.llm.factory import LLMClientFactory

from .document_processor import read_and_categorize_documents, build_text_context
from .rag_pipeline import process_documents_with_rag
from .prompt_builder import build_system_prompt, build_user_prompt


@click.command()
@click.argument("documents", nargs=-1, required=True, type=click.Path(exists=True))
@click.argument("query")
@click.option(
    "--noverify",
    is_flag=True,
    help="Skip standard verification",
)
@click.option(
    "--diversity",
    type=float,
    help="Control diversity of search results (0.0-1.0)",
    default=None,
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.pass_context
@timed
def draft(ctx, documents, query, noverify, diversity, output):
    """
    Citation-rich drafting via RAG & GPT-4o.

    For text files under 400KB (like case_facts.txt), passes the entire content
    directly to the LLM for comprehensive drafting. For PDFs or larger files,
    implements a Retrieval-Augmented Generation workflow that embeds document
    chunks, stores them in Pinecone, and retrieves relevant passages using
    MMR re-ranking.

    Accepts multiple documents to combine knowledge from different sources
    (e.g., case_facts.txt and strategies.txt).

    Args:
        documents: One or more paths to documents (PDF or text files) to use as knowledge base.
                  Examples:
                  - litassist draft case_facts.txt "query"
                  - litassist draft case_facts.txt strategies.txt "query"
                  - litassist draft bundle.pdf case_facts.txt "query"
        query: The specific legal topic or argument to draft.
        diversity: Optional float (0.0-1.0) controlling the balance between
                  relevance and diversity in retrieved passages. Higher values
                  prioritize diversity over relevance. (Only used for PDFs/large files)

    Raises:
        click.ClickException: If there are errors with file reading, embedding,
                             vector storage, retrieval, or LLM API calls.
    """
    # Command start log
    try:
        log_task_event(
            "draft",
            "init",
            "start",
            "Starting draft generation",
            {"model": LLMClientFactory.get_model_for_command("draft")},
        )
    except Exception:
        pass

    # Process all documents
    structured_content = read_and_categorize_documents(documents)

    # Build structured context for the LLM
    combined_text_context = build_text_context(structured_content)

    # Process PDFs with embedding/retrieval if any
    retrieved_context = ""
    if structured_content["pdf_documents"]:
        retrieved_context = process_documents_with_rag(
            structured_content["pdf_documents"],
            query,
            diversity
        )

    # Combine all context with proper === separation
    context = combined_text_context
    if retrieved_context:
        if context:
            # Retrieved context already has its own END marker from above
            context = context + "\n\n" + retrieved_context
        else:
            context = retrieved_context

    # Build prompts
    system_prompt = build_system_prompt(structured_content)
    user_prompt = build_user_prompt(query, context)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Generate draft with LLM
    client = LLMClientFactory.for_command("draft")

    try:
        log_task_event(
            "draft",
            "generation",
            "llm_call",
            "Sending draft generation prompt to LLM",
            {"model": client.model}
        )
    except Exception:
        pass

    try:
        content, usage = client.complete(messages)

        try:
            log_task_event(
                "draft",
                "generation",
                "llm_response",
                "Draft LLM response received",
                {"model": client.model}
            )
        except Exception:
            pass
    except Exception as e:
        raise click.ClickException(f"LLM draft error: {e}")

    # Note: Citation verification now handled automatically in LLMClient.complete()

    # Apply standard verification (uses verification chain like extractfacts/strategy)
    if not noverify:
        try:
            log_task_event(
                "draft",
                "verification",
                "start",
                "Starting draft verification"
            )
        except Exception:
            pass

        content, _ = verify_content_if_needed(
            client, content, "draft", verify_flag=True
        )
        click.echo(info_message("Standard verification applied"))

        try:
            log_task_event(
                "draft",
                "verification",
                "end",
                "Verification complete"
            )
        except Exception:
            pass
    else:
        click.echo(info_message("Standard verification skipped by --noverify flag"))

    # Track critiques for appending to output
    critiques = []

    # Check for potential hallucinations
    try:
        log_task_event(
            "draft",
            "hallucination",
            "start",
            "Checking for potential hallucinations"
        )
    except Exception:
        pass

    hallucination_warnings = detect_factual_hallucinations(content, context)

    try:
        log_task_event(
            "draft",
            "hallucination",
            "end",
            f"Hallucination check complete - {len(hallucination_warnings) if hallucination_warnings else 0} warnings"
        )
    except Exception:
        pass
    if hallucination_warnings:
        # Capture hallucination warnings for critique section
        warning_text = "The following potentially hallucinated facts were detected:\n"
        for warning in hallucination_warnings:
            warning_text += f"- {warning}\n"
        warning_text += (
            "\nPlease verify all facts against source documents before use.\n"
        )
        warning_text += (
            "Replace any invented details with placeholders like [TO BE PROVIDED]."
        )
        critiques.append(("Factual Accuracy Warning", warning_text))

        # Also add to main content for visibility
        warning_header = "# FACTUAL ACCURACY WARNING\n\n"
        warning_header += (
            "The following potentially hallucinated facts were detected:\n"
        )
        for warning in hallucination_warnings:
            warning_header += f"- {warning}\n"
        warning_header += (
            "\nPlease verify all facts against source documents before use.\n"
        )
        warning_header += (
            "Replace any invented details with placeholders like [TO BE PROVIDED].\n\n"
        )
        warning_header += "---\n\n"
        content = warning_header + content

    # Save output using utility
    output_file = save_command_output(
        output if output else "draft",
        content,
        "" if output else query,
        metadata={"Query": query, "Documents": ", ".join(documents)},
        critique_sections=critiques if critiques else None,
    )

    # Reasoning trace is embedded in the main output, not saved separately
    extra_files = None

    # Save audit log (without response content)
    save_log(
        "draft",
        {
            "inputs": {
                "documents": list(documents),
                "query": query,
                "context": context if context else None,
            },
            # Response content removed - already logged by LLMClient separately
            "usage": usage,
            "verification": "standard" if not noverify else "disabled",
            "output_file": output_file,
        },
    )

    # Show completion with preview
    stats = {
        "Query": query,
        "Documents": len(documents),
        "Verification": "Standard verification" if not noverify else "Disabled",
    }

    show_command_completion("draft", output_file, extra_files, stats)

    # Command end log
    try:
        log_task_event(
            "draft",
            "init",
            "end",
            "Draft generation complete"
        )
    except Exception:
        pass

    # Show brief preview
    lines = content.split("\n")
    preview_lines = [line for line in lines[:10] if line.strip()][:5]
    if preview_lines:
        click.echo(f"\n{info_message('Preview:')}")
        for line in preview_lines:
            click.echo(f"   {line[:80]}..." if len(line) > 80 else f"   {line}")
