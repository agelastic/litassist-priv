"""
Main CLI entry point for LitAssist.

This module defines the main CLI group and global options, registers all commands,
and serves as the entry point for the LitAssist application.
"""

import sys
import click
import logging

from litassist.config import load_config
from litassist.commands import register_commands

# Config is loaded lazily inside command handlers (see `cli` below) so that
# `--help`, command discovery and tab-completion still work when the user has
# not yet created or has broken their config.yaml. Eager loading here used to
# crash the entire CLI before Click could render help.


@click.group()
@click.option(
    "--log-format",
    type=click.Choice(["json", "markdown"]),
    default=None,  # Will use config.yaml value if not specified
    help="Format for audit logs (overrides config.yaml setting).",
)
@click.option(
    "--verbose", is_flag=True, default=False, help="Enable debug-level logging."
)
@click.pass_context
def cli(ctx, log_format, verbose):
    """
    LitAssist: automated litigation support workflows for Australian legal practice.

    This is the main entry point for the CLI application, handling global options
    and command selection. The tool provides multiple commands for different legal
    workflows including case-law lookup, document analysis, creative legal ideation,
    fact extraction, and citation-rich drafting.

    Global options:
    \b
    --log-format    Choose log output format (json or markdown).
    --verbose       Enable debug logging and detailed output.
    """
    # Set up logging first
    from litassist.logging import setup_logging

    log_file = setup_logging(verbose=verbose)

    # Ensure context object exists and store logging info
    ctx.ensure_object(dict)
    ctx.obj["log_file"] = log_file
    ctx.obj["verbose"] = verbose

    # Show log file location if verbose
    if verbose:
        click.echo(f"[INFO] Logging to: {log_file}")

    # Load config after logging is set up
    config = load_config()

    # Use config.yaml value if no CLI option provided
    if log_format is None:
        log_format = config.log_format
    # Store the chosen log format for downstream use
    ctx.obj["log_format"] = log_format

    logging.debug(
        f"Log format set to: {log_format} (from {'CLI' if ctx.params.get('log_format') else 'config.yaml'})"
    )


def validate_credentials(show_progress=True):
    """
    Test API connections with provided credentials.

    This function attempts to validate credentials for OpenAI, OpenRouter,
    and Google CSE by making test API calls. Invalid credentials will result
    in an early exit.
    """
    config = load_config()
    placeholder_checks = config.using_placeholders()

    if show_progress:
        print("Verifying API connections...")

    # Test OpenAI connectivity (only if not using placeholders)
    if not placeholder_checks["openai"]:
        try:
            if show_progress:
                print("  - Testing OpenAI API... ", end="", flush=True)
            # Lazy import OpenAI only when needed
            from openai import OpenAI
            # Use the new OpenAI v1.0+ API
            client = OpenAI(api_key=config.oa_key)
            # List models to test the connection
            client.models.list()
            if show_progress:
                print("OK")
        except Exception as e:
            if show_progress:
                print("FAILED")
            sys.exit(f"Error: OpenAI API test failed: {e}")
    else:
        if show_progress:
            print("  - Skipping OpenAI connectivity test (placeholder credentials)")

    # Test Google CSE connectivity (only if not using placeholder values)
    if not placeholder_checks["google_cse"]:
        try:
            if show_progress:
                print("  - Testing Google CSE API... ", end="", flush=True)
            import warnings

            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*file_cache.*")
                from googleapiclient.discovery import build
            # Disable cache to avoid warning
            service = build(
                "customsearch", "v1", developerKey=config.g_key, cache_discovery=False
            )
            # Perform a lightweight test query (no logging)
            service.cse().list(q="test", cx=config.cse_id, num=1).execute()
            if show_progress:
                print("OK")
        except Exception as e:
            if show_progress:
                print("FAILED")
            sys.exit(f"Error: Google CSE API test failed: {e}")
    else:
        if show_progress:
            print("  - Skipping Google CSE connectivity test (placeholder credentials)")

    # Test OpenRouter connectivity (only if not using placeholders)
    if not placeholder_checks.get("openrouter", False):
        try:
            if show_progress:
                print("  - Testing OpenRouter API... ", end="", flush=True)
            # Test OpenRouter by making a minimal API call
            import requests

            headers = {
                "Authorization": f"Bearer {config.or_key}",
                "Content-Type": "application/json",
            }
            # Use the models endpoint which doesn't cost credits. Honour the
            # configured `or_base` so users pointing at a proxy/mirror don't
            # silently validate against the public endpoint instead.
            base = (config.or_base or "https://openrouter.ai/api/v1").rstrip("/")
            response = requests.get(
                f"{base}/models", headers=headers, timeout=10
            )
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            # Verify configured models are available
            models = response.json().get("data", [])
            model_ids = {m.get("id", "") for m in models}

            from litassist.llm.factory import LLMClientFactory

            configured_models = {
                cfg["model"]
                for cfg in LLMClientFactory.list_configurations().values()
                if cfg.get("model")
            }
            missing = configured_models - model_ids
            if missing:
                raise Exception(
                    f"OpenRouter missing configured models: {sorted(missing)}"
                )

            if show_progress:
                print("OK")
        except Exception as e:
            if show_progress:
                print("FAILED")
            sys.exit(f"Error: OpenRouter API test failed: {e}")
    else:
        if show_progress:
            print("  - Skipping OpenRouter connectivity test (placeholder credentials)")

    # Jade API direct validation removed - now uses public endpoints

    if show_progress:
        print("All API connections verified.\n")


