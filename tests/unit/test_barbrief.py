"""Unit tests for the barbrief command."""

from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from litassist.commands.barbrief import barbrief
from litassist.commands.barbrief.validator import validate_case_facts
from litassist.commands.barbrief.section_builder import prepare_brief_sections


class TestValidateCaseFacts:
    """Test case facts validation."""

    def test_valid_case_facts(self):
        """Test validation with all required headings."""
        content = """
        # Case Facts
        
        ## Parties
        John Smith (Plaintiff) v ABC Corp (Defendant)
        
        ## Background
        Contract dispute arising from...
        
        ## Key Events
        1. January 2024: Contract signed
        
        ## Legal Issues
        - Breach of contract
        - Damages
        
        ## Evidence Available
        - Contract document
        - Emails
        
        ## Opposing Arguments
        Defendant claims...
        
        ## Procedural History
        Filed in Supreme Court...
        
        ## Jurisdiction
        Supreme Court of Victoria
        
        ## Applicable Law
        Contract Act, common law
        
        ## Client Objectives
        Seek damages and costs
        """
        assert validate_case_facts(content) is True

    def test_invalid_case_facts_missing_heading(self):
        """Test validation with missing required heading."""
        content = """
        ## Parties
        John v Jane
        
        ## Background
        Dispute about property
        
        ## Legal Issues
        Property settlement
        """
        # Missing most required headings
        assert validate_case_facts(content) is False

    def test_case_insensitive_validation(self):
        """Test that validation is case-insensitive."""
        content = """
        parties: John v Jane
        BACKGROUND: Dispute
        Key Events: Listed
        legal issues: Settlement
        Evidence Available: Documents
        opposing arguments: None
        Procedural History: Filed
        JURISDICTION: Federal
        applicable law: Family Law Act
        Client OBJECTIVES: Resolution
        """
        assert validate_case_facts(content) is True


class TestPrepareBriefSections:
    """Test brief section preparation."""

    def test_prepare_sections_minimal(self):
        """Test with minimal inputs."""
        sections = prepare_brief_sections(
            case_facts="Facts content",
            strategies=None,
            research_docs=[],
            supporting_docs=[],
            context=None,
            hearing_type="trial",
        )

        assert sections["case_facts"] == "Facts content"
        assert sections["hearing_type"] == "trial"
        assert sections["has_strategies"] is False
        assert sections["strategies"] == ""
        assert sections["research_count"] == 0
        assert sections["research_content"] == ""
        assert sections["supporting_count"] == 0
        assert sections["supporting_content"] == ""
        assert sections["context"] == "No specific context provided."

    def test_prepare_sections_full(self):
        """Test with all inputs provided."""
        sections = prepare_brief_sections(
            case_facts="Facts content",
            strategies="Strategy content",
            research_docs=["Research 1", "Research 2"],
            supporting_docs=["Doc 1", "Doc 2", "Doc 3"],
            context="Please focus on X",
            hearing_type="appeal",
        )

        assert sections["case_facts"] == "Facts content"
        assert sections["hearing_type"] == "appeal"
        assert sections["has_strategies"] is True
        assert sections["strategies"] == "Strategy content"
        assert sections["research_count"] == 2
        assert "Research 1" in sections["research_content"]
        assert "Research 2" in sections["research_content"]
        assert sections["supporting_count"] == 3
        assert "Doc 1" in sections["supporting_content"]
        assert sections["context"] == "Please focus on X"


