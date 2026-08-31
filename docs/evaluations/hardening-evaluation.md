# PatchBrief Before/After Hardening Evaluation

## Executive summary

PatchBrief `v1.0.1` is empirically better engineered than the immediate pre-hardening build, but it is not uniformly leaner. The hardening pass replaced silent and unsafe behavior with explicit evidence: repository-controlled Markdown is escaped, an oversized diff is analyzed up to a disclosed 1 MiB bound, Git inspection failures terminate with an actionable error, JSON contracts are formalized, and CI now runs contract tests using a checksum-pinned Kujo runtime.

The comparison uses baseline `1e9ada307f16138dc705a32619cda11a0206d9c2` and current `76adc15975c1c826a1ae59134cdb21905f6c3c48` (`v1.0.1`). Baseline is the parent of the first commit in the contiguous August 30 hardening sequence. Choosing `v1.0.0` would also include unrelated August bug fixes and would not isolate this pass. Both revisions ran from clean detached worktrees with the same Kujo 1.1.0 binary, deterministic Git fixtures, and no network or model calls.

Correctness and failure behavior improved decisively. The same eight-check Kujo Eval rubric scored baseline 5/8 (62.5%) and current 8/8 (100%). Baseline falsely reported an invalid Git index as a successful clean result, silently discarded oversized diff analysis, and allowed a crafted filename to inject Markdown structure. Current passed all three cases while preserving the normal summary and handoff contracts. Five repeated full test-suite runs passed for each revision; no flaky run was observed.

Representative mixed-worktree latency also improved. Across 20 measured runs after three warmups, typical median latency fell from 7.941 s to 2.400 s (-69.8%) and p95 fell from 12.515 s to 3.072 s. The 40-file large workload fell from 27.032 s to 7.461 s (-72.4%), with p95 down from 35.568 s to 11.327 s. This result is workload-sensitive: homogeneous tracked-file scaling fixtures were 6.6% to 49.1% slower at 5–50 files, and the minimal difference (0.816 s to 0.785 s) is too small relative to variance to claim as a meaningful win. The evidence supports a strong improvement for realistic mixed worktrees, not a universal speedup.

The largest tradeoffs are bounded and explainable. Current retains useful diff evidence instead of collapsing output-limit exhaustion to an empty string, so stress peak resident memory rose from 13.05 MB to 15.31 MB (+17.3%). Typical JSON grew from 237 to 266 `cl100k_base` tokens (+12.2%); stress JSON grew from 85 to 135 tokens (+58.8%) because it now reports truncation and analysis metadata. On the corrected failure path, however, output fell from 78 to 15 tokens (-80.8%) and latency fell from 1.010 s to 0.678 s (-32.9%). The full test median rose from 26.286 s to 33.340 s (+26.8%) because the suite exercises three additional security/resource/failure regressions.

For actual users, current is substantially more trustworthy and usually faster on mixed changes. Agents receive slightly more context on successful summaries, but that context now says whether the evidence is complete. There are no LLM calls, provider costs, retries, caches, or network operations to optimize. Dollar savings, model-token savings, agent reasoning cycles, and external tool-call reductions are not demonstrated.

## Before/after scorecard

| Metric | Baseline | Current | Change | Classification |
| --- | ---: | ---: | ---: | --- |
| Kujo Eval | 5/8 (62.5%) | 8/8 (100%) | +37.5 points | Clear improvement |
| Typical median latency, n=20 | 7.941 s | 2.400 s | -5.542 s (-69.8%) | Clear improvement |
| Typical p95 latency | 12.515 s | 3.072 s | -9.443 s (-75.4%) | Clear improvement |
| Large median latency, n=20 | 27.032 s | 7.461 s | -19.572 s (-72.4%) | Clear improvement |
| Large p95 latency | 35.568 s | 11.327 s | -24.241 s (-68.2%) | Clear improvement |
| Failure median latency, n=10 | 1.010 s | 0.678 s | -0.332 s (-32.9%) | Clear improvement |
| Failure output | 78 tokens / 314 B | 15 tokens / 63 B | -80.8% / -79.9% | Clear improvement |
| Typical output | 237 tokens / 827 B | 266 tokens / 934 B | +12.2% / +12.9% | Bounded regression |
| Stress peak RSS, n=10 | 13.05 MB | 15.31 MB | +2.26 MB (+17.3%) | Tradeoff/regression |
| Typical peak RSS | 12.65 MB | 12.95 MB | +0.30 MB (+2.4%) | Small regression |
| Source LOC | 938 | 1,077 | +139 (+14.8%) | More explicit machinery |
| Test LOC | 344 | 384 | +40 (+11.6%) | Coverage increase |
| Full-test median, n=5 | 26.286 s | 33.340 s | +7.053 s (+26.8%) | Test-time regression |
| `kujo check` median, n=10 | 38.73 ms | 40.05 ms | +1.32 ms (+3.4%) | Inconclusive/noisy |
| Direct dependencies | 0 | 0 | none | Neutral |
| Test success | 5/5 runs | 5/5 runs | none | Neutral |

