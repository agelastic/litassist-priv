#!/usr/bin/env bash
# PreToolUse hook: warn when an Edit/Write introduces a model-identifier
# string that wasn't present in the location it replaces. Scoped to files
# where model IDs actually live so the rest of the repo is unaffected.
#
# CLAUDE.md:75 — "Never change model identifiers unless explicitly asked."
# Bridge nodes get_model_parameters and LLMClient amplify the blast radius
# of any silent model drift.
#
# Reads Claude Code's PreToolUse JSON from stdin; warns to stderr;
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
  *litassist/llm/*|*config.yaml|*config.yaml.template|*model_configs.yaml|*model_profiles.py) ;;
  *) exit 0 ;;
esac

# OpenRouter-style "provider/model-name" plus bare provider IDs.
re='(anthropic|openai|google|x-ai|xai)/[A-Za-z0-9._-]+|(gpt-[0-9]|claude-[a-z0-9]|o[0-9]-)[A-Za-z0-9._-]*'

extract_ids() {
  grep -oE "$re" 2>/dev/null | sort -u
}

old_ids=""
new_ids=""

case "$tool" in
  Edit)
    old=$(echo "$input" | jq -r '.tool_input.old_string // empty')
    new=$(echo "$input" | jq -r '.tool_input.new_string // empty')
    old_ids=$(printf '%s' "$old" | extract_ids)
    new_ids=$(printf '%s' "$new" | extract_ids)
    ;;
  MultiEdit)
    # MultiEdit's tool_input.edits is an array of {old_string,new_string}
    # objects; concatenate each side so the regex sees every replacement.
    old=$(echo "$input" | jq -r '[.tool_input.edits[]?.old_string // empty] | join("\n")')
    new=$(echo "$input" | jq -r '[.tool_input.edits[]?.new_string // empty] | join("\n")')
    old_ids=$(printf '%s' "$old" | extract_ids)
    new_ids=$(printf '%s' "$new" | extract_ids)
    ;;
  Write)
    new=$(echo "$input" | jq -r '.tool_input.content // empty')
    new_ids=$(printf '%s' "$new" | extract_ids)
    if [ -f "$file" ]; then
      old_ids=$(extract_ids < "$file")
    fi
    ;;
esac

introduced=$(comm -23 <(printf '%s\n' "$new_ids") <(printf '%s\n' "$old_ids") | grep -v '^$' || true)

if [ -n "$introduced" ]; then
  rel="${file#${PWD}/}"
  echo "[model-identifier] ${rel}: this edit introduces model identifier(s) not present before:" >&2
  while IFS= read -r id; do
    [ -n "$id" ] && echo "  + $id" >&2
  done <<< "$introduced"
  echo "[model-identifier] CLAUDE.md:75 — Never change model identifiers unless explicitly asked." >&2
fi

exit 0
