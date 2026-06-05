"""Real tests that actually test litassist functionality."""

from litassist.utils.text_processing import chunk_text


class TestActualFunctionality:
    """Tests that actually verify real functionality."""

    def test_chunk_text_with_real_input(self):
        """Test chunk_text with actual implementation."""
        # Test with real text that needs chunking
        text = "This is a sentence. " * 100  # 2000 characters

        # Use the actual function signature
        chunks = chunk_text(text, max_chars=500)

        # Verify it actually chunks
        assert len(chunks) > 1
        assert all(len(chunk) <= 500 for chunk in chunks)

        # Verify text is preserved (may have whitespace normalization)
        reconstructed = "".join(chunks)
        # Allow for some text compression due to whitespace normalization
        assert (
            len(reconstructed) >= len(text) * 0.95
        )  # Allow 5% compression from normalization
