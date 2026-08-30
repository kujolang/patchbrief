# Changelog

All notable changes to PatchBrief are documented here.

## [Unreleased]

- Escaped repository-controlled text in Markdown reports to prevent structure and terminal-control injection while preserving exact JSON values.
- Added explicit bounded-diff analysis metadata and warnings when content heuristics reach the 1 MiB limit.
- Added a formal handoff JSON schema and strengthened summary schema field validation.

## [1.0.0] - 2026-08-08

- Declared Markdown/JSON summaries, test suggestions, and handoff output stable for local working-tree review.
- Aligned package, project, CLI, generated-output, and contract-test versions at 1.0.0.

## [0.1.0] - 2026-06-27

- Prepared PatchBrief for public release with git diff summaries, suggested test output, handoff briefs, JSON/Markdown contracts, and CLI regression coverage.
