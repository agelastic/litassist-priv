"""
Tests for the lookup `--context` / `--guidance` split.

Background:
- `--context` (short, search-side) is concatenated to the Google CSE
  query under `--comprehensive` (`search.py:142`) AND wrapped in a
  SEARCH CONTEXT block in the LLM prompt.
- `--guidance` (long, LLM-only) is wrapped in a USER GUIDANCE block
  in the LLM prompt. It NEVER touches the CSE query.

These tests pin:
1. Per-flag prompt-block presence on the four input combinations.
2. Block ordering in the rendered prompt (guidance above context).
3. That `search.py` only ever concatenates `context` -- never
   `guidance` -- to the CSE query.
4. Click parses `--guidance` cleanly without colliding with other
   options.
5. The audit log payload records both flags as distinct inputs.
"""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from litassist.commands.lookup import lookup
from litassist.commands.lookup.processors import LookupProcessor


# A long narrative that should never reach Google CSE. Picked to be
# clearly distinguishable from the short topic-label `context` strings
# the tests use so substring assertions are unambiguous.
LONG_NARRATIVE = (
    "Client seeks write-off of invoice 372763 on basis that the "
    "revised estimate on 3 March 2026 did not comply with s 174; "
    "total fees approximately AUD 113,000 for a AUD 25,000 asset "
    "claim settled without recovery."
)


def _processor():
    """Build a LookupProcessor with a stub config -- build_prompt does
    not touch config, so a MagicMock is sufficient."""
    return LookupProcessor(MagicMock())


@pytest.mark.unit
@pytest.mark.offline
class TestBuildPromptBlocks:
    """`build_prompt` must wrap `context` and `guidance` independently
    in their respective labelled blocks (SEARCH CONTEXT / USER
    GUIDANCE) and prepend each only when the corresponding input is
    truthy."""

    def test_context_only_renders_search_context_block_only(self):
        prompt = _processor().build_prompt(
            question="test query",
            mode="irac",
            extract=None,
            comprehensive=False,
            context="NSW costs",
            guidance=None,
            links=["https://example.com/case"],
            documents=[],
        )
        assert "=== SEARCH CONTEXT ===" in prompt
        assert "NSW costs" in prompt
        assert "=== USER GUIDANCE" not in prompt

    def test_guidance_only_renders_user_guidance_block_only(self):
        prompt = _processor().build_prompt(
            question="test query",
            mode="irac",
            extract=None,
            comprehensive=False,
            context=None,
            guidance=LONG_NARRATIVE,
            links=["https://example.com/case"],
            documents=[],
        )
        assert "=== USER GUIDANCE" in prompt
        assert LONG_NARRATIVE in prompt
        assert "=== SEARCH CONTEXT" not in prompt

    def test_both_flags_render_both_blocks_in_correct_order(self):
        """Both blocks appear; USER GUIDANCE is prepended LAST so it
        sits above SEARCH CONTEXT, which sits above the question.
        Codex audit finding #4 requires index-position assertion, not
        just substring presence."""
        prompt = _processor().build_prompt(
            question="test query",
            mode="irac",
            extract=None,
            comprehensive=True,
            context="NSW costs",
            guidance=LONG_NARRATIVE,
            links=["https://example.com/case"],
            documents=[],
        )
        guidance_pos = prompt.index("=== USER GUIDANCE")
        context_pos = prompt.index("=== SEARCH CONTEXT")
        question_pos = prompt.index("test query")
        assert guidance_pos < context_pos < question_pos, (
            f"Expected USER GUIDANCE above SEARCH CONTEXT above the "
            f"question. Got positions: guidance={guidance_pos}, "
            f"context={context_pos}, question={question_pos}.\n"
            f"Prompt was:\n{prompt}"
        )

    def test_neither_flag_renders_no_extra_blocks(self):
        prompt = _processor().build_prompt(
            question="test query",
            mode="irac",
            extract=None,
            comprehensive=False,
            context=None,
            guidance=None,
            links=["https://example.com/case"],
            documents=[],
        )
        assert "=== SEARCH CONTEXT" not in prompt
        assert "=== USER GUIDANCE" not in prompt


