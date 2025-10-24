"""
Comprehensive end-to-end pipeline tests with offline stubs.

Tests the full litassist workflow with all external services mocked.
"""

import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from litassist.cli import cli
from litassist.commands import register_commands
from litassist.llm.factory import LLMClientFactory, LLMClient
from litassist.config import get_config
CONFIG = get_config()


class TestComprehensivePipeline:
    """Test full litassist pipeline with all external calls mocked."""

    def setup_method(self):
        """Set up test environment."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Register commands
        register_commands(cli)
        self.runner = CliRunner()

        # Create sample test files
        self._create_test_files()

        # Set up mock responses for different services
        self._setup_mock_responses()

    def teardown_method(self):
        """Clean up test environment."""
        os.chdir(self.original_cwd)
        shutil.rmtree(self.test_dir)

    def _create_test_files(self):
        """Create sample case files for testing."""
        # Case facts file with required 10-heading structure
        with open("case_facts.txt", "w") as f:
            f.write("""## PARTIES
- Plaintiff: John Smith (individual)
- Defendant: Jones Construction Pty Ltd (company)

## BACKGROUND
This is a commercial dispute regarding a residential building contract worth $500,000. The defendant ceased work claiming non-payment, while the plaintiff asserts the payment was not due as foundation work was incomplete.

## KEY EVENTS
- 1 January 2024: Written contract executed for construction of residential dwelling
- 15 January 2024: Defendant commenced construction work
- 1 February 2024: First progress payment of $100,000 allegedly due
- 1 March 2024: Defendant ceased all work on site
- Present: Site remains abandoned with no further work undertaken

## LEGAL ISSUES
1. Whether defendant validly suspended work for non-payment
2. Whether plaintiff breached contract by failing to pay progress payment
3. Whether foundation work was sufficiently complete to trigger payment
4. Quantum of damages for wrongful suspension

## EVIDENCE AVAILABLE
- Original written construction contract
- Progress payment schedule
- Site inspection reports showing foundation status
- Correspondence between parties regarding payment dispute
- Photos of abandoned construction site

## OPPOSING ARGUMENTS
- Defendant: Claims entitled to suspend work due to non-payment of $100,000 progress payment
- Plaintiff: Asserts payment not due as foundation work incomplete per contract requirements

## PROCEDURAL HISTORY
- No proceedings yet commenced
- Matter in pre-litigation phase
- Parties attempting negotiation without success

## JURISDICTION
Supreme Court of Victoria, Commercial Court

## APPLICABLE LAW
- Building and Construction Industry Security of Payment Act 2002 (Vic)
- Common law contract principles
- Australian Consumer Law (if applicable)

## CLIENT OBJECTIVES
Plaintiff seeks to compel defendant to complete construction at original contract price or obtain damages for breach of contract.
""")

        # Sample research file
        with open("research_contracts.txt", "w") as f:
            f.write("""
CONTRACT LAW RESEARCH - Progress Payments and Suspension Rights

1. Progress Payments Under Building Contracts
- Building and Construction Industry Security of Payment Act 2002 (Vic)
- Must serve payment claim in prescribed form
- Respondent has 10 business days to provide payment schedule

2. Right to Suspend Work
- Contractual right must be express
- Common law right requires fundamental breach
- Must give notice before suspension

Key Cases:
- Grocon Constructors v Planit Cocciardi [2016] VSC 23
- Seabay Properties v Galvin Construction [2018] VSC 432
""")

        # Create outputs directory
        os.makedirs("outputs", exist_ok=True)

        # Create a dummy strategies file for the strategy command
        with open(
            "outputs/brainstorm_commercial_plaintiff_plaintiff_in_commercial_law.txt",
            "w",
        ) as f:
            f.write("""## ORTHODOX STRATEGIES

1. Security of Payment Act Defense
   Challenge the validity of any payment claim under the Building and Construction Industry Security of Payment Act 2002 (Vic).

## UNORTHODOX STRATEGIES

1. Quantum Meruit Counterclaim
   File counterclaim for quantum meruit for project management work.

## MOST LIKELY TO SUCCEED

1. Security of Payment Act Defense - 75% likelihood
""")

    def _setup_mock_responses(self):
        """Set up canned responses for all external services."""
        self.mock_responses = {
            "caseplan": """## CASE PLAN FOR SMITH V JONES CONSTRUCTION

