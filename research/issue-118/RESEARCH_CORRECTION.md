# Issue #118 — RED findings and research correction

Status: **corrected after observed RED, before any production implementation**.

Observed RED head: `6a18f8b824642efeb945a11f1521c6c9104266fb`.
Observed workflow: `test` run `34323532889`.

## What the RED run corrected

The original research correctly identified that a report path in the Text-Fabric `.tf` namespace is unsafe, but it overstated the final failure mode for direct and target-alias collisions.

On current production code, `--report OUTPUT/otype.tf` does **not** reach a successful final `Path.replace()` that overwrites `otype.tf` with JSON. Before final report publication, the CLI stages a temporary report file in `publication_path.parent`. When that parent is `OUTPUT`, the staged `.tf` appears as a nested `.tf` below the corpus directory. `feature_directory_identity(OUTPUT)` recursively validates the corpus tree and rejects the nested staged feature.

The command therefore fails, but only **after** `_write_prevalidated_tf()` has already run. A deterministic invalid report path can consequently replace the previous TF generation and then make the command fail while the previous report remains unpublished. The transaction boundary is still wrong: a failed conversion may mutate the corpus.

The same post-write failure was observed for:

- direct `OUTPUT/otype.tf`;
- an external report symlink resolving to `OUTPUT/otype.tf`;
- a `..` alias resolving to top-level `OUTPUT/oslots.tf`.

The pinned-upstream integration remained green because normal report paths do not enter this collision class.

## Additional namespace facts proved by RED

### Nested `.tf` reports inside OUTPUT are not valid positive controls

The original plan said `OUTPUT/reports/audit.tf` could remain allowed because the writer manages only top-level `OUTPUT/*.tf`. That is incomplete: canonical feature-directory validation recursively rejects **any nested `.tf` file** under the output tree.

The RED positive-control test for `OUTPUT/reports/audit.tf` failed with:

`DistributionContractError: extracted TF directory contains nested feature files: reports/.pseudepigrapha-tf-report-.../audit.tf`

Even if report staging were moved elsewhere, publishing `OUTPUT/reports/audit.tf` would leave a nested `.tf` sidecar that makes the canonical output directory invalid. This path should therefore also be rejected before TF serialization.

### A top-level `.tf` report symlink pointing outside is still unsafe

`OUTPUT/report.tf -> /external/audit.json` is unsafe for a different reason. The writer enumerates top-level `OUTPUT/*.tf` entries as the generation it owns, so the symlink entry itself can be moved into the backup/discarded during installation even though its resolved publication target is external.

Thus both the report directory entry and its resolved target matter.

## Corrected invariant

Before creating a report staging directory or invoking `_write_prevalidated_tf()`, reject a report when either:

1. its normalized directory entry is a `.tf` path anywhere inside the resolved output tree; or
2. its resolved publication target is a `.tf` path anywhere inside the resolved output tree.

This is broader than the original top-level-only target check because canonical feature-directory validation already reserves the entire output subtree from nested `.tf` sidecars.

External `.tf` reports remain allowed because they do not enter the corpus tree or writer-managed feature namespace.

## Path normalization

Use resolved output and report parents/targets, not textual prefix checks:

```python
resolved_output = args.output.resolve(strict=False)
entry_path = report_path.parent.resolve(strict=False) / report_path.name
publication_path = report_path.resolve(strict=False)
```

A candidate is inside the corpus tree when `candidate == resolved_output` or `resolved_output in candidate.parents` (equivalently `candidate.is_relative_to(resolved_output)` on supported Python versions).

Reject only when the candidate suffix is `.tf` and it is inside the resolved output tree.

This covers direct paths, `..`, symlinked parents/output aliases, report symlink entries inside output, and report symlink targets inside output without banning harmless external `.tf` report files.

## Corrected acceptance claim

The bug is not “successful report publication corrupts a feature” on the current code path. The demonstrated bug is:

> A deterministic invalid report path can be discovered only after the TF generation has already been installed, so a command that exits with failure can still replace the previous corpus generation or remove a report symlink managed as `*.tf`.

The fix remains a pre-write path guard in `cli.main()`; no writer redesign is required.
