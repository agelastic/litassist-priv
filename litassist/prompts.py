"""
Centralized prompt management system for LitAssist.

This module provides a unified interface for managing all prompts and templates
used throughout the LitAssist application. It loads YAML templates from the
prompts directory and provides methods for accessing and composing prompts.
"""

import yaml
import os
from pathlib import Path
from typing import Dict, Any


class PromptManager:
    """
    Centralized prompt management system for LitAssist.

    Provides template-based prompt generation with support for:
    - Australian legal compliance requirements
    - Document structure templates
    - Citation format standards
    - Dynamic prompt composition
    """

    def __init__(self):
        """Initialize the prompt manager with templates from YAML files."""
        self.prompts_dir = Path(__file__).parent / "prompts"
        self.templates = self._load_templates()
        self._templates_loaded = bool(self.templates)

    def _merge_dicts(self, a: dict, b: dict) -> dict:
        """
        Recursively merge dict b into dict a and return the result.
        """
        for k, v in b.items():
            if k in a and isinstance(a[k], dict) and isinstance(v, dict):
                a[k] = self._merge_dicts(a[k], v)
            else:
                a[k] = v
        return a

    def _load_templates(self) -> Dict[str, Any]:
        """
        Load all YAML template files from the prompts directory.

        Returns:
            Dict containing all loaded templates organized by file
        """
        templates = {}

        if not self.prompts_dir.exists():
            # Suppress warning during pytest runs
            if not os.environ.get("PYTEST_CURRENT_TEST"):
                print(f"[WARNING] Prompts directory not found at {self.prompts_dir}")
            return templates

        # Load all YAML files in the prompts directory
        for yaml_file in self.prompts_dir.glob("*.yaml"):
            try:
                with open(yaml_file, "r") as f:
                    file_templates = yaml.safe_load(f)
                    if file_templates:
                        # Recursively merge templates to avoid overwriting
                        templates = self._merge_dicts(templates, file_templates)
            except Exception as e:
                # Suppress warning during pytest runs
                if not os.environ.get("PYTEST_CURRENT_TEST"):
                    print(f"[WARNING] Error loading {yaml_file}: {e}")

        return templates

    def get(self, template_key: str, **kwargs) -> str:
        """
        Get a template by its dot-notation key.

        Args:
            template_key: Dot-separated path to template (e.g., 'base.australian_law')
            **kwargs: Parameters to substitute in the template

        Returns:
            The formatted template string

        Raises:
            KeyError: If the template is not found
            ValueError: If required template parameters are missing
        """
        if not self._templates_loaded:
            raise KeyError(
                f"Unable to retrieve template '{template_key}': no templates loaded"
            )

        # Split the key into parts
        parts = template_key.split(".")

        # Navigate through the template hierarchy
        current = self.templates
        for i, part in enumerate(parts):
            if not isinstance(current, dict) or part not in current:
                path_so_far = ".".join(parts[: i + 1])
                raise KeyError(
                    f"Template key '{template_key}' not found at '{path_so_far}'"
                )
            current = current[part]

        # If we got a string, format it with kwargs
        if isinstance(current, str):
            try:
                return current.format(**kwargs) if kwargs else current
            except KeyError as e:
                raise ValueError(f"Missing template variable: {e}")
        else:
            raise ValueError(f"Template '{template_key}' is not a string template")

    def get_system_prompt(self, command: str) -> str:
        """
        Get the system prompt for a specific command.

        Args:
            command: The command name (e.g., 'extractfacts', 'lookup')

        Returns:
            The complete system prompt including Australian law requirements
        """
        try:
            # Get base Australian law requirement
            base_prompt = self.get("base.australian_law")

            # Get command-specific system prompt
            command_prompt = self.get(f"commands.{command}.system")

            # Combine them
            return f"{base_prompt} {command_prompt}"
        except KeyError:
            # Fallback to just the command prompt if available
            try:
                return self.get(f"commands.{command}.system")
            except KeyError:
                raise KeyError(f"No system prompt found for command '{command}'")

    def get_format_template(self, format_name: str) -> str:
        """
        Get a format template by name.

        Args:
            format_name: The format template name (e.g., 'case_facts_10_heading')

        Returns:
            The format template string
        """
        return self.get(f"formats.{format_name}")

    def get_document_template(self, document_type: str, **kwargs) -> str:
        """
        Get a legal document template.

        Args:
            document_type: The document type (e.g., 'statement_of_claim')
            **kwargs: Parameters to substitute in the template

        Returns:
            The formatted document template
        """
        return self.get(f"documents.{document_type}", **kwargs)

    def compose_prompt(
        self, *template_keys: str, include_glob_help: bool = False
    ) -> str:
        """
        Compose multiple templates into a single prompt.

        Args:
            *template_keys: Variable number of template keys to combine
            include_glob_help: If True, append the glob help addon (if present)

        Returns:
            The combined prompt string
        """
        parts = []
        for key in template_keys:
            try:
                parts.append(self.get(key))
            except KeyError:
                print(f"[WARNING] Template '{key}' not found, skipping")

        # Add glob help section if requested and available
        if include_glob_help:
            try:
                parts.append(self.get("glob_help_section"))
            except KeyError:
                pass

        return "\n\n".join(parts)

    def list_templates(self) -> Dict[str, Any]:
        """
        List all available templates.

        Returns:
            Dictionary of all loaded templates
        """
        return self.templates.copy()


# Global instance for easy import
PROMPTS = PromptManager()


# Convenience functions for backward compatibility
def get_prompt(key: str, **kwargs) -> str:
    """Get a prompt template by key."""
    return PROMPTS.get(key, **kwargs)


def get_system_prompt(command: str) -> str:
    """Get the system prompt for a command."""
    return PROMPTS.get_system_prompt(command)


def get_format_template(format_name: str) -> str:
    """Get a format template."""
    return PROMPTS.get_format_template(format_name)