def test_scraping_capabilities():
    """Test web scraping functionality."""
    print("Verifying web scraping capabilities...")

    # Import utilities for colored output
    from litassist.utils.formatting import error_message

    # Test plain HTTP scraping
    print("  - Testing plain HTTP scraping... ", end="", flush=True)
    try:
        from litassist.commands.lookup.fetchers import (
            PendingOcrContent,
            _fetch_url_content,
        )

        # Test with a reliable static HTML page
        test_url = "https://webscraper.io/test-sites"  # Dedicated scraping test site
        content = _fetch_url_content(test_url, timeout=5)
        if isinstance(content, PendingOcrContent):
            content = content.future.result(timeout=5)

        if content and len(content) > 1000:  # webscraper.io has substantial content
            print(f"OK (fetched {len(content)} chars)")
        else:
            print("FAILED")
            print(f"    {error_message('Could not fetch sufficient content')}")
    except Exception as e:
        print("FAILED")
        print(f"    {error_message(f'HTTP scraping error: {e}')}")

    # Test Jina Reader API
    print("  - Testing Jina Reader API... ", end="", flush=True)
    try:
        from litassist.commands.lookup.fetchers import _fetch_via_jina
        
        # Test with a reliable site
        test_url = "https://www.austlii.edu.au/au/cases/cth/HCA/2020/45.html"
        content = _fetch_via_jina(test_url, timeout=10)
        
        if content and len(content) > 5000:
            # Check for markdown formatting
            has_markdown = '#' in content or '**' in content or '[' in content
            if has_markdown:
                print(f"OK (fetched {len(content)} chars with markdown)")
            else:
                print(f"OK (fetched {len(content)} chars)")
        else:
            print("FAILED")
            print(f"    {error_message('Jina Reader could not fetch content')}")
    except Exception as e:
        logging.error(f"Jina Reader error: {e}")
        print("FAILED")
        print(f"    {error_message(f'Jina Reader error: {str(e)[:100]}')}")

    # Test PDF fetching
    print("  - Testing PDF fetching... ", end="", flush=True)
    try:
        import requests
        
        # Test with a small PDF URL
        test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        
        # Test HEAD request to detect PDF
        head_response = requests.head(test_url, timeout=5, allow_redirects=True)
        content_type = head_response.headers.get("content-type", "").lower()
        
        if "application/pdf" in content_type:
            # Test actual PDF download
            response = requests.get(test_url, timeout=10)
            if response.status_code == 200 and len(response.content) > 100:
                print(f"OK (fetched {len(response.content)} bytes)")
            else:
                print("FAILED")
                print(f"    {error_message('Could not download PDF')}")
        else:
            print("FAILED")
            print(f"    {error_message('PDF detection failed')}")
    except Exception as e:
        logging.error(f"PDF fetching error: {e}")
        print("FAILED")
        print(f"    {error_message(f'PDF fetching error: {str(e)[:100]}')}")

    print("\nAll scraping tests completed.")


@cli.command()
def test():
    """
    Test API connectivity and web scraping capabilities.

    This command validates credentials for OpenAI, OpenRouter, and Google CSE
    by making test API calls and reports success or failure. It also tests web scraping
    functionality including Jina Reader and PDF fetching.
    """
    validate_credentials(show_progress=True)
    test_scraping_capabilities()


def main():
    """
    Main entry point function for the LitAssist CLI application.

    This function registers all commands with the CLI and invokes the CLI group.
    """
    # Register all commands
    register_commands(cli)

    # Launch the CLI
    cli(obj={})


if __name__ == "__main__":
    main()