All token counts are measured locally with `tiktoken` 0.11.0 and `cl100k_base`. They quantify text an agent might place in context; they are not provider-billed tokens.

## Evaluation boundary and Git reconstruction

The primary worktree was clean on `main`, matched `origin/main`, and pointed at `76adc15` when the evaluation began. Current was evaluated as the immutable clean detached tree at `76adc15975c1c826a1ae59134cdb21905f6c3c48`, committed 2026-08-30 19:31:47-04:00 and tagged `v1.0.1`. Baseline was the clean detached tree at `1e9ada307f16138dc705a32619cda11a0206d9c2`, committed 2026-08-11 16:03:44-04:00; it has no tag.

The hardening sequence is contiguous and begins immediately after baseline:

| Commit | Change | Intended effect | Observed effect |
| --- | --- | --- | --- |
| `1ca0cd1` | Safe Markdown/terminal rendering; bounded diff metadata; schemas and regressions | Prevent output injection and make incomplete analysis visible | Injection and truncation Eval checks changed from fail to pass; successful output grew |
| `f7180e6` | Failure-bearing Git status result | Stop false-clean reports | Invalid-index Eval changed from fail to pass; failure output and latency fell |
| `ff0ff7a` | Direct-argv bounded diff process | Avoid shell mediation and preserve native truncation/error state | Representative mixed and large latency fell sharply; attribution is inferred from source mapping, not isolated per-commit timing |
| `215dbee` | Hardening audit | Preserve rationale and evidence | Maintainability/documentation only; no runtime claim |
| `76adc15` | Version synchronization and checksum-pinned CI | Reproducible release contract | Current CI/test contract exists; test suite remains green |

`v1.0.0` (`ba1a9b1`) was considered and rejected as the primary baseline because commits `10789df`, `097e355`, and `1e9ada3` between it and hardening fixed and tested ten separate bugs. Including those would overstate the effect of this pass.

## Architectural change analysis

### Safe presentation boundary

Previously, paths, branch names, repository names, and commit subjects were concatenated directly into Markdown. A filename containing a newline, backtick, or HTML delimiter could create a forged section or break a code span. Current centralizes terminal-control visualization, Markdown text escaping, and HTML-safe `<code>` rendering in `src/common.kujo`; summary, handoff, and test-suggestion paths use those helpers. JSON retains exact repository values.

The measurable outcome is behavioral, not a speed optimization: the adversarial Eval case now passes. The injected report is 22 bytes and 9 tokens larger because the unsafe characters are represented visibly. Median runtime moved from 1.005 s to 1.036 s, while p95 improved from 1.613 s to 1.177 s; the overlapping distributions do not support a runtime regression claim.

### Bounded, inspectable diff analysis

Baseline used `execute()` with a 1 MiB output cap and converted exceptions to an empty diff. Crossing the cap therefore produced a plausible but incomplete report with no warning. Current uses `spawn_process()` with a direct argument vector, 30-second timeout, 1 MiB stdout cap, native truncation metadata, and an unborn-repository fallback. Summary and handoff expose analyzed bytes, limit, truncation, and error state.

