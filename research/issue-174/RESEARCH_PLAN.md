# Issue #174: Frozen research and experiment plan

Status: frozen before RED-first tests or implementation. Research evidence collected 2026-10-10.

## Versions, identity and risk

- Baseline is git tag `v1.0.0`, verified GitHub git ref -> `7c4b757bb543a110ae9a252d1281835859136852`, before performance PRs #166, #168, #170.
- Candidate is actual PR branch/head built from `main` after #173 (`674d176068739ea1e607b012185d00fffb54d57e`); print both its working-tree commit and exact PR head SHA, rather than pretending GitHub's synthetic test merge commit is the branch head.
- Serialized Text-Fabric data is **the same directory** produced by the full pinned CI conversion at `/tmp/pseudepigrapha-tf/1.0`, with OCP source commit `c939dcbacad78c5d18d2c4282cad23c47e19ac07`. Fail if `conversion-report.json` lacks matching provenance or successful semantic audit.
- `src/pseudepigrapha_tf/web.py` at both revisions has the same `load_local_comparison_web_app(data_path, app_path, version='1.0', silent='deep')` function. Both revisions must import from the requested checkout, not accidentally use the installed candidate wheel.
- Reference baseline `docs/runtime-footprint.md` measured warm-server RSS in a fresh subprocess; issue #172's 2.30 GiB lifetime high-water came after two app/API loads in one process. Neither is a valid isolated-versus-isolated comparison.

## Chosen architecture

- Add a **standalone stdlib-only opt-in script** `scripts/matched_comparison_benchmark.py`. Parent is invoked with explicit `--baseline-root`, `--candidate-root`, `--tf-dir`, `--app-dir` and `--output`; a child mode runs in a fresh Python interpreter with `PYTHONPATH=<selected checkout>/src` and verifies actual imported module path and source provenance.
- Each child loads exactly one browser TF app, then uses Flask's in-process test client on 1En 1:2, TJob 1:1, Aristob 7:32:13 and PssSol 1:5 (expected HTTP 400). One first request and N repeated requests per case. Consume/close bodies inside timed interval. Hash the first and every repeated HTML body; parent rejects HTML digest mismatch within each child and between versions. Only SHA-256 and statuses are emitted, not corpus text.
- Child samples current resident RSS via Linux `/proc/self/status VmRSS` **after app initialization** and after all requests, plus process-maximum RSS via `resource.ru_maxrss` (KiB). Measure app-init wall-time separately. Do not report these as incremental per-request allocation or full fresh OS installation time.
- Use ABBA run order (baseline, candidate, candidate, baseline); each measurement in a separate child, never concurrently. Compare medians/spreads across paired samples; keep all raw per-request times. No hard-coded speedup threshold; performance assertions require no semantic drift and matching environments.
- Validate commit, TF version, source identity and result schema in the parent **before** comparing. Parent subprocess timeouts and nonzero exits must fail clearly. Never reinterpret failed/HTTP 500 as a successful faster result.
- GitHub Actions integration is **opt-in only for issue #174 PR branch**, reusing the already built/validated pinned TF corpus in `pinned-upstream-integration` after its semantic acceptance step. No second clone/conversion. Do not run on ordinary main push or unrelated PRs. After merge provide manual CLI reproducibility; no regular CI performance thresholds.

## RED → GREEN → independent review gates

1. Commit this plan and unit tests **alone**. RED must demonstrate missing runner functions, including fail-closed version/HTML/status, setup vs request timing, parent subprocess failure/timeout, and Linux RSS units.
2. Implement worker and orchestrator as separate change. Keep existing `src/` corpus APIs and TF graph unchanged. Focused test GREEN then full PR `unit-and-tf` and pinned integration green.
3. Capture real four-child GitHub CI JSON with per-work times, response digests and isolated memory metrics. Avoid unsupported causal claims: runner scheduling/OS page cache can drift; isolated TF app does not equal network/browser production.
4. Freeze exact tested PR head, perform logically independent adversarial review against actual code and data. If data mismatch or unverifiable provenance, request changes, never merge by force. Merge only when both CI gates pass and review has no blockers.
