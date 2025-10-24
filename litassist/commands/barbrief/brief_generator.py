"""
Brief generation and verification for barbrief command.

Handles LLM generation of barrister's brief and optional citation verification.
"""

import click
from typing import Dict, Tuple, Optional

from litassist.prompts import PROMPTS
from litassist.utils.legal_reasoning import create_reasoning_prompt
from litassist.logging import save_command_output, log_task_event
from litassist.citation.verify import verify_all_citations


def generate_brief(
    client,
    sections: Dict,
    total_tokens: int
) -> Tuple[str, Dict]:
    """
    Generate barrister's brief using LLM.

    Args:
        client: LLM client instance
        sections: Prepared sections dictionary
        total_tokens: Estimated total input tokens (for error messages)

    Returns:
        Tuple of (content, usage)

    Raises:
        click.ClickException: If LLM generation fails
    """
    # Create reasoning-enabled prompt
    try:
        base_prompt = PROMPTS.get("barbrief.main", **sections)
        prompt_with_reasoning = create_reasoning_prompt(base_prompt, "barbrief")
    except Exception as e:
        raise click.ClickException(f"Failed to prepare prompt: {e}")

    # Generate the brief
    click.echo("\nGenerating barrister's brief...")

    try:
        log_task_event(
            "barbrief",
            "generation",
            "start",
            "Starting brief generation",
            {"model": client.model}
        )
    except Exception:
        pass

    messages = [
        {"role": "system", "content": PROMPTS.get("barbrief.system")},
        {"role": "user", "content": prompt_with_reasoning},
    ]

    try:
        # Log LLM call
        try:
            log_task_event(
                "barbrief",
                "generation",
                "llm_call",
                "Sending brief generation prompt to LLM",
                {"model": client.model}
            )
        except Exception:
            pass

        content, usage = client.complete(messages)

        # Log LLM response
        try:
            log_task_event(
                "barbrief",
                "generation",
                "llm_response",
                "Brief LLM response received",
                {"model": client.model}
            )
        except Exception:
            pass
    except Exception as e:
        # Provide helpful error message for common issues
        if "timeout" in str(e).lower():
            raise click.ClickException(
                "Request timed out. The brief may be too large for a single request. "
                "Try reducing the number of input documents."
            )
        elif "rate limit" in str(e).lower():
            raise click.ClickException(
                "Rate limit exceeded. Please wait a moment and try again."
            )
        elif "api key" in str(e).lower():
            raise click.ClickException(
                "API key error. Please check your OpenAI/OpenRouter configuration."
            )
        elif "error occurred while processing" in str(e).lower():
            raise click.ClickException(
                f"API processing error (input was {total_tokens:,} tokens). "
                f"Try with fewer documents. Error: {e}"
            )
        else:
            raise click.ClickException(f"LLM API error: {e}")

    click.echo(f"\nGenerated brief ({usage.get('total_tokens', 'N/A')} tokens used)")

    try:
        log_task_event(
            "barbrief",
            "generation",
            "end",
            "Brief generation complete",
            {"model": client.model}
        )
    except Exception:
        pass

    return content, usage


def verify_citations_if_requested(
    content: str,
    verify: bool
) -> Optional[str]:
    """
    Run manual citation verification if requested.

    Note: Automatic verification already happens during generation via client.complete()
    This provides additional detailed reporting when --verify flag is used.

    Args:
        content: Generated brief content
        verify: Whether to verify citations

    Returns:
        Optional verification file path if verification was run and issues found
    """
    if not verify:
        return None

    try:
        log_task_event(
            "barbrief",
            "verification",
            "start",
            "Starting citation verification"
        )
    except Exception:
        pass

    click.echo("\nVerifying citations...")
    verified, unverified = verify_all_citations(content)

    verify_file = None
    if unverified:
        click.echo(f"Warning: {len(unverified)} citations could not be verified")
        # Save verification report
        verification_content = (
            f"CITATION VERIFICATION REPORT\n\n"
            f"Valid Citations: {len(verified)}\n"
            f"Invalid Citations: {len(unverified)}\n\n"
        )
        verification_content += "INVALID CITATIONS:\n"
        for cit, reason in unverified:
            verification_content += f"- {cit}: {reason}\n"

        verify_file = save_command_output(
            "barbrief", verification_content, "citation_verification"
        )
        click.echo(f"Verification report saved: {verify_file}")

    try:
        log_task_event(
            "barbrief",
            "verification",
            "end",
            "Citation verification complete"
        )
    except Exception:
        pass

    return verify_file
