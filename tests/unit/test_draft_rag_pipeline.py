"""Regression tests for the draft command's RAG pipeline isolation.

The Pinecone-backed RAG pipeline previously used deterministic vector IDs
(`d1`, `d2`, ...) and queried without a namespace or filter, so vectors from
one draft run could be retrieved into another draft for an unrelated matter.
"""

from unittest.mock import Mock, patch

import pytest

from litassist.commands.draft import rag_pipeline


def _make_embedding(dim: int = 4):
    return Mock(embedding=[0.1] * dim)


class TestDraftRAGPipelineIsolation:
    @patch("litassist.commands.draft.rag_pipeline.Retriever")
    @patch("litassist.commands.draft.rag_pipeline.get_pinecone_client")
    @patch("litassist.commands.draft.rag_pipeline.create_embeddings")
    @patch("litassist.commands.draft.rag_pipeline.get_config")
    def test_each_run_uses_unique_namespace(
        self, mock_get_config, mock_create_embeddings, mock_get_pc, mock_retriever_cls
    ):
        mock_config = Mock()
        mock_config.rag_max_chars = 1000
        mock_get_config.return_value = mock_config

        mock_create_embeddings.side_effect = lambda items: [
            _make_embedding() for _ in items
        ]

        # Use two independent mock indexes so we can inspect each call separately.
        idx_a = Mock()
        idx_b = Mock()
        mock_get_pc.side_effect = [idx_a, idx_b]

        retriever_a = Mock()
        retriever_a.retrieve.return_value = ["chunk a"]
        retriever_b = Mock()
        retriever_b.retrieve.return_value = ["chunk b"]
        mock_retriever_cls.side_effect = [retriever_a, retriever_b]

        docs = [("matter1.pdf", "Document text for matter 1")]
        rag_pipeline.process_documents_with_rag(docs, "find clauses", 0.3)
        rag_pipeline.process_documents_with_rag(docs, "find clauses", 0.3)

        # Each upsert must specify a namespace.
        for idx, call in [(idx_a, idx_a.upsert.call_args), (idx_b, idx_b.upsert.call_args)]:
            assert "namespace" in call.kwargs, (
                "Pinecone upsert must specify a namespace per run; otherwise "
                "vectors from a prior matter can be retrieved into a new draft."
            )
            assert call.kwargs["namespace"], "namespace must be non-empty"

        ns_a = idx_a.upsert.call_args.kwargs["namespace"]
        ns_b = idx_b.upsert.call_args.kwargs["namespace"]
        assert ns_a != ns_b, (
            "Each run must use a unique namespace, otherwise the second run "
            "would share Pinecone storage with the first."
        )

        # The retriever for each run must be queried with that run's namespace.
        assert retriever_a.retrieve.call_args.kwargs.get("namespace") == ns_a
        assert retriever_b.retrieve.call_args.kwargs.get("namespace") == ns_b

        # And each run must clean up after itself.
        assert idx_a.delete.called, "Per-run namespace must be deleted after use"
        assert idx_a.delete.call_args.kwargs.get("namespace") == ns_a
        assert idx_b.delete.called
        assert idx_b.delete.call_args.kwargs.get("namespace") == ns_b

    @patch("litassist.commands.draft.rag_pipeline.Retriever")
    @patch("litassist.commands.draft.rag_pipeline.get_pinecone_client")
    @patch("litassist.commands.draft.rag_pipeline.create_embeddings")
    @patch("litassist.commands.draft.rag_pipeline.get_config")
    def test_namespace_cleanup_runs_even_when_retrieval_fails(
        self, mock_get_config, mock_create_embeddings, mock_get_pc, mock_retriever_cls
    ):
        # If retrieval raises, the upserted namespace must still be deleted to
        # avoid leaking vectors that could surface in a future run.
        mock_config = Mock()
        mock_config.rag_max_chars = 1000
        mock_get_config.return_value = mock_config
        mock_create_embeddings.side_effect = lambda items: [
            _make_embedding() for _ in items
        ]

        idx = Mock()
        mock_get_pc.return_value = idx

        retriever = Mock()
        retriever.retrieve.side_effect = RuntimeError("pinecone offline")
        mock_retriever_cls.return_value = retriever

        with pytest.raises(Exception):
            rag_pipeline.process_documents_with_rag(
                [("m.pdf", "text")], "query", 0.3
            )

        assert idx.delete.called, (
            "Namespace cleanup must run even when retrieval fails, otherwise "
            "stale vectors leak into the next run."
        )


pytestmark = [pytest.mark.unit, pytest.mark.offline]
