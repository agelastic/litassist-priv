"""
Aggregate per-call usage dicts.

A single ``LLMClient.complete()`` can make several billed SDK calls internally
(tool-fallback follow-up, retried calls). Each call's usage - including
OpenRouter's actual ``cost`` and ``generation_id`` - is merged here so the
returned/logged figure reflects EVERY paid call, not just the last one.
"""

from typing import Any, Dict, Optional

# Numeric usage fields summed across calls. `cost` is OpenRouter's actual billed
# USD for the call (present when usage accounting is enabled on the request).
_SUM_KEYS = ("prompt_tokens", "completion_tokens", "total_tokens", "cost")


def merge_usage(*usages: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Sum the numeric fields of several usage dicts and collect their generation ids.

    None / empty usages are ignored. A field is summed only across the usages
    that actually carry it (so a missing ``cost`` on one call does not zero the
    total - it is simply excluded, and the result is a partial sum).
    """
    merged: Dict[str, Any] = {}
    generation_ids = []
    # Count contributing billed calls that carried no numeric cost, so a partial
    # sum is not silently presented as a complete one.
    cost_missing = 0
    for usage in usages:
        if not usage:
            continue
        for key in _SUM_KEYS:
            value = usage.get(key)
            if isinstance(value, (int, float)):
                merged[key] = merged.get(key, 0) + value
        # Preserve both a leaf's singular id and any already-merged plural ids.
        gen_id = usage.get("generation_id")
        if gen_id:
            generation_ids.append(gen_id)
        generation_ids.extend(usage.get("generation_ids") or [])
        # An already-merged usage carries its own cost_missing tally; a leaf is
        # "missing" iff it has no numeric cost.
        if "cost_missing" in usage:
            cost_missing += usage["cost_missing"]
        elif not isinstance(usage.get("cost"), (int, float)):
            cost_missing += 1
    if generation_ids:
        merged["generation_ids"] = generation_ids
    if cost_missing:
        merged["cost_missing"] = cost_missing
    return merged
