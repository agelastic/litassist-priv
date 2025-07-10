# Transition Plan: From Prompt Engineering to Context Engineering

This plan outlines steps to evolve the LitAssist codebase from its current prompt-centric approach to a context-engineered architecture. The goal is to keep prompts lightweight while dynamically assembling relevant contextual data for each LLM call.

## 1. Catalogue Existing Prompts

1. **Inventory YAML templates**: review files in `litassist/prompts/*.yaml` and list all keys used across commands.
2. **Locate hard-coded prompts**: search the `commands` directory for any direct string prompts and document them.
3. **Map usage**: create a matrix showing which commands use which prompt templates.

## 2. Design Context Storage

1. **Identify static knowledge**: legal requirements, citation formats, workflow summaries, and other recurring instructions can be stored as retrievable text snippets.
2. **Embed documents**: convert these snippets and existing documentation into embeddings (e.g., using OpenAI or other models).
3. **Choose a vector store**: reuse the Pinecone integration currently leveraged for the `draft` command to store and retrieve context.
4. **Tag metadata**: label each document with categories such as `legal_guidelines`, `formatting`, `jurisdiction`, `document_type`, or command names for targeted retrieval.

## 3. Build Retrieval Utilities

1. **Create a `context` module**: implement functions to query the vector store based on command name and user request.
2. **Implement MMR or similarity search**: use the existing `Retriever` helper to fetch the most relevant snippets.
3. **Cache results**: store retrieved context in an in-memory cache scoped to a single command execution to improve performance.

## 4. Refactor Prompt Composition

1. **Skeleton templates**: reduce YAML files to concise templates with placeholders like `{context}` and `{instructions}`.
2. **Dynamic assembly**: write per-command assemblers that gather prior outputs, retrieved snippets, and user-provided files. Insert this context into the skeleton template at runtime.
3. **Minimize duplication**: ensure common instructions (e.g., Australian law disclaimer) are retrieved once and shared across commands instead of repeated in every prompt file.

## 5. Update Commands Incrementally

1. **Pilot with `draft`**: since `draft.py` already performs retrieval for large documents, extend it to also fetch static instructions from the vector store.
2. **Apply to other commands**: refactor `lookup`, `brainstorm`, and so on to use the new context module instead of loading large prompt sections directly.
3. **Fallback behavior**: if retrieval fails or is disabled (e.g., via a feature flag), commands should gracefully revert to existing templates to avoid breaking workflows during the transition.

## 6. Testing and Validation

1. **Unit tests**: add tests ensuring that each command’s assembler retrieves the expected context given a set of inputs.
2. **Integration tests**: simulate end-to-end runs to confirm that documents are correctly embedded, stored, and retrieved.
3. **Performance and quality checks**: monitor token counts and latency to verify efficiency, and compare outputs against a baseline to ensure quality is maintained.

## 7. Documentation

1. **Developer guide**: write documentation describing how to add new context snippets, create new commands with context retrieval, update embeddings, and maintain the vector store.
2. **User guide updates**: explain any new options or changes in command behavior resulting from context-driven prompts.

By following this plan, LitAssist can transition to a context-engineering approach that leverages dynamic retrieval of relevant information while keeping prompts maintainable and focused on the immediate task.
