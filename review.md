# Caveman Review

> **SUPERSEDED — 28/05/2026.** This review references files removed in
> the `remove-pinecone-rag` branch (May 2026):
> `helpers/retriever.py`, `helpers/pinecone_config.py`,
> `commands/draft/rag_pipeline.py`, and the four-provider shape of
> `validate_credentials()` in `litassist/cli.py`. Line numbers and
> file paths in this document do not map to current source. Patterns
> identified here (silent fallbacks, log truncation, hardcoded retry
> counts, single-method classes) may still apply to other code paths;
> re-run the review against current `HEAD` rather than acting on the
> specific citations below.

Last updated: 30/05/2026

Axes: simplicity / over-engineering + correctness / bug risk. Format: `path:line - problem - fix`.

## Summary

- Total findings: ~140 (after pruning false positives)
- CRITICAL correctness: ~22 (silent fallbacks, race conditions, regex bugs, off-by-one, log truncation)
- SIMPLICITY: ~40 (duplication, dead code, over-engineered factories, oversized functions)
- CLAUDE.md violations: ~18 (silent fallbacks, log truncation, separator format, file size >500 LOC, hardcoded prompts in .py)
- Files >500 LOC needing refactor: 6 (brainstorm/core.py 818, citation_context.py 689, lookup/fetchers.py 615, verification_chain.py 587, llm/api_handlers.py 554, llm/client.py 513)
- Stale .bak files: 3 (digest.py.bak 22KB, strategy.py.bak 40KB, utils.py.bak 53KB) - confirmed present
- Loose `test_results_*.log` files at repo root: 10 - confirmed
- False positives excluded: slice 4 "PROMPTS.get() **kwargs runtime crash" - verified prompts.py:79,118 - `.get()` does accept and apply `**kwargs` via `current.format(**kwargs)`. Not a bug.

Top fix priorities:
1. Silent fallbacks across logging/retry/citation paths (CLAUDE.md rule violation pattern)
2. Log truncation in api_handlers and markdown_writers (CLAUDE.md "never truncate")
3. Race condition + off-by-one in citation_context.py (LOC 25, 679)
4. Greedy/unanchored regex in brainstorm + citation_context
5. Hallucination detection ordering bug in draft/core.py:220
6. Mixed document separators in brainstorm/core.py (CLAUDE.md mandates `=== NAME ===` only)

---

## Findings by package

### litassist/ core

#### litassist/cli.py
litassist/cli.py:98 - over-broad `except Exception` without re-raise/context - keep but log full traceback
litassist/cli.py:101 - `sys.exit()` with string arg - use `sys.exit(1)` after `print`
litassist/cli.py:72-194 - `validate_credentials()` 120 LOC, 3 near-identical API test blocks (OpenAI, Pinecone, Google CSE, OpenRouter) - factor common probe into helper, loop providers
litassist/cli.py:201-278 - `test_scraping_capabilities()` duplicates `error_message` formatting 3x - extract helper

#### litassist/config.py
litassist/config.py:14-17 - `ConfigError` wraps single string - use `ValueError`
litassist/config.py:206 - `_setup_api_keys()` empty body - delete or document
litassist/config.py:208-223 - `using_placeholders()` returns hardcoded-key dict - collapse to single method

#### litassist/prompts.py
litassist/prompts.py:32-37 - lazy-load gating for one YAML dir - over-engineered, eager load on construction
litassist/prompts.py:60-61, 73-74 - `os.environ.get("PYTEST_CURRENT_TEST")` to suppress warnings - couples module to pytest, use a `quiet` flag

