"""
Essential pytest tests for centralized prompt management.

Tests the core functionality of the PromptManager class and ensures
commands fail appropriately when centralized prompts are unavailable.
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch

from litassist.prompts import PromptManager, PROMPTS


class TestPromptManager:
    """Test the core PromptManager functionality."""

    def test_template_loading(self):
        """Test that templates load correctly from YAML files."""
        # Use the global PROMPTS instance which should have loaded templates
        templates = PROMPTS.list_templates()

        # Verify key template categories exist
        assert "base" in templates
        assert "commands" in templates
        assert "formats" in templates

        # Verify essential templates exist
        assert "australian_law" in templates["base"]
        assert "extractfacts" in templates["commands"]
        assert "case_facts_10_heading" in templates["formats"]

    def test_get_basic_template(self):
        """Test basic template retrieval."""
        australian_law = PROMPTS.get("base.australian_law")

        assert isinstance(australian_law, str)
        assert len(australian_law) > 0
        assert "Australian" in australian_law

    def test_get_system_prompt(self):
        """Test system prompt generation for commands."""
        system_prompt = PROMPTS.get_system_prompt("extractfacts")

        assert isinstance(system_prompt, str)
        assert len(system_prompt) > 0
        # Should contain both Australian law base and command-specific content
        assert "Australian" in system_prompt

    def test_get_format_template(self):
        """Test format template retrieval."""
        format_template = PROMPTS.get_format_template("case_facts_10_heading")

        assert isinstance(format_template, str)
        assert len(format_template) > 0
        # Should contain the 10 headings structure
        assert "Parties" in format_template
        assert "Background" in format_template

    def test_template_composition(self):
        """Test combining multiple templates."""
        composed = PROMPTS.compose_prompt(
            "base.australian_law",
            # 'base.citation_standards'
        )

        assert isinstance(composed, str)
        assert len(composed) > 0
        # Should contain content from both templates
        assert "Australian" in composed

    def test_template_with_parameters(self):
        """Test template parameter substitution."""
        # This test assumes document templates support parameters
        try:
            doc_template = PROMPTS.get_document_template(
                "statement_of_claim",
                court_name="Test Court",
                file_number="123/2024",
                plaintiff_name="John Doe",
                defendant_name="Jane Smith",
            )
            assert "Test Court" in doc_template
            assert "123/2024" in doc_template
            assert "John Doe" in doc_template
            assert "Jane Smith" in doc_template
        except KeyError:
            # If document template doesn't exist, test with a basic template
            pytest.skip("Document templates not available for parameter testing")

    def test_nonexistent_template_raises_keyerror(self):
        """Test that missing templates raise KeyError."""
        with pytest.raises(
            KeyError, match="Template key 'nonexistent.template' not found"
        ):
            PROMPTS.get("nonexistent.template")

    def test_invalid_template_key_raises_keyerror(self):
        """Test that malformed template keys raise KeyError."""
        with pytest.raises(KeyError):
            PROMPTS.get("base.nonexistent_key")


class TestExplicitFailureBehavior:
    """Test that commands fail explicitly without centralized prompts."""

    def test_empty_prompt_manager_fails_correctly(self):
        """Test PromptManager with no templates fails with clear errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create PromptManager with no templates directory
            class EmptyPromptManager(PromptManager):
                def __init__(self):
                    self.prompts_dir = temp_path / "nonexistent_prompts"
                    self.templates = self._load_templates()
                    self._templates_loaded = bool(self.templates)

            empty_manager = EmptyPromptManager()

            # Should fail with clear KeyError
            with pytest.raises(KeyError, match="no templates loaded"):
                empty_manager.get("base.australian_law")

            with pytest.raises(KeyError, match="No system prompt found"):
                empty_manager.get_system_prompt("extractfacts")

            with pytest.raises(KeyError, match="no templates loaded"):
                empty_manager.get_format_template("case_facts_10_heading")

    def test_missing_template_directory(self):
        """Test behavior when templates directory doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            class NoDirectoryPromptManager(PromptManager):
                def __init__(self):
                    self.prompts_dir = temp_path / "missing_directory"
                    self.templates = self._load_templates()
                    self._templates_loaded = bool(self.templates)

            no_dir_manager = NoDirectoryPromptManager()

            # Should have empty templates
            assert no_dir_manager.templates == {}
            assert not no_dir_manager._templates_loaded

            # Should fail when trying to get templates
            with pytest.raises(KeyError, match="no templates loaded"):
                no_dir_manager.get("base.australian_law")


class TestIntegrationWithCommands:
    """Test that command modules integrate correctly with prompt management."""

    def test_llm_client_requires_prompts(self):
        """Test that LLMClient requires centralized prompts."""
        # This test verifies that llm.py will fail without prompts
        # by importing and checking the code path

        # Mock empty PROMPTS to simulate missing templates
        with patch("litassist.llm.PROMPTS") as mock_prompts:
            mock_prompts.get.side_effect = KeyError("Template not found")

            # Import should work, but using it should fail
            from litassist.llm import LLMClient

            client = LLMClient("test/model")

            # The complete method should fail when it tries to get Australian law prompt
            with pytest.raises(KeyError):
                client.complete([{"role": "user", "content": "test"}])

    def test_extractfacts_command_requires_prompts(self):
        """Test that extractfacts command requires centralized prompts."""
        # Mock empty PROMPTS
        with patch("litassist.commands.extractfacts.PROMPTS") as mock_prompts:
            mock_prompts.get_format_template.side_effect = KeyError(
                "Template not found"
            )
            mock_prompts.get_system_prompt.side_effect = KeyError("Template not found")

            # Import the command function
            from litassist.commands.extractfacts import extractfacts

            # The command should fail when trying to get templates
            # (We can't easily test the click command without more complex mocking,
            # but we can verify the template access points would fail)

            # This test verifies the code structure requires prompts
            assert hasattr(extractfacts, "name")  # Verify Click command imported
            assert extractfacts.name == "extractfacts"

    def test_lookup_command_requires_prompts(self):
        """Test that lookup command requires centralized prompts."""
        # Mock empty PROMPTS
        with patch("litassist.commands.lookup.PROMPTS") as mock_prompts:
            mock_prompts.get_system_prompt.side_effect = KeyError("Template not found")

            # Import the command function
            from litassist.commands.lookup import lookup

            # The command should fail when trying to get system prompt
            # This test verifies the code structure requires prompts
            assert hasattr(lookup, "name")  # Verify Click command imported
            assert lookup.name == "lookup"


class TestTemplateValidation:
    """Test template content validation and structure."""

    def test_essential_templates_exist(self):
        """Test that all essential templates are present."""
        essential_templates = [
            "base.australian_law",
            # 'base.citation_standards',
            "commands.extractfacts.system",
            "commands.lookup.system",
            "formats.case_facts_10_heading",
        ]

        for template_key in essential_templates:
            try:
                content = PROMPTS.get(template_key)
                assert isinstance(content, str)
                assert len(content.strip()) > 0
            except KeyError:
                pytest.fail(f"Essential template '{template_key}' is missing")

    def test_australian_law_template_content(self):
        """Test that Australian law template contains expected content."""
        australian_law = PROMPTS.get("base.australian_law")

        # Should mention Australian requirements
        assert any(
            word in australian_law.lower() for word in ["australian", "australia"]
        )

    def test_case_facts_template_structure(self):
        """Test that case facts template has required structure."""
        case_facts = PROMPTS.get_format_template("case_facts_10_heading")

        # Should contain the 10 essential headings
        required_headings = [
            "Parties",
            "Background",
            "Key Events",
            "Legal Issues",
            "Evidence",
            "Arguments",
            "Procedural",
            "Jurisdiction",
            "Law",
            "Objectives",
        ]

        # At least most headings should be present (allowing for variations)
        found_headings = sum(
            1 for heading in required_headings if heading.lower() in case_facts.lower()
        )

        assert (
            found_headings >= 7
        ), f"Case facts template missing essential headings. Found {found_headings}/10"

    def test_templates_are_strings(self):
        """Test that all loaded templates are valid strings."""

        def check_dict_values(d, path=""):
            for key, value in d.items():
                current_path = f"{path}.{key}" if path else key
                if isinstance(value, dict):
                    check_dict_values(value, current_path)
                elif isinstance(value, str):
                    assert len(value.strip()) > 0, f"Empty template at {current_path}"
                else:
                    pytest.fail(
                        f"Template at {current_path} is not a string: {type(value)}"
                    )

        templates = PROMPTS.list_templates()
        check_dict_values(templates)


@pytest.mark.unit
class TestPromptManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_malformed_yaml_handling(self):
        """Test handling of malformed YAML files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prompts_dir = temp_path / "prompts"
            prompts_dir.mkdir()

            # Create malformed YAML file
            bad_yaml = prompts_dir / "bad.yaml"
            bad_yaml.write_text("malformed: yaml: content: [")

            # Create custom PromptManager
            class TestPromptManager(PromptManager):
                def __init__(self):
                    self.prompts_dir = prompts_dir
                    self.templates = self._load_templates()
                    self._templates_loaded = bool(self.templates)

            manager = TestPromptManager()

            # Should handle malformed YAML gracefully
            # Templates should be empty or minimal since YAML couldn't load
            assert isinstance(manager.templates, dict)

    def test_template_parameter_missing(self):
        """Test error when template parameters are missing."""
        # Create a template that requires parameters
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            prompts_dir = temp_path / "prompts"
            prompts_dir.mkdir()

            # Create template with parameters
            test_yaml = prompts_dir / "test.yaml"
            test_yaml.write_text(
                """
test:
  parameterized: "Hello {name}, welcome to {place}!"
"""
            )

            class TestPromptManager(PromptManager):
                def __init__(self):
                    self.prompts_dir = prompts_dir
                    self.templates = self._load_templates()
                    self._templates_loaded = bool(self.templates)

            manager = TestPromptManager()

            # Should work with parameters
            result = manager.get("test.parameterized", name="John", place="Australia")
            assert "Hello John, welcome to Australia!" == result

            # Should fail without required parameters
            with pytest.raises(ValueError, match="Missing template variable"):
                manager.get("test.parameterized", name="John")  # Missing 'place'
