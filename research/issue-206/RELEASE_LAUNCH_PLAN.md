# Issue #206: guarded one-shot v1.1.0 tag creation and publication handoff

Frozen research/plan, committed before RED tests or automation implementation.

## Actual blocker / research

The repository's main commit `cbf190a62af798586938221f3a58dd2614e5fa04` has successful push CI workflow run `38165048540`. The `v1.1.0` Git ref and public release both return 404. The existing protected `.github/workflows/publish-corpus-release.yml` has a strict `workflow_dispatch` API requiring `release_tag` and `release_commit`, a preflight binding the dispatched workflow SHA to `release_commit`, and a reusable corpus builder + no-clobber draft publisher + live verification. Existing connected GitHub operations cannot create a tag or dispatch a workflow. Adding another release format or manually forging a complete.zip is explicitly rejected.

A one-shot **GitHub Actions** launcher triggered by a successful *push to main* test workflow can use repository-scoped credentials to create the lightweight immutable release tag and dispatch the existing publisher. This solves both missing write capabilities through the repository's own audited release infrastructure; it does not replace the publisher or relax its checks.

## Threat model and gate decisions

- Only `workflow_run` on an already successful `test` **push to this repository's `main` branch**, not PR tests, forks, manual arbitrary inputs, or scheduled runs. The trigger workflow must be on default branch to run.
- Pin candidate `TARGET_COMMIT` to the triggering test run's `head_sha`, check `HEAD` of `main` still matches it before tagging (reject stale successful checks), and require checkout precisely that SHA (no reliance on mutable branch references).
- Derive/check exact expected `v1.1.0` from `pyproject.toml` package version and `1.1` from `app/config.yaml`; the current publisher is 1.1-only, so forbid publishing another version.
- Preflight remote `v1.1.0` **tag** and public **release**. Never move, delete, force-update, clobber, overwrite or republish a tag/release. If a tag is present for another commit, fail; if public release exists, exit before changing anything. A matching tag without public release is not a reason to move the tag, but may be dispatched if it remains target-compatible.
- Tag with `gh api -X POST repos/$GITHUB_REPOSITORY/git/refs -f ref=refs/tags/v1.1.0 -f sha=$TARGET_COMMIT`, then dispatch exactly `publish-corpus-release.yml` with tag/ref `v1.1.0` and matching commit. Use `gh workflow run --ref v1.1.0` so the publisher's `GITHUB_SHA` preflight is pinned to the tag, not later advancing main. The full verified publisher remains solely responsible for asset generation, validation, draft promotion, and live TF acceptance. A tag-only state after downstream failure is a recoverable, non-destructive checkpoint.
- Permissions scoped to `contents: write`, `actions: write` **on this launcher only**. Never run generated or upstream code with a write token. The launcher itself should execute only `gh`, basic shell/stdlib Python and read the tracked version files (no pip install).
- Single release only. Release workflow should become inert after publication, and no further release tags should be generated from this launcher.
- If GitHub connector lacks authorization to write `.github/workflows`, stop without claiming success; do not circumvent GitHub permissions. Publication issue remains open until both public release and Agora pin are verified.

## RED test gate

Add `tests/test_release_110_launcher_contract.py` **before** the workflow implementation. Assert workflow exists, exact `workflow_run` success/push/main/same-repository guards, commit liveness/immutable checkout, version pin, scoped permissions, tag/create + dispatch contract, `--ref` tag, no force/delete/other-release side effects, no unsafe PR trigger, no installer or dynamic script. Existing publisher contracts must remain green. RED failure must be observed on GitHub Actions at the tests-only SHA.

## Implementation and GREEN

Add `.github/workflows/launch-v1-1-release.yml` with short fail-closed job as specified. No modification to canonical publisher or OCP converter. Run exact-head full unit + pinned upstream end-to-end corpus conversion/audit/native/express/stock offline TF app and 1 Enoch comparison. Post a logically independent, adversarial review on real YAML, tests, branch/ref semantics, permissions, race and absence conditions. Merge only if all test gates green.

## Post-merge release verification

The automatic workflow should fire after post-merge main `test` succeeds. Verify newly created tag resolves to **the launcher's own final main merge SHA**; verify publication workflow started with that exact release SHA and progressed to completion with validated draft and live TF. Then verify public GitHub release exact four assets, source/license identity and Agora materializer stable pin. If automation is blocked at any gate, file a precise diagnosis on Issue #206 and leave issue open; never report release as published without live evidence.