class TestBarbriefCommand:
    """Test the barbrief CLI command."""

    @patch("litassist.commands.barbrief.document_reader.read_document")
    @patch("litassist.commands.barbrief.core.LLMClientFactory")
    @patch("litassist.commands.barbrief.core.save_command_output")
    def test_barbrief_minimal(
        self,
        mock_save,
        mock_factory,
        mock_read,
    ):
        """Test barbrief with minimal required arguments."""
        # Setup mocks
        valid_case_facts = """
        Parties: A v B
        Background: Test
        Key Events: Test
        Legal Issues: Test
        Evidence Available: Test
        Opposing Arguments: Test
        Procedural History: Test
        Jurisdiction: Test
        Applicable Law: Test
        Client Objectives: Test
        """
        mock_read.return_value = valid_case_facts

        mock_client = MagicMock()
        mock_client.complete.return_value = ("Brief content", {"total_tokens": 1000})
        mock_factory.for_command.return_value = mock_client

        mock_save.return_value = "outputs/barbrief_trial_123.txt"

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create a temporary file to satisfy Click's path validation
            with open("test_facts.txt", "w") as f:
                f.write("dummy content")

            result = runner.invoke(
                barbrief,
                ["test_facts.txt", "--hearing-type", "trial"],
            )

            # Assertions
            if result.exit_code != 0:
                print(f"Exit code: {result.exit_code}")
                print(f"Output: {result.output}")
                print(f"Exception: {result.exception}")
                if result.exception:
                    import traceback

                    traceback.print_exception(
                        type(result.exception),
                        result.exception,
                        result.exception.__traceback__,
                    )
            assert result.exit_code == 0
            mock_read.assert_called_once_with("test_facts.txt")
            mock_factory.for_command.assert_called_once_with("barbrief")
            mock_save.assert_called_once()
            assert "Barristers Brief Generated complete!" in result.output

    @patch("litassist.commands.barbrief.document_reader.read_document")
    def test_barbrief_invalid_case_facts(self, mock_read):
        """Test barbrief with invalid case facts format."""
        mock_read.return_value = "Invalid format content"

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test_facts.txt", "w") as f:
                f.write("dummy content")

            result = runner.invoke(
                barbrief,
                ["test_facts.txt", "--hearing-type", "trial"],
            )

            assert result.exit_code == 1
            assert "Case facts must be in 10-heading format" in result.output

    @patch("litassist.commands.barbrief.document_reader.read_document")
    @patch("litassist.commands.barbrief.core.LLMClientFactory")
    @patch("litassist.commands.barbrief.core.save_command_output")
    def test_barbrief_with_all_options(
        self,
        mock_save,
        mock_factory,
        mock_read,
    ):
        """Test barbrief with all optional arguments."""
        # Setup mocks
        valid_case_facts = """
        Parties: A v B
        Background: Test
        Key Events: Test
        Legal Issues: Test
        Evidence Available: Test
        Opposing Arguments: Test
        Procedural History: Test
        Jurisdiction: Test
        Applicable Law: Test
        Client Objectives: Test
        """

        mock_read.side_effect = [
            valid_case_facts,  # case facts
            "Strategy content",  # strategies
            "Research 1",  # research file 1
            "Research 2",  # research file 2
            "Document 1",  # supporting doc
        ]

        mock_client = MagicMock()
        mock_client.complete.return_value = ("Brief content", {"total_tokens": 5000})
        mock_client.command_context = "barbrief"
        mock_factory.for_command.return_value = mock_client

        mock_save.return_value = "outputs/barbrief_appeal_123.txt"

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem():
            # Create all necessary files
            for filename in [
                "test_facts.txt",
                "strategies.txt",
                "research1.txt",
                "research2.txt",
                "doc1.txt",
            ]:
                with open(filename, "w") as f:
                    f.write("dummy content")

            result = runner.invoke(
                barbrief,
                [
                    "test_facts.txt",
                    "--hearing-type",
                    "appeal",
                    "--strategies",
                    "strategies.txt",
                    "--research",
                    "research1.txt",
                    "--research",
                    "research2.txt",
                    "--documents",
                    "doc1.txt",
                    "--context",
                    "Focus on jurisdiction",
                    "--verify",
                ],
            )

            # Assertions
            assert result.exit_code == 0
            assert mock_read.call_count == 5
            mock_factory.for_command.assert_called_once_with("barbrief")
            mock_save.assert_called()

    @patch("litassist.commands.barbrief.document_reader.read_document")
    @patch("litassist.commands.barbrief.core.LLMClientFactory")
    @patch("litassist.commands.barbrief.brief_generator.save_command_output")
    @patch("litassist.commands.barbrief.core.save_command_output")
    @patch("litassist.commands.barbrief.brief_generator.verify_all_citations")
    def test_barbrief_with_citation_verification(
        self,
        mock_citation_verify,
        mock_save_core,
        mock_save_brief_gen,
        mock_factory,
        mock_read,
    ):
        """Test barbrief with citation verification enabled."""
        # Setup mocks
        valid_case_facts = """
        Parties: A v B
        Background: Test
        Key Events: Test
        Legal Issues: Test
        Evidence Available: Test
        Opposing Arguments: Test
        Procedural History: Test
        Jurisdiction: Test
        Applicable Law: Test
        Client Objectives: Test
        """
        mock_read.return_value = valid_case_facts

        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "Brief with [2024] HCA 1 citation",
            {"total_tokens": 2000},
        )
        mock_factory.for_command.return_value = mock_client

        mock_citation_verify.return_value = (
            ["[2024] HCA 1"],  # verified
            [("[2024] FAKE 99", "Citation not found in database")],  # unverified
        )

        mock_save_brief_gen.return_value = "outputs/barbrief_verify_report.txt"
        mock_save_core.return_value = "outputs/barbrief_interlocutory_123.txt"

        # Run command
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("test_facts.txt", "w") as f:
                f.write("dummy content")

            result = runner.invoke(
                barbrief,
                ["test_facts.txt", "--hearing-type", "interlocutory", "--verify"],
            )

            # Assertions
            assert result.exit_code == 0
            mock_citation_verify.assert_called_once()
            mock_save_brief_gen.assert_called_once()  # verification report
            mock_save_core.assert_called_once()  # main output
            assert "Warning: 1 citations could not be verified" in result.output
            assert "Verification report saved" in result.output


class TestBarbriefIntegration:
    """Integration tests for barbrief command."""

    def test_command_registration(self):
        """Test that barbrief is properly registered as a CLI command."""
        # Import register_commands to ensure commands are registered
        from litassist.cli import cli
        from litassist.commands import register_commands

        # Ensure commands are registered
        register_commands(cli)

        # Check that barbrief is in the list of commands
        command_names = list(cli.commands.keys())
        assert "barbrief" in command_names

    def test_hearing_type_choices(self):
        """Test that hearing type choices are enforced."""
        runner = CliRunner()
        result = runner.invoke(
            barbrief,
            ["test_facts.txt", "--hearing-type", "invalid_type"],
        )

        assert result.exit_code == 2  # Click validation error
        assert "Invalid value for '--hearing-type'" in result.output
