"""
Case-specific litigation workflow planning.

This module implements the 'caseplan' command which analyzes case facts
and generates a customized, efficient litigation workflow plan.
"""

import click
from litassist.logging_utils import save_log, save_command_output
from litassist.timing import timed
from litassist.utils.file_ops import validate_file_size_limit
from litassist.llm import LLMClientFactory
from litassist.utils.formatting import saved_message, tip_message, success_message, warning_message
from litassist.prompts import PROMPTS


def extract_cli_commands(plan_content):
    """
    Extract all CLI commands from the caseplan output.

    Returns a formatted string with commands and their phase context.
    """
    commands = [
        "#!/bin/bash",
        "# Extracted CLI commands from caseplan",
        "# Execute commands in order, reviewing output between phases",
        "",
    ]

    lines = plan_content.split("\n")
    lines_iter = iter(enumerate(lines))
    current_phase = "Initial Setup"

    for idx, line in lines_iter:
        stripped_line = line.strip()

        # Track current phase/section - handle various formats
        if "PHASE" in stripped_line.upper() and ":" in stripped_line:
            # Extract phase name after colon for better formatting
            phase_parts = stripped_line.split(":", 1)
            if len(phase_parts) > 1:
                # Clean up the phase number part and description
                phase_num = phase_parts[0].replace("#", "").strip()
                phase_desc = phase_parts[1].strip()
                current_phase = f"{phase_num}: {phase_desc}"
            else:
                current_phase = stripped_line.replace("#", "").strip()

        # Look for bash code blocks
        if stripped_line == "```bash":
            block_content = []
            current_command = []

            # Collect all lines within the code block
            for _, block_line in lines_iter:
                if block_line.strip() == "```":
                    # Save any pending command
                    if current_command:
                        block_content.append(" ".join(current_command))
                    break

                # Check if this line starts a new command or continues the previous one
                if block_line.strip().startswith("litassist"):
                    # Save previous command if exists
                    if current_command:
                        block_content.append(" ".join(current_command))
                    # Start new command
                    current_command = [block_line.rstrip()]
                elif current_command and (
                    block_line.startswith("  ")
                    or block_line.endswith("\\")
                    or block_line.strip().startswith("--")
                    or block_line.strip().startswith('"')
                ):
                    # This is a continuation of the current command
                    # Remove trailing backslash if present
                    cleaned_line = block_line.rstrip()
                    if cleaned_line.endswith("\\"):
                        cleaned_line = cleaned_line[:-1].rstrip()
                    current_command.append(cleaned_line.strip())

            # Add commands from this block
            if block_content:
                commands.append(f"\n# {current_phase}")
                commands.extend(block_content)

        # Fallback for commands not in a block
        elif stripped_line.startswith("litassist"):
            commands.append(f"\n# {current_phase}")
            # Check if this is a multi-line command
            full_command = [line.rstrip()]
            next_idx = idx + 1
            while next_idx < len(lines) and (
                lines[next_idx].startswith("  ")
                or lines[next_idx].rstrip().endswith("\\")
            ):
                cleaned_line = lines[next_idx].rstrip()
                if cleaned_line.endswith("\\"):
                    cleaned_line = cleaned_line[:-1].rstrip()
                full_command.append(cleaned_line.strip())
                next_idx += 1
            commands.append(" ".join(full_command))

    commands.extend(
        [
            "\n# End of extracted commands",
            "# Remember to update case_facts.txt after digest phases",
        ]
    )

    return "\n".join(commands)


