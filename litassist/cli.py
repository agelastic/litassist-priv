"""
Main CLI entry point for LitAssist.

This module defines the main CLI group and global options, registers all commands,
and serves as the entry point for the LitAssist application.
"""

import sys
import click
import logging
import openai
import pinecone

from litassist.config import load_config
from litassist.commands import register_commands

# Load configuration early so that CONFIG is populated before other modules
CONFIG = load_config()


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
    # Ensure context object exists
    ctx.ensure_object(dict)
    config = load_config()
    # Use config.yaml value if no CLI option provided
    if log_format is None:
        log_format = config.log_format
    # Store the chosen log format for downstream use
    ctx.obj["log_format"] = log_format
    # Configure logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.debug(
        f"Log format set to: {log_format} (from {'CLI' if ctx.params.get('log_format') else 'config.yaml'})"
    )


def validate_credentials(show_progress=True):
    """
    Test API connections with provided credentials.

    This function attempts to validate credentials for OpenAI, Pinecone, and Google CSE
    by making test API calls. Invalid credentials will result in an early exit.
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
            openai.Model.list()
            if show_progress:
                print("OK")
        except Exception as e:
            if show_progress:
                print("FAILED")
            sys.exit(f"Error: OpenAI API test failed: {e}")
    else:
        if show_progress:
            print("  - Skipping OpenAI connectivity test (placeholder credentials)")

    # Test Pinecone connectivity (only if not using placeholders)
    if not placeholder_checks["pinecone"]:
        try:
            if show_progress:
                print("  - Testing Pinecone API... ", end="", flush=True)
            # Initialize Pinecone before testing
            pinecone.init(api_key=config.pc_key, environment=config.pc_env)
            _ = pinecone.list_indexes()
            if show_progress:
                print("OK")
        except Exception as e:
            if show_progress:
                print("FAILED")
            sys.exit(f"Error: Pinecone API test failed: {e}")
    else:
        if show_progress:
            print("  - Skipping Pinecone connectivity test (placeholder credentials)")

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
            # Use the models endpoint which doesn't cost credits
            response = requests.get(
                "https://openrouter.ai/api/v1/models", headers=headers, timeout=10
            )
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.text}")

            # Verify at least one required model is available
            models = response.json().get("data", [])
            model_ids = [m.get("id", "") for m in models]
            required_models = [
                "anthropic/claude-sonnet-4",
                "x-ai/grok-3",
                "google/gemini-2.5-pro-preview",
            ]

            if not any(model in model_ids for model in required_models):
                raise Exception(
                    f"No required models found. Available: {len(model_ids)} models"
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


@cli.command()
def test():
    """
    Test API connectivity.

    This command validates credentials for OpenAI, OpenRouter, Pinecone, and Google CSE
    by making test API calls and reports success or failure. For OpenRouter, it also
    verifies that at least one of the required models is available.
    """
    validate_credentials(show_progress=True)


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