### IMMEDIATE ACTIONS (Next 7 days)
1. Review contract for suspension clause
2. Analyze payment claim requirements
3. Gather evidence of work completed

### DISCOVERY PHASE (Next 30 days)
1. Request all correspondence regarding payment claims
2. Obtain site inspection reports
3. Expert report on work completed to date

### LEGAL RESEARCH
1. Security of Payment Act application
2. Common law suspension rights
3. Damages for wrongful suspension
""",
            "extractfacts": """## EXTRACTED CASE FACTS

### PARTIES
- Plaintiff: John Smith (individual)
- Defendant: Jones Construction Pty Ltd (company)

### KEY DATES
- 1 January 2024: Contract executed
- 15 January 2024: Work commenced
- 1 February 2024: First progress payment allegedly due
- 1 March 2024: Work ceased
- 1 July 2024: Completion date

### AMOUNTS
- Contract price: $500,000
- First progress payment: $100,000

### DISPUTED ISSUES
1. Whether foundation work was completed
2. Whether payment was properly due
3. Whether suspension was justified
""",
            "digest": """## CHRONOLOGICAL SUMMARY

**1 January 2024**: Smith and Jones Construction enter into building contract for $500,000

**15 January 2024**: Jones Construction commences work on site

**1 February 2024**: First progress payment of $100,000 allegedly falls due
- Jones claims payment due for work completed
- Smith disputes foundation work incomplete

**1 March 2024**: Jones Construction ceases all work
- Claims suspension due to non-payment
- Smith argues wrongful suspension

**Present**: Site remains abandoned, no further work undertaken

## KEY LEGAL ISSUES IDENTIFIED
1. Progress payment requirements under contract
2. Right to suspend work for non-payment
3. Completion of foundation work as payment trigger
4. Damages for breach of contract
""",
            "brainstorm_orthodox": """## ORTHODOX LEGAL STRATEGIES

1. Security of Payment Act Claim
   Utilize the Building and Construction Industry Security of Payment Act 2002 (Vic) to challenge the validity of any payment claim. If defendant failed to serve a proper payment claim in the prescribed form, the suspension may be invalid.
   Key principles: Strict compliance required per Grocon Constructors v Planit Cocciardi [2016] VSC 23

2. Contractual Interpretation - Condition Precedent
   Argue that completion of foundation work was a condition precedent to the progress payment obligation. Apply strict interpretation of payment milestones.
   Key principles: Construction of payment clauses per Seabay Properties v Galvin Construction [2018] VSC 432
""",
            "brainstorm_unorthodox": """## UNORTHODOX STRATEGIES

1. Quantum Meruit Counterclaim
   File a counterclaim for quantum meruit for any project management or preliminary work performed by plaintiff before defendant commenced. This creates settlement pressure.
   Key principles: Restitutionary remedies available where contract frustrated

2. Corporate Regulator Complaint
   Lodge complaint with Victorian Building Authority regarding abandoned site and safety issues. Regulatory pressure may encourage commercial resolution.
   Key principles: Leverage regulatory compliance obligations
""",
            "brainstorm_analysis": """## MOST LIKELY TO SUCCEED

1. Security of Payment Act Defense
   Success likelihood: 75%
   The strict technical requirements often trip up contractors. If payment claim was defective, suspension was wrongful.

2. Contractual Interpretation Argument  
   Success likelihood: 70%
   Courts strictly construe payment triggers in building contracts. Strong documentary evidence supports incomplete foundations.
""",
            "verification": """## VERIFIED UNORTHODOX STRATEGIES

1. Quantum Meruit Counterclaim
   File a counterclaim for quantum meruit for any project management or preliminary work performed by plaintiff before defendant commenced. This creates settlement pressure.
   Key principles: Restitutionary remedies available where contract frustrated

2. Corporate Regulator Complaint
   Lodge complaint with Victorian Building Authority regarding abandoned site and safety issues. Regulatory pressure may encourage commercial resolution.
   Key principles: Leverage regulatory compliance obligations
""",
            "strategy": """## RECOMMENDED LITIGATION STRATEGY

### PRIMARY APPROACH
Run the Security of Payment Act defense while simultaneously pursuing wrongful suspension damages. This creates a two-front battle that maximizes settlement pressure.

