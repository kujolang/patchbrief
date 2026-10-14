# Changelog

All notable changes to PatchBrief are documented here.

## [Unreleased]

## [1.0.2] - 2026-10-14

### Fixed

- Run Git inspection through bounded argument-vector processes without shell authority; use the native UTC clock for handoffs.
- Disable Git text conversion and external diff commands during review, and treat file pathspecs literally.
- Reject failed, timed-out or truncated Git output instead of reporting a complete inspection.

### Compatibility

- Require Kujo 1.6.0 or newer; CLI commands and JSON shapes remain unchanged apart from the tool version.
- Add real Git regression coverage in VM and interpreter modes on Linux, macOS and Windows.
- Include the reproducible hardening evaluation harness and historical benchmark evidence; those measurements are not new release performance claims.

## [1.0.1] - 2026-08-30

- Escaped repository-controlled text in Markdown reports to prevent structure and terminal-control injection while preserving exact JSON values.
- Added explicit bounded-diff analysis metadata and warnings when content heuristics reach the 1 MiB limit.
- Made Git working-tree inspection failures explicit instead of reporting a false clean state.
- Added a formal handoff JSON schema and strengthened summary schema field validation.
- Added CI contract tests using a checksum-pinned Kujo v1.1.0 release binary.

## [1.0.0] - 2026-08-08

- Declared Markdown/JSON summaries, test suggestions, and handoff output stable for local working-tree review.
- Aligned package, project, CLI, generated-output, and contract-test versions at 1.0.0.

## [0.1.0] - 2026-06-27

- Prepared PatchBrief for public release with git diff summaries, suggested test output, handoff briefs, JSON/Markdown contracts, and CLI regression coverage.
