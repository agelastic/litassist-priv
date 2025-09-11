"""
Pytest configuration and shared fixtures for LitAssist tests.
"""

import pytest
from unittest.mock import Mock, patch
import tempfile
from pathlib import Path

# Mock the CONFIG object before any imports to prevent SystemExit
import sys

mock_config = Mock()
mock_config.oa_key = "test-openai-key"
mock_config.get_openai_api_key = Mock(return_value="test-openai-key")
mock_config.get_jade_api_key = Mock(return_value="test-jade-key")
mock_config.openrouter_api_key = "test-openrouter-key"
mock_config.google_api_key = "test-google-key"
mock_config.google_cse_id = "test-cse-id"
mock_config.pinecone_api_key = "test-pinecone-key"
mock_config.pinecone_environment = "test-env"
mock_config.pinecone_index = "test-index"
mock_config.log_format = "json"
mock_config.heartbeat_interval = 10
mock_config.fetch_timeout = 10
mock_config.max_fetch_time = 300
mock_config.selenium_enabled = True
mock_config.selenium_timeout_multiplier = 2

# Replace the CONFIG in sys.modules before litassist is imported
config_module = Mock()
config_module.CONFIG = mock_config
sys.modules["litassist.config"] = config_module

# Mock fixtures for external services


@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses."""
    with patch("openai.OpenAI") as mock_openai_class:
        # Create mock client instance
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Mock embeddings.create and chat.completions.create
        mock_embed = mock_client.embeddings.create
        mock_chat = mock_client.chat.completions.create

        # Mock embedding response
        mock_embed.return_value = Mock(data=[Mock(embedding=[0.1] * 1536)])

        # Mock chat completion response
        mock_chat.return_value = Mock(
            choices=[Mock(message=Mock(content="Test response"), finish_reason="stop")],
            usage=Mock(total_tokens=100, prompt_tokens=50, completion_tokens=50),
        )

        yield mock_embed, mock_chat


@pytest.fixture
def mock_pinecone():
    """Mock Pinecone client responses."""
    with patch("pinecone.init") as mock_init:
        with patch("pinecone.Index") as mock_index_cls:
            mock_index = Mock()
            mock_index_cls.return_value = mock_index

            # Mock vector operations
            mock_index.query.return_value = Mock(
                matches=[
                    Mock(
                        id="test-id",
                        score=0.95,
                        metadata={"text": "Test passage", "source": "Test source"},
                    )
                ]
            )

            yield mock_init, mock_index


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient for command tests."""

    class MockLLMClient:
        def __init__(self, model, temperature=0.2, top_p=0.95):
            self.model = model
            self.temperature = temperature
            self.top_p = top_p

        def complete(self, messages, tools=None):
            # Return different responses based on the command
            return "Test response content", {"total_tokens": 100}

        def verify(self, content):
            return []

    with patch("litassist.llm.LLMClient", MockLLMClient):
        yield MockLLMClient


@pytest.fixture
def mock_retriever():
    """Mock Retriever for command tests."""

    class MockRetriever:
        def __init__(self, *args, **kwargs):
            pass

        def retrieve(self, query_embedding, top_k=5):
            return [
                {"text": "Test passage 1", "source": "Source 1"},
                {"text": "Test passage 2", "source": "Source 2"},
            ]

    with patch("litassist.retriever.Retriever", MockRetriever):
        yield MockRetriever


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_pdf(temp_dir):
    """Create a test PDF file."""
    pdf_path = temp_dir / "test.pdf"
    pdf_path.write_text("Test PDF content")
    return pdf_path


@pytest.fixture
def test_text_file(temp_dir):
    """Create a test text file."""
    txt_path = temp_dir / "test.txt"
    txt_path.write_text("Test text content")
    return txt_path


@pytest.fixture
def test_case_facts(temp_dir):
    """Create a test case facts file."""
    facts_path = temp_dir / "case_facts.txt"
    facts_path.write_text(
        """
Parties:
- Applicant: John Smith
- Respondent: ABC Corporation

Background:
Test case background.

Key Events:
1. Event one
2. Event two

Issues:
- Issue one
- Issue two

Jurisdiction:
Federal Court of Australia

Evidence:
- Document A
- Witness B

Relief Sought:
Damages and injunction
"""
    )
    return facts_path


@pytest.fixture
def mock_env(monkeypatch):
    """Mock environment variables."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-openrouter-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-google-key")
    monkeypatch.setenv("GOOGLE_CSE_ID", "test-cse-id")
    monkeypatch.setenv("PINECONE_API_KEY", "test-pinecone-key")
    monkeypatch.setenv("PINECONE_ENVIRONMENT", "test-env")
    monkeypatch.setenv("PINECONE_INDEX", "test-index")
