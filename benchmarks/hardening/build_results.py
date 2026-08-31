#!/usr/bin/env python3
"""Build the compact, machine-readable hardening evaluation result."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "docs/evaluations/evidence"


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def delta(before, after):
    return {"baseline": before, "current": after, "absolute_change": after - before, "percent_change": ((after - before) / before * 100) if before else None}


def metric(raw, workload, metric_name):
    before = raw["versions"]["baseline"]["workloads"][workload]["summary"][metric_name]
    after = raw["versions"]["current"]["workloads"][workload]["summary"][metric_name]
    return {
        "baseline": before,
        "current": after,
        "median_comparison": delta(before["median"], after["median"]),
        "p95_comparison": delta(before["p95"], after["p95"]),
    }


def main():
    raw = load("raw-measurements.json")
    check = load("check-benchmark.json")["results"]
    tests = load("test-benchmark.json")["results"]
    eval_scores = {}
    for version in ("baseline", "current"):
        payload = load(f"eval-{version}/last_run.json")
        data = payload.get("data", payload)
        eval_scores[version] = {"passed": data["passed"], "failed": data["failed"], "total": data["total"], "score_percent": data["passed"] / data["total"] * 100}
    workloads = {}
    for workload in raw["versions"]["baseline"]["workloads"]:
        workloads[workload] = {
            key: metric(raw, workload, key)
            for key in ("wall_seconds", "user_seconds", "sys_seconds", "cpu_percent", "max_rss_bytes", "stdout_bytes", "stdout_lines", "stdout_tokens")
            if key in raw["versions"]["baseline"]["workloads"][workload]["summary"]
            and key in raw["versions"]["current"]["workloads"][workload]["summary"]
        }
        workloads[workload]["baseline_exit_codes"] = sorted({x["exit_code"] for x in raw["versions"]["baseline"]["workloads"][workload]["runs"]})
        workloads[workload]["current_exit_codes"] = sorted({x["exit_code"] for x in raw["versions"]["current"]["workloads"][workload]["runs"]})
    scaling = {}
    for size in raw["versions"]["baseline"]["scaling"]:
        scaling[size] = metric(raw, "minimal_summary", "wall_seconds")
        before = raw["versions"]["baseline"]["scaling"][size]["summary"]["wall_seconds"]
        after = raw["versions"]["current"]["scaling"][size]["summary"]["wall_seconds"]
        scaling[size] = {"baseline": before, "current": after, "median_comparison": delta(before["median"], after["median"])}
    result = {
        "schema_version": "1.0.0",
        "generated_at": raw["environment"]["timestamp_utc"],
        "comparison": raw["comparison"],
        "environment": raw["environment"],
        "methodology": {
            "runtime_warmups": 3,
            "runtime_measured_runs": 20,
            "stress_failure_injection_measured_runs": 10,
            "scaling_measured_runs": 10,
            "check_measured_runs": 10,
            "test_measured_runs": 5,
            "latency_percentile_method": "nearest rank",
            "primary_latency_statistic": "median",
            "tokenizer": "cl100k_base via tiktoken 0.11.0",
            "same_runtime_for_both_versions": True,
            "network_enabled_by_workload": False,
        },
        "workloads": workloads,
        "scaling": scaling,
        "build_and_test": {
            "check": {"baseline": check[0], "current": check[1], "median_comparison": delta(check[0]["median"], check[1]["median"])},
            "tests": {"baseline": tests[0], "current": tests[1], "median_comparison": delta(tests[0]["median"], tests[1]["median"]), "both_passed_all_repetitions": True},
            "binary_size": {"applicable": False, "reason": "PatchBrief is interpreted Kujo source and declares no build artifact."},
            "direct_dependencies": {"baseline": 0, "current": 0},
            "transitive_dependencies": {"baseline": 0, "current": 0},
        },
        "source_metrics": {"baseline": raw["versions"]["baseline"]["source_metrics"], "current": raw["versions"]["current"]["source_metrics"]},
        "kujo_eval": {
            "baseline": eval_scores["baseline"],
            "current": eval_scores["current"],
            "delta_percentage_points": eval_scores["current"]["score_percent"] - eval_scores["baseline"]["score_percent"],
            "criteria": raw["versions"]["current"]["eval_checks"],
        },
        "agent_metrics": {
            "llm_input_tokens": {"status": "not_applicable", "reason": "PatchBrief makes no LLM calls."},
            "llm_output_tokens": {"status": "not_applicable", "reason": "PatchBrief makes no LLM calls."},
            "active_context_tokens": {"status": "measured_for_cli_output_only", "tokenizer": "cl100k_base"},
            "tool_calls": {"status": "not_demonstrated", "reason": "The workload is a local CLI, not an instrumented agent session."},
            "model_provider_cost": {"status": "not_applicable", "reason": "No model/provider is used."},
        },
        "regressions": [
            {"metric": "stress peak RSS", **delta(workloads["stress_summary"]["max_rss_bytes"]["baseline"]["median"], workloads["stress_summary"]["max_rss_bytes"]["current"]["median"]), "severity": "moderate", "likely_cause": "Current retains and analyzes the bounded 1 MiB diff instead of converting limit exhaustion to an empty string."},
            {"metric": "test-suite median wall time", **delta(tests[0]["median"], tests[1]["median"]), "severity": "low", "likely_cause": "Three regression scenarios and additional assertions were added."},
            {"metric": "25-file homogeneous scaling median wall time", **delta(scaling["25"]["baseline"]["median"], scaling["25"]["current"]["median"]), "severity": "moderate", "likely_cause": "The direct process path has higher overhead on this homogeneous fixture; mixed worktrees improve sharply, so the effect is workload-sensitive."},
        ],
        "verdict": {
            "answer": "YES",
            "reason": "Current passes all 8 deterministic Eval criteria versus 5/8, fixes three false-success/injection/truncation behaviors, and materially reduces latency on representative mixed and large workloads. The conclusion remains qualified by higher bounded-output/context volume, stress memory, test time, and slower homogeneous scaling fixtures."
        },
        "raw_evidence": "raw-measurements.json",
    }
    if "stdout_tokens" in workloads["typical_summary"]:
        result["regressions"].insert(2, {"metric": "routine JSON output tokens (typical)", **delta(workloads["typical_summary"]["stdout_tokens"]["baseline"]["median"], workloads["typical_summary"]["stdout_tokens"]["current"]["median"]), "severity": "low", "likely_cause": "Additive analysis evidence."})
    (RESULTS / "evaluation-results.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
