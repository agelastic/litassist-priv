# Lookup Command Enhancement Roadmap

Last updated: 27/05/2026

## Current State (May 2026)

The lookup command is a modular system at `litassist/commands/lookup/` that searches Jade and AustLII via Google CSE, fetches accessible content, and synthesises results with `google/gemini-3.5-flash` (per `litassist/llm/model_configs.yaml`).

### Implemented features

#### User-facing options
- `--mode irac|broad` -- structured IRAC analysis or wider discursive answer
- `--extract citations|principles|checklist` -- extract a specific output type via prompt engineering
- `--comprehensive` -- exhaustive analysis using up to 40 sources across Jade, AustLII, and secondary CSE
- `--context` -- additional context string appended to the query
- `--output` -- custom output filename prefix
- `--no-fetch` -- skip content fetching, analyse URLs and search snippets only

#### Transport layer (May 2026 rework, see Fetcher chain below)
- Cloudflare-resilient fetching via `curl_cffi` (Chrome 136 TLS impersonation) — defeats the TLS fingerprint detection that newly applied to AustLII
- AustLII PDF URLs transparently rewritten to their `.html` siblings (Cloudflare blocks AustLII PDFs for all tested Python clients; HTML siblings stay reachable)
- RTF document handling: URL fetches with RTF magic bytes and local `.rtf` files both extract via `striprtf` (via `litassist/utils/rtf.py`)
- PDF extraction via `pdfplumber` (no page cap; binary truncation deferred to the orchestration layer)
- legislation.gov.au `/latest/text` ToC-link follow with hostname-based safety check
- SPA-shell detection (Angular / React / Vue / Next / Nuxt markers + text/HTML ratio) routes JS-rendered sites to Jina
- Content-Type guard rejects non-text payloads before they reach BS4

#### Audit and observability
- Full audit logging of every LLM request, response, and fetch attempt
- `fetch_attempt` markdown logs include `http_status`, `content_size`, `rejection_reason`, `cf_mitigated`, `cf_ray`, and `rewrite_target` fields — distinguishes real Cloudflare challenges (HTTP 403 + `cf-mitigated: challenge`) from detector false positives (HTTP 200 + no `cf-mitigated`)
- Microsecond-resolution timestamps on audit log filenames prevent collisions between the curl_cffi-failure record and the immediate-Jina-fallback record
- Drop-largest truncation when fetched content exceeds model context

#### Infrastructure
- Prompt templates in `litassist/prompts/lookup.yaml`
- LLMClientFactory for centralised model configuration

### Architecture

```
__init__.py   -- CLI entry point, orchestration
search.py     -- Google CSE queries (Jade, AustLII, secondary)
fetchers.py   -- URL content fetching: curl_cffi primary, Jina fallback,
                 PDF/RTF magic-byte routing, AustLII PDF -> HTML rewrite,
                 challenge / SPA-shell / Content-Type / gibberish detection
processors.py -- Prompt building, LLM interaction, output saving
error_handlers.py -- User-facing error guidance
```

Configuration in `litassist/llm/model_configs.yaml` under the `lookup` key.

### Fetcher chain (post May 2026 rework)

The single-pipeline `_fetch_url_content` in `fetchers.py` handles every URL:

1. **Local file path** → `read_document` (PDF via pdfplumber, RTF via `litassist/utils/rtf.py`, text directly).
2. **`jade.io` main domain** → skipped (cookie-gated; future cookie-reuse work tracked in TODO.md `[SOON]` entry).
3. **`ndfv.jade.io`** → Jina with `/download` URL rewrite.
4. **AustLII `*.pdf` URL** → rewritten to `.html` sibling before the HTTP fetch. AustLII Cloudflare policy blocks PDF paths for all tested Python clients (curl_cffi multiple Chrome profiles, Playwright + playwright_stealth, patchright, nodriver, Camoufox — 16+ approaches all returned challenge body). The HTML sibling stays reachable. URL parsing uses `urlsplit` to preserve query strings and fragments.
5. **AustLII rate limit** → 2–3 s random delay between requests (measured from previous request completion).
6. **`curl_cffi` GET** with Chrome 136 TLS impersonation. Replaces direct `requests` calls; defeats Cloudflare's TLS fingerprint detection.
7. **PDF magic bytes** (`%PDF`) → `_extract_pdf_text` via pdfplumber.
8. **RTF magic bytes** (`{\rtf`) → `extract_rtf_text` via striprtf.
9. **Content-Type guard** → non-text payloads (`application/javascript`, `application/json`, etc.) route to Jina; prevents long-garbage text passing through to BS4.
10. **legislation.gov.au `/latest/text`** → follow the OEBPS document link via curl_cffi to retrieve the real document (the URL itself returns a ToC page). Hostname check via `urlsplit().hostname` (not substring) prevents attacker URLs with `legislation.gov.au` in query string from triggering the follow.
11. **BS4 text extraction** (strip scripts, styles, meta, link, noscript).
12. **Unusable response detection** → Jina fallback fires on:
    - Cloudflare challenge markers (`_looks_like_challenge_page`) — phrase-level matches, not bare substrings (the bare `"captcha"` marker was false-positive-flagging fedcourt practice-note pages with Google reCAPTCHA widgets).
    - SPA shell (`_looks_like_spa_shell`) — Angular/React/Vue/Next/Nuxt framework markers with short extracted text, or text/HTML ratio below 5%.
    - Gibberish — extracted text under 100 chars. Newline-count heuristic dropped in May 2026 after rejecting Nuxt server-pre-rendered pages using Unicode word-joiner separators.