@pytest.mark.unit
@pytest.mark.offline
class TestCSEConcatenation:
    """`search.py:perform_cse_searches` may only concatenate `context`
    to the comprehensive-mode query. `guidance` must never reach the
    CSE side."""

    def test_comprehensive_query_uses_context_not_guidance(self):
        """Exercises the concatenation logic at search.py:139-144 by
        observing the query strings passed to `_perform_cse_search`."""
        with (
            patch("litassist.commands.lookup.search.get_config") as mock_cfg,
            patch("googleapiclient.discovery.build") as mock_build,
            patch("litassist.commands.lookup.search.time.sleep"),
            patch(
                "litassist.commands.lookup.search._perform_cse_search"
            ) as mock_cse,
        ):
            cfg = MagicMock()
            cfg.g_key = "k"
            cfg.cse_id = "primary"
            cfg.cse_id_austlii = "austlii"
            cfg.cse_id_comprehensive = "comp"
            mock_cfg.return_value = cfg
            mock_build.return_value = MagicMock()
            mock_cse.return_value = ([], [])

            from litassist.commands.lookup.search import perform_cse_searches

            perform_cse_searches(
                question="negligence duty of care",
                comprehensive=True,
                context="NSW",
            )

            queries = [call.args[1] for call in mock_cse.call_args_list]
            assert any(q == "negligence duty of care NSW" for q in queries), (
                f"Expected `context` to be concatenated to the "
                f"comprehensive query. Queries seen: {queries!r}"
            )

    def test_search_signature_does_not_accept_guidance(self):
        """`perform_cse_searches` must remain context-only. If a future
        change starts threading `guidance` into CSE, this test fails
        and forces an explicit review."""
        import inspect

        from litassist.commands.lookup.search import perform_cse_searches

        params = inspect.signature(perform_cse_searches).parameters
        assert "guidance" not in params, (
            "perform_cse_searches must not accept `guidance` -- the "
            "split's whole point is that guidance is LLM-only and "
            "never reaches the CSE query."
        )


@pytest.mark.unit
@pytest.mark.offline
class TestCliParse:
    """Codex audit finding #7: confirm Click parses `--guidance` with
    no collisions against global options or other lookup flags."""

    def test_guidance_flag_is_parsed(self):
        """A `--help` invocation succeeds (exit_code 0) and includes
        the new flag's name, proving the decorator is wired."""
        runner = CliRunner()
        result = runner.invoke(lookup, ["--help"])
        assert result.exit_code == 0, result.output
        assert "--guidance" in result.output
        assert "--context" in result.output


@pytest.mark.unit
@pytest.mark.offline
class TestAuditLog:
    """Codex audit finding #5: the lookup audit log records both
    `context` and `guidance` as distinct inputs."""

    @patch("litassist.commands.lookup.get_config")
    @patch("litassist.commands.lookup.search.get_config")
    # `processors.py:26` imports `_fetch_url_content` directly from
    # `.fetchers` at module load, binding it into the `processors`
    # namespace. Patching at `fetchers` leaves the in-processors
    # reference untouched, so the patch must target the
    # `processors`-side binding. Today's CSE stub returns zero items
    # so `_fetch_url_content` is not actually called; pinning the
    # correct patch target prevents a silent real-HTTP regression if
    # the test later exercises the link-fetch path (gemini-code-assist
    # PR #79 review).
    @patch("litassist.commands.lookup.processors._fetch_url_content", return_value="")
    @patch("litassist.commands.lookup.search.time.sleep")
    @patch("googleapiclient.discovery.build")
    @patch("litassist.llm.factory.LLMClientFactory.for_command")
    @patch("litassist.commands.lookup.save_log")
    def test_save_log_records_both_inputs(
        self,
        mock_save_log,
        mock_factory,
        mock_build,
        mock_sleep,
        mock_fetch,
        mock_search_cfg,
        mock_lookup_cfg,
    ):
        cfg = MagicMock()
        cfg.g_key = "k"
        cfg.cse_id = "primary"
        cfg.cse_id_austlii = ""
        cfg.cse_id_comprehensive = ""
        mock_lookup_cfg.return_value = cfg
        mock_search_cfg.return_value = cfg

        # Make CSE return no links so the pipeline runs quickly to the
        # save_log call without needing real link processing.
        fake_service = MagicMock()
        fake_service.cse().list().execute.return_value = {"items": []}
        mock_build.return_value = fake_service

        fake_client = MagicMock()
        fake_client.complete.return_value = (
            "stub LLM response",
            {"total_tokens": 1},
        )
        fake_client.model = "stub/model"
        mock_factory.return_value = fake_client

        runner = CliRunner()
        result = runner.invoke(
            lookup,
            [
                "negligence",
                "--context",
                "NSW",
                "--guidance",
                LONG_NARRATIVE,
            ],
        )
        assert result.exit_code == 0, result.output

        lookup_log_calls = [
            call for call in mock_save_log.call_args_list
            if call.args and call.args[0] == "lookup"
        ]
        assert lookup_log_calls, (
            f"Expected at least one save_log('lookup', ...) call. "
            f"Saw: {mock_save_log.call_args_list!r}"
        )
        payload = lookup_log_calls[-1].args[1]
        assert payload["inputs"]["context"] == "NSW"
        assert payload["inputs"]["guidance"] == LONG_NARRATIVE
