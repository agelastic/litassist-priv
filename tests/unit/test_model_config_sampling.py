"""Guard: every command's effective sampling params are accepted by its model.

This cross-checks each entry in model_configs.yaml against the authoritative
per-model supported_parameters in model_capabilities.yaml (refreshed from
OpenRouter), after running the config through the real parameter filter. It
catches two classes of provider 400s that OpenRouter would otherwise silently
absorb:

  1. Sending a sampling param (temperature/top_p/top_k) a model does not accept
     (Opus 4.7+ removed them).
  2. Sending temperature and top_p together to any Claude model (Anthropic
     rejects this since 4.1).
"""

from pathlib import Path

import yaml

import litassist.llm
from litassist.llm.parameter_handler import get_model_parameters

_SAMPLING_PARAMS = {"temperature", "top_p", "top_k"}
_LLM_DIR = Path(litassist.llm.__file__).parent


def _load(name):
    return yaml.safe_load((_LLM_DIR / name).read_text())


def test_no_command_sends_unsupported_sampling_params():
    capabilities = _load("model_capabilities.yaml")
    configs = _load("model_configs.yaml")

    for command, cfg in configs.items():
        model = cfg["model"]
        assert model in capabilities, f"{command}: model {model} missing from capabilities"
        supported = set(capabilities[model]["supported_parameters"])

        requested = {k: v for k, v in cfg.items() if k != "model"}
        filtered = get_model_parameters(model, requested)

        for param in _SAMPLING_PARAMS:
            if param in filtered:
                assert param in supported, (
                    f"{command}: sends '{param}' which {model} does not accept"
                )

        # Anthropic Claude models reject temperature and top_p together.
        if model.startswith("anthropic/claude-") and "temperature" in filtered:
            assert "top_p" not in filtered, (
                f"{command}: sends both temperature and top_p to {model}"
            )
