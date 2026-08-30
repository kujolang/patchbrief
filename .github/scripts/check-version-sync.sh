#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

expected_version="$(sed -n 's/^VERSION := "\([^"]*\)"$/\1/p' patchbrief.kujo)"
if [[ -z "$expected_version" ]]; then
  echo "[version-sync] ERROR: unable to read VERSION from patchbrief.kujo"
  exit 1
fi

failures=()
require_match() {
  local file="$1"
  local pattern="$2"
  if ! grep -Fqx -- "$pattern" "$file"; then
    failures+=("$file: $pattern")
  fi
}

require_regex() {
  local file="$1"
  local pattern="$2"
  if ! grep -Eq -- "$pattern" "$file"; then
    failures+=("$file: $pattern")
  fi
}

require_match kujo.toml "version = \"${expected_version}\""
require_match kennel.toml "version = \"${expected_version}\""
require_match patchbrief.spec.yml "version: \"${expected_version}\""
require_match src/summarize.kujo $'\t\t"version": "'"${expected_version}"$'",'
require_match src/handoff.kujo $'\t\t"version": "'"${expected_version}"$'",'
require_match tests/patchbrief_tests.kujo $'\t\t"PatchBrief v'"${expected_version}"$'",'
require_regex CHANGELOG.md "^## \\[${expected_version//./\\.}\\] - [0-9]{4}-[0-9]{2}-[0-9]{2}$"

if (( ${#failures[@]} > 0 )); then
  echo "[version-sync] ERROR: release version is not synchronized"
  printf '[version-sync] Missing: %s\n' "${failures[@]}"
  exit 1
fi

echo "[version-sync] OK: ${expected_version}"
