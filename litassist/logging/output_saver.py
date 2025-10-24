"""
Command output file saving functionality.

Handles saving command outputs with standard formatting and metadata.
"""

import os
import re
import time
from typing import Dict, List, Optional, Tuple


def save_command_output(
    command_name: str,
    content: str,
    query_or_slug: str,
    metadata: Optional[Dict[str, str]] = None,
    critique_sections: Optional[List[Tuple[str, str]]] = None,
    output_dir: str = None,
) -> str:
    """
    Save command output with standard format.

    Args:
        command_name: Name of the command (e.g., 'strategy', 'draft')
        content: The main content to save
        query_or_slug: Query string or slug for filename generation
        metadata: Optional dict of metadata to include in header
        critique_sections: Optional list of (title, critique_content) tuples for AI critiques
        output_dir: Directory for output files (defaults to outputs/)

    Returns:
        Path to the saved output file
    """
    # Use provided output_dir or default
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "outputs")

    os.makedirs(output_dir, exist_ok=True)

    timestamp = time.strftime("%Y%m%d_%H%M%S")

    # Create filename based on whether a slug is provided
    slug = ""
    if query_or_slug:  # Non-empty slug means normal usage
        sanitized_slug = re.sub(r"[^\w\s-]", "", query_or_slug.lower())
        slug = re.sub(r"[-\s]+", "_", sanitized_slug)[:40].strip("_")

    if slug:
        output_file = os.path.join(output_dir, f"{command_name}_{slug}_{timestamp}.txt")
    else:
        # This handles both cases: empty query_or_slug, or a slug that becomes empty after sanitization.
        output_file = os.path.join(output_dir, f"{command_name}_{timestamp}.txt")

    with open(output_file, "w", encoding="utf-8") as f:
        # Standard header
        f.write(f"{command_name.replace('_', ' ').title()}\n")

        # Add metadata if provided
        if metadata:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")

        f.write(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 80 + "\n\n")
        f.write(content)

        # Append critique sections if provided
        if critique_sections:
            f.write("\n\n" + "=" * 80 + "\n")
            f.write("AI CRITIQUE & VERIFICATION\n")
            f.write("=" * 80 + "\n\n")

            for title, critique_content in critique_sections:
                f.write(f"## {title}\n\n")
                f.write(critique_content)
                f.write("\n\n")

    return output_file
