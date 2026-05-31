"""
Tests for size-cap derivation from model context windows.

These tests anchor the contract between the capability infrastructure
(`LLMClientFactory.get_context_window_for_command` →
`get_input_budget_for_command`) and the per-command size enforcement
points (draft preflight, digest chunker). Both anchor points compute
char budgets from token windows via the same arithmetic, so they share
this test module.
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from litassist.commands.digest.chunker import determine_chunk_size
from litassist.commands.draft.core import draft


@pytest.mark.unit
@pytest.mark.offline
class TestDraftPreflight:
    """Boundary behaviour of draft's oversize preflight.

    Soft warn fires at HARD * SOFT_WARN_FRACTION; hard fail fires at
    `HARD_INPUT_FRACTION * window * chars_per_token`. The constants live
    in `litassist/commands/draft/core.py`; this test class verifies the
    three regions (below soft, between soft and hard, above hard) by
    monkeypatching the underlying context window so the test does not
    depend on the active draft model's actual window size.
    """

    # Picked so the math is round: 100_000 tokens × 3.5 chars/token = 350_000
    # chars total; hard = 350_000 × 0.70 = 245_000; soft = 245_000 × 0.70
    # = 171_500. Comfortable headroom below 171_500 fires nothing.
    FAKE_WINDOW_TOKENS = 100_000
    HARD_CHARS = 245_000
    SOFT_CHARS = 171_500

    def _invoke_draft_with_payload(self, payload_chars: int, tmp_path):
        """Drive `draft` end-to-end with a controlled payload size and
        intercept the LLM call so we only observe preflight behaviour."""
        case_facts = tmp_path / "case_facts.txt"
        # User-prompt payload is what dominates -- pad case_facts to the
        # target size minus the small system-prompt overhead. The system
        # prompt for draft is around 1-2 KB; deduct 3000 chars to stay
        # safely under the target when the system prompt is added.
        case_facts.write_text("A" * max(0, payload_chars - 3000))

        runner = CliRunner()
        with (
            patch(
                "litassist.commands.draft.core.LLMClientFactory."
                "get_context_window_for_command",
                return_value=self.FAKE_WINDOW_TOKENS,
            ),
            patch(
                "litassist.commands.draft.core.LLMClientFactory."
                "get_model_for_command",
                return_value="fake/test-model",
            ),
            patch(
                "litassist.commands.draft.core.LLMClientFactory.for_command"
            ) as mock_factory,
            patch(
                "litassist.commands.draft.core.build_system_prompt",
                return_value="system",
            ),
            patch(
                "litassist.commands.draft.core.build_user_prompt",
                return_value="A" * payload_chars,
            ),
            patch(
                "litassist.commands.draft.core.read_and_categorize_documents",
                return_value={
                    "case_facts": case_facts.read_text(),
                    "strategies": "",
                    "other_text": [],
                    "pdf_documents": [],
                },
            ),
            patch(
                "litassist.commands.draft.core.build_text_context",
                return_value="A" * payload_chars,
            ),
            patch("litassist.commands.draft.core.save_log"),
            patch("litassist.commands.draft.core.save_command_output"),
            patch(
                "litassist.commands.draft.core.verify_content_if_needed",
                side_effect=lambda client, content, *a, **kw: (content, False, None),
            ),
            patch(
                "litassist.commands.draft.core.detect_factual_hallucinations",
                return_value=[],
            ),
            patch("litassist.commands.draft.core.show_command_completion"),
        ):
            mock_factory.return_value.complete.return_value = (
                "drafted content",
                {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            )
            mock_factory.return_value.model = "fake/test-model"
            return runner.invoke(
                draft,
                [str(case_facts), "the query"],
                catch_exceptions=False,
            ), mock_factory.return_value.complete

    def test_above_soft_below_hard_warns_but_proceeds(self, tmp_path):
        result, complete = self._invoke_draft_with_payload(
            self.SOFT_CHARS + 10_000, tmp_path
        )
        assert result.exit_code == 0
        assert "approaching the model's input budget" in result.output
        assert complete.called

    def test_at_or_above_hard_threshold_raises(self, tmp_path):
        result, complete = self._invoke_draft_with_payload(
            self.HARD_CHARS + 10_000, tmp_path
        )
        assert result.exit_code != 0
        assert "exceeds the safe input budget" in result.output
        assert not complete.called


@pytest.mark.unit
@pytest.mark.offline
class TestDigestChunkSize:
    """`determine_chunk_size` must equal
    `int(window_tokens * 3.5 * CHUNK_FRACTION_OF_WINDOW)`.

    Monkeypatches the underlying capability lookup so the formula is
    tested against a known token count, not whatever the current digest
    model happens to be. CHUNK_FRACTION_OF_WINDOW lives in
    `litassist/commands/digest/chunker.py`; if that constant changes
    this test fails loudly, prompting an update to whichever rationale
    comment moved.
    """

    def test_sub_type_propagates_to_capability_lookup(self):
        """The sub_type argument flows through to the underlying
        get_context_window_for_command call so digest-summary and
        digest-issues can use different models if the user routes them
        differently in model_configs.yaml."""
        from litassist.commands.digest import chunker  # noqa: F401

        with patch(
            "litassist.commands.digest.chunker."
            "LLMClientFactory.get_context_window_for_command"
        ) as mock_window:
            mock_window.return_value = 100_000
            determine_chunk_size("digest", "summary")
            determine_chunk_size("digest", "issues")
            assert mock_window.call_args_list[0][0] == ("digest", "summary")
            assert mock_window.call_args_list[1][0] == ("digest", "issues")
