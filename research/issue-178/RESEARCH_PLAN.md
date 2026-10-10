# #178: Conversion report / Text-Fabric generation consistency

Status: plan frozen before RED-first fault-injection tests and implementation.

## Primary-source diagnosis

- Normal `cli.main(convert)` constructs a parity-checked TF graph/report, stages the report, calls `_write_prevalidated_tf`, hashes newly installed files with `feature_directory_identity(output)`, writes the report a second time, and finally renames staged report to its publication path.
- In `writer._serialize_tf` / `_install_staged_tf_features`, old TF files are moved into a local backup, new staged TF files are moved into place, and **the old backup is removed immediately after successful TF renames**, before returning to CLI.
- A later identity-hash error, second report serialization error, final report rename error, or interruption consequently leaves a new TF file generation under a previous report. The release manifest builder rejects stale hashes, but an invalid local corpus pair should not be left behind after a controlled conversion failure.
- Existing tests provide strong mid-install rollback and explicit report-path failure coverage; neither tests a fault **after successful feature installation and before report commit**. This is a demonstrable code path, not a claim of observed production incident.

## Chosen minimal architecture

- Extend private writer ` _install_staged_tf_features(stage, output, *, after_install=None)`: stage and install TF files exactly as today, then invoke an optional *commit hook* while the old TF backup is still available. The hook is responsible only for completing the matching report publication. If any exception or `KeyboardInterrupt` happens, reuse the exact existing `_rollback_tf_features` path; on rollback failure retain backups and propagate `_TFInstallRollbackError` carrying both errors. Only delete old backup if both TF install and commit hook succeed.
- Plumb `after_install` via `_serialize_tf` and the CLI-internal `_write_prevalidated_tf` without modifying the public `write_tf` signature or nonstandard/custom Fabric behavior. The normal `write_tf` path supplies no hook and retains prior behavior and performance.
- In `cli.main`, stage the report before writing TF; the commit hook computes `feature_directory_identity`, updates the report, writes staged JSON and makes `staged_report.replace(publication_path)` its last operation. No extra corpus serialization or complete output-copy. Preserve explicit report symlink-target semantics, non-TF sidecars, feature addition/removal and source identity.
- Keep the original two-phase TF per-file rename limitation: concurrent uncoordinated readers can see a temporary mixed feature set during commit; the intent is failure rollback/CLI consistency, not lock-free multi-file atomics.

## RED-first TDD and verification

1. Commit tests only first, reproducibly inject errors in (i) post-install `feature_directory_identity` and (ii) final staged report `Path.replace`. Prepopulate an older TF feature set, old conversion report and non-TF sidecar; require bytewise rollback of all old features and report, no new-only `.tf`, and propagated original failure. Include the analogous `KeyboardInterrupt` case.
2. Test failure to rollback after report commit failure: original hook error and rollback error both visible; recovery backup retains old TF bytes. Test ordinary successful CLI conversion still binds the report to feature hashes, with one TF save and no extra output copy.
3. Implement narrowly; keep existing writer tests (partial install, symlink, cleanup warning, hardlink collision) passing. Verify full `pytest` and pinned conversion/audit/stock `complete.zip` reload and Flask comparison. If test patches monkeypatch private writer calls, update them deliberately without bypassing commit behavior.
4. Perform genuinely separate adversarial review grounded in final patch, tests, real CI, output state and error semantics; only merge after successful exact-head gates.

## Failure semantics and limits

- For a report publication failure the report remains previous content and TF files return to previous content; if no prior TF files existed, output has no new `.tf` features after rollback.
- For rollback failure, retain the old generation backup and raise the writer's dual-error exception rather than claiming restoration.
- A process crash, SIGKILL or power loss during the rename interval is outside Python exception recovery; a future journaled/two-pointer generation store would be needed for power-loss atomicity.
- Preserve the existing behavior of successful TF write with only cleanup failure: warnings only, not a false failure that could leave inconsistent report.
