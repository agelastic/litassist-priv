"""
Markdown formatting functions for different log types.

Specialized formatters for citation verification, LLM messages, fetch logs, etc.
"""

import json
import time


def write_citation_verification_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for citation verification logs."""
    f.write(f"# {tag}  {ts}\n\n")

    # Summary section
    f.write("## Summary\n\n")
    f.write(f"- **Method**: `{payload.get('method', 'N/A')}`  \n")
    f.write(
        f"- **Input Text Length**: {payload.get('input_text_length', 0)} characters  \n"
    )
    f.write(f"- **Citations Found**: {payload.get('citations_found', 0)}  \n")
    f.write(f"- **Verified**: {payload.get('citations_verified', 0)}  \n")
    f.write(f"- **Unverified**: {payload.get('citations_unverified', 0)}  \n")
    f.write(f"- **Processing Time**: {payload.get('processing_time_ms', 'N/A')} ms  \n")
    f.write(f"- **Timestamp**: {payload.get('timestamp', ts)}  \n\n")

    # Verified citations
    verified = payload.get("verified_citations", [])
    if verified:
        f.write("## Verified Citations\n\n")
        for citation in verified:
            f.write(f"- `{citation}`  \n")
        f.write("\n")

    # Unverified citations
    unverified = payload.get("unverified_citations", [])
    if unverified:
        f.write("## Unverified Citations\n\n")
        for item in unverified:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                citation, reason = item[0], item[1]
                f.write(f"- `{citation}`  \n")
                f.write(f"  - **Reason**: {reason}  \n")
            else:
                f.write(f"- `{item}`  \n")
        f.write("\n")

    # Settings
    f.write("## Settings\n\n")
    settings = payload.get("settings", {})
    f.write(f"- **Strict Mode**: {settings.get('strict_mode', 'N/A')}  \n")
    f.write(f"- **Cache Used**: {settings.get('cache_used', 'N/A')}  \n")
    f.write(f"- **API Calls Made**: {settings.get('api_calls_made', 'N/A')}  \n\n")

    # Errors if any
    errors = payload.get("errors", [])
    if errors:
        f.write("## Errors\n\n")
        for error in errors:
            f.write(f"- {error}  \n")
        f.write("\n")


def write_citation_validation_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for citation validation logs."""
    f.write(f"# {tag}  {ts}\n\n")
    f.write("## Summary\n\n")
    f.write(
        f"- **Method**: `{payload.get('method', 'validate_citation_patterns')}`  \n"
    )
    issues = payload.get("issues", [])
    f.write(f"- **Issues Found**: {len(issues)}  \n")
    f.write(f"- **Online Enabled**: {payload.get('online_enabled', False)}  \n")
    f.write(f"- **Timestamp**: {payload.get('timestamp', ts)}  \n\n")

    if issues:
        f.write("## Issues\n\n")
        for issue in issues:
            f.write(f"- {issue}  \n")
        f.write("\n")


def write_http_validation_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for HTTP validation logs."""
    f.write(f"# {tag}  {ts}\n\n")
    f.write("## HTTP Validation\n\n")
    f.write(f"- **Method**: `{payload.get('method', 'check_url_exists')}`  \n")
    f.write(f"- **URL**: `{payload.get('url', 'N/A')}`  \n")
    f.write(f"- **Status Code**: {payload.get('status_code', 'N/A')}  \n")
    f.write(f"- **Valid**: {payload.get('valid', False)}  \n")
    if payload.get("error"):
        f.write(f"- **Error**: {payload.get('error')}  \n")
    f.write("\n")


def write_search_validation_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for search validation logs."""
    f.write(f"# {tag}  {ts}\n\n")
    f.write("## Search Validation\n\n")
    f.write("- **Method**: `search_austlii`  \n")
    f.write(f"- **Citation**: `{payload.get('citation', 'N/A')}`  \n")
    f.write(f"- **Found**: {payload.get('found', False)}  \n")
    if payload.get("url"):
        f.write(f"- **URL**: {payload.get('url')}  \n")
    f.write("\n")


