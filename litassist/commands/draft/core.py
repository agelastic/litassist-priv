"""
Citation-rich drafting via full-context LLM call.

This module implements the 'draft' command. All provided documents (PDFs and
text files) are concatenated with section markers and sent in a single
LLM call. There is no retrieval, embedding, or vector store: legal drafting
relies on every document being visible to the model.

For documents that exceed the configured model's context window, use
`litassist digest --mode summary <file>` first and feed the summary in.
"""

import click

from litassist.logging import save_log, save_command_output, log_task_event
from litassist.timing import timed
from litassist.utils.formatting import info_message
from litassist.utils.legal_reasoning import (
    detect_factual_hallucinations,
    verify_content_if_needed,
)
from litassist.utils.core import show_command_completion
from litassist.utils.file_ops import expand_glob_patterns_callback as expand_glob_patterns
from litassist.llm.factory import LLMClientFactory

from .document_processor import read_and_categorize_documents, build_text_context
from .prompt_builder import build_system_prompt, build_user_prompt


@click.command()
@click.argument(
    "documents",
    nargs=-1,
    required=True,
    type=click.Path(),
    callback=expand_glob_patterns,
)
@click.argument("query")
@click.option(
    "--heavy",
    is_flag=True,
    help="Use verification-heavy mode (max thinking effort)",
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Skip verification stage (not recommended for legal work)",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.pass_context
@timed
def draft(ctx, documents, query, heavy, noverify, output):
    """
    Citation-rich drafting via full-context LLM call.

    Concatenates every provided document into one context payload (PDFs and
    text files alike) and sends a single LLM call. Accepts multiple documents
    to combine knowledge from different sources (e.g., case_facts.txt and
    strategies.txt).

    Args:
        documents: One or more paths to documents (PDF or text files) to use as knowledge base.
                  Examples:
                  - litassist draft case_facts.txt "query"
                  - litassist draft case_facts.txt strategies.txt "query"
                  - litassist draft bundle.pdf case_facts.txt "query"
        query: The specific legal topic or argument to draft.

    Raises:
        click.ClickException: If there are errors with file reading or LLM API calls,
                             or if the combined context exceeds the model's window.
    """
    # Command start log
    try:
        log_task_event(
            "draft",
            "init",
            "start",
            "Starting draft generation",
            {"model": LLMClientFactory.get_model_for_command("draft")},
        )
    except Exception:
        pass

    # Process all documents
    structured_content = read_and_categorize_documents(documents)

    # Build a single full-context payload from every input document.
    context = build_text_context(structured_content)

    # Build prompts
    system_prompt = build_system_prompt(structured_content)
    user_prompt = build_user_prompt(query, context)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    # Preflight: compare the assembled payload against the configured model's
    # context window. Char-count is a conservative token proxy
    # (~3.5 chars/token for legal English).
    context_window_tokens = LLMClientFactory.get_context_window_for_command("draft")
    hard_limit_chars = int(context_window_tokens * 3.5 * 0.7)
    soft_limit_chars = int(hard_limit_chars * 0.7)
    payload_chars = sum(len(m["content"]) for m in messages)
    if payload_chars >= hard_limit_chars:
        raise click.ClickException(
            f"Combined draft context is {payload_chars:,} characters, which "
            f"exceeds the safe input budget ({hard_limit_chars:,} chars) for "
            f"{LLMClientFactory.get_model_for_command('draft')}. "
            f"Run `litassist digest --mode summary <file>` on the largest "
            f"inputs and feed the summary to draft."
        )
    if payload_chars >= soft_limit_chars:
        from litassist.utils.formatting import warning_message
        click.echo(warning_message(
            f"Draft context is {payload_chars:,} characters, approaching the "
            f"model's input budget ({hard_limit_chars:,} chars). Consider "
            f"running `litassist digest --mode summary <file>` on the largest "
            f"inputs first."
        ))

    # Generate draft with LLM
    client = LLMClientFactory.for_command("draft")

    try:
        log_task_event(
            "draft",
            "generation",
            "llm_call",
            "Sending draft generation prompt to LLM",
            {"model": client.model}
        )
    except Exception:
        pass

    try:
        content, usage = client.complete(messages)

        try:
            log_task_event(
                "draft",
                "generation",
                "llm_response",
                "Draft LLM response received",
                {"model": client.model}
            )
        except Exception:
            pass
    except Exception as e:
        # Safety net: if the provider rejects on context length despite our
        # preflight (e.g. token estimate undercounted), reframe with the same
        # digest guidance instead of leaking a raw provider error.
        err_text = str(e).lower()
        if any(s in err_text for s in (
            "context_length_exceeded",
            "context length",
            "maximum context",
            "too long",
            "exceeds the model",
        )):
            raise click.ClickException(
                f"Provider rejected draft on context length: {e}\n"
                f"Run `litassist digest --mode summary <file>` on the largest "
                f"inputs and feed the summary to draft."
            )
        raise click.ClickException(f"LLM draft error: {e}")

    # Note: Citation verification now handled automatically in LLMClient.complete()

    # Warn if both --noverify and --heavy are specified
    if noverify and heavy:
        from litassist.utils.formatting import warning_message
        click.echo(warning_message("--heavy flag ignored when --noverify is specified"))

    if noverify:
        click.echo(info_message("Standard verification skipped"))

    # Prepare base metadata
    base_metadata = {
        "Query": query,
        "Documents": ", ".join(documents),
    }

    if not noverify:
        # Save raw pre-verification output for audit trail
        raw_metadata = {**base_metadata, "Verification": "Not yet applied (raw output)"}
        save_command_output(
            output if output else "draft",
            content,
            "" if output else query,
            metadata=raw_metadata,
            suffix="_raw",
        )

        # Apply standard verification (uses verification chain like extractfacts/strategy)
        try:
            log_task_event(
                "draft",
                "verification",
                "start",
                "Starting draft verification"
            )
        except Exception:
            pass

        content, _ = verify_content_if_needed(
            client, content, "draft", verify_flag=True, heavy=heavy
        )
        verification_mode = "verification-heavy (max thinking effort)" if heavy else "Standard verification"
        click.echo(info_message(f"{verification_mode} applied"))

        try:
            log_task_event(
                "draft",
                "verification",
                "end",
                "Verification complete"
            )
        except Exception:
            pass

    # Track critiques for appending to output
    critiques = []

    # Check for potential hallucinations
    try:
        log_task_event(
            "draft",
            "hallucination",
            "start",
            "Checking for potential hallucinations"
        )
    except Exception:
        pass

    hallucination_warnings = detect_factual_hallucinations(content, context)

    try:
        log_task_event(
            "draft",
            "hallucination",
            "end",
            f"Hallucination check complete - {len(hallucination_warnings) if hallucination_warnings else 0} warnings"
        )
    except Exception:
        pass
    if hallucination_warnings:
        # Capture hallucination warnings for critique section
        warning_text = "The following potentially hallucinated facts were detected:\n"
        for warning in hallucination_warnings:
            warning_text += f"- {warning}\n"
        warning_text += (
            "\nPlease verify all facts against source documents before use.\n"
        )
        warning_text += (
            "Replace any invented details with placeholders like [TO BE PROVIDED]."
        )
        critiques.append(("Factual Accuracy Warning", warning_text))

        # Also add to main content for visibility
        warning_header = "# FACTUAL ACCURACY WARNING\n\n"
        warning_header += (
            "The following potentially hallucinated facts were detected:\n"
        )
        for warning in hallucination_warnings:
            warning_header += f"- {warning}\n"
        warning_header += (
            "\nPlease verify all facts against source documents before use.\n"
        )
        warning_header += (
            "Replace any invented details with placeholders like [TO BE PROVIDED].\n\n"
        )
        warning_header += "---\n\n"
        content = warning_header + content

    # Save output using utility
    final_metadata = {"Query": query, "Documents": ", ".join(documents)}
    if noverify:
        final_metadata["Verification"] = "Skipped (--noverify)"
    else:
        verification_mode = "verification-heavy (max thinking effort)" if heavy else "Standard verification"
        final_metadata["Verification"] = verification_mode

    output_file = save_command_output(
        output if output else "draft",
        content,
        "" if output else query,
        metadata=final_metadata,
        critique_sections=critiques if critiques else None,
    )

    # Reasoning trace is embedded in the main output, not saved separately
    extra_files = None

    # Save audit log (without response content)
    save_log(
        "draft",
        {
            "inputs": {
                "documents": list(documents),
                "query": query,
                "context": context if context else None,
            },
            # Response content removed - already logged by LLMClient separately
            "usage": usage,
            "verification": "disabled" if noverify else ("heavy" if heavy else "standard"),
            "output_file": output_file,
        },
    )

    # Show completion with preview
    if noverify:
        verification_mode = "Skipped (--noverify)"
    else:
        verification_mode = "verification-heavy (max thinking effort)" if heavy else "Standard verification"
    stats = {
        "Query": query,
        "Documents": len(documents),
        "Verification": verification_mode,
    }

    show_command_completion("draft", output_file, extra_files, stats)

    # Command end log
    try:
        log_task_event(
            "draft",
            "init",
            "end",
            "Draft generation complete"
        )
    except Exception:
        pass

    # Show brief preview
    lines = content.split("\n")
    preview_lines = [line for line in lines[:10] if line.strip()][:5]
    if preview_lines:
        click.echo(f"\n{info_message('Preview:')}")
        for line in preview_lines:
            click.echo(f"   {line[:80]}..." if len(line) > 80 else f"   {line}")
