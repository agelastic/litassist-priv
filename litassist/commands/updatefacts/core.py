"""
Main CLI orchestration for the updatefacts command.

Folds source documents (digest/extractfacts output, or any text) into the
10-heading case_facts structure: it updates an existing case-facts file or
creates one from scratch, then writes a fresh, auto-discoverable
case_facts_<timestamp>.txt into the current directory so downstream commands
(strategy, brainstorm, barbrief, draft) pick it up without manual copy-paste.
"""

import os

import click

from litassist.timing import timed
from litassist.utils.core import show_command_completion
from litassist.utils.formatting import info_message, warning_message
from litassist.utils.file_ops import (
    expand_glob_patterns_callback as expand_glob_patterns,
    validate_file_size,
)
from litassist.utils.case_facts import (
    resolve_case_facts_file,
    validate_case_facts_format,
)
from litassist.logging import (
    save_log,
    save_command_output,
    log_task_event,
)
from litassist.llm.factory import LLMClientFactory
from litassist.prompts import PROMPTS


@click.command()
@click.argument(
    "file", nargs=-1, required=True, type=click.Path(), callback=expand_glob_patterns
)
@click.option(
    "--facts",
    "facts",
    type=click.Path(exists=True),
    default=None,
    help=(
        "Existing case facts file to update. Default: the latest "
        "case_facts*.txt in the current directory; created from scratch if none."
    ),
)
@timed
def updatefacts(file, facts):
    """
    Fold source documents into the 10-heading case_facts structure.

    Reads one or more SOURCE documents (e.g. digest or extractfacts output) and
    merges their content into an existing case-facts file - or creates one when
    none exists - under the ten standard headings, with a final Notes section
    for anything that does not fit. Always writes a fresh, auto-discoverable
    case_facts_<timestamp>.txt into the current directory; source files are
    never modified.

    Args:
        file: Path(s) to the source document(s) to fold in (glob supported).
        facts: Optional existing case-facts file to update.

    Raises:
        click.ClickException: On file read errors, an oversized combined input,
                              or LLM API errors. A merge missing required headings
                              is warned about but still saved (downstream commands
                              run the same validation).
    """
    try:
        log_task_event(
            "updatefacts",
            "init",
            "start",
            "Starting case facts update",
            {"model": LLMClientFactory.get_model_for_command("updatefacts")},
        )
    except Exception:
        pass

    # Single per-call character budget derived from the configured model window.
    budget = LLMClientFactory.get_input_budget_for_command("updatefacts")

    # Resolve the base case-facts file: explicit --facts, else the latest
    # case_facts*.txt in the current directory, else create from scratch.
    if facts:
        base_path = facts
    else:
        try:
            base_path = resolve_case_facts_file()
        except click.ClickException:
            base_path = None

    if base_path:
        existing_facts = validate_file_size(
            base_path, max_size=budget, file_type="case facts"
        )
    else:
        existing_facts = "(none yet -- create from scratch)"
        click.echo(
            info_message("No existing case facts found; creating from scratch")
        )

    # Read and combine all source documents through a single read path:
    # validate_file_size calls read_document internally and returns the content,
    # so there is no separate read_document pass.
    new_material = ""
    source_files = []
    for path in file:
        text = validate_file_size(path, max_size=budget, file_type="source")
        name = os.path.basename(path)
        source_files.append(name)
        new_material += f"\n\n=== SOURCE: {name} ===\n\n{text}"

    try:
        log_task_event(
            "updatefacts", "reading", "end", f"Read {len(file)} document(s)"
        )
    except Exception:
        pass

    # Per-file validation does not bound the COMBINED prompt, so check the total
    # against the model window and fail fast rather than silently truncating.
    total_len = len(existing_facts) + len(new_material)
    if total_len > budget:
        raise click.ClickException(
            f"Combined input too large ({total_len:,} characters) for the "
            f"updatefacts model window (~{budget:,} characters). Reduce the "
            "number of source files or summarise them first (e.g. with 'digest')."
        )

    # Build the merge prompt from the shared 10-heading format template plus the
    # existing facts and new material.
    format_instructions = PROMPTS.get_format_template("case_facts_10_heading")
    prompt = PROMPTS.get("analysis.updatefacts.merge_prompt").format(
        format_instructions=format_instructions,
        existing_facts=existing_facts,
        new_material=new_material,
    )

    client = LLMClientFactory.for_command("updatefacts")

    try:
        log_task_event(
            "updatefacts",
            "merge",
            "llm_call",
            "Sending merge prompt to LLM",
            {"model": client.model},
        )
    except Exception:
        pass

    try:
        combined, _ = client.complete(
            [
                {
                    "role": "system",
                    "content": PROMPTS.get_system_prompt("updatefacts"),
                },
                {"role": "user", "content": prompt},
            ]
        )
    except Exception as e:
        raise click.ClickException(f"Error updating case facts: {e}")

    # Validate the merged result. Like extractfacts, warn (the validator echoes
    # the missing headings) but still save - the downstream commands run the same
    # validation and reject a wrong-shaped file with a clear message, so there is
    # no need to special-case it here.
    if not validate_case_facts_format(combined):
        click.echo(
            warning_message(
                "Updated facts are missing one or more required headings (see "
                "above). Saving anyway - review before using downstream."
            )
        )

    # Write a fresh case_facts_<timestamp>.txt into the CURRENT directory (not
    # outputs/) so resolve_case_facts_file picks it up automatically.
    metadata = {
        "Source Files": ", ".join(source_files),
        "Base Facts": base_path if base_path else "created from scratch",
        "Model": client.model,
    }
    output_file = save_command_output(
        "case_facts",
        combined,
        "",
        metadata=metadata,
        output_dir=os.getcwd(),
    )

    # Also refresh a stable ./case_facts.txt with the merged facts. The timestamped
    # copy above keeps history and feeds resolve_case_facts_file, but downstream
    # scripts (and the caseplan planner's examples) frequently reference the literal
    # 'case_facts.txt'; without this they fail with "File not found: case_facts.txt".
    stable_path = os.path.join(os.getcwd(), "case_facts.txt")
    with open(stable_path, "w", encoding="utf-8") as fh:
        fh.write(combined)
    click.echo(info_message(f"Refreshed {stable_path}"))

    save_log(
        "updatefacts",
        {
            "inputs": {
                "source_files": list(file),
                "base_facts": base_path,
            },
            "output_file": output_file,
        },
    )

    stats = {
        "Sources": (
            f"{len(source_files)} files"
            if len(source_files) > 1
            else source_files[0]
        ),
        "Base": base_path if base_path else "created from scratch",
        "Structure": "10 headings + Notes",
    }
    show_command_completion("updatefacts", output_file, None, stats)

    try:
        log_task_event("updatefacts", "init", "end", "Case facts update complete")
    except Exception:
        pass
