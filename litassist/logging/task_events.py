"""
Structured event logging for multistage commands.

Provides consistent logging for command execution stages and progress tracking.
"""

import time
import click
from typing import Any, Dict, Optional


def log_task_event(
    command: str,
    stage: str,
    event: str,
    message: str = "",
    details: Optional[Dict[str, Any]] = None,
    save_log_fn=None,
):
    """
    Log structured events for multistage commands.

    This function provides consistent logging for command execution stages,
    making it easier to track progress and debug issues in complex workflows.

    Args:
        command: Command name (e.g., 'verify', 'verify-cove')
        stage: Stage name (e.g., 'citations', 'reasoning', 'soundness', 'cove-questions')
        event: Event type ('start', 'end', 'progress', 'llm_call', 'llm_response')
        message: Human-readable message describing the event
        details: Optional dictionary with additional structured data
        save_log_fn: Function to call for saving logs (injected to avoid circular import)

    Examples:
        log_task_event('verify', 'citations', 'start', 'Beginning citation verification')
        log_task_event('verify-cove', 'cove-questions', 'llm_call', 'Sending questions to LLM')
        log_task_event('verify', 'soundness', 'end', 'Soundness check completed', {'issues_found': 2})
    """
    # Create structured log payload
    payload = {
        "command": command,
        "stage": stage,
        "event": event,
        "message": message,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # Add details if provided
    if details:
        payload["details"] = details

    # Prepare model suffix for console messages when available
    model_suffix = ""
    try:
        if details and details.get("model"):
            model_suffix = f" [model: {details.get('model')}]"
    except Exception:
        # Be resilient to unexpected 'details' types
        model_suffix = ""

    # Use consistent tag format for easy filtering
    tag = f"task_event_{command}_{stage}_{event}"

    # Log using the provided save_log function
    if save_log_fn:
        save_log_fn(tag, payload)

    # Also log to console for immediate visibility during development/debugging
    # Show model suffix on ALL event types when available
    if event in ["start", "end"]:
        click.echo(f"[{event.upper()}] {command}.{stage}: {message}{model_suffix}")
    elif event == "llm_call":
        click.echo(f"[LLM CALL] {command}.{stage}: {message}{model_suffix}")
    elif event == "llm_response":
        click.echo(f"[LLM RESPONSE] {command}.{stage}: {message}{model_suffix}")
    elif event == "progress":
        click.echo(f"[PROGRESS] {command}.{stage}: {message}{model_suffix}")