#### litassist/citation_context.py (689 LOC - exceeds 500)
litassist/citation_context.py:25 - `_last_austlii_completion` global written without `global` declaration in caller scope; race risk under threading - wrap with `threading.Lock` or pass timestamp through call chain
litassist/citation_context.py:28-35 - `HARDCODED_LEGISLATION_URLS` dict has 5 keys all mapping to same PDF URL - collapse to one entry per unique URL
litassist/citation_context.py:53 - lazy import of `_fetch_url_content` inside hot path - hoist to module-level
litassist/citation_context.py:55 - `timeout=15` hardcoded, no retry, no status-code check, exception swallowed returning None - add retry+backoff, surface HTTP errors distinctly
litassist/citation_context.py:65-76 - broad `except Exception` returns None silently - CLAUDE.md violation; either re-raise or return distinct error sentinel so caller can branch
litassist/citation_context.py:115-119 - rate-limit gap (2-3s) read+write of `_last_austlii_completion` racy under concurrent calls - guard with lock
litassist/citation_context.py:161-175 - same silent-swallow in `_search_and_validate` - distinguish quota/auth errors from validation failures
litassist/citation_context.py:217-219 - `getattr(config, "cse_id_austlii", None)` only - CLAUDE.md says env > config.yaml > defaults; add `os.environ.get` first
litassist/citation_context.py:229-235 - `_citation_cache` unbounded growth - add LRU bound or TTL
litassist/citation_context.py:229 - `normalize_citation()` called inside `_cache_lock` - compute outside lock
litassist/citation_context.py:255-275 - `(act)` substring match collides with "ACT" jurisdiction tag - match jurisdiction abbreviations as regex `r"\(([a-z]{2,3})\)$"` against fixed set
litassist/citation_context.py:288-289 - `".pdf" in link.lower()` mixed with `"/PDF/" in link` (uppercase, no .lower) - normalize once, check once
litassist/citation_context.py:369 - `"s " in citation.lower()` matches "sunrise" - use `re.search(r'\bs\b|\bsection\b', ..., re.I)`
litassist/citation_context.py:427 - `r"\n+(?:Copyright|\xa9).*?(?:All rights reserved|$).*$"` - orphan trailing `.*$` swallows valid text - use `re.MULTILINE` and tighter end anchor
litassist/citation_context.py:457 - judgment marker regex requires literal `\n` on both sides - fails when JUDGMENT is first/last line - use `(?:^|\n)` ... `(?:\n|$)`
litassist/citation_context.py:459 - `r'\n\s*\[\d+\]\s+'` matches `[12345]` - constrain to `\d{1,3}`
litassist/citation_context.py:460 - `r'\n[A-Z\s]{10,}:\s*\n'` matches 10+ spaces or random caps - require word characters
litassist/citation_context.py:480, 482 - lazy `(.+?)` capture spans multiple sections under DOTALL - switch to lookahead end-anchor `(?=\n\n|\n\w+:)`
litassist/citation_context.py:506 - parallel-citation pattern `[^.!?]{0,200}` extremely loose, optional `\[?\d{4}\]?` - require literal `[year]`
litassist/citation_context.py:525 - `[A-Za-z\s]+` allows trailing spaces - strip captured groups, require word boundaries
litassist/citation_context.py:534 - `len(p.strip()) > 2` discards "R v Jones" - relax for known single-letter party prefixes
litassist/citation_context.py:542 - court code regex matches `[2022] A 1` (single letter) - restrict to known AustLII codes (HCA, FCA, FCC, NSWCA, ...)
litassist/citation_context.py:627 - section regex without `re.I` and assumes pre-normalized text - add flag, normalize first
litassist/citation_context.py:636-638 - `^` without `re.MULTILINE`; trailing `[A-Z]` rejects lowercase intros - use `(?:^|\n)` and drop the `[A-Z]` requirement
litassist/citation_context.py:651 - section context regex hardcoded to consumer-law keywords (`misleading|deceptive|conduct`) - drop keyword filter, widen context window
litassist/citation_context.py:665 - `if section_num in section_match.group()` substring match - `5` matches `Section 25` - use word-boundary regex
(Slice claim of off-by-one IndexError at citation_context.py:679-680 - VERIFIED FALSE: code at 679-682 has `if end_idx < len(sections) - 1: ... else: end_pos = len(text)` which already guards the access.)
litassist/citation_context.py:469 - `content[:min(earliest_pos, 1000)]` truncates silently to 1000 chars - log when no marker found, raise threshold or signal failure
litassist/citation_context.py:492-493 - `.replace(" ","").replace("[","").replace("]","")` loses smart-quote variants - use `normalize_citation()` (already imported)

