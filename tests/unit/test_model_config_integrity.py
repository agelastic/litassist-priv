"""
Structural integrity tests for litassist/llm/model_configs.yaml.

These tests catch typos and unknown providers without pinning specific model
identifiers. Complements the runtime startup check in cli.py (which validates
configured models against OpenRouter's live inventory) by providing an offline
guard at unit-test time.
"""

from litassist.llm.factory import LLMClientFactory
from litassist.llm.parameter_handler import get_model_family


def test_every_configured_command_has_a_model():
    """Every command in model_configs.yaml must declare a non-empty model identifier."""
    configs = LLMClientFactory.list_configurations()
    assert configs, "No model configurations loaded from model_configs.yaml"

    missing = [
        command for command, cfg in configs.items() if not cfg.get("model")
    ]
    assert not missing, (
        f"Commands missing 'model' in model_configs.yaml: {sorted(missing)}"
    )


def test_every_configured_model_matches_a_known_family():
    """
    Every configured model identifier must dispatch to a known routing family.

    Falling into the 'default' family means the model identifier matches no
    pattern in MODEL_PATTERNS — typically caused by a provider-name typo
    (e.g., 'anthrpoic/...' instead of 'anthropic/...') or a brand-new
    provider that needs a pattern entry added.
    """
    configs = LLMClientFactory.list_configurations()
    unrouted = []
    for command, cfg in configs.items():
        model = cfg.get("model")
        if not model:
            continue  # caught by test_every_configured_command_has_a_model
        family = get_model_family(model)
        if family == "default":
            unrouted.append((command, model))

    assert not unrouted, (
        "Model identifiers do not match any MODEL_PATTERNS regex (typo or "
        f"missing pattern): {unrouted}"
    )
