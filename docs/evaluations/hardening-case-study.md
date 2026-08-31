# Hardening PatchBrief

## Why we did it

PatchBrief turns an uncommitted Git diff into summaries, test suggestions, and reviewer handoffs. That puts repository-controlled text and potentially large command output directly on an agent-facing path. The hardening work focused on whether reports were safe, complete, explicit about limits, and reliable when Git itself failed.

## What changed

Current PatchBrief escapes terminal and Markdown control text, analyzes diffs through a bounded direct-argument process, reports truncation/error metadata, returns non-zero actionable errors when Git inspection fails, formalizes both JSON contracts, and runs contract tests in checksum-pinned CI.

## How we measured it

We compared the parent of the first hardening commit (`1e9ada3`) with `v1.0.1` (`76adc15`). Both ran through Kujo 1.1.0 on the same machine using identical deterministic Git fixtures. Normal workloads used three warmups and 20 measurements; stress/failure cases and five scaling sizes used 10 measured runs. We recorded wall/CPU time, RSS, output bytes/lines/`cl100k_base` tokens, full-test timing, source metrics, and eight deterministic Kujo Eval criteria.

## Before vs after

| Metric | Before | After | Change |
| --- | ---: | ---: | ---: |
| Kujo Eval | 5/8 | 8/8 | +3 checks |
| Typical median latency | 7.941 s | 2.400 s | -69.8% |
| Typical p95 | 12.515 s | 3.072 s | -75.4% |
| Large median latency | 27.032 s | 7.461 s | -72.4% |
| Failure latency | 1.010 s | 0.678 s | -32.9% |
| Failure output | 78 tokens | 15 tokens | -80.8% |
| Typical output | 237 tokens | 266 tokens | +12.2% |
| Stress peak RSS | 13.05 MB | 15.31 MB | +17.3% |

## Biggest improvements

The most important improvement was not raw speed. Three unsafe or misleading baseline behaviors became passing deterministic checks: Markdown injection was contained, oversized analysis was disclosed, and a broken Git index stopped with an actionable error.

Runtime improved most on realistic mixed worktrees. Across 20 runs, typical median latency fell by 5.542 seconds and large median latency fell by 19.572 seconds. Variance also fell sharply. The likely cause is the new direct bounded process path, although the evaluation did not benchmark each intermediate commit separately.

## What surprised us

Current was not faster everywhere. Homogeneous tracked-only fixtures were 6.6% to 49.1% slower at 5–50 files, including 3.840 s to 5.724 s at 25 files. This makes the speedup workload-sensitive rather than universal.

Preserving evidence also costs memory and context. The stress case now retains and reports the bounded diff instead of silently returning an empty analysis, raising peak RSS 17.3% and output by 50 tokens. That is a deliberate correctness tradeoff, but still a regression worth tracking.

## What did not improve

Dependency footprint remained zero. There is no PatchBrief binary or build step to shrink. Successful JSON summaries became slightly larger, not smaller. The expanded full test suite is 26.8% slower. Agent reasoning cycles and provider costs were not measured because PatchBrief makes no LLM or network calls.

## What remains

The highest-value follow-up is to profile the homogeneous tracked-file slowdown before changing code. A runtime-level comparison of shell `execute()` and direct `spawn_process()` would help explain why mixed worktrees improve while some tracked-only fixtures regress. Larger scaling and allocation tracing would strengthen the memory and curve conclusions.

## Reproducing the results

```bash
KUJO_BIN=/path/to/kujo-1.1.0 \
KUJO_EVAL_DIR=/path/to/kujo-eval \
bash scripts/run-hardening-evaluation.sh
python3 benchmarks/hardening/build_results.py
```

The full methodology, raw samples, Eval artifacts, regression report, and machine-readable results are stored under `docs/evaluations/` and `docs/evaluations/evidence/`.
