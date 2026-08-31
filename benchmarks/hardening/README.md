# Hardening benchmark harness

This harness compares the immediate pre-hardening commit `1e9ada307f16138dc705a32619cda11a0206d9c2` with release `v1.0.1` at `76adc15975c1c826a1ae59134cdb21905f6c3c48`. It creates detached temporary worktrees and deterministic Git fixtures, runs identical commands against both versions, and removes the temporary data afterward.

Default runtime measurements use three warmups and twenty recorded runs. The slower stress and failure paths retain at least ten recorded runs. Scaling measurements use three warmups and ten recorded runs at 1, 5, 10, 25, and 50 changed files. `/usr/bin/time -l` supplies CPU, resident-memory, filesystem-block, and context-switch observations. If Python `tiktoken` is available, the harness also counts `cl100k_base` tokens; otherwise it records token metrics as unavailable rather than estimating them.

Run the complete benchmark and Kujo Eval pass:

```bash
KUJO_BIN=/path/to/kujo-v1.1.0 \
KUJO_EVAL_DIR=/path/to/kujo-eval \
bash scripts/run-hardening-evaluation.sh
```

Install `tiktoken==0.11.0` in the selected Python environment before the run to reproduce the committed `cl100k_base` token measurements. Without it, the harness remains valid but records token metrics as unavailable.

For a faster harness smoke test:

```bash
python3 benchmarks/hardening/run_benchmarks.py --runs 1 --warmups 0 --scaling-runs 1 --output /tmp/patchbrief-evaluation-smoke
```

The committed evidence under `docs/evaluations/evidence/` was produced on the environment described in `evaluation-results.json`. The two Eval suites intentionally use identical criteria. Baseline failures are evidence of missing behavior, not harness failures.
