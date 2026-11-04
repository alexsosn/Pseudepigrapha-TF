# #224 — current-release TF data version in comparison benchmark reproduction

## Evidence from existing repository and full-corpus workflow

- Verified baseline main: `252e0cc4cbf85d4c01ef37489b49daf28b6bc1fe`. Its post-merge main test workflow #41838994358 completed successfully.
- `src/pseudepigrapha_tf/release_identity.py`: `TF_DATA_VERSION = "1.1"`.
- `.github/workflows/test.yml` builds `/tmp/pseudepigrapha-tf/1.1` and invokes `tests/pinned_comparison_acceptance.py` against it.
- `tests/pinned_comparison_acceptance.py::verify()` calls `load_local_comparison_web_app(tf_dir, Path("app"), version=TF_DATA_VERSION)`; this is specifically a versioned advanced-browser load.
- `docs/comparison-performance-benchmark.md` still uses `/tmp/pseudepigrapha-tf/1.0` both in `convert --output` and in the manual acceptance invocation, despite the page claiming to reproduce the *current* pinned benchmark. This drift is untested.
- Preserve historic v1.0 measurement attribution in README and other docs: only the `Reproduce` block's **current** workflow is defective.

## Frozen research → plan → TDD → verification → independent review

1. Commit this file *before* new tests and production/docs changes.
2. Add tests-only contract in `tests/test_comparison_benchmark_docs.py`: parse the bash block after `## Reproduce`, require it to derive a variable `DATA_VERSION` from installed package `pseudepigrapha_tf.release_identity.TF_DATA_VERSION` after editable installation, use that variable in both converter `--output` and acceptance script arguments, forbid a literal historical `/1.0` in the executable block, and `bash -n` the actual block. Keep pinned upstream SHA in sync with test workflow. Observe actual RED on prior docs.
3. Minimal change: add one safe command substitution and quote the same dynamic path in both uses. No source/converter/runtime changes; no new service or benchmark results.
4. Full exact-final-head pytest plus pinned OCP convert/report/TF stock reload/browser acceptance.
5. Independent skeptical diff/code/doc review, filed on GitHub; if no blockers after full CI, squash merge with SHA lease and verify main CI.

## Boundaries

Current release version only, reproducibility not new measurements. Historic figures explicitly remain attributed to their measured release. CI itself remains authoritative for pinned OCP source; the guide is a standalone reproducibility recipe.
