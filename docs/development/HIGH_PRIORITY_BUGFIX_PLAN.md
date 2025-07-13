# High‑Priority Bugfix Plan

This document outlines the five top‑priority issues in LitAssist and the plan to resolve them.

## 1. Sync `lookup --comprehensive` help text with actual behavior
The CLI help claims "40 instead of 5" sources but the code uses 20. Decide on the correct limit and update both the `help` string and User Guide to match, or bump `max_sources` to 40.

## 2. Enable `openrouter.api_base` in configuration setup
Uncomment or conditionally set `openai.api_base = self.or_base` in `Config._setup_api_keys` to allow routing through OpenRouter (BYOK) when configured.

## 3. Implement `safety_cutoff` circuit‑breaker for API retries
Hook the `safety_cutoff` parameter from the OpenRouter config into the retry logic (in the LLM client or HTTP wrapper) to disable retries after N failures per hour. Add unit tests and remove the TODO when done.

## 4. Remove redundant top‑level `litassist.py` entry point
Delete the root `litassist.py` script and ensure the console_script entry in `setup.py` (`litassist=litassist.cli:main`) remains the sole launcher. Update docs referencing the old script.

## 5. Fail fast on config load errors
Remove the silent catch in `litassist/config.py` that only warns on `ConfigError`. Let configuration errors propagate (or catch in CLI entry) so the application exits immediately when `config.yaml` is missing or invalid.

## Roll‑out Steps for Each Fix
1. Create a dedicated bugfix branch.
2. Implement the change and update any affected docs.
3. Add or update unit tests to cover new behavior.
4. Run `pre-commit run --all-files` and `pytest` to ensure green CI.
5. Submit PR and merge once tests pass.
