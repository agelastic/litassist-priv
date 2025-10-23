"""
Emergency save functionality for digest command.

This module handles emergency saving of partial results when
the digest process is interrupted or fails.
"""

import sys
import atexit
import signal
from typing import Dict, Any, Optional
from litassist.logging import save_command_output


class EmergencySaveHandler:
    """
    Handler for emergency saving of digest results.

    Saves partial results when the process is interrupted by
    Ctrl+C, system signals, or unexpected errors.
    """

    def __init__(self):
        """Initialize the emergency save handler."""
        self.metadata = {}
        self.partial_output = []
        self.enabled = False
        self.output_prefix = None

    def setup(self, metadata: Dict[str, Any], output_prefix: Optional[str] = None):
        """
        Set up emergency save handlers.

        Args:
            metadata: Metadata about the digest operation
            output_prefix: Optional output file prefix
        """
        self.metadata = metadata
        self.output_prefix = output_prefix or "digest"
        self.enabled = True

        # Register signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Register exit handler
        atexit.register(self._emergency_save)

    def update_output(self, content: str):
        """
        Update the partial output with new content.

        Args:
            content: New content to add to partial output
        """
        if self.enabled:
            self.partial_output.append(content)

    def update_metadata(self, key: str, value: Any):
        """
        Update metadata for emergency save.

        Args:
            key: Metadata key
            value: Metadata value
        """
        if self.enabled:
            self.metadata[key] = value

    def disable(self):
        """Disable emergency save (used when completing normally)."""
        self.enabled = False
        # Unregister handlers
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)

    def _handle_signal(self, signum, frame):
        """
        Handle interrupt signals.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        if self.enabled and self.partial_output:
            # Use stderr for last-resort logging as stdout may be redirected
            print("\n[INTERRUPTED] Attempting emergency save...", file=sys.stderr)
            self._emergency_save()
        sys.exit(1)

    def _emergency_save(self):
        """Perform emergency save of partial results."""
        if not self.enabled or not self.partial_output:
            return

        try:
            # Combine partial output
            emergency_content = "\n".join(self.partial_output)

            # Add emergency header
            header = "=" * 80 + "\n"
            header += "EMERGENCY SAVE - PARTIAL RESULTS\n"
            header += "Process was interrupted. These are incomplete results.\n"
            header += "=" * 80 + "\n\n"

            # Add metadata
            if self.metadata:
                header += "Metadata:\n"
                for key, value in self.metadata.items():
                    header += f"  {key}: {value}\n"
                header += "\n"

            full_content = header + emergency_content

            # Save to file
            output_file = save_command_output(
                f"{self.output_prefix}_emergency",
                full_content,
                "",
                metadata=self.metadata,
            )

            print(f"[SAVED] Emergency output saved to: {output_file}", file=sys.stderr)

        except Exception as e:
            print(f"[ERROR] Emergency save failed: {e}", file=sys.stderr)
        finally:
            # Disable to prevent double-save
            self.enabled = False


def create_emergency_handler() -> EmergencySaveHandler:
    """
    Create and return a new emergency save handler.

    Returns:
        EmergencySaveHandler instance
    """
    return EmergencySaveHandler()