#### litassist/citation_patterns.py
litassist/citation_patterns.py:18-146 - `GENERIC_SURNAMES`, `PLACEHOLDER_PATTERNS` defined but unused - delete
litassist/citation_patterns.py:152-254 - `extract_citations()` 10 near-identical regex blocks - loop over (name, pattern, handler) tuples
litassist/citation_patterns.py:265-350 - `validate_citation_patterns()` thin wrapper around `verify_all_citations` - inline at callers or document why wrapper
litassist/citation_patterns.py:265 - return type `List[str]` but caller in verification_chain unpacks as different shape - fix one or the other
litassist/citation_patterns.py:315-317 - broad `except Exception` then append message without source context - surface origin

#### litassist/verification_chain.py (587 LOC - exceeds 500)
litassist/verification_chain.py:95-120 - `run_cove_verification` makes 3 separate `LLMClientFactory.for_command()` calls - memoize or pass single client
litassist/verification_chain.py:168-170 - `command_context` set after client creation - set in init
litassist/verification_chain.py:299-389 - token-error retry loop drops largest input on `tokens` substring match, no max-attempts cap - bound iterations, log each drop, break out if no input remains
litassist/verification_chain.py:544 - `if "usage4" in locals()` - fragile, track the variable explicitly

#### litassist/timing.py
litassist/timing.py:14-78 - `@timed` mutates caller's `usage_dict` without defensive copy - copy or document side effect

#### litassist/utils/core.py
litassist/utils/core.py:31 - `@timed` exists here AND in `litassist/timing.py` - pick one, delete other (incomplete migration smell)

#### litassist/utils/legal_reasoning.py
litassist/utils/legal_reasoning.py:194 - confidence cast to int with no bounds check - clamp `0..100`
litassist/utils/legal_reasoning.py:333 - `noverify` inverts `verify_flag` - confusing double negative, rename or invert at the boundary

#### litassist/utils/truncation.py
litassist/utils/truncation.py:174 - `manager.attempt` only incremented in error path - increment on each iteration entry, not error

#### litassist/utils/file_ops.py
litassist/utils/file_ops.py:82-94 - `is_text_file()` checks .txt/.md only - inline at the one caller, this is not worth a function

#### litassist/helpers/retriever.py
litassist/helpers/retriever.py:60-81 - silent fallback to `MockPineconeIndex` on any exception - CLAUDE.md violation, must surface
litassist/helpers/retriever.py:152 - `getattr(self, "use_mmr", False)` after `__init__` sets it - drop the getattr

#### litassist/helpers/pinecone_config.py
litassist/helpers/pinecone_config.py:130-135 - broad `except` no re-raise, silent wrapper fallback - CLAUDE.md violation
litassist/helpers/pinecone_config.py:34-41, 68-72, 94-106 - `type("ClassName", (), {...})()` dynamic class 3x - replace with `dataclass` or `namedtuple`

---

### litassist/llm