On the 1.1 MB stress fixture, baseline returned 350 bytes/85 tokens and failed the completeness criterion. Current returned 565 bytes/135 tokens and passed. Current median latency was 1.225 s versus 1.353 s, but peak RSS increased 17.3% because current retains the bounded evidence that baseline discarded. This is an acceptable correctness-for-memory tradeoff at the fixed 1 MiB ceiling, not a memory optimization.

The direct process path is the most plausible cause of the 69.8–72.4% latency reductions on mixed typical/large fixtures. CPU time also fell on large input: median user time 7.065 s to 5.305 s and system time 0.640 s to 0.440 s. Wall time improved more than CPU time, implying reduced waiting or process-capture overhead. Because intermediate commits were not benchmarked, this causal attribution is inferred rather than experimentally isolated.

### Explicit failure semantics

Baseline `changed_files()` erased Git status errors and continued as though the tree were clean. Current returns `{ok, files}` and all command paths fail with exit 1 and either concise text or structured JSON. Under `GIT_INDEX_FILE=/dev/null`, baseline exited 0 with a 314-byte false-success summary; current exited 1 with a 63-byte actionable error. This both improves correctness and avoids unnecessary downstream Git work.

### Contracts, CI, and dependencies

Current adds a handoff schema, strengthens nested summary schema types, adds contract tests, and introduces checksum-pinned CI plus version synchronization checks. No runtime package was added: both manifests declare zero direct and zero transitive dependencies, and PatchBrief remains interpreted source with no build command or binary artifact. Binary size, release build time, and incremental linking are therefore not applicable.

## Benchmark methodology

The host was macOS 26.3.1 on x86_64, Darwin 25.3.0, Intel Core i7-9750H (6 physical/12 logical CPUs), 16 GiB RAM, APFS SSD, Git 2.42.0, Rust/Cargo 1.96.0, Python 3.10.5, and Kujo 1.1.0. Both revisions used the same runtime binary and environment. PatchBrief performed no network or model operations.

The harness created temporary detached Git worktrees and deterministic fixture repositories. It ran three warmups followed by 20 measurements for normal workloads. Stress, failure, and injection used at least one warmup and 10 measurements. Scaling used three warmups and 10 measurements at 1, 5, 10, 25, and 50 tracked changed files. `/usr/bin/time -l` supplied user/system CPU, RSS, filesystem block, and context-switch data. Latency uses median as the primary statistic, nearest-rank p95/p99, and sample standard deviation. The complete raw samples, stdout, and time output are preserved.

Workloads were:

| Workload | Fixture and purpose |
| --- | --- |
| Minimal | Clean one-file repository; startup/fixed overhead |
| Typical | Eight tracked modifications plus two untracked tests; common mixed worktree |
| Large | Thirty tracked modifications plus ten untracked docs; repository-scale behavior |
| Stress | 1.1 MB single-file diff; output cap and evidence preservation |
| Failure | Invalid Git index; fail-fast behavior and diagnostic quality |
| Agent-facing | Typical handoff Markdown and adversarial Markdown filename; context volume and usability |
| Scaling | Homogeneous tracked changes at five sizes; curve and workload sensitivity |

Known limitations: the macOS scheduler and concurrent host activity create variance; p99 with 10–20 samples is effectively the worst observation and should not be generalized; allocation counts and subprocess counts were not instrumented; full tests used five rather than ten samples because each run took 26–36 seconds; the tokenizer is a context-size proxy, not PatchBrief billing; and causal attribution was not isolated commit by commit.

## Runtime, CPU, memory, and scaling

Typical throughput derived from median latency increased from 0.126 to 0.417 operations/s (+231%). Large throughput increased from 0.0370 to 0.134 operations/s (+262%). Typical latency standard deviation fell from 2.474 s to 0.331 s, and large fell from 5.577 s to 1.683 s, so current was both faster and less variable in those workloads.

Minimal latency changed by only 31 ms (-3.8%) with standard deviations of 41–45 ms; this is neutral. Agent handoff median improved 13.7% (3.254 s to 2.807 s), but current user CPU increased 12.3%, so it appears to trade more active processing for less waiting. Stress median improved 9.4%, with substantially lower variance, but incurred the measured memory tradeoff.

The homogeneous scaling series does not demonstrate a better curve:

