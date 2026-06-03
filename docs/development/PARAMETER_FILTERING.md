# Model Parameter Filtering

Last updated: 28/05/2026

Parameters defined in `model_configs.yaml` are filtered at call time so that only parameters the target model actually supports reach the API. The filtering operates in two tiers: first identifying the model family, then applying a per-family allowlist.

## Data flow

```
model_configs.yaml          model_profiles.py            parameter_handler.py         api_handlers.py
+------------------+        +--------------------+       +---------------------+      +------------------+
| command config   | -----> | MODEL_PATTERNS     | ----> | get_model_family()  |      |                  |
| model + params   |        | PARAMETER_PROFILES |       | get_model_params()  | ---> | extra_body split |
+------------------+        +--------------------+       +---------------------+      | API call         |
                                                                                      +------------------+
```

1. `LLMClientFactory.for_command()` in `litassist/llm/factory.py` loads a command entry from `model_configs.yaml`, extracts the model name and special flags (`enforce_citations`, `disable_tools`), and passes the remaining parameters to `LLMClient`.
2. At call time, `LLMClient.complete()` in `litassist/llm/client.py` calls `get_model_parameters(model_name, params)`.
3. The filtered dict is handed to `execute_api_call_with_retry()` in `litassist/llm/api_handlers.py`, which splits out OpenRouter-specific parameters into `extra_body` before making the OpenAI SDK call.

## Tier 1 -- model family identification

`get_model_family()` in `litassist/llm/parameter_handler.py` iterates `MODEL_PATTERNS` (an ordered dict of regex patterns in `litassist/llm/model_profiles.py`) and returns the key of the first match. Order matters: specific patterns precede general ones.

```
MODEL_PATTERNS = {
    "openai_reasoning":  r"openai/o\d+"                              # o1, o3, o3-pro, o4 ...
    "gpt5.5":            r"openai/gpt-5\.5"                          # active GPT-5.5 family
    "gpt5.1":            r"openai/gpt-5\.1"                          # legacy GPT-5.1 family
    "gpt5-pro":          r"openai/gpt-5-pro$"                        # legacy GPT-5 Pro family
    "gpt5":              r"openai/gpt-5$"
    "claude4":           r"anthropic/claude-(opus-4|sonnet-4)(\.\d+)?"
    "anthropic":         r"anthropic/claude"                          # catch-all Claude
    "google":            r"google/(gemini|palm|bard)"
    "openai_standard":   r"openai/(gpt|chatgpt)"                     # GPT-4, ChatGPT ...
    "xai":               r"x-ai/grok"
    "meta":              r"meta/(llama|codellama)"
    "mistral":           r"mistral/"
    "cohere":            r"cohere/"
    "moonshotai":        r"moonshotai/"
}
```

Examples:
- `anthropic/claude-sonnet-4.6` matches `claude4`
- `anthropic/claude-3-sonnet` matches `anthropic` (the broader catch-all)
- `openai/o3-pro` matches `openai_reasoning`
- `openai/gpt-5.5` matches `gpt5.5` (not `gpt5` or `openai_standard`)

If nothing matches, the family defaults to `"default"`.

## Tier 2 -- parameter allowlists

Each family key maps to an entry in `PARAMETER_PROFILES` (same file). A profile contains:

| Field | Purpose |
|-------|---------|
| `allowed` | Whitelist of parameter names the model accepts |
| `transforms` | Renames applied before sending (e.g. `max_tokens` -> `max_completion_tokens`) |
| `system_message_support` | Whether the model accepts system role messages (defaults to `True`) |

Key differences between families:

- **openai_reasoning / gpt5 / gpt5.1 / gpt5.5 / gpt5-pro** -- no `temperature` or `top_p` in the allowlist; `max_tokens` is transformed to `max_completion_tokens`.
- **anthropic / claude4** -- allow `temperature`, `top_p`, `max_tokens`, `top_k`, `min_p`, `top_a`, `repetition_penalty`.
- **xai** -- allows `temperature` and `top_p`; OpenRouter-specific sampling params (`min_p`, `top_a`, `repetition_penalty`) are not in the allowlist but pass through as OpenRouter params (see below).
- **cohere** -- transforms `top_k` -> `k`, `top_p` -> `p`, `stop` -> `stop_sequences`.
- **mistral** -- transforms `seed` -> `random_seed`.
- **default** -- only `temperature`, `top_p`, `max_tokens`, `stop`.

## Filtering algorithm

`get_model_parameters()` in `litassist/llm/parameter_handler.py` processes parameters in this order:

### 1. thinking_effort (handled first)