def write_command_output_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for command output logs."""
    f.write(f"# {tag}  {ts}\n\n")

    # Inputs section
    if "inputs" in payload:
        f.write("## Inputs\n\n")
        inputs = payload["inputs"]
        if isinstance(inputs, dict):
            for key, value in inputs.items():
                # Special handling for complex data structures
                if isinstance(value, dict):
                    # Check for research_analysis with combined_content
                    if key == "research_analysis" and "combined_content" in value:
                        # Only log metadata, not the massive content
                        f.write(f"- **{key}**:\n")
                        f.write(
                            f"  - Total tokens: {value.get('total_tokens', 'N/A')}\n"
                        )
                        f.write(f"  - Total words: {value.get('total_words', 'N/A')}\n")
                        f.write(f"  - File count: {value.get('file_count', 'N/A')}\n")
                        f.write(
                            f"  - Exceeds threshold: {value.get('exceeds_threshold', 'N/A')}\n"
                        )
                    else:
                        # Format dict as JSON code block
                        f.write(
                            f"- **{key}**:\n```json\n{json.dumps(value, indent=2, ensure_ascii=False)}\n```\n"
                        )
                elif isinstance(value, list):
                    if len(value) > 10:
                        # For long lists, show count and first few items
                        f.write(f"- **{key}**: {len(value)} items\n")
                        f.write(f"  First 3: {value[:3]}\n")
                    else:
                        # Short lists can be shown inline
                        f.write(f"- **{key}**: {value}  \n")
                elif isinstance(value, str) and len(value) > 1000:
                    # Truncate very long strings
                    f.write(
                        f"- **{key}**: {value[:500]}... (truncated, {len(value)} chars total)  \n"
                    )
                else:
                    # Simple values
                    f.write(f"- **{key}**: {value}  \n")
        else:
            f.write(f"{inputs}  \n")
        f.write("\n")

    # Response section
    if "response" in payload:
        f.write("## Response\n\n")
        response = payload["response"]
        # Handle long responses
        if isinstance(response, str) and len(response) > 10000:
            f.write(
                f"{response[:10000]}\n\n... (truncated, {len(response)} total characters)\n"
            )
        else:
            f.write(f"{response}\n")
        f.write("\n")

    # Usage statistics
    if "usage" in payload:
        f.write("## Usage Statistics\n\n")
        usage = payload["usage"]
        if isinstance(usage, dict):
            for key, value in usage.items():
                f.write(f"- **{key}**: {value}  \n")
        f.write("\n")


def write_llm_messages_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for LLM message logs."""
    f.write(f"# {tag}  {ts}\n\n")

    # Model information
    f.write("## Model Information\n\n")
    f.write(f"- **Model**: {payload.get('model', 'N/A')}\n")
    f.write(f"- **Timestamp**: {payload.get('timestamp', ts)}\n")
    if "correlation_id" in payload:
        f.write(f"- **Correlation ID**: {payload['correlation_id']}\n")
    if "command_context" in payload:
        f.write(f"- **Context**: {payload['command_context']}\n")
    f.write("\n")

    # Messages - check both 'messages' and 'messages_sent' for compatibility
    messages = payload.get("messages", payload.get("messages_sent", []))
    if messages:
        f.write("## Messages Sent\n\n")
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "system":
                f.write("### System Message\n\n")
            elif role == "user":
                f.write("### User Message\n\n")
            elif role == "assistant":
                f.write("### Assistant Message\n\n")
            else:
                f.write(f"### {role.title()} Message\n\n")

            # Handle long content
            if len(content) > 50000:
                f.write(
                    f"{content[:50000]}\n\n[... truncated, {len(content)} total characters ...]\n\n"
                )
            else:
                f.write(f"{content}\n\n")

    # LLM Response - the actual output from the model
    response = payload.get("response")
    if response:
        f.write("## LLM Response\n\n")
        # Handle very long responses (some can be 50K+ chars)
        if len(response) > 100000:
            f.write(
                f"{response[:100000]}\n\n[... truncated, {len(response)} total characters ...]\n\n"
            )
        else:
            f.write(f"{response}\n\n")

    # Parameters
    params = payload.get("params", {})
    if params:
        f.write("## Parameters\n\n")
        f.write("| Parameter | Value |\n")
        f.write("|-----------|-------|\n")
        for key, value in params.items():
            f.write(f"| {key} | {value} |\n")
        f.write("\n")

    # Usage stats if present
    usage = payload.get("usage", {})
    if usage:
        f.write("## Token Usage\n\n")
        for key, value in usage.items():
            f.write(f"- **{key}**: {value}\n")
        f.write("\n")


