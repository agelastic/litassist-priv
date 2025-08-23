"""Test that Selenium is installed as a required dependency."""

import pytest


class TestSeleniumRequired:
    """Test that Selenium is properly installed."""
    
    def test_selenium_import(self):
        """Test that Selenium can be imported."""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.chrome.options import Options
        except ImportError as e:
            pytest.fail(
                f"Selenium is required but not installed. Install with: pip install selenium\n"
                f"Error: {e}"
            )
    
    def test_selenium_in_lookup(self):
        """Test that lookup.py has Selenium available."""
        from litassist.commands.lookup import SELENIUM_AVAILABLE
        
        assert SELENIUM_AVAILABLE, (
            "Selenium is not available in lookup.py. "
            "This is now a required dependency. "
            "Install with: pip install selenium"
        )
    
    def test_selenium_version(self):
        """Test that Selenium version is adequate."""
        import selenium
        from packaging import version
        
        selenium_version = version.parse(selenium.__version__)
        minimum_version = version.parse("4.0.0")
        
        assert selenium_version >= minimum_version, (
            f"Selenium version {selenium.__version__} is too old. "
            f"Minimum required version is 4.0.0. "
            f"Upgrade with: pip install --upgrade selenium"
        )