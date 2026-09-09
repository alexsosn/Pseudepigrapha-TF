# Issue #115 — reproducible canonical release ZIP research

Status: **research complete before plan/TDD/implementation**.

Base commit: `16a6a11920ff232e8101b9cb6a8382d52868a206`.

## Scope

Issue #115 is a release-distribution stability/reproducibility fix. It does not change corpus semantics, Text-Fabric feature bytes, source provenance, release version identity, or the three-asset publication contract. It only removes filesystem/platform metadata from the byte identity of the generated native TF ZIP.

## Current production path

`stage_distribution_assets()` obtains a canonical sorted list of top-level `.tf` files through `_directory_feature_records()`, then currently writes them with:

```python
with ZipFile(archive, "w", compression=ZIP_DEFLATED) as zf:
    for feature in features:
        zf.write(feature, arcname=feature.name)
```

The resulting archive is then hashed by `_file_record()` and that full-archive SHA-256 is embedded in `dataset-manifest.json`. Feature-set identity itself is already content-derived and canonically sorted; manifest JSON is already serialized deterministically by `canonical_manifest_bytes()`.

## Standard-library behavior

Python's `zipfile` documentation defines `ZipInfo.date_time` as the member's last-modification time recorded in the ZIP central directory. `ZipInfo.from_file()` constructs a `ZipInfo` from a filesystem path, and `ZipFile.write()` writes a filesystem file into the archive. The project supports Python >=3.10, so reproducibility cannot depend on the Python 3.14 `SOURCE_DATE_EPOCH` behavior.

Primary references:

- https://docs.python.org/3/library/zipfile.html#zipfile.ZipInfo
- https://docs.python.org/3/library/zipfile.html#zipfile.ZipInfo.date_time
- https://docs.python.org/3/library/zipfile.html#zipfile.ZipInfo.from_file
- https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile.write
- https://docs.python.org/3/library/zipfile.html#zipfile.ZipFile.writestr

## Reproduction

A direct standard-library reproduction wrote the same payload (`b"same bytes\n"`) to a ZIP twice with `ZipFile.write()`, changing only the source file mtime between builds:

- source mtime 2000-01-01 -> member `date_time=(2000, 1, 1, 0, 0, 0)`;
- source mtime 2021-01-01 -> member `date_time=(2021, 1, 1, 0, 0, 0)`;
- member payloads remained identical;
- complete archive bytes differed;
- complete archive SHA-256 values differed.

Therefore a canonical manifest can currently change without any corpus or feature-byte change.

## Existing test coverage

`tests/test_distribution_staging.py` currently proves:

- exactly `tf-<version>.zip`, `conversion-report.json`, and `dataset-manifest.json` are staged;
- archive members are sorted top-level `.tf` files;
- member payloads equal source feature bytes;
- staged report bytes are preserved;
- `validate_distribution()` accepts the resulting generation;
- failed reports leave no partial destination;
- an existing destination is never mixed/overwritten.

Other distribution tests cover unsafe layouts, feature/report binding, serialized identity, provenance closure, manifest structure, and adversarial tampering. None asserts byte-identical repeated archive builds after changing source mtimes or permissions.

## Metadata inventory and deterministic contract

For byte-for-byte reproducibility across supported Python versions and ordinary Unix/Windows runners, do not let `ZipInfo.from_file()` derive entry metadata. Construct each entry explicitly and write bytes with `ZipFile.writestr()`.

Chosen entry contract:

- filename: the existing canonical top-level feature filename;
- entry order: existing sorted feature order;
- `date_time`: `(1980, 1, 1, 0, 0, 0)`, the earliest portable ZIP timestamp and independent of wall clock/filesystem mtime;
- `compress_type`: `ZIP_DEFLATED`, preserving the current archive format;
- `create_system`: `3` (Unix), fixed rather than host-derived;
- `external_attr`: `0o100644 << 16`, fixed regular-file type + read/write owner/read others permissions;
- `extra`: empty bytes;
- `comment`: empty bytes;
- archive comment: default empty;
- input payload: `feature.read_bytes()` exactly.

A local reproduction with this explicit contract produced byte-identical archives when the corresponding source files had different mtimes **and** different filesystem modes. The member metadata round-tripped as the fixed timestamp, creator system, regular-file mode, empty extras/comments, and deflate compression.

No compression level will be explicitly changed in this ticket: the current `ZIP_DEFLATED` default is retained. The relevant invariant is deterministic output within the supported Python/runtime contract from identical input bytes; the ticket does not promise cross-zlib-version identity unless evidence shows that is required. The manifest will continue binding the actual published ZIP bytes.

## Boundaries

This ticket must not:

- modify `.tf` contents or ordering semantics;
- change `feature_set_sha256` derivation;
- weaken report, source, license, serialized-metadata, or manifest validation;
- alter release tag/commit/converter/data identity;
- publish/tag a release;
- change atomic staging/no-mix behavior;
- add nested files or non-`.tf` members.

## Interaction with current release work

#104 publication is separately blocked by #113. This ticket is logically independent and may merge while #113 is active. Any eventual v0.2.0 release candidate must be cut from a main lineage containing all release blockers/fixes and receive fresh exact-candidate gates/review before tagging.