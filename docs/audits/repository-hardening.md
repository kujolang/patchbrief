# Repository Hardening Audit

## Repository

- Repository: `patchbrief`
- Branch: `main`
- Starting SHA: `1e9ada307f16138dc705a32619cda11a0206d9c2`
- Ending audited implementation SHA: `ff0ff7af2ebd13feff2bb6eb8af70150bc2f1783`
- Purpose: local, rule-based inspection of Git working-tree changes with Markdown and JSON summaries, test suggestions, and reviewer handoffs.
- Important dependencies and integrations: Kujo runtime, Git, POSIX-like local execution environment, Kennel package metadata, PatchBrief JSON consumers, the contract-test workflow, and the Kujo tool-artifact CI guard.

The audit receipt itself is committed after the ending audited implementation SHA above.

## Baseline

The starting tree was clean on `main` and matched `origin/main`. The baseline passed `kujo test` (one discovered test file; 8.49 seconds wall time), `kujo check` for every Kujo source/test file, shell syntax and the tool-artifact guard. All documented CLI commands completed successfully. No pre-existing verification failure was found.

The clean-tree baseline pretty JSON sizes were 631 bytes for `summarize` and 828 bytes for `handoff`. A controlled 10-run `hyperfine` comparison later measured the starting implementation at 606.910 ms mean (49.277 ms standard deviation) for clean-tree `summarize --format json`.

## Findings

| ID | Priority | Area | Finding | Evidence | Action | Status |
| -- | -------- | ---- | ------- | -------- | ------ | ------ |
| PBH-001 | P1 | Security/output | Newlines, terminal controls, HTML boundaries, and Markdown delimiters from repository-owned paths or commit subjects could alter human-readable reports. | Adversarial filenames produced a forged Markdown heading and broken code span. | Added centralized terminal/Markdown rendering helpers and regression coverage while preserving exact JSON values. | Fixed |
| PBH-002 | P1 | Resource/correctness | Diff analysis was capped at 1 MiB, but cap exhaustion was swallowed as an empty diff, making content heuristics silently incomplete. | A 2.25 MB tracked diff returned no truncation indication before the change. | Added bounded direct-argv execution with explicit byte, truncation, and error metadata plus human-readable risk warnings. | Fixed |
| PBH-003 | P1 | Failure semantics | `git status` failures returned an empty file list and could be reported as a clean tree. | `GIT_INDEX_FILE=/dev/null` made Git fail while PatchBrief previously had no failure-bearing status result. | Added a failure-bearing result contract, non-zero CLI behavior, JSON error payload, and regression test. | Fixed |
| PBH-004 | P1 | API/contracts | Handoff JSON had no formal schema, and the summary schema did not validate nested field types. | Only `schemas/patchbrief-summary.schema.json` existed; its nested shapes were unconstrained. | Added the handoff schema, strengthened the summary schema, and validated live outputs with Draft 2020-12 validation. | Fixed |
| PBH-005 | P2 | Documentation | README linked to a hardening backlog that had been deleted from the current tree. | The documented path did not exist at the starting SHA. | Removed the stale reference and documented current schemas and analysis limits. | Fixed |
| PBH-006 | P1 | CI | CI checked committed tool artifacts but did not execute PatchBrief contract tests. | `.github/workflows/kujo-tool-artifacts-guard.yml` was the only workflow at the starting SHA. | Added a contract-test workflow that verifies a checksum-pinned Kujo v1.1.0 release binary before running source checks and tests. | Fixed |

## Changes Implemented

### Safe human-readable rendering

- Problem/root cause: raw Git-controlled strings were concatenated into Markdown.
- Implementation: `src/common.kujo` now renders terminal controls visibly, escapes Markdown text, and uses HTML-safe `<code>` elements for arbitrary paths. Summary, handoff, and manual-check renderers use these helpers.
- Tests: added control-character, newline, backtick, and HTML-boundary regression assertions.
- Compatibility: JSON values remain exact. Markdown headings and sections are unchanged; path markup changed from backtick spans to equivalent HTML code elements so arbitrary backticks cannot break the report.

### Bounded, inspectable diff analysis

- Problem/root cause: `execute()` converts output-limit exhaustion into an exception, and the old wrapper converted that exception to an empty string.
- Implementation: `src/git.kujo` now uses `spawn_process()` with direct argv, a 1 MiB bound, timeout, and native truncation metadata. Unborn repositories fall back to the cached diff. Summary and handoff JSON include `analysis.diff_bytes_analyzed`, `analysis.diff_max_bytes`, `analysis.diff_truncated`, and `analysis.diff_error`; Markdown reports warn when analysis is incomplete.
- Tests: added a deterministic small-limit truncation regression and preserved unborn-repository behavior.
- Compatibility: fields are additive. Existing JSON fields and data types remain unchanged.