Popped from the dict and converted by `convert_thinking_effort()` into a `reasoning` object (`{"reasoning": {"effort": "<level>"}}`). The mapping varies by family:

- **openai_reasoning / gpt5 / gpt5.1 / xai**: effort values `minimal`, `low`, `medium`, `high` (with `max` mapped to `high`). o4 models additionally get `"summary": "auto"`.
- **anthropic / claude4**: effort values `low`, `medium`, `high` (with `minimal` mapped to `low`, `max` mapped to `high`).
- **google**: same mapping as Anthropic.

After conversion, conflicting keys (`reasoning_effort`, `reasoning`, `thinking`, `thinking_config`) are removed to prevent API errors.

### 2. verbosity (handled second)

Popped and converted by `convert_verbosity()` into `{"verbosity": "<level>"}`. Skipped entirely for `openai_reasoning` (o-series models do not support it).

### 3. Remaining parameters

Each remaining parameter is evaluated in order:

1. If the value is `None` -- skip.
2. If the key is in `transforms` -- rename and keep.
3. If the key is in `allowed` -- keep as-is.
4. If the key is in the OpenRouter params set (`reasoning`, `min_p`, `top_a`, `repetition_penalty`, `provider`, `verbosity`) -- keep (will be split into `extra_body` later).
5. Otherwise -- silently dropped.

## OpenRouter extra_body split

`execute_api_call_with_retry()` in `litassist/llm/api_handlers.py` performs a final split before the API call. Parameters in the OpenRouter set (returned by `get_openrouter_params()`) are moved from the filtered dict into an `extra_body` dict, because the OpenAI SDK does not recognise them as standard parameters. The call then looks like:

```python
client.chat.completions.create(
    model=model_name,
    messages=messages,
    extra_body=extra_body,   # reasoning, verbosity, min_p, etc.
    **filtered_params,       # temperature, top_p, max_tokens, etc.
)
```

If no OpenRouter params exist, the call omits `extra_body` entirely.

## Worked example

Command `brainstorm-unorthodox` with model `x-ai/grok-4.20`:

```yaml
# model_configs.yaml
brainstorm-unorthodox:
  model: "x-ai/grok-4.20"
  temperature: 0.8
  top_p: 0.95
  min_p: 0.05
  repetition_penalty: 1.2
  enforce_citations: false
  disable_tools: true
```

1. `factory.py` pops `model`, `enforce_citations`, `disable_tools`. Remaining params: `{temperature: 0.8, top_p: 0.95, min_p: 0.05, repetition_penalty: 1.2}`.
2. `get_model_family("x-ai/grok-4.20")` matches `"xai"`.
3. No `thinking_effort` or `verbosity` to handle.
4. Per-parameter filtering against the xai profile:
   - `temperature` -- in `allowed` -- kept.
   - `top_p` -- in `allowed` -- kept.
   - `min_p` -- not in `allowed`, but is in OpenRouter params set -- kept.
   - `repetition_penalty` -- not in `allowed`, but is in OpenRouter params set -- kept.
5. Filtered result: `{temperature: 0.8, top_p: 0.95, min_p: 0.05, repetition_penalty: 1.2}`.
6. In `api_handlers.py`, `min_p` and `repetition_penalty` move to `extra_body`.
7. Final API call: `create(model="x-ai/grok-4.20", messages=[...], extra_body={min_p: 0.05, repetition_penalty: 1.2}, temperature=0.8, top_p=0.95)`.

If the same config were used with `openai/gpt-5.5`, steps 4-5 would drop `temperature`, `top_p`, `min_p`, and `repetition_penalty` entirely (none are in the gpt5.5 allowlist or transforms).

## Files

| File | Role |
|------|------|
| `litassist/llm/model_configs.yaml` | Command-to-model+params mapping (source of truth) |
| `litassist/llm/model_profiles.py` | `MODEL_PATTERNS` and `PARAMETER_PROFILES` definitions |
| `litassist/llm/parameter_handler.py` | `get_model_family()`, `get_model_parameters()`, conversion functions |
| `litassist/llm/factory.py` | `LLMClientFactory.for_command()` loads config, creates client |
| `litassist/llm/client.py` | `LLMClient.complete()` calls `get_model_parameters()` at call time |
| `litassist/llm/api_handlers.py` | Splits OpenRouter params into `extra_body`, executes API call |

## Adding a new provider

1. Add a regex pattern to `MODEL_PATTERNS` in `model_profiles.py`. Place it before any broader pattern that would match the same model names.
2. Add a corresponding entry to `PARAMETER_PROFILES` with `allowed`, `transforms`, and optionally `system_message_support`.
3. Add command entries referencing the new model in `model_configs.yaml`.

No code changes are needed in the filtering or API layers.
