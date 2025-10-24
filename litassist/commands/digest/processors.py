"""
Content processing functions for digest command.

This module handles the actual LLM processing of document chunks
for both summary and issues modes.
"""

from typing import List, Dict, Any, Tuple, Optional
import click
from litassist.prompts import PROMPTS
from litassist.llm.api_handlers import NonRetryableAPIError
from litassist.logging import log_task_event


def process_single_chunk(
    content: str, mode: str, context: Optional[str], llm_client: Any, file_name: str
) -> Tuple[str, Dict[str, Any]]:
    """
    Process a single document chunk with the LLM.

    Args:
        content: The document content to process
        mode: Processing mode ('summary' or 'issues')
        context: Optional context to guide analysis
        llm_client: The LLM client instance
        file_name: Name of the file being processed

    Returns:
        Tuple of (processed content, usage statistics)
    """
    # Use centralized digest prompts for unified analysis
    if mode == "summary":
        if context:
            context_instruction = PROMPTS.get(
                "processing.digest.summary_mode_context_instruction_with_context",
                context=context,
            )
        else:
            context_instruction = PROMPTS.get(
                "processing.digest.summary_mode_context_instruction_no_context"
            )

        digest_prompt = PROMPTS.get(
            "processing.digest.summary_mode", context_instruction=context_instruction
        )
        base_prompt = PROMPTS.get("analysis.chunk_processing.digest_prompt").format(
            digest_prompt=digest_prompt, chunk=content
        )
        system_prompt = PROMPTS.get("processing.digest.system_prompt")
    else:  # issues mode
        if context:
            context_instruction = PROMPTS.get(
                "processing.digest.issues_mode_context_instruction_with_context",
                context=context,
            )
        else:
            context_instruction = PROMPTS.get(
                "processing.digest.issues_mode_context_instruction_no_context"
            )

        digest_prompt = PROMPTS.get(
            "processing.digest.issues_mode", context_instruction=context_instruction
        )
        base_prompt = PROMPTS.get("analysis.chunk_processing.digest_prompt").format(
            digest_prompt=digest_prompt, chunk=content
        )
        system_prompt = PROMPTS.get("processing.digest.system_prompt")

    # Call the LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": base_prompt},
    ]

    try:
        log_task_event(
            "digest",
            "processing",
            "llm_call",
            "Sending single chunk to LLM",
            {"model": llm_client.model, "mode": mode}
        )
    except Exception:
        pass
    
    result = llm_client.complete(messages)
    
    try:
        log_task_event(
            "digest",
            "processing",
            "llm_response",
            "Single chunk LLM response received",
            {"model": llm_client.model}
        )
    except Exception:
        pass
    
    return result


def process_multiple_chunks(
    chunks: List[str],
    mode: str,
    context: Optional[str],
    llm_client: Any,
    file_name: str,
) -> Tuple[List[str], int, int, List[str]]:
    """
    Process multiple document chunks sequentially.

    Args:
        chunks: List of document chunks to process
        mode: Processing mode ('summary' or 'issues')
        context: Optional context to guide analysis
        llm_client: The LLM client instance
        file_name: Name of the file being processed

    Returns:
        Tuple of (chunk outputs, total prompt tokens, total completion tokens, errors)
    """
    chunk_outputs = []
    chunk_errors = []
    total_prompt_tokens = 0
    total_completion_tokens = 0

    for i, chunk in enumerate(chunks, 1):
        try:
            click.echo(f"  Processing chunk {i}/{len(chunks)}...")

            # Build prompt based on mode
            if mode == "summary":
                chunk_prompt = PROMPTS.get(
                    "processing.digest.chunk_analysis_summary",
                    chunk_num=i,
                    total_chunks=len(chunks),
                    context=context or "all relevant topics",
                    documents=chunk,
                )
                system_prompt = PROMPTS.get("processing.digest.system_prompt")
            else:  # issues mode
                chunk_prompt = PROMPTS.get(
                    "processing.digest.chunk_analysis_issues",
                    chunk_num=i,
                    total_chunks=len(chunks),
                    context=context or "all legal issues",
                    documents=chunk,
                )
                system_prompt = PROMPTS.get("processing.digest.system_prompt")

            # Process chunk
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chunk_prompt},
            ]

            try:
                log_task_event(
                    "digest",
                    "chunk_processing",
                    "llm_call",
                    f"Processing chunk {i}/{len(chunks)}",
                    {"model": llm_client.model, "chunk": i, "total": len(chunks)}
                )
            except Exception:
                pass
            
            chunk_response, chunk_usage = llm_client.complete(messages)
            
            try:
                log_task_event(
                    "digest",
                    "chunk_processing",
                    "llm_response",
                    f"Chunk {i}/{len(chunks)} complete",
                    {"model": llm_client.model}
                )
            except Exception:
                pass

            # Format chunk output
            formatted_output = format_chunk_output(i, len(chunks), chunk_response, mode)
            chunk_outputs.append(formatted_output)

            # Track usage
            total_prompt_tokens += chunk_usage.get("prompt_tokens", 0)
            total_completion_tokens += chunk_usage.get("completion_tokens", 0)

        except NonRetryableAPIError as e:
            error_msg = f"[ERROR] Chunk {i} failed: {str(e)}"
            click.echo(click.style(error_msg, fg="red"))
            chunk_outputs.append(f"\n[Chunk {i} - FAILED]\nError: {str(e)}\n")
            chunk_errors.append(error_msg)
        except Exception as e:
            error_msg = f"[ERROR] Chunk {i} failed with unexpected error: {str(e)}"
            click.echo(click.style(error_msg, fg="red"))
            chunk_outputs.append(
                f"\n[Chunk {i} - FAILED]\nUnexpected error: {str(e)}\n"
            )
            chunk_errors.append(error_msg)

    return chunk_outputs, total_prompt_tokens, total_completion_tokens, chunk_errors


