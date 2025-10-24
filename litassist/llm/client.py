"""
LLM Client for LitAssist.

This module provides a unified interface for chat completions across different LLM providers,
handling parameter management and response processing.
"""

import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple

from litassist.timing import timed
from litassist.logging import save_log
from litassist.utils.core import heartbeat
from litassist.utils.formatting import success_message
from litassist.config import get_config
from litassist.prompts import PROMPTS
from litassist.citation.exceptions import CitationVerificationError

from .api_handlers import execute_api_call_with_retry
from .verification import LLMVerificationMixin
from .response_parser import extract_content_and_usage
from .retry_handler import handle_citation_retry
from .citation_handler import process_citation_verification, handle_retry_failure
from .tools import get_tool_definitions, execute_tool, format_tool_response
from .parameter_handler import (
    get_model_family,
    get_model_parameters,
    supports_system_messages,
)


logger = logging.getLogger(__name__)


# Parameter handling functions now imported from parameter_handler.py
# Model configuration data imported from model_profiles.py

class LLMClient(LLMVerificationMixin):
    """
    Wrapper for LLM API calls with support for completions and self-verification.

    This class provides a unified interface for chat completions across different LLM
    providers, handling parameter management and response processing. It supports both
    creative (high temperature) and deterministic (low temperature) generation, as well
    as legal self-critique verification.

    Attributes:
        model: The model identifier to use for completions (e.g., 'openai/gpt-4o').
        default_params: Default parameters dictionary for completions.

    Example:
        ```python
        # Initialize client with default parameters
        client = LLMClient("anthropic/claude-sonnet-4", temperature=0.2, top_p=0.8)

        # Run a completion
        content, usage = client.complete([
            {"role": "system", "content": "Australian law only."},
            {"role": "user", "content": "Explain adverse possession."}
        ])

        # Optional verification
        if needs_verification:
            corrections = client.verify(content)
        ```
    """

    def __init__(self, model: str, **default_params):
        """
        Initialize an LLM client for chat completions.

        Args:
            model: The model name to use (e.g., 'openai/gpt-4o', 'anthropic/claude-sonnet-4').
            **default_params: Default decoding parameters (temperature, top_p, etc.) to use
                             for all completions unless overridden.
        """
        self.model = model
        self.command_context = None  # Track which command is using this client

        # Set token limit from config if enabled and not explicitly specified
        config = get_config()
        if config.use_token_limits:
            # Determine if we need to transform max_tokens to another parameter
            test_params = {"max_tokens": 1}
            filtered = get_model_parameters(model, test_params)
            token_param = (
                "max_completion_tokens"
                if "max_completion_tokens" in filtered
                else "max_tokens"
            )

            if token_param not in default_params:
                # Use token limit from config
                default_params[token_param] = config.token_limit

        self.default_params = default_params
        self._client = None  # Will be created when needed

    # Add heartbeat messages so users see progress during lengthy LLM calls
    # The verification helpers already had their own heartbeat wrapper, but that
    # resulted in progress messages only during the verification stage.  By
    # moving the heartbeat decorator to the main `complete` method we ensure
    # that all long-running LLM invocations – including the initial content
    # generation used by commands such as `extractfacts` – emit "…still working,
    # please wait…" notifications.  Down-stream helpers that themselves call
    # `complete` therefore no longer need their own heartbeat wrappers.
    def _format_date_string(self):
        """Get current date formatted for prompt injection."""
        import pytz

        sydney_tz = pytz.timezone("Australia/Sydney")
        return datetime.now(sydney_tz).strftime("%B %d, %Y")

    def _prepare_messages_for_model(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Prepare messages based on model's system message support."""
        if not supports_system_messages(self.model):
            # For o1/o3 models - merge system into first user message
            return self._merge_system_into_user(messages)
        else:
            # For all other models - add Australian law to system messages
            return self._add_australian_law_to_system(messages)

    def _merge_system_into_user(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Merge system messages into first user message for o1/o3 models."""
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        non_system_messages = [msg for msg in messages if msg.get("role") != "system"]

        if not system_messages:
            # No system messages to merge
            return messages

        # Combine all system content
        system_content = "\n".join([msg.get("content", "") for msg in system_messages])
        if "Australian English" not in system_content:
            system_content += "\n" + PROMPTS.get("base.australian_law")

        # Find first user message and prepend system content
        modified_messages = []
        for i, msg in enumerate(non_system_messages):
            if msg.get("role") == "user":
                content = f"{system_content}\n\n{msg.get('content', '')}"
                modified_messages.append({"role": "user", "content": content})
                modified_messages.extend(non_system_messages[i + 1 :])
                return modified_messages

        # No user message found - just return non-system messages
        return non_system_messages

    def _add_australian_law_to_system(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Add Australian law prompt to system messages."""
        australian_law = PROMPTS.get("base.australian_law")
        if not australian_law:
            return messages

        modified_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                # Only add if not already present
                if australian_law not in content:
                    content = f"{australian_law}\n\n{content}"
                modified_messages.append({"role": "system", "content": content})
            else:
                modified_messages.append(msg)

        return modified_messages

    def _add_date_instruction(
        self, messages: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """Add appropriate date instruction based on tool availability."""
        if getattr(self, "_disable_tools", False):
            # Tools disabled - inject date directly
            today_date = self._format_date_string()
            date_text = PROMPTS.get("base.date_fallback_instruction").format(
                date=today_date
            )
        else:
            # Tools enabled - use tool instruction
            date_text = PROMPTS.get("base.date_tool_instruction")

        # Add to first system or user message
        modified_messages = []
        date_added = False

        for msg in messages:
            if not date_added and msg.get("role") in ["system", "user"]:
                content = msg.get("content", "")
                content = f"{date_text}\n\n{content}"
                modified_messages.append({"role": msg["role"], "content": content})
                date_added = True
            else:
                modified_messages.append(msg)

        return modified_messages

    # The enclosing `complete` method now emits heartbeat updates, so we no
    # longer need a second heartbeat layer here. Retaining only the timing
    # decorator avoids duplicated progress messages.
    @heartbeat()  # Uses heartbeat_interval from config.yaml
    @timed
    def complete(
        self,
        messages: List[Dict[str, str]],
        skip_citation_verification: bool = False,
        **overrides,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Run a single chat completion with the configured model.

        Args:
            messages: List of message dictionaries, each containing 'role' (system/user/assistant)
                     and 'content' (the message text).
            skip_citation_verification: If True, bypass the citation verification step.
            **overrides: Optional parameter overrides for this specific completion that will
                        take precedence over the default parameters.

        Returns:
            A tuple containing:
                - The generated text content (str)
                - The usage statistics dictionary (with prompt_tokens, completion_tokens, etc.)

        Raises:
            Exception: If the API call fails or returns an error.
        """
        # Step 1: Handle model-specific message formatting
        messages = self._prepare_messages_for_model(messages)

        # Step 2: Add date instruction (tool or direct based on disable_tools)
        messages = self._add_date_instruction(messages)

        # Merge default and override parameters
        params = {**self.default_params, **overrides}

        # Determine the correct model name
        model_name = self.model

        # Extract just the model name for direct OpenAI models
        if (
            self.model.startswith("openai/")
            and "/" in self.model
            and not get_model_family(self.model) == "openai_reasoning"
        ):
            model_name = self.model.replace("openai/", "")

        try:
            # Filter parameters based on model capabilities
            filtered_params = get_model_parameters(self.model, params)

            # Check if tools should be disabled for this client
            if getattr(self, "_disable_tools", False):
                # Date has already been injected by _add_date_instruction at line 966
                logging.info(
                    f"Tools disabled for {self.model}, using date injection fallback"
                )

                # Log the prepared messages
                save_log(
                    f"llm_{self.model.replace('/', '_')}_messages",
                    {
                        "model": self.model,
                        "messages_sent": messages,  # Use already-prepared messages
                        "params": filtered_params,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "tools_disabled": True,
                    },
                )

                # Call API without tools using prepared messages
                response = execute_api_call_with_retry(
                    model_name, messages, filtered_params
                )
            else:
                # Add tool definitions for date handling
                tools = get_tool_definitions()

                # Add tools to parameters (most models support this)
                # We'll try with tools, and fall back without if it fails
                filtered_params_with_tools = filtered_params.copy()
                filtered_params_with_tools["tools"] = tools
                # Let the model decide when to call tools (follows "MUST" instruction in prompt)

                # Log the final messages being sent to the API
                save_log(
                    f"llm_{self.model.replace('/', '_')}_messages",
                    {
                        "model": self.model,
                        "messages_sent": messages,
                        "params": filtered_params_with_tools,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )

                # Use ChatCompletion API with retry logic - try with tools first
                try:
                    response = execute_api_call_with_retry(
                        model_name, messages, filtered_params_with_tools
                    )

                    # Check if response is empty (some models don't support forced tool calls)
                    if (
                        hasattr(response, "choices")
                        and response.choices
                        and hasattr(response.choices[0], "message")
                        and not response.choices[0].message.content
                        and not getattr(response.choices[0].message, "tool_calls", None)
                    ):
                        # Empty response - model doesn't support forced tools
                        # Fall back to regular call without tools
                        logging.info(
                            f"Model {model_name} returned empty with forced tools, falling back"
                        )
                        response = execute_api_call_with_retry(
                            model_name, messages, filtered_params
                        )
                except Exception as e:
                    # If tools aren't supported, fall back to regular call
                    if "tools" in str(e).lower() or "tool_choice" in str(e).lower():
                        logging.info(
                            f"Model {model_name} doesn't support tools, falling back"
                        )

                        # Replace tool instruction with direct date injection in messages
                        fallback_messages = []
                        today_date = self._format_date_string()
                        date_fallback = PROMPTS.get(
                            "base.date_fallback_instruction"
                        ).format(date=today_date)
                        tool_instruction = PROMPTS.get("base.date_tool_instruction")

                        for msg in messages:
                            if msg.get("role") in [
                                "system",
                                "user",
                            ] and tool_instruction in msg.get("content", ""):
                                # Replace tool instruction with date fallback
                                new_content = msg["content"].replace(
                                    tool_instruction, date_fallback
                                )
                                fallback_messages.append(
                                    {"role": msg["role"], "content": new_content}
                                )
                            else:
                                fallback_messages.append(msg)

                        response = execute_api_call_with_retry(
                            model_name, fallback_messages, filtered_params
                        )
                    else:
                        raise

            # Check for errors in the response
            if (
                hasattr(response, "choices")
                and response.choices
                and hasattr(response.choices[0], "error")
                and response.choices[0].error
            ):
                error_info = response.choices[0].error
                error_msg = error_info.get("message", "Unknown API error")
                raise Exception(f"API Error: {error_msg}")

            # Check for error finish_reason
            if (
                hasattr(response, "choices")
                and response.choices
                and hasattr(response.choices[0], "finish_reason")
                and response.choices[0].finish_reason == "error"
            ):
                # Try to get error details
                if hasattr(response.choices[0], "error"):
                    error_info = response.choices[0].error
                    error_msg = error_info.get("message", "Unknown API error")
                    raise Exception(f"API request failed: {error_msg}")
                else:
                    raise Exception(
                        "API request failed with error finish_reason but no error details"
                    )

            # Validate response structure before accessing
            if not response:
                raise Exception("Empty response from API")

            if not hasattr(response, "choices") or not response.choices:
                # Log the actual response for debugging
                logging.error(f"Invalid API response structure: {response}")
                error_msg = "API response missing 'choices' field"
                if hasattr(response, "error") and response.error:
                    if hasattr(response.error, "get"):
                        error_msg = f"API error: {response.error.get('message', 'Unknown error')}"
                    else:
                        error_msg = f"API error: {response.error}"
                raise Exception(error_msg)

            if not hasattr(response.choices[0], "message"):
                raise Exception(f"Invalid choice structure: {response.choices[0]}")

            # Check if the response contains tool calls
            if (
                hasattr(response.choices[0].message, "tool_calls")
                and response.choices[0].message.tool_calls
            ):
                # Handle tool calls - wrap in try/except for test compatibility
                try:
                    tool_calls = response.choices[0].message.tool_calls

                    for tool_call in tool_calls:
                        tool_name = tool_call.function.name
                        # Execute the tool (we know it's the now() function)
                        tool_result = execute_tool(tool_name)

                        # Format the tool response for the model
                        tool_message = format_tool_response(tool_name, tool_result)

                        # Add tool response to messages for follow-up
                        messages.append(response.choices[0].message.model_dump())
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": tool_message,
                            }
                        )

                    # Make a follow-up call with the tool results
                    # This time without forcing tool use
                    filtered_params_followup = filtered_params.copy()
                    response = execute_api_call_with_retry(
                        model_name, messages, filtered_params_followup
                    )
                except (TypeError, AttributeError):
                    # In tests or if tool_calls is not properly formed, skip tool handling
                    logging.debug(
                        "Tool calls not available or malformed, skipping tool handling"
                    )

            # Extract content and usage from chat response
            content, usage = extract_content_and_usage(response)
        finally:
            # No cleanup needed with client instances
            pass

        if not skip_citation_verification:
            # Citation verification workflow
            try:
                content, verification_issues = process_citation_verification(
                    content=content, client_instance=self, skip_verification=False
                )

            except CitationVerificationError as e:
                # Strict mode failed - attempt retry with enhanced prompt
                try:
                    content, usage, retry_issues = handle_citation_retry(
                        error=e,
                        model=self.model,
                        model_name=model_name,
                        messages=messages,
                        params=params,
                        validate_func=self.validate_and_verify_citations,
                    )

                    # Display success message for fully verified retries
                    if not retry_issues:
                        try:
                            all_verified_msg = PROMPTS.get(
                                "warnings.all_citations_verified"
                            )
                        except (KeyError, ValueError):
                            all_verified_msg = success_message(
                                "Retry successful: All citations verified"
                            )
                        print(all_verified_msg)

                except CitationVerificationError as retry_error:
                    # Both attempts failed - this is a critical error
                    handle_retry_failure(retry_error)
                finally:
                    # No cleanup needed with client instances
                    pass

        # Normalize usage data so it can be safely serialized
        if hasattr(usage, "_asdict"):
            usage = usage._asdict()
        elif hasattr(usage, "to_dict"):
            usage = usage.to_dict()
        elif not isinstance(usage, dict):
            usage = {"raw": str(usage)}

        # Log the LLM call with optional CoVe stage identification
        log_tag = f"llm_{self.model.replace('/', '_')}"
        command_context = getattr(self, "command_context", None)

        # Use specific log tag for CoVe stages
        if command_context and "cove" in command_context:
            log_tag = f"{command_context}_{self.model.replace('/', '_')}"

        save_log(
            log_tag,
            {
                "method": "complete",
                "model": self.model,
                "command_context": command_context,
                "messages": messages,
                "params": {**self.default_params, **overrides},
                "response": content,
                "usage": usage,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
        )

        return content, usage
