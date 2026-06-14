"""Offline tests for litassist.llm.cost.estimate_call_cost and cost_message."""

import pytest

from litassist.llm import cost as cost_module
from litassist.llm.cost import estimate_call_cost
from litassist.utils.formatting import cost_message

# A controlled capabilities table so the arithmetic assertions stay stable
# regardless of what `litassist refresh` writes into model_capabilities.yaml.
_FAKE_CAPS = {
    "openai/o3-pro": {
        "input_price_per_mtok": 20.0,
        "output_price_per_mtok": 80.0,
    },
    "no/prices": {
        "context_window": 100000,
    },
}


@pytest.fixture(autouse=True)
def _patch_caps(monkeypatch):
    # cost.py binds _get_model_capabilities at import, so patch the name in the
    # cost module's namespace, not factory's.
    monkeypatch.setattr(cost_module, "_get_model_capabilities", lambda: _FAKE_CAPS)


def test_known_prices():
    # 1M prompt tokens at $20/mtok + 1M completion tokens at $80/mtok = $100.00.
    usage = {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000}
    assert estimate_call_cost("openai/o3-pro", usage) == pytest.approx(100.0)


def test_fractional_tokens():
    # 12,000 prompt + 3,000 completion: 0.012*20 + 0.003*80 = 0.24 + 0.24 = 0.48.
    usage = {"prompt_tokens": 12_000, "completion_tokens": 3_000}
    assert estimate_call_cost("openai/o3-pro", usage) == pytest.approx(0.48)


def test_missing_usage_keys_count_as_zero():
    assert estimate_call_cost("openai/o3-pro", {}) == 0.0


def test_unknown_model_raises_keyerror():
    with pytest.raises(KeyError) as exc:
        estimate_call_cost("ghost/model", {"prompt_tokens": 1})
    assert "litassist refresh" in str(exc.value)


def test_missing_price_fields_raise_keyerror():
    # NO FALLBACKS: a model present but without price fields raises rather than
    # silently costing $0.
    with pytest.raises(KeyError):
        estimate_call_cost("no/prices", {"prompt_tokens": 1})


def test_cost_message_prefix():
    assert "[COST]" in cost_message("hello")
