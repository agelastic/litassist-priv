"""
Truncation utilities for managing document size when hitting LLM token limits.
Uses drop-largest strategy to maximize content retention.
"""

from typing import List, Tuple, Optional, Callable, Any
import click


class TruncationManager:
    """Manages document truncation for LLM token limits using drop-largest strategy."""
    
    def __init__(self, documents: List[Tuple[str, str]], max_attempts: Optional[int] = None):
        """
        Initialize truncation manager with documents to manage.
        
        Args:
            documents: List of (name, content) tuples
            max_attempts: Maximum retry attempts (default: None for unlimited)
        """
        self.documents = list(documents)  # Make a copy to avoid modifying original
        self.dropped = []
        self.max_attempts = max_attempts
        self.attempt = 0
    
    def drop_largest(self) -> Optional[str]:
        """
        Drop the largest document by content size.
        
        Returns:
            Name of dropped document, or None if no documents left
        """
        if not self.documents:
            return None
        
        # Find largest document by content length (index 1 in tuple)
        largest_idx = max(
            range(len(self.documents)), 
            key=lambda i: len(self.documents[i][1])
        )
        dropped = self.documents.pop(largest_idx)
        self.dropped.append(dropped)
        return dropped[0]  # Return the name
    
    def get_documents(self) -> List[Tuple[str, str]]:
        """Get current list of documents that haven't been dropped."""
        return self.documents
    
    def get_dropped(self) -> List[Tuple[str, str]]:
        """Get list of documents that have been dropped."""
        return self.dropped
    
    def can_retry(self) -> bool:
        """
        Check if we can retry (have attempts left and documents to drop).
        
        Returns:
            True if retry is possible, False otherwise
        """
        if self.max_attempts is None:
            return bool(self.documents)
        return self.attempt < self.max_attempts and bool(self.documents)
    
    @staticmethod
    def is_token_error(error: Exception) -> bool:
        """
        Check if an exception is a token/context limit error.
        
        Args:
            error: Exception to check
            
        Returns:
            True if this appears to be a token limit error
        """
        error_str = str(error).lower()
        token_error_keywords = [
            'token', 'context', 'length', 'too long', 'maximum',
            'exceeded', 'limit', 'too many tokens'
        ]
        return any(keyword in error_str for keyword in token_error_keywords)


def execute_with_truncation(
    client: Any,
    build_prompt_fn: Callable[[List[Tuple[str, str]]], str],
    documents: List[Tuple[str, str]],
    execute_fn: Optional[Callable] = None,
    warning_fn: Optional[Callable] = None,
    log_fn: Optional[Callable] = None,
    system_content: Optional[str] = None
) -> Tuple[Any, Any]:
    """
    Execute LLM call with automatic truncation on token errors.
    
    This function will retry LLM calls that fail due to token limits by
    progressively dropping the largest documents until the call succeeds
    or no documents remain.
    
    Args:
        client: LLM client instance
        build_prompt_fn: Function that takes documents list and returns prompt string
        documents: List of (name, content) tuples to include in prompt
        execute_fn: Optional custom execution function, defaults to client.complete()
        warning_fn: Optional function to display warnings (e.g., click.echo)
        log_fn: Optional function for logging dropped documents
        system_content: Optional system prompt to include in LLM call
    
    Returns:
        Tuple of (response, usage) from the LLM call
        
    Raises:
        Exception: If all documents are dropped and call still fails,
                   or if a non-token-limit error occurs
    """
    from litassist.utils.formatting import warning_message, info_message
    
    manager = TruncationManager(documents)
    
    # Default execution function if none provided
    if execute_fn is None:
        def default_execute(prompt):
            messages = []
            if system_content:
                messages.append({"role": "system", "content": system_content})
            messages.append({"role": "user", "content": prompt})
            return client.complete(messages)
        execute_fn = default_execute
    
    while manager.can_retry():
        try:
            # Build prompt with current set of documents
            prompt = build_prompt_fn(manager.get_documents())
            
            # Execute LLM call
            result = execute_fn(prompt)
            return result
            
        except Exception as e:
            if manager.is_token_error(e):
                # Drop the largest document and retry
                dropped_name = manager.drop_largest()
                if dropped_name:
                    # Display warning about dropped document
                    warning_msg = warning_message(
                        f"Prompt exceeded token limit. Dropping largest document: {dropped_name}"
                    )
                    if warning_fn:
                        warning_fn(warning_msg)
                    else:
                        click.echo(warning_msg)
                    
                    # Show progress if documents remain
                    if manager.documents:
                        # Calculate estimated tokens for remaining documents
                        remaining_chars = sum(len(content) for _, content in manager.documents)
                        estimated_tokens = remaining_chars / 4
                        
                        click.echo(info_message(
                            f"Retrying with {len(manager.documents)} documents remaining "
                            f"(~{int(estimated_tokens):,} tokens)..."
                        ))
                    
                    # Log the drop if logging function provided
                    if log_fn:
                        log_fn(
                            dropped_name, 
                            [doc[0] for doc in manager.get_documents()],
                            manager.attempt + 1
                        )
                
                manager.attempt += 1
            else:
                # Not a token error, re-raise the original exception
                raise
    
    # Exhausted all retries
    if not manager.documents:
        raise Exception("Failed to get LLM response after dropping all documents")
    else:
        raise Exception(
            f"Failed after {manager.attempt} attempts. "
            f"Dropped {len(manager.dropped)} documents, {len(manager.documents)} remaining"
        )