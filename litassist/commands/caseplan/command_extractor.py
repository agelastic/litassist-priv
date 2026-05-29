"""
CLI command extraction from caseplan output.

Parses markdown plan output and extracts the executable litassist commands.
Because the result is saved as a script the user is told to run with bash, every
accepted command is round-tripped through shlex: tokens are parsed with
shlex.split and re-rendered with shlex.join, so shell control characters in the
LLM output (;, |, &&, $(...), redirections) cannot survive as live operators.
"""

import shlex
from typing import List, Optional, Tuple

# Only bash/sh fences delimit command regions; the fence lines themselves are
# skipped. A leading "Commands:" label (used by older prompt examples) is
# stripped before tokenisation.
_COMMANDS_LABEL = "Commands:"


def _phase_from_line(stripped_line: str, current_phase: str) -> str:
    """Derive a phase label from a heading line, else keep the current phase."""
    if "PHASE" in stripped_line.upper() and ":" in stripped_line:
        phase_num, phase_desc = stripped_line.split(":", 1)
        return f"{phase_num.replace('#', '').strip()}: {phase_desc.strip()}"
    return current_phase


def _safe_command(raw_line: str, rejected: List[str]) -> Optional[str]:
    """Return a shlex-normalised ``litassist ...`` command, or None.

    Lines that do not start a litassist command return None silently (prose,
    headings, manual tasks). Lines that look like a command but fail validation
    (unbalanced quotes, first token not exactly ``litassist``) are recorded in
    ``rejected`` so the caller can surface them instead of writing unsafe shell.
    """
    candidate = raw_line.strip()
    if candidate.startswith(_COMMANDS_LABEL):
        candidate = candidate[len(_COMMANDS_LABEL):].strip()
    if not candidate.startswith("litassist"):
        return None
    try:
        tokens = shlex.split(candidate)
    except ValueError:
        rejected.append(candidate)
        return None
    if not tokens or tokens[0] != "litassist":
        rejected.append(candidate)
        return None
    return shlex.join(tokens)


def _merge_continuations(lines: List[str]) -> List[str]:
    """Collapse trailing-backslash line continuations into single logical lines."""
    merged: List[str] = []
    buffer = ""
    for line in lines:
        if line.rstrip().endswith("\\"):
            buffer += line.rstrip()[:-1].rstrip() + " "
            continue
        merged.append(buffer + line)
        buffer = ""
    if buffer:
        merged.append(buffer.rstrip())
    return merged


def extract_cli_commands(plan_content: str) -> Tuple[str, int, List[str]]:
    """
    Extract executable litassist commands from the caseplan output.

    Returns a tuple of:
        - the formatted bash script (always at least the header/footer),
        - the number of accepted commands,
        - the list of rejected command strings (looked like commands but failed
          safety validation).
    """
    header = [
        "#!/bin/bash",
        "# Extracted CLI commands from caseplan",
        "# Review every command before running - generated from LLM output.",
        "# Execute commands in order, reviewing output between phases",
        "",
    ]
    body: List[str] = []
    rejected: List[str] = []
    accepted = 0
    current_phase = "Initial Setup"
    last_phase: Optional[str] = None

    for line in _merge_continuations(plan_content.split("\n")):
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        command = _safe_command(line, rejected)
        if command is None:
            current_phase = _phase_from_line(stripped, current_phase)
            continue
        if current_phase != last_phase:
            body.append(f"\n# {current_phase}")
            last_phase = current_phase
        body.append(command)
        accepted += 1

    footer = [
        "\n# End of extracted commands",
        "# Remember to update case_facts.txt after digest phases",
    ]
    script = "\n".join(header + body + footer)
    return script, accepted, rejected
