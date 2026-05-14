#!/usr/bin/env bash
# PostToolUse hook: lint YAML files under litassist/prompts/ after every
# Edit/Write/MultiEdit. CLAUDE.md:35 — "Validate all .yaml changes with a
# linter, especially under litassist/prompts/." Catches real bugs (parse
# errors, duplicate keys, indentation drift) without flagging the long
# scalar lines that prompts intentionally use.
#
# Reads Claude Code's PostToolUse JSON from stdin; warns to stderr;
# never blocks (exit 0 always).

set -uo pipefail

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
  echo "[yaml-lint-prompts] jq not on PATH; CLAUDE.md:35 enforcement DISABLED. Install jq to restore." >&2
  exit 0
fi

tool=$(echo "$input" | jq -r '.tool_name // empty')
file=$(echo "$input" | jq -r '.tool_input.file_path // empty')

case "$tool" in
  Edit|Write|MultiEdit) ;;
  *) exit 0 ;;
esac

case "$file" in
  */litassist/prompts/*.yaml|*/litassist/prompts/*.yml) ;;
  *) exit 0 ;;
esac

[ -f "$file" ] || exit 0

# Prerequisite check is deferred until after the scope gates so it only fires
# on edits that *should* have been linted — silent disappearance of yamllint
# would otherwise mask CLAUDE.md:35 enforcement.
if ! command -v yamllint >/dev/null 2>&1; then
  rel="${file#${PWD}/}"
  echo "[yaml-lint-prompts] ${rel}: yamllint NOT INSTALLED — CLAUDE.md:35 enforcement DISABLED for this edit." >&2
  echo "[yaml-lint-prompts] Install with 'brew install yamllint' or 'pip install yamllint', then re-edit to revalidate." >&2
  exit 0
fi

rules='{extends: default, rules: {line-length: disable, trailing-spaces: disable, document-start: disable, comments: disable, comments-indentation: disable, truthy: disable, empty-lines: disable, new-line-at-end-of-file: disable, indentation: {indent-sequences: consistent, check-multi-line-strings: false}}}'

output=$(yamllint -d "$rules" "$file" 2>&1)
status=$?

if [ "$status" -ne 0 ]; then
  rel="${file#${PWD}/}"
  echo "[yaml-lint-prompts] ${rel}: yamllint reported issues:" >&2
  echo "$output" | sed 's/^/  /' >&2
  echo "[yaml-lint-prompts] CLAUDE.md:35 — Validate all .yaml changes with a linter." >&2
fi

exit 0
