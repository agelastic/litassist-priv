# Static Analysis Debt

Last updated: 26/06/2026

Pyright diagnostics that exist in the codebase and are recorded here to address
later. They were surfaced (not introduced) during the P-FAITH work on branch
`feat/p-faith-faithfulness` when `litassist/verification_chain.py` was edited and the
linter re-ran over the whole file. None is a known runtime defect today, but each is
real and ours to clean up. Priority: LOW (no observed misbehaviour); fix in a
dedicated pass, not bundled into feature commits.

## `litassist/verification_chain.py`

| Line | Diagnostic | Detail | Runtime risk |
|------|------------|--------|--------------|
| 88 | `model_name` is not accessed | In `run_verification_chain` stage 3, `corrected_content, model_name = client.verify(...)` binds `model_name` but it is never used. | None. Dead variable; the soundness/cove handlers capture and log their model name, this stage does not. Either log it or discard with `_`. |
| 433-435 | `answers_prompt` possibly unbound | In `run_cove_verification`, `answers_prompt` is assigned inside the `while answers is None and attempts < 5:` loop (line 324) and read after the loop in `cove_stages["answers"]`. | None at runtime: the loop always executes at least once (`attempts` starts at 0). Static analysis cannot prove it. Initialise `answers_prompt = ""` before the loop to satisfy the checker. |
| 576 | `usage4` possibly unbound | In `run_cove_verification`'s summary `total_tokens`, `usage4` is assigned only inside the `if not passed:` regeneration block and read in the summary. | None at runtime: guarded by `if not passed and "usage4" in locals()`. The `locals()` guard is what trips the checker. Hoist `usage4 = {}` before the branch and drop the `in locals()` check. |

## How to clear

A single focused commit that initialises the loop/branch variables and removes or
uses `model_name` -- no behavioural change, just making the static checker agree with
the runtime invariants. Verify with `pytest` (the CoVe tests already cover these
paths) and a clean Pyright pass on the file.
