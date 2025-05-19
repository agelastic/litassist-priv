"""
LitAssist commands package.

This package contains the implementation of all CLI commands
available in the LitAssist tool.
"""

from typing import List
import click

# Import all command modules to make them available
from litassist.commands import lookup, digest, brainstorm, extractfacts, draft, strategy


def register_commands(cli: click.Group) -> None:
    """
    Register all command modules with the CLI group.

    Args:
        cli: The Click command group to register commands with.
    """
    cli.add_command(lookup.lookup)
    cli.add_command(digest.digest)
    cli.add_command(brainstorm.brainstorm)
    cli.add_command(extractfacts.extractfacts)
    cli.add_command(draft.draft)
    cli.add_command(strategy.strategy)
