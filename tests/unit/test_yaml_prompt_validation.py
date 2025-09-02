"""
Test suite for YAML prompt file validation.
Catches fatfingering, missing prompts, and policy violations.
"""

import pytest
import yaml
from pathlib import Path
import re


class TestYAMLPromptValidation:
    """Validate YAML prompt files for common errors."""

    @pytest.fixture
    def prompts_dir(self):
        """Return path to prompts directory."""
        return Path(__file__).parent.parent.parent / "litassist" / "prompts"

    def test_yaml_files_parse(self, prompts_dir):
        """Test that all YAML files parse without syntax errors."""
        yaml_files = prompts_dir.glob("*.yaml")
        errors = []

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    yaml.safe_load(f)
            except yaml.YAMLError as e:
                errors.append(f"{yaml_file.name}: {e}")

        if errors:
            pytest.fail("YAML parsing errors:\n" + "\n".join(errors))

    def test_all_placeholders_are_valid(self, prompts_dir):
        """Test that placeholder names are consistent and valid."""
        # Common placeholder patterns used in the codebase
        # Collected from actual usage in YAML files and Python code
        valid_placeholders = {
            # Core data placeholders
            "facts_content",
            "outcome",
            "legal_issues",
            "facts",
            "side",
            "area",
            "research",
            "research_context",
            "orthodox_strategies",
            "unorthodox_strategies",
            "strategy_count",
            "selected_count",
            "remaining_strategies_list",
            "strategies_list",
            "format_instructions",
            "content",
            "chunk_template",
            "chunk",
            "digest_prompt",
            "question",
            "links",
            "context",
            "prompt",
            # Error and status placeholders
            "operation",
            "error",
            "command_name",
            "chunk_idx",
            "path",
            "issue",
            "applicable_law",
            "application",
            "conclusion",
            "confidence",
            "sources_text",
            "command",
            "timestamp",
            "sources",
            "option_num",
            "strategy_content",
            "option_number",
            "existing_count",
            "existing_titles",
            "base_prompt",
            "feedback",
            "citation_instructions",
            # Document and file placeholders
            "recommended_strategy",
            "chunk_num",
            "total_chunks",
            "name",
            "place",
            "court_name",
            "file_number",
            "plaintiff_name",
            "defendant_name",
            "size",
            "max_size",
            "word_count",
            "file_type",
            "count",
            "key",
            "value",
            "log_type",
            "config_key",
            "model",
            "error_type",
            "citation",
            "reason",
            # Processing placeholders
            "context_instruction",
            "documents",
            "chunk_analyses",
            "document_type",
            "user_request",
            "all_facts",
            "hearing_date",
            "hearing_type",
            "hearing_time",
            "jurisdiction",
            "registry",
            "judge",
            "judicial_officer",
            "party_capacity",
            # System feedback placeholders
            "found",
            "expected_area",
            "doc_path",
            "length",
            "line_preview",
            "line",
            "link",
            "index",
            "extract_type",
            "analysis_type",
            "missing_list",
            "strategy_numbers",
            "strategy_type",
            "max_attempts",
            "title",
            "output_file",
            "function_name",
            "duration",
            "start_timestamp",
            "end_timestamp",
            "attempt",
            "retry_attempt",
            "max_retries",
            "item",
            "strategy_num",
            "issue_count",
            "categorized_issues",
            # Configuration placeholders
            "litassist_capabilities",
            "max_tokens",
            "temperature",
            "reasoning_effort",
            "service",
            "budget",
            "instructions",
            "request",
            # Document-specific placeholders
            "applicant_name",
            "respondent_name",
            "deponent_name",
            "deponent_full_name",
            "deponent_occupation",
            "deponent_address",
            "deponent_role",
            "annexure_mark",
            "witness_full_name",
            "witness_address",
            "witness_occupation",
            # Barbrief placeholders
            "case_facts",
            "strategies",
            "research_count",
            "research_content",
            "supporting_count",
            "supporting_content",
            "config_path",
            # Strategy placeholders
            "most_likely_count",
            "orthodox_count",
            "unorthodox_count",
            "strategies_content",
            # Additional document placeholders
            "location",
            "state",
            "date",
            "file_number_or_placeholder",
            "witness_address_or_placeholder",
            "witness_occupation_if_known",
            # CoVe citation context placeholders
            "legal_context",
            "questions",
            # Cross-file consolidation placeholders
            "file_count",
            "file_digests",
            # Reasoning trace placeholders
            "reasoning_header",
        }

        errors = []
        yaml_files = prompts_dir.glob("*.yaml")

        for yaml_file in yaml_files:
            with open(yaml_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Find all placeholders in the file
            placeholders = re.findall(r"\{([a-zA-Z_]+)\}", content)

            for placeholder in placeholders:
                if placeholder not in valid_placeholders:
                    # Check if it's a typo of a valid placeholder
                    possible_typos = [
                        valid
                        for valid in valid_placeholders
                        if abs(len(valid) - len(placeholder)) <= 2
                    ]
                    if possible_typos:
                        errors.append(
                            f"{yaml_file.name}: Unknown placeholder '{{{placeholder}}}' "
                            f"(did you mean: {', '.join(possible_typos)}?)"
                        )
                    else:
                        errors.append(
                            f"{yaml_file.name}: Unknown placeholder '{{{placeholder}}}'"
                        )

        if errors:
            pytest.fail("Invalid placeholders found:\n" + "\n".join(errors))

    def test_critical_prompts_not_empty(self, prompts_dir):
        """Test that critical prompts exist and are not empty."""
        from litassist.prompts import PROMPTS

        critical_prompts = [
            "base.australian_law",
            "commands.brainstorm.orthodox_system",
            "commands.brainstorm.unorthodox_system",
            "commands.brainstorm.analysis_system",
            "strategies.brainstorm.orthodox_base",
            "strategies.brainstorm.unorthodox_base",
            "strategies.brainstorm.analysis_base",
            "reasoning.instruction",
            "analysis.base_case_facts_prompt",
            "analysis.case_facts_prompt",
            "verification.citation_retry_instructions",
        ]

        errors = []

        for prompt_key in critical_prompts:
            try:
                content = PROMPTS.get(prompt_key)
                if not content or len(content.strip()) < 10:
                    errors.append(
                        f"{prompt_key}: Empty or too short (less than 10 chars)"
                    )
            except KeyError:
                errors.append(f"{prompt_key}: Missing prompt")

        if errors:
            pytest.fail("Critical prompt issues:\n" + "\n".join(errors))

    def test_no_emojis_in_prompts(self, prompts_dir):
        """Test that no emoji characters exist in any YAML file (CLAUDE.md policy)."""
        # Unicode emoji ranges
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags (iOS)
            "\U00002500-\U00002bef"  # chinese char
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "\U0001f926-\U0001f937"
            "\U00010000-\U0010ffff"
            "\u2640-\u2642"
            "\u2600-\u2b55"
            "\u200d"
            "\u23cf"
            "\u23e9"
            "\u231a"
            "\ufe0f"  # dingbats
            "\u3030"
            "]+",
            re.UNICODE,
        )

        errors = []
        yaml_files = prompts_dir.glob("*.yaml")

        for yaml_file in yaml_files:
            with open(yaml_file, "r", encoding="utf-8") as f:
                content = f.read()
                line_num = 0
                for line in content.splitlines():
                    line_num += 1
                    emojis_found = emoji_pattern.findall(line)
                    if emojis_found:
                        errors.append(
                            f"{yaml_file.name}:{line_num}: Found emoji(s): {', '.join(emojis_found)}"
                        )

        if errors:
            pytest.fail(
                "CRITICAL: Emojis found in YAML files (violates CLAUDE.md policy):\n"
                + "\n".join(errors)
            )
