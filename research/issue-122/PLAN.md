# Issue #122 — frozen implementation plan

Status: **frozen after code-grounded research and before RED tests / production changes**.

Research base: `be074c0a269fb20a0340d6a04fa9ab05a86ee906`.
Research: `research/issue-122/RESEARCH.md`.

## Invariant

The CLI must not install a Text-Fabric generation through an `--output` pathname that the same CLI's canonical post-write `feature_directory_identity()` will deterministically reject because the **final output directory entry is a symbolic link**.

That invalidity must be detected before `_write_prevalidated_tf()` is invoked, so a pre-existing generation remains byte-for-byte unchanged on failure.

The invariant is deliberately narrower than path canonicalization:

- final-component output symlink: reject;
- real final directory reached through a symlinked parent: allow, because current canonical distribution validation allows it;
- lexical `..` spelling resolving to a real final directory: allow;
- direct `write_tf(..., symlink_dir)` API: unchanged by this CLI policy ticket.

Do not use `output.resolve() != output.absolute()` or equivalent. That would invent a stricter policy than the existing distribution contract.

## TDD RED

Add a focused CLI regression module before editing production code.

### RED 1 — final-component output symlink

Create:

```text
REAL_OUTPUT/
  otype.tf   # sentinel old bytes
  oslots.tf  # sentinel old bytes
OUTPUT_ALIAS -> REAL_OUTPUT
```

Invoke normal successful conversion with the default report location and `--output OUTPUT_ALIAS`.

Instrument `_write_prevalidated_tf()` with a writer that records calls and, if invoked, changes the real output sentinel. Require:

- clear `ValueError` mentioning the Text-Fabric output symlink/canonical output problem;
- writer call count `0`;
- `REAL_OUTPUT/*.tf` sentinel bytes unchanged;
- no new conversion report published through the alias.

Current code must fail because there is no pre-write output-path guard.

### Positive 1 — ordinary real directory

Use an existing real output directory. A counted/stub writer should be invoked and the CLI should complete normally.

### Positive 2 — symlinked parent

Create:

```text
PARENT_ALIAS -> REAL_PARENT
OUTPUT = PARENT_ALIAS/tf
```

where `tf` is a real final directory entry under `REAL_PARENT`. Require success / writer invocation. This protects the researched distinction between a symlinked final directory and a path traversing a symlinked parent.

### Positive 3 — lexical `..`

Use a spelling such as `ROOT/lex/../tf` where the final `tf` directory is real. Require success / writer invocation.

### Direct writer contract

Keep or add a focused writer-level positive regression only if necessary to make scope explicit: `write_tf(data, symlink_dir)` remains supported. The CLI guard must not be moved into `_serialize_tf()` or `write_tf()` in this ticket.

## Minimal GREEN

Add a small CLI-local validator, conceptually:

```python
def _validate_output_path(output: Path) -> None:
    if output.is_symlink():
        raise ValueError(
            f"Text-Fabric output directory must not be a symlink: {output}"
        )
```

Call it after parsing the `convert` command and before `_write_prevalidated_tf()` can run. Prefer fail-fast placement before expensive source/build work unless an existing CLI ordering contract makes that incompatible.

No `resolve()` comparison and no parent-component symlink scan.

## Full gates

On the exact final head require:

1. `unit-and-tf` complete success;
2. `pinned-upstream-integration` complete success, including fresh wheel install, exact OCP conversion/parity, feature-help coverage, canonical stage/verify/extract/reload, generated translations, public metadata, classifications/provenance and tracked advanced app load.

The isolated research probe `34363530423` is observational; record its result when the runner executes. If it contradicts the plan's path semantics, amend the plan before production implementation.

## Logically independent adversarial review

Review the exact final green head without relying on implementation intent. Challenge:

- final-component symlink to an existing corpus with sentinel bytes;
- dangling final-component symlink;
- symlinked-parent path with real final directory;
- lexical `..` alias;
- ordinary existing and non-existing real output directories;
- whether any mutation/report publication occurs before rejection;
- whether direct writer API semantics changed accidentally;
- consistency with `_directory_feature_records()` rather than a newly invented canonicalization policy;
- interaction with #118 report-path guards when the default report lies under the output alias.

Any blocker becomes a new RED regression before revision and re-review.

## Merge criterion

Merge only after authoritative RED evidence on current behavior, exact-head full GREEN, narrow diff, and exact-head adversarial review with no blockers.