#### litassist/llm/api_handlers.py (554 LOC - exceeds 500)
litassist/llm/api_handlers.py:266-274 - `requests.ConnectionError` AND `requests.exceptions.ConnectionError` listed in same retry tuple - same class, drop one
litassist/llm/api_handlers.py:283 - function `_call_with_streaming_wrap` does not stream, only catches stream errors - rename `_call_with_error_handling`
litassist/llm/api_handlers.py:295-303 - `except Exception: pass` around `log_task_event` - CLAUDE.md violation, log failure to stderr
litassist/llm/api_handlers.py:327 - `if hasattr(resp, "error") and resp.error:` - empty dict `{}` is falsy and would be silently ignored - use `is not None`
litassist/llm/api_handlers.py:360-375 - `resp.choices[0]` access without `len(resp.choices) > 0` guard - IndexError risk
litassist/llm/api_handlers.py:377-388 - second `except Exception: pass` around inbound-response log - same fix
litassist/llm/api_handlers.py:397-455 - broad `except Exception` whose tail can `raise StreamingAPIError(...)` then unconditional `raise` - restructure as if/elif/else; use `raise ... from e` to preserve chain
litassist/llm/api_handlers.py:402-403 - `import time`, `from litassist.logging import save_log` inside exception handler - hoist to top
litassist/llm/api_handlers.py:410 - `extra_body if 'extra_body' in locals() else None` - variable always defined here, drop the locals() guard
litassist/llm/api_handlers.py:415 - error message `[:250]` - CLAUDE.md "never truncate" - drop slice
litassist/llm/api_handlers.py:450-454 - `raise StreamingAPIError(...)` without `from e` - chain it
litassist/llm/api_handlers.py:457-522 - `before_retry_callback` 6 nested try/excepts, multiple bare excepts - CLAUDE.md violation, simplify and surface failures
litassist/llm/api_handlers.py:458-459 - `if retry_state.attempt_number > 1` guard redundant; callback only fires after first failure - remove
litassist/llm/api_handlers.py:465-466 - `import time`, `import save_log` inside callback fired every retry - hoist
litassist/llm/api_handlers.py:469, 482-515 - hardcoded `/5` in 7 user messages, separate from `stop_after_attempt(5)` at 525 - extract `MAX_ATTEMPTS = 5` constant
litassist/llm/api_handlers.py:472 - `error_str[:1000]` "for summary" alongside `full_error: error_str` - CLAUDE.md "never truncate", drop the summary slice
litassist/llm/api_handlers.py:515 - error message `[:150]` in user-visible warning - drop slice
litassist/llm/api_handlers.py:517-522 - bare `except Exception: pass` wrapping the whole callback body - silently nukes retry logging; let exceptions propagate or log to stderr
litassist/llm/api_handlers.py:539-554 - `import time`, `import save_log` inside outer except - hoist; also no error handling if `save_log` itself fails

#### litassist/llm/client.py (513 LOC - exceeds 500)
litassist/llm/client.py:318-352 - fallback to non-tools call on `"tools" in str(e).lower()` - fragile string match, vendor-specific - catch the specific exception/code instead
litassist/llm/client.py:432-437 - `except (TypeError, AttributeError)` for missing `tool_calls` - `AttributeError` only is the real signal; drop `TypeError`
litassist/llm/client.py:495-511 - `save_log` runs even when message extraction failed - log the failure mode explicitly so the audit trail is complete

#### litassist/llm/citation_handler.py
litassist/llm/citation_handler.py:45 - bare `print()` to stdout - use ANSI helpers (`warning_message` etc.)
litassist/llm/citation_handler.py:59-66 - `PROMPTS.get(...)` in try/except catching only `ValueError` - `KeyError` from missing template is uncaught
litassist/llm/citation_handler.py:79-95 - `handle_retry_failure` raises after `print` - print can fail, masking the raise

#### litassist/llm/factory.py
litassist/llm/factory.py:50-58 - module-level `_MODEL_CONFIGS_CACHE` mutable, no lock - race on concurrent first-load - guard with `threading.Lock`
litassist/llm/factory.py:121-125 - sequential `pop()` for `enforce_citations`, `disable_tools` - pop with `default=None` if optional, document if required

#### litassist/llm/response_parser.py
litassist/llm/response_parser.py:24-26 - `message.content or ""` returns empty string on falsy non-empty content - use `if message.content is None: return ""`

#### litassist/llm/retry_handler.py
litassist/llm/retry_handler.py:72 - `from .client import get_model_parameters` inside function - circular-import smell - move to `parameter_handler` if that's where it belongs

