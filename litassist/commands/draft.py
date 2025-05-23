"""
Citation-rich drafting via RAG & GPT-4o.

This module implements the 'draft' command which uses Retrieval-Augmented Generation
to create well-supported legal drafts. The process embeds document chunks, stores them
in Pinecone, retrieves relevant passages using MMR re-ranking, and generates a draft
with GPT-4o that incorporates these citations.
"""

import click

from litassist.config import CONFIG
from litassist.utils import (
    read_document,
    chunk_text,
    create_embeddings,
    save_log,
    heartbeat,
)
from litassist.llm import LLMClient
from litassist.retriever import Retriever, get_pinecone_client


@click.command()
@click.argument("pdf", type=click.Path(exists=True))
@click.argument("query")
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
@click.option(
    "--diversity",
    type=float,
    help="Control diversity of search results (0.0-1.0)",
    default=None,
)
def draft(pdf, query, verify, diversity):
    """
    Citation-rich drafting via RAG & GPT-4o.

    Implements a Retrieval-Augmented Generation workflow to create well-supported
    legal drafts. The process embeds document chunks, stores them in Pinecone,
    retrieves relevant passages using MMR re-ranking, and generates a draft
    with GPT-4o that incorporates these citations.

    Args:
        pdf: Path to the PDF document to use as a knowledge base.
        query: The specific legal topic or argument to draft.
        verify: Whether to run a self-critique verification pass on the draft.
        diversity: Optional float (0.0-1.0) controlling the balance between
                  relevance and diversity in retrieved passages. Higher values
                  prioritize diversity over relevance.

    Raises:
        click.ClickException: If there are errors with file reading, embedding,
                             vector storage, retrieval, or LLM API calls.
    """
    # Read and chunk the document
    text = read_document(pdf)
    chunks = chunk_text(text)

    # Get Pinecone client
    pc_index = get_pinecone_client()

    # Embed and upsert document chunks
    docs = [(f"d{i}", chunk) for i, chunk in enumerate(chunks, start=1)]
    try:
        embeddings = create_embeddings([d[1] for d in docs])
    except Exception as e:
        raise click.ClickException(f"Embedding error: {e}")
    vectors = [
        (docs[i][0], embeddings[i].embedding, {"text": docs[i][1]})
        for i in range(len(docs))
    ]
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
        context_list = retriever.retrieve(qemb, top_k=5, diversity_level=diversity)
    except Exception as e:
        raise click.ClickException(f"Pinecone retrieval error: {e}")
    context = "\n\n".join(context_list)

    # Generate draft with GPT-4o
    client = LLMClient(
        "openai/gpt-4o",
        temperature=0.5,
        top_p=0.8,
        presence_penalty=0.1,
        frequency_penalty=0.1,
    )
    client.command_context = "draft"  # Set command context
    messages = [
        {
            "role": "system",
            "content": "Australian law only. Draft a legally precise document with proper citations and structure. Be thorough but concise. Focus on legal accuracy, relevant precedents, and clear organization. Use section headings, numbered paragraphs, and proper legal citation format. Maintain internal consistency throughout and ensure all claims are supported by the provided context. Avoid speculation beyond the provided information.",
        },
        {"role": "user", "content": f"Context:\n{context}\n\nDraft {query}"},
    ]
    call_with_hb = heartbeat(CONFIG.heartbeat_interval)(client.complete)
    try:
        content, usage = call_with_hb(messages)
    except Exception as e:
        raise click.ClickException(f"LLM draft error: {e}")

    # Smart verification with conditional depth
    needs_verification = verify or client.should_auto_verify(content, "draft")
    
    if needs_verification:
        try:
            # Use heavy verification for legal drafting (high stakes)
            correction = client.verify_with_level(content, "heavy")
            if correction.strip():  # Only append if there are actual corrections
                content = content + "\n\n--- Legal Draft Review ---\n" + correction
                
            # Run comprehensive citation validation for drafts
            citation_issues = client.validate_citations(content)
            if citation_issues:
                content += "\n\n--- Citation Warnings ---\n" + "\n".join(citation_issues)
                
        except Exception as e:
            raise click.ClickException(f"Verification error during drafting: {e}")

    # Save audit log and echo response
    save_log(
        "draft",
        {
            "inputs": {"pdf": pdf, "query": query, "context": context},
            "response": content,
            "usage": usage,
            "verification": f"enabled={needs_verification}, level=heavy" if needs_verification else "disabled",
        },
    )
    click.echo(content)