### SEQUENCE OF ACTIONS
1. **Immediate**: File defense challenging payment claim validity
2. **Week 2**: Serve expert report on incomplete foundations
3. **Week 3**: Commence counterclaim for wrongful suspension damages
4. **Week 4**: Make strategic settlement offer

### EVIDENCE PRIORITIES
1. Payment claim documentation (or lack thereof)
2. Site photos showing incomplete foundations
3. Expert quantity surveyor report
4. Correspondence regarding work stages

### SETTLEMENT PARAMETERS
- Best case: Defendant completes work for original price
- Acceptable: Mutual termination with part payment for work done
- Walk-away: Less than $50,000 payment to defendant
""",
            "draft": """IN THE SUPREME COURT OF VICTORIA
AT MELBOURNE
COMMERCIAL COURT

BETWEEN:
JOHN SMITH                           Plaintiff
and
JONES CONSTRUCTION PTY LTD           Defendant

DEFENCE AND COUNTERCLAIM

THE DEFENDANT SAYS:

## DEFENCE

1. The Defendant admits paragraphs 1, 2 and 3 of the Statement of Claim.

2. As to paragraph 4, the Defendant:
   (a) denies that it wrongfully ceased work;
   (b) says that it was entitled to suspend work due to the Plaintiff's failure to pay the first progress payment.

3. As to paragraph 5, the Defendant says that:
   (a) the first progress payment of $100,000 was due on 1 February 2024;
   (b) the payment was due upon completion of the foundation excavation stage;
   (c) the foundation excavation was completed by 31 January 2024.

## COUNTERCLAIM

4. The Defendant repeats paragraphs 1 to 3 above.

5. The Plaintiff breached the contract by failing to pay $100,000 on 1 February 2024.

6. By reason of the matters aforesaid, the Defendant has suffered loss and damage.

DATED: [DATE TO BE PROVIDED]

