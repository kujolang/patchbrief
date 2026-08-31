#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
kujo_bin="${KUJO_BIN:-$(command -v kujo || true)}"
eval_dir="${KUJO_EVAL_DIR:-${repo_dir}/../eval}"
if [[ -z "${kujo_bin}" || ! -x "${kujo_bin}" ]]; then
  printf '%s\n' "Set KUJO_BIN to an executable Kujo 1.1.0 runtime." >&2
  exit 2
fi
if [[ ! -f "${eval_dir}/main.kujo" || ! -d "${eval_dir}/src" ]]; then
  printf '%s\n' "Set KUJO_EVAL_DIR to a Kujo Eval checkout." >&2
  exit 2
fi
eval_run_dir="$(mktemp -d "${TMPDIR:-/tmp}/patchbrief-eval.XXXXXX")"
trap 'rm -rf "${eval_run_dir}"' EXIT

python3 "${repo_dir}/benchmarks/hardening/run_benchmarks.py" --repo "${repo_dir}" --kujo "${kujo_bin}" "$@"

cp "${eval_dir}/main.kujo" "${eval_run_dir}/main.kujo"
cp -R "${eval_dir}/src" "${eval_run_dir}/src"
mkdir -p "${eval_run_dir}/evidence"
cp "${repo_dir}/docs/evaluations/evidence/baseline/eval-evidence.json" "${eval_run_dir}/evidence/baseline.json"
cp "${repo_dir}/docs/evaluations/evidence/current/eval-evidence.json" "${eval_run_dir}/evidence/current.json"

for version in baseline current; do
  output_dir="${repo_dir}/docs/evaluations/evidence/eval-${version}"
  if ! (
    cd "${eval_run_dir}"
    "${kujo_bin}" run main.kujo run "${repo_dir}/eval/hardening-${version}.json" --output-dir "${output_dir}" --json
  ); then
    if [[ "${version}" == "current" ]]; then
      printf '%s\n' "Current Kujo Eval failed" >&2
      exit 1
    fi
  fi
done

python3 "${repo_dir}/benchmarks/hardening/build_results.py"

printf '%s\n' "Evidence written to ${repo_dir}/docs/evaluations/evidence"
