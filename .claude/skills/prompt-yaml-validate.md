---
name: Prompt YAML Validate
description: Audit litassist/prompts/ and Python sources for prompt-handling rule violations
---

## Prompt YAML Validate

Enforces the four CLAUDE.md rules that govern how prompts live in this codebase:

- **CLAUDE.md:35** — Validate all `.yaml` changes with a linter, especially under `litassist/prompts/`.
- **CLAUDE.md:38** — Do not hardcode prompts in Python (except trivial one-liners). Keep all prompts in YAML. Access via `PROMPTS.get()` with stable keys.
- **CLAUDE.md:39** — Avoid dynamic f-string keys to `PROMPTS.get()` unless necessary and approved.
- **CLAUDE.md:70** — Use only `=== NAME ===` as the separator in prompts. Not dashes, underscores, or asterisks.

### Steps

1. **YAML lint**

   ```
   python -m yamllint litassist/prompts/
   ```

   If `yamllint` is not installed in `.venv`, fall back to a hand check: confirm each `.yaml` file under `litassist/prompts/` parses with `python -c "import yaml; yaml.safe_load(open('<path>'))"`.

2. **Forbidden inline-prompt patterns in Python sources**

   Grep for long string literals containing prompt-like content under `litassist/`:

   ```
   grep -rEn '("|\x27{3})You are|"Analyse |"Draft |"Verify ' litassist/ --include="*.py" \
     | grep -v __pycache__
   ```

   Long multi-line strings in `litassist/` that look like prompts and are NOT delegating to `PROMPTS.get()` violate CLAUDE.md:38.

3. **Dynamic `PROMPTS.get()` key audit**

   Find call sites that pass a non-string-literal to `PROMPTS.get`:

   ```
   grep -rEn 'PROMPTS\.get\([^"\x27]' litassist/ --include="*.py" \
     | grep -v __pycache__
   ```

   Each hit is a dynamic key. Each one needs a justification per CLAUDE.md:39.

4. **Non-`===` separators in prompt YAML**

   ```
   grep -rEn '^---+$|^___+$|^\*\*\*+$' litassist/prompts/
   ```

   Hits indicate dashes / underscores / asterisks used as separators. Replace with `=== NAME ===` per CLAUDE.md:70.

5. **Stable-key audit** (optional, slower)

   For each `.yaml` under `litassist/prompts/`, load keys and cross-check against the `PROMPTS.get(...)` literal calls collected in step 3. Surface (a) keys defined but never accessed and (b) literal calls referencing keys that don't exist.

### Output

Report grouped by rule violated:

```
CLAUDE.md:35 yamllint failures:
  - <file>:<line>  <rule-id>  <message>

CLAUDE.md:38 inline prompts in Python:
  - <file>:<line>  <snippet>

CLAUDE.md:39 dynamic PROMPTS.get keys:
  - <file>:<line>  <snippet>

CLAUDE.md:70 wrong separator:
  - <file>:<line>  <snippet>
```

Clean tree: zero hits in any section.

### Token efficiency

- Run all four greps in parallel via Bash tool calls in the same message.
- Skip step 5 unless step 3 or step 4 produced hits.
- Do NOT recurse into `.venv`, `__pycache__`, `outputs`, `logs`.
