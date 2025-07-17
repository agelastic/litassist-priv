ARCHITECTURE Gemini.md
# LitAssist Architecture Report

## High-Level Architecture

LitAssist is a Python-based command-line application designed for legal professionals in Australia. It leverages various AI and natural language processing (NLP) services to provide a suite of tools for litigation support. The application is built with a modular architecture, making it easy to extend with new commands and functionalities.

## Core Components

*   **CLI Interface (`litassist.cli`):** The main entry point of the application, built using the `click` library. It handles command registration and execution.
*   **LLM Abstraction (`litassist.llm`):** A key component is the `LLMClient`, which provides a standardized interface to various Large Language Model (LLM) providers like OpenAI and Anthropic. This allows the application to switch between different models and providers without changing the core logic of the commands.
*   **Vector Search (`litassist.helpers.retriever`):** The application uses a `Retriever` class that integrates with Pinecone for vector-based document retrieval. This is likely used for tasks like Retrieval-Augmented Generation (RAG) to provide contextually relevant information to the LLMs. It also supports Maximal Marginal Relevance (MMR) to improve the diversity of search results.
*   **Configuration Management (`litassist.config`):** A centralized module for managing API keys, service endpoints, and other application settings.
*   **Utilities (`litassist.utils`):** A collection of helper functions for common tasks such as reading documents (PDF and text), chunking text for processing, logging, and performance monitoring.

## Commands (`litassist.commands`)

The application's functionality is organized into a series of commands, each implemented in its own module within the `litassist/commands` directory. This modular design makes the application easy to maintain and extend. Some of the key commands include:

*   **`lookup`:** Searches for case law using external services like Google CSE or Jade.
*   **`digest`:** Summarizes and digests legal documents.
*   **`brainstorm`:** Generates legal strategies.
*   **`extractfacts`:** Extracts key facts from case documents.
*   **`draft`:** Drafts legal documents using RAG.
*   **`strategy`:** Generates strategic options and documents.
*   **`verify`:** Verifies citations within a document.
*   **`counselnotes`:** Provides strategic analysis of advocate's notes.
*   **`caseplan`:** Creates phased workflow plans for a case.
*   **`barbrief`:** Generates comprehensive barrister's briefs.

## Prompts (`litassist/prompts`)

The prompts used to interact with the LLMs are managed in a dedicated `prompts` directory. This separation of prompts from the application logic allows for easier management and versioning of the prompts.

## Overall Design

The architecture of LitAssist is well-structured and follows best practices for building maintainable and extensible command-line applications. The clear separation of concerns between the core components, commands, and prompts makes the codebase easy to understand and navigate. The use of a centralized LLM client and a dedicated retriever component demonstrates a thoughtful approach to integrating with external AI services.