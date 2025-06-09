"""Basic unit tests to verify test infrastructure is working."""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner


class TestBasicFunctionality:
    """Test basic functionality."""

    def test_simple_assert(self):
        """Test basic assertion."""
        assert 1 + 1 == 2

    def test_mock_usage(self):
        """Test that mocks work."""
        mock_obj = Mock(return_value=42)
        assert mock_obj() == 42

    def test_click_runner(self):
        """Test click runner works."""
        runner = CliRunner()
        assert runner is not None

    def test_pytest_raises(self):
        """Test pytest raises works."""
        with pytest.raises(ValueError):
            raise ValueError("Test error")

    @patch("os.path.exists")
    def test_patch_decorator(self, mock_exists):
        """Test patch decorator works."""
        mock_exists.return_value = True
        import os

        assert os.path.exists("fake_file.txt") is True
        mock_exists.assert_called_once_with("fake_file.txt")


class TestMockConfig:
    """Test mocked config."""

    def test_config_is_mocked(self):
        """Test that CONFIG is properly mocked."""
        from litassist.config import CONFIG

        assert CONFIG is not None
        assert CONFIG.openai_api_key == "test-openai-key"
        assert CONFIG.get_openai_api_key() == "test-openai-key"


class TestModuleImports:
    """Test that modules can be imported."""

    def test_import_utils(self):
        """Test utils module imports."""
        from litassist import utils

        assert utils is not None

    def test_import_llm(self):
        """Test llm module imports."""
        from litassist import llm

        assert llm is not None

    def test_import_retriever(self):
        """Test retriever module imports."""
        from litassist.helpers import retriever

        assert retriever is not None

    def test_import_commands(self):
        """Test commands module imports."""
        from litassist import commands

        assert commands is not None
