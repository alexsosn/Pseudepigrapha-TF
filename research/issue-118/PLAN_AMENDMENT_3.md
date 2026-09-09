# Issue #118 — plan amendment 3: validate before failed-audit report publication

Status: **amended before production implementation**.

A second pre-implementation adversarial pass found a collision path earlier than the successful publication transaction.

## Missed failure-audit path

`report_path` is selected before the semantic audit result is checked. If `report["status"] != "ok"`, current code immediately calls:

```python
write_conversion_report(report, report_path)
```

and then exits with `SystemExit`.

Therefore a failed semantic audit plus `--report OUTPUT/otype.tf` can overwrite an existing Text-Fabric feature directly, without reaching `_write_prevalidated_tf()` or the success-path publication validation at all. The same risk applies to report symlink/alias targets in the output `.tf` namespace.

## Final placement invariant

The report namespace guard must run **immediately after `report_path` is chosen and before building/publishing any conversion report side effect**. In particular it must precede:

- failed-audit `write_conversion_report(report, report_path)`;
- report parent creation/staging;
- `_write_prevalidated_tf()`;
- successful final report publication.

Path validation itself does not depend on semantic report contents.

The existing directory-target check may remain near successful publication if desired, but collision validation must be earlier.

## Added RED case

Force `build_conversion_report()` to return a failed audit and use `--report OUTPUT/otype.tf` with an existing sentinel TF generation. Require:

- collision `ValueError` before the feature is touched;
- sentinel `.tf` bytes unchanged;
- TF writer not called;
- no diagnostic report published into the feature namespace.

## Minimal implementation adjustment

Extract or inline a small path-only validator and call it directly after:

```python
report_path = args.report or (args.output / "conversion-report.json")
```

The validator computes resolved output, normalized report entry, and resolved publication target and rejects `.tf` candidates inside the output tree. It may return `publication_path` so the success path does not need to resolve it twice.

All earlier amendments and full gates remain required.
