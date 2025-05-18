#!/usr/bin/env python3
import os
import sys
import time
import json
import logging
import click
import yaml
import threading
import functools

import openai
import pinecone
from googleapiclient.discovery import build
from PyPDF2 import PdfReader
import re
from pinecone_config import get_pinecone_client

# ── Configuration ───────────────────────────────────────
CONFIG_PATH = "config.yaml"
if not os.path.exists(CONFIG_PATH):
    sys.exit("Error: Missing config.yaml")

with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

# Validate and assign
try:
    OR_KEY = cfg["openrouter"]["api_key"]
    OR_BASE = cfg["openrouter"].get("api_base", "https://openrouter.ai/api/v1")
    OA_KEY = cfg["openai"]["api_key"]
    EMB_MODEL = cfg["openai"].get("embedding_model", "text-embedding-3-small")
    G_KEY = cfg["google_cse"]["api_key"]
    CSE_ID = cfg["google_cse"]["cse_id"]
    PC_KEY = cfg["pinecone"]["api_key"]
    PC_ENV = cfg["pinecone"]["environment"]
    PC_INDEX = cfg["pinecone"]["index_name"]

except KeyError as e:
    sys.exit(f"Error: config.yaml missing key {e}")

# ── Validate config values ──────────────────────────────────
required_configs = {
    "openrouter.api_key": OR_KEY,
    "openai.api_key": OA_KEY,
    "openai.embedding_model": EMB_MODEL,
    "google_cse.api_key": G_KEY,
    "google_cse.cse_id": CSE_ID,
    "pinecone.api_key": PC_KEY,
    "pinecone.environment": PC_ENV,
    "pinecone.index_name": PC_INDEX,
}
for key, val in required_configs.items():
    if not isinstance(val, str) or not val.strip():
        sys.exit(f"Error: config '{key}' must be a non-empty string")

# ── API Initialization ─────────────────────────────────
openai.api_key = OA_KEY
# Don't set api_base unless we're using OpenRouter specifically
# openai.api_base = OR_BASE

# Create a mock Pinecone index for testing purposes
class MockPineconeIndex:
    def __init__(self, *args, **kwargs):
        pass

    def query(self, *args, **kwargs):
        return {"matches": []}

    def upsert(self, *args, **kwargs):
        pass

    def delete(self, *args, **kwargs):
        pass

    def describe_index_stats(self, *args, **kwargs):
        class MockStats:
            def __init__(self):
                self.total_vector_count = 0

        return MockStats()

# Check if we're using placeholder values for Pinecone
if "YOUR_PINECONE" in PC_KEY or "YOUR_PINECONE" in PC_ENV:
    print(
        "WARNING: Using placeholder Pinecone credentials. Some features will be limited."
    )
    pc_index = MockPineconeIndex()
else:
    # Use our wrapper to handle connection issues
    pc_index = get_pinecone_client(PC_KEY, PC_ENV, PC_INDEX)
    
    # Test if we can access it
    try:
        stats = pc_index.describe_index_stats()
        print(f"✓ Connected to index '{PC_INDEX}' (dimension: {stats.dimension}, vectors: {stats.total_vector_count})")
    except Exception as e:
        print(f"WARNING: Cannot access index '{PC_INDEX}'.")
        print(f"Error: {e}")
        print("Using mock index for testing.")
        pc_index = MockPineconeIndex()

# ── Startup API Connection Tests ───────────────────────────

# Test OpenAI connectivity (only if not using placeholders)
if "YOUR_" not in OA_KEY and "YOUR_" not in OR_KEY:
    try:
        openai.Model.list()
    except Exception as e:
        sys.exit(f"Error: OpenAI API test failed: {e}")
else:
    print("Skipping OpenAI connectivity test due to placeholder credentials")

# Test Pinecone connectivity (only if not using placeholders)
if "YOUR_PINECONE" not in PC_KEY and "YOUR_PINECONE" not in PC_ENV:
    try:
        _ = pinecone.list_indexes()
    except Exception as e:
        sys.exit(f"Error: Pinecone API test failed: {e}")
