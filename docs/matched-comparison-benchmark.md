# Matched pre-cache / cached comparison experiment

This opt-in experiment addresses [issue #174](https://github.com/alexsosn/Pseudepigrapha-TF/issues/174), which asks whether the three 2026 caching changes really improve repeated `/compare` rendering on the **same serialized Text-Fabric corpus**. It is distinct from the first-in-app single-revision benchmark in [comparison-performance-benchmark.md](comparison-performance-benchmark.md).

## Exact revisions and source

- Baseline `v1.0.0`: Git SHA `7c4b757bb543a110ae9a252d1281835859136852`, **before** PRs #166, #168 and #170.
- Candidate: recorded exact checked-out SHA of current code, including cache changes.
- Both variants use the same converted TF `1.0` directory from pinned OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`. The runner refuses missing/mismatched conversion provenance or failed independent semantic checks.
- Each worker is a **separate sequential Python process** with `PYTHONPATH` bound to its own checkout. No worker loads a second TF API; the same Python executable, installed Text-Fabric dependencies, filesystem and benchmark script are used for both.

## One-off CI invocation

The existing `.github/workflows/test.yml` already converts and audits the whole OCP corpus. A final experiment step executes **only for a pull request whose head branch is `perf/174-matched-comparison`**, reusing the same serialized TF directory after the existing acceptance tests. It checks out the pinned old code with `git worktree`, runs ABBA (baseline–candidate–candidate–baseline) sequentially, and uploads the complete JSON measurements as the `matched-comparison` artifact. No extra automatic conversion or benchmark job is added to unrelated PRs or `main`.

## Manual reproduction

On Linux, with compatible Python 3.10+, `text-fabric[github]>=13.1,<14`, this repository and the pinned OCP source:

```bash
git clone https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha.git /tmp/ocp
git -C /tmp/ocp checkout c939dcbacad78c5d18d2c4282cad23c47e19ac07
python -m pip install -e '.[dev]'
pseudepigrapha-tf convert /tmp/ocp/static/docs \
  --output /tmp/pseudepigrapha-tf/1.0 \
  --upstream-commit c939dcbacad78c5d18d2c4282cad23c47e19ac07
git fetch origin 7c4b757bb543a110ae9a252d1281835859136852
git worktree add --detach /tmp/pseudepigrapha-tf-pre-cache 7c4b757bb543a110ae9a252d1281835859136852
python scripts/matched_comparison_benchmark.py \
  --baseline-root /tmp/pseudepigrapha-tf-pre-cache \
  --candidate-root "$PWD" \
  --tf-dir /tmp/pseudepigrapha-tf/1.0 \
  --repeat-count 5 \
  --output /tmp/pseudepigrapha-tf-matched-comparison.json
```

This one-off command is not part of default `pytest`, researcher corpus installation, or any scheduled build.

## What the JSON proves and does not prove

Four independent subprocesses run in ABBA order. Each loads **one** browser-mode Text-Fabric app and issues the same four routes: `1En 1:2`, `TJob 1:1`, `Aristob 7:32:13`, and the deliberately ambiguous `PssSol 1:5` expecting HTTP 400. Every response body is consumed and closed inside the timing interval. SHA-256 digests of HTML must be identical within and across both revisions; any unexpected HTTP status, HTML mismatch, source-commit mismatch, Text-Fabric version drift or subprocess failure **fails the experiment** rather than yielding a misleading improvement.

Each child reports app-initialization seconds, one first request plus all repeated-request milliseconds, Linux `VmRSS` before app, after app and after requests, and peak process RSS in **KiB** (`ru_maxrss`). These are **separate fresh-process states**, not the 2.30 GiB process lifetime high water of issue #172's integrated acceptance. They do **not** isolate the memory allocated strictly by caches: Text-Fabric base loading accounts for most memory.

Results include per-work medians of the two process-level warm medians and an **observed baseline/candidate ratio**, not a guaranteed or causal speedup. The four process order reduces some order effects but does not randomize workloads, eliminate OS page-cache effects, control runner hardware noise, or measure a network service/browser. Five repetitions per process and two independent processes per variant are exploratory, not precise confidence intervals. The expected-400 error-path timings must never be interpreted as equivalent to successful-rendering throughput.

See [the frozen research plan](../research/issue-174/RESEARCH_PLAN.md) and the exact-head CI artifact for raw data, source identity and test results.
