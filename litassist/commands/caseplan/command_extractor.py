"""
CLI command extraction from caseplan output.

Handles parsing of markdown plan output to extract executable bash commands.
"""


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
