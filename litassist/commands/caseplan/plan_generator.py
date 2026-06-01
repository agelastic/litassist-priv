"""
Full plan generation workflow for caseplan command.

Handles complete litigation plan generation using Claude Opus.
"""

import time
import click
from typing import Dict, Optional, Tuple

from litassist.logging import save_log, save_command_output, log_task_event
from litassist.llm.factory import LLMClientFactory
from litassist.utils.formatting import (
    saved_message,
    tip_message,
    success_message,
    warning_message,
)
from litassist.prompts import PROMPTS

from .command_extractor import extract_cli_commands

# Literal placeholder the model writes wherever a per-run id belongs (every
# --output prefix and every outputs/ glob filename). Replaced with one real id
# per generation so a producer filename and its downstream glob share the SAME
# prefix and match by construction - no token parsing needed.
RUN_ID_SENTINEL = "RUNID"


def generate_full_plan(
    facts_content: str,
    case_facts_name: str,
    context: str,
    budget: str,
    output: str
) -> Tuple[str, Optional[str], Dict]:
    """
    Generate full litigation plan and extract commands.

    Args:
        facts_content: Case facts content
        case_facts_name: Name of the case facts file
        context: Additional context (if provided)
        budget: Budget level (minimal/standard/comprehensive)
        output: Custom output prefix (if provided)

    Returns:
        Tuple of (output_file, commands_file, usage)

    Raises:
        click.ClickException: If LLM processing fails
    """
    click.echo("Analyzing case and generating litigation plan...")

    try:
        log_task_event(
            "caseplan",
            "plan",
            "start",
            f"Starting full plan generation - budget: {budget}"
        )
    except Exception:
        pass

    llm_client = LLMClientFactory.for_command("caseplan")

    system_prompt = PROMPTS.get("commands.caseplan.system").format(
        litassist_capabilities=PROMPTS.get("capabilities.litassist_capabilities")
    )

    # Build the main user prompt
    prompt_parts = [
        f"CASE FACTS:\n{facts_content}",
        f"BUDGET LEVEL: {budget}",
    ]
    if context:
        prompt_parts.append(
            f"USER ANALYSIS GUIDANCE (NOT case facts): {context}\n"
            f"IMPORTANT: This is guidance for your analysis, not factual information from the case."
        )

    # Select appropriate analysis instructions based on budget level
    analysis_prompt_key = f"commands.caseplan.analysis_instructions_{budget}"
    prompt_parts.append(PROMPTS.get(analysis_prompt_key))
    user_prompt = "\n\n".join(prompt_parts)

    def _generate_plan():
        """Execute plan generation LLM call (timed by the caseplan command)."""
        try:
            log_task_event(
                "caseplan",
                "plan",
                "llm_call",
                "Sending plan generation prompt to LLM",
                {"model": llm_client.model, "budget": budget}
            )
        except Exception:
            pass

        result = llm_client.complete(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )

        try:
            log_task_event(
                "caseplan",
                "plan",
                "llm_response",
                "Plan generation LLM response received",
                {"model": llm_client.model}
            )
        except Exception:
            pass

        return result

    try:
        plan_content, usage = _generate_plan()
    except Exception as e:
        raise click.ClickException(f"Plan generation error: {e}")

    # Group this run's outputs by substituting the RUNID sentinel with one real
    # id (seconds precision: caseplan is a single heavyweight invocation, so a
    # same-second collision across two runs is not a real scenario). Done before
    # the plan is saved and before command extraction so both carry the id. The
    # sentinel is always written as the prefix token "RUNID_<name>", so replacing
    # "RUNID_" (not bare "RUNID") avoids mutating any stray RUNID echoed from the
    # case facts or prose.
    sentinel_token = RUN_ID_SENTINEL + "_"
    run_id = "run" + time.strftime("%Y%m%d%H%M%S")
    if sentinel_token in plan_content:
        plan_content = plan_content.replace(sentinel_token, run_id + "_")
    else:
        run_id = None
        click.echo(
            warning_message(
                f"Plan did not mark any outputs with {sentinel_token}; this run's "
                "files are not grouped and cross-run globs may collide."
            )
        )

    metadata = {"Case Facts File": case_facts_name, "Budget Level": budget}
    if context:
        metadata["Context"] = context
    if run_id:
        metadata["Run ID"] = run_id

    output_file = save_command_output(
        f"{output}_plan" if output else "caseplan",
        plan_content,
        "" if output else case_facts_name,
        metadata=metadata,
    )

    # Extract and validate CLI commands. Each accepted command is round-tripped
    # through shlex so shell metacharacters in the LLM output cannot run as live
    # operators in the saved script (see command_extractor).
    extracted_commands, command_count, rejected_commands = extract_cli_commands(
        plan_content
    )
    try:
        log_task_event(
            "caseplan",
            "plan",
            "commands_extracted",
            f"Extracted {command_count} CLI commands; {len(rejected_commands)} rejected",
        )
    except Exception:
        pass

    # Partial run-id compliance: the sentinel was present (run_id set) but the
    # model may have stamped only SOME outputs. Count output references in the
    # extracted script against those carrying the run prefix; a shortfall means
    # some steps stayed ungrouped and could match files from another run. Cheap
    # substring counts (no tokenising) - warning only, never mutates the script.
    #
    # This closes the only SILENT failure mode: a bare consumer glob
    # ('outputs/brainstorm_*.txt') that over-matches a prior run's files. The
    # other mismatch - a STAMPED glob whose producer was left unstamped - is not
    # silent: 'outputs/run<id>_x_*.txt' matches this run's files or nothing, and
    # the glob callbacks raise BadParameter on a zero match (file_ops.py), i.e. a
    # loud runtime error rather than a wrong result.
    if run_id:
        total_refs = extracted_commands.count("--output ") + extracted_commands.count(
            "outputs/"
        )
        grouped_refs = extracted_commands.count(
            f"--output {run_id}_"
        ) + extracted_commands.count(f"outputs/{run_id}_")
        ungrouped = total_refs - grouped_refs
        if ungrouped > 0:
            click.echo(
                warning_message(
                    f"{ungrouped} output reference(s) in the generated script do not "
                    f"carry the run id {run_id} (the model skipped the {sentinel_token} "
                    "marker there); those steps may match files from other runs. "
                    "Review the saved commands before running."
                )
            )

    commands_file = None
    if command_count == 0:
        # Fail loud rather than save a header-only script the user is told to run.
        click.echo(
            warning_message(
                "No executable commands could be extracted from the plan. "
                "Review the saved plan and run the workflow steps manually."
            )
        )
    else:
        commands_file = save_command_output(
            f"{output}_commands" if output else f"caseplan_commands_{budget}",
            extracted_commands,
            "" if output else case_facts_name,
            metadata={"Type": "Executable Commands", "Budget": budget},
        )
        if rejected_commands:
            click.echo(
                warning_message(
                    f"{len(rejected_commands)} line(s) in command blocks were not "
                    "runnable litassist commands and were excluded from the script "
                    "(review them):"
                )
            )
            for rejected in rejected_commands:
                click.echo(f"  - {rejected}")

    save_log(
        "caseplan",
        {
            "inputs": {"case_facts": facts_content},
            "params": {
                "model": llm_client.model,
                "context": context,
                "budget": budget,
            },
            "usage": usage,
            # Response content removed - already logged by LLMClient separately
            "output_file": output_file,
            "commands_file": commands_file,
            "rejected_commands": rejected_commands,
        },
    )

    click.echo(f"\n{success_message('Litigation plan generated successfully!')}")
    click.echo(saved_message(f'Plan saved to: "{output_file}"'))
    if commands_file:
        click.echo(saved_message(f'Executable commands saved to: "{commands_file}"'))
        msg = tip_message(f'Execute commands: bash "{commands_file}"')
        click.echo(f"\n{msg}")

    try:
        log_task_event(
            "caseplan",
            "plan",
            "end",
            f"Full plan generation complete - budget: {budget}"
        )
    except Exception:
        pass

    return output_file, commands_file, usage
