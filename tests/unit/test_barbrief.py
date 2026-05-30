"""Unit tests for the barbrief command."""

from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from litassist.commands.barbrief import barbrief
from litassist.commands.barbrief.section_builder import prepare_brief_sections
from litassist.prompts import PROMPTS

_VALID_FACTS = "\n".join(
    f"{h}: placeholder"
    for h in [
        "Parties",
        "Background",
        "Key Events",
        "Legal Issues",
        "Evidence Available",
        "Opposing Arguments",
        "Procedural History",
        "Jurisdiction",
        "Applicable Law",
        "Client Objectives",
    ]
)


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
        Parties:
        A v B
        Background:
        Test
        Key Events:
        Test
        Legal Issues:
        Test
        Evidence Available:
        Test
        Opposing Arguments:
        Test
        Procedural History:
        Test
        Jurisdiction:
        Test
        Applicable Law:
        Test
        Client Objectives:
        Test
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
        Parties:
        A v B
        Background:
        Test
        Key Events:
        Test
        Legal Issues:
        Test
        Evidence Available:
        Test
        Opposing Arguments:
        Test
        Procedural History:
        Test
        Jurisdiction:
        Test
        Applicable Law:
        Test
        Client Objectives:
        Test
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
        Parties:
        A v B
        Background:
        Test
        Key Events:
        Test
        Legal Issues:
        Test
        Evidence Available:
        Test
        Opposing Arguments:
        Test
        Procedural History:
        Test
        Jurisdiction:
        Test
        Applicable Law:
        Test
        Client Objectives:
        Test
        """
        mock_read.return_value = valid_case_facts

        mock_client = MagicMock()
        mock_client.complete.return_value = (
            "Brief with [2024] HCA 1 citation",
            {"total_tokens": 2000},
        )
        mock_factory.for_command.return_value = mock_client

        mock_citation_verify.return_value = (
            [{"citation": "[2024] HCA 1", "url": "", "snippet": "", "reason": ""}],  # verified
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

    @patch("litassist.commands.barbrief.document_reader.read_document")
    def test_barbrief_omitted_case_facts_none_present(self, mock_read):
        """No case_facts arg and no case_facts*.txt in cwd -> ClickException."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(barbrief, ["--hearing-type", "trial"])
        assert result.exit_code != 0
        assert "case facts" in result.output.lower()
        mock_read.assert_not_called()

    @patch("litassist.commands.barbrief.document_reader.read_document")
    @patch("litassist.commands.barbrief.core.LLMClientFactory")
    @patch("litassist.commands.barbrief.core.save_command_output")
    def test_barbrief_generation_failure_surfaces_clickexception(
        self, mock_save, mock_factory, mock_read
    ):
        """An LLM failure surfaces as a ClickException, not a raw traceback."""
        mock_read.return_value = _VALID_FACTS
        client = MagicMock()
        client.complete.side_effect = Exception("upstream boom")
        mock_factory.for_command.return_value = client
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("facts.txt", "w") as f:
                f.write("dummy")
            result = runner.invoke(barbrief, ["facts.txt", "--hearing-type", "trial"])
        assert result.exit_code == 1
        assert "LLM API error" in result.output

    @patch("litassist.commands.barbrief.brief_generator.verify_all_citations")
    @patch("litassist.commands.barbrief.document_reader.read_document")
    @patch("litassist.commands.barbrief.core.LLMClientFactory")
    @patch("litassist.commands.barbrief.core.save_command_output")
    def test_barbrief_verification_exception_is_handled(
        self, mock_save, mock_factory, mock_read, mock_verify
    ):
        """If citation verification raises, the command warns and still succeeds."""
        mock_read.return_value = _VALID_FACTS
        mock_save.return_value = "outputs/barbrief_trial.txt"
        client = MagicMock()
        client.complete.return_value = ("Brief body", {"total_tokens": 100})
        mock_factory.for_command.return_value = client
        mock_verify.side_effect = Exception("verifier down")
        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("facts.txt", "w") as f:
                f.write("dummy")
            result = runner.invoke(
                barbrief, ["facts.txt", "--hearing-type", "trial", "--verify"]
            )
        assert result.exit_code == 0
        assert "Citation verification error" in result.output

    @patch("litassist.commands.barbrief.document_reader.read_document")
    @patch("litassist.commands.barbrief.core.LLMClientFactory")
    @patch("litassist.commands.barbrief.core.save_command_output")
    def test_barbrief_all_hearing_types(self, mock_save, mock_factory, mock_read):
        """Every --hearing-type choice runs (only trial/appeal were covered)."""
        mock_read.return_value = _VALID_FACTS
        mock_save.return_value = "outputs/barbrief.txt"
        client = MagicMock()
        client.complete.return_value = ("Brief body", {"total_tokens": 100})
        mock_factory.for_command.return_value = client
        runner = CliRunner()
        for hearing in ("trial", "directions", "interlocutory", "appeal"):
            with runner.isolated_filesystem():
                with open("facts.txt", "w") as f:
                    f.write("dummy")
                result = runner.invoke(
                    barbrief, ["facts.txt", "--hearing-type", hearing]
                )
            assert result.exit_code == 0, f"{hearing}: {result.output}"

    @patch("litassist.commands.barbrief.document_reader.read_document")
    @patch("litassist.commands.barbrief.core.LLMClientFactory")
    @patch("litassist.commands.barbrief.core.save_command_output")
    def test_barbrief_optional_files_partial(self, mock_save, mock_factory, mock_read):
        """Partial optional-file combinations (strategies-only, research-only) run."""
        mock_save.return_value = "outputs/barbrief.txt"
        client = MagicMock()
        client.complete.return_value = ("Brief body", {"total_tokens": 100})
        mock_factory.for_command.return_value = client
        runner = CliRunner()
        # strategies only
        mock_read.side_effect = [_VALID_FACTS, "strategy content"]
        with runner.isolated_filesystem():
            for name in ("facts.txt", "strat.txt"):
                with open(name, "w") as f:
                    f.write("dummy")
            result = runner.invoke(
                barbrief,
                ["facts.txt", "--hearing-type", "trial", "--strategies", "strat.txt"],
            )
        assert result.exit_code == 0, result.output
        # research only
        mock_read.side_effect = [_VALID_FACTS, "research content"]
        with runner.isolated_filesystem():
            for name in ("facts.txt", "res.txt"):
                with open(name, "w") as f:
                    f.write("dummy")
            result = runner.invoke(
                barbrief,
                ["facts.txt", "--hearing-type", "trial", "--research", "res.txt"],
            )
        assert result.exit_code == 0, result.output

    def test_barbrief_main_prompt_renders_with_section_keys(self):
        """barbrief.main placeholders stay in sync with prepare_brief_sections."""
        sections = prepare_brief_sections(
            case_facts="facts",
            strategies=None,
            research_docs=[],
            supporting_docs=[],
            context=None,
            hearing_type="trial",
        )
        rendered = PROMPTS.get("barbrief.main", **sections)
        assert isinstance(rendered, str)
        # no unfilled placeholder remains for any section key
        for key in sections:
            assert "{" + key + "}" not in rendered
        assert "trial" in rendered
        assert isinstance(PROMPTS.get("barbrief.system"), str)

    @patch("litassist.commands.barbrief.document_reader.read_document")
    def test_read_all_documents_tags_sources(self, mock_read):
        """research/supporting docs are wrapped with SOURCE markers so the brief
        can name them in the ANNEXURES section."""
        from litassist.commands.barbrief.document_reader import read_all_documents

        mock_read.side_effect = lambda p: f"body-of-{p}"
        result = read_all_documents("cf.txt", (), ("research1.txt",), ("doc1.txt",))
        assert "=== SOURCE: research1.txt ===" in result["research_docs"][0]
        assert "body-of-research1.txt" in result["research_docs"][0]
        assert "=== SOURCE: doc1.txt ===" in result["supporting_docs"][0]
