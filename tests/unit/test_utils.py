"""
Unit tests for utility functions.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import json
import tempfile
import os
from datetime import datetime
from click import ClickException

from litassist.utils import (
    read_document,
    chunk_text,
    create_embeddings,
    save_log,
    heartbeat,
    timed,
)


class TestReadDocument:
    """Test the read_document function."""

    def test_read_text_file(self, temp_text_file):
        """Test reading a text file."""
        content = read_document(temp_text_file)
        assert content == "Test case facts content\nLine 2\nLine 3"

    @patch("litassist.utils.PdfReader")
    def test_read_pdf_file(self, mock_pdf_reader):
        """Test reading a PDF file."""
        # Mock PDF reader
        mock_page = Mock()
        mock_page.extract_text.return_value = "Page 1 text\n"
        mock_reader = Mock()
        mock_reader.pages = [mock_page, mock_page]
        mock_pdf_reader.return_value = mock_reader

        with tempfile.NamedTemporaryFile(suffix=".pdf") as f:
            content = read_document(f.name)
            assert content == "Page 1 text\nPage 1 text\n"

    def test_read_nonexistent_file(self):
        """Test reading a non-existent file."""
        with pytest.raises(ClickException, match="Error reading document"):
            read_document("nonexistent.txt")

    def test_unsupported_file_type(self):
        """Test reading an unsupported file type."""
        with tempfile.NamedTemporaryFile(suffix=".doc") as f:
            with pytest.raises(ClickException, match="Unsupported file type"):
                read_document(f.name)


class TestChunkText:
    """Test the chunk_text function."""

    def test_chunk_small_text(self):
        """Test chunking text smaller than chunk size."""
        text = "Small text"
        chunks = chunk_text(text, max_chars=100)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_large_text(self):
        """Test chunking text larger than chunk size."""
        text = "Word " * 100  # 500 characters
        chunks = chunk_text(text, max_chars=100)
        assert len(chunks) > 1
        # Verify all chunks are within size limit
        for chunk in chunks:
            assert len(chunk) <= 100

    def test_chunk_exact_size(self):
        """Test chunking text exactly at chunk size."""
        text = "x" * 100
        chunks = chunk_text(text, max_chars=100)
        assert len(chunks) == 1

    def test_empty_text(self):
        """Test chunking empty text."""
        chunks = chunk_text("")
        assert chunks == []


class TestCreateEmbeddings:
    """Test the create_embeddings function."""

    @patch("litassist.utils.openai.Embedding.create")
    def test_create_embeddings_success(self, mock_create):
        """Test successful embedding creation."""
        mock_create.return_value = Mock(data=[Mock(embedding=[0.1, 0.2, 0.3])])

        embeddings = create_embeddings(["Test text"])
        assert len(embeddings) == 1
        assert embeddings[0].embedding == [0.1, 0.2, 0.3]
        mock_create.assert_called_once()

    @patch("litassist.utils.openai.Embedding.create")
    def test_create_embeddings_multiple_texts(self, mock_create):
        """Test creating embeddings for multiple texts."""
        mock_create.return_value = Mock(
            data=[Mock(embedding=[0.1, 0.2]), Mock(embedding=[0.3, 0.4])]
        )

        embeddings = create_embeddings(["Text 1", "Text 2"])
        assert len(embeddings) == 2
        assert embeddings[0].embedding == [0.1, 0.2]
        assert embeddings[1].embedding == [0.3, 0.4]

    @patch("litassist.utils.openai.Embedding.create")
    def test_create_embeddings_api_error(self, mock_create):
        """Test handling API error."""
        mock_create.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            create_embeddings(["Test text"])


class TestSaveLog:
    """Test the save_log function."""

    @patch("litassist.utils.click.get_current_context")
    @patch("litassist.utils.datetime")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_log_json(self, mock_file, mock_datetime, mock_context):
        """Test saving log in JSON format."""
        mock_context.return_value.obj = {"log_format": "json"}
        mock_datetime.now.return_value.strftime.return_value = "20240101-120000"

        test_data = {"key": "value"}
        save_log("test_command", test_data)

        mock_file.assert_called_once_with(
            "logs/test_command_20240101-120000.json", "w", encoding="utf-8"
        )
        written_content = mock_file().write.call_args[0][0]
        assert json.loads(written_content) == test_data

    @patch("litassist.utils.click.get_current_context")
    @patch("litassist.utils.datetime")
    @patch("builtins.open", new_callable=mock_open)
    def test_save_log_markdown(self, mock_file, mock_datetime, mock_context):
        """Test saving log in Markdown format."""
        mock_context.return_value.obj = {"log_format": "markdown"}
        mock_datetime.now.return_value.strftime.return_value = "20240101-120000"

        test_data = {
            "params": "test=true",
            "inputs": {"query": "test query"},
            "response": "test response",
        }
        save_log("test_command", test_data)

        mock_file.assert_called_once_with(
            "logs/test_command_20240101-120000.md", "w", encoding="utf-8"
        )
        written_content = mock_file().write.call_args[0][0]
        assert "# test_command Log" in written_content
        assert "test query" in written_content

    @patch("litassist.utils.os.makedirs")
    def test_save_log_creates_directory(self, mock_makedirs):
        """Test that save_log creates logs directory if it doesn't exist."""
        with patch("litassist.utils.click.get_current_context") as mock_ctx:
            with patch("builtins.open", mock_open()):
                mock_ctx.return_value.obj = {"log_format": "json"}
                save_log("test", {})
                mock_makedirs.assert_called_once_with("logs", exist_ok=True)


class TestHeartbeat:
    """Test the heartbeat decorator."""

    @patch("litassist.utils.click.echo")
    @patch("litassist.utils.threading.Event")
    @patch("litassist.utils.threading.Thread")
    def test_heartbeat_decorator(self, mock_thread, mock_event, mock_echo):
        """Test heartbeat decorator functionality."""
        mock_event_instance = Mock()
        mock_event.return_value = mock_event_instance

        @heartbeat(0.1)  # Short interval for testing
        def slow_function():
            return "result"

        result = slow_function()

        assert result == "result"
        mock_thread.assert_called_once()
        mock_event_instance.set.assert_called_once()

    def test_heartbeat_with_exception(self):
        """Test heartbeat handles function exceptions."""

        @heartbeat(0.1)
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()


class TestTimed:
    """Test the timed decorator."""

    @patch("litassist.utils.logging.debug")
    def test_timed_decorator(self, mock_debug):
        """Test timed decorator logs execution time."""

        @timed
        def fast_function():
            return "result"

        result = fast_function()

        assert result == "result"
        mock_debug.assert_called_once()
        debug_message = mock_debug.call_args[0][0]
        assert "fast_function took" in debug_message
        assert "seconds" in debug_message

    def test_timed_with_exception(self):
        """Test timed decorator handles exceptions."""

        @timed
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            failing_function()
