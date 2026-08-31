#!/usr/bin/env python3
"""Reproducible before/after benchmark harness for the PatchBrief hardening pass."""

from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import shutil
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

BASELINE_SHA = "1e9ada307f16138dc705a32619cda11a0206d9c2"
CURRENT_SHA = "76adc15975c1c826a1ae59134cdb21905f6c3c48"
TIME_RE = {
    "real_seconds": re.compile(r"^\s*([0-9.]+) real\s+([0-9.]+) user\s+([0-9.]+) sys$", re.M),
    "max_rss_bytes": re.compile(r"^\s*(\d+)\s+maximum resident set size$", re.M),
    "block_reads": re.compile(r"^\s*(\d+)\s+block input operations$", re.M),
    "block_writes": re.compile(r"^\s*(\d+)\s+block output operations$", re.M),
    "voluntary_context_switches": re.compile(r"^\s*(\d+)\s+voluntary context switches$", re.M),
    "involuntary_context_switches": re.compile(r"^\s*(\d+)\s+involuntary context switches$", re.M),
}


def run(cmd, cwd=None, env=None, check=True, text=True):
    return subprocess.run(cmd, cwd=cwd, env=env, check=check, text=text, capture_output=True)


def git(repo, *args):
    return run(["git", "-C", str(repo), *args]).stdout.strip()


def write(path: Path, content: str | bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content, encoding="utf-8")


def init_repo(path: Path, tracked: dict[str, str], changed: dict[str, str], untracked: dict[str, str] | None = None):
    path.mkdir(parents=True)
    run(["git", "init", "-q"], cwd=path)
    run(["git", "config", "user.email", "benchmark@example.invalid"], cwd=path)
    run(["git", "config", "user.name", "PatchBrief Benchmark"], cwd=path)
    for name, content in tracked.items():
        write(path / name, content)
    run(["git", "add", "."], cwd=path)
    run(["git", "commit", "-q", "-m", "benchmark fixture baseline"], cwd=path)
    for name, content in changed.items():
        write(path / name, content)
    for name, content in (untracked or {}).items():
        write(path / name, content)


def make_fixtures(root: Path):
    fixtures = {}
    init_repo(root / "minimal", {"README.md": "# Fixture\n"}, {})
    fixtures["minimal"] = root / "minimal"

    tracked = {f"src/module_{i:03}.kujo": "func value() { return 1 }\n" * 12 for i in range(8)}
    changed = {f"src/module_{i:03}.kujo": "func value() { return 2 }\n" * 20 for i in range(8)}
    untracked = {f"tests/new_{i:03}_test.kujo": "assert(true)\n" * 12 for i in range(2)}
    init_repo(root / "typical", tracked, changed, untracked)
    fixtures["typical"] = root / "typical"

    tracked = {f"src/feature_{i:04}.kujo": "let old = 1\n" * 12 for i in range(30)}
    changed = {f"src/feature_{i:04}.kujo": "let new = 2\n" * 20 for i in range(30)}
    untracked = {f"docs/note_{i:04}.md": "benchmark note\n" * 10 for i in range(10)}
    init_repo(root / "large", tracked, changed, untracked)
    fixtures["large"] = root / "large"

    init_repo(root / "stress", {"large.txt": "a" * 1_100_000 + "\n"}, {"large.txt": "b" * 1_100_000 + "\n"})
    fixtures["stress"] = root / "stress"

    init_repo(root / "failure", {"README.md": "failure fixture\n"}, {})
    fixtures["failure"] = root / "failure"

    injection = root / "injection"
    injection.mkdir(parents=True)
    run(["git", "init", "-q"], cwd=injection)
    run(["git", "config", "user.email", "benchmark@example.invalid"], cwd=injection)
    run(["git", "config", "user.name", "PatchBrief Benchmark"], cwd=injection)
    write(injection / "safe.txt", "safe\n")
    run(["git", "add", "."], cwd=injection)
    run(["git", "commit", "-q", "-m", "baseline"], cwd=injection)
    write(injection / "evil\n## injected`<tag>.md", "untrusted\n")
    fixtures["injection"] = injection

    scaling = {}
    for count in (1, 5, 10, 25, 50):
        target = root / f"scale-{count}"
        old = {f"src/item_{i:04}.kujo": "let value = 1\n" * 20 for i in range(count)}
        new = {f"src/item_{i:04}.kujo": "let value = 2\n" * 20 for i in range(count)}
        init_repo(target, old, new)
        scaling[str(count)] = target
    fixtures["scaling"] = scaling
    return fixtures


