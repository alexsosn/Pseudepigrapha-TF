# Issue #118 — report/feature path-collision research

Status: **research complete before plan/TDD/production changes**.

Research base: `38fb7abaaf03f39c4558d521b8af9a219f17b39a`.

## Scope

This is a CLI publication-integrity bug. It does not concern semantic report contents, Text-Fabric serialization semantics, release packaging, or corpus provenance. It concerns the final filesystem target used to publish `conversion-report.json` (or an explicit `--report` path) after a successful TF generation has already been installed and hashed.

## Current successful publication order

`cli.main()` currently performs the relevant successful path in this order:

1. build and semantically audit the graph;
2. choose `report_path = args.report or (args.output / "conversion-report.json")`;
3. create `report_path.parent`;
4. compute `publication_path = report_path.resolve(strict=False)`;
5. reject only `publication_path.is_dir()`;
6. write the report to a temporary staged file;
7. call `_write_prevalidated_tf(data, args.output)`;
8. compute `report["text_fabric"] = feature_directory_identity(args.output)` from the installed feature bytes;
9. rewrite the staged report with that feature identity;
10. call `staged_report.replace(publication_path)`.

`Path.replace()` replaces an existing file at the target. Therefore if the publication target is a generated top-level TF feature, step 10 overwrites the feature **after** step 8 recorded its hash.

## Corruption cases

### Direct target

For:

```text
--output /tmp/tf/0.2 --report /tmp/tf/0.2/otype.tf
```

`publication_path` is `/tmp/tf/0.2/otype.tf`. The TF writer installs a valid `otype.tf`; `feature_directory_identity()` hashes it; then staged report JSON replaces it. The command has no post-replacement feature validation and can return success.

The same applies to any top-level `*.tf` filename in the output generation, including optional/support features produced by Text-Fabric. The CLI cannot safely hard-code a feature-name allow/deny list because the serializer may add support features and future feature contracts can evolve.

### Symlink/alias target

The CLI intentionally resolves explicit report symlinks so it can update the symlink target without replacing the symlink itself. Consequently, a report symlink whose target resolves to `OUTPUT/otype.tf` reaches the same corruption target.

Likewise, lexical aliases using `..` can refer to the same target. Python 3.10 documents `Path.resolve(strict=False)` as making a path absolute, resolving symlinks, and eliminating `..` components; this is the appropriate comparison primitive already used by the CLI.

Primary reference:

- https://docs.python.org/3.10/library/pathlib.html#pathlib.Path.resolve
- https://docs.python.org/3.10/library/pathlib.html#pathlib.Path.replace

## Existing transaction boundary

`writer._install_staged_tf_features()` only reconciles top-level `*.tf` files and intentionally leaves non-TF sidecars untouched. It backs up the previous TF set, installs the staged TF set, and rolls back on installation failure.

The report collision occurs **after** that transaction succeeds. The writer cannot protect against it because the report publication is a separate CLI step. The correct guard must therefore run before `_write_prevalidated_tf()` so a deterministic report-target error cannot mutate the existing corpus at all.

## Existing tests

`tests/test_cli_validation.py` already covers:

- successful report identity binding;
- preserving the previous/default report when TF serialization fails;
- preserving an explicit external report when TF serialization fails;
- publishing a semantic-audit failure report without invoking the TF writer;
- rejecting a directory report target before TF serialization;
- preserving explicit report-symlink semantics on success.

It does not cover a report publication target that resolves to `OUTPUT/*.tf`.

## Narrow invariant

Before successful TF serialization begins:

> The resolved report publication target must not be a top-level `.tf` path in the resolved output directory.

This is intentionally path-based rather than feature-registry-based:

- any top-level `.tf` in `OUTPUT` is inside the generation managed by the writer;
- rejecting all such targets protects present and future serializer-added TF files;
- a `.tf`-suffixed report outside `OUTPUT` does not collide with the installed generation and should remain legal;
- nested `.tf` report targets below a subdirectory of `OUTPUT` are not writer-managed top-level TF features and are not part of this demonstrated corruption path.

## Resolution semantics

Use resolved paths for both sides:

```text
resolved_output = args.output.resolve(strict=False)
publication_path = report_path.resolve(strict=False)
collision = publication_path.parent == resolved_output and publication_path.suffix == ".tf"
```

`report_path.parent.mkdir(...)` already precedes report resolution, which permits non-existing final report files to resolve as far as possible. `args.output` may not exist yet, but `resolve(strict=False)` still yields a normalized absolute target.

This detects:

- direct absolute/relative collisions;
- `..` aliases;
- symlinked report filenames whose target is an output feature;
- symlink aliases in existing parent path components.

It does not depend on file existence and therefore can reject before writer mutation.

## Error behavior

The CLI currently raises `IsADirectoryError` directly for a deterministic invalid report publication target. A report/feature collision can likewise raise a clear `ValueError` (or a narrow dedicated value error if justified), mentioning that the report target collides with the Text-Fabric output generation. There is no need to route this through semantic parity or TF writer failure handling.

## Boundaries

This ticket must not:

- change report JSON contents;
- change the successful default report path;
- change writer rollback/install semantics;
- reject harmless external `.tf` report paths;
- replace explicit report symlinks on successful non-colliding publication;
- create a duplicated list of expected TF feature names;
- broaden into generic path-sandboxing unrelated to corpus integrity.

## Research conclusion

The defect is real and the narrow pre-write guard is sufficient for the demonstrated corruption class. The guard belongs in `cli.main()` immediately after the existing publication-path resolution/directory check and before creation/use of the staged report + TF write transaction.