else:
    print("Skipping Pinecone connectivity test due to placeholder credentials")

# Test Google CSE connectivity (only if not using placeholder values)
if "YOUR_GOOGLE" not in G_KEY and "YOUR_GOOGLE" not in CSE_ID:
    try:
        service = build("customsearch", "v1", developerKey=G_KEY)
        # Perform a lightweight test query (no logging)
        service.cse().list(q="test", cx=CSE_ID, num=1).execute()
    except Exception as e:
        sys.exit(f"Error: Google CSE API test failed: {e}")
else:
    print("Skipping Google CSE connectivity test due to placeholder credentials")

# ── Logging ─────────────────────────────────────────────
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(message)s")


# ── Utilities ───────────────────────────────────────────
def timed(func):
    """
    Decorator to measure and log execution time of functions.

    Args:
        func: The function to time.

    Returns:
        A wrapped function that includes timing measurements.

    Example:
        @timed
        def my_function():
            # Function code
            pass
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            end_timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            # Add timing info to the result if it's a tuple with a dict
            if (
                isinstance(result, tuple)
                and len(result) >= 2
                and isinstance(result[1], dict)
            ):
                content, usage_dict = result[0], result[1]
                if "timing" not in usage_dict:
                    usage_dict["timing"] = {}
                usage_dict["timing"].update(
                    {
                        "start_time": start_timestamp,
                        "end_time": end_timestamp,
                        "duration_seconds": round(duration, 3),
                    }
                )
                return content, usage_dict

            # Just log the timing info
            logging.debug(
                f"Function {func.__name__} execution time: {duration:.3f} seconds"
            )
            logging.debug(f"  - Started: {start_timestamp}")
            logging.debug(f"  - Ended: {end_timestamp}")

            return result

        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logging.debug(
                f"Function {func.__name__} failed after {duration:.3f} seconds"
            )
            raise e

    return wrapper


@timed
def save_log(tag: str, payload: dict):
    """
    Save an audit log under logs/ in either JSON or Markdown format.

    Args:
        tag: A string identifier for the log (e.g., command name).
        payload: Dictionary containing log data including inputs, response, and usage statistics.

    Raises:
        click.ClickException: If there's an error writing the log file.
    """
    from click import get_current_context

    ts = time.strftime("%Y%m%d-%H%M%S")
    ctx = get_current_context(silent=True)
    log_format = (
        ctx.obj.get("log_format", "markdown") if ctx and ctx.obj else "markdown"
    )

    # JSON logging
    if log_format == "json":
        path = os.path.join(LOG_DIR, f"{tag}_{ts}.json")
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            logging.info(f"JSON log saved: {path}")
        except IOError as e:
            raise click.ClickException(f"Failed to save JSON log {path}: {e}")
        return

    # Markdown logging (default)
    md_path = os.path.join(LOG_DIR, f"{tag}_{ts}.md")
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            # Metadata
            f.write(f"# {tag} — {ts}\n\n")
            f.write(f"- **Command**: `{tag}`  \n")
            f.write(f"- **Parameters**: `{payload.get('params','')}`  \n\n")
            # Inputs
            f.write("## Inputs\n\n")
            for k, v in payload.get("inputs", {}).items():
                f.write(f"**{k}**:  \n```\n{v}\n```\n\n")
            # Output
            f.write("## Output\n\n```\n")
            f.write(payload.get("response", "").strip())
            f.write("\n```\n\n")
            # Usage
            f.write("## Usage\n\n")
            usage = payload.get("usage", {})
            for field in ("prompt_tokens", "completion_tokens", "total_tokens"):
                if field in usage:
                    f.write(f"- **{field}**: {usage[field]}  \n")

            # Add timing information if available
            timing = usage.get("timing", {})
            if timing:
                f.write("\n## Timing\n\n")
                f.write(f"- **Start Time**: {timing.get('start_time', 'N/A')}  \n")
                f.write(f"- **End Time**: {timing.get('end_time', 'N/A')}  \n")
                f.write(
                    f"- **Duration**: {timing.get('duration_seconds', 'N/A')} seconds  \n"
                )
        logging.info(f"Markdown log saved: {md_path}")
    except IOError as e:
        raise click.ClickException(f"Failed to save Markdown log {md_path}: {e}")


@timed
def read_document(path: str) -> str:
    """
    Read a PDF (text‐only) or plain‐text file and return its full text.

    Args:
        path: The path to the PDF or text file to read.

    Returns:
        The extracted text content as a string.

    Raises:
        click.ClickException: On any I/O or text extraction errors.
    """
    try:
        if path.lower().endswith(".pdf"):
            reader = PdfReader(path)
            pages = []
            for page in reader.pages:
                txt = page.extract_text()
                if txt:
                    pages.append(txt)
            if not pages:
                raise click.ClickException(f"No extractable text found in PDF: {path}")
            return "\n".join(pages)
        else:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                raise click.ClickException(f"No text found in file: {path}")
            return content
    except FileNotFoundError:
        raise click.ClickException(f"File not found: {path}")
    except Exception as e:
        raise click.ClickException(f"Error reading document {path}: {e}")


@timed
def create_embeddings(texts: list[str]):
    """
    Create embeddings for a list of text inputs.

    Args:
        texts: List of text strings to embed.

    Returns:
        The embedding data from the OpenAI API response.

    Raises:
        Exception: If the embedding API call fails.
    """
    # Use the model without custom dimensions since our index is 1536-dimensional
    return openai.Embedding.create(input=texts, model=EMB_MODEL).data


@timed
def chunk_text(text: str, max_chars: int = 60000) -> list[str]:
    """
    Split text into chunks of up to max_chars characters, attempting to break at sentence boundaries
    to avoid cutting sentences in half.

    Args:
        text: The text to split into chunks.
        max_chars: Maximum characters per chunk. Must be a positive integer.

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
    if not text:
        return []

    try:
        # Split into sentences by punctuation followed by whitespace
        sentences = re.split(r"(?<=[\.\?\!]\s)", text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # Handle sentences longer than max_chars by splitting directly
                while len(sentence) > max_chars:
                    chunks.append(sentence[:max_chars])
                    sentence = sentence[max_chars:]
                current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
    except re.error as e:
        raise ValueError(f"Error in regex pattern during text chunking: {e}")
    except MemoryError:
        raise ValueError("Text is too large to process with the given chunk size")
    except Exception as e:
        raise ValueError(f"Error during text chunking: {e}")


# ── Heartbeat Decorator ────────────────────────────────
def heartbeat(interval: int = 30):
    """
    Decorator to emit a heartbeat message every `interval` seconds while a long-running function executes.

    Args:
        interval: Number of seconds between heartbeat messages. Defaults to 30.

    Returns:
        A decorator function that wraps the target function with heartbeat functionality.

    Example:
        @heartbeat(60)
        def long_running_function():
            # Function that takes a long time to execute
            pass
    """

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            done = threading.Event()

            def ping():
                while not done.is_set():
                    click.echo("…still working, please wait…", err=True)
                    time.sleep(interval)

            t = threading.Thread(target=ping, daemon=True)
            t.start()
            try:
                return fn(*args, **kwargs)
            finally:
                done.set()
                t.join(timeout=0)

        return wrapper

    return decorator


# ── LLM Client Wrapper ─────────────────────────────────
class LLMClient:
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
        client = LLMClient("anthropic/claude-3-sonnet", temperature=0.2, top_p=0.8)

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
            model: The model name to use (e.g., 'openai/gpt-4o', 'anthropic/claude-3-sonnet').
            **default_params: Default decoding parameters (temperature, top_p, etc.) to use
                             for all completions unless overridden.
        """
        self.model = model
        self.default_params = default_params

    @timed
    def complete(self, messages: list[dict], **overrides) -> tuple[str, dict]:
        """
        Run a single chat completion with the configured model.

        Args:
            messages: List of message dictionaries, each containing 'role' (system/user/assistant)
                     and 'content' (the message text).
            **overrides: Optional parameter overrides for this specific completion that will
                        take precedence over the default parameters.

        Returns:
            A tuple containing:
                - The generated text content (str)
                - The usage statistics dictionary (with prompt_tokens, completion_tokens, etc.)

        Raises:
            Exception: If the API call fails or returns an error.
        """
        # Merge default and override parameters
        params = {**self.default_params, **overrides}
        
        # Set API base based on model type
        original_api_base = openai.api_base
        original_api_key = openai.api_key
        
        # Determine the correct model name
        model_name = self.model
        
        # Use OpenRouter for non-OpenAI models
        if "/" in self.model and not self.model.startswith("openai/"):
            openai.api_base = OR_BASE
            openai.api_key = OR_KEY
        else:
            # Extract just the model name for OpenAI models
            if self.model.startswith("openai/"):
                model_name = self.model.replace("openai/", "")
            
        # Invoke the chat completion
        try:
            response = openai.ChatCompletion.create(
                model=model_name, messages=messages, **params
            )
        finally:
            # Restore original settings
            openai.api_base = original_api_base
            openai.api_key = original_api_key
        # Extract content and usage
        content = response.choices[0].message.content
        usage = getattr(response, "usage", {})
        return content, usage

    @timed
    def verify(self, primary_text: str) -> str:
        """
        Run a self-critique pass to identify and correct legal inaccuracies in text.

        Uses the same model as the client instance but with deterministic settings
        (temperature=0, top_p=0.2) to minimize variability in verification.

        Args:
            primary_text: The text content to verify for legal accuracy.

        Returns:
            A string containing corrections to any legal inaccuracies found.

        Raises:
            Exception: If the verification API call fails.
        """
        critique_prompt = [
            {"role": "system", "content": "Australian law only."},
            {
                "role": "user",
                "content": primary_text
                + "\n\nIdentify and correct any legal inaccuracies above, and provide the corrected text only.",
            },
        ]
        # Use deterministic settings for verification
        params = {"temperature": 0, "top_p": 0.2, "max_tokens": 800}
        
        # Set API base based on model type
        original_api_base = openai.api_base
        original_api_key = openai.api_key
        
        # Determine the correct model name
        model_name = self.model
        
        # Use OpenRouter for non-OpenAI models
        if "/" in self.model and not self.model.startswith("openai/"):
            openai.api_base = OR_BASE
            openai.api_key = OR_KEY
        else:
            # Extract just the model name for OpenAI models
            if self.model.startswith("openai/"):
                model_name = self.model.replace("openai/", "")
                
        # Invoke the verification
        try:
            response = openai.ChatCompletion.create(
                model=model_name, messages=critique_prompt, **params
            )
        finally:
            # Restore original settings
            openai.api_base = original_api_base
            openai.api_key = original_api_key
        return response.choices[0].message.content


# ── Retriever Wrapper ──────────────────────────────────
class Retriever:
    """
    Vector search retrieval system with Maximal Marginal Relevance (MMR) re-ranking support.

    This class handles querying a vector database (Pinecone) and retrieving relevant text passages,
    with optional diversity-based re-ranking using MMR. MMR balances between retrieving the most
    relevant results and ensuring diversity in the result set, which can be important for
    legal research where getting varied perspectives is valuable.

    Attributes:
        index: The Pinecone index used for vector search.
        use_mmr: Boolean indicating whether to use MMR for diversity in results.
        diversity_level: Float between 0.0-1.0 controlling the balance between relevance
                        and diversity when MMR is enabled.

    Example:
        ```python
        # Initialize with default MMR settings
        retriever = Retriever(pc_index, use_mmr=True, diversity_level=0.3)

        # Retrieve passages using a query embedding
        passages = retriever.retrieve(query_embedding, top_k=5)

        # Or with a custom diversity setting for this query
        diverse_passages = retriever.retrieve(query_embedding, top_k=5, diversity_level=0.7)
        ```
    """

    def __init__(self, index, use_mmr: bool = True, diversity_level: float = 0.3):
        """
        Initialize the retriever with MMR settings.

        Args:
            index: The Pinecone index to query.
            use_mmr: Whether to use Maximal Marginal Relevance for diversity in results.
            diversity_level: Controls the balance between relevance and diversity (0.0-1.0).
                             Lower values (closer to 0) prioritize relevance,
                             Higher values (closer to 1) prioritize diversity.
        """
        self.index = index
        self.use_mmr = use_mmr
        self.diversity_level = max(
            0.0, min(1.0, diversity_level)
        )  # Clamp between 0 and 1

    @timed
    def retrieve(
        self, query_emb: list[float], top_k: int = 5, diversity_level: float = None
    ) -> list[str]:
        """
        Query Pinecone (with optional MMR) and return a list of passage texts.

        Args:
            query_emb: Embedding vector of the user query.
            top_k: Number of passages to return.
            diversity_level: Override the default diversity level for this query.
                             Controls the balance between relevance and diversity (0.0-1.0).
                             Lower values prioritize relevance, higher values prioritize diversity.

        Returns:
            A list of text passages retrieved from the vector store.
        """
        # Build query arguments
        query_kwargs = {"vector": query_emb, "top_k": top_k, "include_metadata": True}
        # Enable Maximal Marginal Relevance if requested
        if getattr(self, "use_mmr", False):
            query_kwargs["use_mmr"] = True
            # Apply diversity setting - use the provided value or fall back to instance default
            actual_diversity = (
                diversity_level if diversity_level is not None else self.diversity_level
            )
            actual_diversity = max(
                0.0, min(1.0, actual_diversity)
            )  # Clamp between 0 and 1
            query_kwargs["diversity_bias"] = actual_diversity

        # Execute the query
        result = self.index.query(**query_kwargs)
        # Extract and return the text field from metadata
        passages = []
        for match in result.matches:
            metadata = match.metadata
            text = metadata.get("text")
            if text:
                passages.append(text)
        return passages


# ── CLI Definition ─────────────────────────────────────
@click.group()
@click.option(
    "--log-format",
    type=click.Choice(["json", "markdown"]),
    default="markdown",
    show_default=True,
    help="Format for audit logs.",
)
@click.option(
    "--verbose", is_flag=True, default=False, help="Enable debug-level logging."
)
@click.pass_context
def cli(ctx, log_format, verbose):
    """
    LitAssist: automated litigation support workflows for Australian legal practice.

    This is the main entry point for the CLI application, handling global options
    and command selection. The tool provides multiple commands for different legal
    workflows including case-law lookup, document analysis, creative legal ideation,
    fact extraction, and citation-rich drafting.

    Args:
        ctx: Click context object for sharing data between commands.
        log_format: Format for audit logs (json or markdown).
        verbose: Whether to enable detailed debug logging.

    Global options:
    \b
    --log-format    Choose log output format (json or markdown).
    --verbose       Enable debug logging and detailed output.

    Example:
        # Basic case-law lookup with IRAC format
        litassist.py lookup "What constitutes negligence in medical malpractice?"

        # Document summarization with verification
        litassist.py digest large_document.pdf --mode summary --verify
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    # Store the chosen log format for downstream use
    ctx.obj["log_format"] = log_format
    # Configure logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    logging.debug(f"Log format set to: {log_format}")


# ── lookup ───────────────────────────────────────────────
@cli.command()
@click.argument("question")
@click.option("--mode", type=click.Choice(["irac", "broad"]), default="irac")
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
def lookup(question, mode, verify):
    """
    Rapid case-law lookup via Google CSE + Gemini.

    Searches for legal information on AustLII via Google Custom Search,
    then processes the results with Google Gemini to produce a structured
    legal answer citing relevant cases.

    Args:
        question: The legal question to search for.
        mode: Answer format - 'irac' (Issue, Rule, Application, Conclusion) for
              structured analysis, or 'broad' for more creative exploration.
        verify: Whether to run a self-critique verification pass on the answer.

    Raises:
        click.ClickException: If there are errors with the Google CSE or LLM API calls.
    """
    # Fetch AustLII links via Google Custom Search
    try:
        service = build("customsearch", "v1", developerKey=G_KEY)
        res = (
            service.cse()
            .list(q=question, cx=CSE_ID, num=3, siteSearch="austlii.edu.au")
            .execute()
        )
    except Exception as e:
        raise click.ClickException(f"Google CSE error: {e}")
    links = [item.get("link") for item in res.get("items", [])]
    click.echo("Found links:")
    for link in links:
        click.echo(f"- {link}")

    # Prepare prompt
    prompt = f"Question: {question}\nLinks:\n" + "\n".join(links)
    # Select parameters based on mode
    if mode == "irac":
        overrides = {"temperature": 0, "top_p": 0.1, "max_tokens": 512}
    else:
        overrides = {"temperature": 0.5, "top_p": 0.9, "max_tokens": 800}

    # Call the LLM
    client = LLMClient("google/gemini-2.5-pro-preview", temperature=0, top_p=0.2)
    call_with_hb = heartbeat(30)(client.complete)
    try:
        content, usage = call_with_hb(
            [
                {"role": "system", "content": "Australian law only. Cite sources."},
                {"role": "user", "content": prompt},
            ],
            **overrides,
        )
    except Exception as e:
        raise click.ClickException(f"LLM error during lookup: {e}")
    # Citation guard: retry once if no AustLII pattern found
    if not re.search(r"austlii\.edu\.au", content):
        try:
            content, usage = call_with_hb(
                [
                    {"role": "system", "content": "Australian law only. Cite sources."},
                    {"role": "user", "content": prompt + "\n\n(Cite your sources!)"},
                ],
                **overrides,
            )
        except Exception as e:
            raise click.ClickException(f"LLM retry error during lookup: {e}")

    # Optional self-critique verification
    if verify:
        try:
            correction = client.verify(content)
            content = content + "\n\n--- Corrections ---\n" + correction
        except Exception as e:
            raise click.ClickException(f"Self-verification error during lookup: {e}")

    # Save audit log and output
    save_log(
        "lookup",
        {
            "params": f"mode={mode}, verify={verify}",
            "inputs": {
                "question": question,
                "links": "\n".join(links),
                "prompt": prompt,
            },
            "response": content,
            "usage": usage,
        },
    )
    click.echo(content)


# ── digest ───────────────────────────────────────────────
@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["summary", "issues"]), default="summary")
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
def digest(file, mode, verify):
    """
    Mass-document digestion via Claude.

    Processes large documents by splitting them into manageable chunks
    and using Claude to either summarize content chronologically or
    identify potential legal issues in each section.

    Args:
        file: Path to the document (PDF or text) to analyze.
        mode: Type of analysis to perform - 'summary' for chronological summaries
              or 'issues' to identify potential legal problems.
        verify: Whether to perform a self-critique verification pass on each chunk's output.

    Raises:
        click.ClickException: If there are errors with file reading, processing,
                             or LLM API calls.
    """
    # Read and split the document
    text = read_document(file)
    chunks = chunk_text(text)
    # Select parameter presets based on mode
    presets = {
        "summary": {"temperature": 0, "top_p": 0, "max_tokens": 2000},
        "issues": {"temperature": 0.2, "top_p": 0.5, "max_tokens": 1500},
    }[mode]
    client = LLMClient("anthropic/claude-3-sonnet", **presets)

    # Process each chunk with a progress bar
    with click.progressbar(chunks, label="Processing chunks") as chunks_bar:
        for idx, chunk in enumerate(chunks_bar, start=1):
            prompt = (
                "Provide a concise chronological summary:\n\n" + chunk
                if mode == "summary"
                else "Identify any potential legal issues:\n\n" + chunk
            )
            # Call the LLM
            try:
                content, usage = client.complete(
                    [
                        {"role": "system", "content": "Australian law only."},
                        {"role": "user", "content": prompt},
                    ]
                )
            except Exception as e:
                raise click.ClickException(f"LLM error in digest chunk {idx}: {e}")

            # Optional self-critique verification
            if verify:
                try:
                    correction = client.verify(content)
                    content = content + "\n\n--- Corrections ---\n" + correction
                except Exception as e:
                    raise click.ClickException(
                        f"Self-verification error in digest chunk {idx}: {e}"
                    )

            # Save audit log for this chunk
            save_log(
                f"digest_{mode}",
                {
                    "file": file,
                    "chunk": idx,
                    "verify": verify,
                    "response": content,
                    "usage": usage,
                },
            )
            # Output to user
            click.echo(f"\n--- Chunk {idx} ---\n{content}")


