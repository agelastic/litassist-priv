"""
Utils module for LitAssist.

This module provides utility functions and classes organized into specialized submodules
for better maintainability and organization.
"""

# NOTE: Imports removed for performance - import directly from submodules instead
# e.g., from litassist.utils.formatting import success_message

# Re-export for backward compatibility
__all__ = [
    # Formatting
    "Colors",
    "colored_message",
    "success_message",
    "warning_message",
    "error_message",
    "info_message",
    "stats_message",
    "tip_message",
    "saved_message",
    "verifying_message",
    # File operations
    "read_document",
    "validate_file_size",
    "is_text_file",
    "validate_file_size_limit",
    # Text processing
    "create_embeddings",
    "count_tokens_and_words",
    "chunk_text",
    # Legal reasoning
    "LegalReasoningTrace",
    "create_reasoning_prompt",
    "extract_reasoning_trace",
    "save_reasoning_trace",
    "detect_factual_hallucinations",
    "verify_content_if_needed",
    # Core utilities
    "timed",
    "heartbeat",
    "show_command_completion",
    "parse_strategies_file",
    "validate_side_area_combination",
    # Logging utilities
    "OUTPUT_DIR",
    "save_log",
    "save_command_output",
    # Truncation utilities
    "TruncationManager",
    "execute_with_truncation",
]
