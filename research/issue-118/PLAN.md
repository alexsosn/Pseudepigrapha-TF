# Issue #118 — frozen implementation plan

Status: **frozen before RED tests and production implementation**.

Research base: `38fb7abaaf03f39c4558d521b8af9a219f17b39a`.
Research: `research/issue-118/RESEARCH.md`.

## Invariant

A successful conversion must never publish its report over a top-level `.tf` member of the Text-Fabric output generation.

The collision must be rejected before `_write_prevalidated_tf()` runs, so an already installed corpus remains untouched.

## RED-first tests

Extend `tests/test_cli_validation.py` before editing `cli.py`.

### RED 1 — direct collision

Prepare an existing output generation containing sentinel `otype.tf` and `oslots.tf` bytes. Invoke the CLI with:

```text
--output OUTPUT --report OUTPUT/otype.tf
```

Instrument `_write_prevalidated_tf()` with a counted/guarded writer. Require:

- a clear collision error;
- writer call count `0`;
- sentinel TF bytes unchanged.

Current code must fail because it invokes the writer and/or overwrites the target instead of rejecting it pre-write.

### RED 2 — symlink collision

Create an explicit report symlink whose resolved target is `OUTPUT/otype.tf`. Invoke with `--report REPORT_SYMLINK`.

Require:

- collision rejection before writer call;
- report symlink remains a symlink;
- existing `otype.tf` bytes remain unchanged.

Current code must fail because `report_path.resolve(strict=False)` intentionally follows the symlink but does not classify the resulting target as unsafe.

### RED 3 — lexical/path alias collision

Use a report path containing a `..` alias that resolves to top-level `OUTPUT/oslots.tf`.

Require the same pre-write rejection. This prevents a future regression to string-prefix/path-text comparisons.

### Positive controls

Retain existing tests and add only where needed to make the boundary explicit:

- default `OUTPUT/conversion-report.json` succeeds;
- explicit external report succeeds;
- non-colliding explicit report symlink updates its target without replacing the symlink;
- an external file named `something.tf` remains allowed;
- if tested, nested `OUTPUT/reports/result.tf` remains allowed because it does not collide with the writer-managed top-level feature set.

## Minimal GREEN implementation

In `cli.py`, after:

```python
report_path.parent.mkdir(parents=True, exist_ok=True)
publication_path = report_path.resolve(strict=False)
if publication_path.is_dir():
    raise IsADirectoryError(str(report_path))
```

compute the resolved output path and reject exactly the dangerous class:

```python
output_path = args.output.resolve(strict=False)
if publication_path.parent == output_path and publication_path.suffix == ".tf":
    raise ValueError(...)
```

Requirements:

- guard executes before `TemporaryDirectory(...)` and `_write_prevalidated_tf()`;
- error includes the report path and explains that it collides with Text-Fabric output;
- no feature-name registry;
- no change to report staging or writer transaction logic.

If RED reveals a subtlety requiring a helper function, keep it pure/path-only and locally scoped; do not broaden the patch.

## Focused GREEN gate

Run the full CLI validation module, with special attention to:

- direct collision;
- symlink collision;
- `..` alias collision;
- previous corpus bytes preserved;
- existing report symlink behavior;
- default report identity binding.

## Full gates

On the exact final head require both permanent CI jobs:

1. `unit-and-tf` — complete test suite and real Text-Fabric integration;
2. `pinned-upstream-integration` — wheel build/fresh install, exact OCP conversion/audit, feature docs, semantic parity, canonical staging/validation/extraction/reload, generated translations, public metadata, advanced app load.

No release/tag action belongs to this ticket.

## Independent adversarial review

Review the exact final green head without relying on the implementation rationale. Challenge:

- direct absolute and relative aliases;
- `..` normalization;
- report symlink target collisions;
- symlinked output-directory aliases;
- whether guard executes before any TF mutation;
- whether a top-level future serializer-generated `.tf` is protected without a registry;
- accidental rejection of external `.tf` reports;
- accidental rejection of nested non-colliding sidecars;
- preservation of explicit non-colliding report symlink behavior;
- preservation of existing directory-target rejection and serialization rollback semantics.

A blocker requires a new RED regression and a complete GREEN/full-gate/re-review cycle.

## Merge criterion

Merge only when:

- RED history demonstrates the original hole;
- exact final head is green in both permanent CI jobs;
- final diff remains narrow;
- logically independent adversarial review on the exact green SHA has no blocking findings.
