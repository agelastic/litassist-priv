"""
Tests for brainstorm command internals.

Tests the end-to-end flow of the brainstorm command with mocked LLM responses.
"""

from unittest.mock import Mock, patch
from click.testing import CliRunner

from litassist.cli import cli
from litassist.commands import register_commands


class TestBrainstormInternals:
    """Test brainstorm command internal flow and output structure."""

    def setup_method(self):
        """Set up test fixtures."""
        # Register commands with CLI
        register_commands(cli)
        self.runner = CliRunner()

        # Create mock clients
        self.mock_orthodox_client = Mock()
        self.mock_unorthodox_client = Mock()
        self.mock_analysis_client = Mock()

        # Set model attributes to avoid "Mock not iterable" errors
        self.mock_orthodox_client.model = "anthropic/claude-sonnet-4"
        self.mock_unorthodox_client.model = "x-ai/grok-3"
        self.mock_analysis_client.model = "anthropic/claude-sonnet-4"

        # Set up mock responses
        self.orthodox_response = """## ORTHODOX LEGAL STRATEGIES

### 1. Breach of Contract - Failure to Deliver
**Legal Basis**: Australian Consumer Law s.54 - Guarantee as to acceptable quality
**Strategy**: Argue that defendant failed to deliver goods of acceptable quality within agreed timeframe.
**Key Evidence**: Purchase order dated 1/1/2024, delivery records showing 30-day delay
**Precedent**: ACCC v Valve Corporation [2016] FCA 196

### 2. Negligent Misrepresentation
**Legal Basis**: Common law tort of negligent misrepresentation
**Strategy**: Establish that defendant made false representations about product capabilities.
**Key Evidence**: Marketing materials, email correspondence  
**Precedent**: Hedley Byrne & Co Ltd v Heller & Partners Ltd [1964] AC 465

### 3. Misleading and Deceptive Conduct
**Legal Basis**: Competition and Consumer Act 2010 s.18
**Strategy**: Demonstrate pattern of misleading conduct in trade
**Key Evidence**: Website claims, customer testimonials
**Precedent**: Parkdale Custom Built Furniture v Puxu [1982] HCA 44"""

        self.unorthodox_response = """## UNORTHODOX BUT POTENTIALLY EFFECTIVE STRATEGIES

### 1. Social Media Pressure Campaign
**Approach**: Leverage negative publicity to force settlement
**Rationale**: Modern corporations are highly sensitive to brand damage
**Execution**: Document all issues publicly with evidence
**Risk**: Could backfire if seen as harassment

### 2. Industry Ombudsman Complaint
**Approach**: File complaint with relevant industry ombudsman
**Rationale**: Free process that can yield binding decisions
**Execution**: Compile comprehensive evidence dossier
**Risk**: Limited remedies available

### 3. Strategic Non-Payment
**Approach**: Withhold payment for related services as leverage
**Rationale**: Creates immediate financial pressure
**Execution**: Ensure legal right to withhold exists first
**Risk**: Could trigger counter-claims"""

        self.analysis_response = """## STRATEGIC ANALYSIS - MOST LIKELY TO SUCCEED

Based on the facts and available strategies, the following approaches show the highest probability of success:

### TOP 3 STRATEGIES:

1. **Misleading and Deceptive Conduct (Orthodox #3)**
   - Success Rate: 75%
   - Strong statutory protection under ACL
   - Low burden of proof
   - Significant penalties create settlement pressure

2. **Breach of Contract (Orthodox #1)**  
   - Success Rate: 70%
   - Clear documentary evidence
   - Straightforward damages calculation
   - Well-established legal principles

3. **Industry Ombudsman Complaint (Unorthodox #2)**
   - Success Rate: 65%
   - Cost-effective approach
   - Can run parallel to litigation
   - Often triggers internal review

### RECOMMENDED APPROACH:
Pursue misleading conduct claim while simultaneously filing ombudsman complaint. Hold breach of contract as fallback if primary strategy fails."""

        # Configure mock responses
        self.mock_orthodox_client.complete.return_value = (
            self.orthodox_response,
            {"total_tokens": 500},
        )
        self.mock_unorthodox_client.complete.return_value = (
            self.unorthodox_response,
            {"total_tokens": 400},
        )
        self.mock_analysis_client.complete.return_value = (
            self.analysis_response,
            {"total_tokens": 300},
        )

        # Mock citation validation (no issues)
        self.mock_orthodox_client.validate_citations.return_value = []
        self.mock_unorthodox_client.validate_citations.return_value = []
        self.mock_analysis_client.validate_citations.return_value = []

        # Mock verify method for the analysis client (used for brainstorm verification)
        self.mock_analysis_client.verify.return_value = "No corrections needed"

        # Create mock verification client for unorthodox verification
        self.mock_verification_client = Mock()
        self.mock_verification_client.model = "anthropic/claude-opus-4.1"
        self.mock_verification_client.verify.return_value = (
            self.unorthodox_response,
            {},
        )

    @patch("litassist.commands.brainstorm.analysis_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.unorthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.orthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.core.LLMClientFactory")
    @patch("litassist.commands.brainstorm.core.save_command_output")
    @patch("litassist.commands.brainstorm.core.save_log")
    def test_brainstorm_end_to_end(
        self,
        mock_save_log,
        mock_save_output,
        mock_factory_core,
        mock_factory_orth,
        mock_factory_unorth,
        mock_factory_analysis,
    ):
        """Test complete brainstorm flow with all three phases."""
        # Configure all factory patches to return our mock clients
        mock_factory_orth.for_command.return_value = self.mock_orthodox_client
        mock_factory_unorth.for_command.side_effect = [
            self.mock_unorthodox_client,  # First call for unorthodox
            self.mock_verification_client,  # Second call for verification
        ]
        mock_factory_analysis.for_command.return_value = self.mock_analysis_client
        mock_factory_core.for_command.side_effect = [
            self.mock_orthodox_client,  # For regeneration if needed
            self.mock_unorthodox_client,  # For regeneration if needed
            self.mock_analysis_client,  # For citation check at end
        ]

        # Mock save functions to capture output
        saved_content = {}

        def capture_save(
            command_name,
            content,
            description=None,
            metadata=None,
            critique_sections=None,
        ):
            filename = f"{command_name}_output.txt"
            saved_content[filename] = content
            return filename

        mock_save_output.side_effect = capture_save

        with self.runner.isolated_filesystem():
            # Create a test facts file
            with open("facts.txt", "w") as f:
                f.write("Test case facts: Plaintiff purchased goods from defendant.")

            # Run brainstorm command
            result = self.runner.invoke(
                cli,
                [
                    "brainstorm",
                    "--facts",
                    "facts.txt",
                    "--side",
                    "plaintiff",
                    "--area",
                    "commercial",
                ],
            )

            # Check command succeeded
            assert result.exit_code == 0

            # Verify clients were created
            mock_factory_orth.for_command.assert_called_with("brainstorm", "orthodox")
            mock_factory_unorth.for_command.assert_any_call("brainstorm", "unorthodox")
            mock_factory_analysis.for_command.assert_called_with(
                "brainstorm", "analysis"
            )

            # Verify output contains all sections
            output = result.output
            assert "Generating orthodox strategies..." in output
            assert "Generating unorthodox strategies..." in output
            assert "Analyzing most promising strategies..." in output

            # Check saved content structure
            assert len(saved_content) == 1
            saved_filename = list(saved_content.keys())[0]
            saved_text = saved_content[saved_filename]

            # Verify all three sections are in saved output
            assert "ORTHODOX LEGAL STRATEGIES" in saved_text
            assert "UNORTHODOX BUT POTENTIALLY EFFECTIVE STRATEGIES" in saved_text
            assert "STRATEGIC ANALYSIS - MOST LIKELY TO SUCCEED" in saved_text

            # Check statistics in output
            assert "[STATS] Generated strategies" in output
            assert "Orthodox strategies:" in output
            assert "Unorthodox strategies:" in output
            assert "Most likely to succeed:" in output

    @patch("litassist.commands.brainstorm.analysis_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.unorthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.orthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.core.LLMClientFactory")
    def test_brainstorm_with_citation_issues(
        self,
        mock_factory_core,
        mock_factory_orth,
        mock_factory_unorth,
        mock_factory_analysis,
    ):
        """Test brainstorm handling citation validation issues."""
        # Configure citation issues
        self.mock_orthodox_client.validate_citations.return_value = [
            "Found invalid citation: [2024] FAKE 123"
        ]

        mock_factory_orth.for_command.return_value = self.mock_orthodox_client
        mock_factory_unorth.for_command.side_effect = [
            self.mock_unorthodox_client,  # First call for unorthodox
            self.mock_verification_client,  # Second call for verification
        ]
        mock_factory_analysis.for_command.return_value = self.mock_analysis_client
        mock_factory_core.for_command.return_value = (
            self.mock_orthodox_client
        )  # For regeneration

        with self.runner.isolated_filesystem():
            with open("facts.txt", "w") as f:
                f.write("Test facts")

            # Mock regenerate function
            with patch(
                "litassist.commands.brainstorm.core.regenerate_bad_strategies"
            ) as mock_regen:
                mock_regen.return_value = "Fixed orthodox content"

                result = self.runner.invoke(
                    cli,
                    [
                        "brainstorm",
                        "--facts",
                        "facts.txt",
                        "--side",
                        "defendant",
                        "--area",
                        "civil",
                    ],
                )

                # Should still succeed
                assert result.exit_code == 0

                # Verify regeneration was called
                mock_regen.assert_called_once()
                assert "citation issues in orthodox strategies" in result.output

    @patch("litassist.commands.brainstorm.analysis_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.unorthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.orthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.core.LLMClientFactory")
    def test_brainstorm_output_formatting(
        self,
        mock_factory_core,
        mock_factory_orth,
        mock_factory_unorth,
        mock_factory_analysis,
    ):
        """Test that brainstorm formats output correctly."""
        mock_factory_orth.for_command.return_value = self.mock_orthodox_client
        mock_factory_unorth.for_command.side_effect = [
            self.mock_unorthodox_client,  # First call for unorthodox
            self.mock_verification_client,  # Second call for verification
        ]
        mock_factory_analysis.for_command.return_value = self.mock_analysis_client
        mock_factory_core.for_command.return_value = self.mock_analysis_client

        with self.runner.isolated_filesystem():
            with open("facts.txt", "w") as f:
                f.write("Test facts")

            result = self.runner.invoke(
                cli,
                [
                    "brainstorm",
                    "--facts",
                    "facts.txt",
                    "--side",
                    "plaintiff",
                    "--area",
                    "civil",
                ],
            )

            # Check formatting elements
            output = result.output

            # Progress messages
            assert "[SUCCESS]" in output

            # Strategy counts
            assert "Orthodox strategies:" in output
            assert "Unorthodox strategies:" in output
            assert "Most likely to succeed:" in output

            # Other formatting elements
            assert "[STATS]" in output
            assert "[TIP]" in output
            assert "[INFO]" in output

    @patch("litassist.commands.brainstorm.analysis_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.unorthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.orthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.core.LLMClientFactory")
    def test_brainstorm_with_research_files(
        self,
        mock_factory_core,
        mock_factory_orth,
        mock_factory_unorth,
        mock_factory_analysis,
    ):
        """Test brainstorm with additional research context."""
        mock_factory_orth.for_command.return_value = self.mock_orthodox_client
        mock_factory_unorth.for_command.side_effect = [
            self.mock_unorthodox_client,  # First call for unorthodox
            self.mock_verification_client,  # Second call for verification
        ]
        mock_factory_analysis.for_command.return_value = self.mock_analysis_client
        mock_factory_core.for_command.return_value = self.mock_analysis_client

        with self.runner.isolated_filesystem():
            # Create facts and research files
            with open("facts.txt", "w") as f:
                f.write("Basic facts")

            with open("research1.txt", "w") as f:
                f.write("Legal research on contract law")

            with open("research2.txt", "w") as f:
                f.write("Case law precedents")

            result = self.runner.invoke(
                cli,
                [
                    "brainstorm",
                    "--facts",
                    "facts.txt",
                    "--side",
                    "plaintiff",
                    "--area",
                    "commercial",
                    "--research",
                    "research1.txt",
                    "--research",
                    "research2.txt",
                ],
            )

            assert result.exit_code == 0

            # Check that research was mentioned
            output = result.output
            assert "Research context:" in output or "research" in output.lower()

            # Verify orthodox client got research context
            orthodox_messages = self.mock_orthodox_client.complete.call_args[0][0]
            # Should have research in the user message
            found_research = False
            for msg in orthodox_messages:
                if msg["role"] == "user" and "research" in msg["content"].lower():
                    found_research = True
                    break
            assert found_research

    @patch("litassist.commands.brainstorm.orthodox_generator.LLMClientFactory")
    def test_brainstorm_error_handling(self, mock_factory_orth):
        """Test brainstorm handles errors gracefully."""
        # Make orthodox generation fail
        self.mock_orthodox_client.complete.side_effect = Exception("API Error")

        mock_factory_orth.for_command.return_value = self.mock_orthodox_client

        with self.runner.isolated_filesystem():
            with open("facts.txt", "w") as f:
                f.write("Test facts")

            result = self.runner.invoke(
                cli,
                [
                    "brainstorm",
                    "--facts",
                    "facts.txt",
                    "--side",
                    "plaintiff",
                    "--area",
                    "civil",
                ],
            )

            # Should fail with error message
            assert result.exit_code != 0
            assert "Error generating orthodox strategies" in result.output

    def test_brainstorm_validates_inputs(self):
        """Test brainstorm validates required inputs."""
        with self.runner.isolated_filesystem():
            # Missing required --side option
            result = self.runner.invoke(cli, ["brainstorm", "--area", "civil"])

            assert result.exit_code != 0
            assert "Missing option" in result.output
            assert "--side" in result.output

    @patch("litassist.commands.brainstorm.analysis_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.unorthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.orthodox_generator.LLMClientFactory")
    @patch("litassist.commands.brainstorm.core.LLMClientFactory")
    @patch("os.path.exists")
    def test_brainstorm_default_facts_file(
        self,
        mock_exists,
        mock_factory_core,
        mock_factory_orth,
        mock_factory_unorth,
        mock_factory_analysis,
    ):
        """Test brainstorm uses case_facts.txt by default if it exists."""
        # Make it look like case_facts.txt exists
        mock_exists.return_value = True

        mock_factory_orth.for_command.return_value = self.mock_orthodox_client
        mock_factory_unorth.for_command.side_effect = [
            self.mock_unorthodox_client,  # First call for unorthodox
            self.mock_verification_client,  # Second call for verification
        ]
        mock_factory_analysis.for_command.return_value = self.mock_analysis_client
        mock_factory_core.for_command.return_value = self.mock_analysis_client

        with self.runner.isolated_filesystem():
            # Create the default file
            with open("case_facts.txt", "w") as f:
                f.write("Default case facts")

            # Don't specify --facts
            result = self.runner.invoke(
                cli, ["brainstorm", "--side", "plaintiff", "--area", "civil"]
            )

            assert result.exit_code == 0
            assert "Using facts from: case_facts.txt" in result.output
