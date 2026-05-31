"""Real tests that actually test litassist functionality."""

from unittest.mock import patch
import tempfile
from pathlib import Path

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

    def test_save_log_creates_file(self):
        """Test save_log creates actual files."""
        from litassist.logging import save_log
        import os
        import tempfile

        # Create a temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch LOG_DIR to use temp directory
            with patch("litassist.logging.LOG_DIR", temp_dir):
                payload = {"input": "test", "response": "result"}
                save_log("test", payload)

                # Check that a file was created
                files = os.listdir(temp_dir)
                assert len(files) == 1
                assert files[0].startswith("test_")
                # Accept either JSON or Markdown format (depends on config)
                assert files[0].endswith(".json") or files[0].endswith(".md")

    def test_real_file_operations(self):
        """Test file operations with real temp files."""
        from litassist.utils.file_ops import read_document

        # Create a real temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("Test content")
            temp_path = f.name

        try:
            # Read the actual file
            content = read_document(temp_path)
            assert content == "Test content"
        finally:
            # Clean up
            Path(temp_path).unlink()
