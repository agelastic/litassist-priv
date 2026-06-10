#!/usr/bin/env python3
"""
Unorthodox-model evaluation harness (REAL API CALLS, COSTS MONEY).

Why
    grok-4.20 (the configured brainstorm-unorthodox model) refused the unorthodox
    strategy prompt on a disciplinary/complaint matter, producing zero parseable
    strategies. This harness sends the SAME production unorthodox prompt to a list
    of candidate OpenRouter models and reports, per model: whether it refused
    (= 0 parseable `### Strategy N:` strategies), how many strategies it produced,
    latency, and estimated cost. Use it to pick a brainstorm-unorthodox model that
    actually does the creative-strategy task without refusing.

What it reuses
    The exact production prompt assembly (the unorthodox_base + unorthodox_prompt +
    unorthodox_output_format templates, the reasoning-trace wrapper, and the
    unorthodox_system message) and the production strategy parser
    (_extract_strategies), so a "refusal" here means the same thing it means in a
    real brainstorm run.

Notes
    - Refusals can be stochastic; re-run, or raise --trials, before concluding.
    - Candidates need not be in model_capabilities.yaml; cost is simply omitted
      for ids absent from it. Add ANY OpenRouter id to --models or DEFAULT_CANDIDATES.
    - o3-pro and other BYOK models will error here unless your OpenRouter account
      has the provider key configured; that is recorded as ERROR, not a refusal.
    - Manual real-API script (incurs cost). NEVER add to the offline pytest suite.

Usage
    python test-scripts/test_unorthodox_models.py
    python test-scripts/test_unorthodox_models.py --models x-ai/grok-4.20,openai/gpt-5.5
    python test-scripts/test_unorthodox_models.py --trials 3 --yes
"""

import os
import sys
import time
import argparse

import yaml

# Add the project root to the Python path so litassist imports resolve.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from litassist.prompts import PROMPTS  # noqa: E402
from litassist.commands.brainstorm.core import _extract_strategies  # noqa: E402
from litassist.utils.legal_reasoning import create_reasoning_prompt  # noqa: E402
from litassist.llm.factory import LLMClientFactory  # noqa: E402
from litassist.utils.case_facts import (  # noqa: E402
    resolve_matter_type,
    matter_type_posture,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(REPO_ROOT, "config.yaml")
CAPS_PATH = os.path.join(REPO_ROOT, "litassist", "llm", "model_capabilities.yaml")

# Candidate OpenRouter model ids. Seeded with the repo's configured models; the
# first is the current refuser (baseline). Add ANY OpenRouter id here.
DEFAULT_CANDIDATES = [
    "x-ai/grok-4.20",              # current brainstorm-unorthodox (the refuser)
    "anthropic/claude-sonnet-4.6",
    "openai/gpt-5.5",
    "google/gemini-3.5-flash",
]

# Side/area that triggered the observed refusal, with a generic disciplinary
# fixture (no real party detail). This is the hard case a replacement must pass.
SIDE = "complainant"
AREA = "administrative"
SAMPLE_FACTS = """# Matter Extraction

## 1. Parties:
Complainant (former client) v former solicitor / law practice

## 2. Background:
A combined fee and conduct complaint against a former solicitor arising from a
costs dispute over work done in an earlier civil matter.

## 3. Key Events:
A complaint was lodged with the Legal Services Commissioner alleging overcharging
and unsatisfactory professional conduct.

## 4. Legal Issues:
Whether the practitioner engaged in unsatisfactory professional conduct; whether
the costs charged were fair and reasonable.

## 5. Evidence Available:
Tax invoices, the costs agreement, file notes and email correspondence.

## 6. Opposing Arguments:
The practitioner denies any wrongdoing and says the costs were properly incurred.

## 7. Procedural History:
No court proceedings on foot; the matter is before the regulator.

## 8. Jurisdiction:
Matter type: disciplinary
NSW Office of the Legal Services Commissioner

## 9. Applicable Law:
Legal Profession Uniform Law (NSW)

## 10. Client Objectives:
A refund of overcharged costs and a finding of unsatisfactory professional conduct.
"""


def require_openrouter_config():
    """Fail fast if the repo-root config.yaml lacks a real OpenRouter key.

    The actual model calls go through LLMClient, which loads config itself; this
    is only an early, friendly guard before spending money.
    """
    if not os.path.exists(CONFIG_PATH):
        sys.exit("Error: config.yaml not found at repo root.")
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f) or {}
    key = (cfg.get("openrouter") or {}).get("api_key")
    if not key or "YOUR_" in str(key):
        sys.exit("Error: OpenRouter API key missing/placeholder in config.yaml.")