| Changed files | Baseline median | Current median | Current change |
| ---: | ---: | ---: | ---: |
| 1 | 1.039 s | 1.137 s | +9.5% |
| 5 | 1.594 s | 1.948 s | +22.2% |
| 10 | 2.452 s | 2.615 s | +6.6% |
| 25 | 3.840 s | 5.724 s | +49.1% |
| 50 | 10.274 s | 11.022 s | +7.3% |

Both series are startup-dominated at small sizes and irregular at larger sizes; neither supports a clean constant/linear/N-log-N classification. There is no evidence of exponential behavior within the tested range. Current's 25-file slowdown is operationally meaningful and remains an optimization opportunity. The contrast with large mixed worktrees shows that file count alone does not predict the direct-process benefit.

## Token, context, and agentic efficiency

PatchBrief has no LLM integration, so input, completion, cached, and provider-billed tokens are not applicable. The measured token figures cover CLI output only. Normal current summaries add a fixed analysis object: minimal +28 tokens, typical +29, large +29. Handoff adds 40 tokens. This is a context cost, but it preserves completeness evidence that baseline omitted.

The failure path saves 63 output tokens per execution while changing task success from no to yes. At the same output mix, that is 6,300 tokens per 100 failures, 63,000 per 1,000, and 630,000 per 10,000. Conversely, 1,000 typical successful summaries add 29,000 context tokens. No dollar estimate is provided because no model/provider pricing or actual model invocation is involved.

Agent reasoning/action cycles, repeated reads, tool retries, model completion rate, and time-to-evidence were not measured because the component is a local deterministic CLI rather than an instrumented agent runner. Each benchmark invoked PatchBrief once. No claim of fewer agent tool calls is made.

## Reliability and Kujo Eval report

The stored Eval definitions use the same eight criteria for both revisions: valid minimal JSON, complete typical file accounting, actionable Git failure, disclosed truncation, contained Markdown injection, usable handoff sections, successful normal repetitions, and stable output size. Baseline passed five and failed the three hardening targets. Current passed all eight. The score is the actual Kujo Eval pass ratio; no subjective weighted score was invented.

| Category | Baseline | Current | Change |
| --- | ---: | ---: | ---: |
| Correctness | 2/2 | 2/2 | neutral |
| Failure behavior | 0/2 | 2/2 | +2 |
| Agent usability | 1/2 | 2/2 | +1 |
| Reliability | 1/1 | 1/1 | neutral |
| Determinism | 1/1 | 1/1 | neutral |
| Overall | 5/8 | 8/8 | +3 checks / +37.5 points |

All 20 normal invocations per version exited successfully, and typical stdout size was byte-stable across repetitions. Five complete test runs per version also passed. Current's test median is 26.8% slower; this measures additional regression coverage, not production command latency. No flaky behavior, crash, panic, or timeout occurred in the measured normal current workloads.

## Complexity and maintainability

Complexity was added, not removed: production source LOC rose 14.8%, functions rose from 88 to 97 across source/tests, branch tokens rose from 128 to 153, tracked files rose from 20 to 24, and tracked bytes rose 34.1%. The increase is localized in reusable rendering, failure-bearing results, bounded process metadata, schemas, CI, tests, and audit documentation. There is no evidence that complexity was merely hidden in a dependency because dependency counts stayed at zero.

Maintainability therefore improves in contracts, observability, and testability while declining in raw code volume and control-flow surface. The new JSON schema and centralized renderers reduce duplicated policy, but future changes must preserve more explicit states. No `unwrap`/`expect` use was found; TODO/FIXME count remained nine. Cyclomatic complexity was not measured with a Kujo-aware parser, so branch-token counts are structural proxies only.

## Change-to-result mapping

