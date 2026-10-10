# Recovery contract for TF feature/report publication

The `pseudepigrapha-tf convert` command publishes a validated Text-Fabric generation and its matching `conversion-report.json`. The report includes a SHA-256 identity of the actual serialized `*.tf` files. A previous report must not silently remain paired with a different feature generation after a recoverable CLI failure.

## Successful conversion

After independent semantic audit, the CLI stages the report in a temporary directory on the report filesystem. The writer serializes `*.tf` into a temporary stage adjacent to the output directory and moves the existing feature set into a temporary backup, both on the output filesystem.

The new `*.tf` files are then moved into the output. **While the previous feature set is still retained in the backup**, the CLI computes the new `feature_directory_identity`, writes the final report in its stage, and replaces the report publication path. Only once that succeeds is the feature backup cleaned up. Direct `write_tf()` callers do not publish a CLI report and retain their prior immediate-commit behavior.

No second full TF serialization or copy of the previous feature set is required. This preserves the repository's optimized serialization and source-to-TF semantic audit contracts.

## Failure scenarios

- Failure or `KeyboardInterrupt` during TF installation or later report fingerprinting/write/final rename: **restore all previous `*.tf` features**, removing new-only features; leave the previous report untouched; retain unrelated non-TF files.
- If no previous feature generation existed: remove partially installed `*.tf` files after failure, without deleting unrelated files.
- If rollback fails: propagate the combined installation/publication **and** rollback exceptions and retain the backup directory with recoverable old feature bytes. Investigate that backup before retrying conversion.
- A failure only to delete a backup *after* successfully publishing both features and report is nonfatal housekeeping, reported as a warning. The published matched pair remains valid.
- If semantic parity audit fails **before** feature installation, the CLI may publish a failure diagnostic report, but does not publish a new TF generation.

Explicit `--report` paths, including symlinks to a non-TF report file, retain their existing publication semantics; the destination is checked for namespace/hardlink collision before feature installation. Publication itself remains a single filesystem rename of the report target.

## Limitations

This is **exception-safe recovery**, not general multi-file transaction isolation: while individual `*.tf` feature files are renamed, uncoordinated concurrent readers could temporarily observe a mixed generation. An unconditional process kill, machine crash, or power loss during this interval cannot be recovered by a Python exception handler. True crash-safe atomic visibility would require a generation-pointer/journaling design and its own migration/research plan.

Do not use these guarantees to skip release manifest verification: distribution still checks that the report's feature-set hash matches the exact serialized archive. Regression tests cover post-install report-publication errors, interruptions, failed rollback recovery, and ordinary success.
