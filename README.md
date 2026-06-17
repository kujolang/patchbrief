# PatchBrief

A local developer tool that inspects git diffs and generates structured implementation briefs. Built in [Kujo/Kujo](https://github.com/kujolang/kujo) as an ecosystem dogfood showcase.

## Quick Start

```bash
kujo run patchbrief.kujo -- summarize
```

When there are no uncommitted changes, the output starts like this:

```md
# PatchBrief Summary

**Repo:** patchbrief
**Branch:** main

No uncommitted changes detected.
```

Note: use `--` before PatchBrief arguments so Kujo does not parse tool flags as runtime flags.
PatchBrief treats `help` and `version` as commands; `--help` and `--version`
are not standalone aliases and will fall back to the command-order guidance.

Common follow-up commands:

```bash
kujo run patchbrief.kujo -- summarize --format json --pretty
kujo run patchbrief.kujo -- suggest-tests
kujo run patchbrief.kujo -- handoff
```

## Commands

| Command | Description |
|---------|-------------|
| `summarize` | Generate a Markdown or JSON summary of the current git diff |
| `suggest-tests` | Suggest test commands based on changed files |
| `handoff` | Generate a structured handoff note for reviewers or agents |
| `version` | Print version information |
| `help` | Print usage information |

## Options

| Option | Description |
|--------|-------------|
| `--format markdown\|json` | Output format (default: markdown) |
| `--pretty` | Pretty-print JSON output when `--format json` is used |

## Requirements

- Kujo runtime (`kujo` binary)
- Git (on PATH)
- Run inside a git repository

## Running Tests

```bash
kujo test
```

## Agent and Contributor Notes

Prioritize copyable examples over tests: examples should model the most token-efficient idioms we want agents to imitate.

Canonical examples live in this README and the static help output in `patchbrief.kujo`. Tests in `tests/` are contract checks, not example style guides. The repo currently has no tracked fixtures, generated outputs, legacy demos, or expected-fail examples.

When sweeping for readability, exclude generated or bulk paths unless a task explicitly targets them. Use the package exclusions as the default search hygiene list: `.git`, `kennel_packages`, `dist`, `build`, `node_modules`, and `.dogfood`.

Keep CLI output byte-stable when refactoring report emitters. Add or update exact-output tests before changing copyable help text, command syntax, JSON shape, or Markdown section names.

Use the shared output helpers in `src/common.kujo` (`print_lines`, `print_prefixed_lines`, `print_prefixed_or_fallback`, `print_wrapped_lines`, `print_markdown_section`, `print_markdown_paragraph`, `print_fenced`, and `print_not_git_repo_error`) before adding repeated `print(...)` blocks.

## Project Structure

```
patchbrief.kujo          # Main entrypoint
src/
  common.kujo            # Shared utilities (arg parsing, string helpers)
  git.kujo               # Git command wrappers
  summarize.kujo         # Diff analysis and summary generation
  suggest_tests.kujo     # Test suggestion logic
  handoff.kujo           # Handoff note generation
tests/
  patchbrief_tests.kujo  # Test suite
patchbrief.spec.yml      # Spec file (task definition)
kujo.toml               # Kujo project config
kennel.toml             # Kennel package manifest
.dogfood/               # Ecosystem dogfood reports
```

## Status

MVP — dogfood build. Testing the Kujo/Kujo ecosystem while building a useful tool.

## License

MIT
