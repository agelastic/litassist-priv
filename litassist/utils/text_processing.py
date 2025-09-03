"""
Text processing utilities.

This module provides functions for text embedding, tokenization, chunking,
and other text processing operations used throughout LitAssist.
"""

import re
import logging
from typing import List, Any

from litassist.timing import timed


@timed
def create_embeddings(texts: List[str]) -> List[Any]:
    """
    Create embeddings for a list of text inputs.

    Args:
        texts: List of text strings to embed.

    Returns:
        The embedding data from the OpenAI API response.

    Raises:
        Exception: If the embedding API call fails.
        ValueError: If any text exceeds the model's token limit.
    """
    # Import here to avoid circular imports
    from litassist.config import get_config

    # Validate text lengths (8191 tokens ≈ 32000 chars for safety)
    MAX_CHARS = 32000
    for i, text in enumerate(texts):
        if len(text) > MAX_CHARS:
            raise ValueError(
                f"Text at index {i} is too long ({len(text)} chars). "
                f"Maximum is approximately {MAX_CHARS} characters. "
                f"Use smaller chunks with chunk_text(text, max_chars=8000)."
            )

    # Use the model without custom dimensions since our index is 1536-dimensional
    from openai import OpenAI

    config = get_config()
    client = OpenAI(api_key=config.oa_key)
    response = client.embeddings.create(input=texts, model=config.emb_model)
    return response.data


def count_tokens_and_words(text: str) -> tuple[int, int]:
    """
    Count both tokens and words in text content.

    Args:
        text: The text content to analyze

    Returns:
        Tuple of (token_count, word_count)
    """
    # Try to import tiktoken if available
    try:
        import tiktoken

        TIKTOKEN_AVAILABLE = True
    except ImportError:
        TIKTOKEN_AVAILABLE = False

    if TIKTOKEN_AVAILABLE:
        try:
            # Use cl100k_base encoding (used by GPT-4, Claude, most modern models)
            encoding = tiktoken.get_encoding("cl100k_base")
            token_count = len(encoding.encode(text))
        except Exception as e:
            # Log warning and fall back to estimation
            logging.warning(
                f"tiktoken token counting failed: {e}. Falling back to word count estimation."
            )
            # Fallback: rough estimation (1 token ≈ 0.75 words)
            token_count = int(len(text.split()) * 1.33)
    else:
        # Fallback: rough estimation (1 token ≈ 0.75 words)
        token_count = int(len(text.split()) * 1.33)

    word_count = len(text.split())
    return token_count, word_count


@timed
def chunk_text(text: str, max_chars: int = 20000) -> List[str]:
    """
    Enhanced text chunking that handles OCR artifacts and provides better granularity.

    Uses multiple splitting strategies to create more manageable chunks:
    1. Split by paragraph breaks (double newlines)
    2. Split by enhanced sentence detection (handles OCR issues)
    3. Character-based splitting as fallback

    Args:
        text: The text to split into chunks.
        max_chars: Maximum characters per chunk (default: 20000 for better granularity).

    Returns:
        A list of text chunks, each up to max_chars in length.

    Raises:
        TypeError: If text is not a string or max_chars is not an integer.
        ValueError: If max_chars is not positive or text processing fails.
    """
    # Parameter validation
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not isinstance(max_chars, int):
        raise TypeError("max_chars must be an integer")
    if max_chars <= 0:
        raise ValueError("max_chars must be a positive integer")

    # Handle empty input case
    if not text or not text.strip():
        return []

    try:
        # Normalize whitespace first (OCR often has inconsistent spacing)
        normalized_text = re.sub(r"\s+", " ", text.strip())

        chunks = []
        current_chunk = ""

        # Strategy 1: Split by paragraph breaks (preserve original structure where possible)
        paragraphs = re.split(r"\n\s*\n", normalized_text)

        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue

            # If paragraph fits in current chunk, add it
            if len(current_chunk) + len(paragraph) + 2 <= max_chars:  # +2 for spacing
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
            else:
                # Save current chunk if it exists
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""

                # If paragraph is too long, split it by sentences
                if len(paragraph) > max_chars:
                    sentences = _split_into_sentences(paragraph)

                    for sentence in sentences:
                        if len(current_chunk) + len(sentence) + 1 <= max_chars:
                            if current_chunk:
                                current_chunk += " " + sentence
                            else:
                                current_chunk = sentence
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                                current_chunk = ""

                            # If sentence is still too long, split by character
                            if len(sentence) > max_chars:
                                for i in range(0, len(sentence), max_chars):
                                    chunk_part = sentence[i : i + max_chars]
                                    if (
                                        current_chunk
                                        and len(current_chunk) + len(chunk_part)
                                        <= max_chars
                                    ):
                                        current_chunk += chunk_part
                                    else:
                                        if current_chunk:
                                            chunks.append(current_chunk)
                                        current_chunk = chunk_part
                            else:
                                current_chunk = sentence
                else:
                    current_chunk = paragraph

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    except re.error as e:
        raise ValueError(f"Error in regex pattern during text chunking: {e}")
    except MemoryError:
        raise ValueError("Text is too large to process with the given chunk size")
    except Exception as e:
        raise ValueError(f"Error during text chunking: {e}")


def _split_into_sentences(text: str) -> List[str]:
    """
    Enhanced sentence splitting that handles OCR artifacts.

    Args:
        text: Text to split into sentences.

    Returns:
        List of sentences.
    """
    # Multiple patterns to catch different sentence endings common in OCR text
    patterns = [
        r"(?<=[.!?])\s+(?=[A-Z])",  # Standard: punctuation + space + capital
        r"(?<=[.!?])\s*\n+\s*(?=[A-Z])",  # punctuation + newline(s) + capital
        r"(?<=[.!?])\s*(?=\d+\.)",  # punctuation + numbered list
        r"(?<=\.)\s*(?=[A-Z][a-z])",  # period + capital + lowercase (common in OCR)
        r"(?<=[.!?])\s*(?=[A-Z][A-Z])",  # punctuation + all caps (headers)
    ]

    sentences = [text]

    for pattern in patterns:
        new_sentences = []
        for sentence in sentences:
            split_parts = re.split(pattern, sentence)
            new_sentences.extend(split_parts)
        sentences = [s.strip() for s in new_sentences if s.strip()]

    return sentences
