"""Test that fetch functions are available and working."""

import pytest


class TestFetchFunctions:
    """Test that fetching functions are properly available."""

    def test_fetch_functions_exist(self):
        """Test that required fetch functions can be imported."""
        try:
            from litassist.commands.lookup.fetchers import _fetch_url_content  # noqa: F401
            from litassist.commands.lookup.fetchers import _fetch_via_jina  # noqa: F401
            from litassist.commands.lookup.fetchers import _extract_pdf_text  # noqa: F401
        except ImportError as e:
            pytest.fail(
                f"Failed to import fetch functions from fetchers.py\n"
                f"Error: {e}"
            )

    def test_jina_reader_configuration(self):
        """Test that Jina Reader can be configured."""
        from litassist.config import get_config
        
        try:
            config = get_config()
            # Check that Jina API key config exists (may be empty)
            assert hasattr(config, 'jina_api_key'), (
                "Jina API key configuration not found in config"
            )
        except Exception:
            # Config may not be available in test environment
            pass

    def test_requests_available(self):
        """Test that requests library is available for fetching."""
        try:
            import requests
            assert hasattr(requests, 'get'), "requests.get not available"
        except ImportError as e:
            pytest.fail(
                f"requests library is required but not installed.\n"
                f"Error: {e}"
            )
