# Issue #200 — Report rename committed before interrupted Python return

Frozen source-grounded plan before RED-only tests or implementation.

## Observed source-level inconsistency

- CLI's `publish_matching_report()` is the `after_install` callback to `_write_prevalidated_tf`. It computes new feature hashes, writes staged JSON, and finally runs `staged_report.replace(publication_path)`.
- `writer._install_staged_tf_features()` invokes the callback inside a broad `try/except BaseException` that **always rolls back the TF features** when the callback raises. A `Path.replace` can have performed its atomic filesystem rename before a signal/interrupt is delivered or a wrapper raises. In that case the report now identifies the **new** features but the writer restores the **old** ones, silently leaving an incoherent pair.
- Existing `tests/test_cli_report_publication_rollback.py` covers exceptions before rename and failed rollback, not a rename that already completed successfully before raising.

## Selected recovery architecture

1. Introduce an explicit optional **commit-state probe** inside the private writer transaction, alongside `after_install`. CLI prepares the intended report bytes **after** writing the final staged report, **before** renaming it. The probe returns true only if the intended published report bytes are present at `publication_path`; it never trusts a Python `published=True` assignment that could itself be interrupted immediately after the filesystem syscall.
2. Upon exceptions during TF renames or report publication, query the probe **before any TF rollback**. If report identity is committed, leave the newly published TF files in place, clean up the previous-generation backup best-effort, and re-raise the original exception (interruption/error remains observable). If it is not committed, reuse existing complete TF rollback, preserving original report. If checking committed status raises, **do not guess or roll back**; retain recovery backup and surface both original and status-probe error with the path so operator recovery is possible.
3. Pass the private `publication_committed` keyword only in the `cli convert` standard staging path, through `_write_prevalidated_tf` and `_serialize_tf` to `_install_staged_tf_features`. The public `write_tf()` interface and custom Fabric behavior remain unchanged. Update existing mocked writer stubs deliberately so they preserve the after-install callback semantics.
4. Actual user report is a relatively small JSON identity record; compare exactly its serialized bytes only on ambiguous *exception path*, not on success, to avoid another complete TF serialization/copy/hash. No extra scans of TF corpus.

## RED → GREEN → full CI → independent review

1. RED-only fault-injection tests: patch `Path.replace` so **real report rename happens first**, then raise `KeyboardInterrupt` (and independently `OSError`); require original exception still propagates but new feature files and committed report remain consistent, old-only feature is absent, sidecar untouched, no rollback to old. A pre-rename failure must continue preserving old report/TF generation as already tested.
2. Positive normal CLI conversion must bind report to new `feature_directory_identity`, as currently tested. Add an exception case where publication status cannot be determined (injected I/O read failure) and require recoverable backup plus explicit dual-error exception without destructive rollback.
3. Unit/TF full suite plus complete pinned OCP conversion, independent semantic audit, native/express canonical release, offline stock TF reload and real comparison.
4. Freeze exact head. Perform logically separate skeptical review grounded in real code, injected filesystem state and actual pinned CI. Publish review before merge; no blocker may be waived.

## Limits

This hardens Python exception/interrupt ambiguity. It is not power-loss durability, crash-safe atomic multi-file TF publication, or isolation from concurrent external writers. True robust generation pointer/journal remains a separate architectural change.