#### litassist/llm/verification.py
litassist/llm/verification.py:119-126 - `validate_citations(enable_online=False)` results still appended into `issues` - gate the append behind the flag
litassist/llm/verification.py:308 - `from litassist.citation_patterns import validate_citation_patterns` - confirm `validate_citation_patterns` is exported, otherwise this raises at import
litassist/llm/verification.py:407-412 - dynamic `type()` class creation, mutates `__class__` - replace with explicit subclass or composition

---

### litassist/citation

#### litassist/citation/austlii.py
litassist/citation/austlii.py:98-110 - `save_log` called inside exception handler can mask the original exception - wrap `save_log` in its own try/except

(Slice claim of `response.get()` AttributeError at 72-76 - VERIFIED FALSE: file uses `response.status_code` and never calls `.get()` on the Response.)

#### litassist/citation/cache.py
litassist/citation/cache.py:12 - module-level dict `_citation_cache` with `threading.Lock`, unbounded growth - add LRU bound or TTL eviction

#### litassist/citation/google_cse.py
litassist/citation/google_cse.py:49-67 - bracket/paren cleanup duplicated - extract helper
litassist/citation/google_cse.py:120-149 - broad `except Exception`, `save_log`, then silent return - CLAUDE.md violation, surface error

#### litassist/citation/verify.py
litassist/citation/verify.py:163-164 - `except Exception: pass` - CLAUDE.md violation
litassist/citation/verify.py:294-338 - `is_core_citation()` uses `text.find()` without checking for `-1` before comparison - guard explicitly

---

### litassist/logging

#### litassist/logging/__init__.py
litassist/logging/__init__.py:44-93 - `save_log()` single-attempt write, no retry on `IOError` - wrap in retry, log failure to stderr
litassist/logging/__init__.py:72-74 - `config.log_format` default `"json"` if `get_config()` fails outside click context - log the fallback decision

#### litassist/logging/json_utils.py
litassist/logging/json_utils.py:26-34 - `research_analysis` special-case accesses `combined_content` without key check
litassist/logging/json_utils.py:40-42 - recursive `sanitize_for_json(obj.__dict__)` no cycle detection - track visited ids

#### litassist/logging/markdown_writers.py
litassist/logging/markdown_writers.py:13, 66, 85, 100 - `f"{tag}  {ts}"` double space - collapse to single
litassist/logging/markdown_writers.py:148, 164, 214, 226, 419 - string truncation in markdown output - CLAUDE.md "never truncate, log every request in full" - remove slices
litassist/logging/markdown_writers.py:319 - comment claims "no truncation for legal compliance" yet line 226 truncates - comment lies, fix code

#### litassist/logging/output_saver.py
litassist/logging/output_saver.py:48-49 - `re.sub(r"[^\w\s-]", ...)` then `re.sub(r"[-\s]+", ...)` - second pass undoes work - combine into single substitution
litassist/logging/output_saver.py:57 - `open()` no encoding/error handler - use `encoding="utf-8", errors="replace"`

#### litassist/logging/task_events.py
litassist/logging/task_events.py:54-59 - `except Exception` silently sets `model_suffix=""` - CLAUDE.md violation

---

### litassist/commands/lookup

#### litassist/commands/lookup/fetchers.py (615 LOC - exceeds 500)
litassist/commands/lookup/fetchers.py:98-113 - broad `except Exception` swallows Jina errors, returns empty string - CLAUDE.md violation
litassist/commands/lookup/fetchers.py:202-217 - same pattern on AustLII direct fetch - surface errors
litassist/commands/lookup/fetchers.py:316-320 - `_fetch_gov_legislation` -> `_fetch_via_jina` -> empty string fallback chain - return error sentinel or raise

#### litassist/commands/lookup/processors.py
litassist/commands/lookup/processors.py:29-453 - `LookupProcessor` is stateless orchestration over read-only `self.config` - convert to module-level functions OR document why class stays

