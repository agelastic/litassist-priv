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

# OpenRouter routes some models only via user-supplied provider keys
# (BYOK). OpenRouter does not expose this status programmatically -- it
# is published on per-model pages, not in `/api/v1/models` or
# `/api/v1/models/{id}/endpoints` (verified 29/05/2026: no `byok` field
# in either response). Maintain this set by hand; add an entry only
# after confirming on the model's OpenRouter page. Removing an entry is
# cheap (the reminder just stops printing). Each entry below has a
# one-line rationale per CLAUDE.md's constant-rationale rule.
BYOK_REQUIRED_MODELS = {
    # openai/o3-pro: BYOK-required per https://openrouter.ai/openai/o3-pro
    # (model page lists "Bring your own key" as the only access path).
    "openai/o3-pro",
}

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

    This function attempts to validate credentials for OpenRouter and
    Google CSE by making test API calls. Invalid credentials will result
    in an early exit.
    """
    config = load_config()
    placeholder_checks = config.using_placeholders()

    if show_progress:
        print("Verifying API connections...")

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
            # /models is unauthenticated catalogue lookup -- doesn't cost
            # credits or prove the key works. /key requires the bearer
            # token, so a 200 here proves the key authenticates. The
            # response body returns rate-limit + label metadata only; it
            # does NOT surface BYOK provider status (OpenRouter exposes
            # BYOK requirements only on per-model pages, not via the
            # API). Honour the configured `or_base` so users pointing
            # at a proxy/mirror don't silently validate against the
            # public endpoint instead.
            base = (config.or_base or "https://openrouter.ai/api/v1").rstrip("/")

            # 1. Auth check. /key is the current canonical endpoint per
            # OpenRouter's API reference; the legacy /auth/key alias
            # still resolves but /key is what current docs publish.
            key_resp = requests.get(
                f"{base}/key", headers=headers, timeout=10
            )
            if key_resp.status_code != 200:
                raise Exception(
                    f"Auth check failed: HTTP {key_resp.status_code}: {key_resp.text}"
                )

            # 2. Catalogue check -- confirm every model in model_configs.yaml
            # is currently visible on OpenRouter so a refresh-deferred
            # deprecation doesn't surprise the user mid-command.
            response = requests.get(
                f"{base}/models", headers=headers, timeout=10
            )
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            models = response.json().get("data", [])
            model_ids = {m.get("id", "") for m in models}

            from litassist.llm.factory import LLMClientFactory

            configurations = LLMClientFactory.list_configurations()
            configured_models = {
                cfg["model"]
                for cfg in configurations.values()
                if cfg.get("model")
            }
            missing = configured_models - model_ids
            if missing:
                raise Exception(
                    f"OpenRouter missing configured models: {sorted(missing)}"
                )

            # Group BYOK-required configured commands by model id so the
            # reminder lists each model once with the commands that route
            # to it. Built from `configurations` (already in hand) so no
            # extra YAML round-trip.
            configured_byok: dict[str, list[str]] = {}
            for cfg_key, cfg in configurations.items():
                model_name = cfg.get("model")
                if model_name in BYOK_REQUIRED_MODELS:
                    configured_byok.setdefault(model_name, []).append(
                        cfg_key
                    )

            if show_progress:
                print("OK (key authenticated; catalogue verified)")
                if configured_byok:
                    print("  - BYOK reminder:")
                    for byok_model, cmds in sorted(configured_byok.items()):
                        print(
                            f"      {byok_model} is configured for "
                            f"{', '.join(sorted(cmds))}."
                        )
                    print(
                        "      OpenRouter does not expose BYOK status "
                        "programmatically; verify provider key(s) at "
                        "https://openrouter.ai/settings/integrations."
                    )
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

    # NOTE: no Jina Reader probe here by design. Jina is a fallback
    # transport in lookup/fetchers.py, only exercised on Cloudflare
    # challenges, SPA shells, or non-HTML payloads. Free-tier
    # r.jina.ai has tight rate limits and routinely timed out at the
    # 10-second probe budget, producing false-negative FAILED lines
    # that taught users to ignore the test command. Health of the
    # Jina fallback surfaces on the first `lookup` that hits a
    # Cloudflare challenge. Do not re-add the probe.

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

    This command validates credentials for OpenRouter and Google CSE
    by making test API calls and reports success or failure. It also tests
    web scraping functionality (direct HTTP fetching and PDF retrieval),
    and prints a BYOK reminder for configured models that require a
    user-supplied provider key at OpenRouter.
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
