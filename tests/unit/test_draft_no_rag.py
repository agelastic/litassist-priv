"""
Regression tests for the RAG removal in `draft`.

Before this change, the draft command routed any text file >= 400000 chars
(and all PDFs) into a Pinecone-backed retrieval pipeline. After the change,
every input flows through a single full-context LLM call. These tests guard
that contract.
"""


def test_large_text_file_categorised_to_text_bucket(tmp_path):
    """A text file at or above the old 400000-char RAG threshold must
    categorise as case_facts / strategies / other_text, not pdf_documents.
    Pre-removal, files this size were routed into pdf_documents to trigger
    the embedding/retrieval pipeline."""
    from litassist.commands.draft.document_processor import (
        read_and_categorize_documents,
    )

    big_text = "x" * 500_000
    f = tmp_path / "case_facts.txt"
    f.write_text(big_text)
    result = read_and_categorize_documents((str(f),))
    assert result["case_facts"] == big_text
    assert result["pdf_documents"] == []


def test_draft_module_does_not_reference_rag_pipeline():
    """draft/core.py must not import or call any RAG / Pinecone construct
    after the removal."""
    from litassist.commands.draft import core

    with open(core.__file__) as f:
        src = f.read()

    forbidden = [
        "rag_pipeline",
        "process_documents_with_rag",
        "from .rag_pipeline",
    ]
    for term in forbidden:
        assert term not in src, (
            f"draft/core.py must not reference '{term}' after RAG removal"
        )