# ── ideate ───────────────────────────────────────────────
@cli.command()
@click.argument("facts_file", type=click.Path(exists=True))
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
def ideate(facts_file, verify):
    """
    Generate novel legal strategies via Grok.

    Uses Grok's creative capabilities to generate ten unorthodox litigation
    arguments or remedies based on the facts provided. Particularly useful
    for brainstorming alternative legal approaches.

    Args:
        facts_file: Path to a text file containing structured case facts.
        verify: Whether to run a self-critique verification pass on the generated ideas.

    Raises:
        click.ClickException: If there are errors reading the facts file or with the LLM API call.
    """
    # Read the structured facts file
    facts = read_document(facts_file)

    # Initialise the LLM for creative ideation
    client = LLMClient("x-ai/grok-3-beta", temperature=0.9, top_p=0.95, max_tokens=1200)

    # Build and send the prompt
    prompt = f"Facts:\n{facts}\n\nList ten unorthodox litigation arguments or remedies not commonly raised."
    messages = [
        {"role": "system", "content": "Australian law only."},
        {"role": "user", "content": prompt},
    ]
    call_with_hb = heartbeat(30)(client.complete)
    try:
        content, usage = call_with_hb(messages)
    except Exception as e:
        raise click.ClickException(f"Grok ideation error: {e}")

    # Optional self-critique verification
    if verify:
        try:
            correction = client.verify(content)
            content = content + "\n\n--- Corrections ---\n" + correction
        except Exception as e:
            raise click.ClickException(f"Self-verification error during ideation: {e}")

    # Save audit log
    save_log(
        "ideate",
        {
            "inputs": {"facts_file": facts_file, "prompt": prompt},
            "params": f"verify={verify}",
            "response": content,
            "usage": usage,
        },
    )

    # Display the ideas
    click.echo(f"--- Ideas ---\n{content}")


