# Issue #129 — warning-discipline research and frozen plan

## Research baseline

Current base: `daad3d32c659d2531f10fa4d038d911f6f895b2b`.

Permanent main CI run `34473153838` is green with `559 passed, 2 warnings` in the unit/Text-Fabric job. Both warnings come from `tests/test_writer_cleanup_interrupts.py`:

1. `test_cleanup_interrupt_after_successful_rollback_preserves_original_error` emits `RuntimeWarning: previous TF set was restored, but empty backup cleanup failed ...`.
2. `test_cleanup_interrupt_after_commit_cannot_turn_committed_install_into_failure` emits `RuntimeWarning: Text-Fabric features were installed successfully, but the old backup could not be removed ...`.

These are deliberate production diagnostics from the atomic-install cleanup path, not leaked resources or third-party warnings. The same test module already captures equivalent nonfatal cleanup diagnostics in neighboring cases using `pytest.warns(RuntimeWarning, match=...)`.

`pyproject.toml` currently configures only `addopts = "-q"` and `testpaths = ["tests"]`; no repository-wide warning policy exists.

The pinned-upstream job in the same run is green and does not report pytest warning summaries. Action/runtime deprecation notices emitted by GitHub Actions itself are outside pytest and therefore outside this ticket.

## Ownership conclusion

The warning semantics in `writer.py` are correct and must remain unchanged. The defect is test ownership / CI signal quality: two tests intentionally trigger diagnostics but do not assert them, while pytest is configured to allow all unexpected Python warnings without failing the suite.

## Frozen implementation plan

1. RED: add `filterwarnings = ["error"]` to `[tool.pytest.ini_options]` and make no test or production change in that commit.
2. Prove the strict policy fails specifically on the two intentionally unowned `RuntimeWarning`s above.
3. GREEN: wrap the exact operations in those two tests with `pytest.warns(RuntimeWarning, match=...)` using message fragments specific to rollback-restored cleanup and committed-install backup cleanup.
4. Preserve all existing assertions about original exception identity, output bytes, obsolete-feature removal, and report preservation.
5. Do not add category/module ignores, do not weaken to `default`, and do not change production source.
6. Run focused `tests/test_writer_cleanup_interrupts.py`, then full unit/real-TF and exact pinned-OCP gates.
7. Perform a logically independent adversarial review of the exact final head, specifically challenging overbroad warning suppression, false-positive global strictness, swallowed diagnostics, and weakened transaction assertions.

## Expected RED

With only `filterwarnings = ["error"]` added, all pre-existing tests except the two intentional cleanup-diagnostic cases should remain green. Those two should fail because their `RuntimeWarning`s are no longer globally tolerated.

## Acceptance

- unexpected Python warnings are fatal under pytest;
- intentional cleanup diagnostics are asserted locally by the tests that trigger them;
- `writer.py` and all runtime modules are unchanged;
- final suite has no pytest warning summary from owned cleanup diagnostics;
- exact pinned OCP integration remains green;
- exact-head independent review finds no blocker.
