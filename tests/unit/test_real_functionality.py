"""Real tests that actually test litassist functionality."""

import pytest
from unittest.mock import Mock, patch
import tempfile
from pathlib import Path

from litassist.utils import chunk_text


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

        # Verify no text is lost
        reconstructed = "".join(chunks)
        assert len(reconstructed) >= len(text)  # May have overlap

    def test_real_config_mock(self):
        """Test with properly mocked config."""
        from litassist.config import CONFIG

        # The config should be mocked by conftest.py
        assert CONFIG is not None
        assert hasattr(CONFIG, "openai_api_key")


    def test_save_log_creates_file(self):
        """Test save_log creates actual files."""
        from litassist.utils import save_log
        import os
        import tempfile

        # Create a temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch LOG_DIR to use temp directory
            with patch("litassist.utils.LOG_DIR", temp_dir):
                payload = {"input": "test", "response": "result"}
                save_log("test", payload)
                
                # Check that a file was created
                files = os.listdir(temp_dir)
                assert len(files) == 1
                assert files[0].startswith("test_")
                assert files[0].endswith(".md")

    def test_real_file_operations(self):
        """Test file operations with real temp files."""
        from litassist.utils import read_document

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


class TestCLICommandsWithRealFiles:
    """Test CLI commands with real file handling."""

    def test_brainstorm_with_real_file(self):
        """Test brainstorm command with actual file."""
        from click.testing import CliRunner
        from litassist.commands.brainstorm import brainstorm

        runner = CliRunner()

        with runner.isolated_filesystem():
            # Create a real file in the isolated filesystem
            with open("facts.txt", "w") as f:
                f.write("Test case facts")

            # Mock the actual command logic
            with patch("litassist.commands.brainstorm.LLMClient") as mock_client:
                mock_instance = Mock()
                mock_instance.complete.return_value = (
                    "Strategy",
                    {"total_tokens": 100},
                )
                mock_client.return_value = mock_instance

                # Run with real file
                result = runner.invoke(
                    brainstorm, ["facts.txt", "--side", "plaintiff", "--area", "civil"]
                )

                # Should not fail on file not found
                assert "does not exist" not in result.output