---

### litassist/commands/brainstorm (1,401 LOC pkg)

#### litassist/commands/brainstorm/core.py (818 LOC - biggest file)
litassist/commands/brainstorm/core.py:49-61 - strategy header regex tries 4 formats then falls back to blank-line split - CLAUDE.md "prefer prompt engineering over local parsing", enforce single `=== STRATEGY N ===` marker
litassist/commands/brainstorm/core.py:53 - header regex: 53 chars, 4 alt formats, unanchored - debug nightmare
litassist/commands/brainstorm/core.py:70-121 - `_annotate_strategies_with_verification` 52 LOC, complexity 4+ - split annotation building
litassist/commands/brainstorm/core.py:105 - `strategy_id = f"{strategy_type}_{i}"` (i 1-indexed) but plausibility response keys may be 0-indexed - validate response schema
litassist/commands/brainstorm/core.py:111 - `f"(confidence: {confidence}%)"` no type guard, may format dict/list - coerce or check
litassist/commands/brainstorm/core.py:126 - `dict[str, str] = None` invalid type hint - `dict[str, str] | None`
litassist/commands/brainstorm/core.py:178-181 - second `.format()` after `PROMPTS.get()` already formats - risk if template contains literal `{}` - load template, format once
litassist/commands/brainstorm/core.py:189 - `PROMPTS.get(... plausibility_system)` returns raw template if YAML uses `{}` - if no kwargs intended, fine; document
litassist/commands/brainstorm/core.py:201 - `re.search(r'\{[\s\S]*\}', response)` greedy - extracts first-to-last brace - enforce response schema, parse directly
litassist/commands/brainstorm/core.py:227 - hardcoded model name `"openai/o3-pro"` in log message - pull from client config
litassist/commands/brainstorm/core.py:242-385 - `verify_and_annotate_strategies` 144 LOC - decompose
litassist/commands/brainstorm/core.py:362-364 - `## ORTHODOX STRATEGIES` markdown header used as document separator - CLAUDE.md mandates only `=== NAME ===`
litassist/commands/brainstorm/core.py:362-365 - header detection logic duplicated for orthodox/unorthodox - extract helper
litassist/commands/brainstorm/core.py:375 - risk counting trusts `assessment.get("risk", "UNKNOWN")` for missing keys - validate plausibility schema upfront
litassist/commands/brainstorm/core.py:424 - `def brainstorm(facts, side, area, research, verify, output)` no type hints; function body 395 LOC - type-annotate, extract sub-flows
litassist/commands/brainstorm/core.py:462-469, 539-544, plus ~15 more sites - `except Exception: pass` swallowing `log_task_event` - CLAUDE.md violation
litassist/commands/brainstorm/core.py:505 - `=== SOURCE: {source} ===` correct, but inconsistent with line 362 ## headers - standardize
litassist/commands/brainstorm/core.py:669 - `r"## Verified and Corrected Document\s*\n(.*)"` exact-match, fails silently on header drift - enforce structured output
litassist/commands/brainstorm/core.py:807 - hint `'open "{output_file}"'` macOS-only - say "open with editor"

---

### litassist/commands/digest

#### litassist/commands/digest/core.py
litassist/commands/digest/core.py:88-96, 103-112, 142-149, 160-168, 184-191, 213-220, 331-339 - 7 try/except pass blocks around `log_task_event` break audit trail - CLAUDE.md violation
litassist/commands/digest/core.py:179-180 - single-chunk vs multi-chunk paths near-identical try/excepts - unify
litassist/commands/digest/core.py:361 - dynamic key `f"processing.digest.consolidation_cross_file_{mode}"` - CLAUDE.md flags dynamic f-string keys, document or hardcode both branches

---

### litassist/commands/extractfacts

#### litassist/commands/extractfacts/core.py
litassist/commands/extractfacts/core.py:138-139 - verification auto-enabled even without `--verify` flag, comment on 127 misleading - clarify auto-enable logic, update comment

