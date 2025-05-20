# LitAssist

**LitAssist** is a command-line tool for automated litigation support workflows, tailored to Australian law. It leverages large language models (LLMs) and a managed vector store to help you:

- **Rapid case-law lookup** (Google Custom Search + Google Gemini)  
- **Mass-document digestion** (Chronological summaries or issue-spotting via Claude)  
- **Creative brainstorming** (Unorthodox legal strategies via Grok)  
- **Automatic extraction of case facts** into a structured file  
- **Citation-rich drafting** (Retrieval-Augmented Generation with GPT-4o)  
- **Strategic analysis** (Generate legal options and draft documents)  

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
   pip install -r requirements.txt
   ```
   
   Or install packages individually:
   ```bash
   pip install click openai==0.28.1 pinecone-client==2.2.4 PyPDF2 google-api-python-client pyyaml requests reportlab
   ```

4. **Setup configuration**:
   ```bash
   cp config.yaml.template config.yaml
   ```

5. **Make the script executable**:
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

**Note**: If you see warnings about Google API file_cache during startup, these are automatically suppressed and won't affect functionality.


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

Search for legal information using either Google Custom Search (on AustLII) or Jade.io, then process the results with Google Gemini to produce a structured legal answer citing relevant cases.

```bash
# IRAC-style answer using Google CSE
./litassist.py lookup "What defences exist to adverse costs orders?"

# Broader exploration using Jade
./litassist.py lookup "What defences exist to adverse costs orders?" --mode broad --engine jade
```

Options:
- `--mode [irac|broad]` (default: irac): Choose between structured IRAC format or broader creative exploration
- `--verify`: Enable self-critique verification pass for legal accuracy
- `--engine [google|jade]` (default: google): Search engine - 'google' for AustLII via CSE, 'jade' for Jade.io


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

**Note on non-legal documents**: While primarily designed for legal content, the `digest` command can process any text document:
- For non-legal documents (like bank statements or purchase agreements), use `--mode summary` for better results
- The system is optimized for legal analysis, so outputs for non-legal content may attempt to frame information in legal terms
- Financial documents will receive chronological summaries but may have legal perspectives applied


---

### 3. Comprehensive legal strategy brainstorming (brainstorm)

Uses Grok's creative capabilities to generate a comprehensive set of litigation strategies based on the facts provided, tailored to your specific party side and legal area. The command leverages Grok with optimized temperature settings for creative legal thinking.

```bash
./litassist.py brainstorm case_facts.txt --side plaintiff --area civil

# Example for family law
./litassist.py brainstorm case_facts.txt --side respondent --area family --verify
```

The command produces three sections:
1. 10 orthodox legal strategies commonly used in the specified legal area
2. 10 unorthodox but potentially effective strategies that could work
3. A shortlist of 3-5 strategies (from either category) most likely to succeed

Required parameters:
- `--side`: Which side you are representing (options depend on area):
  - Criminal cases: `accused` only
  - Civil/Commercial cases: `plaintiff` or `defendant`
  - Family/Administrative cases: `plaintiff`, `defendant`, or `respondent`
- `--area`: Legal area - `criminal`, `civil`, `family`, `commercial`, or `administrative`

Options:
- `--verify`: Enable self-critique verification pass on generated strategies

**Compatibility**: The command validates side/area combinations and will display a warning if you use uncommon pairings (e.g., "plaintiff" in criminal matters) but will still proceed with strategy generation.


---

### 4. Auto-extract facts (extractfacts)

Processes a document to extract relevant case facts and organizes them into a structured format with ten standard headings. It uses Claude 3 Sonnet with deterministic settings (low temperature) to ensure consistent, factual extraction. The output is saved to a file named `case_facts.txt` that can be used with the `brainstorm` command.

The output is saved to a file named `case_facts.txt` that can be used with both the `brainstorm` and `strategy` commands.

```bash
./litassist.py extractfacts police_ebrief.pdf
```

The tool organizes facts under these headings:
1. Parties
2. Background
3. Key Events
4. Legal Issues
5. Evidence Available
6. Opposing Arguments
7. Procedural History
8. Jurisdiction
9. Applicable Law
10. Client Objectives

**Note on non-legal documents**: The `extractfacts` command is specifically designed for legal documents and will attempt to fit any input into the 10-heading legal framework. For non-legal documents:
- Commercial agreements may map reasonably well to the structure
- Financial documents or personal records will have forced categorization
- Consider pre-processing non-legal documents with `digest --mode summary` first, then manually creating the case_facts.txt file

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

### 6. Generate legal strategy (strategy)

Generates comprehensive legal strategy options and draft documents tailored to Australian civil matters. The command analyzes case facts structured according to the LitAssist ten-heading format and produces strategic options with probability assessments, recommended next steps, and appropriate draft legal documents to achieve the desired outcome.

```bash
# Generate strategy options for specific outcome
./litassist.py strategy case_facts.txt --outcome "Obtain interim injunction against defendant"

# Another example
./litassist.py strategy case_facts.txt --outcome "Resist enforcement of liquidated damages clause"
```

The command produces three sections:
1. Strategic options with probability of success and critical hurdles
2. Recommended next steps in priority order
3. A draft legal document (claim, application, or affidavit) tailored to the outcome

Required parameters:
- `--outcome`: A single sentence describing the desired outcome

Notes:
- `case_facts.txt` must follow the ten-heading LitAssist structure (as produced by `extractfacts`)
- The command uses GPT-4o for deterministic legal analysis and document generation
- **Important**: The `strategy` command strictly enforces the 10-heading format and will reject any input that doesn't contain all required headings

**For mixed document sets**:
1. Process each document using `digest` first
2. Manually combine relevant information into a `case_facts.txt` file following the 10-heading structure
3. Only then run the `strategy` command with your desired outcome


---

## 📂 Audit Logging

All commands write detailed logs under logs/:
- JSON or Markdown, as chosen via `--log-format`
- Contains metadata, inputs, prompts, responses and token usage
- Persisted as `logs/<command>_YYYYMMDD-HHMMSS.{json|md}`


---

## 🔒 Additional Features

### Progress Indicators
- Long-running operations (LLM calls) display heartbeat messages every 30 seconds
- Document processing shows progress bars for multi-chunk operations

### Automatic Retries
- The `lookup` command automatically retries once if citations are missing
- Network errors are caught and displayed with user-friendly messages

### Validation & Warnings
- Configuration files are validated on startup with clear error messages
- Placeholder API keys are detected and operations gracefully degrade
- Parameter compatibility warnings help avoid terminology mistakes

### Mock Mode
- When using placeholder credentials, some commands enter mock mode
- Allows testing the CLI without active API subscriptions

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
