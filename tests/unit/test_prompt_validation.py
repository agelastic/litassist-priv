"""
Tests to verify that all prompt keys used in commands exist in YAML files.
Simple regex-based extraction - no overengineering.
"""

import re
from pathlib import Path
import pytest
from litassist.prompts import PROMPTS


class TestPromptValidation:
    """Test that all prompt keys referenced in commands exist."""

    # List of command files that use PROMPTS
    COMMAND_FILES = [
        # Barbrief module files (refactored from barbrief.py)
        "litassist/commands/barbrief/brief_generator.py",
        # Brainstorm module files (refactored from brainstorm.py)
        "litassist/commands/brainstorm/analysis_generator.py",
        "litassist/commands/brainstorm/citation_regenerator.py",
        "litassist/commands/brainstorm/core.py",
        "litassist/commands/brainstorm/orthodox_generator.py",
        "litassist/commands/brainstorm/unorthodox_generator.py",
        # Caseplan module files (refactored from caseplan.py)
        "litassist/commands/caseplan/budget_assessor.py",
        "litassist/commands/caseplan/plan_generator.py",
        # Counselnotes module files (refactored from counselnotes.py)
        "litassist/commands/counselnotes/analysis_processor.py",
        "litassist/commands/counselnotes/consolidator.py",
        "litassist/commands/counselnotes/extraction_processor.py",
        "litassist/commands/digest/processors.py",
        # Draft module files (refactored from draft.py)
        "litassist/commands/draft/core.py",
        "litassist/commands/draft/prompt_builder.py",
        # Extractfacts module files (refactored from extractfacts.py)
        "litassist/commands/extractfacts/single_extractor.py",
        "litassist/commands/extractfacts/multi_extractor.py",
        "litassist/commands/lookup/processors.py",
        # Strategy module files (refactored from strategy.py)
        "litassist/commands/strategy/core.py",
        "litassist/commands/strategy/document_generator.py",
        "litassist/commands/strategy/ranker.py",
        # Verify module files (refactored from verify.py)
        "litassist/commands/verify/__init__.py",
        "litassist/commands/verify/reasoning_handler.py",
    ]

    @pytest.mark.parametrize("command_file", COMMAND_FILES)
    def test_prompts_exist(self, command_file):
        """Test that all PROMPTS.get() calls reference existing keys."""
        filepath = Path(command_file)

        if not filepath.exists():
            pytest.skip(f"File {command_file} does not exist")

        with open(filepath, "r") as f:
            content = f.read()

        # Find all PROMPTS.get("...") calls with static strings
        # Matches: PROMPTS.get("key") or PROMPTS.get('key')
        static_keys = re.findall(r'PROMPTS\.get\s*\(\s*["\']([^"\']+)["\']', content)

        # Check each key exists
        missing = []
        for key in static_keys:
            try:
                PROMPTS.get(key)
            except KeyError:
                missing.append(key)

        # Find f-string uses (just report them, don't try to resolve)
        # Matches: PROMPTS.get(f"...") or PROMPTS.get(f'...')
        fstring_uses = re.findall(r'PROMPTS\.get\s*\(\s*f["\']([^"\']+)["\']', content)

        # Report missing keys as test failure
        assert not missing, f"Missing prompt keys in {command_file}: {missing}"

        # Report f-string usage as warning (doesn't fail test)
        if fstring_uses:
            print(f"\nWarning: {command_file} uses f-string prompt keys:")
            for pattern in fstring_uses:
                print(f"  - {pattern}")
