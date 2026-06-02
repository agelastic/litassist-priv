"""
CLI command extraction from caseplan output.

Parses markdown plan output and emits an executable PYTHON runner. The runner
isolates each EXECUTION under a fresh outputs/run_<timestamp>/ directory: it seeds
a baseline case_facts from the launch dir, sets LITASSIST_OUTPUT_DIR (which the
output sink + updatefacts + resolve_case_facts_file honour), and runs each step
with subprocess.run(args, shell=False) - so shell control characters in the LLM
output (;, |, &&, $(...), redirections) are inert literal arguments, never live
operators. Every accepted command becomes a `run([...])` call whose `outputs/` and
case_facts path tokens are rewritten to os.path.join(run_dir, ...), keeping reads
and writes inside the per-run dir.
"""

import shlex
from typing import List, Optional, Tuple

# Only bash/sh fences delimit command regions; the fence lines themselves are
# skipped. A leading "Commands:" label (used by older prompt examples) is
# stripped before tokenisation. (Fences stay bash-flavoured as the INPUT
# delimiter; the SAVED artifact is Python.)
_COMMANDS_LABEL = "Commands:"


def _phase_from_line(stripped_line: str, current_phase: str) -> str:
    """Derive a phase label from a heading line, else keep the current phase."""
    if "PHASE" in stripped_line.upper() and ":" in stripped_line:
        phase_num, phase_desc = stripped_line.split(":", 1)
        return f"{phase_num.replace('#', '').strip()}: {phase_desc.strip()}"
    return current_phase


def _safe_command(raw_line: str, rejected: List[str]) -> Optional[List[str]]:
    """Return the validated ``litassist ...`` token list, or None.

    Lines that do not start a litassist command return None silently (prose,
    headings, manual tasks). Lines that look like a command but fail validation
    (unbalanced quotes, first token not exactly ``litassist``) are recorded in
    ``rejected`` so the caller can surface them instead of emitting unsafe steps.
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
    return tokens


def _path_expr(token: str) -> str:
    """Python expression for one path token, isolating run-dir paths.

    Strips a leading ``./``. An ``outputs/<rest>`` token or a ``case_facts...``
    ``.txt``/``.md`` file/glob is rewritten to ``os.path.join(run_dir, ...)`` so the
    runner reads/writes inside the per-run dir; anything else (source documents,
    prose, bare words) stays a cwd-relative literal. Classification is by token
    SHAPE, not by which option precedes it: the prompt only ever emits ``outputs/``
    or ``case_facts*.{txt,md}`` shapes where a run-dir path belongs, so a prose
    value (an --outcome sentence, a --context phrase) is never path-shaped.
    """
    norm = token[2:] if token.startswith("./") else token
    # Run-dir paths (outputs/ globs and case_facts) are normalised to .md before
    # rewriting: save_command_output always writes outputs with a .md extension and
    # the runner seeds case_facts.md, so a legacy .txt reference (an old/hand-edited
    # plan, or an LLM slip back to the historic .txt convention) must point at the
    # .md file that actually exists in the per-run dir. Without this it would route
    # to a never-created run_dir/*.txt and the step would fail with "File not found".
    if norm.startswith("outputs/"):
        rest = norm[len("outputs/"):]
        if rest.endswith(".txt"):
            rest = rest[:-4] + ".md"
        return f"os.path.join(run_dir, {rest!r})"
    if norm.startswith("case_facts") and norm.endswith((".txt", ".md")):
        if norm.endswith(".txt"):
            norm = norm[:-4] + ".md"
        return f"os.path.join(run_dir, {norm!r})"
    return repr(token)


def _python_arg(token: str, prev: str) -> str:
    """Python expression for one command token (handles --output + equals-form)."""
    # The value after --output is a filename PREFIX routed by the sink, not a
    # path: never rewrite it (rewriting would corrupt the producer name).
    if prev == "--output":
        return repr(token)
    if token.startswith("--") and "=" in token:
        flag, _, val = token.partition("=")
        if flag != "--output":
            expr = _path_expr(val)
            if expr != repr(val):  # the value is a run-dir path -> splice it in
                return f"{(flag + '=')!r} + {expr}"
        return repr(token)  # --output= form, or a non-path equals value: literal
    return _path_expr(token)


def _emit_run(tokens: List[str]) -> str:
    """Render one validated command as a ``run([...])`` call."""
    args: List[str] = []
    prev = ""
    for tok in tokens:
        args.append(_python_arg(tok, prev))
        prev = tok
    return "run([" + ", ".join(args) + "])"


def _merge_continuations(lines: List[str]) -> List[str]:
    """Collapse trailing-backslash continuations into single logical lines.

    A trailing backslash is the only thing that continues a command across lines
    in the source plan, so it is the only continuation honoured here. Fence
    markers are preserved (extract_cli_commands tracks fence state); a backslash
    continuation that runs into a fence flushes rather than absorbing the fence.
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


