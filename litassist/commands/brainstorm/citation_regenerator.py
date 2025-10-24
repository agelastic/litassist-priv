"""
Citation regeneration utilities for brainstorm command.

Handles selective regeneration of strategies with citation issues.
"""

import re
import click

from litassist.llm.client import LLMClient
from litassist.utils.formatting import (
    info_message,
    warning_message,
    success_message,
    stats_message,
)
from litassist.prompts import PROMPTS


def regenerate_bad_strategies(
    client: LLMClient,
    original_content: str,
    base_prompt: str,
    strategy_type: str,
    max_retries: int = 2,
) -> str:
    """
    Selectively regenerate only strategies with citation issues.

    Args:
        client: LLMClient instance to use for regeneration
        original_content: Original strategy content with potential citation issues
        base_prompt: Base prompt used for generation
        strategy_type: Type of strategies ("orthodox" or "unorthodox") for logging
        max_retries: Maximum regeneration attempts

    Returns:
        Clean content with verified strategies only
    """
    click.echo(
        info_message(f"Analyzing {strategy_type} strategies for citation issues...")
    )

    # Split content into individual strategies using a robust regex
    # This pattern finds all numbered list items (e.g., "1. Strategy Title...")
    # and treats each one as a separate strategy.
    # Remove any section headers before processing
    original_content = re.sub(
        r"##\s+\w+\s+STRATEGIES\s*\n+", "", original_content.strip()
    )
    strategies = re.split(r"\n(?=\d+\.\s+)", original_content.strip())
    # The first item might be a header, so filter it out if it doesn't start with a number
    strategies = [s.strip() for s in strategies if re.match(r"^\d+\.", s.strip())]

    # Validate each strategy individually and track their final state
    strategy_results = {}  # Maps original position to final strategy content
    strategies_to_regenerate = []

    for i, strategy in enumerate(strategies, 1):
        if not strategy.strip():
            continue

        citation_issues = client.validate_citations(strategy)
        if citation_issues:
            click.echo(
                warning_message(
                    f"Strategy {i}: Found {len(citation_issues) - 1} citation issues"
                )
            )
            strategies_to_regenerate.append((i, strategy))
        else:
            click.echo(success_message(f"Strategy {i}: Citations verified"))
            strategy_results[i] = strategy

    # Regenerate problematic strategies
    for retry_attempt in range(max_retries):
        if not strategies_to_regenerate:
            break

        click.echo(
            info_message(
                f"Regeneration attempt {retry_attempt + 1}: {len(strategies_to_regenerate)} strategies need fixing"
            )
        )

        remaining_to_regenerate = []

        for strategy_num, bad_strategy in strategies_to_regenerate:
            # Create focused regeneration prompt
            # Use centralized regeneration prompt template
            # Build regeneration prompt from template
            regen_content = PROMPTS.get(
                "strategies.brainstorm.regeneration_template"
            ).format(base_prompt=base_prompt)

            regen_prompt = PROMPTS.get(
                "strategies.brainstorm.regeneration_format"
            ).format(content=regen_content, strategy_num=strategy_num)

            try:
                # Generate single replacement strategy
                new_strategy, _ = client.complete(
                    [{"role": "user", "content": regen_prompt}]
                )

                # Validate the regenerated strategy
                new_citation_issues = client.validate_citations(new_strategy)
                if new_citation_issues:
                    click.echo(
                        warning_message(
                            f"    Strategy {strategy_num}: Still has citation issues after regeneration"
                        )
                    )
                    remaining_to_regenerate.append((strategy_num, bad_strategy))
                else:
                    click.echo(
                        success_message(
                            f"    Strategy {strategy_num}: Successfully regenerated with clean citations"
                        )
                    )
                    # Strip any headers from the regenerated strategy
                    new_strategy = re.sub(
                        r"##\s+\w+\s+STRATEGIES\s*\n+", "", new_strategy.strip()
                    )
                    strategy_results[strategy_num] = new_strategy

            except Exception as e:
                click.echo(
                    f"    [FAILED] Strategy {strategy_num}: Regeneration failed - {str(e)}"
                )
                remaining_to_regenerate.append((strategy_num, bad_strategy))

        strategies_to_regenerate = remaining_to_regenerate

    # Report final status
    if strategies_to_regenerate:
        click.echo(
            warning_message(
                f"  {len(strategies_to_regenerate)} {strategy_type} strategies still have citation issues after {max_retries} attempts"
            )
        )
        click.echo(
            info_message(
                f"    Excluding these strategies: {[num for num, _ in strategies_to_regenerate]}"
            )
        )
    else:
        click.echo(
            success_message(
                f"  All {strategy_type} strategies now have verified citations"
            )
        )

    click.echo(
        stats_message(
            f"  Final result: {len(strategy_results)} verified {strategy_type} strategies"
        )
    )

    # Reconstruct content with final verified strategies only
    if strategy_results:
        # Get strategies in their final positions and renumber sequentially
        renumbered_strategies = []
        for i, (original_pos, strategy) in enumerate(
            sorted(strategy_results.items()), 1
        ):
            # Replace the original numbering with sequential numbering
            strategy_lines = strategy.split("\n")
            if strategy_lines and re.match(r"^\d+\.\s+", strategy_lines[0].strip()):
                # Replace first line numbering
                strategy_lines[0] = re.sub(r"^\d+\.", f"{i}.", strategy_lines[0])
                renumbered_strategies.append("\n".join(strategy_lines))
            else:
                renumbered_strategies.append(strategy)

        # Add the appropriate header back
        header = (
            "## ORTHODOX STRATEGIES"
            if strategy_type == "orthodox"
            else "## UNORTHODOX STRATEGIES"
        )
        return f"{header}\n\n" + "\n\n".join(renumbered_strategies)
    else:
        return (
            f"No {strategy_type} strategies could be generated with verified citations."
        )
