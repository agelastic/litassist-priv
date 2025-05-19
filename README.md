# LitAssist

**LitAssist** is a command-line tool for automated litigation support workflows, tailored to Australian law. It leverages large language models (LLMs) and a managed vector store to help you:

- **Rapid case-law lookup** (Google Custom Search + Google Gemini)  
- **Mass-document digestion** (Chronological summaries or issue-spotting via Claude)  
- **Creative brainstorming** (Unorthodox legal strategies via Grok)  
- **Automatic extraction of case facts** into a structured file  
- **Citation-rich drafting** (Retrieval-Augmented Generation with GPT-4o)  

All processing is cloud-only: no local model downloads required.

## 📁 Example Files

The `examples/` directory contains sample files referenced in the documentation, including:
- PDF documents for testing the `digest`, `extractfacts`, and `draft` commands
- A sample `case_facts.txt` file for testing the `brainstorm` command
- All examples are based on the fictional *Smith v Jones* family law case

---

## 🔧 Installation

1. **Clone or download** this repository and `cd` into it:
   ```bash
   git clone https://github.com/your-org/litassist.git
   cd litassist
   ```

2. **Create and activate** a Python 3.8+ virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install click openai pinecone-client PyPDF2 google-api-python-client pyyaml
   ```
   
   This will install all required packages for LitAssist's functionality.

4. **Make the script executable**:
   ```bash
   chmod +x litassist.py
   ```


---

## ⚙️ Configuration

Create a file named config.yaml in the same directory as litassist.py:

```yaml
openrouter:
  api_key:    "YOUR_OPENROUTER_KEY"
  api_base:   "https://openrouter.ai/api/v1"   # optional

openai:
  api_key:          "YOUR_OPENAI_KEY"
  embedding_model:  "text-embedding-ada-002"

google_cse:
  api_key:  "YOUR_GOOGLE_API_KEY"
  cse_id:   "YOUR_GOOGLE_CSE_ID"

pinecone:
  api_key:     "YOUR_PINECONE_KEY"
  environment: "YOUR_PINECONE_ENV"   # e.g. "us-east-1-aws"
  index_name:  "legal-rag"
```

The tool validates all required keys on startup and performs a lightweight connectivity check against each service.


---

## 🚀 Usage

Run the tool as:

```bash
./litassist.py [GLOBAL OPTIONS] <command> [ARGS] [OPTIONS]
```

Global options:
- `--log-format [json|markdown]`: Choose audit-log format (default: markdown).
- `--verbose`: Enable debug-level logging.


---

### 1. Rapid case-law lookup (lookup)

Fetch AustLII links via Google CSE and get an IRAC-style answer from Google Gemini. The tool searches for Australian legal information on AustLII via Google Custom Search, then processes the results with Google Gemini to produce a structured legal answer citing relevant cases.

```bash
# IRAC-style answer
./litassist.py lookup "What defences exist to adverse costs orders?"

# Broader brainstorm
./litassist.py lookup "What defences exist to adverse costs orders?" --mode broad
```

Options:
- `--mode irac|broad` (default: irac): Choose between structured IRAC format or a broader creative exploration
- `--verify` (optional) run a self-critique pass on the answer for legal accuracy


---

### 2. Mass-document digestion (digest)

Processes large documents by splitting them into manageable chunks and using Claude (specifically Claude 3 Sonnet) to either summarize content chronologically or identify potential legal issues in each section.

```bash
# Chronological summary of a PDF bundle
./litassist.py digest bundle.pdf --mode summary

