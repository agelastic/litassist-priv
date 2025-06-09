"""
Citation-rich drafting via RAG & GPT-4o.

This module implements the 'draft' command which uses Retrieval-Augmented Generation
to create well-supported legal drafts. The process embeds document chunks, stores them
in Pinecone, retrieves relevant passages using MMR re-ranking, and generates a draft
with GPT-4o that incorporates these citations.
"""

import click

from litassist.config import CONFIG
from litassist.prompts import PROMPTS
from litassist.utils import (
    read_document,
    chunk_text,
    create_embeddings,
    save_log,
    heartbeat,
    timed,
    create_reasoning_prompt,
    extract_reasoning_trace,
    save_reasoning_trace,
    save_command_output,
    show_command_completion,
    verify_content_if_needed,
)
from litassist.llm import LLMClientFactory
from litassist.retriever import Retriever, get_pinecone_client


@click.command()
@click.argument("documents", nargs=-1, required=True, type=click.Path(exists=True))
@click.argument("query")
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
@click.option(
    "--diversity",
    type=float,
    help="Control diversity of search results (0.0-1.0)",
    default=None,
)
@timed
def draft(documents, query, verify, diversity):
    """
    Citation-rich drafting via RAG & GPT-4o.

    For text files under 50KB (like case_facts.txt), passes the entire content
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
        verify: Whether to run a self-critique verification pass on the draft.
        diversity: Optional float (0.0-1.0) controlling the balance between
                  relevance and diversity in retrieved passages. Higher values
                  prioritize diversity over relevance. (Only used for PDFs/large files)

    Raises:
        click.ClickException: If there are errors with file reading, embedding,
                             vector storage, retrieval, or LLM API calls.
    """
    # Process all documents
    structured_content = {
        "case_facts": "",
        "strategies": "",
        "other_text": [],
        "pdf_documents": [],
    }

    for doc_path in documents:
        text = read_document(doc_path)

        # Categorize documents by type - separate file type check from size check
        if doc_path.lower().endswith(".txt"):
            # For text files, categorize by content and handle large files appropriately
            if "case_facts" in doc_path.lower():
                if len(text) < 50000:
                    structured_content["case_facts"] = text
                    click.echo(
                        f"Using {doc_path} as CASE FACTS ({len(text)} characters)"
                    )
                else:
                    # Large case facts file - use embedding/retrieval
                    structured_content["pdf_documents"].append((doc_path, text))
                    click.echo(f"Will use embedding/retrieval for large {doc_path}")
            elif "strategies" in doc_path.lower() or "# Legal Strategies" in text:
                if len(text) < 50000:
                    structured_content["strategies"] = text
                    click.echo(
                        f"Using {doc_path} as LEGAL STRATEGIES ({len(text)} characters)"
                    )
                else:
                    # Large strategies file - use embedding/retrieval
                    structured_content["pdf_documents"].append((doc_path, text))
                    click.echo(f"Will use embedding/retrieval for large {doc_path}")
            else:
                if len(text) < 50000:
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

    # Build structured context for the LLM
    context_parts = []

    if structured_content["case_facts"]:
        context_parts.append("=== CASE FACTS ===\n" + structured_content["case_facts"])

    if structured_content["strategies"]:
        context_parts.append(
            "=== LEGAL STRATEGIES FROM BRAINSTORMING ===\n"
            + structured_content["strategies"]
        )

    for doc_path, text in structured_content["other_text"]:
        context_parts.append(f"=== SUPPORTING DOCUMENT: {doc_path} ===\n{text}")

    combined_text_context = "\n\n".join(context_parts) if context_parts else ""

    # Process PDFs with embedding/retrieval if any
    retrieved_context = ""
    if structured_content["pdf_documents"]:
        # Get Pinecone client
        pc_index = get_pinecone_client()

        # Process all PDFs
        all_chunks = []
        doc_counter = 0

        for doc_path, text in structured_content["pdf_documents"]:
            # Chunk each document
            chunks = chunk_text(text, max_chars=CONFIG.rag_max_chars)
            for chunk in chunks:
                doc_counter += 1
                all_chunks.append((f"d{doc_counter}", chunk, doc_path))

        # Embed all chunks
        try:
            embeddings = create_embeddings([chunk[1] for chunk in all_chunks])
        except Exception as e:
            raise click.ClickException(f"Embedding error: {e}")

        # Create vectors with metadata
        vectors = []
        for i, (chunk_id, chunk_content, source_doc) in enumerate(all_chunks):
            vectors.append(
                (
                    chunk_id,
                    embeddings[i].embedding,
                    {"text": chunk_content, "source": source_doc},
                )
            )

        # Upsert to Pinecone
        try:
            pc_index.upsert(vectors=vectors)
        except Exception as e:
            raise click.ClickException(f"Pinecone upsert error: {e}")

        # Retrieve relevant context with MMR
        try:
            qemb = create_embeddings([query])[0].embedding
        except Exception as e:
            raise click.ClickException(f"Embedding error for query: {e}")

        retriever = Retriever(pc_index, use_mmr=True)
        try:
            context_list = retriever.retrieve(qemb, top_k=7, diversity_level=diversity)
        except Exception as e:
            raise click.ClickException(f"Pinecone retrieval error: {e}")

        retrieved_context = "\n\n=== Retrieved Context ===\n" + "\n\n".join(
            context_list
        )

    # Combine all context
    context = combined_text_context
    if retrieved_context:
        context = (
            (context + "\n\n" + retrieved_context) if context else retrieved_context
        )

    # Generate draft with GPT-4o
    client = LLMClientFactory.for_command("draft")
    # Build system prompt based on available content
    system_prompt = PROMPTS.get('processing.draft.system_prompt_base')

    if structured_content["case_facts"] and structured_content["strategies"]:
        system_prompt += PROMPTS.get('processing.draft.context_case_facts_and_strategies')
    elif structured_content["case_facts"]:
        system_prompt += PROMPTS.get('processing.draft.context_case_facts_only')
    elif structured_content["strategies"]:
        system_prompt += PROMPTS.get('processing.draft.context_strategies_only')

    system_prompt += PROMPTS.get('processing.draft.general_instructions')

    # Create user prompt using centralized template
    user_template = PROMPTS.get('processing.draft.user_prompt_template')
    base_user_prompt = user_template.format(document_type=query, user_request=f"Context:\n{context}")

    # Add reasoning trace to user prompt
    user_prompt = create_reasoning_prompt(base_user_prompt, "draft")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    call_with_hb = heartbeat(CONFIG.heartbeat_interval)(client.complete)
    try:
        content, usage = call_with_hb(messages)
    except Exception as e:
        raise click.ClickException(f"LLM draft error: {e}")

    # Note: Citation verification now handled automatically in LLMClient.complete()

    # Apply verification if needed
    content, needs_verification = verify_content_if_needed(client, content, "draft", verify)

    # Extract reasoning trace before saving
    reasoning_trace = extract_reasoning_trace(content, "draft")

    # Save output using utility
    output_file = save_command_output(
        "draft",
        content,
        query,
        metadata={
            "Query": query,
            "Documents": ", ".join(documents)
        }
    )

    # Save reasoning trace if extracted
    extra_files = {}
    if reasoning_trace:
        reasoning_file = save_reasoning_trace(reasoning_trace, output_file)
        extra_files["Reasoning trace"] = reasoning_file

    # Save audit log
    save_log(
        "draft",
        {
            "inputs": {
                "documents": list(documents),
                "query": query,
                "context": context,
            },
            "response": content,
            "usage": usage,
            "verification": (
                f"enabled={needs_verification}, level=heavy"
                if needs_verification
                else "disabled"
            ),
            "output_file": output_file,
        },
    )

    # Show completion with preview
    stats = {
        "Query": query,
        "Documents": len(documents),
        "Verification": "Applied" if needs_verification else "Not needed"
    }
    
    show_command_completion("draft", output_file, extra_files, stats)
    
    # Show brief preview
    lines = content.split("\n")
    preview_lines = [line for line in lines[:10] if line.strip()][:5]
    if preview_lines:
        click.echo("\n📋 Preview:")
        for line in preview_lines:
            click.echo(f"   {line[:80]}..." if len(line) > 80 else f"   {line}")
