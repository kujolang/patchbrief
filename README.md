# PatchBrief

A local developer tool that inspects git diffs and generates structured implementation briefs. Built in [Kujo/Kujo](https://github.com/kujolang/kujo) as an ecosystem dogfood showcase.

## Quick Start

```bash
# Summarize current git diff
kujo run patchbrief.kujo -- summarize

# JSON output for programmatic consumption
kujo run patchbrief.kujo -- summarize --format json

# Pretty JSON for easier human review
kujo run patchbrief.kujo -- summarize --format json --pretty

# Get test suggestions
kujo run patchbrief.kujo -- suggest-tests

# Generate a handoff note for reviewers
kujo run patchbrief.kujo -- handoff
```

Note: use `--` before PatchBrief arguments so Kujo does not parse tool flags as runtime flags.
PatchBrief treats `help` and `version` as commands; `--help` and `--version`
are not standalone aliases and will fall back to the command-order guidance.

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