# ── extractfacts ───────────────────────────────────────
@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
def extractfacts(file, verify):
    """
    Auto-generate case_facts.txt under ten structured headings.

    Processes a document to extract relevant case facts and organizes them
    into a structured format with ten standard headings. This provides a
    foundation for other commands like 'ideate' which require structured facts.

    Args:
        file: Path to the document (PDF or text) to extract facts from.
        verify: Whether to run a self-critique verification pass on the extracted facts.

    Raises:
        click.ClickException: If there are errors reading the file, processing chunks,
                             or with the LLM API calls.
    """
    # Read and chunk the document
    text = read_document(file)
    chunks = chunk_text(text)

    # Initialize the LLM client with deterministic settings
    client = LLMClient(
        "anthropic/claude-3-sonnet", temperature=0, top_p=0.15, max_tokens=2000
    )

    assembled = []
    # Process each chunk with a progress bar
    with click.progressbar(chunks, label="Extracting facts") as bar:
        for chunk in bar:
            prompt = (
                "Extract under these headings:\n"
                "1. Jurisdiction & Forum\n"
                "2. Parties & Roles\n"
                "3. Procedural Posture\n"
                "4. Chronology of Key Events\n"
                "5. Factual Background\n"
                "6. Legal Issues & Applicable Law\n"
                "7. Client Objectives & Constraints\n"
                "8. Key Evidence\n"
                "9. Known Weaknesses or Gaps\n"
                "10. Commercial or Policy Context\n\n" + chunk
            )
            try:
                content, usage = client.complete(
                    [
                        {"role": "system", "content": "Australian law only."},
                        {"role": "user", "content": prompt},
                    ]
                )
            except Exception as e:
                raise click.ClickException(f"Error extracting facts in chunk: {e}")
            assembled.append(content.strip())

    # Combine all chunks into a single facts file
    combined = "\n\n".join(assembled)

    # Optional self-critique verification
    if verify:
        try:
            correction = client.verify(combined)
            combined = combined + "\n\n--- Corrections ---\n" + correction
        except Exception as e:
            raise click.ClickException(
                f"Self-verification error during fact extraction: {e}"
            )

    with open("case_facts.txt", "w", encoding="utf-8") as f:
        f.write(combined)

    # Audit log
    save_log(
        "extractfacts",
        {
            "inputs": {"source_file": file, "chunks": len(chunks)},
            "params": f"verify={verify}",
            "response": combined,
        },
    )
    click.echo("case_facts.txt created successfully.")


