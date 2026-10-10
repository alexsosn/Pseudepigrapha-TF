# Issue #172 — frozen research and plan

Status: Plan frozen before RED tests / implementation.
Scope: opt-in, measured HTTP test-client performance on the **real pinned Text-Fabric corpus**. No converter, TF serialization, or researcher UI semantics change.

## Research evidence

- #164, #167, #169 merged instance-local `Apparatus`, app-lifetime `PassageNavigator`, and app-lifetime `Translations` caching, respectively. The current CI verifies behavior and cache reuse, but no end-to-end timings are recorded.
- The existing `tests/pinned_comparison_acceptance.py` already loads the **complete pinned corpus** through `Fabric`, creates the supported `load_local_comparison_web_app()`, and runs representative real HTTP requests, including successful 1 Enoch and TJob comparisons and deliberately invalid PssSol witness ambiguity.
- `.github/workflows/test.yml` already runs this acceptance at the end of the pinned integration gate. Instrument that **same** long-lived app so there is no second full-corpus load, and keep measurement out of ordinary unit tests.
- Source identity: OCP commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`; TF data version `1.0`; Text-Fabric package version should be recorded at runtime.
- Flask `test_client()` measures in-process request building and HTML response serialization, **not network round-trip time, browser rendering or interactive user latency**.

## Plan / immutable acceptance criteria

1. RED-first focused tests require an opt-in benchmark routine `benchmark_comparison_client(client, cases, *, repetitions, clock_ns, setup_seconds, source_commit)`. Tests use a deterministic injected nanosecond clock and fake client; fail until the implementation is written.
2. Benchmark must validate input, make one first-in-app request and N repeated warm requests per case, consume/close each response within the timed interval, validate exact HTTP status for both success (200) and intentional 400, and raise on unexpected status.
3. Output a JSON-serializable record with setup time measured **separately**, individual first/warm timings (ms), warm median/min/max, scoped case labels, source commit, TF version/environment metadata, platform and optional peak RSS with precise OS units. No corpus text or HTML body in JSON.
4. Wire into existing `tests/pinned_comparison_acceptance.py` immediately after creation of the real Flask app, before other comparison requests warm caches; benchmark known 1En/TJob/Aristob and fail-closed PssSol requests. Reuse the real app, no additional TF loads. Print machine-readable `COMPARISON_BENCHMARK_JSON=<json>` and write to CI temp dir.
5. Record candid caveats: first request to each work after other measured works is **not a fresh-process cold start**; setup occurs after an existing in-process TF load; process peak RSS is a high-water figure, not per-request allocation; GitHub runners and caches vary. Do not create a CI latency threshold and **do not claim a speedup ratio** without a version-matched baseline benchmark.
6. Verify focused tests then full CI including pinned complete corpus/translation/apparatus acceptance, freeze exact PR head, conduct logically independent adversarial code/data review, then merge only if both gates are green.

## TDD / review checkpoints

- RED test-only commit and observed focused CI failure.
- GREEN implementation in separate commit(s).
- Real pinned JSON measurement from exact-head CI.
- Independent skeptical review with particular attention to unexpected HTTP status, cache contamination by test order, instrumentation overhead, apparent cold/warm labels, OS-specific RSS interpretation, and whether benchmark makes unsupported conclusions.
