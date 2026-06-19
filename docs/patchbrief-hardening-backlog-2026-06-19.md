# PatchBrief Hardening Backlog

Date: 2026-06-19
Scope: Follow-up review items to make PatchBrief more robust, broadly useful, and presentation-ready as a Kujo showcase.

## Current assessment

PatchBrief is useful and test-backed, but it should still be treated as a dogfood beta rather than enterprise-grade production software. This session improved working-tree coverage, safer diff execution, output quality, tests, and README positioning. The items below are the next best work to push it toward a polished, universally useful developer tool.

## P0 - Release confidence and contract hardening

1. Publish a formal JSON schema for `summarize --format json` and `handoff --format json`
- Files: `src/summarize.kujo`, `src/handoff.kujo`, `tests/patchbrief_tests.kujo`, `docs/`
- Problem: JSON fields are stable by convention, but not documented as a machine contract.
- Fix: Add schema docs and tests that assert required keys, types, optional fields, and no-change behavior.
- Validation: Schema examples parse and contract tests cover clean, staged, unstaged, and untracked repositories.

2. Add explicit `has_changes` and `message` fields to JSON outputs
- Files: `src/summarize.kujo`, `src/handoff.kujo`, `tests/patchbrief_tests.kujo`, `README.md`
- Problem: Machine consumers infer no-change state from empty arrays and zero counts.
- Fix: Add explicit state fields while preserving existing keys for compatibility.
- Validation: No-change JSON tests assert `has_changes == false` and a human-readable message.

3. Harden test shellouts against runtime path differences
- Files: `tests/patchbrief_tests.kujo`
- Problem: Tests execute `kujo run ...`; this can call the wrong binary when multiple Kujo builds exist or when `kujo` is absent from `PATH`.
- Fix: Add a test helper that resolves `KUJO_BIN` when available and falls back to `kujo`.
- Validation: Tests pass with `KUJO_BIN=/path/to/kujo` and with the default command.

## P1 - Security and predictable execution

4. Add a single git-command helper with enforced timeout and `--no-ext-diff`
- Files: `src/git.kujo`
- Problem: Git command options are repeated manually, which makes future command additions easy to get wrong.
- Fix: Centralize git execution for read-only commands and default to `--no-ext-diff` where applicable.
- Validation: Tests cover summary, handoff, and file-specific diff paths.

5. Add path quoting tests for changed files with spaces and quotes
- Files: `src/git.kujo`, `tests/patchbrief_tests.kujo`
- Problem: `file_diff()` shell-quotes paths, but changed-file reporting should also be verified with awkward file names.
- Fix: Create temp-repo tests using names with spaces and apostrophes.
- Validation: JSON output remains valid and paths round-trip as expected.

6. Document threat model and non-goals
- Files: `README.md`, `docs/`
- Problem: PatchBrief runs local git commands and emits heuristic findings; security posture should be explicit for enterprise users.
- Fix: Add a short threat model covering local-only execution, no network calls, no secret scanning guarantees, and no LLM calls.
- Validation: README answers what the tool does and does not protect.

## P1 - Functionality and usefulness

7. Add optional `--base <ref>` support
- Files: `patchbrief.kujo`, `src/git.kujo`, `src/summarize.kujo`, `src/handoff.kujo`, `tests/patchbrief_tests.kujo`
- Problem: Teams often review a branch against `main`, not only the working tree.
- Fix: Let users summarize `git diff <base>...HEAD` while keeping current working-tree mode as default.
- Validation: Temp-repo tests cover default mode and base-ref mode.

8. Include per-file status in JSON
- Files: `src/git.kujo`, `src/summarize.kujo`, `src/handoff.kujo`
- Problem: Consumers can see file paths but not whether each file is staged, modified, deleted, renamed, or untracked.
- Fix: Parse porcelain status into structured file entries and preserve the existing `path` field.
- Validation: JSON tests cover modified, staged, deleted, renamed, and untracked states.

9. Add configurable risk and test rules
- Files: `src/summarize.kujo`, `src/suggest_tests.kujo`, `README.md`
- Problem: Current heuristics are hard-coded and useful but generic.
- Fix: Support an optional local config file for custom test commands, risk terms, and ignored paths.
- Validation: Tests cover default behavior and a temp config override.

## P2 - Performance and large-repo behavior

10. Add large-diff truncation metadata
- Files: `src/git.kujo`, `src/summarize.kujo`, `src/handoff.kujo`
- Problem: `full_diff()` caps output bytes, but reports do not tell users when analysis saw a truncated diff.
- Fix: Return `truncated` metadata and include it in JSON and Markdown risk notes.
- Validation: Fixture test forces a small cap and asserts truncation is reported.

11. Avoid reading full diff when only file-based suggestions are needed
- Files: `src/suggest_tests.kujo`, `src/git.kujo`
- Problem: `suggest-tests` already avoids `full_diff()`, but future refactors should preserve this performance property.
- Fix: Add a regression test or module boundary note to keep suggestion generation file-list-only.
- Validation: Test confirms `suggest-tests` succeeds in a repo with a very large tracked diff.

12. Benchmark common repo sizes
- Files: `docs/`, optional benchmark script
- Problem: There is no recorded performance envelope for small, medium, or large repositories.
- Fix: Add repeatable timing runs for clean repo, small patch, large patch, and many-file patch.
- Validation: Document expected runtime and command used to reproduce.

## P2 - Presentation and distribution

13. Add a polished example transcript
- Files: `README.md`, `docs/`
- Problem: The README explains commands but could better sell the workflow.
- Fix: Add a compact before/after example showing dirty repo input and PatchBrief summary/handoff output.
- Validation: Example stays copyable and consistent with tests.

14. Add installation guidance
- Files: `README.md`, `kennel.toml`
- Problem: Users outside this workspace need a clear path from clone to running `patchbrief.kujo`.
- Fix: Document clone, Kujo runtime setup, test, and first command.
- Validation: Fresh clone instructions work on a clean machine with Kujo installed.

15. Prepare a release checklist
- Files: `docs/`
- Problem: There is no repeatable release process.
- Fix: Add checklist for tests, README examples, version bump, schema compatibility, changelog, tag, and publish path.
- Validation: Checklist can drive the next tagged release without tribal knowledge.

## Root and generated-file hygiene

- Root files are currently appropriate: entrypoint, package/config manifests, spec, README, license, tests, and `src/`.
- Generated or dogfood artifacts are intentionally ignored under `.dogfood/`, `.kujo-mcp/`, and `tests/*.out`.
- New maintainer-facing docs should live under tracked `docs/` unless they are generated proof artifacts.

## Suggested next-session order

1. Add JSON contract/schema and explicit no-change state.
2. Harden test binary resolution with `KUJO_BIN`.
3. Add per-file status parsing.
4. Add threat model and install/release docs.
5. Start `--base <ref>` support once the default working-tree contract is locked.
