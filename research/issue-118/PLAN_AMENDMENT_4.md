# Issue #118 — plan amendment 4: hard-link aliases

Status: **blocking adversarial finding after first GREEN, before final review/merge**.

The first GREEN head `e0d319230f21258f5ddbc343ef6386f0c6f74a04` passed the complete unit/Text-Fabric and pinned full-corpus gates. A fresh adversarial review then challenged filesystem aliasing that `Path.resolve()` cannot distinguish and found a remaining corruption path.

## Hard-link bypass

`Path.resolve()` resolves lexical components and symbolic links, but two hard-linked regular-file directory entries remain distinct path strings that refer to the same inode.

Suppose an existing corpus has:

```text
OUTPUT/otype.tf
```

and the user supplies a report pathname such as:

```text
/external/report.json
```

that is a hard link to `OUTPUT/otype.tf`.

The current GREEN path guard sees:

- report entry outside the output tree;
- publication path outside the output tree;
- suffix `.json`;

and permits it.

If semantic audit fails, current code calls `write_conversion_report(report, report_path)`. `Path.write_text()` opens/truncates the existing inode in place, so the diagnostic JSON overwrites the bytes also visible at `OUTPUT/otype.tf` before the CLI exits failed.

The same bypass can use a non-`.tf` hard-link sidecar inside the output tree, e.g. `OUTPUT/report.json` hard-linked to `OUTPUT/otype.tf`.

The successful-audit final publication path uses staged `Path.replace()`, so replacing an external hard-link directory entry would detach that one link rather than mutate the feature inode. The demonstrated corruption surface is specifically the in-place failed-audit report write (and any future in-place report write).

## Amended invariant

Before any report publication, detect an **existing report target that is the same file as an existing `.tf` feature under the resolved output tree**, even when path/suffix checks do not reveal the alias.

This is an inode-identity check, not a feature-name registry.

Potential minimal helper:

```python
def _report_aliases_existing_tf(publication_path: Path, output: Path) -> bool:
    if not publication_path.exists() or not output.is_dir():
        return False
    for feature in output.rglob("*.tf"):
        if feature.is_file() and publication_path.samefile(feature):
            return True
    return False
```

Implementation must handle expected filesystem races/errors deliberately; do not silently swallow a permission/stat failure that could turn a fail-closed validation into permission to overwrite. Keep scope limited to existing regular-file identity aliases.

## New RED gate

Starting from first GREEN, add RED before changing production again:

1. existing sentinel `OUTPUT/otype.tf`;
2. create an external `report.json` hard link to that feature;
3. force semantic audit failure;
4. require collision rejection before diagnostic report write;
5. require sentinel feature bytes unchanged;
6. require the external hard-link entry still refers to unchanged bytes.

Also cover `OUTPUT/report.json` hard-linked to `OUTPUT/otype.tf` if practical, because suffix/path-only checks likewise miss it.

Positive control: an ordinary pre-existing external report file that is not inode-identical to any output feature remains accepted.

## GREEN/full gates restart

After the minimal inode-alias fix:

- focused collision tests;
- complete unit/Text-Fabric suite;
- complete pinned OCP integration;
- fresh logically independent adversarial review of the new exact green head.

The previous GREEN evidence is superseded for merge purposes by the new final head.