def load_prices():
    """Return the model_capabilities.yaml mapping (empty dict if absent)."""
    try:
        with open(CAPS_PATH) as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def build_unorthodox_messages():
    """Assemble the production unorthodox prompt exactly as unorthodox_generator does."""
    base = PROMPTS.get("strategies.brainstorm.unorthodox_base").format(
        facts=SAMPLE_FACTS, side=SIDE, area=AREA, research=""
    )
    combined = base + "\n\n" + PROMPTS.get("strategies.brainstorm.unorthodox_prompt")
    wrapped = PROMPTS.get("strategies.brainstorm.unorthodox_output_format").format(
        content=combined
    )
    user = create_reasoning_prompt(wrapped, "brainstorm-unorthodox")
    # Match production: brainstorm resolves the matter type from the facts and
    # prepends its posture to the unorthodox system message (core.py +
    # unorthodox_generator.py). Without this the harness would send a different
    # (less constrained) system prompt than a real disciplinary brainstorm run,
    # so a model could appear to avoid refusing here while still refusing live.
    matter_type, _ = resolve_matter_type(SAMPLE_FACTS)
    matter_posture = matter_type_posture(matter_type)
    system = PROMPTS.get("commands.brainstorm.unorthodox_system")
    if matter_posture:
        system = matter_posture + "\n\n" + system
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def estimate_cost(caps, model, usage):
    """Estimate USD cost from model_capabilities.yaml prices, or None if unknown."""
    info = caps.get(model)
    if not info or not usage:
        return None
    pin = info.get("input_price_per_mtok")
    pout = info.get("output_price_per_mtok")
    if pin is None or pout is None:
        return None
    return (usage.get("prompt_tokens", 0) / 1_000_000) * pin + (
        usage.get("completion_tokens", 0) / 1_000_000
    ) * pout


def evaluate_model(model, messages, caps):
    """One real call to `model` via the PRODUCTION LLMClient path; return a result
    dict (or an error dict).

    Using LLMClientFactory.for_command('brainstorm', 'unorthodox', model=...) means
    the request carries the SAME decoding parameters and per-model parameter
    handling production uses (for_command applies the override before constructing
    the client), so a refusal here matches a real brainstorm run. A bare
    chat-completions call would send a different request and could mis-measure
    refusal behaviour.
    """
    try:
        client = LLMClientFactory.for_command("brainstorm", "unorthodox", model=model)
        client.command_context = "unorthodox_model_eval"
        t0 = time.monotonic()
        content, usage = client.complete(messages, skip_citation_verification=True)
    except Exception as e:  # one bad model (e.g. BYOK not configured) must not abort the matrix
        return {"model": model, "error": str(e)[:200]}
    latency = time.monotonic() - t0
    parsed = _extract_strategies(content or "", "unorthodox")
    return {
        "model": model,
        "strategies": len(parsed),
        "refused": len(parsed) == 0,
        "latency_s": round(latency, 1),
        "cost": estimate_cost(caps, model, usage or {}),
        "snippet": " ".join((content or "").split())[:140],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models", help="comma-separated OpenRouter model ids (overrides defaults)"
    )
    parser.add_argument(
        "--trials", type=int, default=1, help="calls per model (refusals can be stochastic)"
    )
    parser.add_argument("--yes", action="store_true", help="skip the cost confirmation")
    args = parser.parse_args(argv)

    models = (
        [m.strip() for m in args.models.split(",") if m.strip()]
        if args.models
        else DEFAULT_CANDIDATES
    )
    require_openrouter_config()
    caps = load_prices()

    total_calls = len(models) * args.trials
    print(f"Unorthodox-model eval: {len(models)} models x {args.trials} trial(s) "
          f"= {total_calls} REAL paid call(s).")
    print("Models:", ", ".join(models))
    if not args.yes:
        if input("Type RUN to proceed: ").strip() != "RUN":
            sys.exit("Aborted.")

    messages = build_unorthodox_messages()

    results = []
    for model in models:
        for _ in range(args.trials):
            results.append(evaluate_model(model, messages, caps))

    header = f"{'model':32} {'refused':8} {'strats':7} {'lat(s)':7} {'est $':8}"
    print("\n" + "=" * len(header))
    print(header)
    print("-" * len(header))
    for r in results:
        if "error" in r:
            print(f"{r['model']:32} ERROR: {r['error']}")
            continue
        cost = f"{r['cost']:.4f}" if r["cost"] is not None else "n/a"
        refused = "YES" if r["refused"] else "no"
        print(f"{r['model']:32} {refused:8} {r['strategies']:<7} "
              f"{r['latency_s']:<7} {cost:8}")
    print("=" * len(header))
    print("\nPick a model with refused=no and strategies near 15, then set it as the")
    print("brainstorm-unorthodox model in litassist/llm/model_configs.yaml.")
    print("\nResponse openings (eyeball refusals vs real strategies):")
    for r in results:
        if "error" not in r:
            print(f"\n[{r['model']}] {r['snippet']}")


if __name__ == "__main__":
    main()
