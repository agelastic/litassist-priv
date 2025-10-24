"""
Auto-generate case_facts.txt under ten structured headings.

This module implements the 'extractfacts' command which processes a document
to extract relevant case facts and organizes them into a structured format
with ten standard headings.
"""

import click
import os

from litassist.config import get_config
from litassist.prompts import PROMPTS
from litassist.utils.text_processing import chunk_text
from litassist.utils.file_ops import validate_file_size
from litassist.utils.core import (
    timed,
    show_command_completion,
)
from litassist.utils.legal_reasoning import (
    create_reasoning_prompt,
    verify_content_if_needed,
)
from litassist.utils.formatting import (
    info_message,
)
from litassist.logging import (
    save_log,
    save_command_output,
    log_task_event,
)
from litassist.llm.factory import LLMClientFactory


@click.command()
@click.argument("file", nargs=-1, required=True, type=click.Path(exists=True))
@click.option(
    "--verify", is_flag=True, help="Enable self-critique pass (default: auto-enabled)"
)
@click.option(
    "--noverify",
    is_flag=True,
    help="Skip standard verification",
)
@click.option("--output", type=str, help="Custom output filename prefix")
@timed
def extractfacts(file, verify, noverify, output):
    """
    Auto-generate case_facts.txt under ten structured headings.

    Processes one or more documents to extract relevant case facts and organizes them
    into a structured format with ten standard headings. This provides a
    foundation for other commands like 'brainstorm' and 'strategy' which require structured facts.

    Args:
        file: Path(s) to the document(s) (PDF or text) to extract facts from.
        verify: Whether to run a self-critique verification pass on the extracted facts.

    Raises:
        click.ClickException: If there are errors reading the file, processing chunks,
                             or with the LLM API calls.
    """
    # Command start log
    try:
        log_task_event(
            "extractfacts",
            "init",
            "start",
            "Starting fact extraction",
            {"model": LLMClientFactory.get_model_for_command("extractfacts")},
        )
    except Exception:
        pass

    # Process all files
    try:
        log_task_event(
            "extractfacts",
            "reading",
            "start",
            "Reading input documents"
        )
    except Exception:
        pass
    
    all_text = ""
    source_files = []
    for f in file:
        text = validate_file_size(f, max_size=3000000, file_type="source")
        source_files.append(os.path.basename(f))
        all_text += f"\n\n--- SOURCE: {os.path.basename(f)} ---\n\n{text}"

    # Use existing chunking on combined text
    chunks = chunk_text(all_text, max_chars=get_config().max_chars)

    # Initialize the LLM client using factory
    client = LLMClientFactory.for_command("extractfacts")
    
    try:
        log_task_event(
            "extractfacts",
            "reading",
            "end",
            f"Read {len(file)} document(s)"
        )
    except Exception:
        pass

    # Process content based on chunking needs (now most documents will be single chunk)
    if len(chunks) == 1:
        # Single chunk - unified extraction approach
        # Use centralized format template
        format_instructions = PROMPTS.get_format_template("case_facts_10_heading")
        base_prompt = PROMPTS.get("analysis.extraction.base_prompt").format(
            format_instructions=format_instructions, content=chunks[0]
        )

        # Add reasoning trace to prompt
        prompt = create_reasoning_prompt(base_prompt, "extractfacts")
        
        try:
            log_task_event(
                "extractfacts",
                "extraction",
                "llm_call",
                "Sending single-file extraction prompt to LLM",
                {"model": client.model}
            )
        except Exception:
            pass
        
        try:
            combined, usage = client.complete(
                [
                    {
                        "role": "system",
                        "content": PROMPTS.get_system_prompt("extractfacts"),
                    },
                    {"role": "user", "content": prompt},
                ]
            )
            
            try:
                log_task_event(
                    "extractfacts",
                    "extraction",
                    "llm_response",
                    "Single-file extraction LLM response received",
                    {"model": client.model}
                )
            except Exception:
                pass
            
        except Exception as e:
            raise click.ClickException(f"Error extracting facts: {e}")

    else:
        # Multiple chunks - enhanced two-stage approach with better context preservation
        click.echo(
            info_message(
                "Processing large document in sections for comprehensive fact extraction..."
            )
        )
        accumulated_facts = []

        # First, extract relevant facts from each chunk
        with click.progressbar(chunks, label="Extracting facts from sections") as bar:
            for idx, chunk in enumerate(bar, 1):
                chunk_template = PROMPTS.get("processing.extraction.chunk_facts_prompt")
                prompt = PROMPTS.get("analysis.extraction.chunk_prompt").format(
                    chunk_template=chunk_template.format(
                        chunk_num=idx, total_chunks=len(chunks)
                    ),
                    chunk=chunk,
                )

                try:
                    log_task_event(
                        "extractfacts",
                        "extraction",
                        "llm_call",
                        f"Extracting facts from section {idx}/{len(chunks)}",
                        {"model": client.model}
                    )
                except Exception:
                    pass
                
                try:
                    content, usage = client.complete(
                        [
                            {
                                "role": "system",
                                "content": PROMPTS.get(
                                    "processing.extraction.chunk_system_prompt"
                                ),
                            },
                            {"role": "user", "content": prompt},
                        ]
                    )
                    
                    try:
                        log_task_event(
                            "extractfacts",
                            "extraction",
                            "llm_response",
                            f"Section {idx}/{len(chunks)} extraction complete",
                            {"model": client.model}
                        )
                    except Exception:
                        pass
                    
                except Exception as e:
                    raise click.ClickException(f"Error processing chunk {idx}: {e}")
                accumulated_facts.append(content.strip())

        # Enhanced organization phase with better synthesis
        click.echo(
            info_message("Organizing and synthesizing facts into structured format...")
        )
        # Join accumulated facts with clear === separators for each chunk
        # Add END marker after each chunk's facts
        facts_with_markers = []
        for idx, facts in enumerate(accumulated_facts, 1):
            facts_with_markers.append(
                f"=== CHUNK {idx} FACTS ===\n{facts}\n=== END CHUNK {idx} FACTS ==="
            )
        all_facts = "\n\n".join(facts_with_markers)

        # Use centralized format template for organizing
        format_instructions = PROMPTS.get_format_template("case_facts_10_heading")
        organize_template = PROMPTS.get("processing.extraction.organize_facts_prompt")
        base_organize_prompt = organize_template.format(
            format_instructions=format_instructions, all_facts=all_facts
        )

        # Add reasoning trace to organize prompt
        organize_prompt = create_reasoning_prompt(base_organize_prompt, "extractfacts")

        try:
            log_task_event(
                "extractfacts",
                "consolidation",
                "llm_call",
                "Sending consolidation prompt to LLM",
                {"model": client.model}
            )
        except Exception:
            pass
        
        try:
            combined, usage = client.complete(
                [
                    {
                        "role": "system",
                        "content": PROMPTS.get_system_prompt("extractfacts"),
                    },
                    {"role": "user", "content": organize_prompt},
                ]
            )
            
            try:
                log_task_event(
                    "extractfacts",
                    "consolidation",
                    "llm_response",
                    "Consolidation LLM response received",
                    {"model": client.model}
                )
            except Exception:
                pass
            
        except Exception as e:
            raise click.ClickException(f"Error organizing facts: {e}")

    # Note: Citation verification now handled automatically in LLMClient.complete()

    # Apply standard verification (CoVe moved to standalone 'verify-cove' command)
    verification_metadata = {"Source Files": ", ".join(source_files)}
    if not noverify:
        try:
            log_task_event(
                "extractfacts",
                "verification",
                "start",
                "Starting verification"
            )
        except Exception:
            pass
        
        combined, _ = verify_content_if_needed(
            client, combined, "extractfacts", verify_flag=True
        )
        verification_metadata["Verification"] = "Standard verification"
        verification_metadata["Model"] = client.model
        click.echo(info_message("Standard verification applied"))
        
        try:
            log_task_event(
                "extractfacts",
                "verification",
                "end",
                "Verification complete"
            )
        except Exception:
            pass
    else:
        verification_metadata["Verification"] = "Disabled"
        verification_metadata["Model"] = "N/A"
        click.echo(info_message("Standard verification skipped by --noverify flag"))

    # Save output using utility (reasoning trace remains inline)
    slug = "_".join(source_files[:3])  # Use first 3 files for slug
    if len(source_files) > 3:
        slug += f"_and_{len(source_files) - 3}_more"
    output_file = save_command_output(
        output if output else "extractfacts",
        combined,
        "" if output else slug,
        metadata=verification_metadata,
    )

    # Audit log (without response content)
    save_log(
        "extractfacts",
        {
            "inputs": {"source_files": list(file), "chunks": len(chunks)},
            "params": "verify=True (auto-enabled)",
            # Response content removed - already logged by LLMClient separately
            "output_file": output_file,
        },
    )

    # Show completion
    chunk_desc = f"{len(chunks)} chunks" if len(chunks) > 1 else "single document"
    source_desc = ", ".join(source_files[:3])
    if len(source_files) > 3:
        source_desc += f" + {len(source_files) - 3} more"
    stats = {
        "Sources": (
            f"{len(source_files)} files" if len(source_files) > 1 else source_files[0]
        ),
        "Processed": chunk_desc,
        "Structure": "10 structured headings",
        "Verification": "Legal accuracy review applied",
    }

    show_command_completion("extractfacts", output_file, None, stats)
    click.echo(
        info_message("To use with other commands, manually copy to case_facts.txt")
    )
    
    # Command end log
    try:
        log_task_event(
            "extractfacts",
            "init",
            "end",
            "Fact extraction complete"
        )
    except Exception:
        pass
