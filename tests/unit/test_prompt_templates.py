"""
Test suite for verifying YAML template completeness and structure.
Validates that all required prompt templates exist with correct key structures.
"""

import pytest
import yaml
from pathlib import Path


class TestPromptTemplates:
    """Test class for validating YAML template structures."""

    @pytest.fixture
    def prompts_dir(self):
        """Return path to prompts directory."""
        return Path(__file__).parent.parent.parent / "litassist" / "prompts"

    @pytest.fixture
    def expected_yaml_files(self):
        """Define expected YAML files in prompts directory."""
        return {
            "base.yaml",
            "strategies.yaml",
            "documents.yaml",
            "lookup.yaml",
            "verification.yaml",
            "formats.yaml",
            "processing.yaml",
            "system_feedback.yaml",
            "barbrief.yaml",
        }

    @pytest.fixture
    def expected_schemas(self):
        """Define expected key structure for each YAML file."""
        return {
            "base.yaml": {
                "base": {
                    "australian_law": str,
                    # "citation_standards": str,
                    # "accuracy_standards": str,
                    # "verification_standards": str,
                },
                "commands": {
                    "extractfacts": {"system": str},
                    "lookup": {"system": str},
                    "brainstorm": {
                        "system": str,
                        "orthodox_system": str,
                        "unorthodox_system": str,
                        "analysis_system": str,
                    },
                    "strategy": {"system": str, "ranking_system": str},
                    "draft": {"system": str},
                    "digest": {"system": str},
                },
            },
            "strategies.yaml": {
                "strategies": {
                    "brainstorm": {
                        "orthodox_prompt": str,
                        "unorthodox_prompt": str,
                        "analysis_prompt": str,
                        "regeneration_prompt": str,
                    },
                    "strategy": {
                        "strategic_options_instructions": str,
                        "next_steps_prompt": str,
                        "document_generation_context": str,
                        "unique_title_requirement": str,
                    },
                }
            },
            "documents.yaml": {
                "documents": {
                    "statement_of_claim": str,
                    "originating_application": str,
                    "affidavit": str,
                    # "notice_of_motion": str,
                    # "outline_submissions": str,
                    # "interlocutory_application": str,
                }
            },
            "lookup.yaml": {
                "lookup": {
                    # "research_assistant": {"system_prompt": str},
                    "extraction_instructions": {
                        "citations": str,
                        # "principles": str,
                        # "checklist": str,
                    },
                    "comprehensive_analysis": {
                        "requirements": str,
                        "citation_requirements": str,
                        "output_structure": str,
                    },
                    "standard_analysis": {"instructions": str},
                    # "standard_user_template": str,
                }
            },
            "verification.yaml": {
                "verification": {
                    "self_critique": str,
                    "citation_retry_instructions": str,
                    "light_verification": str,
                    "heavy_verification": str,
                    "system_prompt": str,
                }
            },
            "formats.yaml": {
                "formats": {
                    "case_facts_10_heading": str,
                    "strategic_options": str,
                    "irac_structure": str,
                    "chronological_summary": str,
                    "citation_extraction": str,
                    "principles_extraction": str,
                    "checklist_extraction": str,
                }
            },
            "processing.yaml": {
                "processing": {
                    "digest": {
                        "summary_mode": str,
                        "issues_mode": str,
                        "system_prompt": str,
                    },
                    "draft": {
                        "system_prompt_base": str,
                        "context_case_facts_and_strategies": str,
                        "context_case_facts_only": str,
                        "context_strategies_only": str,
                        "general_instructions": str,
                        "context_aware_prompt": str,
                        "user_prompt_template": str,
                    },
                    "extraction": {
                        "chunk_facts_prompt": str,
                        "chunk_system_prompt": str,
                        "organize_facts_prompt": str,
                        "organize_system_prompt": str,
                    },
                }
            },
            "system_feedback.yaml": {
                "system_feedback": {
                    "errors": {
                        "llm": dict,
                        "file": dict,
                        "processing": dict,
                        "external": dict,
                        "config": dict,
                        "citation": dict,
                    },
                    "warnings": {
                        "validation": dict,
                        "file_size": dict,
                        "api": dict,
                        "citation": dict,
                    },
                    "status": {
                        "progress": dict,
                        "completion": dict,
                        "file_ops": dict,
                        "search": dict,
                        "strategy_analysis": dict,
                        "command_completion": dict,
                        "debug": dict,
                        "citation_processing": dict,
                    },
                }
            },
        }

    def test_prompts_directory_exists(self, prompts_dir):
        """Test that the prompts directory exists."""
        assert prompts_dir.exists(), f"Prompts directory not found: {prompts_dir}"
        assert prompts_dir.is_dir(), f"Prompts path is not a directory: {prompts_dir}"

    def test_all_yaml_files_exist(self, prompts_dir, expected_yaml_files):
        """Test that all expected YAML files exist in the prompts directory."""
        existing_files = {f.name for f in prompts_dir.glob("*.yaml")}

        missing_files = expected_yaml_files - existing_files
        assert not missing_files, f"Missing YAML files: {sorted(missing_files)}"

        # Log extra files for awareness (not failure)
        extra_files = existing_files - expected_yaml_files
        if extra_files:
            print(f"Note: Extra YAML files found: {sorted(extra_files)}")

    def test_yaml_files_are_valid(self, prompts_dir, expected_yaml_files):
        """Test that all YAML files are syntactically valid."""
        for yaml_file in expected_yaml_files:
            file_path = prompts_dir / yaml_file
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    yaml.safe_load(f)
                except yaml.YAMLError as e:
                    pytest.fail(f"Invalid YAML syntax in {yaml_file}: {e}")

    def _validate_schema_recursive(self, data, schema, path=""):
        """Recursively validate data structure against schema."""
        errors = []

        if isinstance(schema, dict):
            if not isinstance(data, dict):
                errors.append(f"{path}: Expected dict, got {type(data).__name__}")
                return errors

            # Check for missing required keys
            missing_keys = set(schema.keys()) - set(data.keys())
            if missing_keys:
                for key in missing_keys:
                    errors.append(f"{path}.{key}: Missing required key")

            # Validate existing keys
            for key, expected_type in schema.items():
                if key in data:
                    key_path = f"{path}.{key}" if path else key
                    if isinstance(expected_type, dict):
                        errors.extend(
                            self._validate_schema_recursive(
                                data[key], expected_type, key_path
                            )
                        )
                    else:
                        if not isinstance(data[key], expected_type):
                            errors.append(
                                f"{key_path}: Expected {expected_type.__name__}, "
                                f"got {type(data[key]).__name__}"
                            )

        return errors

    @pytest.mark.parametrize(
        "yaml_file",
        [
            "base.yaml",
            "strategies.yaml",
            "documents.yaml",
            "lookup.yaml",
            "verification.yaml",
            "formats.yaml",
            "processing.yaml",
            "system_feedback.yaml",
        ],
    )
    def test_yaml_structure_completeness(
        self, prompts_dir, expected_schemas, yaml_file
    ):
        """Test that each YAML file has the complete expected structure."""
        file_path = prompts_dir / yaml_file

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        expected_schema = expected_schemas[yaml_file]
        errors = self._validate_schema_recursive(data, expected_schema)

        if errors:
            error_msg = f"Schema validation failed for {yaml_file}:\n" + "\n".join(
                errors
            )
            pytest.fail(error_msg)

    def test_no_empty_string_values(self, prompts_dir, expected_yaml_files):
        """Test that no template values are empty strings."""
        errors = []

        for yaml_file in expected_yaml_files:
            file_path = prompts_dir / yaml_file
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            empty_keys = self._find_empty_string_values(data, yaml_file)
            errors.extend(empty_keys)

        if errors:
            pytest.fail("Empty string values found:\n" + "\n".join(errors))

    def _find_empty_string_values(self, data, filename, path=""):
        """Recursively find empty string values in nested dictionary."""
        empty_keys = []

        if isinstance(data, dict):
            for key, value in data.items():
                key_path = f"{path}.{key}" if path else key
                if isinstance(value, str) and value.strip() == "":
                    empty_keys.append(f"{filename}:{key_path}")
                elif isinstance(value, dict):
                    empty_keys.extend(
                        self._find_empty_string_values(value, filename, key_path)
                    )

        return empty_keys

    def test_specific_command_templates_accessible(self, prompts_dir):
        """Test that specific templates used by commands are accessible."""
        # Test base templates
        base_file = prompts_dir / "base.yaml"
        with open(base_file, "r", encoding="utf-8") as f:
            base_data = yaml.safe_load(f)

        # Test critical base templates
        assert "base" in base_data
        assert "australian_law" in base_data["base"]
        assert "commands" in base_data
        assert "brainstorm" in base_data["commands"]

        # Test strategies templates
        strategies_file = prompts_dir / "strategies.yaml"
        with open(strategies_file, "r", encoding="utf-8") as f:
            strategies_data = yaml.safe_load(f)

        assert "strategies" in strategies_data
        assert "brainstorm" in strategies_data["strategies"]
        assert "orthodox_prompt" in strategies_data["strategies"]["brainstorm"]

        # Test lookup templates
        lookup_file = prompts_dir / "lookup.yaml"
        with open(lookup_file, "r", encoding="utf-8") as f:
            lookup_data = yaml.safe_load(f)

        assert "lookup" in lookup_data
        # assert "research_assistant" in lookup_data["lookup"]
        # assert "system_prompt" in lookup_data["lookup"]["research_assistant"]

    def test_template_content_has_substance(self, prompts_dir, expected_yaml_files):
        """Test that template content is substantial (not just whitespace)."""
        min_content_length = 10  # Minimum meaningful content length

        # Exceptions for templates that are legitimately short (formatting templates with placeholders)
        short_template_exceptions = {
            "system_feedback.yaml:system_feedback.warnings.citation.strict_mode_failed",
            "system_feedback.yaml:system_feedback.warnings.citation.error_item",
            "system_feedback.yaml:system_feedback.warnings.citation.retry_also_failed",
            "system_feedback.yaml:system_feedback.warnings.citation.citation_verification_warning",
            "system_feedback.yaml:system_feedback.warnings.citation.retry_successful",
            "system_feedback.yaml:system_feedback.status.file_ops.preview_line_short",
            "system_feedback.yaml:system_feedback.status.search.link_item",
        }

        for yaml_file in expected_yaml_files:
            file_path = prompts_dir / yaml_file
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            short_content = self._find_short_content(
                data, yaml_file, min_content_length, short_template_exceptions
            )

            if short_content:
                pytest.fail(
                    f"Templates with insufficient content in {yaml_file}:\n"
                    + "\n".join(short_content)
                )

    def _find_short_content(self, data, filename, min_length, exceptions=None, path=""):
        """Find string values that are too short to be meaningful."""
        if exceptions is None:
            exceptions = set()

        short_content = []

        if isinstance(data, dict):
            for key, value in data.items():
                key_path = f"{path}.{key}" if path else key
                full_key = f"{filename}:{key_path}"

                if isinstance(value, str):
                    if len(value.strip()) < min_length and full_key not in exceptions:
                        short_content.append(
                            f"{filename}:{key_path} (length: {len(value.strip())})"
                        )
                elif isinstance(value, dict):
                    short_content.extend(
                        self._find_short_content(
                            value, filename, min_length, exceptions, key_path
                        )
                    )

        return short_content
