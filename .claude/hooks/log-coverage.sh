#!/usr/bin/env bash
# PostToolUse hook: warn when a Python file under litassist/ contains
# LLMClient(...) or .complete(...) calls without log_task_event or save_log
# in the same file. CLAUDE.md mandates full LLM request/response logging;
# log_task_event has 170+ call sites and is the single most-imported
# function in the codebase. Missing it silently bypasses the audit trail.
#
# Reads Claude Code's PostToolUse JSON from stdin; warns to stderr;
# never blocks (exit 0 always).

set -uo pipefail

input=$(cat)

command -v jq >/dev/null 2>&1 || exit 0

tool=$(echo "$input" | jq -r '.tool_name // empty')
file=$(echo "$input" | jq -r '.tool_input.file_path // empty')

case "$tool" in
  Edit|Write|MultiEdit) ;;
  *) exit 0 ;;
esac

case "$file" in
  */litassist/*.py) ;;
  *) exit 0 ;;
esac

[ -f "$file" ] || exit 0

if grep -qE '(LLMClient[[:space:]]*\(|\.complete[[:space:]]*\()' "$file"; then
  if ! grep -qE 'log_task_event|save_log' "$file"; then
    rel="${file#${PWD}/}"
    echo "[log-coverage] ${rel}: contains LLMClient/complete() but no log_task_event or save_log." >&2
    echo "[log-coverage] Verify logging is wired before relying on the audit trail." >&2
  fi
fi

exit 0
