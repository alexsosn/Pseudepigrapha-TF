# Issue #122 — output-path symlink research

Research base: `be074c0a269fb20a0340d6a04fa9ab05a86ee906` (`main` after #118/#120).

## Question

Can the CLI deterministically accept an `--output` pathname that the canonical distribution contract will reject only *after* `_write_prevalidated_tf()` has installed a new generation, leaving a failed conversion with mutated TF bytes and no matching published report?

## Static execution trace

The current CLI success path is:

1. select/validate the report path;
2. build and stage the successful conversion report;
3. call `_write_prevalidated_tf(data, args.output)`;
4. call `feature_directory_identity(args.output)`;
5. add that identity to the staged report and publish it.

The writer deliberately accepts ordinary `Path` locations. `_serialize_tf()` does:

```python
output = Path(output_dir)
output.mkdir(parents=True, exist_ok=True)
...
stage = Path(mkdtemp(..., dir=output.parent))
...
_install_staged_tf_features(stage, output)
```

`_install_staged_tf_features()` enumerates `output.glob("*.tf")` and replaces those entries. A final-component directory symlink is therefore followed by normal filesystem operations; there is no writer-level canonical-path rejection.

The post-write distribution contract is stricter. `_directory_feature_records()` begins with:

```python
if directory.is_symlink():
    raise DistributionContractError(
        f"extracted TF directory must not itself be a symlink: {directory}"
    )
```

Therefore a final-component output symlink is deterministically invalid for canonical publication even though the writer can operate through it.

## Writer API versus CLI publication policy

No writer test, public writer validation, or writer implementation currently declares a symlinked destination invalid. `write_tf()` validates the graph and delegates to `_serialize_tf()`; the writer transaction is concerned with serialized feature integrity and rollback, not canonical distribution pathname policy.

The narrow issue is therefore the CLI's canonical-publication boundary. This ticket should not silently change direct `write_tf(..., symlink_dir)` semantics without separate evidence.

## Parent symlinks and lexical aliases

The canonical distribution check uses `directory.is_symlink()` on the final directory entry. It does **not** reject a real final directory reached through a symlinked parent. For example, if `PARENT_ALIAS -> REAL_PARENT` and `PARENT_ALIAS/tf` is a real directory entry under `REAL_PARENT`, then `Path("PARENT_ALIAS/tf").is_symlink()` is false.

Likewise, a lexical spelling containing `..` that resolves to a real final directory does not make that final directory a symlink. A guard based on `output.resolve() != output.absolute()` would therefore be broader than the canonical distribution contract and would incorrectly reject accepted aliases.

The narrow pre-write predicate matching the existing canonical contract is final-component `output.is_symlink()`.

## Empirical probe

Actions run `34363530423` was created from the exact research base to exercise four cases without production changes:

1. final-component `OUTPUT_ALIAS -> REAL_OUTPUT` with an existing sentinel TF generation and normal/default report path;
2. direct `write_tf()` to a symlinked directory;
3. CLI/writer/canonical identity through a symlinked parent with a real final directory;
4. a lexical `..` alias resolving to a real final directory.

The probe is isolated on temporary branch `research/issue-122-output-symlink` and deletes that branch at completion. Its result must be recorded before the implementation plan is frozen. If it contradicts the static trace above, the plan must follow observed behavior instead.

## Scope boundary

This issue is not another report-path collision ticket. #118/#120 already protect report entries/targets and same-inode aliases to TF features. Here the report may be the ordinary default JSON path; the defect is that the output generation itself can be installed through a pathname that canonical post-write validation rejects.

No production change is justified yet in this research commit. The implementation plan follows only after empirical confirmation.