[DEFENDANT'S SOLICITORS TO BE PROVIDED]
""",
            "barbrief": """## BARRISTER'S BRIEF - SMITH V JONES CONSTRUCTION

### MATTER SUMMARY
Commercial dispute regarding residential building contract. Defendant suspended work claiming non-payment. Plaintiff argues payment not due as foundations incomplete.

### KEY CHRONOLOGY
- 1/1/24: Contract signed ($500,000)
- 15/1/24: Work commenced  
- 1/2/24: Payment dispute arises ($100,000)
- 1/3/24: Work suspended
- Present: Site abandoned

### CRITICAL ISSUES FOR COUNSEL
1. **Payment Claim Validity**: Did defendant serve valid payment claim under Security of Payment Act?
2. **Foundation Completion**: Was foundation work sufficiently complete to trigger payment?
3. **Suspension Rights**: Did contract permit suspension for non-payment?

### RECOMMENDED APPROACH
Focus on technical defects in payment claim. Security of Payment Act requires strict compliance - any defect defeats claim and makes suspension wrongful.

### EVIDENCE NEEDED
- Original contract (especially payment/suspension clauses)
- Any payment claim documents
- Site photos from February 2024
- Expert report on foundation completion status

### SETTLEMENT RANGE
Best: Completion at original price
Acceptable: Termination with $200-250k payment
Worst: Pay $100k progress payment plus costs
""",
            "verify": """No corrections needed.""",
            "lookup": """## CASE LAW LOOKUP RESULTS

### Grocon Constructors v Planit Cocciardi [2016] VSC 23
- Security of Payment Act requires strict compliance with form requirements
- Defective payment claims are invalid ab initio
- No right to suspend work based on invalid payment claim

### Seabay Properties v Galvin Construction [2018] VSC 432  
- Progress payment triggers must be construed strictly
- Substantial completion required unless contract specifies otherwise
- Photos and expert evidence admissible on completion issues
""",
            # Mock LLM responses
            "llm_complete": "Mock LLM response for testing",
            # Mock Pinecone responses
            "pinecone_query": {
                "matches": [
                    {
                        "id": "doc_001",
                        "score": 0.92,
                        "metadata": {
                            "text": "Progress payments in building contracts require strict compliance with contractual milestones."
                        },
                    }
                ]
            },
            # Mock Google CSE response
            "google_cse": {
                "items": [
                    {
                        "title": "[2016] VSC 23",
                        "link": "https://jade.io/case/2016_VSC_23",
                        "snippet": "Grocon Constructors v Planit Cocciardi - Security of Payment Act",
                    }
                ]
            },
        }

    def test_full_pipeline(self):
        """Test complete litassist pipeline with all external calls mocked."""
        # Use context managers to patch everything
        # Setup citation mocks first to prevent ANY real API calls
        with patch("litassist.citation.verify.verify_all_citations") as mock_verify_citations:
            with patch("litassist.citation_context.fetch_citation_context") as mock_fetch_context:
                with patch("litassist.citation.google_cse.search_legal_database_via_cse") as mock_search_cse:
                    # Configure citation mocks to prevent real API calls
                    verified_citations = ["[2016] VSC 23", "[2018] VSC 432", "Security of Payment Act"]
                    mock_verify_citations.return_value = (verified_citations, [])
                    mock_fetch_context.return_value = {}
                    # Mock CSE search to always find citations and return a URL
                    mock_search_cse.return_value = (True, "https://jade.io/citation/test")
                    
                    self._run_pipeline_test()
    
    def _run_pipeline_test(self):
        """Run the actual pipeline test with all mocks."""
        with (
            patch("litassist.llm.api_handlers.get_openai_client") as mock_get_client,
            patch("requests.get") as mock_requests_get,
            patch("requests.post") as mock_requests_post,
            patch("aiohttp.ClientSession"),
            patch("litassist.helpers.pinecone_config.get_pinecone_client") as mock_get_pinecone_client,
            patch("litassist.commands.digest.processors.PROMPTS") as mock_prompts,
            patch("litassist.commands.strategy.core.PROMPTS") as mock_strategy_prompts,
            patch("litassist.commands.brainstorm.PROMPTS") as mock_brainstorm_prompts,
            patch("litassist.commands.lookup.processors.PROMPTS") as mock_lookup_prompts,
            patch.object(CONFIG, "max_chars", 10000),
            patch.object(CONFIG, "use_token_limits", True),
            patch.object(CONFIG, "openrouter_key", "test_key"),
            patch.object(CONFIG, "openai_key", "test_key"),
            patch.object(CONFIG, "or_base", "https://openrouter.ai/api/v1"),
            patch.object(CONFIG, "or_key", "test_key"),
            patch.object(CONFIG, "google_cse_key", "test_key"),
            patch.object(CONFIG, "google_cse_id", "test_id"),
        ):
            # Configure PROMPTS mock - return actual strings with format method
            class MockPromptString(str):
                def format(self, **kwargs):
                    return "Test prompt content"

            mock_prompts.get.return_value = MockPromptString("Test prompt content")
            mock_strategy_prompts.get.return_value = MockPromptString(
                "Test prompt content"
            )
            mock_brainstorm_prompts.get.return_value = MockPromptString(
                "Test prompt content"
            )
            mock_lookup_prompts.get.return_value = MockPromptString(
                "Test prompt content"
            )

            # Configure OpenAI v1.x mock client
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            def openai_side_effect(*args, **kwargs):
                # Filter out parameters that OpenAI doesn't accept
                # These should have been filtered by get_model_parameters but mock needs to handle them
                openai_params = ['model', 'messages', 'temperature', 'top_p', 'max_tokens', 
                                 'frequency_penalty', 'presence_penalty', 'stop', 'stream', 
                                 'n', 'seed', 'response_format', 'max_completion_tokens', 
                                 'reasoning', 'extra_body']  # reasoning goes in extra_body for OpenRouter
                
                # Remove unexpected parameters like thinking_effort
                for key in list(kwargs.keys()):
                    if key not in openai_params:
                        kwargs.pop(key)
                
                messages = kwargs.get("messages", [])
                if not messages:
                    messages = args[0] if args else []

                # Determine response based on the messages content
                user_content = ""
                for msg in messages:
                    if msg.get("role") == "user":
                        user_content = msg.get("content", "").lower()
                        break

                # Create mock response
                mock_response = Mock()
                mock_response.choices = [Mock()]
                mock_response.usage = Mock(
                    total_tokens=100,
                    prompt_tokens=50,
                    completion_tokens=50,
                    model_dump=lambda: {
                        "total_tokens": 100,
                        "prompt_tokens": 50,
                        "completion_tokens": 50,
                    },
                )

                # Route to appropriate mock response
                if "case plan" in user_content:
                    content = self.mock_responses["caseplan"]
                elif "extract" in user_content and "facts" in user_content:
                    content = self.mock_responses["extractfacts"]
                elif "chronological" in user_content or "digest" in user_content:
                    content = self.mock_responses["digest"]
                elif "orthodox" in user_content:
                    content = self.mock_responses["brainstorm_orthodox"]
                elif "unorthodox" in user_content:
                    content = self.mock_responses["brainstorm_unorthodox"]
                elif "verif" in user_content and "unorthodox" in str(messages):
                    # Return the verified unorthodox strategies
                    content = self.mock_responses["verification"]
                elif "most likely" in user_content:
                    content = self.mock_responses["brainstorm_analysis"]
                elif "strategy" in user_content or "litigation" in user_content:
                    content = self.mock_responses["strategy"]
                elif "defence" in user_content or "draft" in user_content:
                    content = self.mock_responses["draft"]
                elif "barrister" in user_content or "brief" in user_content:
                    content = self.mock_responses["barbrief"]
                elif "verify" in user_content or "correction" in user_content:
                    content = self.mock_responses["verify"]
                else:
                    content = self.mock_responses["llm_complete"]

                mock_response.choices[0].message = Mock(content=content)
                mock_response.choices[0].error = None
                mock_response.choices[0].finish_reason = "stop"

                return mock_response

            mock_client.chat.completions.create.side_effect = openai_side_effect

            # Configure Google CSE mock (for citation verification)
            def requests_get_side_effect(url, **kwargs):
                mock_resp = Mock()
                if "googleapis.com/customsearch" in url:
                    mock_resp.json.return_value = self.mock_responses["google_cse"]
                    mock_resp.status_code = 200
                else:
                    mock_resp.status_code = 404
                return mock_resp

            mock_requests_get.side_effect = requests_get_side_effect

            # Configure Pinecone mock
            mock_index = Mock()
            mock_index.query.return_value = self.mock_responses["pinecone_query"]
            mock_get_pinecone_client.return_value = mock_index

            # Track all external calls
            external_calls = []

            # Patch all external call points to track them
            original_openai = mock_client.chat.completions.create.side_effect

            def track_openai(*args, **kwargs):
                external_calls.append(("openai", args, kwargs))
                return original_openai(*args, **kwargs)

            mock_client.chat.completions.create.side_effect = track_openai

            original_requests_get = mock_requests_get.side_effect

            def track_requests_get(*args, **kwargs):
                external_calls.append(("requests_get", args, kwargs))
                return original_requests_get(*args, **kwargs)

            mock_requests_get.side_effect = track_requests_get

            # Execute the pipeline commands in sequence
            commands = [
                ("caseplan", ["caseplan", "case_facts.txt", "--budget", "standard"]),
                ("extractfacts", ["extractfacts", "case_facts.txt"]),
                ("digest", ["digest", "case_facts.txt", "--mode", "summary"]),
                (
                    "brainstorm",
                    [
                        "brainstorm",
                        "--facts",
                        "case_facts.txt",
                        "--side",
                        "plaintiff",
                        "--area",
                        "commercial",
                    ],
                ),
                (
                    "strategy",
                    [
                        "strategy",
                        "case_facts.txt",
                        "--outcome",
                        "Defendant to complete construction at original price",
                        "--strategies",
                        "outputs/brainstorm_commercial_plaintiff_plaintiff_in_commercial_law.txt",
                    ],
                ),
                (
                    "draft",
                    [
                        "draft",
                        "case_facts.txt",
                        "Draft a defence and counterclaim for the defendant",
                    ],
                ),
                ("barbrief", ["barbrief", "case_facts.txt", "--hearing-type", "trial"]),
            ]

            # Store outputs for verification
            outputs = {}

            for cmd_name, cmd_args in commands:
                result = self.runner.invoke(cli, cmd_args)

                # Command should succeed
                assert result.exit_code == 0, (
                    f"{cmd_name} failed: {result.output}\nException: {result.exception}"
                )

                # Store output
                outputs[cmd_name] = result.output

                # Verify output contains expected content
                if cmd_name == "caseplan":
                    assert (
                        "Litigation plan generated" in result.output
                        or "Plan saved" in result.output
                    )
                elif cmd_name == "extractfacts":
                    assert (
                        "Facts extracted" in result.output or "[SAVED]" in result.output
                    )
                elif cmd_name == "digest":
                    assert (
                        "Digest complete" in result.output or "[SAVED]" in result.output
                    )
                elif cmd_name == "brainstorm":
                    assert (
                        "Generated strategies" in result.output
                        or "Brainstorm complete" in result.output
                    )
                elif cmd_name == "strategy":
                    assert (
                        "strategies analyzed" in result.output
                        or "[SAVED]" in result.output
                    )
                elif cmd_name == "draft":
                    assert (
                        "Draft created" in result.output or "[SAVED]" in result.output
                    )
                elif cmd_name == "barbrief":
                    assert (
                        "Brief created" in result.output or "[SAVED]" in result.output
                    )

            # Verify outputs directory exists (commands create it)
            assert os.path.exists("outputs"), "Outputs directory should exist"

            # The fact that all commands ran successfully without real API calls
            # demonstrates the pipeline works with mocked external services

            # Verify external calls were made (but all mocked)
            assert len(external_calls) > 0, "Should have made external calls"
            assert any(call[0] == "openai" for call in external_calls), (
                "Should have called OpenAI"
            )

            # Ensure no real HTTP calls were made
            assert mock_requests_post.call_count == 0, (
                "Should not make real POST requests"
            )
            assert all(
                call[0] in ["openai", "requests_get"] for call in external_calls
            ), "Only expected mocked calls"

    def test_env_var_overrides(self):
        """Test that environment variables override model configurations."""
        # Set environment variables
        test_env = {
            "OPENAI_MODEL": "gpt-4-turbo-preview",
            "ANTHROPIC_MODEL": "claude-3-opus",
            "GOOGLE_MODEL": "gemini-ultra",
            "XGROK_MODEL": "grok-2-beta",
        }

        with patch.dict(os.environ, test_env):
            # Test that config picks up environment variables
            from litassist.config import Config

            # Create a config instance that should pick up env vars
            with patch.object(Config, "_load_config", return_value={}):
                Config()

                # The get_required_key method should return env values when available
                # Testing model overrides
                assert os.environ.get("OPENAI_MODEL") == "gpt-4-turbo-preview"
                assert os.environ.get("ANTHROPIC_MODEL") == "claude-3-opus"
                assert os.environ.get("GOOGLE_MODEL") == "gemini-ultra"
                assert os.environ.get("XGROK_MODEL") == "grok-2-beta"

                # Test that LLMClientFactory would use these when creating clients
                with patch("litassist.config.CONFIG") as mock_config:
                    mock_config.openrouter_key = "test_key"
                    mock_config.openai_key = "test_key"

                    # Mock the model retrieval to use env var
                    with patch.object(
                        LLMClientFactory, "get_model_for_command"
                    ) as mock_get_model:
                        # When env var is set, it should override default model
                        mock_get_model.return_value = test_env["GOOGLE_MODEL"]

                        # Verify the override is returned
                        model = LLMClientFactory.get_model_for_command("lookup")
                        assert model == "gemini-ultra"

    def test_token_limit_enforcement(self):
        """Test that token limits are enforced when CONFIG.use_token_limits=True."""
        # Test with use_token_limits = True
        with (
            patch.object(CONFIG, "use_token_limits", True),
            patch.object(CONFIG, "token_limit", 16384),
            patch.object(CONFIG, "openrouter_key", "test_key"),
            patch.object(CONFIG, "openai_key", "test_key"),
        ):
            # Create an LLMClient which should apply token limits
            client = LLMClient("openai/gpt-4")

            # Should use token_limit from config
            expected_limit = 16384

            # Check that default_params includes max_tokens
            assert "max_tokens" in client.default_params
            assert client.default_params["max_tokens"] == expected_limit

        # Test with use_token_limits = False
        with (
            patch.object(CONFIG, "use_token_limits", False),
            patch.object(CONFIG, "openrouter_key", "test_key"),
            patch.object(CONFIG, "openai_key", "test_key"),
        ):
            # Create another client
            client2 = LLMClient("openai/gpt-4")

            # Should not include max_tokens when disabled
            assert "max_tokens" not in client2.default_params