13. **Otherwise** → return cleaned text.

#### Audit logging
Every step writes a `fetch_attempt` log entry. Markdown renderer in `litassist/logging/markdown_writers.py` includes `http_status`, `content_size`, `rejection_reason`, `cf_mitigated`, `cf_ray`, `rewrite_target` — enough to distinguish a real Cloudflare challenge (HTTP 403 + `cf-mitigated: challenge`) from a detector false positive (HTTP 200 + no `cf-mitigated`).

#### Known limitations
- **AustLII PDFs with no HTML sibling** (notably `legis/cth/bill_em/`) return 404 on the substitution and content is unrecoverable.
- **Jade.io main domain** is skipped; awaiting cookie-reuse implementation.
- **Jina's outbound IPs** are themselves Cloudflare-challenged on some AU government sites (notably AustLII PDFs), so Jina is not a guaranteed escape hatch.

---

## Roadmap

### 1. Add `--min-year` filter

**Value:** Practitioners often need only recent authorities. Currently they must read through the full output to filter by date.

**Approach:** Prompt engineering only. Add a click option and append a line to the user prompt:

```
Focus on authorities from {min_year} onwards. Older cases may be cited only if they remain leading authorities.
```

**Scope:** One click option in `__init__.py`, one line in `processors.py:build_prompt()`. No schema, no parsing.

### 2. Lookup-to-verify pipeline

**Value:** After `--extract citations`, the user often wants to verify those citations are real. Today this requires manually copying them into a file and running `litassist verify`.

**Approach:** The `--extract citations` prompt already produces a clean one-citation-per-line format. The output file from lookup can be passed directly to the verify command:

```bash
litassist lookup "bail exceptional circumstances NSW" --extract citations --output bail_cases
litassist verify outputs/bail_cases_citations_*.txt
```

**What needs to happen:**
- Confirm the extraction prompt produces a format the verify command can parse (one citation per line, no bullet prefixes that break parsing)
- If needed, tighten the extraction prompt to produce bare citations without bullet characters
- Document the pipeline in LOOKUP_USE_CASES.md

**Scope:** Prompt adjustment in `lookup.yaml` (extraction_instructions.citations), possibly minor parsing tolerance in the verify command. No schema, no new classes.

### 3. Lookup-to-draft integration

**Value:** The brainstorm-to-strategy pipeline (`--strategies <file>`) proves that cross-command file-based integration works. Lookup output could feed into the draft command the same way.

**Approach:** Follow the existing pattern:

1. Add `--research <file>` option to the draft command
2. The file is a plain-text lookup output (not JSON)
3. Draft reads the file and appends it to the prompt as research context
4. No schema, no JSON interchange -- same pattern as `--strategies`

**What needs to happen:**
- Add `--research` option to `litassist/commands/draft/core.py`
- Read the file content and include it in the draft prompt as a "Research context" section
- Update draft prompt templates if needed
- Add a workflow example to LOOKUP_USE_CASES.md

**Scope:** Changes to the draft command, not lookup. Lookup output format stays as-is.

---

## Ideas evaluated and rejected

The following ideas from the original design were evaluated against the project's minimal-changes philosophy and found to be over-engineering for the current stage:

| Idea | Reason for rejection |
|------|---------------------|
| LookupResult structured schema | Requires local parsing of LLM output -- contradicts "prefer prompt engineering over local parsing" |
| LookupPostProcessor class | NLP pipeline to extract case names, courts, hierarchy from text -- exactly the regex/parsing the project rejects |
| `--format` option (text/structured/JSON) | Redundant with `--extract`; JSON output has no consumer |
| `--legal-area` with area-specific templates | LLM already adapts based on question content; `--context` handles ambiguity |
| `--court-level` filtering | Marginal value; can be achieved with `--context "focus on High Court and Federal Court authorities"` |
| `--save-for draft/strategy` with JSON | Premature without consumer-side changes; plain text integration (item 3 above) is simpler |
| `--max-cases` | Already controlled by CSE result count and model context |
| Court hierarchy ranking | Would require reliable extraction of court identifiers -- parsing problem |
| Relevance scoring | LLM already ranks by relevance in its output; numeric scores add false precision |

These ideas are not inherently bad -- they are premature. If the three roadmap items above prove their value, some of these could be revisited.

---

## Design principles

Any enhancement to lookup must satisfy:

1. **Prompt engineering over local parsing** -- ask the LLM for the right format, do not parse its output into structures
2. **Fail fast** -- if the output format is wrong, surface it; do not add fallback parsing
3. **File-based integration** -- follow the brainstorm-to-strategy pattern (plain text via click.File)
4. **No new abstractions** -- no result schemas, no manager classes, no post-processing pipelines
5. **One change at a time** -- each item above is independently useful and independently shippable