---

### litassist/commands/strategy

#### litassist/commands/strategy/ranker.py
litassist/commands/strategy/ranker.py:13-14 - `@timed` decorator on function whose body already times its work - drop one
#### litassist/commands/strategy/document_generator.py
litassist/commands/strategy/document_generator.py:85-91 - malformed multi-line f-string, extra brace nesting - flatten to `doc_context.format(...) + "\n\n" + doc_formats.get(...)`

---

### litassist/commands/draft

#### litassist/commands/draft/core.py
litassist/commands/draft/core.py:220 - hallucination detection runs AFTER verification - CLAUDE.md anti-hallucination rule expects detection BEFORE verify so placeholders propagate - move call before `verify_content_if_needed`

---

### litassist/commands/verify

#### litassist/commands/verify/reasoning_handler.py
litassist/commands/verify/reasoning_handler.py:73-74 - silent fallback when `client is None` but trace exists - raise `click.ClickException`
litassist/commands/verify/reasoning_handler.py:141-206 - `cases_to_include.pop()` inside retry loop without delay or attempt cap (5) - log dropped cases, add delay, lower cap to 3
#### litassist/commands/verify/soundness_checker.py
litassist/commands/verify/soundness_checker.py:128-142 - same retry/pop pattern - same fix
#### litassist/commands/verify/formatters.py
litassist/commands/verify/formatters.py:46-59 - regex assumes `1.` numbering - accept `- ` and `: ` bullets, raise on missing section
#### litassist/commands/verify/verify.py
litassist/commands/verify/verify.py:92 - bare `except Exception` - narrow

---

### litassist/commands/verify_cove

#### litassist/commands/verify_cove/core.py
litassist/commands/verify_cove/core.py:112-130 - three fallback saves with same prefix, no logging on trigger - log each, raise if all fail
#### litassist/commands/verify_cove/fallback_handler.py
litassist/commands/verify_cove/fallback_handler.py:14-128 - three identical save attempts (preflight, fallback, final_safeguard) call same function with same params - collapse to single save with explicit retry policy

---

### litassist/commands/counselnotes

NOTE: slice review claimed `PROMPTS.get(..., **kwargs)` would crash at runtime. Verified false: `prompts.py:79,118` accepts `**kwargs` and applies `.format(**kwargs)`. The 6 reported "PROMPTS.get runtime bugs" in counselnotes/, extraction_processor, barbrief brief_generator are NOT bugs.

Real findings:
(none beyond the false-positive cluster)

---

### litassist/commands/barbrief

#### litassist/commands/barbrief/document_reader.py
litassist/commands/barbrief/document_reader.py:20, 76 - type hint `any` (lowercase builtin) instead of `typing.Any` - change to `Any`
#### litassist/commands/barbrief/section_builder.py
litassist/commands/barbrief/section_builder.py:7 - `@timed` on dict-construction function - remove

---

### litassist/commands/caseplan

#### litassist/commands/caseplan/plan_generator.py
[FIXED] litassist/commands/caseplan/plan_generator.py - nested `@timed` on `_generate_plan` removed; the `caseplan` command remains `@timed`.
#### litassist/commands/caseplan/budget_assessor.py
[FIXED] litassist/commands/caseplan/budget_assessor.py - nested `@timed` on `_assess_budget` removed; same fix.

---

### tests/unit

#### tests/unit/test_draft_command_comprehensive.py
tests/unit/test_draft_command_comprehensive.py:198 - `assert True` trivially passing - replace with real assertion or delete

All other 40 test files: clean. No real-API calls in pytest, mocking sane, no obviously stale tests, conftest fixtures isolated.

---

### litassist/prompts/*.yaml

Cosmetic across all 14 files (LOW priority):
- Trailing whitespace on multiple lines, 14/14 files
- 98 lines exceed 120 chars without justification comment

