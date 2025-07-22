The LitAssist application is a command-line tool built with Python and the Click library. It's designed to assist with legal workflows by leveraging Large Language Models (LLMs). The architecture is modular, with a clear separation of concerns.

### High-Level Architecture

The application follows a layered architecture:

1.  **CLI (Command Line Interface):** This is the user-facing layer, built using the `click` library. The main entry point is `litassist.py` and `litassist/cli.py`, which handles command parsing, global options (like logging), and registration of various commands.

2.  **Command Modules:** Each command available in the CLI (e.g., `lookup`, `digest`, `draft`) is implemented as a separate module in the `litassist/commands/` directory. This modular approach makes it easy to add new commands.

3.  **Core Components:** This layer provides the core functionality and services used by the command modules.
    *   **Configuration (`config.py`):** Manages application settings and API keys, loading them from a `config.yaml` file.
    *   **LLM Client (`llm.py`):** A wrapper around different LLM providers (like OpenAI, Anthropic, Google), providing a unified interface for interacting with them. It also handles features like streaming and retries.
    *   **Prompt Management (`prompts.py` and `prompts/`):** Manages the prompts used to interact with the LLMs. Prompts are defined in YAML files, allowing for easy editing and versioning.
    *   **Utilities (`utils.py`):** A collection of helper functions for tasks like file I/O, text processing, and logging.
    *   **Helpers (`helpers/`):** Contains modules for specific tasks, such as interacting with Pinecone for vector search (`retriever.py`).
    *   **Citation Verification (`citation_verify.py`, `citation_patterns.py`):**  Provides functionality to verify legal citations.

4.  **External Services:** The application integrates with several external services:
    *   **LLM Providers:** OpenAI, OpenRouter, etc.
    *   **Pinecone:** For vector database capabilities (used in RAG).
    *   **Google Custom Search:** For case-law lookup.

### Data Flow

A typical workflow looks like this:

1.  A user runs a command from their terminal.
2.  Click parses the command and its arguments.
3.  The corresponding command module is executed.
4.  The command module uses the core components to perform its task. This might involve:
    *   Reading documents from the local filesystem.
    *   Retrieving information from the Pinecone vector database.
    *   Constructing a prompt using the `PromptManager`.
    *   Sending the prompt to an LLM via the `LLMClient`.
5.  The response from the LLM is processed. This might include verifying citations.
6.  The final output is displayed to the user, and logs are saved.

### Extensibility

The architecture is designed to be extensible. New commands can be added by creating a new file in the `litassist/commands/` directory and registering it in `litassist/commands/__init__.py`. Similarly, new LLM providers or prompt templates can be added with relative ease.

In summary, LitAssist is a well-structured, modular application that effectively separates concerns, making it maintainable and extensible. It leverages a combination of local processing and external services to provide its powerful legal assistance features.
