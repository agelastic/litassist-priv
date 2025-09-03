"""
Vector search retrieval system for LitAssist.

This module handles querying a vector database (Pinecone) and retrieving relevant text passages,
with optional diversity-based re-ranking using Maximal Marginal Relevance (MMR).
"""

from typing import List, Dict, Any, Optional

from litassist.timing import timed
from litassist.config import get_config


class MockPineconeIndex:
    """
    Mock Pinecone index for testing purposes.

    This class provides a simplified interface that mimics the Pinecone index API
    when real credentials aren't available.
    """

    def __init__(self, *args, **kwargs):
        """Initialize the mock index."""
        pass

    def query(self, *args, **kwargs) -> Dict[str, List[Any]]:
        """Mock query returning empty results."""
        return {"matches": []}

    def upsert(self, *args, **kwargs):
        """Mock upsert (no-op)."""
        pass

    def delete(self, *args, **kwargs):
        """Mock delete (no-op)."""
        pass

    def describe_index_stats(self, *args, **kwargs) -> Any:
        """
        Mock index statistics.

        Returns:
            A mock stats object with basic properties.
        """
        # Return simple object instead of inner class
        return type("MockStats", (), {"total_vector_count": 0, "dimension": 1536})()


def get_pinecone_client():
    """
    Initialize a Pinecone client connection.

    Returns:
        A Pinecone index object, or a mock index if credentials are placeholder values.
    """
    config = get_config()
    
    # Check if we're using placeholder values for Pinecone
    if "YOUR_PINECONE" in config.pc_key or "YOUR_PINECONE" in config.pc_env:
        print(
            "WARNING: Using placeholder Pinecone credentials. Some features will be limited."
        )
        return MockPineconeIndex()

    # Import locally to allow for mock usage when pinecone-client isn't installed
    from litassist.helpers.pinecone_config import get_pinecone_client as get_pc

    pc_index = get_pc(config.pc_key, config.pc_env, config.pc_index)

    # Test if we can access it
    try:
        stats = pc_index.describe_index_stats()
        print(
            f"[OK] Connected to index '{config.pc_index}' (dimension: {stats.dimension}, vectors: {stats.total_vector_count})"
        )
        return pc_index
    except Exception as e:
        print(f"WARNING: Cannot access index '{config.pc_index}'.")
        print(f"Error: {e}")
        print("Using mock index for testing.")
        return MockPineconeIndex()


class Retriever:
    """
    Vector search retrieval system with Maximal Marginal Relevance (MMR) re-ranking support.

    This class handles querying a vector database (Pinecone) and retrieving relevant text passages,
    with optional diversity-based re-ranking using MMR. MMR balances between retrieving the most
    relevant results and ensuring diversity in the result set, which can be important for
    legal research where getting varied perspectives is valuable.

    Attributes:
        index: The Pinecone index used for vector search.
        use_mmr: Boolean indicating whether to use MMR for diversity in results.
        diversity_level: Float between 0.0-1.0 controlling the balance between relevance
                        and diversity when MMR is enabled.

    Example:
        ```python
        # Initialize with default MMR settings
        retriever = Retriever(pc_index, use_mmr=True, diversity_level=0.3)

        # Retrieve passages using a query embedding
        passages = retriever.retrieve(query_embedding, top_k=5)

        # Or with a custom diversity setting for this query
        diverse_passages = retriever.retrieve(query_embedding, top_k=5, diversity_level=0.7)
        ```
    """

    def __init__(self, index, use_mmr: bool = True, diversity_level: float = 0.3):
        """
        Initialize the retriever with MMR settings.

        Args:
            index: The Pinecone index to query.
            use_mmr: Whether to use Maximal Marginal Relevance for diversity in results.
            diversity_level: Controls the balance between relevance and diversity (0.0-1.0).
                             Lower values (closer to 0) prioritize relevance,
                             Higher values (closer to 1) prioritize diversity.
        """
        self.index = index
        self.use_mmr = use_mmr
        self.diversity_level = max(
            0.0, min(1.0, diversity_level)
        )  # Clamp between 0 and 1

    @timed
    def retrieve(
        self,
        query_emb: List[float],
        top_k: int = 5,
        diversity_level: Optional[float] = None,
    ) -> List[str]:
        """
        Query Pinecone (with optional MMR) and return a list of passage texts.

        Args:
            query_emb: Embedding vector of the user query.
            top_k: Number of passages to return.
            diversity_level: Override the default diversity level for this query.
                             Controls the balance between relevance and diversity (0.0-1.0).
                             Lower values prioritize relevance, higher values prioritize diversity.

        Returns:
            A list of text passages retrieved from the vector store.
        """
        # Build query arguments
        query_kwargs = {"vector": query_emb, "top_k": top_k, "include_metadata": True}
        # Enable Maximal Marginal Relevance if requested
        if getattr(self, "use_mmr", False):
            query_kwargs["use_mmr"] = True
            # Apply diversity setting - use the provided value or fall back to instance default
            actual_diversity = (
                diversity_level if diversity_level is not None else self.diversity_level
            )
            actual_diversity = max(
                0.0, min(1.0, actual_diversity)
            )  # Clamp between 0 and 1
            query_kwargs["diversity_bias"] = actual_diversity

        # Execute the query
        result = self.index.query(**query_kwargs)
        # Extract and return the text field from metadata
        passages = []
        for match in result.matches:
            metadata = match.metadata
            text = metadata.get("text")
            if text:
                passages.append(text)
        return passages