@click.command()
@click.argument("case_facts", type=click.File("r"))
@click.option("--context", help="Additional context to guide the analysis")
@click.option(
    "--budget",
    type=click.Choice(["minimal", "standard", "comprehensive"]),
    default=None,
    help="Budget constraint level (if not specified, LLM will recommend)",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.option(
    "--verify",
    is_flag=True,
    help="Not supported - caseplan outputs are not verified. Use 'litassist verify' command for verification.",
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Not supported - caseplan has no internal verification.",
)
@timed
def caseplan(case_facts, context, budget, output, verify, noverify):
    """
    Generate customized litigation workflow plan based on case facts.

    If --budget is not specified, performs a rapid assessment using Claude Sonnet 4
    and outputs a short summary, budget recommendation, and justification.
    If --budget is specified, generates a full plan using Claude Opus 4.

    Args:
        case_facts: Path to case facts file (10-heading structure)

    Examples:
        litassist caseplan case_facts.txt
        litassist caseplan case_facts.txt --context "property dispute"
        litassist caseplan case_facts.txt --budget minimal
    """
    # Handle unsupported verification flags
    if verify:
        click.echo(
            warning_message(
                "--verify not supported: This command has no internal verification. Use 'litassist verify' for post-processing verification."
            )
        )
    if noverify:
        click.echo(
            warning_message(
                "--noverify not supported: This command has no verification to skip."
            )
        )

    facts_content = case_facts.read()
    validate_file_size_limit(facts_content, 50000, "Case facts")

    if budget is None:
        # Budget assessment mode (Sonnet)
        click.echo("Analyzing case to recommend appropriate budget level...")

        llm_client = LLMClientFactory.for_command("caseplan", "assessment")

        system_prompt = PROMPTS.get("commands.caseplan.budget_assessment_system")
        # Use base case facts template for budget assessment
        user_prompt = PROMPTS.get("analysis.base_case_facts_prompt").format(
            facts_content=facts_content
        )

        user_prompt += (
            f"\n\n{PROMPTS.get('commands.caseplan.budget_assessment_instructions')}"
        )

        @timed
        def assess_budget():
            return llm_client.complete(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )

        try:
            assessment, usage = assess_budget()
        except Exception as e:
            raise click.ClickException(f"Budget assessment error: {e}")

        output_file = save_command_output(
            f"{output}_assessment" if output else "caseplan-assessment",
            assessment,
            "" if output else case_facts.name,
            metadata={"Type": "Budget Assessment"},
        )

        save_log(
            "caseplan-assessment",
            {
                "inputs": {"case_facts": facts_content},
                "params": {"model": llm_client.model},
                "usage": usage,
                # Response content removed - already logged by LLMClient separately
                "output_file": output_file,
            },
        )

        click.echo("\n" + "=" * 60)
        click.echo("BUDGET RECOMMENDATION")
        click.echo("=" * 60)
        click.echo(assessment)
        click.echo("=" * 60)
        msg = saved_message(f'Recommendation saved to: "{output_file}"')
        click.echo(f"\n{msg}")
        click.echo(
            f"\n{tip_message('To generate full plan, run again with recommended budget:')}"
        )
        click.echo("   e.g., litassist caseplan case_facts.txt --budget standard")

    else:
        # Full plan mode (Opus)
        click.echo("Analyzing case and generating litigation plan...")

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
            prompt_parts.append(f"CONTEXT: {context}")

        # Select appropriate analysis instructions based on budget level
        analysis_prompt_key = f"commands.caseplan.analysis_instructions_{budget}"
        prompt_parts.append(PROMPTS.get(analysis_prompt_key))
        user_prompt = "\n\n".join(prompt_parts)

        # Add glob help section if available
        try:
            glob_help = PROMPTS.get("glob_help_section")
            user_prompt = f"{user_prompt}\n\n{glob_help}"
        except KeyError:
            pass  # Glob help addon not available

        @timed
        def generate_plan():
            return llm_client.complete(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
            )

        try:
            plan_content, usage = generate_plan()
        except Exception as e:
            raise click.ClickException(f"Plan generation error: {e}")

        metadata = {"Case Facts File": case_facts.name, "Budget Level": budget}
        if context:
            metadata["Context"] = context

        output_file = save_command_output(
            f"{output}_plan" if output else "caseplan",
            plan_content,
            "" if output else case_facts.name,
            metadata=metadata,
        )

        # Extract and save CLI commands
        extracted_commands = extract_cli_commands(plan_content)
        commands_file = save_command_output(
            f"{output}_commands" if output else f"caseplan_commands_{budget}",
            extracted_commands,
            "" if output else case_facts.name,
            metadata={"Type": "Executable Commands", "Budget": budget},
        )

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
            },
        )

        click.echo(f"\n{success_message('Litigation plan generated successfully!')}")
        click.echo(saved_message(f'Plan saved to: "{output_file}"'))
        click.echo(saved_message(f'Executable commands saved to: "{commands_file}"'))
        msg = tip_message(f'Execute commands: bash "{commands_file}"')
        click.echo(f"\n{msg}")
