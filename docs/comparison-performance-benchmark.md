# Comparison HTTP benchmark (pinned corpus)

This is an **opt-in diagnostic**, not a latency requirement or a claimed speedup. It executes real `/compare` routes through Flask's **in-process test client** against the release-pinned complete Text-Fabric corpus. It does not measure internet latency, browser rendering, server deployment overhead or user-perceived page paint.

## Reproduce

The repository's `test` workflow already performs the complete OCP conversion and semantic acceptance. On each pinned integration run, the `Verify 1 Enoch comparison workflow` step prints a single `COMPARISON_BENCHMARK_JSON=` line and writes `/tmp/pseudepigrapha-tf-comparison-benchmark.json` in that CI runner. The JSON is a machine-readable report, not an uploaded public artifact.

From a repository checkout with the project's development dependencies installed, reproduce the same source and benchmark locally:

```bash
git clone https://github.com/OnlineCriticalPseudepigrapha/Online-Critical-Pseudepigrapha.git /tmp/ocp
git -C /tmp/ocp checkout c939dcbacad78c5d18d2c4282cad23c47e19ac07
python -m pip install -e '.[dev]'
pseudepigrapha-tf convert /tmp/ocp/static/docs \
  --output /tmp/pseudepigrapha-tf/1.0 \
  --upstream-commit c939dcbacad78c5d18d2c4282cad23c47e19ac07
python tests/pinned_comparison_acceptance.py /tmp/pseudepigrapha-tf/1.0
```

This command also runs the scholarly acceptance checks; it should fail rather than record an apparently successful benchmark if semantics or status codes regress.

## Cases and fields

The test first loads the complete TF API, then times setup of the supported browser-mode Flask app. **That setup is after an in-process TF load, not fresh-process installation, conversion, compilation or network acquisition.** Each case makes one first-in-app request and five repeated requests:

| Work | Route | Expected status | Purpose |
|---|---|---:|---|
| 1 Enoch | `/compare?work=1En&chapter=1&verse=2` | 200 | multilingual apparatus/translations |
| Testament of Job | `/compare?work=TJob&chapter=1&verse=1` | 200 | large witnesses, metadata-only sibling |
| Aristobulus | `/compare?work=Aristob&chapter=7%3A32&verse=13` | 200 | deep sections and absent parallel version |
| Psalms of Solomon | `/compare?work=PssSol&chapter=1&verse=5` | 400 | expected fail-closed manuscript ambiguity |

The JSON includes `setup_seconds` separately; for every case, `first_request_ms`, the individual `warm_request_ms` values and `warm_median_ms`/`warm_min_ms`/`warm_max_ms`. It also contains Python/platform/Text-Fabric package version, source commit, TF data version, and optional process peak RSS. Linux `ru_maxrss` is in KiB; macOS uses bytes; the value is **process lifetime high-water RSS**, not incremental per-request usage. The benchmark never records rendered HTML or source text.

## Interpretation and limits

- A first request to *one work* can benefit from caches built for *earlier works*. Do not call these values fresh-process cold starts. The first-request/warm contrast reflects one Flask app's request order only.
- The benchmark uses actual corpus data and includes HTML response generation; test-client calls bypass a real HTTP server/network and browser. The harness and full CI acceptance may warm OS disk caches as well.
- GitHub-hosted runner hardware and scheduling are noisy. Timings are observations, never a CI pass/fail threshold. Compare only equivalent pinned corpus, route selection, Text-Fabric version, runtime and machine/environment.
- A claimed speedup over another revision requires executing **the same benchmark** on both revisions under matched conditions, reporting samples and uncertainty. Merely observing one warm request faster than the first does not establish a code-change speedup.

Architectural background: [ADR-0002](architecture/ADR-0002-tff-source-format-boundary.md) covers the authoritative pinned source; [research plan #172](../research/issue-172/RESEARCH_PLAN.md) describes the frozen RED → GREEN → review gates.