# Identify potential issues in a transcript
./litassist.py digest hearing.txt --mode issues
```

Options:
- `--mode summary|issues` (default: summary): Choose between chronological summary or issue identification
- `--verify` (optional) run a self-critique verification pass on each chunk's output for legal accuracy


---

### 3. Creative brainstorming (brainstorm)

Uses Grok's creative capabilities to generate ten unorthodox litigation arguments or remedies based on the facts provided. The command leverages Grok-3-beta with higher temperature settings optimized for creative legal thinking.

```bash
./litassist.py brainstorm case_facts.txt
```

Notes:
- `case_facts.txt` must be a plain-text file containing structured case facts.
- Facts are expected to include relevant details for creative argument generation.

Options:
- `--verify` (optional) run a self-critique verification pass on the generated ideas for legal accuracy


---

### 4. Auto-extract facts (extractfacts)

Processes a document to extract relevant case facts and organizes them into a structured format with ten standard headings. It uses Claude 3 Sonnet with deterministic settings (low temperature) to ensure consistent, factual extraction. The output is saved to a file named `case_facts.txt` that can be used with the `brainstorm` command.

```bash
./litassist.py extractfacts police_ebrief.pdf
```

The tool organizes facts under these headings:
1. Jurisdiction & Forum
2. Parties & Roles
3. Procedural Posture
4. Chronology of Key Events
5. Factual Background
6. Legal Issues & Applicable Law
7. Client Objectives & Constraints
8. Key Evidence
9. Known Weaknesses or Gaps
10. Commercial or Policy Context

Options:
- `--verify` (optional) run a self-critique verification pass on the extracted facts


---

### 5. Citation-rich drafting (draft)

Implements a Retrieval-Augmented Generation (RAG) workflow to create well-supported legal drafts. The process embeds document chunks, stores them in Pinecone, retrieves relevant passages using MMR re-ranking for diversity, and generates a draft with GPT-4o that incorporates these citations.

```bash
./litassist.py draft bundle.pdf "skeleton argument on jurisdictional error"
```

The RAG process follows these steps:
1. Document is broken into chunks and embedded using OpenAI's embedding model
2. Embeddings are stored in a Pinecone vector index
3. Query is embedded and relevant passages are retrieved with optional diversity re-ranking
4. GPT-4o generates a legal draft incorporating the retrieved passages as evidence

Options:
- `--verify` (optional) run a self-critique verification pass for legal accuracy
- `--diversity FLOAT` (0.0–1.0) adjust Maximal Marginal Relevance (MMR) diversity bias to control balance between relevance and diversity in retrieved passages (default: None)


---

## 📂 Audit Logging

All commands write detailed logs under logs/:
- JSON or Markdown, as chosen via `--log-format`
- Contains metadata, inputs, prompts, responses and token usage
- Persisted as `logs/<command>_YYYYMMDD-HHMMSS.{json|md}`


---

## 🛠️ Extending & Maintenance

- **Modular structure**:
  - `LLMClient` wraps LLM API calls with standardized interface for completions and verification
  - `Retriever` handles Pinecone vector search with Maximal Marginal Relevance (MMR) re-ranking
  - `read_document()` and `chunk_text()` utilities provide document handling capabilities
  - `heartbeat()` decorator for long-running functions

- **Key Class Details**:
  - `LLMClient`: Configure with model and default parameters
    ```python
    client = LLMClient("anthropic/claude-3-sonnet", temperature=0.2, top_p=0.8)
    content, usage = client.complete(messages)
    corrections = client.verify(content)  # Optional verification
    ```
  
  - `Retriever`: Vector search with diversity control
    ```python
    retriever = Retriever(pc_index, use_mmr=True, diversity_level=0.3)
    passages = retriever.retrieve(query_embedding, top_k=5)
    ```

- **Error handling**: Friendly `click.ClickException` on API failures with descriptive messages
- **Progress feedback**:
  - `click.progressbar` for multi-chunk processing
  - Heartbeat messages (30s interval) for lengthy API calls


---

## ⚖️ Disclaimer

This tool provides drafts and summaries only. All outputs should be reviewed by qualified counsel before filing or submission.

---

Enjoy accelerated, accurate legal research and drafting with LitAssist!
If you encounter issues or have suggestions, please open an issue or pull request in the repository.
