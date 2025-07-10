#!/usr/bin/env python3
"""
Simple test script for the centralized prompt management system.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_prompt_system():
    """Test that the prompt management system works correctly."""
    try:
        from litassist.prompts import PROMPTS

        print("[START] Testing centralized prompt management system...")

        # Test 1: Basic prompt retrieval
        print("\n1. Testing basic prompt retrieval...")
        try:
            australian_law = PROMPTS.get("base.australian_law")
            print(f"[PASS] Australian law base: {australian_law}")
        except Exception as e:
            print(f"[FAIL] Failed to get base.australian_law: {e}")
            return False

        # Test 2: System prompt generation
        print("\n2. Testing system prompt generation...")
        try:
            system_prompt = PROMPTS.get_system_prompt("extractfacts")
            print(f"[PASS] Extractfacts system prompt: {system_prompt[:100]}...")
        except Exception as e:
            print(f"[FAIL] Failed to get extractfacts system prompt: {e}")
            return False

        # Test 3: Format template retrieval
        print("\n3. Testing format template retrieval...")
        try:
            format_template = PROMPTS.get_format_template("case_facts_10_heading")
            print(f"[PASS] Case facts format: {format_template[:100]}...")
        except Exception as e:
            print(f"[FAIL] Failed to get case_facts_10_heading format: {e}")
            return False

        # Test 4: Template composition
        print("\n4. Testing template composition...")
        try:
            composed = PROMPTS.compose_prompt(
                "base.australian_law", "base.citation_standards"
            )
            print(f"[PASS] Composed prompt: {composed[:100]}...")
        except Exception as e:
            print(f"[FAIL] Failed to compose prompts: {e}")
            return False

        # Test 5: Template listing
        print("\n5. Testing template listing...")
        try:
            templates = PROMPTS.list_templates()
            print(f"[PASS] Found {len(templates)} template categories")
            for category in templates.keys():
                print(f"  - {category}")
        except Exception as e:
            print(f"[FAIL] Failed to list templates: {e}")
            return False

        print("\n[PASS] All prompt management tests passed!")
        return True

    except ImportError as e:
        print(f"[FAIL] Failed to import prompt management system: {e}")
        return False


def test_fallback_behavior():
    """Test that commands work even without centralized prompts."""
    print("\n[START] Testing fallback behavior...")

    try:
        # Test creating a new PromptManager instance with no templates
        import tempfile
        from pathlib import Path

        # Create a temporary directory without prompts
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a mock PromptManager with no templates directory
            from litassist.prompts import PromptManager

            # Create an instance that will have no templates
            class EmptyPromptManager(PromptManager):
                def __init__(self):
                    self.prompts_dir = temp_path / "nonexistent_prompts"
                    self.templates = self._load_templates()
                    self._templates_loaded = bool(self.templates)

            empty_manager = EmptyPromptManager()

            # Test that it correctly fails with missing templates
            try:
                empty_manager.get("base.australian_law")
                print("[FAIL] Should have failed with missing templates")
                return False
            except KeyError as e:
                if "no templates loaded" in str(e):
                    print("[PASS] Correctly failed with KeyError for missing templates")
                else:
                    print(f"[FAIL] Wrong error message: {e}")
                    return False

        print("[PASS] Fallback behavior test passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Fallback test failed: {e}")
        return False


if __name__ == "__main__":
    print("[START] Testing LitAssist Phase 1 Prompt Centralization")
    print("=" * 50)

    success = True

    # Test the prompt management system
    if not test_prompt_system():
        success = False

    # Test fallback behavior
    if not test_fallback_behavior():
        success = False

    print("\n" + "=" * 50)
    if success:
        print(
            "[PASS] All tests passed! Phase 1 prompt centralization is working correctly."
        )
        sys.exit(0)
    else:
        print("[FAIL] Some tests failed. Please check the implementation.")
        sys.exit(1)
