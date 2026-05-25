"""
Regression test: openai/ provider prefix must be preserved when calling OpenRouter.

api_handlers.get_openai_client always returns an OpenRouter-routed SDK client
(see api_handlers.py:97 — "ALL models are routed through OpenRouter").
OpenRouter requires `provider/model` slugs; passing a bare model name (e.g.
"gpt-5.5" instead of "openai/gpt-5.5") causes a 404 / unknown model error.

LLMClient.complete previously stripped the `openai/` prefix for non-reasoning
openai models before invoking the OpenRouter-routed SDK. This test asserts
the prefix is preserved end-to-end.
"""

import pytest
from unittest.mock import patch, MagicMock
from litassist.llm.client import LLMClient


class _MockResponse:
    def __init__(self, content="ok"):
        self.choices = [
            type(
                "Choice",
                (),
                {
                    "message": type("Msg", (), {"content": content}),
                    "error": None,
                    "finish_reason": "stop",
                },
            )()
        ]
        self.usage = type(
            "Usage",
            (),
            {
                "prompt_tokens": 1,
                "completion_tokens": 1,
                "total_tokens": 2,
                "model_dump": lambda self: {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )()


@pytest.mark.parametrize(
    "slug",
    [
        "openai/gpt-5.5",
        "openai/gpt-5.1",
        "openai/gpt-5-pro",
        "openai/gpt-4",
    ],
)
def test_openai_provider_prefix_preserved_for_openrouter(slug):
    """All openai/ slugs must reach the SDK with the full provider/model identifier."""
    with patch("litassist.config.CONFIG") as mock_config:
        mock_config.or_base = "https://openrouter.ai/api/v1"
        mock_config.or_key = "test_key"
        mock_config.openai_key = "test_key"

        client = LLMClient(slug)
        # Bypass tool-handling complexity; routes through the no-tools branch
        client._disable_tools = True

        with patch("litassist.llm.api_handlers.get_openai_client") as mock_get_client:
            mock_oai = MagicMock()
            mock_get_client.return_value = mock_oai
            mock_oai.chat.completions.create.return_value = _MockResponse("ok")

            client.complete(
                [{"role": "user", "content": "x"}],
                skip_citation_verification=True,
            )

            create_calls = mock_oai.chat.completions.create.call_args_list
            assert create_calls, "Expected chat.completions.create to be called"
            actual_model = create_calls[0].kwargs.get("model")
            assert actual_model == slug, (
                f"OpenRouter requires provider/model slug; got {actual_model!r} (expected {slug!r}). "
                f"LLMClient is stripping the openai/ prefix before calling OpenRouter."
            )