def format_chunk_output(
    chunk_num: int, total_chunks: int, content: str, mode: str
) -> str:
    """
    Format the output for a single chunk.

    Args:
        chunk_num: The chunk number
        total_chunks: Total number of chunks
        content: The processed content
        mode: Processing mode

    Returns:
        Formatted output string
    """
    header = f"\n{'=' * 50}\n"
    header += f"Chunk {chunk_num}/{total_chunks}"
    if mode == "summary":
        header += " - Summary"
    else:
        header += " - Issues Identified"
    header += f"\n{'=' * 50}\n"

    return header + content


def consolidate_chunk_outputs(
    chunk_outputs: List[str], mode: str, llm_client: Any, context: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Consolidate multiple chunk outputs into a final summary.

    Args:
        chunk_outputs: List of processed chunk outputs
        mode: Processing mode
        llm_client: The LLM client instance
        context: Optional context

    Returns:
        Tuple of (consolidated output, usage statistics)
    """
    combined_chunks = "\n".join(chunk_outputs)

    # Build consolidation prompt
    consolidation_prompt = PROMPTS.get(
        f"processing.digest.consolidation_{mode}",
        chunk_analyses=combined_chunks,
        total_chunks=len(chunk_outputs),
        context=context or "comprehensive analysis",
    )
    system_prompt = PROMPTS.get("processing.digest.system_prompt")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": consolidation_prompt},
    ]

    try:
        log_task_event(
            "digest",
            "consolidation",
            "llm_call",
            "Sending consolidation prompt to LLM",
            {"model": llm_client.model, "mode": mode}
        )
    except Exception:
        pass
    
    result = llm_client.complete(messages)
    
    try:
        log_task_event(
            "digest",
            "consolidation",
            "llm_response",
            "Consolidation LLM response received",
            {"model": llm_client.model}
        )
    except Exception:
        pass
    
    return result


def validate_citations_if_needed(
    content: str, mode: str, llm_client: Any
) -> Tuple[str, Optional[List[str]]]:
    """
    Validate citations in content if in issues mode.

    Args:
        content: The content to validate
        mode: Processing mode
        llm_client: The LLM client instance

    Returns:
        Tuple of (validated content, list of issues or None)
    """
    if mode == "issues":  # Legal issues mode is more likely to contain citations
        try:
            try:
                log_task_event(
                    "digest",
                    "citation_validation",
                    "start",
                    "Starting citation validation"
                )
            except Exception:
                pass
            
            validated_content, issues = llm_client.validate_and_verify_citations(
                content,
                strict_mode=False,  # Lenient for digest
            )
            
            try:
                log_task_event(
                    "digest",
                    "citation_validation",
                    "end",
                    f"Citation validation complete - {len(issues) if issues else 0} issues found"
                )
            except Exception:
                pass
            
            return validated_content, issues
        except Exception as e:
            # Don't fail digest for citation issues
            click.echo(
                click.style(f"Citation validation skipped: {str(e)}", fg="yellow")
            )
            return content, None

    return content, None