def percentile(values, q):
    ordered = sorted(values)
    rank = max(1, math.ceil(q * len(ordered)))
    return ordered[rank - 1]


def summary(values):
    return {
        "n": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "p95": percentile(values, 0.95),
        "p99": percentile(values, 0.99),
    }


def tokenize(text: str):
    try:
        import tiktoken  # type: ignore
        encoder = tiktoken.get_encoding("cl100k_base")
        return len(encoder.encode(text)), "cl100k_base"
    except Exception:
        return None, None


def measure_once(kujo: Path, script: Path, cwd: Path, args: list[str], extra_env=None):
    env = os.environ.copy()
    env.update(extra_env or {})
    cmd = ["/usr/bin/time", "-l", str(kujo), "run", str(script), "--", *args]
    started = time.perf_counter()
    proc = subprocess.run(cmd, cwd=cwd, env=env, text=False, capture_output=True)
    wall = time.perf_counter() - started
    stdout = proc.stdout.decode("utf-8", "replace")
    stderr = proc.stderr.decode("utf-8", "replace")
    match = TIME_RE["real_seconds"].search(stderr)
    user_seconds = float(match.group(2)) if match else None
    sys_seconds = float(match.group(3)) if match else None
    record = {
        "wall_seconds": wall,
        "time_real_seconds": float(match.group(1)) if match else None,
        "user_seconds": user_seconds,
        "sys_seconds": sys_seconds,
        "cpu_percent": ((user_seconds + sys_seconds) / wall * 100) if match and wall else None,
        "exit_code": proc.returncode,
        "stdout_bytes": len(proc.stdout),
        "stdout_lines": stdout.count("\n") + (1 if stdout and not stdout.endswith("\n") else 0),
    }
    for key, pattern in TIME_RE.items():
        if key == "real_seconds":
            continue
        found = pattern.search(stderr)
        record[key] = int(found.group(1)) if found else None
    tokens, tokenizer = tokenize(stdout)
    record["stdout_tokens"] = tokens
    record["tokenizer"] = tokenizer
    return record, stdout, stderr


def benchmark(label, kujo, script, cwd, args, warmups, runs_count, extra_env=None):
    for _ in range(warmups):
        measure_once(kujo, script, cwd, args, extra_env)
    records = []
    representative = ("", "")
    for idx in range(runs_count):
        record, stdout, stderr = measure_once(kujo, script, cwd, args, extra_env)
        records.append(record)
        if idx == 0:
            representative = (stdout, stderr)
    metrics = {}
    for key in ("wall_seconds", "user_seconds", "sys_seconds", "cpu_percent", "max_rss_bytes", "block_reads", "block_writes", "stdout_bytes", "stdout_lines"):
        values = [float(r[key]) for r in records if r.get(key) is not None]
        if values:
            metrics[key] = summary(values)
    token_values = [float(r["stdout_tokens"]) for r in records if r.get("stdout_tokens") is not None]
    if token_values:
        metrics["stdout_tokens"] = summary(token_values)
    return {
        "label": label,
        "command_args": args,
        "cwd_fixture": cwd.name,
        "warmups": warmups,
        "runs": records,
        "summary": metrics,
        "representative_stdout": representative[0],
        "representative_stderr": representative[1],
    }


def source_metrics(repo: Path, sha: str):
    files = git(repo, "ls-tree", "-r", "--name-only", sha).splitlines()
    source_files = [f for f in files if f.endswith(".kujo")]
    test_files = [f for f in source_files if f.startswith("tests/")]
    production_files = [f for f in source_files if not f.startswith("tests/")]
    totals = {"source_loc": 0, "test_loc": 0, "blank_loc": 0, "comment_loc": 0, "functions": 0, "branch_tokens": 0, "unwrap_expect": 0, "todo_fixme": 0}
    largest = []
    for name in source_files:
        text = run(["git", "-C", str(repo), "show", f"{sha}:{name}"]).stdout
        lines = text.splitlines()
        code = 0
        for line in lines:
            stripped = line.strip()
            if not stripped:
                totals["blank_loc"] += 1
            elif stripped.startswith("#"):
                totals["comment_loc"] += 1
            else:
                code += 1
        if name in test_files:
            totals["test_loc"] += code
        else:
            totals["source_loc"] += code
        totals["functions"] += len(re.findall(r"\bfunc\s+[A-Za-z_]", text))
        totals["branch_tokens"] += len(re.findall(r"\b(?:if|else if|while|except)\b", text))
        totals["unwrap_expect"] += len(re.findall(r"\b(?:unwrap|expect)\s*\(", text))
        totals["todo_fixme"] += len(re.findall(r"\b(?:TODO|FIXME)\b", text, re.I))
        largest.append({"path": name, "lines": len(lines)})
    return {
        **totals,
        "tracked_files": len(files),
        "kujo_files": len(source_files),
        "production_kujo_files": len(production_files),
        "test_kujo_files": len(test_files),
        "tracked_bytes": sum(int(x.split()[3]) for x in git(repo, "ls-tree", "-r", "-l", sha).splitlines() if len(x.split()) >= 4 and x.split()[3].isdigit()),
        "largest_kujo_files": sorted(largest, key=lambda x: x["lines"], reverse=True)[:5],
    }