def format_dict_as_markdown(d: dict, indent: int = 0) -> str:
    """Recursively format a dictionary as markdown lists."""
    lines = []
    prefix = "  " * indent + "- "

    for key, value in d.items():
        if isinstance(value, dict):
            lines.append(f"{prefix}**{key}**:")
            lines.append(format_dict_as_markdown(value, indent + 1))
        elif isinstance(value, list):
            lines.append(f"{prefix}**{key}**:")
            for item in value:
                if isinstance(item, dict):
                    lines.append(format_dict_as_markdown(item, indent + 1))
                else:
                    lines.append(f"  {'  ' * indent}- {item}")
        else:
            lines.append(f"{prefix}**{key}**: {value}")

    return "\n".join(lines)


def write_fetch_log_markdown(f, tag: str, ts: str, payload: dict):
    """Write markdown for fetch attempt logs."""
    f.write(f"# {tag}  {ts}\n\n")

    # Summary section
    f.write("## Fetch Summary\n\n")
    f.write(f"- **URL**: `{payload.get('url', 'N/A')}`  \n")
    if payload.get("original_url"):
        f.write(f"- **Original URL**: `{payload.get('original_url')}`  \n")
    f.write(f"- **Method**: `{payload.get('method', 'N/A')}`  \n")
    f.write(f"- **Status**: `{payload.get('status', 'N/A')}`  \n")
    if payload.get("reason"):
        f.write(f"- **Reason**: {payload.get('reason')}  \n")
    if payload.get("error"):
        f.write(f"- **Error**: {payload.get('error')}  \n")
    f.write(
        f"- **Timestamp**: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload.get('timestamp', time.time())))}  \n\n"
    )

    # Size statistics
    if any(
        k in payload
        for k in ["html_size", "extracted_size", "final_size", "jina_response_size"]
    ):
        f.write("## Size Statistics\n\n")
        if payload.get("html_size"):
            f.write(f"- **HTML Size**: {payload['html_size']:,} chars  \n")
        if payload.get("jina_response_size"):
            f.write(
                f"- **Jina Response Size**: {payload['jina_response_size']:,} chars  \n"
            )
        if payload.get("extracted_size"):
            f.write(f"- **Extracted Size**: {payload['extracted_size']:,} chars  \n")
        if payload.get("final_size"):
            f.write(f"- **Final Size**: {payload['final_size']:,} chars  \n")
        if payload.get("reduction_percent"):
            f.write(f"- **Reduction**: {payload['reduction_percent']}%  \n")
        if payload.get("pdf_pages"):
            f.write(f"- **PDF Pages**: {payload['pdf_pages']} total  \n")
        if payload.get("pages_extracted"):
            f.write(f"- **Pages Extracted**: {payload['pages_extracted']}  \n")
        f.write("\n")

    # Content section
    content = payload.get("content", "")
    if content:
        f.write("## Scraped Content\n\n")
        # Write FULL content - no truncation for legal compliance
        f.write("```text\n")
        f.write(content)
        f.write("\n```\n")
    elif payload.get("status") == "failed":
        f.write("## Content\n\nFetch failed - no content retrieved.\n")
    elif payload.get("status") == "skipped":
        f.write("## Content\n\nFetch skipped - no content retrieved.\n")

    f.write("\n")


def write_generic_markdown(f, tag: str, ts: str, payload: dict):
    """Write pure markdown for unknown log types - no JSON."""
    f.write(f"# {tag}  {ts}\n\n")
    f.write("## Log Data\n\n")

    # Convert the payload to pure markdown format
    if payload:
        markdown_content = format_dict_as_markdown(payload)
        f.write(markdown_content)
        f.write("\n")
    else:
        f.write("No data available.\n")
