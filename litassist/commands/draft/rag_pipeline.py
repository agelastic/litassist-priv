"""
RAG pipeline for draft command.

Handles document chunking, embedding, vector storage, and retrieval.
"""

import click
from typing import List, Tuple, Optional

from litassist.config import get_config
from litassist.utils.text_processing import chunk_text, create_embeddings
from litassist.logging import log_task_event
from litassist.helpers.retriever import Retriever, get_pinecone_client


def process_documents_with_rag(
    pdf_documents: List[Tuple[str, str]],
    query: str,
    diversity: Optional[float]
) -> str:
    """
    Process documents using RAG pipeline.

    Args:
        pdf_documents: List of (doc_path, text) tuples
        query: Query string for retrieval
        diversity: Optional diversity level for MMR

    Returns:
        Retrieved context string with === markers

    Raises:
        click.ClickException: If RAG pipeline fails
    """
    try:
        log_task_event(
            "draft",
            "indexing",
            "start",
            "Starting document indexing for RAG pipeline"
        )
    except Exception:
        pass

    # Get Pinecone client
    pc_index = get_pinecone_client()

    # Process all PDFs
    all_chunks = []
    doc_counter = 0

    for doc_path, text in pdf_documents:
        # Chunk each document
        chunks = chunk_text(text, max_chars=get_config().rag_max_chars)
        for chunk in chunks:
            doc_counter += 1
            all_chunks.append((f"d{doc_counter}", chunk, doc_path))

    # Embed all chunks
    try:
        log_task_event(
            "draft",
            "embedding",
            "start",
            f"Creating embeddings for {len(all_chunks)} chunks"
        )
    except Exception:
        pass

    try:
        embeddings = create_embeddings([chunk[1] for chunk in all_chunks])

        try:
            log_task_event(
                "draft",
                "embedding",
                "end",
                f"Created {len(embeddings)} embeddings"
            )
        except Exception:
            pass
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
        log_task_event(
            "draft",
            "pinecone",
            "start",
            f"Upserting {len(vectors)} vectors to Pinecone"
        )
    except Exception:
        pass

    try:
        pc_index.upsert(vectors=vectors)

        try:
            log_task_event(
                "draft",
                "pinecone",
                "end",
                "Vectors uploaded to Pinecone"
            )
        except Exception:
            pass

    except Exception as e:
        raise click.ClickException(f"Pinecone upsert error: {e}")

    # Retrieve relevant context with MMR
    try:
        qemb = create_embeddings([query])[0].embedding
    except Exception as e:
        raise click.ClickException(f"Embedding error for query: {e}")

    retriever = Retriever(pc_index, use_mmr=True)

    try:
        log_task_event(
            "draft",
            "retrieval",
            "start",
            "Retrieving relevant context with MMR"
        )
    except Exception:
        pass

    try:
        context_list = retriever.retrieve(qemb, top_k=7, diversity_level=diversity)

        try:
            log_task_event(
                "draft",
                "retrieval",
                "end",
                f"Retrieved {len(context_list)} relevant chunks"
            )
        except Exception:
            pass
    except Exception as e:
        raise click.ClickException(f"Pinecone retrieval error: {e}")

    retrieved_context = (
        "\n\n=== RETRIEVED CONTEXT ===\n"
        + "\n\n".join(context_list)
        + "\n=== END RETRIEVED CONTEXT ==="
    )

    try:
        log_task_event(
            "draft",
            "indexing",
            "end",
            "RAG pipeline complete"
        )
    except Exception:
        pass

    return retrieved_context
