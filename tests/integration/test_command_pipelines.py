"""
Integration tests for command pipelines.
"""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner
import tempfile
import os

from litassist import cli
from litassist.commands import extractfacts, brainstorm, strategy


class TestCommandPipelines:
    """Test integration between different commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("litassist.commands.extractfacts.LLMClient")
    @patch("litassist.commands.brainstorm.LLMClient")
    def test_extractfacts_to_brainstorm_pipeline(
        self, mock_brainstorm_llm, mock_extract_llm
    ):
        """Test pipeline from extractfacts to brainstorm."""
        # Mock extractfacts LLM
        mock_extract_instance = Mock()
        mock_extract_instance.complete.return_value = (
            """Parties:
Plaintiff: John Smith
Defendant: ABC Corp

Background:
Contract dispute

Key Events:
1. Contract signed
2. Breach occurred""",
            {"tokens": 100},
        )
        mock_extract_llm.return_value = mock_extract_instance

        # Mock brainstorm LLM
        mock_brainstorm_instance = Mock()
        mock_brainstorm_instance.complete.return_value = (
            "Strategic options generated",
            {"tokens": 100},
        )
        mock_brainstorm_llm.return_value = mock_brainstorm_instance

        with self.runner.isolated_filesystem():
            # Create test PDF
            with open("test.pdf", "w") as f:
                f.write("Test content")

            # Step 1: Extract facts
            result1 = self.runner.invoke(cli.cli, ["extractfacts", "test.pdf"])
            assert result1.exit_code == 0
            assert os.path.exists("case_facts.txt")

            # Step 2: Brainstorm with extracted facts
            result2 = self.runner.invoke(
                cli.cli,
                [
                    "brainstorm",
                    "case_facts.txt",
                    "--side",
                    "plaintiff",
                    "--area",
                    "civil",
                ],
            )
            assert result2.exit_code == 0
            assert "Civil Law Strategies" in result2.output

    @patch("litassist.commands.extractfacts.LLMClient")
    @patch("litassist.commands.strategy.LLMClient")
    def test_extractfacts_to_strategy_pipeline(
        self, mock_strategy_llm, mock_extract_llm
    ):
        """Test pipeline from extractfacts to strategy."""
        # Mock extractfacts to produce compatible output
        valid_facts = """Parties:
Plaintiff: John Smith
Defendant: ABC Corp

Background:
Test background

Key Events:
Event 1

Legal Issues:
Issue 1
Issue 2

Evidence Available:
Evidence 1

Opposing Arguments:
Argument 1

Procedural History:
History 1

Jurisdiction:
Federal Court

Applicable Law:
Contract Law

Client Objectives:
Win case"""

        mock_extract_instance = Mock()
        mock_extract_instance.complete.return_value = (valid_facts, {"tokens": 100})
        mock_extract_llm.return_value = mock_extract_instance

        # Mock strategy LLM responses
        mock_strategy_instance = Mock()
        mock_strategy_instance.complete.side_effect = [
            # Strategic options
            (
                '{"options": [{"title": "Option 1", "probability": 75, "hurdles": []}]}',
                {"tokens": 100},
            ),
            # Next steps
            ('{"steps": ["Step 1"]}', {"tokens": 100}),
            # Document
            ('{"doc_type": "claim", "content": "Test"}', {"tokens": 100}),
        ]
        mock_strategy_llm.return_value = mock_strategy_instance

        with self.runner.isolated_filesystem():
            # Create test PDF
            with open("test.pdf", "w") as f:
                f.write("Test content")

            # Step 1: Extract facts
            result1 = self.runner.invoke(cli.cli, ["extractfacts", "test.pdf"])
            assert result1.exit_code == 0

            # Step 2: Generate strategy
            result2 = self.runner.invoke(
                cli.cli, ["strategy", "case_facts.txt", "--outcome", "Win case"]
            )
            assert result2.exit_code == 0
            assert "STRATEGIC OPTIONS" in result2.output

    @patch("litassist.utils.openai.Embedding.create")
    @patch("litassist.retriever.get_pinecone_client")
    @patch("litassist.commands.draft.LLMClient")
    def test_digest_to_draft_pipeline(
        self, mock_draft_llm, mock_pinecone, mock_embedding
    ):
        """Test pipeline from digest to draft."""
        # Mock embeddings
        mock_embedding.return_value = Mock(data=[Mock(embedding=[0.1] * 1536)])

        # Mock Pinecone
        mock_index = Mock()
        mock_index.query.return_value = Mock(
            matches=[
                Mock(metadata={"text": "Relevant passage 1"}),
                Mock(metadata={"text": "Relevant passage 2"}),
            ]
        )
        mock_index.describe_index_stats.return_value = Mock(
            dimension=1536, total_vector_count=100
        )
        mock_pinecone.return_value = mock_index

        # Mock draft LLM
        mock_draft_instance = Mock()
        mock_draft_instance.complete.return_value = ("Draft content", {"tokens": 100})
        mock_draft_llm.return_value = mock_draft_instance

        with self.runner.isolated_filesystem():
            # Create test PDF
            with open("test.pdf", "w") as f:
                f.write("Test content")

            # Just test draft command (digest is for analysis, not required for draft)
            result = self.runner.invoke(
                cli.cli, ["draft", "test.pdf", "Draft a contract"]
            )
            assert result.exit_code == 0
            assert mock_draft_instance.complete.called
