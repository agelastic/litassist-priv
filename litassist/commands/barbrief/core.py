"""
Generate comprehensive barrister's brief for Australian litigation.

This module implements the 'barbrief' command which consolidates case materials
into a structured brief suitable for briefing counsel. It combines case facts,
strategies, research, and supporting documents into a comprehensive document
with proper citations and Australian legal formatting.
"""

import click

from litassist.utils.file_ops import expand_glob_patterns_callback as expand_glob_patterns
from litassist.utils.core import timed, show_command_completion
from litassist.utils.text_processing import count_tokens_and_words
from litassist.logging import save_command_output, log_task_event
from litassist.llm.factory import LLMClientFactory

from .validator import validate_case_facts
from .document_reader import read_all_documents, estimate_input_size
from .section_builder import prepare_brief_sections
from .brief_generator import generate_brief, verify_citations_if_requested


@click.command()
@click.argument("case_facts", type=click.Path(exists=True))
@click.option(
    "--strategies",
    multiple=True,
    type=click.Path(),  # Remove exists=True since we check in callback
    callback=expand_glob_patterns,
    help="Brainstormed strategies files. Supports glob patterns. Use: --strategies 'outputs/brainstorm_*.txt'",
)
@click.option(
    "--research",
    multiple=True,
    type=click.Path(),
    callback=expand_glob_patterns,
    help="Lookup/research reports. Supports glob patterns. Use: --research 'outputs/lookup_*.txt'",
)
@click.option(
    "--documents",
    multiple=True,
    type=click.Path(),
    callback=expand_glob_patterns,
    help="Supporting documents. Supports glob patterns. Use: --documents '*.pdf'",
)
@click.option(
    "--context",
    type=str,
    help="Additional context to guide the analysis",
)
@click.option(
    "--hearing-type",
    type=click.Choice(["trial", "directions", "interlocutory", "appeal"]),
    required=True,
    help="Type of hearing",
)
@click.option(
    "--verify",
    is_flag=True,
    help="Enable citation verification",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@click.pass_context
@timed
def barbrief(
    ctx,
    case_facts,
    strategies,
    research,
    documents,
    context,
    hearing_type,
    verify,
    output,
):
    """
    Generate comprehensive barrister's brief for Australian litigation.

    Creates a structured brief combining case facts, legal strategies,
    research, and supporting documents. The brief follows Australian
    legal conventions and includes proper citation formatting.

    Args:
        case_facts: Path to structured case facts (10-heading format)
        strategies: Optional path to brainstormed strategies
        research: Optional research/lookup reports (multiple allowed)
        documents: Optional supporting documents (multiple allowed)
        context: Optional additional context to guide the analysis
        hearing_type: Type of hearing (trial/directions/interlocutory/appeal)
        verify: Whether to verify citations

    Raises:
        click.ClickException: If case facts are invalid or API calls fail
    """
    # Command start log
    try:
        log_task_event(
            "barbrief",
            "init",
            "start",
            "Starting barrister's brief generation",
            {"model": LLMClientFactory.get_model_for_command("barbrief")},
        )
    except Exception:
        pass

    # Read all documents
    content_dict = read_all_documents(case_facts, strategies, research, documents)

    # Validate case facts
    if not validate_case_facts(content_dict["case_facts_content"]):
        raise click.ClickException(
            "Case facts must be in 10-heading format from extractfacts command"
        )

    # Estimate input size and warn if large
    estimate_input_size(content_dict)

    # Calculate total tokens for error messages
    total_content = (
        content_dict["case_facts_content"]
        + "\n"
        + content_dict["strategies_content"]
        + "\n"
        + "\n".join(content_dict["research_docs"])
        + "\n"
        + "\n".join(content_dict["supporting_docs"])
    )
    total_tokens, _ = count_tokens_and_words(total_content)

    # Prepare sections
    try:
        log_task_event(
            "barbrief",
            "preparation",
            "start",
            "Preparing brief sections"
        )
    except Exception:
        pass

    sections = prepare_brief_sections(
        content_dict["case_facts_content"],
        content_dict["strategies_content"],
        content_dict["research_docs"],
        content_dict["supporting_docs"],
        context,
        hearing_type,
    )

    # Get LLM client
    try:
        client = LLMClientFactory.for_command("barbrief")
    except Exception as e:
        raise click.ClickException(f"Failed to initialize LLM client: {e}")

    # Generate the brief
    content, usage = generate_brief(client, sections, total_tokens)

    # Run manual citation verification if requested
    verify_citations_if_requested(content, verify)

    # Save the brief with comprehensive metadata
    metadata = {
        "Case Facts": case_facts,
        "Hearing Type": hearing_type.title(),
    }

    # Add optional file inputs if provided
    if strategies:
        metadata["Strategies"] = ", ".join(strategies)
    if research:
        metadata["Research"] = ", ".join(research)
    if documents:
        metadata["Documents"] = ", ".join(documents)
    if context:
        metadata["Context"] = context

    output_file = save_command_output(
        output if output else "barbrief",
        content,
        "" if output else hearing_type,
        metadata=metadata
    )

    # Show completion message
    show_command_completion(
        "Barristers brief generated",
        output_file,
        stats={"Tokens used": usage.get("total_tokens")},
    )

    # Command end log
    try:
        log_task_event(
            "barbrief",
            "init",
            "end",
            "Barrister's brief generation complete"
        )
    except Exception:
        pass