# ── draft ────────────────────────────────────────────────
@cli.command()
@click.argument("pdf", type=click.Path(exists=True))
@click.argument("query")
@click.option("--verify", is_flag=True, help="Enable self-critique pass")
@click.option(
    "--diversity",
    type=float,
    help="Control diversity of search results (0.0-1.0)",
    default=None,
)
def draft(pdf, query, verify, diversity):
    """
    Citation-rich drafting via RAG & GPT-4o.

    Implements a Retrieval-Augmented Generation workflow to create well-supported
    legal drafts. The process embeds document chunks, stores them in Pinecone,
    retrieves relevant passages using MMR re-ranking, and generates a draft
    with GPT-4o that incorporates these citations.

    Args:
        pdf: Path to the PDF document to use as a knowledge base.
        query: The specific legal topic or argument to draft.
        verify: Whether to run a self-critique verification pass on the draft.
        diversity: Optional float (0.0-1.0) controlling the balance between
                  relevance and diversity in retrieved passages. Higher values
                  prioritize diversity over relevance.

    Raises:
        click.ClickException: If there are errors with file reading, embedding,
                             vector storage, retrieval, or LLM API calls.
    """
    # Read and chunk the document
    text = read_document(pdf)
    chunks = chunk_text(text)

    # Embed and upsert document chunks
    docs = [(f"d{i}", chunk) for i, chunk in enumerate(chunks, start=1)]
    try:
        embeddings = create_embeddings([d[1] for d in docs])
    except Exception as e:
        raise click.ClickException(f"Embedding error: {e}")
    vectors = [
        (docs[i][0], embeddings[i].embedding, {"text": docs[i][1]})
        for i in range(len(docs))
    ]
    try:
        pc_index.upsert(vectors=vectors)
    except Exception as e:
        raise click.ClickException(f"Pinecone upsert error: {e}")

    # Retrieve relevant context with MMR
    try:
        qemb = create_embeddings([query])[0].embedding
    except Exception as e:
        raise click.ClickException(f"Embedding error for query: {e}")
    retriever = Retriever(pc_index, use_mmr=True)
    try:
        context_list = retriever.retrieve(qemb, top_k=5, diversity_level=diversity)
    except Exception as e:
        raise click.ClickException(f"Pinecone retrieval error: {e}")
    context = "\n\n".join(context_list)

    # Generate draft with GPT-4o
    client = LLMClient(
        "openai/gpt-4o",
        temperature=0.5,
        top_p=0.8,
        presence_penalty=0.1,
        frequency_penalty=0.1,
        max_tokens=2000,
    )
    messages = [
        {"role": "system", "content": "Australian law only."},
        {"role": "user", "content": f"Context:\n{context}\n\nDraft {query}"},
    ]
    call_with_hb = heartbeat(30)(client.complete)
    try:
        content, usage = call_with_hb(messages)
    except Exception as e:
        raise click.ClickException(f"LLM draft error: {e}")

    # Optional self-critique verification
    if verify:
        try:
            correction = client.verify(content)
        except Exception as e:
            raise click.ClickException(f"Self-verification error: {e}")
        content = content + "\n\n--- Corrections ---\n" + correction

    # Save audit log and echo response
    save_log(
        "draft",
        {
            "inputs": {"pdf": pdf, "query": query, "context": context},
            "response": content,
            "usage": usage,
        },
    )
    click.echo(content)


if __name__ == "__main__":
    cli()
