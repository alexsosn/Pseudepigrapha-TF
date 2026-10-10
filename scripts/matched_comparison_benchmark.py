#!/usr/bin/env python3
"""Matched, sequential, process-isolated /compare benchmark (issue #174).

Run from scripts/ in the candidate checkout with the same installed Python/TF
dependencies for each revision. Workers import package code via an explicit
revision's PYTHONPATH, never via whatever editable checkout is installed.
This is an opt-in experiment, not a CI regression threshold.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import re
import statistics
import subprocess
import sys
from time import perf_counter_ns
from typing import Callable

BASELINE_SHA = "7c4b757bb543a110ae9a252d1281835859136852"
SOURCE_SHA = "c939dcbacad78c5d18d2c4282cad23c47e19ac07"
ABBA_SCHEDULE = ("baseline", "candidate", "candidate", "baseline")
CHILD_PREFIX = "MATCHED_CHILD_JSON="
ROUTES = (
    ("1en", "/compare?work=1En&chapter=1&verse=2", 200),
    ("tjob", "/compare?work=TJob&chapter=1&verse=1", 200),
    ("aristob", "/compare?work=Aristob&chapter=7%3A32&verse=13", 200),
    ("psssol-ambiguous", "/compare?work=PssSol&chapter=1&verse=5", 400),
)


def parse_linux_vmrss_kib(status_text: str) -> int:
    """Read *current* resident memory (KiB) from Linux /proc/self/status."""

    match = re.search(r"^VmRSS:\s*(\d+)\s+kB\s*$", status_text, re.MULTILINE)
    if match is None:
        raise ValueError("VmRSS in KiB is unavailable from Linux /proc/self/status")
    return int(match.group(1))


def _rss_kib() -> int:
    if platform.system() != "Linux":
        raise RuntimeError("isolated RSS experiment currently requires Linux /proc")
    return parse_linux_vmrss_kib(Path("/proc/self/status").read_text())


def _peak_rss_kib() -> int:
    from resource import RUSAGE_SELF, getrusage

    if platform.system() != "Linux":
        raise RuntimeError("ru_maxrss units for this experiment require Linux")
    return int(getrusage(RUSAGE_SELF).ru_maxrss)


def verify_corpus_report(data_dir: Path, source_commit: str) -> None:
    """Fail closed when the TF materialization is not the audited pinned corpus."""

    report_path = Path(data_dir) / "conversion-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("status") != "ok":
        raise ValueError("TF conversion report is not successful")
    if report.get("provenance", {}).get("upstream_commit") != source_commit:
        raise ValueError("TF conversion report source commit is not the requested pin")
    checks = report.get("semantic_checks")
    if not isinstance(checks, dict) or not checks or not all(value is True for value in checks.values()):
        raise ValueError("TF conversion semantic parity checks are missing or failed")
    if report.get("provenance", {}).get("source_identity_status") != "verified":
        raise ValueError("TF source identity is not verified")


def _validate_routes(cases, repeat_count: int) -> tuple[tuple[str, str, int], ...]:
    if isinstance(repeat_count, bool) or not isinstance(repeat_count, int) or repeat_count < 1:
        raise ValueError("repeat_count must be a positive integer")
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("at least one benchmark case is needed")
    result = tuple(cases)
    labels: set[str] = set()
    for case in result:
        if not isinstance(case, tuple) or len(case) != 3:
            raise ValueError("cases must contain (label, path, expected HTTP status)")
        label, path, expected = case
        if not isinstance(label, str) or not label or label in labels:
            raise ValueError("benchmark case labels must be unique and nonempty")
        labels.add(label)
        if not isinstance(path, str) or not path.startswith("/compare?") or "#" in path:
            raise ValueError("benchmark paths must be local /compare query routes")
        if expected not in (200, 400):
            raise ValueError("only expected 200/400 comparison statuses are supported")
    return result


def measure_routes(
    client,
    cases=ROUTES,
    *,
    repeat_count: int = 5,
    clock_ns: Callable[[], int] = perf_counter_ns,
) -> list[dict[str, object]]:
    """Time real body materialization; never write content to result or logs."""

    selected = _validate_routes(cases, repeat_count)

    def get_once(label: str, route: str, expected: int) -> tuple[float, str]:
        before = clock_ns()
        response = client.get(route)
        try:
            body = response.get_data()
            status = response.status_code
        finally:
            response.close()
        elapsed = clock_ns() - before
        if status != expected:
            raise AssertionError(f"{label}: expected HTTP {expected}, got {status}")
        if elapsed < 0:
            raise ValueError("benchmark clock moved backwards")
        if not isinstance(body, bytes):
            raise ValueError("Flask response body is not bytes")
        return round(elapsed / 1_000_000, 3), sha256(body).hexdigest()

    rows: list[dict[str, object]] = []
    for label, route, status in selected:
        first_ms, body_digest = get_once(label, route, status)
        warms: list[float] = []
        for _ in range(repeat_count):
            ms, digest = get_once(label, route, status)
            if digest != body_digest:
                raise AssertionError(f"{label}: HTML digest drift within one worker")
            warms.append(ms)
        rows.append(
            {
                "label": label,
                "route": route,
                "expected_status": status,
                "body_sha256": body_digest,
                "first_ms": first_ms,
                "warm_ms": warms,
                "warm_median_ms": round(statistics.median(warms), 3),
            }
        )
    return rows


def run_child(
    command: list[str],
    *,
    timeout: int = 180,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    runner: Callable = subprocess.run,
) -> dict[str, object]:
    """Run one isolated process; treat failures/missing or bad JSON as blockers."""

    try:
        finished = runner(
            command, capture_output=True, text=True, timeout=timeout,
            env=env, cwd=cwd, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"isolated benchmark child timed out after {timeout}s") from exc
    if finished.returncode != 0:
        # Never forward captured stdout/HTML or corpus text into public logs.
        raise RuntimeError(f"isolated benchmark child exited {finished.returncode}")
    records = [
        line.removeprefix(CHILD_PREFIX)
        for line in finished.stdout.splitlines()
        if line.startswith(CHILD_PREFIX)
    ]
    if len(records) != 1:
        raise ValueError("expected exactly one MATCHED_CHILD_JSON result from worker")
    value = json.loads(records[0])
    if not isinstance(value, dict):
        raise ValueError("MATCHED_CHILD_JSON must be an object")
    return value


def _check_metrics(report: dict[str, object]) -> None:
    memory = report.get("memory")
    if not isinstance(memory, dict) or memory.get("unit") != "KiB":
        raise ValueError("incomparable RSS units; only Linux KiB supported")
    for key in ("rss_before_app_kib", "rss_after_app_kib", "rss_after_requests_kib", "peak_rss_kib"):
        value = memory.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"missing or invalid RSS metric: {key}")
    # VmRSS is a separately sampled /proc estimate, while ru_maxrss is a
    # kernel high-water counter. Linux does not promise synchronous, identical
    # accounting between these two interfaces. Preserve their raw values and
    # units; do not reject valid measurements merely because VmRSS briefly
    # exceeds the separately reported high-water value.
    cases = report.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("missing comparison cases")
    for item in cases:
        if not isinstance(item, dict) or item.get("expected_status") not in (200, 400):
            raise ValueError("invalid HTTP case or expected status")
        ms = item.get("warm_ms")
        if not isinstance(ms, list) or not ms or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not 0 <= x < float("inf")
            for x in ms
        ):
            raise ValueError("invalid warm request samples")
        if item.get("warm_median_ms") != round(statistics.median(ms), 3):
            raise ValueError("inconsistent warm median")
        if not isinstance(item.get("body_sha256"), str):
            raise ValueError("missing HTML hash")


def validate_pair(
    baseline: dict[str, object],
    candidate: dict[str, object],
    *,
    baseline_sha: str,
    candidate_sha: str,
    source_commit: str,
) -> dict[str, dict[str, float]]:
    """Reject code/environment/corpus and response drift before computing ratios."""

    for report, variant, expected_sha in (
        (baseline, "baseline", baseline_sha),
        (candidate, "candidate", candidate_sha),
    ):
        if report.get("variant") != variant or report.get("commit") != expected_sha:
            raise ValueError(f"{variant} does not identify the pinned requested revision")
        if report.get("source_commit") != source_commit or report.get("tf_data_version") != "1.0":
            raise ValueError("unmatched dataset source commit or TF data version")
        _check_metrics(report)
    for field in ("python", "text_fabric", "platform"):
        if baseline.get(field) != candidate.get(field):
            raise ValueError(f"unmatched process environment: {field}")

    original = {str(row["label"]): row for row in baseline["cases"]}
    revised = {str(row["label"]): row for row in candidate["cases"]}
    if not original or original.keys() != revised.keys() or len(original) != len(baseline["cases"]) or len(revised) != len(candidate["cases"]):
        raise ValueError("unmatched or duplicate route case labels")
    comparison: dict[str, dict[str, float]] = {}
    for label, left in original.items():
        right = revised[label]
        for field in ("route", "expected_status", "body_sha256"):
            if left.get(field) != right.get(field):
                raise ValueError(f"{label}: unmatched HTTP response semantics ({field})")
        if len(left["warm_ms"]) != len(right["warm_ms"]):
            raise ValueError("unmatched request repetition counts")
        comparison[label] = {
            "baseline_warm_median_ms": left["warm_median_ms"],
            "candidate_warm_median_ms": right["warm_median_ms"],
        }
    return comparison


def _commit_sha(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, timeout=30,
    ).strip()


def _child_report(args) -> dict[str, object]:
    root = Path(args.root).resolve()
    current_sha = _commit_sha(root)
    if current_sha != args.commit:
        raise ValueError("worker git revision does not match requested commit")
    verify_corpus_report(Path(args.tf_dir), args.source_commit)

    import pseudepigrapha_tf
    from importlib.metadata import version
    from pseudepigrapha_tf.web import load_local_comparison_web_app

    module_path = Path(pseudepigrapha_tf.__file__).resolve()
    expected_package = (root / "src" / "pseudepigrapha_tf").resolve()
    if not module_path.is_relative_to(expected_package):
        raise ValueError("worker imported wrong package code checkout")

    rss_before = _rss_kib()
    started = perf_counter_ns()
    app = load_local_comparison_web_app(
        Path(args.tf_dir).resolve(), Path(args.app_dir).resolve(),
        version="1.0", silent="deep",
    )
    setup_s = round((perf_counter_ns() - started) / 1_000_000_000, 3)
    rss_after_app = _rss_kib()
    client = app.test_client()
    cases = measure_routes(client, repeat_count=args.repeat_count)
    rss_after_requests = _rss_kib()

    return {
        "variant": args.variant,
        "commit": current_sha,
        "source_commit": args.source_commit,
        "tf_data_version": "1.0",
        "python": platform.python_version(),
        "text_fabric": version("text-fabric"),
        "platform": platform.platform(),
        "app_setup_s": setup_s,
        "memory": {
            "unit": "KiB",
            "rss_before_app_kib": rss_before,
            "rss_after_app_kib": rss_after_app,
            "rss_after_requests_kib": rss_after_requests,
            "peak_rss_kib": _peak_rss_kib(),
        },
        "cases": cases,
    }


def _summary(rounds: list[dict[str, object]]) -> dict[str, object]:
    baseline = [item for item in rounds if item["variant"] == "baseline"]
    candidate = [item for item in rounds if item["variant"] == "candidate"]
    result: dict[str, object] = {}
    for label in (row["label"] for row in baseline[0]["cases"]):
        baseline_rows = [next(c for c in item["cases"] if c["label"] == label) for item in baseline]
        candidate_rows = [next(c for c in item["cases"] if c["label"] == label) for item in candidate]
        base = [x["warm_median_ms"] for x in baseline_rows]
        newer = [x["warm_median_ms"] for x in candidate_rows]
        median_base = round(statistics.median(base), 3)
        median_newer = round(statistics.median(newer), 3)
        result[label] = {
            "baseline_warm_medians_ms": base,
            "candidate_warm_medians_ms": newer,
            "baseline_median_ms": median_base,
            "candidate_median_ms": median_newer,
            "observed_baseline_to_candidate_ratio_not_speedup_claim": (
                round(median_base / median_newer, 3) if median_newer > 0 else None
            ),
        }
    result["app_setup_seconds"] = {
        variant: [item["app_setup_s"] for item in rounds if item["variant"] == variant]
        for variant in ("baseline", "candidate")
    }
    result["rss_after_requests_kib"] = {
        variant: [item["memory"]["rss_after_requests_kib"] for item in rounds if item["variant"] == variant]
        for variant in ("baseline", "candidate")
    }
    result["peak_rss_kib"] = {
        variant: [item["memory"]["peak_rss_kib"] for item in rounds if item["variant"] == variant]
        for variant in ("baseline", "candidate")
    }
    return result


def _parent_report(args) -> dict[str, object]:
    baseline_root = Path(args.baseline_root).resolve()
    candidate_root = Path(args.candidate_root).resolve()
    data_dir = Path(args.tf_dir).resolve()
    app_dir = Path(args.app_dir).resolve()
    if not app_dir.is_dir():
        raise ValueError("benchmark app directory not found")
    if baseline_root == candidate_root:
        raise ValueError("comparison revisions must be separate checkouts")
    baseline_sha = _commit_sha(baseline_root)
    candidate_sha = _commit_sha(candidate_root)
    candidate_head_sha = args.candidate_head_sha or candidate_sha
    if re.fullmatch(r"[0-9a-f]{40}", candidate_head_sha) is None:
        raise ValueError("candidate head SHA must be an exact commit identifier")
    if baseline_sha != BASELINE_SHA:
        raise ValueError("baseline checkout must be the verified pre-cache v1.0.0 commit")
    verify_corpus_report(data_dir, args.source_commit)
    script = Path(__file__).resolve()
    rounds: list[dict[str, object]] = []
    for variant in ABBA_SCHEDULE:
        root = baseline_root if variant == "baseline" else candidate_root
        commit = baseline_sha if variant == "baseline" else candidate_sha
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(root / "src")
        command = [
            sys.executable, str(script), "--child",
            "--root", str(root),
            "--tf-dir", str(data_dir),
            "--app-dir", str(app_dir),
            "--variant", variant,
            "--commit", commit,
            "--source-commit", args.source_commit,
            "--repeat-count", str(args.repeat_count),
        ]
        record = run_child(
            command, timeout=args.timeout_seconds, env=environment,
            cwd=candidate_root,
        )
        rounds.append(record)

    baselines = [row for row in rounds if row.get("variant") == "baseline"]
    candidates = [row for row in rounds if row.get("variant") == "candidate"]
    if len(baselines) != 2 or len(candidates) != 2:
        raise ValueError("ABBA schedule did not produce exactly two results per version")
    for older in baselines:
        for newer in candidates:
            validate_pair(
                older, newer, baseline_sha=baseline_sha, candidate_sha=candidate_sha,
                source_commit=args.source_commit,
            )
    for version_rows in (baselines, candidates):
        left, right = version_rows
        if {r["label"]: r["body_sha256"] for r in left["cases"]} != {
            r["label"]: r["body_sha256"] for r in right["cases"]
        }:
            raise ValueError("same-revision HTML digest drift across fresh processes")
    return {
        "schema_version": 1,
        "experiment": "ABBA isolated sequential Flask test_client comparisons",
        "source_commit": args.source_commit,
        "baseline_commit": baseline_sha,
        "candidate_commit": candidate_sha,
        "candidate_head_sha": candidate_head_sha,
        "repetitions_per_case": args.repeat_count,
        "limitations": (
            "same runner, sequential fresh Python subprocesses and compiled TF cache; "
            "in-process Flask test_client, no network/browser, no randomization; "
            "RSS VmRSS is current process resident memory in KiB, not app allocation; "
            "two process replicates each, no causal speedup guarantee"
        ),
        "rounds": rounds,
        "summary": _summary(rounds),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--child", action="store_true")
    parser.add_argument("--root")
    parser.add_argument("--baseline-root")
    parser.add_argument("--candidate-root")
    parser.add_argument("--candidate-head-sha")
    parser.add_argument("--tf-dir", required=True)
    parser.add_argument("--app-dir", required=True)
    parser.add_argument("--variant", choices=("baseline", "candidate"))
    parser.add_argument("--commit")
    parser.add_argument("--source-commit", default=SOURCE_SHA)
    parser.add_argument("--repeat-count", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=int, default=180)
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.child:
        if not args.root or not args.variant or not args.commit:
            parser.error("child requires --root, --variant and --commit")
        report = _child_report(args)
        print(CHILD_PREFIX + json.dumps(report, sort_keys=True), flush=True)
    else:
        if not args.baseline_root or not args.candidate_root or not args.output:
            parser.error("parent requires --baseline-root, --candidate-root and --output")
        if args.repeat_count < 1 or args.timeout_seconds < 1:
            parser.error("repeat count and timeout must be positive")
        report = _parent_report(args)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        # Print only aggregate metrics, never rendered HTML or corpus text.
        print("MATCHED_COMPARISON_SUMMARY_JSON=" + json.dumps({
            "baseline_commit": report["baseline_commit"],
            "candidate_commit": report["candidate_commit"],
            "candidate_head_sha": report["candidate_head_sha"],
            "source_commit": report["source_commit"],
            "summary": report["summary"],
        }, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
