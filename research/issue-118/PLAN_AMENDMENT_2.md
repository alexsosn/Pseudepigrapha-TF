# Issue #118 — plan amendment 2 after observed RED

Status: **amended after RED evidence and before production implementation**.

This amendment supersedes the two inaccurate parts of the original plan while preserving the rest of the research → plan → RED → GREEN gates.

## Corrected failure model

Direct/target-alias `.tf` report collisions currently fail during `feature_directory_identity()` because the staged report is itself seen as a nested `.tf` under the output tree. The required invariant is therefore pre-write failure atomicity: reject the deterministic invalid path before `_write_prevalidated_tf()` can replace the previous generation.

## Corrected namespace boundary

The guard must reject a `.tf` report **anywhere inside the resolved output tree**, not only at top level, because canonical feature-directory validation reserves nested `.tf` paths as invalid feature entries.

Check both:

- the normalized report directory entry (`report_path.parent.resolve(strict=False) / report_path.name`), so a `.tf` symlink entry inside output cannot be consumed by the writer even when its target is external;
- the fully resolved publication target (`report_path.resolve(strict=False)`), so an external/non-`.tf` alias cannot target a corpus `.tf` path.

External `.tf` report files remain legal.

## Corrected RED tests

The authoritative RED suite must require pre-write rejection and unchanged previous TF bytes for:

1. direct `OUTPUT/otype.tf`;
2. report symlink resolving to `OUTPUT/otype.tf`;
3. `..` alias resolving to `OUTPUT/oslots.tf`;
4. top-level `OUTPUT/report.tf` symlink pointing to an external JSON target;
5. nested `OUTPUT/reports/audit.tf`.

The nested case is now a rejection test, not a positive control.

Positive controls remain:

- default `OUTPUT/conversion-report.json`;
- external JSON report;
- external `.tf` report;
- non-colliding external report symlink whose target is updated without replacing the symlink.

## Minimal GREEN implementation

Add a small path-only helper in `cli.py` or equivalent local logic:

```python
def _is_tf_path_within(candidate: Path, root: Path) -> bool:
    return candidate.suffix == ".tf" and (
        candidate == root or root in candidate.parents
    )
```

Then, before report staging and before `_write_prevalidated_tf()`:

```python
resolved_output = args.output.resolve(strict=False)
entry_path = report_path.parent.resolve(strict=False) / report_path.name
publication_path = report_path.resolve(strict=False)
if _is_tf_path_within(entry_path, resolved_output) or _is_tf_path_within(
    publication_path, resolved_output
):
    raise ValueError(...)
```

The check should run before creating a report staging directory. Parent creation for valid report paths remains unchanged afterward.

Do not move report staging outside the output tree merely to make nested `.tf` sidecars work: such sidecars violate the canonical output-directory contract anyway.

## Review additions

The final independent reviewer must explicitly challenge:

- nested `.tf` report paths inside output;
- a `.tf` report symlink entry inside output pointing outside;
- symlinked output-directory aliases;
- external `.tf` reports remaining accepted;
- whether any deterministic collision is detected only after TF mutation.