def metadata(repo: Path, sha: str):
    tags = git(repo, "tag", "--points-at", sha).splitlines()
    return {
        "sha": sha,
        "timestamp": git(repo, "show", "-s", "--format=%cI", sha),
        "subject": git(repo, "show", "-s", "--format=%s", sha),
        "tags": tags,
    }


def filesystem_description(repo: Path):
    probe = subprocess.run(["diskutil", "info", str(repo)], text=True, capture_output=True)
    if probe.returncode == 0:
        personality = re.search(r"File System Personality:\s*(.+)", probe.stdout)
        solid_state = re.search(r"Solid State:\s*(.+)", probe.stdout)
        if personality:
            suffix = " (SSD)" if solid_state and solid_state.group(1).strip().lower() == "yes" else ""
            return personality.group(1).strip() + suffix
    return "not reliably identified"


def evaluate(version: str, workloads: dict):
    checks = []
    def add(category, name, passed, evidence):
        checks.append({"category": category, "name": name, "passed": bool(passed), "evidence": evidence})
    minimal = workloads["minimal_summary"]["representative_stdout"]
    typical = workloads["typical_summary"]["representative_stdout"]
    stress = workloads["stress_summary"]["representative_stdout"]
    failure = workloads["failure_summary"]["representative_stdout"]
    injection = workloads["injection_markdown"]["representative_stdout"]
    handoff = workloads["agent_handoff"]["representative_stdout"]
    try: minimal_obj = json.loads(minimal)
    except Exception: minimal_obj = {}
    try: typical_obj = json.loads(typical)
    except Exception: typical_obj = {}
    try: stress_obj = json.loads(stress)
    except Exception: stress_obj = {}
    try: failure_obj = json.loads(failure)
    except Exception: failure_obj = {}
    add("correctness", "minimal JSON is valid and identifies PatchBrief", minimal_obj.get("tool") == "patchbrief", {"tool": minimal_obj.get("tool")})
    add("correctness", "typical workload reports all 10 changed files", typical_obj.get("summary", {}).get("files_changed") == 10, {"files_changed": typical_obj.get("summary", {}).get("files_changed")})
    add("failure_behavior", "invalid Git index exits non-zero with actionable JSON", workloads["failure_summary"]["runs"][0]["exit_code"] == 1 and failure_obj.get("error") is True, {"exit_code": workloads["failure_summary"]["runs"][0]["exit_code"], "payload": failure_obj})
    add("failure_behavior", "oversized diff discloses truncation", stress_obj.get("analysis", {}).get("diff_truncated") is True, {"analysis": stress_obj.get("analysis")})
    add("agent_usability", "Markdown cannot inject a second-level heading", "\n## injected" not in injection and "\x1b" not in injection, {"contains_injected_heading": "\n## injected" in injection, "contains_escape": "\x1b" in injection})
    add("agent_usability", "handoff preserves required reviewer sections", all(x in handoff for x in ("## Summary", "## What Changed", "## Risk Assessment", "## Reviewer Notes")), {"stdout_bytes": len(handoff.encode())})
    add("reliability", "all measured normal workload invocations succeeded", all(r["exit_code"] == 0 for key, value in workloads.items() if key != "failure_summary" for r in value["runs"]), {})
    add("determinism", "typical output size is stable across repetitions", len({r["stdout_bytes"] for r in workloads["typical_summary"]["runs"]}) == 1, {"distinct_sizes": sorted({r["stdout_bytes"] for r in workloads["typical_summary"]["runs"]})})
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--kujo", type=Path, default=Path(shutil.which("kujo") or "kujo"))
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument("--scaling-runs", type=int, default=10)
    args = parser.parse_args()
    repo = args.repo.resolve()
    output = (args.output or repo / "docs/evaluations/evidence").resolve()
    output.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix="patchbrief-hardening-"))
    worktrees = temp_root / "worktrees"
    fixtures_root = temp_root / "fixtures"
    try:
        versions = {"baseline": BASELINE_SHA, "current": CURRENT_SHA}
        scripts = {}
        for name, sha in versions.items():
            target = worktrees / name
            run(["git", "worktree", "add", "--detach", str(target), sha], cwd=repo)
            scripts[name] = target / "patchbrief.kujo"
        fixtures = make_fixtures(fixtures_root)
        raw = {}
        for name in ("baseline", "current"):
            script = scripts[name]
            workloads = {}
            definitions = [
                ("minimal_summary", fixtures["minimal"], ["summarize", "--format", "json"], None, args.runs, args.warmups),
                ("typical_summary", fixtures["typical"], ["summarize", "--format", "json"], None, args.runs, args.warmups),
                ("large_summary", fixtures["large"], ["summarize", "--format", "json"], None, args.runs, args.warmups),
                ("stress_summary", fixtures["stress"], ["summarize", "--format", "json"], None, min(args.runs, max(10, args.runs // 2)), 1 if args.warmups else 0),
                ("failure_summary", fixtures["failure"], ["summarize", "--format", "json"], {"GIT_INDEX_FILE": "/dev/null"}, min(args.runs, max(10, args.runs // 2)), args.warmups),
                ("agent_handoff", fixtures["typical"], ["handoff"], None, args.runs, args.warmups),
                ("injection_markdown", fixtures["injection"], ["summarize"], None, min(args.runs, max(10, args.runs // 2)), args.warmups),
            ]
            for label, cwd, command_args, env, measured, warmups in definitions:
                workloads[label] = benchmark(label, args.kujo, script, cwd, command_args, warmups, measured, env)
            scaling = {}
            for count, cwd in fixtures["scaling"].items():
                scaling[count] = benchmark(f"scale_{count}", args.kujo, script, cwd, ["summarize", "--format", "json"], args.warmups, args.scaling_runs)
            checks = evaluate(name, workloads)
            raw[name] = {"workloads": workloads, "scaling": scaling, "eval_checks": checks, "source_metrics": source_metrics(repo, versions[name])}

        environment = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "hostname": platform.node(),
            "os": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "kujo_binary": str(args.kujo.resolve()),
            "kujo_version": run([str(args.kujo), "--version"]).stdout.strip(),
            "git_version": run(["git", "--version"]).stdout.strip(),
            "cpu": run(["sysctl", "-n", "machdep.cpu.brand_string"]).stdout.strip(),
            "logical_cores": int(run(["sysctl", "-n", "hw.ncpu"]).stdout.strip()),
            "ram_bytes": int(run(["sysctl", "-n", "hw.memsize"]).stdout.strip()),
            "filesystem": filesystem_description(repo),
            "warmups": args.warmups,
            "measured_runs": args.runs,
            "scaling_runs": args.scaling_runs,
            "model_provider": None,
            "network_used_by_patchbrief": False,
        }
        payload = {
            "schema_version": "1.0.0",
            "comparison": {"baseline": metadata(repo, BASELINE_SHA), "current": metadata(repo, CURRENT_SHA), "baseline_reason": "Immediate parent of the first contiguous 2026-08-30 hardening commit; selects the last pre-hardening tree without including unrelated v1.0.0-to-August bug fixes."},
            "environment": environment,
            "versions": raw,
        }
        write(output / "raw-measurements.json", json.dumps(payload, indent=2, sort_keys=True) + "\n")
        for name in ("baseline", "current"):
            version_dir = output / name
            version_dir.mkdir(exist_ok=True)
            checks = raw[name]["eval_checks"]
            write(version_dir / "eval-evidence.json", json.dumps({"version": name, "checks": checks, "passed": sum(1 for c in checks if c["passed"]), "failed": sum(1 for c in checks if not c["passed"]), "total": len(checks)}, indent=2) + "\n")
            for label, measurement in raw[name]["workloads"].items():
                write(version_dir / f"{label}.stdout", measurement["representative_stdout"])
                write(version_dir / f"{label}.time-stderr", measurement["representative_stderr"])
        print(output / "raw-measurements.json")
    finally:
        for name in ("baseline", "current"):
            target = worktrees / name
            if target.exists():
                subprocess.run(["git", "worktree", "remove", "--force", str(target)], cwd=repo, capture_output=True)
        shutil.rmtree(temp_root, ignore_errors=True)


if __name__ == "__main__":
    main()
