"""Opt-in, in-process comparison HTTP measurements (not a speedup claim).

The routine deliberately does not start a server or load a corpus. Callers must
pass an already initialized Flask test client and report app setup separately.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
import math
from platform import platform, python_version, system
from statistics import median
from time import perf_counter_ns
from typing import Callable, Iterable

from .release_identity import TF_DATA_VERSION


def _peak_rss() -> dict[str, int | str | None]:
    """Return process high-water RSS with its platform-dependent raw units."""

    if system() not in {"Linux", "Darwin"}:
        return {"value": None, "unit": None, "meaning": "not collected on this platform"}
    try:
        from resource import RUSAGE_SELF, getrusage

        maximum = getrusage(RUSAGE_SELF).ru_maxrss
    except (ImportError, OSError):
        return {"value": None, "unit": None, "meaning": "resource metrics unavailable"}
    return {
        "value": int(maximum),
        "unit": "KiB" if system() == "Linux" else "bytes",
        "meaning": "process lifetime high-water RSS, not per-request allocation",
    }


def benchmark_comparison_client(
    client,
    cases: Iterable[tuple[str, str, int]],
    *,
    repetitions: int = 5,
    clock_ns: Callable[[], int] = perf_counter_ns,
    setup_seconds: float,
    source_commit: str,
) -> dict[str, object]:
    """Measure first-in-app and N repeated requests for each provided route.

    This is an in-process Flask test-client measurement. First-in-app is not a
    fresh-process cold start, and earlier cases can populate shared caches.
    """

    if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < 1:
        raise ValueError("benchmark repetitions must be a positive integer")
    if not isinstance(setup_seconds, (int, float)) or not math.isfinite(setup_seconds) or setup_seconds < 0:
        raise ValueError("benchmark setup_seconds must be finite and nonnegative")
    if not isinstance(source_commit, str) or not source_commit.strip():
        raise ValueError("benchmark source_commit must be nonempty")

    selected = tuple(cases)
    if not selected:
        raise ValueError("at least one comparison benchmark case is required")
    seen: set[str] = set()
    for item in selected:
        if not isinstance(item, tuple) or len(item) != 3:
            raise ValueError("benchmark cases must be (label, URL, expected_status) triples")
        label, url, status = item
        if not isinstance(label, str) or not label.strip() or label in seen:
            raise ValueError("benchmark labels must be unique, nonempty strings")
        seen.add(label)
        if not isinstance(url, str) or not url.startswith("/compare?"):
            raise ValueError("benchmark URLs must be in-process /compare query paths")
        if status not in (200, 400):
            raise ValueError("benchmark supports only expected HTTP 200 or 400")

    def request_ms(label: str, url: str, expected: int) -> float:
        start = clock_ns()
        response = client.get(url)
        try:
            # Force body generation/decoding inside the timed scope. The text
            # itself is never copied into the benchmark record.
            response.get_data()
            status = response.status_code
        finally:
            response.close()
        elapsed_ns = clock_ns() - start
        if status != expected:
            raise AssertionError(
                f"{label}: expected HTTP {expected}, got {status}"
            )
        if elapsed_ns < 0:
            raise ValueError("benchmark clock moved backwards")
        return round(elapsed_ns / 1_000_000, 3)

    result_cases: list[dict[str, object]] = []
    for label, url, expected in selected:
        first = request_ms(label, url, expected)
        warms = [request_ms(label, url, expected) for _ in range(repetitions)]
        result_cases.append(
            {
                "label": label,
                "route": url,
                "expected_status": expected,
                "first_request_ms": first,
                "warm_request_ms": warms,
                "warm_median_ms": round(median(warms), 3),
                "warm_min_ms": min(warms),
                "warm_max_ms": max(warms),
            }
        )

    try:
        tf_version = version("text-fabric")
    except PackageNotFoundError:
        tf_version = "unavailable"

    return {
        "source_commit": source_commit,
        "tf_data_version": TF_DATA_VERSION,
        "setup_seconds": round(float(setup_seconds), 3),
        "setup_scope": "web app setup after an earlier in-process TF API load",
        "scope": "in-process Flask test_client, includes HTML response generation",
        "first_request_scope": "first request for this work in one app, not a fresh process",
        "repetitions_per_case": repetitions,
        "environment": {
            "python": python_version(),
            "platform": platform(),
            "text_fabric": tf_version,
            "peak_rss": _peak_rss(),
        },
        "cases": result_cases,
    }
