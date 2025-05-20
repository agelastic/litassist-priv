"""
Unit tests for the Retriever module.
"""

import pytest
from unittest.mock import Mock, patch
from litassist.retriever import Retriever, MockPineconeIndex, get_pinecone_client


class TestRetriever:
    """Test the Retriever class."""

    def test_init_with_defaults(self):
        """Test Retriever initialization with default parameters."""
        mock_index = Mock()
        retriever = Retriever(mock_index)

        assert retriever.index == mock_index
        assert retriever.use_mmr is True
        assert retriever.diversity_level == 0.3

    def test_init_with_custom_params(self):
        """Test Retriever initialization with custom parameters."""
        mock_index = Mock()
        retriever = Retriever(mock_index, use_mmr=False, diversity_level=0.7)

        assert retriever.use_mmr is False
        assert retriever.diversity_level == 0.7

    def test_diversity_level_clamping(self):
        """Test that diversity level is clamped between 0 and 1."""
        mock_index = Mock()

        # Test upper bound
        retriever = Retriever(mock_index, diversity_level=1.5)
        assert retriever.diversity_level == 1.0

        # Test lower bound
        retriever = Retriever(mock_index, diversity_level=-0.5)
        assert retriever.diversity_level == 0.0

    @patch("litassist.retriever.timed")
    def test_retrieve_without_mmr(self, mock_timed):
        """Test retrieve without MMR."""
        mock_timed.return_value = lambda f: f

        mock_index = Mock()
        mock_index.query.return_value = Mock(
            matches=[
                Mock(metadata={"text": "Passage 1"}),
                Mock(metadata={"text": "Passage 2"}),
                Mock(metadata={"text": "Passage 3"}),
            ]
        )

        retriever = Retriever(mock_index, use_mmr=False)
        query_emb = [0.1] * 1536
        passages = retriever.retrieve(query_emb, top_k=3)

        assert len(passages) == 3
        assert passages[0] == "Passage 1"
        mock_index.query.assert_called_once_with(
            vector=query_emb, top_k=3, include_metadata=True
        )

    @patch("litassist.retriever.timed")
    def test_retrieve_with_mmr(self, mock_timed):
        """Test retrieve with MMR enabled."""
        mock_timed.return_value = lambda f: f

        mock_index = Mock()
        mock_index.query.return_value = Mock(
            matches=[
                Mock(metadata={"text": "Passage 1"}),
                Mock(metadata={"text": "Passage 2"}),
            ]
        )

        retriever = Retriever(mock_index, use_mmr=True, diversity_level=0.5)
        query_emb = [0.1] * 1536
        passages = retriever.retrieve(query_emb, top_k=2)

        assert len(passages) == 2
        query_kwargs = mock_index.query.call_args[1]
        assert query_kwargs["use_mmr"] is True
        assert query_kwargs["diversity_bias"] == 0.5

    @patch("litassist.retriever.timed")
    def test_retrieve_with_override_diversity(self, mock_timed):
        """Test retrieve with diversity level override."""
        mock_timed.return_value = lambda f: f

        mock_index = Mock()
        mock_index.query.return_value = Mock(matches=[])

        retriever = Retriever(mock_index, use_mmr=True, diversity_level=0.3)
        query_emb = [0.1] * 1536
        retriever.retrieve(query_emb, top_k=5, diversity_level=0.8)

        query_kwargs = mock_index.query.call_args[1]
        assert query_kwargs["diversity_bias"] == 0.8

    def test_retrieve_empty_results(self):
        """Test retrieve with no matches."""
        mock_index = Mock()
        mock_index.query.return_value = Mock(matches=[])

        retriever = Retriever(mock_index)
        passages = retriever.retrieve([0.1] * 1536)

        assert passages == []


class TestMockPineconeIndex:
    """Test the MockPineconeIndex class."""

    def test_mock_query(self):
        """Test mock query returns empty results."""
        mock_index = MockPineconeIndex()
        result = mock_index.query(vector=[0.1] * 1536)
        assert result["matches"] == []

    def test_mock_stats(self):
        """Test mock index stats."""
        mock_index = MockPineconeIndex()
        stats = mock_index.describe_index_stats()
        assert stats.total_vector_count == 0
        assert stats.dimension == 1536

    def test_mock_upsert(self):
        """Test mock upsert (no-op)."""
        mock_index = MockPineconeIndex()
        # Should not raise any errors
        mock_index.upsert(vectors=[])

    def test_mock_delete(self):
        """Test mock delete (no-op)."""
        mock_index = MockPineconeIndex()
        # Should not raise any errors
        mock_index.delete(ids=["1", "2"])


class TestGetPineconeClient:
    """Test the get_pinecone_client function."""

    @patch("litassist.retriever.CONFIG")
    def test_with_placeholder_credentials(self, mock_config):
        """Test handling of placeholder credentials."""
        mock_config.pc_key = "YOUR_PINECONE_KEY"
        mock_config.pc_env = "YOUR_PINECONE_ENV"

        client = get_pinecone_client()
        assert isinstance(client, MockPineconeIndex)

    @patch("litassist.retriever.CONFIG")
    @patch("litassist.retriever.get_pc")
    def test_with_real_credentials(self, mock_get_pc, mock_config):
        """Test with real credentials."""
        mock_config.pc_key = "real_key"
        mock_config.pc_env = "us-east-1"
        mock_config.pc_index = "test_index"

        mock_pc_index = Mock()
        mock_pc_index.describe_index_stats.return_value = Mock(
            dimension=1536, total_vector_count=100
        )
        mock_get_pc.return_value = mock_pc_index

        client = get_pinecone_client()
        assert client == mock_pc_index
        mock_get_pc.assert_called_once()

    @patch("litassist.retriever.CONFIG")
    @patch("litassist.retriever.get_pc")
    def test_fallback_to_mock_on_error(self, mock_get_pc, mock_config):
        """Test fallback to mock when real connection fails."""
        mock_config.pc_key = "real_key"
        mock_config.pc_env = "us-east-1"
        mock_config.pc_index = "test_index"

        mock_get_pc.side_effect = Exception("Connection failed")

        client = get_pinecone_client()
        assert isinstance(client, MockPineconeIndex)