| Code change | Behavioral change | Measured impact | Evidence class |
| --- | --- | --- | --- |
| Central render helpers and safe call sites | Repository text cannot become Markdown/terminal control | Injection Eval fail to pass; +22 B/+9 tokens | Measured + observed |
| Native bounded diff process and metadata | Preserves up to 1 MiB and declares truncation | Stress Eval fail to pass; 1.353 s to 1.225 s; RSS +17.3% | Measured; causal link inferred |
| Direct argv instead of shell command | Less shell/process-capture waiting on mixed diffs | Typical -69.8%; large -72.4%; lower CPU and variance | Measured result; primary cause inferred |
| Failure-bearing status result | Invalid index stops immediately | Exit 0 to 1; 1.010 s to 0.678 s; 78 to 15 tokens | Measured |
| Additive analysis JSON | Agents can judge completeness | +29 tokens on typical/large summaries | Measured |
| Three regression scenarios | Prevent reintroduction of hardening defects | Eval 5/8 to 8/8; test median +26.8% | Measured |

## Regressions and Tradeoffs

| Metric | Baseline | Current | Severity | Assessment and action |
| --- | ---: | ---: | --- | --- |
| Stress peak RSS | 13.05 MB | 15.31 MB | Moderate | Expected cost of retaining bounded evidence; keep 1 MiB cap and monitor |
| 25-file homogeneous latency | 3.840 s | 5.724 s | Moderate | Workload-sensitive direct-process overhead; profile before changing implementation |
| Typical output context | 237 tokens | 266 tokens | Low | Useful fixed metadata; acceptable unless an explicit compact mode is designed |
| Test-suite median | 26.286 s | 33.340 s | Low | More coverage; investigate VM fallback/test fixture startup separately |
| Source/control-flow volume | 938 LOC / 128 branch tokens | 1,077 / 153 | Low | Explicit safety state; contain future policy in shared helpers |
| Large peak RSS | 17.11 MB | 18.25 MB | Low | +6.6%; monitor with larger mixed repositories |

No functionality loss was observed in the tested command contracts. A blanket statement that no meaningful regressions exist would not be supported.

## Remaining opportunities

- **P0:** none identified.
- **P1:** profile the homogeneous tracked-file path, especially the 25-file case, before considering any change. The regression is measured but its cause is not isolated.
- **P1:** add a Kujo-runtime benchmark for shell `execute()` versus direct `spawn_process()` across mixed tracked/untracked repositories; this is a cross-repository follow-up because the behavior likely belongs to the runtime.
- **P2:** consider an opt-in compact JSON representation only if consumers demonstrate that the 29-token analysis object is costly; do not remove completeness evidence by default.
- **P2:** isolate test VM fallback and fixture startup costs; production latency is not responsible for the full test-time increase.
- **P3:** extend scaling beyond 50 files and measure allocations/subprocess counts on an instrumented runner.

## Reproduction and evidence

Run:

```bash
KUJO_BIN=/path/to/kujo-1.1.0 \
KUJO_EVAL_DIR=/path/to/kujo-eval \
bash scripts/run-hardening-evaluation.sh
python3 benchmarks/hardening/build_results.py
```

The benchmark runner creates and removes temporary worktrees and fixtures. Eval runs from an isolated temporary copy of its runtime modules to avoid `src/` module-name collisions. The following committed artifacts support audit and reproduction:

- `benchmarks/hardening/run_benchmarks.py`: fixtures, repetitions, statistics, token counting, environment capture.
- `eval/hardening-baseline.json` and `eval/hardening-current.json`: identical evaluation criteria.
- `docs/evaluations/evidence/raw-measurements.json`: every recorded sample and representative output.
- `docs/evaluations/evidence/evaluation-results.json`: compact machine-readable comparison.
- `docs/evaluations/evidence/eval-*/`: Kujo Eval reports and checksum manifests.
- `docs/evaluations/evidence/*-benchmark.json`: source-check and full-test timings.

## Final question

**If we erase the commit messages and ignore what the hardening work intended to accomplish, does the empirical evidence independently demonstrate that CURRENT is a better engineered version than BASELINE?**

**YES.** Current passes all eight deterministic outcome criteria versus five, eliminates three independently reproduced unsafe/false-success behaviors, and materially reduces latency and variance on representative mixed and large workloads. The answer is not “uniformly better”: current uses more memory under bounded-diff stress, emits more successful-path context, runs a larger test suite more slowly, and regresses homogeneous scaling cases. Those losses are measured and material, but they do not outweigh the correctness, evidence integrity, and realistic-workload gains.
