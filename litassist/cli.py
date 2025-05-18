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

from litassist.config import CONFIG
from litassist.commands import register_commands


@click.group()
@click.option(
    "--log-format",
    type=click.Choice(["json", "markdown"]),
    default="markdown",
    show_default=True,
    help="Format for audit logs.",
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
    # Store the chosen log format for downstream use
    ctx.obj["log_format"] = log_format
    # Configure logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.debug(f"Log format set to: {log_format}")


def validate_credentials():
    """
    Test API connections with provided credentials.

    This function attempts to validate credentials for OpenAI, Pinecone, and Google CSE
    by making test API calls. Invalid credentials will result in an early exit.
    """
    placeholder_checks = CONFIG.using_placeholders()

    # Test OpenAI connectivity (only if not using placeholders)
    if not placeholder_checks["openai"]:
        try:
            openai.Model.list()
        except Exception as e:
            sys.exit(f"Error: OpenAI API test failed: {e}")
    else:
        print("Skipping OpenAI connectivity test due to placeholder credentials")

    # Test Pinecone connectivity (only if not using placeholders)
    if not placeholder_checks["pinecone"]:
        try:
            # Initialize Pinecone before testing
            pinecone.init(api_key=CONFIG.pc_key, environment=CONFIG.pc_env)
            _ = pinecone.list_indexes()
        except Exception as e:
            sys.exit(f"Error: Pinecone API test failed: {e}")
    else:
        print("Skipping Pinecone connectivity test due to placeholder credentials")

    # Test Google CSE connectivity (only if not using placeholder values)
    if not placeholder_checks["google_cse"]:
        try:
            from googleapiclient.discovery import build

            service = build("customsearch", "v1", developerKey=CONFIG.g_key)
            # Perform a lightweight test query (no logging)
            service.cse().list(q="test", cx=CONFIG.cse_id, num=1).execute()
        except Exception as e:
            sys.exit(f"Error: Google CSE API test failed: {e}")
    else:
        print("Skipping Google CSE connectivity test due to placeholder credentials")


def main():
    """
    Main entry point function for the LitAssist CLI application.

    This function validates API credentials, registers all commands with the CLI,
    and then invokes the CLI group.
    """
    # Test API connections at startup
    validate_credentials()

    # Register all commands
    register_commands(cli)

    # Launch the CLI
    cli(obj={})


if __name__ == "__main__":
    main()