Higher:
- litassist/prompts/verification.yaml:97 - single line 341 chars (`heavy_verification`) - split into multi-line YAML literal block (`|` or `>`)
- litassist/prompts/verification.yaml:99 - 237 chars continuation - same
- litassist/prompts/processing.yaml:66 - 233 chars (`chunk_analysis_summary`) - split
- litassist/prompts/documents.yaml:176 - 254 chars - split
- litassist/prompts/analysis.yaml:38, 53, 65 - `{strategy_count}`, `{outcome}`, `{remaining_strategies_list}` placeholders not documented inline - add comment listing required substitutions
- litassist/prompts/barbrief.yaml:128 - `{hearing_type}` undocumented - same fix

No duplicate keys, no non-standard separators detected, no hardcoded model names in prompt bodies (only in user-facing error text).

---

## Deep dive cross-cuts

### Pattern: silent fallbacks (CLAUDE.md violation)
Sites: retriever.py:60-81, pinecone_config.py:130-135, citation_context.py:65-76, citation_context.py:161-175, citation/google_cse.py:120-149, citation/verify.py:163-164, lookup/fetchers.py:98-113, lookup/fetchers.py:202-217, lookup/fetchers.py:316-320, llm/api_handlers.py 295-303, 377-388, 517-522, logging/task_events.py:54-59, brainstorm/core.py ~17 sites, digest/core.py 7 sites, verify/reasoning_handler.py:73-74, verify/verify.py:92, verify_cove/core.py:112-130, citation_patterns.py:315-317.

### Pattern: log truncation (CLAUDE.md "never truncate")
Sites: logging/markdown_writers.py 148, 164, 214, 226, 419; llm/api_handlers.py 415, 472, 515; citation_context.py:469.

### Pattern: import inside exception/function body (perf + circular-import smell)
Sites: llm/api_handlers.py 402-403, 465-466, 543-544; citation_context.py:53; llm/retry_handler.py:72.

### Pattern: hardcoded retry/attempt counts
Sites: llm/api_handlers.py 7 occurrences of literal `5`; verify/reasoning_handler.py and soundness_checker.py both hardcode 5 attempts.

### Pattern: classes with single-method or stateless behaviour
Sites: lookup/processors.py:LookupProcessor; helpers/pinecone_config.py:PineconeWrapper (light wrapper); config.py:ConfigError.

---

## Cleanup punch list (delete candidates, ask user before destructive action)

- litassist/commands/digest.py.bak (22KB, dated 2025-08-28)
- litassist/commands/strategy.py.bak (40KB, dated 2025-08-29)
- litassist/utils.py.bak (53KB, dated 2025-08-25)
- 10x test_results_*.log at repo root (20251211 through 20260225)
- test_facts.txt, test_case_simple.txt at repo root (loose test fixtures)
- test_output_option.sh at repo root (loose script)

---

## Verification of this report

Spot-checked findings against actual code:
- prompts.py:79,118 - `def get(self, template_key: str, **kwargs)` and `current.format(**kwargs)` confirmed; slice 4 PROMPTS.get() runtime-crash claim REJECTED.
- citation_context.py:679-680 - slice deep-dive IndexError claim REJECTED, guard is correct.
- citation/austlii.py:72-76 - `response.get()` AttributeError claim REJECTED, no such call exists.
- llm/api_handlers.py:410 `extra_body if 'extra_body' in locals() else None` - CONFIRMED smell.
- llm/api_handlers.py:415 `error_str[:250]` truncation - CONFIRMED.
- tests/unit/test_draft_command_comprehensive.py:198 `assert True` - CONFIRMED.
- commands/draft/core.py - CONFIRMED ordering bug: `verify_content_if_needed` at line 190, `detect_factual_hallucinations` at line 220 (hallucination check runs after verification).
- .bak files exist (size+date confirmed via ls).
- test_results_*.log count: 10 confirmed at repo root.

3 false positives identified and excluded from per-package findings (PROMPTS.get kwargs cluster, citation_context.py:679, austlii.py:72-76).