### Explicit working-tree failures

- Problem/root cause: `changed_files()` erased Git status failures by returning `[]`.
- Implementation: command paths consume a failure-bearing status result and exit 1 with a concise diagnostic or JSON error payload.
- Tests: added a forced invalid-index regression.
- Compatibility: successful behavior is unchanged. A previously false-success failure now correctly exits non-zero.

### JSON contracts and documentation

- Added `schemas/patchbrief-handoff.schema.json`.
- Strengthened nested summary/file validation in `schemas/patchbrief-summary.schema.json`.
- Updated README, security boundary, and changelog documentation.

## Performance & Efficiency

The completed clean-tree implementation measured 585.137 ms mean (21.566 ms standard deviation) across the same 10-run `hyperfine` command, versus 606.910 ms (49.277 ms) at the starting SHA. The overlap and short sample do not support a material speedup claim; importantly, no runtime regression was observed.

Pretty JSON output increased by 149 bytes in each command: summary 631 to 780 bytes and handoff 828 to 977 bytes. The increase is intentional, bounded, machine-readable analysis evidence. Help, clean Markdown summary, and clean test-suggestion output remained 1,081, 94, and 81 bytes respectively. No runtime package dependency was added; bounded diff inspection uses Kujo's existing direct process API.

The full test wall time increased from 8.49 seconds to 13.08 seconds on clean trees because three security/failure/resource regressions were added. Production command latency remained within measurement variance.

## Security

Reviewed trust boundaries included CLI arguments, `PATCHBRIEF_CWD`, Git-controlled paths and commit subjects, subprocess construction, shell quoting, process output limits, Markdown/terminal rendering, JSON serialization, and local filesystem/repository inspection. PatchBrief remains read-only and makes no network or LLM calls. Direct argv is now used for the bounded diff hot path; the existing file-specific shell path retains single-quote escaping. Regression tests cover unusual paths, output injection, diff bounds, and Git inspection failure.

Remaining security scope is intentionally heuristic: PatchBrief is not a secret scanner, vulnerability scanner, or policy engine. JSON consumers must continue treating repository-derived strings as untrusted data.

## Compatibility

- Public APIs: no existing exported function was removed; new analysis/status helpers are additive.
- CLI: commands and flags are unchanged. Git inspection failure now exits 1 instead of falsely succeeding.
- Markdown: section names are unchanged; arbitrary paths render with HTML-safe code tags.
- JSON: existing fields and types are unchanged; the `analysis` object is additive.
- Schemas: summary schema now describes the additive analysis object and concrete nested types; a handoff schema was added.
- Configuration and environment variables: unchanged.
- External consumers: consumers following the documented ignore-unknown-fields rule are unaffected. Exact-byte JSON snapshots must accept the new `analysis` object.

## Cross-Repository Follow-Ups

None. Kujo v1.1.0 now publishes checksum-verifiable release binaries, so PatchBrief can enforce its contract tests without modifying the runtime repository.

## Remaining Work

- **P0:** none.
- **P1:** none.
- **P2:** consider structured per-file status and explicit no-change JSON fields only as additive, separately versioned contract work.
- **P3:** none admitted.
- **Needs more evidence:** configurable heuristics, base-ref mode, and broader repository-size benchmarks; these are features or product decisions, not demonstrated defects in this audit.
- **Not worth changing:** concurrency, persistent-state, cache, network, and dependency optimizations; PatchBrief has none of those runtime mechanisms.

## Verification Receipt

Passed commands/checks:

```text
kujo test
kujo check patchbrief.kujo
kujo check src/common.kujo
kujo check src/git.kujo
kujo check src/handoff.kujo
kujo check src/suggest_tests.kujo
kujo check src/summarize.kujo
kujo check tests/patchbrief_tests.kujo
kujo run patchbrief.kujo -- help
kujo run patchbrief.kujo -- summarize
kujo run patchbrief.kujo -- summarize --format json --pretty
kujo run patchbrief.kujo -- suggest-tests
kujo run patchbrief.kujo -- handoff --format json --pretty
bash -n .github/scripts/check-kujo-tool-artifacts.sh
bash .github/scripts/check-kujo-tool-artifacts.sh
bash .github/scripts/check-version-sync.sh
git diff --check
python Draft 2020-12 validation of both live JSON outputs against both schemas
hyperfine --warmup 2 --runs 10 <starting summarize JSON> <ending summarize JSON>
```

Adversarial manual verification also confirmed that newline/backtick/HTML filenames cannot inject Markdown structure, a 2.25 MB diff reports truncation at 1,048,576 bytes, and unborn repositories retain a successful empty analysis result.
