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
    """Collapse trailing-backslash continuations into single logical lines.

    A trailing backslash is the only thing that continues a command across lines
    in bash, so it is the only continuation honoured here. Fence markers are
    preserved (extract_cli_commands tracks fence state); a backslash continuation
    that runs into a fence flushes rather than absorbing the fence as an argument.
    """
    merged: List[str] = []
    buffer = ""
    for line in lines:
        if line.strip().startswith("```"):
            if buffer:
                merged.append(buffer.rstrip())
                buffer = ""
            merged.append(line)
            continue
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
    in_fence = False

    def accept(command: str) -> None:
        nonlocal accepted, last_phase
        if current_phase != last_phase:
            body.append(f"\n# {current_phase}")
            last_phase = current_phase
        body.append(command)
        accepted += 1

    for line in _merge_continuations(plan_content.split("\n")):
        stripped = line.strip()

        if stripped.startswith("```"):
            # Toggle: a bash/sh fence opens a command region; any fence closes.
            in_fence = (not in_fence) and stripped.startswith(("```bash", "```sh"))
            continue

        if in_fence:
            # A command is a single logical line (trailing-backslash wraps are
            # already joined). Blank lines and `#` comments are skipped. A
            # litassist command is accepted; any other line in the fence is a
            # separate (would-be) shell line, NOT part of the command - it is
            # surfaced in `rejected` so it is neither merged into the command nor
            # silently dropped.
            if not stripped or stripped.startswith("#"):
                continue
            command = _safe_command(line, rejected)
            if command is not None:
                accept(command)
            elif stripped not in rejected:
                rejected.append(stripped)
            continue

        # Outside fences: one command per line (bare or `Commands:`-labelled);
        # non-command lines are plan prose and only update the phase label.
        command = _safe_command(line, rejected)
        if command is None:
            current_phase = _phase_from_line(stripped, current_phase)
            continue
        accept(command)

    footer = [
        "\n# End of extracted commands",
        "# Remember to update case_facts.txt after digest phases",
    ]
    script = "\n".join(header + body + footer)
    return script, accepted, rejected
