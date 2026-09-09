# Issue #118 — plan amendment: protect the report directory entry as well as its resolved target

Status: **amended before production implementation**.

The initial frozen plan correctly protected a report whose **resolved publication target** lands on a top-level `OUTPUT/*.tf` feature. A pre-implementation adversarial pass identified a second writer-managed collision class.

## Missed case

Consider:

```text
OUTPUT/report.tf -> /external/audit.json
```

The resolved publication target `/external/audit.json` is not inside the corpus. However, `writer._install_staged_tf_features()` enumerates `output.glob("*.tf")` as the existing TF generation. The `OUTPUT/report.tf` symlink directory entry is therefore writer-managed: a real successful install may move it into the TF backup and then discard that backup. The final report can be published to `/external/audit.json`, but the explicit report symlink itself no longer has the promised preservation semantics.

This is still a report/TF namespace collision and should fail before writer mutation.

## Amended invariant

Reject before `_write_prevalidated_tf()` when **either** of these is true:

1. the report path's own top-level directory entry is inside the resolved output directory and has suffix `.tf`;
2. the report's resolved publication target is inside the resolved output directory and has suffix `.tf`.

Conceptually:

```python
resolved_output = args.output.resolve(strict=False)
report_parent = report_path.parent.resolve(strict=False)
publication_path = report_path.resolve(strict=False)
entry_collision = report_parent == resolved_output and report_path.suffix == ".tf"
target_collision = publication_path.parent == resolved_output and publication_path.suffix == ".tf"
if entry_collision or target_collision:
    raise ValueError(...)
```

The first check protects the writer-managed directory entry even when a symlink points outside. The second protects external/non-`.tf` aliases and symlinks whose resolved target is an actual corpus feature.

## Added RED case

Add a report symlink at top-level `OUTPUT/report.tf` pointing to an external JSON file. Require collision rejection before the writer is called and preservation of both the symlink and existing TF generation.

## Scope remains narrow

- external `.tf` report files whose directory entry is outside `OUTPUT` remain allowed;
- nested `OUTPUT/reports/audit.tf` remains allowed because the writer manages top-level `OUTPUT/*.tf`, not nested sidecars;
- non-`.tf` top-level report symlinks remain allowed unless their resolved target is a top-level output feature;
- no feature-name registry is introduced.

All other gates from `PLAN.md` remain unchanged.