def extract_cli_commands(
    plan_content: str, seed_facts: Optional[str] = None
) -> Tuple[str, int, List[str]]:
    """
    Extract executable litassist commands from the caseplan output.

    Args:
        plan_content: The LLM plan markdown to extract commands from.
        seed_facts: The case-facts file caseplan was given; the runner copies it
            into the run dir as the baseline case_facts.md (the exact facts the plan
            was built for), falling back to a stable ./case_facts.md (or legacy
            ./case_facts.txt).

    Returns a tuple of:
        - the formatted Python runner (always at least the scaffold),
        - the number of accepted commands,
        - the list of rejected command strings (looked like commands but failed
          safety validation).
    """
    header = [
        "#!/usr/bin/env python3",
        '"""Generated by litassist caseplan - review before running.',
        "",
        "Runs the planned litassist commands in order. Every output for THIS run",
        "(and case_facts) is written to a fresh outputs/run_<timestamp>/ directory,",
        "so re-running never mixes with a previous run's files. Stops at the first",
        "failing step.",
        '"""',
        "import os",
        "import shutil",
        "import subprocess",
        "from datetime import datetime",
        "",
        'run_dir = os.path.join("outputs", "run_" + datetime.now().strftime("%Y%m%d_%H%M%S_%f"))',
        "os.makedirs(run_dir)",
        "# Seed the baseline case_facts: the exact file caseplan was given, else a",
        "# stable ./case_facts.md (or legacy ./case_facts.txt). The cwd source is",
        "# copied, never moved/mutated, and always lands as case_facts.md.",
        f"_seed = next((p for p in [{seed_facts!r}, \"case_facts.md\", \"case_facts.txt\"] if p and os.path.exists(p)), \"\")",
        "if _seed:",
        '    shutil.copy(_seed, os.path.join(run_dir, "case_facts.md"))',
        'os.environ["LITASSIST_OUTPUT_DIR"] = run_dir',
        'print("Outputs for this run -> " + run_dir)',
        "",
        "",
        "def run(args):",
        '    print("\\n$ " + " ".join(args))',
        "    if subprocess.run(args).returncode != 0:",
        '        raise SystemExit("Step failed; stopping.")',
        "",
    ]
    body: List[str] = []
    rejected: List[str] = []
    accepted = 0
    current_phase = "Initial Setup"
    last_phase: Optional[str] = None
    in_fence = False

    def accept(tokens: List[str]) -> None:
        nonlocal accepted, last_phase
        if current_phase != last_phase:
            body.append(f"\n# === {current_phase} ===")
            last_phase = current_phase
        body.append(_emit_run(tokens))
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
            # separate (would-be) line, NOT part of the command - surfaced in
            # `rejected` so it is neither merged into the command nor dropped.
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
        "",
        'print("\\nAll steps complete. Outputs in " + run_dir)',
    ]
    script = "\n".join(header + body + footer)
    return script, accepted, rejected
